from __future__ import annotations

from collections import deque
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from typing import Any, Callable, ContextManager, Mapping, Protocol

from jsonschema import Draft202012Validator

from .combat_aggregator import CombatAggregator, CombatEventError


PIPE_NAME = r"\\.\pipe\LostCastle2Toolbox.Combat.v2"
MAX_LINE_BYTES = 64 * 1024
MAX_QUEUE_ITEMS = 512
READ_SIZE = 8192
RECONNECT_DELAY_SECONDS = 1.0
STALE_AFTER_SECONDS = 6.0


class CombatTransportError(ValueError):
    """Base class for bounded local transport failures."""


class CombatProtocolError(CombatTransportError):
    """Raised when the byte stream is not a valid bounded JSON-line stream."""


class CombatSchemaError(CombatTransportError):
    """Raised when an object does not satisfy the public combat-event contract."""


@dataclass(frozen=True)
class TransportNotice:
    state: str
    detail_code: str
    sample: str | None = None


@dataclass(frozen=True)
class CombatDrainReport:
    processed_events: int = 0
    duplicate_events: int = 0
    notices: int = 0
    fault_code: str | None = None


class CombatLineDecoder:
    """Incrementally decode strict UTF-8 JSON objects separated by newlines."""

    def __init__(self, *, max_line_bytes: int = MAX_LINE_BYTES, recover: bool = False) -> None:
        if max_line_bytes <= 0:
            raise ValueError("max_line_bytes must be positive")
        self.max_line_bytes = max_line_bytes
        self._buffer = bytearray()
        self.recover = recover
        self._discarding = False

    def feed(self, chunk: bytes) -> list[dict[str, Any] | TransportNotice]:
        if not isinstance(chunk, bytes):
            raise TypeError("chunk must be bytes")
        records: list[dict[str, Any] | TransportNotice] = []
        # Work one segment at a time: even a damaged unframed stream has a
        # bounded retained buffer, and the next newline restores framing.
        segments = chunk.split(b"\n")
        for index, segment in enumerate(segments):
            complete = index < len(segments) - 1
            if self._discarding:
                if complete:
                    self._discarding = False
                continue
            if len(self._buffer) + len(segment) > self.max_line_bytes:
                sample = (bytes(self._buffer) + segment[:4096])[:4096]
                self._buffer.clear()
                self._discarding = not complete
                records.append(self._reject("line_too_long", sample))
                continue
            self._buffer.extend(segment)
            if not complete:
                continue
            raw_line = bytes(self._buffer)
            self._buffer.clear()
            if raw_line.endswith(b"\r"):
                raw_line = raw_line[:-1]
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line.decode("utf-8", errors="strict"))
                _validate_finite(payload)
            except UnicodeDecodeError:
                records.append(self._reject("invalid_utf8", raw_line))
                continue
            except (ValueError, RecursionError):
                records.append(self._reject("invalid_json", raw_line))
                continue
            if not isinstance(payload, dict):
                records.append(self._reject("event_not_object", raw_line))
                continue
            records.append(payload)
        return records

    def _reject(self, code: str, raw: bytes) -> TransportNotice:
        if not self.recover:
            raise CombatProtocolError(code)
        return TransportNotice("degraded", code, raw[:4096].decode("utf-8", errors="replace"))

    def finish(self) -> TransportNotice | None:
        if self._buffer:
            raw = bytes(self._buffer)
            self._buffer.clear()
            return self._reject("unterminated_line", raw)
        return None


def _validate_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CombatSchemaError("non_finite_number")
    if isinstance(value, Mapping):
        for child in value.values():
            _validate_finite(child)
    elif isinstance(value, list):
        for child in value:
            _validate_finite(child)


class CombatEventValidator:
    def __init__(self, schema: Mapping[str, Any]) -> None:
        Draft202012Validator.check_schema(schema)
        self._validator = Draft202012Validator(schema)

    @classmethod
    def from_file(cls, path: Path) -> CombatEventValidator:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise CombatSchemaError("schema_not_object")
        return cls(payload)

    def validate(self, event: Mapping[str, Any]) -> None:
        try:
            _validate_finite(event)
        except RecursionError as exception:
            raise CombatSchemaError("event_too_deep") from exception
        error = next(self._validator.iter_errors(event), None)
        if error is None:
            return
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        keyword = str(error.validator or "schema")
        raise CombatSchemaError(f"schema_invalid:{path}:{keyword}")


