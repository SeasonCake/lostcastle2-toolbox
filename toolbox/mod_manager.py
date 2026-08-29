from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from typing import Any, Callable

from .windows_input import WindowsInputError, parse_hotkey_chord


SHA256_PATTERN = re.compile(r"^[0-9A-F]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VISIBLE_COPY_FORBIDDEN_TERMS = (
    "frida",
    "注入",
    "未签名",
    "sha-256",
    "sha256",
    "授权来源",
    "再分发",
    "无遥测",
    "无账号",
    "反调试",
    "attestation",
)


class ModManagerError(ValueError):
    """Base class for catalog and managed-copy failures."""


class ModSourceRequired(ModManagerError):
    """Raised when a catalog entry has no redistributable bundled source."""


class ModIntegrityError(ModManagerError):
    """Raised when a selected or installed file differs from the catalog."""


class ModGamePathRequired(ModManagerError):
    """Raised when an in-game plugin has no usable Lost Castle 2 location."""


class ModConflictError(ModManagerError):
    """Raised when another installed MOD provides the same plugin payload."""

    def __init__(self, conflicts: tuple[str, ...]) -> None:
        super().__init__("Conflicting MODs are already installed.")
        self.conflicts = conflicts


@dataclass(frozen=True)
class ModDisplay:
    name: str
    version: str
    author: str
    summary: str
    usage_hint: str = ""


@dataclass(frozen=True)
class ModArchiveSource:
    expected_filename: str
    member: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ModFileSpec:
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ModOperation:
    kind: str
    expected_filename: str
    bundled: bool
    archive_source: ModArchiveSource | None = None
    bundle_dir: str | None = None
    files: tuple[ModFileSpec, ...] = ()
    provides: tuple[str, ...] = ()
    hotkeys: tuple[str, ...] = ()
    panel_hotkey: str | None = None

    @property
    def launchable(self) -> bool:
        return self.kind == "external_trainer"

    @property
    def requires_game_launch(self) -> bool:
        return self.kind == "bepinex_plugin"

    @property
    def is_game_plugin(self) -> bool:
        return self.kind == "bepinex_plugin"

    @property
    def has_game_panel(self) -> bool:
        return self.is_game_plugin and self.panel_hotkey is not None


@dataclass(frozen=True)
class ModIntegrityPolicy:
    version_note: str
    author_source: str
    author_channel: str
    sha256: str
    size_bytes: int
    signature_status: str
    risk_level: str
    capabilities: tuple[str, ...]
    redistribution_status: str


@dataclass(frozen=True)
class ModDescriptor:
    mod_id: str
    display: ModDisplay
    operation: ModOperation
    integrity_policy: ModIntegrityPolicy


@dataclass(frozen=True)
class ModStatus:
    state: str
    source_bundled: bool
    integrity_ok: bool

    @property
    def installed(self) -> bool:
        return self.state == "installed"


