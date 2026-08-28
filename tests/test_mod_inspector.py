from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from toolbox.mod_inspector import ModInspectionError, ModPackageInspector
from toolbox.mod_manager import ModCatalog, ModManager
from toolbox.user_mod_registry import UserModRegistry, UserModRegistryError


class ModInspectorTests(unittest.TestCase):
    def make_inspector(self) -> ModPackageInspector:
        return ModPackageInspector(Path(sys.executable))

    def test_folder_manifest_identifies_display_payload_and_hotkey(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "libs").mkdir()
            (root / "Fixture.dll").write_bytes(b"fixture")
            (root / "libs" / "Dependency.dll").write_bytes(b"dependency")
            manifest = {
                "schema_version": 1,
                "id": "fixture-mod",
                "display": {
                    "name": "Fixture MOD",
                    "version": "2.1.0",
                    "author": "Fixture Author",
                    "summary": "Fixture summary",
                    "usage_hint": "Press F6 in game.",
                },
                "install": {"files": ["Fixture.dll", "libs/Dependency.dll"]},
            }
            (root / "lc2-mod.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            draft = self.make_inspector().inspect(root)
            self.assertEqual(draft.suggested_id, "fixture-mod")
            self.assertEqual(draft.name, "Fixture MOD")
            self.assertEqual(draft.author, "Fixture Author")
            self.assertEqual(len(draft.payload), 2)
            self.assertEqual(draft.hotkeys, ("F6",))

    def test_folder_heuristic_excludes_obj_and_reference_dlls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            release = root / "bin" / "Release" / "net6.0"
            reference = root / "obj" / "Release" / "net6.0" / "ref"
            release.mkdir(parents=True)
            reference.mkdir(parents=True)
            (release / "Fixture.dll").write_bytes(b"release")
            (reference / "Fixture.dll").write_bytes(b"reference")
            draft = self.make_inspector().inspect(root)
            self.assertEqual(len(draft.payload), 1)
            self.assertEqual(draft.payload[0].target_path, "Fixture.dll")
            self.assertEqual(draft.author, "社区未署名")

    def test_framework_and_manifest_traversal_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "BepInEx" / "core"
            core.mkdir(parents=True)
            (core / "BepInEx.Core.dll").write_bytes(b"core")
            with self.assertRaises(ModInspectionError):
                self.make_inspector().inspect(root)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "Fixture.dll").write_bytes(b"fixture")
            (root / "lc2-mod.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "fixture-mod",
                        "display": {
                            "name": "Fixture",
                            "version": "1.0",
                            "author": "Author",
                            "summary": "Summary",
                            "usage_hint": "Usage",
                        },
                        "install": {"files": ["../Fixture.dll"]},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ModInspectionError):
                self.make_inspector().inspect(root)

    def test_user_registry_round_trip_and_duplicate_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "FixtureMod.dll"
            source.write_bytes(b"fixture plugin")
            inspector = self.make_inspector()
            draft = inspector.inspect(source)
            registry = UserModRegistry(root / "registry", inspector)
            registered = registry.register(
                draft,
                {
                    "name": "Fixture MOD",
                    "version": "1.0",
                    "author": "Fixture Author",
                    "summary": "Fixture summary",
                    "usage_hint": "Restart the game.",
                },
                reserved_ids=set(),
            )
            catalog, overrides = registry.load()
            self.assertIsNotNone(catalog)
            assert catalog is not None
            self.assertEqual(catalog.entries[0].mod_id, registered.descriptor.mod_id)
            self.assertEqual(
                overrides[registered.descriptor.mod_id], registered.payload_root
            )
            with self.assertRaises(UserModRegistryError):
                registry.register(
                    draft,
                    {
                        "name": "Fixture MOD",
                        "version": "1.0",
                        "author": "Fixture Author",
                        "summary": "Fixture summary",
                        "usage_hint": "Restart the game.",
                    },
                    reserved_ids={registered.descriptor.mod_id},
                )

            game = root / "game"
            (game / "BepInEx" / "plugins").mkdir(parents=True)
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            manager = ModManager(
                catalog,
                root / "managed",
                root / "bundled",
                game_exe_provider=lambda: game_exe,
                source_overrides=overrides,
            )
            manager.install(registered.descriptor.mod_id)
            self.assertTrue(manager.status(registered.descriptor.mod_id).installed)


if __name__ == "__main__":
    unittest.main()
