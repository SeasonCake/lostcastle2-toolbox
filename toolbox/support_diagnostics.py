"""On-demand support reports, independent of detailed combat recording."""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import struct
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Mapping
import uuid
import zipfile


SCHEMA_VERSION = 1
MAX_READ_BYTES = 256 * 1024 * 1024
MAX_FILE_BYTES = 96 * 1024 * 1024
MAX_LOG_BYTES = 256 * 1024
MAX_SECONDS = 15.0
JOURNAL_BYTES = 512 * 1024
SETTINGS_KEYS = frozenset({
    "x", "y", "ui_scale", "toolbox_width", "toolbox_height", "toolbox_ui_scale",
    "hud_ui_scale", "input_display_mode", "selected_keys", "background_opacity",
    "show_background", "key_only", "always_on_top", "candidate_diagnostics_enabled",
    "game_path", "mouse_passthrough",
})
SENSITIVE_KEYS = frozenset({
    "password", "passwd", "token", "access_token", "authorization", "cookie",
    "secret", "api_key", "steam_id", "steamid", "account", "player_name",
    "username", "user_name", "email", "phone", "clipboard", "text_input",
})


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _utc(timestamp: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if timestamp is None else timestamp, timezone.utc).isoformat()


class DiagnosticLimitError(RuntimeError):
    pass


class DiagnosticRedactor:
    def __init__(self, roots: Mapping[Path, str]) -> None:
        self.roots = sorted(
            ((str(path), label) for path, label in roots.items()), key=lambda item: len(item[0]), reverse=True,
        )
        self.players: dict[str, str] = {}

    def learn_players(self, value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).lower() == "player_name" and isinstance(child, str) and child.strip():
                    self.players.setdefault(child, f"<player-{len(self.players) + 1}>")
                self.learn_players(child)
        elif isinstance(value, (tuple, list)):
            for child in value:
                self.learn_players(child)

    def text(self, value: str) -> str:
        for root, label in self.roots:
            pattern = r"[\\/]+".join(re.escape(part) for part in re.split(r"[\\/]+", root))
            value = re.sub(pattern, lambda _match: label, value, flags=re.IGNORECASE)
        value = re.sub(r"(?i)[a-z]:[\\/]Users[\\/][^\\/\s\"']+", "<user>", value)
        value = re.sub(r"(?i)\bBearer\s+[^\s,;\"']+", "Bearer <redacted>", value)
        keys = "|".join(re.escape(key) for key in sorted(SENSITIVE_KEYS))

        def hide_value(match: re.Match[str]) -> str:
            raw = match.group(2)
            plain = raw.strip("\"'")
            replacement = "<redacted>"
            if match.group(1).lower().startswith("player_name"):
                replacement = plain if re.fullmatch(r"<player-\d+>", plain) else self.players.get(plain, replacement)
            quote = raw[0] if raw.startswith(('"', "'")) else ""
            return match.group(1) + quote + replacement + quote

        value = re.sub(
            rf"(?i)(\b(?:{keys})[\"']?\s*[:=]\s*)(\"(?:\\.|[^\"])*\"|'[^']*'|[^\s,;]+)",
            hide_value, value,
        )
        value = re.sub(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@", r"\1<redacted>@", value)
        for name, alias in self.players.items():
            value = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", lambda _match: alias, value)
        return value

    def value(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): self.players.get(child, "<redacted>") if str(key).lower() == "player_name" and isinstance(child, str)
                else "<redacted>" if str(key).lower() in SENSITIVE_KEYS else self.value(child)
                for key, child in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.value(child) for child in value]
        if isinstance(value, Path):
            return self.text(str(value))
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return self.text(str(value))


def default_export_directory() -> Path:
    if os.name == "nt":
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        # CSIDL_PERSONAL respects redirected Windows Documents folders.
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0:
            return Path(buffer.value) / "失落城堡2工具箱" / "诊断"
    return Path.home() / "Documents" / "失落城堡2工具箱" / "诊断"