class ModCatalog:
    def __init__(self, entries: tuple[ModDescriptor, ...]) -> None:
        if not entries:
            raise ModManagerError("MOD catalog cannot be empty.")
        by_id = {entry.mod_id: entry for entry in entries}
        if len(by_id) != len(entries):
            raise ModManagerError("MOD catalog ids must be unique.")
        self.entries = entries
        self._by_id = by_id

    @classmethod
    def from_file(cls, path: Path) -> ModCatalog:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_payload(payload)

    @classmethod
    def from_payload(cls, payload: Any) -> ModCatalog:
        if not isinstance(payload, dict) or payload.get("schema_version") != 2:
            raise ModManagerError("Unsupported MOD catalog version.")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ModManagerError("MOD catalog entries must be a list.")
        return cls(tuple(cls._parse_entry(raw) for raw in raw_entries))

    @staticmethod
    def _parse_entry(raw: Any) -> ModDescriptor:
        if not isinstance(raw, dict):
            raise ModManagerError("Invalid MOD catalog entry.")
        display_raw = raw.get("display")
        operation_raw = raw.get("operation")
        policy_raw = raw.get("integrity_policy")
        if not isinstance(display_raw, dict):
            raise ModManagerError("MOD catalog display must be an object.")
        if not isinstance(operation_raw, dict):
            raise ModManagerError("MOD catalog operation must be an object.")
        if not isinstance(policy_raw, dict):
            raise ModManagerError("MOD catalog integrity_policy must be an object.")

        mod_id = ModCatalog._required_string(raw, "id", "entry")
        usage_hint = display_raw.get("usage_hint", "")
        if not isinstance(usage_hint, str):
            raise ModManagerError("MOD catalog display usage_hint must be a string.")
        display = ModDisplay(
            name=ModCatalog._required_string(display_raw, "name", "display"),
            version=ModCatalog._required_string(display_raw, "version", "display"),
            author=ModCatalog._required_string(display_raw, "author", "display"),
            summary=ModCatalog._required_string(display_raw, "summary", "display"),
            usage_hint=usage_hint.strip(),
        )
        ModCatalog._validate_visible_copy(display)

        expected_filename = ModCatalog._required_string(
            operation_raw, "expected_filename", "operation"
        )
        bundled = operation_raw.get("bundled")
        operation_kind = ModCatalog._required_string(operation_raw, "kind", "operation")
        if operation_kind not in {"external_trainer", "bepinex_plugin"}:
            raise ModManagerError("Unsupported MOD operation kind.")
        archive_source = ModCatalog._parse_archive_source(
            operation_raw.get("archive_source")
        )
        bundle_dir = ModCatalog._optional_relative_path(
            operation_raw.get("bundle_dir"), "operation.bundle_dir"
        )
        files = ModCatalog._parse_file_specs(operation_raw.get("files"))
        provides = ModCatalog._parse_string_list(
            operation_raw.get("provides", []), "operation.provides"
        )
        hotkeys = ModCatalog._parse_string_list(
            operation_raw.get("hotkeys", []), "operation.hotkeys"
        )
        panel_hotkey = ModCatalog._parse_panel_hotkey(
            operation_raw.get("panel_hotkey"), hotkeys
        )
        operation = ModOperation(
            kind=operation_kind,
            expected_filename=expected_filename,
            bundled=bundled if type(bundled) is bool else False,
            archive_source=archive_source,
            bundle_dir=bundle_dir,
            files=files,
            provides=provides,
            hotkeys=hotkeys,
            panel_hotkey=panel_hotkey,
        )

        size_bytes = policy_raw.get("size_bytes")
        capabilities = policy_raw.get("capabilities")
        sha256 = ModCatalog._required_string(
            policy_raw, "sha256", "integrity_policy"
        ).upper()
        if not ID_PATTERN.fullmatch(mod_id):
            raise ModManagerError("Invalid MOD catalog id.")
        if Path(expected_filename).name != expected_filename:
            raise ModManagerError("MOD filename must not contain a path.")
        if not SHA256_PATTERN.fullmatch(sha256):
            raise ModManagerError("Invalid MOD SHA-256.")
        if type(size_bytes) is not int or size_bytes <= 0:
            raise ModManagerError("Invalid MOD file size.")
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(isinstance(item, str) and item.strip() for item in capabilities)
        ):
            raise ModManagerError("MOD capabilities must be a non-empty string list.")
        if type(bundled) is not bool:
            raise ModManagerError("MOD bundled flag must be boolean.")
        if files:
            if operation_kind != "bepinex_plugin":
                raise ModManagerError("Multi-file MODs must be BepInEx plugins.")
            matching_primary = [
                spec
                for spec in files
                if PurePosixPath(spec.path).name.casefold()
                == expected_filename.casefold()
            ]
            if len(matching_primary) != 1:
                raise ModManagerError(
                    "Multi-file MOD expected_filename must identify one payload file."
                )
            primary = matching_primary[0]
            if primary.sha256 != sha256 or primary.size_bytes != size_bytes:
                raise ModManagerError(
                    "Multi-file MOD primary integrity must match integrity_policy."
                )
            if bundled and bundle_dir is None:
                raise ModManagerError("Bundled multi-file MODs require bundle_dir.")
        integrity_policy = ModIntegrityPolicy(
            version_note=ModCatalog._required_string(
                policy_raw, "version_note", "integrity_policy"
            ),
            author_source=ModCatalog._required_string(
                policy_raw, "author_source", "integrity_policy"
            ),
            author_channel=ModCatalog._required_string(
                policy_raw, "author_channel", "integrity_policy"
            ),
            sha256=sha256,
            size_bytes=size_bytes,
            signature_status=ModCatalog._required_string(
                policy_raw, "signature_status", "integrity_policy"
            ),
            risk_level=ModCatalog._required_string(
                policy_raw, "risk_level", "integrity_policy"
            ),
            capabilities=tuple(item.strip() for item in capabilities),
            redistribution_status=ModCatalog._required_string(
                policy_raw, "redistribution_status", "integrity_policy"
            ),
        )
        return ModDescriptor(
            mod_id=mod_id,
            display=display,
            operation=operation,
            integrity_policy=integrity_policy,
        )

    @staticmethod
    def _parse_archive_source(raw: Any) -> ModArchiveSource | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ModManagerError("MOD archive_source must be an object.")
        expected_filename = ModCatalog._required_string(
            raw, "expected_filename", "archive_source"
        )
        member = ModCatalog._required_string(raw, "member", "archive_source")
        sha256 = ModCatalog._required_string(
            raw, "sha256", "archive_source"
        ).upper()
        size_bytes = raw.get("size_bytes")
        if Path(expected_filename).name != expected_filename:
            raise ModManagerError("MOD archive filename must not contain a path.")
        if Path(member).name != member:
            raise ModManagerError("MOD archive member must be a single filename.")
        if not SHA256_PATTERN.fullmatch(sha256):
            raise ModManagerError("Invalid MOD archive SHA-256.")
        if type(size_bytes) is not int or size_bytes <= 0:
            raise ModManagerError("Invalid MOD archive size.")
        return ModArchiveSource(
            expected_filename=expected_filename,
            member=member,
            sha256=sha256,
            size_bytes=size_bytes,
        )

    @staticmethod
    def _parse_file_specs(raw: Any) -> tuple[ModFileSpec, ...]:
        if raw is None:
            return ()
        if not isinstance(raw, list) or not raw:
            raise ModManagerError("MOD operation.files must be a non-empty array.")
        specs: list[ModFileSpec] = []
        paths: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                raise ModManagerError("MOD operation.files entries must be objects.")
            path = ModCatalog._required_string(item, "path", "operation.files")
            path = ModCatalog._validate_relative_path(path, "operation.files.path")
            sha256 = ModCatalog._required_string(
                item, "sha256", "operation.files"
            ).upper()
            size_bytes = item.get("size_bytes")
            if not SHA256_PATTERN.fullmatch(sha256):
                raise ModManagerError("Invalid MOD payload SHA-256.")
            if type(size_bytes) is not int or size_bytes <= 0:
                raise ModManagerError("Invalid MOD payload size.")
            if path.casefold() in paths:
                raise ModManagerError("Duplicate MOD payload path.")
            paths.add(path.casefold())
            specs.append(ModFileSpec(path, sha256, size_bytes))
        return tuple(specs)

    @staticmethod
    def _parse_string_list(raw: Any, section: str) -> tuple[str, ...]:
        if not isinstance(raw, list) or not all(
            isinstance(item, str) and item.strip() for item in raw
        ):
            raise ModManagerError(f"MOD catalog {section} must be a string array.")
        return tuple(dict.fromkeys(item.strip() for item in raw))

    @staticmethod
    def _parse_panel_hotkey(
        raw: Any, hotkeys: tuple[str, ...]
    ) -> str | None:
        if raw is None:
            return None
        if not isinstance(raw, str) or not raw.strip():
            raise ModManagerError("MOD catalog operation.panel_hotkey must be a hotkey string.")
        try:
            normalized = "+".join(parse_hotkey_chord(raw))
        except WindowsInputError as exception:
            raise ModManagerError("Unsupported MOD panel hotkey.") from exception
        normalized_hotkeys: set[str] = set()
        for item in hotkeys:
            try:
                normalized_hotkeys.add("+".join(parse_hotkey_chord(item)))
            except WindowsInputError:
                continue
        if normalized not in normalized_hotkeys:
            raise ModManagerError("MOD panel_hotkey must also be listed in operation.hotkeys.")
        return normalized

    @staticmethod
    def _optional_relative_path(raw: Any, section: str) -> str | None:
        if raw is None:
            return None
        if not isinstance(raw, str) or not raw.strip():
            raise ModManagerError(f"MOD catalog {section} must be a relative path.")
        return ModCatalog._validate_relative_path(raw.strip(), section)

    @staticmethod
    def _validate_relative_path(value: str, section: str) -> str:
        normalized = value.replace("\\", "/").strip("/")
        path = PurePosixPath(normalized)
        if (
            not normalized
            or path.is_absolute()
            or any(part in {"", ".", ".."} or ":" in part for part in path.parts)
        ):
            raise ModManagerError(f"MOD catalog {section} contains an unsafe path.")
        return path.as_posix()

    @staticmethod
    def _required_string(raw: dict[str, Any], key: str, section: str) -> str:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ModManagerError(
                f"MOD catalog {section} field {key!r} must be non-empty."
            )
        return value.strip()

    @staticmethod
    def _validate_visible_copy(display: ModDisplay) -> None:
        visible = "\n".join(
            (
                display.name,
                display.version,
                display.author,
                display.summary,
                display.usage_hint,
            )
        )
        folded = visible.casefold()
        matches = [term for term in VISIBLE_COPY_FORBIDDEN_TERMS if term in folded]
        if matches:
            raise ModManagerError(
                "MOD display contains internal implementation or policy terms: "
                + ", ".join(matches)
            )

    def get(self, mod_id: str) -> ModDescriptor:
        try:
            return self._by_id[mod_id]
        except KeyError as exception:
            raise ModManagerError(f"Unknown MOD id: {mod_id!r}") from exception


