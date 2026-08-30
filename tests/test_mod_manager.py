from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from toolbox.mod_manager import (
    ModCatalog,
    ModConflictError,
    ModGamePathRequired,
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


def plugin_catalog_payload(content: bytes, archive_content: bytes = b"archive") -> dict[str, object]:
    payload = catalog_payload(content)
    entry = payload["entries"][0]  # type: ignore[index]
    entry["id"] = "fixture-plugin"
    entry["operation"] = {
        "kind": "bepinex_plugin",
        "expected_filename": "fixture.dll",
        "bundled": False,
        "archive_source": {
            "expected_filename": "fixture.7z",
            "member": "fixture.dll",
            "sha256": hashlib.sha256(archive_content).hexdigest().upper(),
            "size_bytes": len(archive_content),
        },
    }
    return payload


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
        gold = catalog.get("gold-editor-f5")
        self.assertEqual(gold.display.author, "刺心")
        self.assertIn("按 F5", gold.display.usage_hint)
        self.assertEqual(gold.operation.kind, "bepinex_plugin")
        self.assertTrue(gold.operation.bundled)
        self.assertFalse(gold.operation.launchable)
        self.assertTrue(gold.operation.requires_game_launch)
        self.assertTrue(gold.operation.has_game_panel)
        self.assertEqual(gold.operation.panel_hotkey, "F5")
        self.assertEqual(gold.operation.archive_source.member, "LC2GoldFree.dll")

    def test_catalog_rejects_internal_details_in_display_copy(self) -> None:
        payload = catalog_payload(b"x")
        payload["entries"][0]["display"]["summary"] = "Uses Frida injection"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ModManagerError):
                ModCatalog.from_file(path)

    def test_catalog_rejects_internal_details_in_usage_hint(self) -> None:
        payload = catalog_payload(b"x")
        payload["entries"][0]["display"]["usage_hint"] = "Uses Frida injection"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ModManagerError):
                ModCatalog.from_file(path)

    def test_panel_hotkey_must_be_supported_and_declared_as_a_hotkey(self) -> None:
        payload = plugin_catalog_payload(b"fixture")
        operation = payload["entries"][0]["operation"]  # type: ignore[index]
        operation["hotkeys"] = ["INS"]
        operation["panel_hotkey"] = "Insert"
        parsed = ModCatalog.from_payload(payload).entries[0]
        self.assertEqual(parsed.operation.panel_hotkey, "INS")

        operation["panel_hotkey"] = "F13"
        with self.assertRaises(ModManagerError):
            ModCatalog.from_payload(payload)

        operation["panel_hotkey"] = "F6"
        with self.assertRaises(ModManagerError):
            ModCatalog.from_payload(payload)

        operation["hotkeys"] = ["CTRL+CTRL+F5"]
        operation["panel_hotkey"] = "CTRL+CTRL+F5"
        with self.assertRaises(ModManagerError):
            ModCatalog.from_payload(payload)

    def test_bundled_gold_editor_build_contract_matches_catalog(self) -> None:
        catalog = ModCatalog.from_file(PROJECT_ROOT / "assets" / "mod_catalog.json")
        gold = catalog.get("gold-editor-f5")
        build_source = (PROJECT_ROOT / "build.ps1").read_text(encoding="utf-8")

        self.assertTrue(gold.operation.bundled)
        self.assertIn("third_party\\LC2GoldFree.dll", build_source)
        self.assertIn(gold.integrity_policy.sha256, build_source)
        self.assertIn('$goldEditorPath;third_party', build_source)

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

    def test_catalog_rejects_archive_member_path_traversal(self) -> None:
        payload = plugin_catalog_payload(b"plugin")
        payload["entries"][0]["operation"]["archive_source"]["member"] = "../fixture.dll"  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ModManagerError):
                ModCatalog.from_file(path)

    def test_bepinex_plugin_installs_and_uninstalls_only_owned_leaf(self) -> None:
        content = b"fixture plugin bytes"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = root / "game"
            game_exe = game_root / "LostCastle2.exe"
            plugins_root = game_root / "BepInEx" / "plugins"
            plugins_root.mkdir(parents=True)
            game_exe.write_bytes(b"game")
            sibling = plugins_root / "another-mod" / "keep.dll"
            sibling.parent.mkdir()
            sibling.write_bytes(b"keep")
            source = root / "fixture.dll"
            source.write_bytes(content)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(
                json.dumps(plugin_catalog_payload(content)), encoding="utf-8"
            )
            manager = ModManager(
                ModCatalog.from_file(catalog_path),
                root / "managed",
                root / "bundled",
                game_exe_provider=lambda: game_exe,
            )

            target = manager.install("fixture-plugin", source)
            self.assertEqual(
                target,
                plugins_root / "fixture-plugin" / "fixture.dll",
            )
            self.assertTrue(manager.status("fixture-plugin").installed)
            with self.assertRaises(ModManagerError):
                manager.launch("fixture-plugin")
            self.assertTrue(manager.uninstall("fixture-plugin"))
            self.assertTrue(sibling.is_file())

    def test_bepinex_plugin_requires_game_and_bepinex(self) -> None:
        content = b"fixture plugin bytes"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(
                json.dumps(plugin_catalog_payload(content)), encoding="utf-8"
            )
            manager = ModManager(
                ModCatalog.from_file(catalog_path),
                root / "managed",
                root / "bundled",
            )
            self.assertEqual(
                manager.status("fixture-plugin").state,
                "game_not_configured",
            )
            with self.assertRaises(ModGamePathRequired):
                manager.install("fixture-plugin", root / "fixture.dll")

    def test_verified_archive_materializes_exact_plugin_dll(self) -> None:
        content = b"fixture plugin bytes"
        archive_content = b"known archive bytes"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game_root = root / "game"
            game_exe = game_root / "LostCastle2.exe"
            (game_root / "BepInEx" / "plugins").mkdir(parents=True)
            game_exe.write_bytes(b"game")
            archive = root / "renamed.7z"
            archive.write_bytes(archive_content)
            catalog_path = root / "catalog.json"
            catalog_path.write_text(
                json.dumps(plugin_catalog_payload(content, archive_content)),
                encoding="utf-8",
            )
            manager = ModManager(
                ModCatalog.from_file(catalog_path),
                root / "managed",
                root / "bundled",
                game_exe_provider=lambda: game_exe,
            )
            manager._extract_archive_member = lambda _path, _member: content  # type: ignore[method-assign]
            target = manager.install("fixture-plugin", archive)
            self.assertEqual(target.read_bytes(), content)

            archive.write_bytes(b"wrong archive")
            with self.assertRaises(ModIntegrityError):
                manager.install("fixture-plugin", archive)

    def test_community_catalog_payloads_are_complete_and_hash_bound(self) -> None:
        catalog = ModCatalog.from_file(
            PROJECT_ROOT / "assets" / "community_mod_catalog.json"
        )
        self.assertEqual(len(catalog.entries), 53)
        bundled_root = PROJECT_ROOT / "third_party"
        for descriptor in catalog.entries:
            self.assertTrue(descriptor.operation.files)
            source_root = bundled_root / str(descriptor.operation.bundle_dir)
            for spec in descriptor.operation.files:
                payload = source_root.joinpath(*Path(spec.path).parts)
                self.assertTrue(payload.is_file(), payload)
                self.assertEqual(payload.stat().st_size, spec.size_bytes)
                self.assertEqual(
                    hashlib.sha256(payload.read_bytes()).hexdigest().upper(),
                    spec.sha256,
                )

    def test_latest_mod_family_versions_and_new_payload_identities_are_frozen(self) -> None:
        catalog = ModCatalog.from_file(
            PROJECT_ROOT / "assets" / "community_mod_catalog.json"
        )
        loot = catalog.get("loot-combat-enhancement")
        staff = catalog.get("staff-skin-swap")
        hide_fx = catalog.get("hide-weapon-fx")

        self.assertEqual(loot.display.version, "2.5.3")
        self.assertEqual(loot.display.author, "茶橘柚、空容、刺心")
        self.assertEqual(catalog.get("enhancement-plan").display.author, "茶橘柚、空容、刺心")
        self.assertEqual(catalog.get("dynamic-hp").display.author, "刺心")
        self.assertEqual(catalog.get("demon-invasion").display.author, "墨河以轩")
        self.assertEqual(staff.display.version, "1.5")
        self.assertEqual(staff.display.author, "兔子王お")
        self.assertEqual(hide_fx.display.version, "1.0")
        self.assertEqual(hide_fx.display.author, "兔子王お")
        self.assertEqual(
            hide_fx.operation.expected_filename,
            "LC2.HideWeaponFX震击环绕球隐藏.dll",
        )
        self.assertEqual(
            hide_fx.integrity_policy.sha256,
            "7A0C082EFE54CFAF7977515A09668EFB01E3CE9C25E22845249FDF1C1291D3E5",
        )
        self.assertIn("自动生效", hide_fx.display.usage_hint)

        live_stats = catalog.get("player-live-stats")
        self.assertEqual(live_stats.display.version, "2.0")
        self.assertEqual(live_stats.display.author, "懒虫桑")
        self.assertEqual(live_stats.operation.expected_filename, "实时数值v2.0.dll")
        self.assertEqual(live_stats.operation.hotkeys, ("F6",))
        self.assertEqual(live_stats.operation.panel_hotkey, "F6")
        self.assertIn("点击玩家名字", live_stats.display.usage_hint)
        self.assertEqual(
            live_stats.integrity_policy.sha256,
            "ED2183DD3DF1A9C7ECB0320D32A766893642A46AE65167E1162A2EB602610194",
        )
        self.assertEqual(len(live_stats.operation.files), 1)

        curse_coin = catalog.get("curse-coin")
        self.assertEqual(curse_coin.display.version, "1.5.0")
        self.assertIn("首个诅咒房", curse_coin.display.summary)
        self.assertIn("每个诅咒房", curse_coin.display.usage_hint)

        damage_meter = catalog.get("damage-meter")
        self.assertEqual(damage_meter.display.version, "1.6.4")
        self.assertEqual(damage_meter.display.author, "水生凛凛")
        self.assertEqual(
            damage_meter.integrity_policy.sha256,
            "915764422A72CE28D268BC19CDF794E781132F3A732EFE4004780EB5A3875A11",
        )
        self.assertIn("联机玩家分列", damage_meter.display.usage_hint)

        duration = catalog.get("evilstone-power-duration")
        self.assertEqual(duration.display.version, "1.5.0")
        self.assertEqual(duration.display.author, "大萝卜鸡")
        self.assertEqual(duration.operation.expected_filename, "EvilStonePowerDuration.dll")
        self.assertEqual(
            duration.integrity_policy.sha256,
            "334A4C3B48E91E74AC6F25576B05CDC4798478DA1DE81A66569D570554B1A099",
        )

        ice_pillar = catalog.get("ice-pillar-enhancement")
        self.assertEqual(ice_pillar.display.version, "1.16.0")
        self.assertEqual(ice_pillar.display.author, "大萝卜鸡")
        self.assertEqual(ice_pillar.operation.expected_filename, "IcePillarCrash.dll")
        self.assertEqual(ice_pillar.operation.hotkeys, ())
        self.assertIsNone(ice_pillar.operation.panel_hotkey)
        self.assertIn("6 增至 12", ice_pillar.display.summary)
        self.assertIn("没有独立设置面板", ice_pillar.display.usage_hint)
        self.assertEqual(
            ice_pillar.integrity_policy.sha256,
            "F4C53E57A87F1F3484E8562B01F43FB72EE92C69BA8BA80C55C77617E7D6253D",
        )

        drug_god = catalog.get("not-drug-god")
        self.assertEqual(drug_god.display.name, "我不是药神（测试版）")
        self.assertEqual(drug_god.display.version, "1.0.0")
        self.assertEqual(drug_god.display.author, "木亦")
        self.assertEqual(drug_god.operation.expected_filename, "LC2NotDrugGod.dll")
        self.assertEqual(drug_god.operation.hotkeys, ("F1",))
        self.assertEqual(drug_god.operation.panel_hotkey, "F1")
        self.assertIn("DIY 药水池", drug_god.display.usage_hint)
        self.assertIn("建议不要同时启用", drug_god.display.usage_hint)
        self.assertEqual(
            drug_god.integrity_policy.sha256,
            "B4D6DF015CCED212B47CF281C74E6EDF416B24E3570C16C4BCA8468277AC8B37",
        )

        hex_augment = catalog.get("hex-augment")
        self.assertEqual(hex_augment.display.version, "2.7.6")
        self.assertEqual(hex_augment.operation.expected_filename, "LC2HexAugment.dll")
        self.assertEqual(hex_augment.operation.hotkeys, ("F1",))
        self.assertEqual(hex_augment.operation.panel_hotkey, "F1")
        self.assertIn("建议不要同时启用", hex_augment.display.usage_hint)
        self.assertEqual(
            hex_augment.integrity_policy.sha256,
            "50CEB677DE7AB88D8E4E4FD8059CEA5FBC440D709DAA7E4A215B059938E04ECC",
        )

        purple_damage = catalog.get("purple-critical-damage")
        self.assertEqual(purple_damage.display.version, "1.0.0")
        self.assertEqual(purple_damage.display.author, "兔子王お")
        self.assertEqual(
            purple_damage.operation.expected_filename,
            "LC2PurpleDamage暴击字体红色改紫色.dll",
        )
        self.assertEqual(purple_damage.operation.hotkeys, ())
        self.assertIsNone(purple_damage.operation.panel_hotkey)
        self.assertIn("物理暴击", purple_damage.display.summary)
        self.assertIn("无快捷键", purple_damage.display.usage_hint)
        self.assertEqual(
            purple_damage.integrity_policy.sha256,
            "5863D6A9346304C418C731F73AF0E0413AAAE1FEBD569065697B9CBDC035EECB",
        )

        max_players = catalog.get("max-players-16")
        self.assertEqual(max_players.display.version, "1.3.0")
        self.assertEqual(max_players.display.author, "梦羽")
        self.assertEqual(
            max_players.operation.expected_filename,
            "LostCastle2MaxPlayers16.dll",
        )
        self.assertEqual(max_players.operation.hotkeys, ())
        self.assertIsNone(max_players.operation.panel_hotkey)
        self.assertIn("加入别人创建的房间前请先卸载", max_players.display.usage_hint)
        self.assertIn("1–16", max_players.display.usage_hint)
        self.assertEqual(
            max_players.integrity_policy.sha256,
            "1247F19FC0C0447B18E38FABC0AE08EF13967282A116D58C2CFF9FBD3A630F25",
        )

    def test_community_catalog_prioritizes_practical_mods_over_cosmetics(self) -> None:
        catalog = ModCatalog.from_file(
            PROJECT_ROOT / "assets" / "community_mod_catalog.json"
        )
        ids = [descriptor.mod_id for descriptor in catalog.entries]

        self.assertEqual(
            ids[:3],
            ["player-live-stats", "enhancement-plan", "resource-transfer-f1"],
        )
        self.assertLess(ids.index("enhancement-plan"), ids.index("resource-transfer-f1"))
        self.assertLess(ids.index("multiplayer-room-fix"), ids.index("max-players-16"))
        self.assertLess(ids.index("max-players-16"), ids.index("dynamic-hp"))
        self.assertLess(ids.index("hex-augment"), ids.index("item-ban-freenix"))
        self.assertLess(ids.index("item-ban-freenix"), ids.index("armor-transmog"))
        self.assertLess(ids.index("dynamic-hp"), ids.index("staff-skin-swap"))
        self.assertLess(ids.index("evilstone-power-duration"), ids.index("damage-meter"))
        self.assertLess(ids.index("ice-pillar-enhancement"), ids.index("damage-meter"))
        self.assertLess(ids.index("damage-meter"), ids.index("welcome-message"))
        self.assertLess(ids.index("hide-weapon-fx"), ids.index("purple-critical-damage"))
        self.assertLess(ids.index("purple-critical-damage"), ids.index("armor-transmog"))

    def test_all_community_mods_install_and_uninstall_in_isolated_game(self) -> None:
        catalog = ModCatalog.from_file(
            PROJECT_ROOT / "assets" / "community_mod_catalog.json"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            plugins = game / "BepInEx" / "plugins"
            plugins.mkdir(parents=True)
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            sibling = plugins / "unrelated" / "keep.dll"
            sibling.parent.mkdir()
            sibling.write_bytes(b"keep")
            manager = ModManager(
                catalog,
                root / "managed",
                PROJECT_ROOT / "third_party",
                game_exe_provider=lambda: game_exe,
            )
            for descriptor in catalog.entries:
                manager.install(descriptor.mod_id)
                self.assertTrue(manager.status(descriptor.mod_id).installed)
                self.assertTrue(manager.uninstall(descriptor.mod_id))
                self.assertEqual(
                    manager.status(descriptor.mod_id).state, "not_installed"
                )
                self.assertTrue(sibling.is_file())

    def test_multi_file_package_install_status_and_uninstall_preserve_unknown_leaf(self) -> None:
        first = b"first dll"
        second = b"dependency dll"
        payload = plugin_catalog_payload(first)
        entry = payload["entries"][0]  # type: ignore[index]
        entry["operation"] = {
            "kind": "bepinex_plugin",
            "expected_filename": "fixture.dll",
            "bundled": True,
            "bundle_dir": "community_mods/fixture-plugin",
            "files": [
                {
                    "path": "fixture.dll",
                    "sha256": hashlib.sha256(first).hexdigest().upper(),
                    "size_bytes": len(first),
                },
                {
                    "path": "libs/dependency.dll",
                    "sha256": hashlib.sha256(second).hexdigest().upper(),
                    "size_bytes": len(second),
                },
            ],
            "provides": ["fixture.dll", "dependency.dll"],
            "hotkeys": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundled = root / "bundled" / "community_mods" / "fixture-plugin"
            (bundled / "libs").mkdir(parents=True)
            (bundled / "fixture.dll").write_bytes(first)
            (bundled / "libs" / "dependency.dll").write_bytes(second)
            game = root / "game"
            (game / "BepInEx" / "plugins").mkdir(parents=True)
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            manager = ModManager(
                ModCatalog.from_payload(payload),
                root / "managed",
                root / "bundled",
                game_exe_provider=lambda: game_exe,
            )
            manager.install("fixture-plugin")
            target_dir = game / "BepInEx" / "plugins" / "fixture-plugin"
            unknown = target_dir / "keep.user"
            unknown.write_bytes(b"keep")
            self.assertTrue(manager.status("fixture-plugin").installed)
            self.assertTrue(manager.uninstall("fixture-plugin"))
            self.assertTrue(unknown.is_file())
            self.assertFalse((target_dir / "fixture.dll").exists())
            self.assertFalse((target_dir / "libs" / "dependency.dll").exists())

    def test_same_provided_dll_blocks_second_installed_mod(self) -> None:
        first = b"first"
        second = b"second"
        payload = plugin_catalog_payload(first)
        first_entry = payload["entries"][0]  # type: ignore[index]
        first_entry["operation"]["provides"] = ["shared.dll"]  # type: ignore[index]
        second_entry = json.loads(json.dumps(first_entry))
        second_entry["id"] = "second-plugin"
        second_entry["display"]["name"] = "Second Plugin"
        second_entry["operation"]["expected_filename"] = "second.dll"
        second_entry["operation"]["provides"] = ["shared.dll"]
        second_entry["integrity_policy"]["sha256"] = hashlib.sha256(second).hexdigest().upper()
        second_entry["integrity_policy"]["size_bytes"] = len(second)
        payload["entries"].append(second_entry)  # type: ignore[index]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = root / "game"
            (game / "BepInEx" / "plugins").mkdir(parents=True)
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            first_source = root / "first.dll"
            second_source = root / "second.dll"
            first_source.write_bytes(first)
            second_source.write_bytes(second)
            manager = ModManager(
                ModCatalog.from_payload(payload),
                root / "managed",
                root / "bundled",
                game_exe_provider=lambda: game_exe,
            )
            manager.install("fixture-plugin", first_source)
            with self.assertRaises(ModConflictError) as context:
                manager.install("second-plugin", second_source)
            self.assertEqual(context.exception.conflicts, ("Fixture Tool",))


if __name__ == "__main__":
    unittest.main()