class CombatInbox:
    """Bounded backpressure; retain the valid prefix and explicitly report loss."""

    def __init__(self, *, max_items: int = MAX_QUEUE_ITEMS) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        self.max_items = max_items
        self._items: deque[Mapping[str, Any] | TransportNotice] = deque()
        self._condition = threading.Condition()
        self._overflow: TransportNotice | None = None
        self._high_water = 0
        self._received = 0
        self._dropped = 0

    @property
    def accepting(self) -> bool:
        with self._condition:
            return self._overflow is None

    def publish_event(self, event: Mapping[str, Any], *, wait_timeout: float = 0) -> bool:
        return self._publish(dict(event), wait_timeout=wait_timeout)

    def publish_notice(self, state: str, detail_code: str, *, sample: str | None = None,
                       wait_timeout: float = 0) -> bool:
        return self._publish(TransportNotice(state, detail_code, sample), wait_timeout=wait_timeout)

    def _publish(self, item: Mapping[str, Any] | TransportNotice, *, wait_timeout: float) -> bool:
        with self._condition:
            available = lambda: self._overflow is None and len(self._items) < self.max_items
            if wait_timeout > 0:
                self._condition.wait_for(available, timeout=wait_timeout)
            if not available():
                self._dropped += 1
                if self._overflow is None:
                    self._overflow = TransportNotice("degraded", "queue_overflow", _sample(item))
                self._condition.notify_all()
                return False
            self._items.append(item)
            self._received += 1
            self._high_water = max(self._high_water, len(self._items))
            self._condition.notify_all()
            return True

    def drain(self, *, limit: int = MAX_QUEUE_ITEMS) -> list[Mapping[str, Any] | TransportNotice]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._condition:
            items: list[Mapping[str, Any] | TransportNotice] = []
            while self._items and len(items) < limit:
                items.append(self._items.popleft())
            if not self._items and self._overflow is not None and len(items) < limit:
                items.append(self._overflow)
                self._overflow = None
            self._condition.notify_all()
            return items

    def wait(self, timeout: float) -> None:
        with self._condition:
            self._condition.wait_for(lambda: bool(self._items) or self._overflow is not None, timeout)

    def diagnostic_state(self) -> dict[str, Any]:
        with self._condition:
            return {"depth": len(self._items), "capacity": self.max_items,
                    "high_water": self._high_water, "received": self._received,
                    "dropped_lower_bound": self._dropped, "overflow_pending": self._overflow is not None}


def _sample(item: Any) -> str:
    if isinstance(item, TransportNotice):
        return item.sample or item.detail_code
    return json.dumps(item, ensure_ascii=False, default=str)[:4096]