class ModManager:
    """Manage exact catalog-owned copies and reversible BepInEx plugin installs."""

    def __init__(
        self,
        catalog: ModCatalog,
        managed_root: Path,
        bundled_root: Path,
        game_exe_provider: Callable[[], Path | None] | None = None,
        source_overrides: dict[str, Path] | None = None,
    ) -> None:
        self.catalog = catalog
        self.managed_root = managed_root.resolve()
        self.bundled_root = bundled_root.resolve()
        self.game_exe_provider = game_exe_provider
        self._source_overrides = {
            mod_id: path.resolve()
            for mod_id, path in (source_overrides or {}).items()
        }
        self._hash_cache: dict[Path, tuple[int, int, str]] = {}

    def descriptor(self, mod_id: str) -> ModDescriptor:
        return self.catalog.get(mod_id)

    def add_descriptor(self, descriptor: ModDescriptor, source: Path) -> None:
        if any(entry.mod_id == descriptor.mod_id for entry in self.catalog.entries):
            raise ModManagerError("MOD id already exists.")
        source = source.resolve()
        if descriptor.operation.files and not source.is_dir():
            raise ModManagerError("Registered MOD payload directory is missing.")
        if not descriptor.operation.files and not source.is_file():
            raise ModManagerError("Registered MOD payload file is missing.")
        self.catalog = ModCatalog(self.catalog.entries + (descriptor,))
        self._source_overrides[descriptor.mod_id] = source

    def bundled_source(self, mod_id: str) -> Path | None:
        descriptor = self.descriptor(mod_id)
        if not descriptor.operation.bundled:
            return None
        override = self._source_overrides.get(mod_id)
        if override is not None:
            expected_type = override.is_dir() if descriptor.operation.files else override.is_file()
            return override if expected_type else None
        if descriptor.operation.files:
            if descriptor.operation.bundle_dir is None:
                return None
            candidate = self._join_relative(
                self.bundled_root, descriptor.operation.bundle_dir
            ).resolve()
        else:
            candidate = (
                self.bundled_root / descriptor.operation.expected_filename
            ).resolve()
        self._ensure_contained(candidate, self.bundled_root)
        expected_type = candidate.is_dir() if descriptor.operation.files else candidate.is_file()
        return candidate if expected_type else None

    def installed_path(self, mod_id: str) -> Path:
        descriptor = self.descriptor(mod_id)
        directory = self._installed_directory(descriptor)
        primary_spec = self._primary_spec(descriptor)
        target = self._join_relative(directory, primary_spec.path).resolve()
        self._ensure_contained(target, directory)
        return target

    def status(self, mod_id: str) -> ModStatus:
        descriptor = self.descriptor(mod_id)
        source_bundled = self.bundled_source(mod_id) is not None
        try:
            directory = self._installed_directory(descriptor)
        except ModGamePathRequired:
            return ModStatus("game_not_configured", source_bundled, False)
        specs = self._file_specs(descriptor)
        targets = [self._join_relative(directory, spec.path) for spec in specs]
        existing = [target.exists() for target in targets]
        if not any(existing):
            return ModStatus("not_installed", source_bundled, False)
        integrity_ok = all(
            target.is_file()
            and target.stat().st_size == spec.size_bytes
            and self._sha256(target) == spec.sha256
            for target, spec in zip(targets, specs, strict=True)
        )
        return ModStatus(
            "installed" if integrity_ok else "integrity_error",
            source_bundled,
            integrity_ok,
        )

    def installed_mtime_ns(self, mod_id: str) -> int | None:
        """Return the newest managed payload write time for load-order checks."""

        descriptor = self.descriptor(mod_id)
        try:
            directory = self._installed_directory(descriptor)
        except ModGamePathRequired:
            return None
        targets = [
            self._join_relative(directory, spec.path)
            for spec in self._file_specs(descriptor)
        ]
        if not targets or not all(target.is_file() for target in targets):
            return None
        return max(target.stat().st_mtime_ns for target in targets)

    def install(self, mod_id: str, source_path: Path | None = None) -> Path:
        descriptor = self.descriptor(mod_id)
        conflicts = self.installed_conflicts(mod_id)
        if conflicts:
            raise ModConflictError(conflicts)
        source = source_path.resolve() if source_path is not None else self.bundled_source(mod_id)
        if source is None:
            raise ModSourceRequired("A matching user-supplied source file is required.")
        if descriptor.operation.files:
            return self._install_package(descriptor, source)
        target = self.installed_path(mod_id)
        if source == target:
            self._validate_file(source, descriptor)
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".installing")
        try:
            if self._is_archive_source(source, descriptor):
                self._validate_archive(source, descriptor.operation.archive_source)
                content = self._extract_archive_member(
                    source, descriptor.operation.archive_source.member
                )
                temporary.write_bytes(content)
            else:
                self._validate_file(source, descriptor)
                shutil.copyfile(source, temporary)
            self._hash_cache.pop(temporary, None)
            self._validate_file(temporary, descriptor)
            os.replace(temporary, target)
            self._hash_cache.pop(target, None)
            self._validate_file(target, descriptor)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target

    def installed_conflicts(self, mod_id: str) -> tuple[str, ...]:
        descriptor = self.descriptor(mod_id)
        provided = {item.casefold() for item in descriptor.operation.provides}
        if not provided:
            return ()
        conflicts: list[str] = []
        for other in self.catalog.entries:
            if other.mod_id == mod_id:
                continue
            other_provided = {item.casefold() for item in other.operation.provides}
            if not provided.intersection(other_provided):
                continue
            if self.status(other.mod_id).installed:
                conflicts.append(other.display.name)
        return tuple(conflicts)

    def uninstall(self, mod_id: str) -> bool:
        descriptor = self.descriptor(mod_id)
        directory = self._installed_directory(descriptor)
        specs = self._file_specs(descriptor)
        targets = [self._join_relative(directory, spec.path) for spec in specs]
        if not any(target.exists() for target in targets):
            return False
        removed = False
        for target in targets:
            if not target.exists():
                continue
            if not target.is_file():
                raise ModManagerError("Managed MOD target is not a removable file.")
            target.unlink()
            removed = True
            self._hash_cache.pop(target, None)
        parents = sorted(
            {target.parent for target in targets},
            key=lambda path: len(path.parts),
            reverse=True,
        )
        for parent in parents:
            current = parent
            while current != directory.parent:
                try:
                    current.rmdir()
                except OSError:
                    break
                if current == directory:
                    break
                current = current.parent
        return removed

    def launch(self, mod_id: str) -> subprocess.Popen[bytes]:
        descriptor = self.descriptor(mod_id)
        if not descriptor.operation.launchable:
            raise ModManagerError("This MOD is loaded by the game and cannot be launched.")
        status = self.status(mod_id)
        if not status.installed:
            raise ModIntegrityError("Managed MOD copy is missing or does not match the catalog.")
        target = self.installed_path(mod_id)
        return subprocess.Popen([str(target)], cwd=str(target.parent), close_fds=True)

    def _install_package(self, descriptor: ModDescriptor, source: Path) -> Path:
        if not source.is_dir():
            raise ModIntegrityError("Bundled MOD payload directory is missing.")
        directory = self._installed_directory(descriptor)
        specs = self._file_specs(descriptor)
        for spec in specs:
            source_file = self._join_relative(source, spec.path).resolve()
            self._ensure_contained(source_file, source)
            self._validate_spec_file(source_file, spec)
        for spec in specs:
            source_file = self._join_relative(source, spec.path).resolve()
            target = self._join_relative(directory, spec.path).resolve()
            self._ensure_contained(target, directory)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".installing")
            try:
                shutil.copyfile(source_file, temporary)
                self._hash_cache.pop(temporary, None)
                self._validate_spec_file(temporary, spec)
                os.replace(temporary, target)
                self._hash_cache.pop(target, None)
                self._validate_spec_file(target, spec)
            finally:
                if temporary.exists():
                    temporary.unlink()
        return self.installed_path(descriptor.mod_id)

    def _installed_directory(self, descriptor: ModDescriptor) -> Path:
        if descriptor.operation.is_game_plugin:
            game_exe = self.game_exe_provider() if self.game_exe_provider else None
            if game_exe is None:
                raise ModGamePathRequired("Lost Castle 2 executable is not configured.")
            game_exe = game_exe.resolve()
            if not game_exe.is_file():
                raise ModGamePathRequired("Lost Castle 2 executable does not exist.")
            plugins_root = (game_exe.parent / "BepInEx" / "plugins").resolve()
            bepinex_root = (game_exe.parent / "BepInEx").resolve()
            if not bepinex_root.is_dir():
                raise ModGamePathRequired("BepInEx is not installed for the configured game.")
            self._ensure_contained(plugins_root, game_exe.parent.resolve())
            directory = (plugins_root / descriptor.mod_id).resolve()
            self._ensure_contained(directory, plugins_root)
            return directory
        directory = (self.managed_root / descriptor.mod_id).resolve()
        self._ensure_contained(directory, self.managed_root)
        return directory

    @staticmethod
    def _file_specs(descriptor: ModDescriptor) -> tuple[ModFileSpec, ...]:
        if descriptor.operation.files:
            return descriptor.operation.files
        policy = descriptor.integrity_policy
        return (
            ModFileSpec(
                descriptor.operation.expected_filename,
                policy.sha256,
                policy.size_bytes,
            ),
        )

    @staticmethod
    def _primary_spec(descriptor: ModDescriptor) -> ModFileSpec:
        matches = [
            spec
            for spec in ModManager._file_specs(descriptor)
            if PurePosixPath(spec.path).name.casefold()
            == descriptor.operation.expected_filename.casefold()
        ]
        if len(matches) != 1:
            raise ModManagerError("MOD primary payload is ambiguous.")
        return matches[0]

    @staticmethod
    def _join_relative(root: Path, relative: str) -> Path:
        return root.joinpath(*PurePosixPath(relative).parts)

    def _validate_spec_file(self, path: Path, spec: ModFileSpec) -> None:
        if not path.is_file():
            raise ModIntegrityError("Bundled MOD payload file is missing.")
        if path.stat().st_size != spec.size_bytes:
            raise ModIntegrityError("Bundled MOD payload size mismatch.")
        if self._sha256(path, use_cache=False) != spec.sha256:
            raise ModIntegrityError("Bundled MOD payload SHA-256 mismatch.")

    @staticmethod
    def _is_archive_source(path: Path, descriptor: ModDescriptor) -> bool:
        archive = descriptor.operation.archive_source
        return archive is not None and path.suffix.casefold() in {".7z", ".zip", ".rar"}

    def _validate_archive(
        self, path: Path, archive: ModArchiveSource | None
    ) -> None:
        if archive is None or not path.is_file():
            raise ModIntegrityError("Selected MOD archive is not a file.")
        if path.stat().st_size != archive.size_bytes:
            raise ModIntegrityError("Selected MOD archive has an unexpected size.")
        if self._sha256(path, use_cache=False) != archive.sha256:
            raise ModIntegrityError("Selected MOD archive failed SHA-256 verification.")

    @staticmethod
    def _extract_archive_member(path: Path, member: str) -> bytes:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                ["tar", "-xOf", str(path), member],
                check=True,
                capture_output=True,
                timeout=15,
                creationflags=creationflags,
            )
        except (OSError, subprocess.SubprocessError) as exception:
            raise ModIntegrityError("Unable to read the selected MOD archive.") from exception
        if not result.stdout:
            raise ModIntegrityError("The selected MOD archive did not contain the expected file.")
        return result.stdout

    def _validate_file(self, path: Path, descriptor: ModDescriptor) -> None:
        policy = descriptor.integrity_policy
        if not path.is_file():
            raise ModIntegrityError("Selected MOD source is not a file.")
        if path.stat().st_size != policy.size_bytes:
            raise ModIntegrityError("Selected MOD source has an unexpected size.")
        if self._sha256(path, use_cache=False) != policy.sha256:
            raise ModIntegrityError("Selected MOD source failed SHA-256 verification.")

    def _sha256(self, path: Path, *, use_cache: bool = True) -> str:
        stat = path.stat()
        cached = self._hash_cache.get(path) if use_cache else None
        identity = (stat.st_mtime_ns, stat.st_size)
        if cached is not None and cached[:2] == identity:
            return cached[2]
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        value = digest.hexdigest().upper()
        if use_cache:
            self._hash_cache[path] = (identity[0], identity[1], value)
        return value

    @staticmethod
    def _ensure_contained(path: Path, root: Path) -> None:
        try:
            path.relative_to(root)
        except ValueError as exception:
            raise ModManagerError("Managed MOD path escaped its configured root.") from exception
