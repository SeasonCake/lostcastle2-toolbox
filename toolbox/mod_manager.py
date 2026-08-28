from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable


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


@dataclass(frozen=True)
class ModDisplay:
    name: str
    version: str
    author: str
    summary: str


@dataclass(frozen=True)
class ModArchiveSource:
    expected_filename: str
    member: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ModOperation:
    kind: str
    expected_filename: str
    bundled: bool
    archive_source: ModArchiveSource | None = None

    @property
    def launchable(self) -> bool:
        return self.kind == "external_trainer"


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
        display = ModDisplay(
            name=ModCatalog._required_string(display_raw, "name", "display"),
            version=ModCatalog._required_string(display_raw, "version", "display"),
            author=ModCatalog._required_string(display_raw, "author", "display"),
            summary=ModCatalog._required_string(display_raw, "summary", "display"),
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
        operation = ModOperation(
            kind=operation_kind,
            expected_filename=expected_filename,
            bundled=bundled if type(bundled) is bool else False,
            archive_source=archive_source,
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
    def _required_string(raw: dict[str, Any], key: str, section: str) -> str:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ModManagerError(
                f"MOD catalog {section} field {key!r} must be non-empty."
            )
        return value.strip()

    @staticmethod
    def _validate_visible_copy(display: ModDisplay) -> None:
        visible = "\n".join((display.name, display.version, display.author, display.summary))
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
    ) -> None:
        self.catalog = catalog
        self.managed_root = managed_root.resolve()
        self.bundled_root = bundled_root.resolve()
        self.game_exe_provider = game_exe_provider
        self._hash_cache: dict[Path, tuple[int, int, str]] = {}

    def descriptor(self, mod_id: str) -> ModDescriptor:
        return self.catalog.get(mod_id)

    def bundled_source(self, mod_id: str) -> Path | None:
        descriptor = self.descriptor(mod_id)
        if not descriptor.operation.bundled:
            return None
        candidate = (
            self.bundled_root / descriptor.operation.expected_filename
        ).resolve()
        self._ensure_contained(candidate, self.bundled_root)
        return candidate if candidate.is_file() else None

    def installed_path(self, mod_id: str) -> Path:
        descriptor = self.descriptor(mod_id)
        if descriptor.operation.kind == "bepinex_plugin":
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
        else:
            directory = (self.managed_root / descriptor.mod_id).resolve()
            self._ensure_contained(directory, self.managed_root)
        target = (directory / descriptor.operation.expected_filename).resolve()
        self._ensure_contained(target, directory)
        return target

    def status(self, mod_id: str) -> ModStatus:
        descriptor = self.descriptor(mod_id)
        source_bundled = self.bundled_source(mod_id) is not None
        try:
            target = self.installed_path(mod_id)
        except ModGamePathRequired:
            return ModStatus("game_not_configured", source_bundled, False)
        if not target.exists():
            return ModStatus("not_installed", source_bundled, False)
        policy = descriptor.integrity_policy
        if not target.is_file() or target.stat().st_size != policy.size_bytes:
            return ModStatus("integrity_error", source_bundled, False)
        integrity_ok = self._sha256(target) == policy.sha256
        return ModStatus(
            "installed" if integrity_ok else "integrity_error",
            source_bundled,
            integrity_ok,
        )

    def install(self, mod_id: str, source_path: Path | None = None) -> Path:
        descriptor = self.descriptor(mod_id)
        source = source_path.resolve() if source_path is not None else self.bundled_source(mod_id)
        if source is None:
            raise ModSourceRequired("A matching user-supplied source file is required.")
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

    def uninstall(self, mod_id: str) -> bool:
        self.descriptor(mod_id)
        target = self.installed_path(mod_id)
        if not target.exists():
            return False
        if not target.is_file():
            raise ModManagerError("Managed MOD target is not a removable file.")
        target.unlink()
        self._hash_cache.pop(target, None)
        try:
            target.parent.rmdir()
        except OSError:
            pass
        return True

    def launch(self, mod_id: str) -> subprocess.Popen[bytes]:
        descriptor = self.descriptor(mod_id)
        if not descriptor.operation.launchable:
            raise ModManagerError("This MOD is loaded by the game and cannot be launched.")
        status = self.status(mod_id)
        if not status.installed:
            raise ModIntegrityError("Managed MOD copy is missing or does not match the catalog.")
        target = self.installed_path(mod_id)
        return subprocess.Popen([str(target)], cwd=str(target.parent), close_fds=True)

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
