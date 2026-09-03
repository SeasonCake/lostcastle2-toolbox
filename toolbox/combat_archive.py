from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Callable, Iterable, Mapping
import uuid
import zipfile


ARCHIVE_SCHEMA_VERSION = 1
DEFAULT_MAX_EVENT_BYTES = 128 * 1024 * 1024
PARTIAL_PREFIX = "_partial_"


class CombatArchiveError(RuntimeError):
    """Raised when an archive cannot be safely created or validated."""


@dataclass(frozen=True)
class CombatArchiveConsistency:
    path: Path
    archive_reason: str
    session_key: str
    summary_session_id: str | None
    events_session_id: str | None
    event_count: int


@dataclass
class ActiveCombatArchive:
    session_id: str
    session_key: str
    directory: Path
    events_path: Path
    summary_path: Path
    meta_path: Path
    started_at: str
    event_count: int = 0
    event_bytes: int = 0
    events_truncated: bool = False


def check_combat_archive_consistency(path: Path) -> CombatArchiveConsistency:
    """Reject archives whose manifest, summary, or events identify different runs."""

    archive_path = Path(path)
    manifest, session_key, summary_session_id = _read_archive_identity(archive_path)
    event_ids: set[str] = set()
    event_session_ids: set[str] = set()
    actual_event_bytes = 0
    actual_event_count = 0
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open("events.jsonl") as events_stream:
                for encoded_line in events_stream:
                    actual_event_bytes += len(encoded_line)
                    actual_event_count += 1
                    digest.update(encoded_line)
                    if not encoded_line.strip():
                        raise CombatArchiveError("archive_events_invalid")
                    try:
                        item = json.loads(encoded_line.decode("utf-8"))
                    except (UnicodeError, ValueError) as exception:
                        raise CombatArchiveError("archive_events_invalid") from exception
                    if not isinstance(item, Mapping):
                        raise CombatArchiveError("archive_events_invalid")
                    event_id = item.get("event_id")
                    if not isinstance(event_id, str) or not event_id:
                        raise CombatArchiveError("archive_event_id_invalid")
                    if event_id in event_ids:
                        raise CombatArchiveError("archive_duplicate_event_id")
                    event_ids.add(event_id)
                    event_session_id = item.get("session_id")
                    if not isinstance(event_session_id, str) or not event_session_id:
                        raise CombatArchiveError("archive_event_session_invalid")
                    event_session_ids.add(event_session_id)
    except CombatArchiveError:
        raise
    except (OSError, KeyError, UnicodeError, ValueError, zipfile.BadZipFile) as exception:
        raise CombatArchiveError("archive_unreadable") from exception

    event_count = _manifest_nonnegative_int(manifest, "event_count")
    event_bytes = _manifest_nonnegative_int(manifest, "event_bytes")
    events_truncated = manifest.get("events_truncated")
    if not isinstance(events_truncated, bool):
        raise CombatArchiveError("archive_events_truncated_invalid")
    if event_bytes != actual_event_bytes:
        raise CombatArchiveError("archive_event_bytes_mismatch")
    expected_sha256 = manifest.get("events_sha256")
    actual_sha256 = digest.hexdigest().upper()
    if not isinstance(expected_sha256, str) or expected_sha256.upper() != actual_sha256:
        raise CombatArchiveError("archive_events_sha256_mismatch")
    if events_truncated:
        if actual_event_count > event_count:
            raise CombatArchiveError("archive_event_count_mismatch")
    elif actual_event_count != event_count:
        raise CombatArchiveError("archive_event_count_mismatch")

    if len(event_session_ids) > 1:
        raise CombatArchiveError("archive_events_session_mismatch")
    events_session_id = next(iter(event_session_ids), None)
    if events_session_id is not None and events_session_id != summary_session_id:
        raise CombatArchiveError("archive_events_session_mismatch")
    archive_reason = manifest.get("archive_reason")
    if not isinstance(archive_reason, str) or not archive_reason:
        raise CombatArchiveError("archive_reason_invalid")

    return CombatArchiveConsistency(
        path=archive_path,
        archive_reason=archive_reason,
        session_key=session_key,
        summary_session_id=summary_session_id,
        events_session_id=events_session_id,
        event_count=event_count,
    )