class CombatEventPump:
    """Single consumer independent of Tk; synchronous drain remains useful for replay."""

    def __init__(
        self,
        inbox: CombatInbox,
        validator: CombatEventValidator,
        aggregator: CombatAggregator,
        event_batch_sink: Callable[[tuple[Mapping[str, Any], ...]], None] | None = None,
        diagnostic_sink: Callable[..., None] | None = None,
        event_batch_context: Callable[[], ContextManager[Any]] | None = None,
    ) -> None:
        self.inbox = inbox
        self.validator = validator
        self.aggregator = aggregator
        self.event_batch_sink = event_batch_sink
        self.diagnostic_sink = diagnostic_sink
        self.event_batch_context = event_batch_context or nullcontext
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.fault_code: str | None = None
        self._diagnostic_counts = {"processed": 0, "duplicates": 0, "notices": 0, "rejected": 0}
        self._last_accepted_at: float | None = None
        self._last_notice: dict[str, Any] | None = None
        self._last_fault_code: str | None = None
        self._issues: deque[dict[str, Any]] = deque(maxlen=16)
        self._recent_context: deque[dict[str, Any]] = deque(maxlen=8)
        self._recovery_count = 0
        self._last_recovered_at: float | None = None
        self._last_drain_at: float | None = None
        self._last_ui_tick: float | None = None
        self._last_ui_tick_mono: float | None = None
        self._max_ui_gap = 0.0
        self._last_health_mono = 0.0
        self._last_transition_emit: dict[str, float] = {}
        self._suppressed_journal_events = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="LC2CombatEventPump", daemon=True)
        self._thread.start()

    def stop(self, *, join_timeout: float = 2.0) -> bool:
        self._stop_event.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=max(0.0, join_timeout))
        return not self.running

    def note_ui_tick(self) -> None:
        # The UI heartbeat never waits for validation or archival I/O.
        now = time.monotonic()
        previous = self._last_ui_tick_mono
        if previous is not None:
            self._max_ui_gap = max(self._max_ui_gap, now - previous)
        self._last_ui_tick_mono = now
        self._last_ui_tick = time.time()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.inbox.wait(0.05)
            try:
                self.drain()
            except Exception as exception:
                with self._lock:
                    self._fault("consumer_exception:" + type(exception).__name__)
            if time.monotonic() - self._last_health_mono >= 5:
                self._last_health_mono = time.monotonic()
                self._emit("combat_transport_health", **self.diagnostic_state(include_samples=False))

    def diagnostic_state(self, *, include_samples: bool = True) -> dict[str, Any]:
        with self._lock:
            return self._diagnostic_state_locked(include_samples)

    def _diagnostic_state_locked(self, include_samples: bool) -> dict[str, Any]:
        state = {
            "counts": dict(self._diagnostic_counts), "fault_code": self.fault_code,
            "last_accepted_at": self._last_accepted_at, "last_notice": self._last_notice,
            "inbox_accepting": self.inbox.accepting,
            "inbox": self.inbox.diagnostic_state(), "worker_running": self.running,
            "last_fault_code": self._last_fault_code, "recovery_count": self._recovery_count,
            "last_recovered_at": self._last_recovered_at, "last_drain_at": self._last_drain_at,
            "last_ui_tick": self._last_ui_tick,
            "ui_tick_age_seconds": None if self._last_ui_tick_mono is None else round(time.monotonic() - self._last_ui_tick_mono, 3),
            "max_ui_gap_seconds": round(self._max_ui_gap, 3),
            "suppressed_journal_events": self._suppressed_journal_events,
        }
        if include_samples:
            state["recent_issues"] = list(self._issues)
            state["recent_context"] = list(self._recent_context)
        return state

    def drain(self, *, limit: int = MAX_QUEUE_ITEMS) -> CombatDrainReport:
        with self._lock, self.event_batch_context():
            return self._drain_locked(limit=limit)

    def _drain_locked(self, *, limit: int) -> CombatDrainReport:
        self._last_drain_at = time.time()
        processed = 0
        duplicates = 0
        notices = 0
        accepted_events: list[Mapping[str, Any]] = []
        for item in self.inbox.drain(limit=limit):
            if isinstance(item, TransportNotice):
                notices += 1
                self._last_notice = {"state": item.state, "detail_code": item.detail_code, "observed_at": time.time()}
                if item.state == "degraded":
                    self._diagnostic_counts["rejected"] += 1
                    self._fault(item.detail_code, item)
                else:
                    try:
                        snapshot = self.aggregator.snapshot()
                        if snapshot.connection_state == "ended" and item.state in {
                            "connecting", "disconnected", "stale", "error"
                        }:
                            # Idle reconnect attempts do not invalidate a
                            # completed settlement. A new game boundary resumes it.
                            continue
                        if item.state in {"disconnected", "stale", "error"}:
                            if snapshot.session_id is not None and snapshot.connection_state != "ended":
                                self._fault(item.detail_code, item)
                        self.aggregator.apply_transport_state(item.state)
                    except CombatEventError:
                        self._fault("invalid_transport_state", item)
                continue
            try:
                self.validator.validate(item)
                if accepted_events and item.get("session_id") != accepted_events[-1].get("session_id"):
                    # Freeze a valid prefix before any explicit foreign boundary
                    # can reset the summary, even when the old ending was lost.
                    self._publish_accepted_events(accepted_events)
                    accepted_events.clear()
                accepted = self.aggregator.ingest(item)
            except Exception as exception:
                self._diagnostic_counts["rejected"] += 1
                self._fault(self._fault_from(exception), item)
                continue
            if accepted:
                processed += 1
                self._last_accepted_at = time.time()
                self._recent_context.append({key: item.get(key) for key in
                    ("session_id", "event_id", "sequence", "monotonic_ms", "event_type", "status")})
                if item.get("event_type") == "status" and item.get("status") == "error":
                    self._fault(str(item.get("detail") or "bridge_error"), item)
                elif self.fault_code is not None:
                    # Receiving one valid record proves consumption resumed;
                    # session quality remains incomplete independently.
                    self._recovery_count += 1
                    self._last_recovered_at = time.time()
                    self._emit("combat_transport_recovered", previous_fault=self.fault_code)
                    self.fault_code = None
                accepted_events.append(dict(item))
                if (
                    item.get("event_type") == "status"
                    and item.get("status") == "session_ended"
                ):
                    self._publish_accepted_events(accepted_events)
                    accepted_events.clear()
            else:
                duplicates += 1
        self._publish_accepted_events(accepted_events)
        self._diagnostic_counts["processed"] += processed
        self._diagnostic_counts["duplicates"] += duplicates
        self._diagnostic_counts["notices"] += notices
        return CombatDrainReport(processed, duplicates, notices, self.fault_code)

    def _publish_accepted_events(
        self,
        events: list[Mapping[str, Any]],
    ) -> None:
        if not events or self.event_batch_sink is None:
            return
        try:
            self.event_batch_sink(tuple(events))
        except Exception as exception:
            # Archival is an independent local side effect. A disk/export
            # failure must not corrupt the live combat aggregation session.
            self._emit("combat_archive_failed", error_type=type(exception).__name__)

    def _emit(self, event: str, **details: Any) -> None:
        if self.diagnostic_sink is not None:
            if event in {"combat_transport_issue", "combat_transport_recovered"}:
                now = time.monotonic()
                if now - self._last_transition_emit.get(event, 0.0) < 1:
                    self._suppressed_journal_events += 1
                    return
                self._last_transition_emit[event] = now
            try:
                self.diagnostic_sink(event, **details)
            except Exception:
                pass

    def _fault(self, code: str, item: Any = None) -> None:
        self.fault_code = code
        self._last_fault_code = code
        self.aggregator.mark_data_gap(code)
        sample = _sample(item) if item is not None else ""
        issue = {"code": code, "observed_at": time.time(), "sample": sample,
                 "sample_sha256": hashlib.sha256(sample.encode("utf-8")).hexdigest(),
                 "sample_limit_chars": 4096, "previous_context": list(self._recent_context)}
        self._issues.append(issue)
        self._emit("combat_transport_issue", **issue)

    @staticmethod
    def _fault_from(exception: Exception) -> str:
        message = str(exception)
        if isinstance(exception, CombatSchemaError):
            return message
        return type(exception).__name__


