from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable, Mapping, Protocol

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


@dataclass(frozen=True)
class CombatDrainReport:
    processed_events: int = 0
    duplicate_events: int = 0
    notices: int = 0
    fault_code: str | None = None


class CombatLineDecoder:
    """Incrementally decode strict UTF-8 JSON objects separated by newlines."""

    def __init__(self, *, max_line_bytes: int = MAX_LINE_BYTES) -> None:
        if max_line_bytes <= 0:
            raise ValueError("max_line_bytes must be positive")
        self.max_line_bytes = max_line_bytes
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:
        if not isinstance(chunk, bytes):
            raise TypeError("chunk must be bytes")
        self._buffer.extend(chunk)
        if len(self._buffer) > self.max_line_bytes and b"\n" not in self._buffer:
            self._buffer.clear()
            raise CombatProtocolError("line_too_long")

        records: list[dict[str, Any]] = []
        while True:
            newline = self._buffer.find(b"\n")
            if newline < 0:
                break
            raw_line = bytes(self._buffer[:newline])
            del self._buffer[: newline + 1]
            if raw_line.endswith(b"\r"):
                raw_line = raw_line[:-1]
            if not raw_line:
                continue
            if len(raw_line) > self.max_line_bytes:
                raise CombatProtocolError("line_too_long")
            try:
                payload = json.loads(raw_line.decode("utf-8", errors="strict"))
            except UnicodeDecodeError as exception:
                raise CombatProtocolError("invalid_utf8") from exception
            except json.JSONDecodeError as exception:
                raise CombatProtocolError("invalid_json") from exception
            if not isinstance(payload, dict):
                raise CombatProtocolError("event_not_object")
            records.append(payload)

        if len(self._buffer) > self.max_line_bytes:
            self._buffer.clear()
            raise CombatProtocolError("line_too_long")
        return records

    def finish(self) -> None:
        if self._buffer:
            self._buffer.clear()
            raise CombatProtocolError("unterminated_line")


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
        error = next(self._validator.iter_errors(event), None)
        if error is None:
            return
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        keyword = str(error.validator or "schema")
        raise CombatSchemaError(f"schema_invalid:{path}:{keyword}")


class CombatInbox:
    """A bounded cross-thread inbox that fails closed instead of dropping events."""

    def __init__(self, *, max_items: int = MAX_QUEUE_ITEMS) -> None:
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        self.max_items = max_items
        self._items: deque[Mapping[str, Any] | TransportNotice] = deque()
        self._lock = threading.Lock()
        self._accepting = True
        self._fault_code: str | None = None

    @property
    def accepting(self) -> bool:
        with self._lock:
            return self._accepting

    def publish_event(self, event: Mapping[str, Any]) -> bool:
        return self._publish(dict(event))

    def publish_notice(self, state: str, detail_code: str) -> bool:
        return self._publish(TransportNotice(state, detail_code))

    def _publish(self, item: Mapping[str, Any] | TransportNotice) -> bool:
        with self._lock:
            if not self._accepting:
                return False
            if len(self._items) >= self.max_items:
                self._items.clear()
                self._accepting = False
                self._fault_code = "queue_overflow"
                return False
            self._items.append(item)
            return True

    def drain(self, *, limit: int = MAX_QUEUE_ITEMS) -> list[Mapping[str, Any] | TransportNotice]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._lock:
            if self._fault_code is not None:
                fault_code = self._fault_code
                self._fault_code = None
                self._items.clear()
                return [TransportNotice("error", fault_code)]
            items: list[Mapping[str, Any] | TransportNotice] = []
            while self._items and len(items) < limit:
                items.append(self._items.popleft())
            return items


class CombatEventPump:
    """Validate and apply inbox items on the Tk/main thread."""

    def __init__(
        self,
        inbox: CombatInbox,
        validator: CombatEventValidator,
        aggregator: CombatAggregator,
    ) -> None:
        self.inbox = inbox
        self.validator = validator
        self.aggregator = aggregator
        self.fault_code: str | None = None

    def drain(self, *, limit: int = MAX_QUEUE_ITEMS) -> CombatDrainReport:
        processed = 0
        duplicates = 0
        notices = 0
        for item in self.inbox.drain(limit=limit):
            if self.fault_code is not None:
                continue
            if isinstance(item, TransportNotice):
                notices += 1
                try:
                    self.aggregator.apply_transport_state(item.state)
                except CombatEventError:
                    self._fault("invalid_transport_state")
                if item.state == "error":
                    self.fault_code = item.detail_code
                continue
            try:
                self.validator.validate(item)
                accepted = self.aggregator.ingest(item)
            except (CombatSchemaError, CombatEventError) as exception:
                self._fault(self._fault_from(exception))
                continue
            if accepted:
                processed += 1
            else:
                duplicates += 1
        return CombatDrainReport(processed, duplicates, notices, self.fault_code)

    def _fault(self, code: str) -> None:
        self.fault_code = code
        self.aggregator.apply_transport_state("error")

    @staticmethod
    def _fault_from(exception: Exception) -> str:
        message = str(exception)
        if isinstance(exception, CombatSchemaError) and message.startswith("schema_invalid:"):
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
        while not self._stop_event.is_set() and self.inbox.accepting:
            if not self.inbox.publish_notice("connecting", "pipe_connecting"):
                return
            decoder = CombatLineDecoder()
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
                            if not self.inbox.publish_notice("stale", "heartbeat_timeout"):
                                return
                            stale_published = True
                        continue
                    if not chunk:
                        decoder.finish()
                        if not self._stop_event.is_set():
                            self.inbox.publish_notice("disconnected", "pipe_closed")
                        break
                    last_data_at = time.monotonic()
                    stale_published = False
                    for event in decoder.feed(chunk):
                        if not self.inbox.publish_event(event):
                            return
            except CombatProtocolError as exception:
                self.inbox.publish_notice("error", str(exception))
                return
            except Exception:
                if not self._stop_event.is_set():
                    self.inbox.publish_notice("disconnected", "pipe_unavailable")
            finally:
                with self._stream_lock:
                    stream = self._stream
                    self._stream = None
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            if not self._stop_event.is_set() and self.inbox.accepting:
                self._stop_event.wait(self.reconnect_delay)