def _read_archive_identity(
    archive_path: Path,
) -> tuple[Mapping[str, Any], str, str | None]:
    expected_members = {"manifest.json", "summary.json", "events.jsonl"}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) != len(expected_members) or set(names) != expected_members:
                raise CombatArchiveError("archive_members_invalid")
            manifest = json.loads(archive.read("manifest.json"))
            summary = json.loads(archive.read("summary.json"))
    except CombatArchiveError:
        raise
    except (OSError, KeyError, UnicodeError, ValueError, zipfile.BadZipFile) as exception:
        raise CombatArchiveError("archive_unreadable") from exception
    if not isinstance(manifest, Mapping):
        raise CombatArchiveError("archive_manifest_invalid")
    if not isinstance(summary, Mapping):
        raise CombatArchiveError("archive_summary_invalid")
    if manifest.get("schema_version") != ARCHIVE_SCHEMA_VERSION:
        raise CombatArchiveError("archive_schema_unsupported")
    session_key = manifest.get("session_key")
    if not isinstance(session_key, str) or not session_key:
        raise CombatArchiveError("archive_session_key_invalid")
    summary_session_id = _summary_session_id(summary)
    expected_summary_key = (
        "no-session"
        if summary_session_id is None
        else _session_key(summary_session_id)
    )
    if session_key != expected_summary_key:
        raise CombatArchiveError("archive_summary_session_mismatch")
    return manifest, session_key, summary_session_id


def _manifest_nonnegative_int(manifest: Mapping[str, Any], name: str) -> int:
    value = manifest.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CombatArchiveError(f"archive_{name}_invalid")
    return value


def _summary_session_id(summary: Mapping[str, Any]) -> str | None:
    value = summary.get("session_id")
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise CombatArchiveError("archive_summary_session_invalid")
    return value


def _session_key(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:10].upper()