class ReadableStream(Protocol):
    def read(self, size: int) -> bytes | None: ...

    def close(self) -> None: ...


class NamedPipeStream:
    def __init__(
        self,
        handle: Any,
        win32file_module: Any,
        win32pipe_module: Any,
        *,
        poll_interval: float = 0.05,
    ) -> None:
        self._handle = handle
        self._win32file = win32file_module
        self._win32pipe = win32pipe_module
        self._poll_interval = poll_interval
        self._closed = False

    def read(self, size: int) -> bytes | None:
        if self._closed:
            return b""
        _preview, available, _remaining = self._win32pipe.PeekNamedPipe(self._handle, 0)
        if available <= 0:
            time.sleep(self._poll_interval)
            return None
        _result, data = self._win32file.ReadFile(self._handle, min(size, available))
        return bytes(data)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._win32file.CloseHandle(self._handle)


class NamedPipeConnector:
    def __init__(self, pipe_name: str = PIPE_NAME, *, wait_timeout_ms: int = 750) -> None:
        self.pipe_name = pipe_name
        self.wait_timeout_ms = wait_timeout_ms

    def __call__(self) -> NamedPipeStream:
        import win32file
        import win32pipe

        win32pipe.WaitNamedPipe(self.pipe_name, self.wait_timeout_ms)
        handle = win32file.CreateFile(
            self.pipe_name,
            win32file.GENERIC_READ,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None,
        )
        return NamedPipeStream(handle, win32file, win32pipe)


