from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


SHA256_PATTERN = re.compile(r"^[0-9A-F]{64}$")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ModManagerError(ValueError):
    """Base class for catalog and managed-copy failures."""


class ModSourceRequired(ModManagerError):
    """Raised when a catalog entry has no redistributable bundled source."""


class ModIntegrityError(ModManagerError):
    """Raised when a selected or installed file differs from the catalog."""


@dataclass(frozen=True)
class ModDescriptor:
    mod_id: str
    display_name: str
    version: str
    version_note: str
    author: str
    author_source: str
    author_channel: str
    kind: str
    expected_filename: str
    sha256: str
    size_bytes: int
    signature_status: str
    risk_level: str
    capabilities: tuple[str, ...]
    redistribution_status: str
    bundled: bool
    description: str


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
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ModManagerError("Unsupported MOD catalog version.")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ModManagerError("MOD catalog entries must be a list.")
        return cls(tuple(cls._parse_entry(raw) for raw in raw_entries))

    @staticmethod
    def _parse_entry(raw: Any) -> ModDescriptor:
        if not isinstance(raw, dict):
            raise ModManagerError("Invalid MOD catalog entry.")
        required_strings = (
            "id",
            "display_name",
            "version",
            "version_note",
            "author_source",
            "author_channel",
            "kind",
            "expected_filename",
            "sha256",
            "signature_status",
            "risk_level",
            "redistribution_status",
            "description",
        )
        values: dict[str, str] = {}
        for key in required_strings:
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ModManagerError(f"MOD catalog field {key!r} must be non-empty.")
            values[key] = value.strip()
        author = raw.get("author", "未知")
        if not isinstance(author, str) or not author.strip():
            author = "未知"
        size_bytes = raw.get("size_bytes")
        capabilities = raw.get("capabilities")
        bundled = raw.get("bundled")
        if not ID_PATTERN.fullmatch(values["id"]):
            raise ModManagerError("Invalid MOD catalog id.")
        if Path(values["expected_filename"]).name != values["expected_filename"]:
            raise ModManagerError("MOD filename must not contain a path.")
        sha256 = values["sha256"].upper()
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
        return ModDescriptor(
            mod_id=values["id"],
            display_name=values["display_name"],
            version=values["version"],
            version_note=values["version_note"],
            author=author.strip(),
            author_source=values["author_source"],
            author_channel=values["author_channel"],
            kind=values["kind"],
            expected_filename=values["expected_filename"],
            sha256=sha256,
            size_bytes=size_bytes,
            signature_status=values["signature_status"],
            risk_level=values["risk_level"],
            capabilities=tuple(item.strip() for item in capabilities),
            redistribution_status=values["redistribution_status"],
            bundled=bundled,
            description=values["description"],
        )

    def get(self, mod_id: str) -> ModDescriptor:
        try:
            return self._by_id[mod_id]
        except KeyError as exception:
            raise ModManagerError(f"Unknown MOD id: {mod_id!r}") from exception


class ModManager:
    """Manage exact, catalog-owned copies without touching user originals or game files."""

    def __init__(
        self,
        catalog: ModCatalog,
        managed_root: Path,
        bundled_root: Path,
    ) -> None:
        self.catalog = catalog
        self.managed_root = managed_root.resolve()
        self.bundled_root = bundled_root.resolve()
        self._hash_cache: dict[Path, tuple[int, int, str]] = {}

    def descriptor(self, mod_id: str) -> ModDescriptor:
        return self.catalog.get(mod_id)

    def bundled_source(self, mod_id: str) -> Path | None:
        descriptor = self.descriptor(mod_id)
        if not descriptor.bundled:
            return None
        candidate = (self.bundled_root / descriptor.expected_filename).resolve()
        self._ensure_contained(candidate, self.bundled_root)
        return candidate if candidate.is_file() else None

    def installed_path(self, mod_id: str) -> Path:
        descriptor = self.descriptor(mod_id)
        directory = (self.managed_root / descriptor.mod_id).resolve()
        self._ensure_contained(directory, self.managed_root)
        target = (directory / descriptor.expected_filename).resolve()
        self._ensure_contained(target, directory)
        return target

    def status(self, mod_id: str) -> ModStatus:
        descriptor = self.descriptor(mod_id)
        target = self.installed_path(mod_id)
        source_bundled = self.bundled_source(mod_id) is not None
        if not target.exists():
            return ModStatus("not_installed", source_bundled, False)
        if not target.is_file() or target.stat().st_size != descriptor.size_bytes:
            return ModStatus("integrity_error", source_bundled, False)
        integrity_ok = self._sha256(target) == descriptor.sha256
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
        self._validate_file(source, descriptor)
        target = self.installed_path(mod_id)
        if source == target:
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".installing")
        try:
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
        status = self.status(mod_id)
        if not status.installed:
            raise ModIntegrityError("Managed MOD copy is missing or does not match the catalog.")
        target = self.installed_path(mod_id)
        return subprocess.Popen([str(target)], cwd=str(target.parent), close_fds=True)

    def _validate_file(self, path: Path, descriptor: ModDescriptor) -> None:
        if not path.is_file():
            raise ModIntegrityError("Selected MOD source is not a file.")
        if path.stat().st_size != descriptor.size_bytes:
            raise ModIntegrityError("Selected MOD source has an unexpected size.")
        if self._sha256(path) != descriptor.sha256:
            raise ModIntegrityError("Selected MOD source failed SHA-256 verification.")

    def _sha256(self, path: Path) -> str:
        stat = path.stat()
        cached = self._hash_cache.get(path)
        identity = (stat.st_mtime_ns, stat.st_size)
        if cached is not None and cached[:2] == identity:
            return cached[2]
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        value = digest.hexdigest().upper()
        self._hash_cache[path] = (identity[0], identity[1], value)
        return value

    @staticmethod
    def _ensure_contained(path: Path, root: Path) -> None:
        try:
            path.relative_to(root)
        except ValueError as exception:
            raise ModManagerError("Managed MOD path escaped its configured root.") from exception
