from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from toolbox.mod_manager import (
    ModCatalog,
    ModIntegrityError,
    ModManager,
    ModManagerError,
    ModSourceRequired,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def catalog_payload(content: bytes) -> dict[str, object]:
    return {
        "schema_version": 2,
        "entries": [
            {
                "id": "fixture-tool",
                "display": {
                    "name": "Fixture Tool",
                    "version": "1.0",
                    "author": "Fixture Author",
                    "summary": "Fixture",
                },
                "operation": {
                    "kind": "external_trainer",
                    "expected_filename": "fixture.exe",
                    "bundled": False,
                },
                "integrity_policy": {
                    "version_note": "fixture version",
                    "author_source": "test fixture",
                    "author_channel": "local",
                    "sha256": hashlib.sha256(content).hexdigest().upper(),
                    "size_bytes": len(content),
                    "signature_status": "unsigned",
                    "risk_level": "high",
                    "capabilities": ["fixture mutation"],
                    "redistribution_status": "test_only",
                },
            }
        ],
    }


class ModManagerTests(unittest.TestCase):
    def make_manager(self, root: Path, content: bytes) -> ModManager:
        catalog_path = root / "catalog.json"
        catalog_path.write_text(json.dumps(catalog_payload(content)), encoding="utf-8")
        return ModManager(
            ModCatalog.from_file(catalog_path),
            root / "managed",
            root / "bundled",
        )

    def test_public_catalog_separates_display_operation_and_policy(self) -> None:
        catalog = ModCatalog.from_file(PROJECT_ROOT / "assets" / "mod_catalog.json")
        entry = catalog.get("soul-stone-trainer")
        self.assertEqual(entry.display.author, "恨你不见")
        self.assertEqual(entry.display.version, "1.2")
        self.assertEqual(entry.display.summary, "生成和管理灵魂石")
        self.assertTrue(entry.operation.bundled)
        self.assertIn("v5.0", entry.integrity_policy.version_note)
        self.assertIn(
            "author_approved", entry.integrity_policy.redistribution_status
        )
        self.assertEqual(len(entry.integrity_policy.sha256), 64)
        display_json = json.dumps(asdict(entry.display), ensure_ascii=False).casefold()
        self.assertNotIn("frida", display_json)
        self.assertNotIn("sha-256", display_json)
        self.assertNotIn("授权", display_json)
        self.assertNotIn("C:\\", json.dumps(asdict(entry), ensure_ascii=False))

    def test_catalog_rejects_internal_details_in_display_copy(self) -> None:
        payload = catalog_payload(b"x")
        payload["entries"][0]["display"]["summary"] = "Uses Frida injection"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ModManagerError):
                ModCatalog.from_file(path)

    def test_regular_ui_copy_does_not_expose_internal_mod_metadata(self) -> None:
        visible_sources = (
            PROJECT_ROOT / "toolbox" / "app_shell.py",
            PROJECT_ROOT / "package_assets" / "使用说明.txt",
        )
        forbidden = (
            "frida",
            "注入",
            "未签名",
            "sha-256",
            "授权来源",
            "再分发",
            "无遥测",
            "无账号",
        )
        for source in visible_sources:
            text = source.read_text(encoding="utf-8").casefold()
            for term in forbidden:
                self.assertNotIn(term, text, f"{term!r} leaked into {source.name}")

    def test_user_supplied_file_is_verified_copied_and_removed_without_touching_original(self) -> None:
        content = b"fixture executable bytes"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "download.exe"
            source.write_bytes(content)
            manager = self.make_manager(root, content)
            with self.assertRaises(ModSourceRequired):
                manager.install("fixture-tool")
            target = manager.install("fixture-tool", source)
            self.assertTrue(target.is_file())
            self.assertTrue(manager.status("fixture-tool").installed)
            self.assertTrue(manager.uninstall("fixture-tool"))
            self.assertTrue(source.is_file())
            self.assertFalse(target.exists())

    def test_wrong_source_fails_closed_but_exact_managed_leaf_remains_removable(self) -> None:
        content = b"known content"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "download.exe"
            source.write_bytes(b"wrong content")
            manager = self.make_manager(root, content)
            with self.assertRaises(ModIntegrityError):
                manager.install("fixture-tool", source)
            source.write_bytes(content)
            target = manager.install("fixture-tool", source)
            target.write_bytes(b"tampered")
            self.assertEqual(manager.status("fixture-tool").state, "integrity_error")
            self.assertTrue(manager.uninstall("fixture-tool"))
            self.assertFalse(target.exists())

    def test_bundled_source_configures_without_a_file_picker(self) -> None:
        content = b"bundled fixture"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            payload = catalog_payload(content)
            payload["entries"][0]["operation"]["bundled"] = True  # type: ignore[index]
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(payload), encoding="utf-8")
            bundled = root / "bundled"
            bundled.mkdir()
            (bundled / "fixture.exe").write_bytes(content)
            manager = ModManager(
                ModCatalog.from_file(catalog_path),
                root / "managed",
                bundled,
            )
            target = manager.install("fixture-tool")
            self.assertTrue(target.is_file())
            self.assertTrue(manager.status("fixture-tool").installed)

    def test_catalog_rejects_path_traversal(self) -> None:
        payload = catalog_payload(b"x")
        payload["entries"][0]["operation"]["expected_filename"] = "../outside.exe"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ModManagerError):
                ModCatalog.from_file(path)


if __name__ == "__main__":
    unittest.main()
