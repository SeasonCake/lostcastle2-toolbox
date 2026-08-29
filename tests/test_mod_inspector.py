from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from toolbox.mod_inspector import ModInspectionError, ModPackageInspector
from toolbox.mod_manager import ModCatalog, ModManager
from toolbox.user_mod_registry import UserModRegistry, UserModRegistryError
from tools.prepare_community_mods import selected_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ModInspectorTests(unittest.TestCase):
    def make_inspector(self) -> ModPackageInspector:
        return ModPackageInspector(Path(sys.executable))

    def test_curated_payload_can_select_a_duplicate_filename_by_sha256(self) -> None:
        payload = {
            "variant-a/Plugin.dll": b"older",
            "variant-b/Plugin.dll": b"newer",
        }
        import hashlib

        selected = selected_payload(
            {
                "include": [
                    {
                        "sha256": hashlib.sha256(b"newer").hexdigest(),
                        "target": "Plugin.dll",
                    }
                ]
            },
            payload,
        )
        self.assertEqual(selected, {"Plugin.dll": b"newer"})

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
                "interaction": {"panel_hotkey": "F6"},
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
            self.assertEqual(draft.panel_hotkey, "F6")

    def test_panel_hotkey_is_inferred_only_for_explicit_ui_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "PanelMod.dll").write_bytes(b"panel")
            (root / "README.txt").write_text(
                "安装后按 INS 打开设置界面。", encoding="utf-8"
            )
            draft = self.make_inspector().inspect(root)
            self.assertEqual(draft.hotkeys, ("INS",))
            self.assertEqual(draft.panel_hotkey, "INS")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "ActionMod.dll").write_bytes(b"action")
            (root / "README.txt").write_text(
                "安装后按 F1 直接丢出金币。", encoding="utf-8"
            )
            draft = self.make_inspector().inspect(root)
            self.assertEqual(draft.hotkeys, ("F1",))
            self.assertIsNone(draft.panel_hotkey)

    def test_managed_dotnet_user_strings_recover_embedded_author_without_guessing_panel(self) -> None:
        source = (
            PROJECT_ROOT
            / "third_party"
            / "community_mods"
            / "player-live-stats"
            / "实时数值v2.0.dll"
        )
        draft = self.make_inspector().inspect(source)
        self.assertEqual(draft.author, "懒虫桑")
        self.assertIsNone(draft.panel_hotkey)

    def test_manifest_rejects_unsupported_or_duplicate_modifier_panel_hotkey(self) -> None:
        for panel_hotkey in ("F13", "CTRL+CTRL+F5"):
            with self.subTest(panel_hotkey=panel_hotkey), tempfile.TemporaryDirectory() as temp_dir:
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
                            "interaction": {"panel_hotkey": panel_hotkey},
                            "install": {"files": ["Fixture.dll"]},
                        }
                    ),
                    encoding="utf-8",
                )
                with self.assertRaises(ModInspectionError):
                    self.make_inspector().inspect(root)

    def test_manifest_payload_limits_match_automatic_inspection_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            files = ["Plugin.dll", *(f"data-{index}.cfg" for index in range(64))]
            for name in files:
                (root / name).write_bytes(b"x")
            (root / "lc2-mod.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "too-many-files",
                        "display": {
                            "name": "Too Many",
                            "version": "1.0",
                            "author": "Author",
                            "summary": "Summary",
                            "usage_hint": "Usage",
                        },
                        "install": {"files": files},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ModInspectionError, "文件过多"):
                self.make_inspector().inspect(root)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            files = ["Plugin.dll", "Data.bytes", "More.bytes"]
            for name, size in zip(
                files,
                (64 * 1024 * 1024, 64 * 1024 * 1024, 1),
                strict=True,
            ):
                with (root / name).open("wb") as stream:
                    stream.truncate(size)
            (root / "lc2-mod.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "too-large",
                        "display": {
                            "name": "Too Large",
                            "version": "1.0",
                            "author": "Author",
                            "summary": "Summary",
                            "usage_hint": "Usage",
                        },
                        "install": {"files": files},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ModInspectionError, "载荷过大"):
                self.make_inspector().inspect(root)

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

    def test_same_plugin_version_series_keeps_only_the_latest_dll(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "RealtimeData1.1.dll").write_bytes(b"old")
            (root / "RealtimeData1.2.dll").write_bytes(b"middle")
            (root / "RealtimeData1.3.dll").write_bytes(b"latest")

            draft = self.make_inspector().inspect(root)

            self.assertEqual(len(draft.payload), 1)
            self.assertEqual(draft.payload[0].target_path, "RealtimeData1.3.dll")
            self.assertEqual(draft.version, "1.3")
            self.assertEqual(draft.suggested_id, "realtimedata")

    def test_distinct_versioned_plugin_names_are_not_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "FeatureA1.2.dll").write_bytes(b"first")
            (root / "FeatureB1.3.dll").write_bytes(b"second")

            draft = self.make_inspector().inspect(root)

            self.assertEqual(
                {item.target_path for item in draft.payload},
                {"FeatureA1.2.dll", "FeatureB1.3.dll"},
            )

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

    def test_formatted_user_mod_round_trip_preserves_panel_action_and_uninstall_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            (source / "Fixture.dll").write_bytes(b"fixture panel plugin")
            (source / "lc2-mod.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "fixture-panel",
                        "display": {
                            "name": "Fixture Panel",
                            "version": "1.2.0",
                            "author": "Fixture Author",
                            "summary": "Fixture panel summary",
                            "usage_hint": "安装后按 Insert（Ins）键打开设置面板。",
                        },
                        "interaction": {"panel_hotkey": "INS"},
                        "install": {"files": ["Fixture.dll"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            inspector = self.make_inspector()
            draft = inspector.inspect(source)
            registry = UserModRegistry(root / "registry", inspector)
            registered = registry.register(
                draft,
                {
                    "name": draft.name,
                    "version": draft.version,
                    "author": draft.author,
                    "summary": draft.summary,
                    "usage_hint": draft.usage_hint,
                },
                reserved_ids=set(),
            )
            catalog, overrides = registry.load()
            self.assertIsNotNone(catalog)
            assert catalog is not None
            descriptor = catalog.get(registered.descriptor.mod_id)
            self.assertEqual(descriptor.operation.panel_hotkey, "INS")

            game = root / "game"
            plugins = game / "BepInEx" / "plugins"
            plugins.mkdir(parents=True)
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            unrelated = plugins / "unrelated" / "keep.dll"
            unrelated.parent.mkdir()
            unrelated.write_bytes(b"keep")
            manager = ModManager(
                catalog,
                root / "managed",
                root / "bundled",
                game_exe_provider=lambda: game_exe,
                source_overrides=overrides,
            )
            manager.install(descriptor.mod_id)
            self.assertTrue(manager.status(descriptor.mod_id).installed)
            self.assertIsNotNone(manager.installed_mtime_ns(descriptor.mod_id))
            self.assertTrue(manager.uninstall(descriptor.mod_id))
            self.assertEqual(manager.status(descriptor.mod_id).state, "not_installed")
            self.assertTrue(unrelated.is_file())


if __name__ == "__main__":
    unittest.main()
