from __future__ import annotations

import hashlib
import json
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
        "schema_version": 1,
        "entries": [
            {
                "id": "fixture-tool",
                "display_name": "Fixture Tool",
                "version": "1.0",
                "author": "Fixture Author",
                "author_source": "test fixture",
                "author_channel": "local",
                "kind": "external_trainer",
                "expected_filename": "fixture.exe",
                "sha256": hashlib.sha256(content).hexdigest().upper(),
                "size_bytes": len(content),
                "signature_status": "unsigned",
                "risk_level": "high",
                "capabilities": ["fixture mutation"],
                "redistribution_status": "test_only",
                "bundled": False,
                "description": "Fixture",
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

    def test_public_catalog_records_author_hash_and_non_bundled_status(self) -> None:
        catalog = ModCatalog.from_file(PROJECT_ROOT / "assets" / "mod_catalog.json")
        entry = catalog.get("soul-stone-trainer")
        self.assertEqual(entry.author, "恨你不见")
        self.assertEqual(entry.version, "1.2")
        self.assertFalse(entry.bundled)
        self.assertEqual(entry.redistribution_status, "permission_not_documented")
        self.assertEqual(len(entry.sha256), 64)
        self.assertNotIn("C:\\", json.dumps(entry.__dict__, ensure_ascii=False))

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

    def test_catalog_rejects_path_traversal(self) -> None:
        payload = catalog_payload(b"x")
        payload["entries"][0]["expected_filename"] = "../outside.exe"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ModManagerError):
                ModCatalog.from_file(path)


if __name__ == "__main__":
    unittest.main()