class CombatBridgeClient:
    """Reconnect a read-only named-pipe client without touching the aggregator."""

    def __init__(
        self,
        inbox: CombatInbox,
        *,
        connector: Callable[[], ReadableStream] | None = None,
        reconnect_delay: float = RECONNECT_DELAY_SECONDS,
        read_size: int = READ_SIZE,
        stale_after: float = STALE_AFTER_SECONDS,
    ) -> None:
        if reconnect_delay < 0:
            raise ValueError("reconnect_delay cannot be negative")
        if read_size <= 0:
            raise ValueError("read_size must be positive")
        if stale_after <= 0:
            raise ValueError("stale_after must be positive")
        self.inbox = inbox
        self.connector = connector or NamedPipeConnector()
        self.reconnect_delay = reconnect_delay
        self.read_size = read_size
        self.stale_after = stale_after
        self._stop_event = threading.Event()
        self._stream_lock = threading.Lock()
        self._stream: ReadableStream | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="LC2CombatBridgeClient",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, join_timeout: float = 2.0) -> None:
        self._stop_event.set()
        with self._stream_lock:
            stream = self._stream
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, join_timeout))

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self.inbox.publish_notice("connecting", "pipe_connecting", wait_timeout=0.25):
                self._stop_event.wait(max(0.05, self.reconnect_delay))
                continue
            decoder = CombatLineDecoder(recover=True)
            try:
                stream = self.connector()
                with self._stream_lock:
                    self._stream = stream
                last_data_at = time.monotonic()
                stale_published = False
                while not self._stop_event.is_set():
                    chunk = stream.read(self.read_size)
                    if chunk is None:
                        if (
                            not stale_published
                            and time.monotonic() - last_data_at >= self.stale_after
                        ):
                            if not self.inbox.publish_notice("stale", "heartbeat_timeout", wait_timeout=0.25):
                                break
                            stale_published = True
                            break
                        continue
                    if not chunk:
                        tail_notice = decoder.finish()
                        if tail_notice is not None:
                            self.inbox.publish_notice(tail_notice.state, tail_notice.detail_code,
                                                      sample=tail_notice.sample, wait_timeout=0.25)
                        if not self._stop_event.is_set():
                            self.inbox.publish_notice("disconnected", "pipe_closed", wait_timeout=0.25)
                        break
                    last_data_at = time.monotonic()
                    stale_published = False
                    reconnect = False
                    for event in decoder.feed(chunk):
                        if self._stop_event.is_set():
                            break
                        if isinstance(event, TransportNotice):
                            published = self.inbox.publish_notice(event.state, event.detail_code,
                                                                  sample=event.sample, wait_timeout=0.25)
                        else:
                            published = self.inbox.publish_event(event, wait_timeout=0.25)
                        if not published or (
                            isinstance(event, dict) and event.get("event_type") == "status"
                            and event.get("status") == "error"
                        ):
                            # Close this stream to request the Bridge's existing
                            # resume anchors. The outer client stays alive.
                            reconnect = True
                            break
                    if reconnect:
                        break
            except Exception:
                if not self._stop_event.is_set():
                    self.inbox.publish_notice("disconnected", "pipe_unavailable", wait_timeout=0.25)
            finally:
                with self._stream_lock:
                    stream = self._stream
                    self._stream = None
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            if not self._stop_event.is_set():
                self._stop_event.wait(self.reconnect_delay)