def game_process_state(game_exe: Path, timeout: float = 3.0) -> dict[str, Any]:
    if os.name != "nt":
        return {"state": "unavailable", "reason": "not_windows"}
    script = (
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
        "$ErrorActionPreference='Stop'; "
        "@(Get-CimInstance Win32_Process -Filter \"Name='LostCastle2.exe'\" -OperationTimeoutSec 2 | "
        "Select-Object ProcessId,ExecutablePath,@{Name='StartedUtc';Expression={"
        "$_.CreationDate.ToUniversalTime().ToString('o')}}) | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=max(0.1, timeout), check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        rows = json.loads(result.stdout.decode("utf-8-sig") or "[]")
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            raise ValueError("process_result_not_array")
        matching = [
            {"pid": row.get("ProcessId"), "started_at": row.get("StartedUtc")}
            for row in rows
            if str(row.get("ExecutablePath") or "").casefold() == str(game_exe).casefold()
        ]
        unknown = any(not row.get("ExecutablePath") for row in rows)
        return {"state": "running" if matching else "unknown" if unknown else "not_running", "processes": matching}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"state": "unknown", "reason": type(error).__name__}


@dataclass(frozen=True)
class SupportExport:
    path: Path
    partial: bool
    finding_count: int


class _Collector:
    def __init__(self, *, seconds: float, max_bytes: int) -> None:
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.phase_deadline = self.deadline
        self.max_bytes = max_bytes
        self.read_bytes = 0
        self.files_read = 0
        self.partial = False
        self.findings: list[dict[str, Any]] = []
        self.metadata: dict[Path, dict[str, Any]] = {}

    def check(self, size: int = 0) -> None:
        if time.monotonic() >= min(self.deadline, self.phase_deadline):
            raise DiagnosticLimitError("time_limit")
        if self.read_bytes + size > self.max_bytes:
            raise DiagnosticLimitError("read_bytes_limit")
        if self.files_read >= 512:
            raise DiagnosticLimitError("file_count_limit")
        self.read_bytes += size

    @staticmethod
    def plain_file(path: Path) -> bool:
        return path.is_file() and not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()

    def read(self, path: Path, *, limit: int = MAX_FILE_BYTES, tail: bool = False) -> bytes:
        self.check()
        if not self.plain_file(path):
            raise OSError("file_missing_or_link")
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > limit and not tail:
                raise DiagnosticLimitError("file_size_limit")
            if tail:
                stream.seek(max(0, before.st_size - limit))
            chunks = []
            remaining = limit + (0 if tail else 1)
            while remaining:
                self.check()
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.check(len(chunk))
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(stream.fileno())
        self.files_read += 1
        if not tail and (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise OSError("file_changed_during_read")
        data = b"".join(chunks)
        if len(data) > limit:
            raise DiagnosticLimitError("file_size_limit")
        return data

    def json_file(self, path: Path) -> dict[str, Any]:
        value = json.loads(self.read(path, limit=2 * 1024 * 1024).decode("utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError("json_not_object")
        return value

    def file(self, path: Path, expected: Mapping[str, Any] | None = None, *, metadata: bool = False) -> dict[str, Any]:
        cached = self.metadata.get(path)
        if cached is None:
            result: dict[str, Any] = {"path": str(path)}
            try:
                self.check()
                if not path.exists():
                    result["status"] = "missing"
                elif not self.plain_file(path):
                    result["status"] = "not_a_plain_file"
                else:
                    stat = path.stat()
                    data = self.read(path)
                    result.update(status="present", bytes=len(data), modified_at=_utc(stat.st_mtime), sha256=hashlib.sha256(data).hexdigest().upper())
                    if metadata and len(data) <= 8 * 1024 * 1024:
                        self.dll_metadata(data, result)
            except (OSError, ValueError, DiagnosticLimitError) as error:
                result.update(status="not_checked", reason=str(error), error_type=type(error).__name__)
                self.partial = True
            self.metadata[path] = result
            cached = result
        result = dict(cached)
        if expected is not None:
            result["expected"] = {key: expected.get(key) for key in ("size_bytes", "sha256")}
            result["matches"] = (
                None if result["status"] == "not_checked" else
                result.get("bytes") == expected.get("size_bytes") and result.get("sha256") == expected.get("sha256")
            )
            if result["matches"] is False:
                self.findings.append({"code": "file_identity_mismatch", "path": str(path), "status": result["status"]})
        return result

    @staticmethod
    def dll_metadata(data: bytes, result: dict[str, Any]) -> None:
        try:
            import dnfile
            from .mod_inspector import _bepin_plugin_metadata
            image = dnfile.dnPE(data=data)
            try:
                if image.net is None:
                    result["metadata_status"] = "not_managed"
                    return
                plugin = _bepin_plugin_metadata(data)
                result["plugin"] = dict(zip(("guid", "name", "version"), plugin)) if plugin else None
                assembly = image.net.mdtables.Assembly
                if assembly and assembly.rows:
                    row = assembly.rows[0]
                    result["assembly_name"] = str(row.Name)
                    result["assembly_version"] = ".".join(str(getattr(row, key)) for key in ("MajorVersion", "MinorVersion", "BuildNumber", "RevisionNumber"))
                references = image.net.mdtables.AssemblyRef
                result["assembly_references"] = [str(row.Name) for row in references.rows] if references else []
                result["metadata_status"] = "read"
            finally:
                image.close()
        except Exception as error:
            result["metadata_status"] = type(error).__name__


def _child(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    parts = normalized.split("/")
    if not normalized or normalized.startswith("/") or any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("invalid_relative_path")
    current = root
    for part in parts:
        current /= part
        if current.is_symlink() or getattr(current, "is_junction", lambda: False)():
            raise OSError("linked_input_not_read")
    return current


class SupportDiagnostics:
    def __init__(
        self, app_dir: Path, resource_dir: Path, config_dir: Path, *, app_version: str,
        game_exe_provider: Callable[[], Path | None] | None = None,
        output_directory: Path | None = None,
        process_probe: Callable[[Path, float], dict[str, Any]] = game_process_state,
        seconds: float = MAX_SECONDS, max_bytes: int = MAX_READ_BYTES,
    ) -> None:
        self.app_dir = app_dir.resolve()
        self.resource_dir = resource_dir.resolve()
        self.config_dir = config_dir.resolve()
        self.app_version = app_version
        self.game_exe_provider = game_exe_provider
        self.output_directory = output_directory
        self.process_probe = process_probe
        self.seconds = seconds
        self.max_bytes = max_bytes
        self.run_id = uuid.uuid4().hex
        self.started_at = _utc()
        self.journal_error: str | None = None
        self._journal_lock = threading.Lock()

    def redactor(self, game: Path | None = None) -> DiagnosticRedactor:
        roots = {Path.home(): "<user>", self.app_dir: "<toolbox>", self.resource_dir: "<resources>", self.config_dir: "<config>"}
        if game:
            roots[game.parent] = "<game>"
        return DiagnosticRedactor(roots)

    def record_event(self, event: str, **details: Any) -> None:
        """Bounded low-frequency operations only; never per-hit or global key capture."""
        try:
            row = self.redactor().value({"at": _utc(), "run_id": self.run_id, "event": event, **details})
            encoded = json.dumps(row, ensure_ascii=False, allow_nan=False)
            if len(encoded.encode("utf-8")) > 16 * 1024:
                row = {"at": _utc(), "run_id": self.run_id, "event": event, "details_truncated": True}
                encoded = json.dumps(row, ensure_ascii=False)
            with self._journal_lock:
                folder = self.config_dir / "support"
                if folder.is_symlink() or getattr(folder, "is_junction", lambda: False)():
                    raise OSError("linked_journal_directory")
                folder.mkdir(parents=True, exist_ok=True)
                path = _child(folder, "operations.jsonl")
                previous = _child(folder, "operations.previous.jsonl")
                if path.exists() and path.stat().st_size >= JOURNAL_BYTES:
                    path.replace(previous)
                with path.open("a", encoding="utf-8") as stream:
                    stream.write(encoded + "\n")
            self.journal_error = None
        except Exception as error:
            self.journal_error = type(error).__name__

    def _game(self, context: _Collector) -> Path | None:
        if self.game_exe_provider is not None:
            result = self.game_exe_provider()
            return Path(result).resolve() if result else None
        settings = self.config_dir / "settings.json"
        if settings.is_file():
            configured = context.json_file(settings).get("game_path")
            if isinstance(configured, str) and configured:
                return Path(configured).resolve()
        return None

    def _application(self, context: _Collector) -> dict[str, Any]:
        profile_path = self.resource_dir / "assets/build_profile.json"
        if not profile_path.exists() and not getattr(sys, "frozen", False):
            profile_path = self.resource_dir / "assets/build_profiles/diagnostic/build_profile.json"
        result: dict[str, Any] = {
            "toolbox_version": self.app_version, "frozen": bool(getattr(sys, "frozen", False)),
            "platform": platform.system(), "windows_version": platform.version(),
            "architecture": platform.machine(), "process_bits": struct.calcsize("P") * 8,
            "python_version": platform.python_version(), "pid": os.getpid(),
            "run_id": self.run_id, "started_at": self.started_at,
            "app_dir": str(self.app_dir), "resource_dir": str(self.resource_dir),
            "support_export_available": True, "journal_error": self.journal_error,
        }
        result["build_profile"] = context.json_file(profile_path)
        executable = Path(sys.executable) if getattr(sys, "frozen", False) else self.resource_dir / "keyview.py"
        result["executable"] = context.file(executable)
        settings = self.config_dir / "settings.json"
        result["settings"] = {
            key: value for key, value in context.json_file(settings).items() if key in SETTINGS_KEYS
        } if settings.is_file() else {"state": "not_created"}
        return result

    def _runtime(self, context: _Collector, game: Path | None) -> dict[str, Any]:
        if game is None:
            return {"state": "game_not_configured"}
        result: dict[str, Any] = {"game_executable": context.file(game), "game_path": str(game)}
        if game.name.casefold() != "lostcastle2.exe" or not game.is_file():
            result["state"] = "game_path_invalid"
            context.findings.append({"code": "game_path_invalid", "path": str(game)})
            return result
        result["process"] = self.process_probe(game, min(3.0, max(0.1, context.deadline - time.monotonic())))
        if result["process"].get("state") in {"unknown", "unavailable"}:
            context.partial = True
        manifest_path = self.resource_dir / "assets/lc2_runtime_manifest.json"
        manifest = context.json_file(manifest_path)
        result["manifest"] = context.file(manifest_path)
        result["expected_runtime_version"] = manifest.get("runtime_version")
        specs = manifest.get("runtime_files")
        required = manifest.get("required_paths")
        if not isinstance(specs, list) or not isinstance(required, list) or len(specs) > 512 or len(required) > 64:
            raise ValueError("invalid_runtime_manifest")
        by_path = {spec["path"]: spec for spec in specs}
        result["required_files"] = [
            context.file(_child(game.parent, relative), None if relative.lower().endswith(".cfg") else by_path[relative])
            for relative in required
        ]
        bridge = manifest.get("bridge", {})
        bridge_target = bridge.get("target") or bridge.get("path")
        if bridge_target:
            result["bridge"] = context.file(_child(game.parent, bridge_target), bridge, metadata=True)
        archive = manifest.get("runtime_archive", {})
        if archive.get("filename"):
            result["bundled_runtime"] = context.file(_child(self.resource_dir / "third_party/lc2_runtime", archive["filename"]), archive)
        config = _child(game.parent, "BepInEx/config/BepInEx.cfg")
        if config.is_file():
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.read_string(context.read(config, limit=256 * 1024).decode("utf-8-sig"))
            result["configuration"] = {
                f"{section}.{key}": parser.get(section, key, fallback=None)
                for section, key in (("IL2CPP", "UnityBaseLibrariesSource"), ("IL2CPP", "UpdateInteropAssemblies"), ("Logging.Console", "Enabled"))
            }
        libraries = _child(game.parent, "BepInEx/unity-libs")
        caches = []
        if libraries.is_dir():
            with os.scandir(libraries) as entries:
                for index, entry in enumerate(entries):
                    context.check()
                    if index >= 256 or len(caches) >= 8:
                        raise DiagnosticLimitError("library_inventory_limit")
                    if not entry.name.lower().endswith(".zip"):
                        continue
                    path = _child(libraries, entry.name)
                    item = context.file(path)
                    try:
                        data = context.read(path, limit=32 * 1024 * 1024)
                        with zipfile.ZipFile(io.BytesIO(data)) as archive_zip:
                            members = archive_zip.infolist()
                            if len(members) > 512 or sum(member.file_size for member in members) > 128 * 1024 * 1024:
                                raise DiagnosticLimitError("zip_expansion_limit")
                            for member in members:
                                with archive_zip.open(member) as stream:
                                    while True:
                                        context.check()
                                        chunk = stream.read(1024 * 1024)
                                        if not chunk:
                                            break
                                        context.check(len(chunk))
                            item.update(zip_status="valid", member_count=len(members))
                    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError) as error:
                        limited = isinstance(error, DiagnosticLimitError)
                        item.update(zip_status="not_checked" if limited else "invalid", reason=str(error))
                        context.partial |= limited
                        if not limited:
                            context.findings.append({"code": "unity_base_zip_invalid", "path": str(path)})
                    caches.append(item)
        result["unity_library_caches"] = caches
        interop = _child(game.parent, "BepInEx/interop")
        result["interop"] = {
            "directory_exists": interop.is_dir(),
            "core_module": context.file(_child(interop, "UnityEngine.CoreModule.dll")),
            "generation_receipt": context.file(_child(interop, "assembly-hash.txt")),
        }
        return result

    def _mods(self, context: _Collector, game: Path | None) -> dict[str, Any]:
        from .mod_manager import ModCatalog
        records = []
        community_bundled = []
        seen_paths: set[Path] = set()
        installed_plugins = []
        catalogs = (
            ("builtin", self.resource_dir / "assets/mod_catalog.json"),
            ("community", self.resource_dir / "assets/community_mod_catalog.json"),
            ("user", self.config_dir / "user_mods/catalog.json"),
        )
        catalog_files = []
        for origin, path in catalogs:
            if origin == "user" and not path.exists():
                continue
            catalog_files.append(context.file(path))
            catalog = ModCatalog.from_payload(context.json_file(path))
            if len(catalog.entries) > 256:
                raise DiagnosticLimitError("catalog_entry_limit")
            for descriptor in catalog.entries:
                context.check()
                operation = descriptor.operation
                if origin == "community":
                    community_bundled.append(operation.bundled)
                row: dict[str, Any] = {
                    "id": descriptor.mod_id, "name": descriptor.display.name,
                    "version": descriptor.display.version, "origin": origin,
                    "declared_bundled": operation.bundled, "hotkeys": operation.hotkeys,
                    "source_state": "user_supplied_required" if not operation.bundled else "present",
                    "source_files": [], "installed_files": [], "superseded_files": [],
                }
                from .mod_manager import ModManager
                specs = ModManager._file_specs(descriptor)
                if operation.bundled:
                    if origin == "user":
                        source = _child(self.config_dir / "user_mods/payloads", descriptor.mod_id)
                    elif operation.bundle_dir:
                        source = _child(self.resource_dir / "third_party", operation.bundle_dir)
                    else:
                        source = self.resource_dir / "third_party"
                    row["source_files"] = [context.file(_child(source, spec.path), vars(spec)) for spec in specs]
                    if any(item.get("matches") is False for item in row["source_files"]):
                        row["source_state"] = "missing_or_different"
                    elif any(item.get("matches") is None for item in row["source_files"]):
                        row["source_state"] = "not_checked"
                installed_root = (
                    _child(game.parent, "BepInEx/plugins/" + descriptor.mod_id) if game and operation.is_game_plugin
                    else _child(self.config_dir / "managed_mods", descriptor.mod_id) if not operation.is_game_plugin
                    else None
                )
                if installed_root:
                    for spec in specs:
                        target = _child(installed_root, spec.path)
                        item = context.file(target, metadata=target.suffix.lower() == ".dll")
                        item["expected"] = vars(spec)
                        if item["status"] == "present":
                            item["matches"] = item.get("sha256") == spec.sha256
                            seen_paths.add(target)
                            installed_plugins.append(item)
                            if not item["matches"]:
                                context.findings.append({"code": "installed_mod_differs", "mod_id": descriptor.mod_id, "path": str(target)})
                        row["installed_files"].append(item)
                    for spec in operation.superseded_files:
                        target = _child(installed_root, spec.path)
                        item = context.file(target)
                        if item.get("sha256") == spec.sha256:
                            row["superseded_files"].append(item)
                records.append(row)
        unknown = []
        if game:
            plugins = _child(game.parent, "BepInEx/plugins")
            pending = [(plugins, 0)] if plugins.is_dir() else []
            visited = 0
            while pending:
                folder, depth = pending.pop()
                with os.scandir(folder) as entries:
                    for entry in entries:
                        context.check()
                        visited += 1
                        if visited > 1024 or depth > 6:
                            raise DiagnosticLimitError("plugin_inventory_limit")
                        if entry.is_symlink() or getattr(Path(entry.path), "is_junction", lambda: False)():
                            continue
                        target = _child(folder, entry.name)
                        if entry.is_dir(follow_symlinks=False):
                            pending.append((target, depth + 1))
                        elif target.suffix.lower() == ".dll" and target not in seen_paths:
                            item = context.file(target, metadata=True)
                            unknown.append(item)
                            installed_plugins.append(item)
        guids: dict[str, list[str]] = {}
        for item in installed_plugins:
            plugin = item.get("plugin") or {}
            if plugin.get("guid"):
                guids.setdefault(plugin["guid"], []).append(item["path"])
        duplicates = {guid: paths for guid, paths in guids.items() if len(paths) > 1}
        for guid, paths in duplicates.items():
            context.findings.append({"code": "duplicate_plugin_guid", "guid": guid, "paths": paths})
        package_kind = "bundled" if community_bundled and all(community_bundled) else "public-core" if community_bundled and not any(community_bundled) else "mixed_or_unknown"
        return {"package_kind": package_kind, "catalogs": catalog_files, "mods": records, "unregistered_plugins": unknown, "duplicate_guids": duplicates}

    def _logs(self, context: _Collector, game: Path | None, files: dict[str, str]) -> dict[str, Any]:
        candidates = [
            (self.config_dir / "support/operations.jsonl", "toolbox-operations.jsonl"),
            (self.config_dir / "support/operations.previous.jsonl", "toolbox-operations-previous.jsonl"),
        ]
        if game:
            candidates.append((_child(game.parent, "BepInEx/LogOutput.log"), "bepinex.log"))
            app_info = _child(game.parent, "LostCastle2_Data/app.info")
            if app_info.is_file():
                names = context.read(app_info, limit=4096).decode("utf-8-sig").splitlines()
                if len(names) >= 2 and os.environ.get("LOCALAPPDATA"):
                    local_low = Path(os.environ["LOCALAPPDATA"]).parent / "LocalLow"
                    log_root = _child(local_low, names[0] + "/" + names[1])
                    candidates.extend(((log_root / "Player.log", "game-player.log"), (log_root / "Player-prev.log", "game-player-previous.log")))
        result = []
        markers = {
            "End of Central Directory": "zip_directory_invalid",
            "Failed to generate Il2Cpp interop": "interop_generation_failed",
            "Unable to execute IL2CPP chainloader": "plugins_not_loaded",
            "MissingMethodException": "plugin_api_missing",
            "FileNotFoundException": "file_or_assembly_not_found",
        }
        for path, name in candidates:
            context.check()
            row: dict[str, Any] = {"source": str(path), "archive_member": "logs/" + name}
            if not path.exists():
                row["status"] = "missing"
            else:
                try:
                    stat = path.stat()
                    text = context.read(path, limit=MAX_LOG_BYTES, tail=True).decode("utf-8-sig", errors="replace")
                    truncated = stat.st_size > MAX_LOG_BYTES
                    if truncated and "\n" in text:
                        text = text.split("\n", 1)[1]
                    row.update(status="included", modified_at=_utc(stat.st_mtime), original_bytes=stat.st_size, tail_truncated=truncated, process_binding="unverified")
                    row["observed_errors"] = [code for marker, code in markers.items() if marker in text]
                    files["logs/" + name] = text
                except (OSError, DiagnosticLimitError) as error:
                    row.update(status="not_checked", reason=str(error))
                    context.partial = True
            result.append(row)
        return {"files": result, "scope": "bounded_tail; timestamps retained; old logs are not proof of the current run"}

    def export(
        self, live_snapshot: Mapping[str, Any] | None = None,
        *, progress: Callable[[str], None] | None = None,
    ) -> SupportExport:
        context = _Collector(seconds=self.seconds, max_bytes=self.max_bytes)
        game = None
        game_error = None
        try:
            game = self._game(context)
        except Exception as error:
            game_error = type(error).__name__
            context.partial = True
        files: dict[str, str] = {}
        modules: dict[str, Any] = {}
        for name, label, seconds, collect in (
            ("application", "读取版本与设置", 2.0, lambda: self._application(context)),
            ("runtime", "检查游戏运行环境", 6.0, lambda: self._runtime(context, game)),
            ("mods", "检查 MOD 文件", 5.0, lambda: self._mods(context, game)),
            ("logs", "收集近期错误", 2.0, lambda: self._logs(context, game, files)),
        ):
            if progress:
                progress(label)
            context.phase_deadline = min(context.deadline, time.monotonic() + seconds)
            try:
                context.check()
                modules[name] = {"status": "collected", "data": collect()}
            except Exception as error:
                modules[name] = {"status": "not_collected", "reason": str(error), "error_type": type(error).__name__}
                context.partial = True
        live = dict(live_snapshot or {"state": "ui_not_running"})
        transport = live.get("transport", {})
        combat = live.get("combat", {})
        if isinstance(transport, Mapping) and transport.get("fault_code"):
            context.findings.append({"code": "combat_transport_fault", "detail": transport["fault_code"]})
        if isinstance(combat, Mapping) and combat.get("data_incomplete"):
            context.findings.append({"code": "combat_data_incomplete", "detail": combat.get("last_data_gap")})
        report = {
            "schema_version": SCHEMA_VERSION, "created_at": _utc(), "run_id": self.run_id,
            "toolbox_version": self.app_version, "game_resolution_error": game_error,
            "modules": modules, "live_snapshot": live,
            "findings": context.findings, "partial": context.partial,
            "collection": {"elapsed_seconds": round(time.monotonic() - context.started, 3), "bytes_read": context.read_bytes, "files_read": context.files_read, "max_seconds": self.seconds, "max_read_bytes": self.max_bytes},
            "scope": {"automatic_upload": False, "detailed_combat_events": "not_included", "historical_key_capture": False},
        }
        redactor = self.redactor(game)
        redactor.learn_players(report)
        files["report.json"] = _json(redactor.value(report))
        summary = [
            "失落城堡2工具箱 · 支持诊断", f"工具箱版本：{self.app_version}",
            "收集结果：" + ("部分信息未能读取，见 report.json。" if context.partial else "已完成本次收集。"),
            f"需关注的检查结果：{len(context.findings)} 项。", "",
            "本包包括版本、运行环境、MOD文件情况、近期日志与可用的界面/战斗快照。",
            "日志保留原时间，旧错误不代表当前仍在发生；未提前记录的操作和对局无法追溯。",
            "请将这个ZIP私发维护者，并说明遇到问题的时间、操作步骤和实际表现。", "",
        ]
        for name, module in modules.items():
            summary.append(f"{name}: {module['status']}")
        for finding in context.findings[:30]:
            summary.append(redactor.text(f"{finding['code']}: {finding.get('path', finding.get('guid', finding.get('detail', '')))}"))
        files["诊断说明.txt"] = "\n".join(summary) + "\n"
        encoded = {name: redactor.text(text).encode("utf-8") for name, text in files.items()}
        manifest = {"schema_version": SCHEMA_VERSION, "created_at": report["created_at"], "partial": context.partial, "files": [
            {"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest().upper()}
            for name, content in encoded.items()
        ]}
        encoded["manifest.json"] = _json(manifest).encode("utf-8")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive_zip:
            for name, data in encoded.items():
                archive_zip.writestr(name, data)
        output = (self.output_directory or default_export_directory()).resolve()
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"LC2诊断-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}.zip"
        if progress:
            progress("保存诊断包")
        with path.open("xb") as stream:
            stream.write(buffer.getvalue())
        self.record_event("support_export_complete", partial=context.partial, finding_count=len(context.findings))
        return SupportExport(path, context.partial, len(context.findings))