class CombatMatchArchiver:
    """Crash-recoverable anonymous combat event archives.

    The live journal is intentionally a task-owned partial directory. Automatic
    settlement or manual export produces a single ZIP containing manifest,
    summary, and accepted protocol events. The protocol exposes only anonymous
    player/entity tokens; this class never reads game logs, nicknames, or platform
    account identifiers.
    """

    def __init__(
        self,
        root: Path,
        *,
        app_version: str,
        snapshot_provider: Callable[[], Any],
        max_event_bytes: int = DEFAULT_MAX_EVENT_BYTES,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if max_event_bytes <= 0:
            raise ValueError("max_event_bytes must be positive")
        self.root = root.resolve()
        self.app_version = str(app_version)
        self.snapshot_provider = snapshot_provider
        self.max_event_bytes = int(max_event_bytes)
        self.now = now or (lambda: datetime.now().astimezone())
        self._lock = threading.RLock()
        self._active: ActiveCombatArchive | None = None
        self._last_archive_path: Path | None = None
        self._finalized_session_keys: set[str] = set()
        self.last_error: str | None = None
        self.root.mkdir(parents=True, exist_ok=True)
        self._recover_stale_partials()
        self._load_existing_archives()

    @property
    def active_session_key(self) -> str | None:
        with self._lock:
            return self._active.session_key if self._active is not None else None

    def record_events(self, events: Iterable[Mapping[str, Any]]) -> None:
        batch = tuple(dict(event) for event in events)
        if not batch:
            return
        with self._lock:
            try:
                for event in batch:
                    session_id = str(event.get("session_id") or "")
                    if not session_id:
                        continue
                    session_key = self._session_key(session_id)
                    session_ended = (
                        event.get("event_type") == "status"
                        and event.get("status") == "session_ended"
                    )
                    if self._active is None:
                        if session_ended or session_key in self._finalized_session_keys:
                            continue
                        self._active = self._start_partial(session_id)
                    elif self._active.session_id != session_id:
                        if session_ended:
                            continue
                        self._finalize_active("superseded")
                        if session_key in self._finalized_session_keys:
                            continue
                        self._active = self._start_partial(session_id)
                    self._append_event(self._active, event)
                    if session_ended:
                        self._finalize_active("automatic")
                if self._active is not None:
                    self._write_checkpoint(self._active)
                self.last_error = None
            except Exception as exception:
                self.last_error = type(exception).__name__

    def checkpoint(self) -> None:
        with self._lock:
            if self._active is None:
                return
            try:
                self._write_checkpoint(self._active)
                self.last_error = None
            except Exception as exception:
                self.last_error = type(exception).__name__

    def export_manual(self) -> Path:
        with self._lock:
            try:
                if self._active is not None:
                    self._write_checkpoint(self._active)
                    result = self._zip_partial(self._active, "manual")
                elif self._last_archive_path is not None and self._last_archive_path.is_file():
                    result = self._last_archive_path
                else:
                    result = self._export_snapshot_only()
                self.last_error = None
                return result
            except Exception as exception:
                self.last_error = type(exception).__name__
                raise CombatArchiveError("manual_export_failed") from exception

    def _start_partial(self, session_id: str) -> ActiveCombatArchive:
        timestamp = self._timestamp()
        session_key = self._session_key(session_id)
        directory = self.root / (
            f"{PARTIAL_PREFIX}{timestamp}_{session_key}_{uuid.uuid4().hex[:8]}"
        )
        directory.mkdir(parents=False, exist_ok=False)
        active = ActiveCombatArchive(
            session_id=session_id,
            session_key=session_key,
            directory=directory,
            events_path=directory / "events.jsonl",
            summary_path=directory / "summary.json",
            meta_path=directory / "partial-meta.json",
            started_at=self.now().isoformat(),
        )
        active.events_path.write_bytes(b"")
        self._write_json_atomic(
            active.meta_path,
            {
                "schema_version": ARCHIVE_SCHEMA_VERSION,
                "app_version": self.app_version,
                "session_key": session_key,
                "started_at": active.started_at,
            },
        )
        return active

    def _append_event(
        self,
        active: ActiveCombatArchive,
        event: Mapping[str, Any],
    ) -> None:
        active.event_count += 1
        encoded = (
            json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        if active.events_truncated or active.event_bytes + len(encoded) > self.max_event_bytes:
            active.events_truncated = True
            return
        with active.events_path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
        active.event_bytes += len(encoded)

    def _write_checkpoint(self, active: ActiveCombatArchive) -> None:
        self._freeze_matching_summary(active)
        self._write_json_atomic(
            active.meta_path,
            {
                "schema_version": ARCHIVE_SCHEMA_VERSION,
                "app_version": self.app_version,
                "session_key": active.session_key,
                "started_at": active.started_at,
                "last_checkpoint_at": self.now().isoformat(),
                "event_count": active.event_count,
                "event_bytes": active.event_bytes,
                "events_truncated": active.events_truncated,
            },
        )

    def _finalize_active(self, reason: str) -> Path:
        if self._active is None:
            raise CombatArchiveError("no_active_archive")
        active = self._active
        self._write_checkpoint(active)
        result = self._zip_partial(active, reason)
        self._remove_owned_partial(active.directory)
        self._active = None
        return result

    def _zip_partial(self, active: ActiveCombatArchive, reason: str) -> Path:
        return self._create_zip(
            reason=reason,
            session_key=active.session_key,
            started_at=active.started_at,
            event_count=active.event_count,
            event_bytes=active.event_bytes,
            events_truncated=active.events_truncated,
            events_path=active.events_path,
            summary_path=active.summary_path,
        )

    def _export_snapshot_only(self) -> Path:
        with tempfile.TemporaryDirectory(prefix="lc2-manual-", dir=self.root) as temp:
            directory = Path(temp)
            events_path = directory / "events.jsonl"
            summary_path = directory / "summary.json"
            events_path.write_bytes(b"")
            summary = self._snapshot_payload()
            summary_session_id = _summary_session_id(summary)
            session_key = (
                "no-session"
                if summary_session_id is None
                else self._session_key(summary_session_id)
            )
            self._write_json_atomic(summary_path, summary)
            return self._create_zip(
                reason="manual",
                session_key=session_key,
                started_at=self.now().isoformat(),
                event_count=0,
                event_bytes=0,
                events_truncated=False,
                events_path=events_path,
                summary_path=summary_path,
            )

    def _create_zip(
        self,
        *,
        reason: str,
        session_key: str,
        started_at: str,
        event_count: int,
        event_bytes: int,
        events_truncated: bool,
        events_path: Path,
        summary_path: Path,
    ) -> Path:
        label = {
            "automatic": "自动",
            "manual": "手动",
            "recovered": "恢复",
            "superseded": "恢复",
        }.get(reason, "归档")
        target = self._unique_archive_path(label, session_key)
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        manifest = {
            "schema_version": ARCHIVE_SCHEMA_VERSION,
            "app_version": self.app_version,
            "archive_reason": reason,
            "session_key": session_key,
            "started_at": started_at,
            "archived_at": self.now().isoformat(),
            "event_count": event_count,
            "event_bytes": event_bytes,
            "events_truncated": events_truncated,
            "events_sha256": self._sha256(events_path),
            "privacy": "anonymous_protocol_tokens_only",
        }
        try:
            with zipfile.ZipFile(
                temporary,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                archive.writestr(
                    "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                )
                archive.write(summary_path, "summary.json")
                archive.write(events_path, "events.jsonl")
            check_combat_archive_consistency(temporary)
            os.replace(temporary, target)
            self._last_archive_path = target
            if reason in {"automatic", "superseded"}:
                self._finalized_session_keys.add(session_key)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def _recover_stale_partials(self) -> None:
        for directory in sorted(self.root.glob(f"{PARTIAL_PREFIX}*")):
            if not directory.is_dir():
                continue
            try:
                meta_path = directory / "partial-meta.json"
                summary_path = directory / "summary.json"
                events_path = directory / "events.jsonl"
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if not summary_path.is_file() or not events_path.is_file():
                    continue
                event_count = 0
                with events_path.open("rb") as stream:
                    for _line in stream:
                        event_count += 1
                self._create_zip(
                    reason="recovered",
                    session_key=str(meta.get("session_key") or "unknown"),
                    started_at=str(meta.get("started_at") or "unknown"),
                    event_count=max(event_count, int(meta.get("event_count") or 0)),
                    event_bytes=events_path.stat().st_size,
                    events_truncated=bool(meta.get("events_truncated")),
                    events_path=events_path,
                    summary_path=summary_path,
                )
                self._remove_owned_partial(directory)
            except Exception as exception:
                self.last_error = type(exception).__name__

    def _load_existing_archives(self) -> None:
        existing = sorted(self.root.glob("*.zip"), key=lambda path: path.stat().st_mtime)
        consistent: list[Path] = []
        for path in existing:
            try:
                result = check_combat_archive_consistency(path)
                if result.archive_reason in {"automatic", "superseded"}:
                    self._finalized_session_keys.add(result.session_key)
                consistent.append(path)
            except Exception as exception:
                self.last_error = type(exception).__name__
        if consistent:
            self._last_archive_path = consistent[-1]

    def _remove_owned_partial(self, directory: Path) -> None:
        resolved = directory.resolve()
        if resolved.parent != self.root or not resolved.name.startswith(PARTIAL_PREFIX):
            raise CombatArchiveError("unsafe_partial_path")
        for name in ("events.jsonl", "summary.json", "partial-meta.json"):
            (resolved / name).unlink(missing_ok=True)
        try:
            resolved.rmdir()
        except OSError as exception:
            raise CombatArchiveError("partial_not_empty") from exception

    def _snapshot_payload(self) -> dict[str, Any]:
        snapshot = self.snapshot_provider()
        if hasattr(snapshot, "to_dict"):
            payload = snapshot.to_dict()
        elif isinstance(snapshot, Mapping):
            payload = dict(snapshot)
        else:
            raise CombatArchiveError("snapshot_not_serializable")
        if not isinstance(payload, dict):
            raise CombatArchiveError("snapshot_not_object")
        return payload

    def _freeze_matching_summary(self, active: ActiveCombatArchive) -> None:
        try:
            payload = self._snapshot_payload()
        except Exception:
            self._require_frozen_summary(active)
            return
        if payload.get("session_id") == active.session_id:
            self._write_json_atomic(active.summary_path, payload)
            return
        self._require_frozen_summary(active)

    @staticmethod
    def _require_frozen_summary(active: ActiveCombatArchive) -> None:
        try:
            payload = json.loads(active.summary_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exception:
            raise CombatArchiveError("frozen_summary_unavailable") from exception
        if not isinstance(payload, Mapping):
            raise CombatArchiveError("frozen_summary_invalid")
        if payload.get("session_id") != active.session_id:
            raise CombatArchiveError("frozen_summary_session_mismatch")

    def _unique_archive_path(self, label: str, session_key: str) -> Path:
        base = f"{self._timestamp()}_{label}_{session_key}"
        candidate = self.root / f"{base}.zip"
        index = 2
        while candidate.exists():
            candidate = self.root / f"{base}_{index}.zip"
            index += 1
        return candidate

    def _timestamp(self) -> str:
        return self.now().strftime("%Y-%m-%d_%H%M%S")

    @staticmethod
    def _session_key(session_id: str) -> str:
        return _session_key(session_id)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().upper()

    @staticmethod
    def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


class CombatDiagnosticsController:
    """Toggle candidate-only event capture without changing live aggregation."""

    def __init__(
        self,
        archiver: CombatMatchArchiver,
        *,
        enabled: bool = True,
        on_enabled_changed: Callable[[bool], None] | None = None,
    ) -> None:
        self.archiver = archiver
        self._enabled = bool(enabled)
        self.on_enabled_changed = on_enabled_changed

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def root(self) -> Path:
        return self.archiver.root

    @property
    def last_error(self) -> str | None:
        return self.archiver.last_error

    def set_enabled(self, enabled: bool) -> None:
        next_enabled = bool(enabled)
        if next_enabled == self._enabled:
            return
        if not next_enabled:
            self.archiver.checkpoint()
        previous = self._enabled
        self._enabled = next_enabled
        try:
            if self.on_enabled_changed is not None:
                self.on_enabled_changed(next_enabled)
        except Exception:
            self._enabled = previous
            raise

    def record_events(self, events: Iterable[Mapping[str, Any]]) -> None:
        batch = tuple(dict(event) for event in events)
        if not batch:
            return
        if self._enabled:
            self.archiver.record_events(batch)
            return
        if self.archiver.active_session_key is None:
            return
        endings = tuple(
            event
            for event in batch
            if event.get("event_type") == "status"
            and event.get("status") == "session_ended"
        )
        if endings:
            self.archiver.record_events(endings)

    def export_manual(self) -> Path:
        return self.archiver.export_manual()

    def checkpoint(self) -> None:
        self.archiver.checkpoint()
