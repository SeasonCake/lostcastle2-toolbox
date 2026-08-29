from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from typing import Mapping
import uuid

from .mod_inspector import ModDraft, ModPackageInspector, normalize_member_path, slugify
from .mod_manager import ID_PATTERN, ModCatalog, ModDescriptor, ModManagerError


class UserModRegistryError(ModManagerError):
    pass


@dataclass(frozen=True)
class RegisteredUserMod:
    descriptor: ModDescriptor
    payload_root: Path
    source_fingerprint: str


def draft_fingerprint(draft: ModDraft) -> str:
    digest = hashlib.sha256()
    for item in sorted(draft.payload, key=lambda value: value.target_path.casefold()):
        digest.update(item.target_path.casefold().encode("utf-8"))
        digest.update(item.sha256.encode("ascii"))
        digest.update(str(item.size_bytes).encode("ascii"))
    return digest.hexdigest().upper()


class UserModRegistry:
    def __init__(self, root: Path, inspector: ModPackageInspector) -> None:
        self.root = root.resolve()
        self.payload_root = (self.root / "payloads").resolve()
        self.catalog_path = self.root / "catalog.json"
        self.inspector = inspector
        self.root.mkdir(parents=True, exist_ok=True)
        self.payload_root.mkdir(parents=True, exist_ok=True)

    def load(self) -> tuple[ModCatalog | None, dict[str, Path]]:
        if not self.catalog_path.is_file():
            return None, {}
        catalog = ModCatalog.from_file(self.catalog_path)
        overrides: dict[str, Path] = {}
        for descriptor in catalog.entries:
            payload = (self.payload_root / descriptor.mod_id).resolve()
            self._ensure_contained(payload, self.payload_root)
            overrides[descriptor.mod_id] = payload
        return catalog, overrides

    def registered_fingerprints(self) -> set[str]:
        fingerprints: set[str] = set()
        for manifest in self.payload_root.glob("*/registration.json"):
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            value = payload.get("source_fingerprint")
            if isinstance(value, str) and value:
                fingerprints.add(value.upper())
        return fingerprints

    def register(
        self,
        draft: ModDraft,
        display: Mapping[str, str],
        *,
        reserved_ids: set[str],
    ) -> RegisteredUserMod:
        fingerprint = draft_fingerprint(draft)
        if fingerprint in self.registered_fingerprints():
            raise UserModRegistryError("该 MOD 内容已经添加。")
        mod_id = self._unique_id(draft.suggested_id, reserved_ids)
        payload = self.inspector.read_payload(draft)
        if not payload:
            raise UserModRegistryError("没有可登记的 MOD 载荷。")
        primary = next(
            (item for item in draft.payload if item.target_path.casefold().endswith(".dll")),
            None,
        )
        if primary is None:
            raise UserModRegistryError("没有可登记的 MOD DLL。")

        staging = (self.payload_root / f".{mod_id}.adding-{uuid.uuid4().hex}").resolve()
        destination = (self.payload_root / mod_id).resolve()
        self._ensure_contained(staging, self.payload_root)
        self._ensure_contained(destination, self.payload_root)
        if destination.exists():
            raise UserModRegistryError("MOD 本地库目录已经存在。")
        staging.mkdir()
        try:
            specs: list[dict[str, object]] = []
            for item in draft.payload:
                relative = normalize_member_path(item.target_path)
                content = payload.get(item.target_path)
                if content is None:
                    raise UserModRegistryError("MOD 载荷读取不完整。")
                if len(content) != item.size_bytes:
                    raise UserModRegistryError("MOD 载荷大小发生变化。")
                digest = hashlib.sha256(content).hexdigest().upper()
                if digest != item.sha256:
                    raise UserModRegistryError("MOD 载荷内容发生变化。")
                target = staging.joinpath(*PurePosixPath(relative).parts).resolve()
                self._ensure_contained(target, staging)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                specs.append(
                    {
                        "path": relative,
                        "sha256": digest,
                        "size_bytes": len(content),
                    }
                )
            registration = {
                "schema_version": 1,
                "source_name": draft.source.name,
                "source_fingerprint": fingerprint,
                "evidence": list(draft.evidence),
                "warnings": list(draft.warnings),
            }
            (staging / "registration.json").write_text(
                json.dumps(registration, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(staging, destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

        try:
            entry = self._catalog_entry(
                mod_id, draft, display, specs, primary.target_path
            )
            existing = self._catalog_payload()
            entries = existing["entries"]
            if not isinstance(entries, list):
                raise UserModRegistryError("用户 MOD 目录损坏。")
            entries.append(entry)
            self._write_catalog(existing)
            descriptor = ModCatalog.from_payload(
                {"schema_version": 2, "entries": [entry]}
            ).entries[0]
        except Exception:
            self._remove_generated_payload(destination)
            raise
        return RegisteredUserMod(descriptor, destination, fingerprint)

    def _catalog_entry(
        self,
        mod_id: str,
        draft: ModDraft,
        display: Mapping[str, str],
        specs: list[dict[str, object]],
        primary_path: str,
    ) -> dict[str, object]:
        required = ("name", "version", "author", "summary", "usage_hint")
        values = {key: str(display.get(key, "")).strip() for key in required}
        if any(not values[key] for key in required):
            raise UserModRegistryError("MOD 名称、版本、作者、简介和使用方法都必须填写。")
        primary_name = PurePosixPath(primary_path).name
        matching = [
            spec
            for spec in specs
            if PurePosixPath(str(spec["path"])).name.casefold()
            == primary_name.casefold()
        ]
        if len(matching) != 1:
            raise UserModRegistryError("无法确定 MOD 主 DLL。")
        primary = matching[0]
        provides = [
            PurePosixPath(str(spec["path"])).name.casefold()
            for spec in specs
            if str(spec["path"]).casefold().endswith(".dll")
        ]
        operation: dict[str, object] = {
            "kind": "bepinex_plugin",
            "expected_filename": primary_name,
            "bundled": True,
            "bundle_dir": "payload",
            "files": specs,
            "provides": list(dict.fromkeys(provides)),
            "hotkeys": list(draft.hotkeys),
        }
        if draft.panel_hotkey is not None:
            operation["panel_hotkey"] = draft.panel_hotkey
        return {
            "id": mod_id,
            "display": values,
            "operation": operation,
            "integrity_policy": {
                "version_note": f"user imported {values['version']}",
                "author_source": "lc2-mod.json or user-confirmed import preview",
                "author_channel": "local user import",
                "sha256": primary["sha256"],
                "size_bytes": primary["size_bytes"],
                "signature_status": "not_assessed",
                "risk_level": "high",
                "capabilities": ["gameplay modification"],
                "redistribution_status": "local_user_import",
            },
        }

    def _catalog_payload(self) -> dict[str, object]:
        if not self.catalog_path.exists():
            return {"schema_version": 2, "entries": []}
        try:
            payload = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exception:
            raise UserModRegistryError("用户 MOD 目录损坏。") from exception
        if not isinstance(payload, dict) or payload.get("schema_version") != 2:
            raise UserModRegistryError("用户 MOD 目录版本不受支持。")
        return payload

    def _write_catalog(self, payload: dict[str, object]) -> None:
        ModCatalog.from_payload(payload)
        temporary = self.catalog_path.with_suffix(".json.writing")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, self.catalog_path)

    @staticmethod
    def _unique_id(suggested: str, reserved_ids: set[str]) -> str:
        base = suggested if ID_PATTERN.fullmatch(suggested) else slugify(suggested)
        if base not in reserved_ids:
            return base
        index = 2
        while True:
            suffix = f"-{index}"
            candidate = f"{base[: 64 - len(suffix)]}{suffix}"
            if candidate not in reserved_ids:
                return candidate
            index += 1

    @staticmethod
    def _ensure_contained(path: Path, root: Path) -> None:
        try:
            path.relative_to(root)
        except ValueError as exception:
            raise UserModRegistryError("用户 MOD 路径越界。") from exception

    @staticmethod
    def _remove_generated_payload(destination: Path) -> None:
        if not destination.is_dir():
            return
        for path in sorted(destination.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        destination.rmdir()
