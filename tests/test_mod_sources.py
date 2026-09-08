from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from tests.test_mod_manager import plugin_catalog_payload
from toolbox.mod_manager import ModCatalog, ModIntegrityError, ModManager


ROOT = Path(__file__).resolve().parents[1]


def make_manager(root: Path, files: dict[str, bytes]) -> ModManager:
    first_name, first_bytes = next(iter(files.items()))
    payload = plugin_catalog_payload(first_bytes)
    operation = payload["entries"][0]["operation"]
    operation.update(
        expected_filename=first_name,
        bundled=False,
        files=[
            {"path": name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest().upper()}
            for name, data in files.items()
        ],
    )
    game = root / "game"
    (game / "BepInEx").mkdir(parents=True)
    exe = game / "LostCastle2.exe"
    exe.write_bytes(b"fixture")
    return ModManager(
        ModCatalog.from_payload(payload), root / "managed", ROOT / "third_party",
        game_exe_provider=lambda: exe,
    )


class ModSourceTests(unittest.TestCase):
    def test_public_single_file_catalog_accepts_exact_dll(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"correct"})
            source = root / "download.dll"
            source.write_bytes(b"correct")
            target = manager.install("fixture-plugin", source)
            self.assertEqual(target.read_bytes(), b"correct")
            self.assertTrue(manager.status("fixture-plugin").installed)

    def test_original_archive_installs_only_registered_files_from_nested_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"main", "panel.dll": b"panel"})
            source = root / "original.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("原包/BepInEx/plugins/fixture.dll", b"main")
                archive.writestr("原包/BepInEx/plugins/panel.dll", b"panel")
                archive.writestr("原包/BepInEx/core/keep.dll", b"framework")
                archive.writestr("原包/说明.txt", "不要安装其它文件")
            target = manager.install("fixture-plugin", source)
            self.assertEqual({path.name for path in target.parent.iterdir()}, {"fixture.dll", "panel.dll"})
            self.assertFalse((root / "game/BepInEx/core").exists())

    def test_extracted_directory_with_wrapper_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"main"})
            folder = root / "download/原包"
            folder.mkdir(parents=True)
            (folder / "fixture.dll").write_bytes(b"main")
            self.assertEqual(manager.install("fixture-plugin", folder.parent).read_bytes(), b"main")

    def test_archive_member_renaming_does_not_reject_the_exact_registered_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"good"})
            source = root / "original.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("旧版/fixture.dll", b"old!")
                archive.writestr("新版/作者重新命名的文件.dll", b"good")
            self.assertEqual(manager.install("fixture-plugin", source).read_bytes(), b"good")

    def test_incomplete_multi_file_source_does_not_write_game_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"main", "panel.dll": b"panel"})
            source = root / "partial.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("fixture.dll", b"main")
            with self.assertRaises(ModIntegrityError) as caught:
                manager.install("fixture-plugin", source)
            self.assertEqual(caught.exception.code, "source_member_missing")
            self.assertIn("panel.dll", caught.exception.details["path"])
            self.assertFalse((root / "game/BepInEx/plugins/fixture-plugin").exists())

    def test_wrong_same_size_file_has_distinct_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"good"})
            source = root / "fixture.dll"
            source.write_bytes(b"evil")
            with self.assertRaises(ModIntegrityError) as caught:
                manager.install("fixture-plugin", source)
            self.assertEqual(caught.exception.code, "source_hash_mismatch")
            self.assertEqual(source.read_bytes(), b"evil")
            self.assertFalse((root / "game/BepInEx/plugins/fixture-plugin").exists())

    def test_multi_file_mod_requires_whole_source_instead_of_one_dll(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"main", "panel.dll": b"panel"})
            source = root / "fixture.dll"
            source.write_bytes(b"main")
            with self.assertRaises(ModIntegrityError) as caught:
                manager.install("fixture-plugin", source)
            self.assertEqual(caught.exception.code, "source_requires_package")

    def test_traversal_member_is_rejected_even_if_requested_dll_is_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"good"})
            source = root / "traversal.zip"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("fixture.dll", b"good")
                archive.writestr("../escape.dll", b"outside")
            with self.assertRaises(ModIntegrityError) as caught:
                manager.install("fixture-plugin", source)
            self.assertEqual(caught.exception.code, "source_unreadable")
            self.assertFalse((root / "escape.dll").exists())
            self.assertFalse((root / "game/BepInEx/plugins/fixture-plugin").exists())

    def test_missing_source_is_distinct_from_wrong_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"good"})
            with self.assertRaises(ModIntegrityError) as caught:
                manager.install("fixture-plugin", root / "missing")
            self.assertEqual(caught.exception.code, "source_missing")

    def test_known_in_place_upgrade_retains_a_modified_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"new"})
            payload = {"schema_version": 2, "entries": []}
            from dataclasses import asdict
            descriptor = manager.descriptor("fixture-plugin")
            entry = asdict(descriptor)
            entry["id"] = entry.pop("mod_id")
            entry["operation"]["superseded_files"] = [
                {"path": "fixture.dll", "sha256": hashlib.sha256(b"old").hexdigest().upper(), "size_bytes": 3}
            ]
            # JSON conversion gives the catalog its ordinary list-shaped inputs.
            import json
            payload["entries"] = [json.loads(json.dumps(entry))]
            manager.catalog = ModCatalog.from_payload(payload)
            target = manager.installed_path("fixture-plugin")
            target.parent.mkdir(parents=True)
            target.write_bytes(b"old")
            source = root / "fixture.dll"
            source.write_bytes(b"new")
            manager.install("fixture-plugin", source)
            self.assertEqual(target.read_bytes(), b"new")
            self.assertTrue(manager.status("fixture-plugin").installed)
            target.write_bytes(b"user modification")
            with self.assertRaises(ModIntegrityError) as caught:
                manager.install("fixture-plugin", source)
            self.assertEqual(caught.exception.code, "target_modified")
            self.assertEqual(target.read_bytes(), b"user modification")


if __name__ == "__main__":
    unittest.main()
