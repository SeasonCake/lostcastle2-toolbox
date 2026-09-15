from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from toolbox.mod_inspector import _bepin_plugin_metadata
from toolbox.mod_manager import ModCatalog, ModConflictError, ModIntegrityError, ModManager, ModManagerError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = PROJECT_ROOT / 'assets/community_mod_catalog.json'
SELECTED = {
    'fire-dragon-enhancement': ('1.0.0', 2, '2FFD4F9F11CEEA67F48427FA89968FCDADD7FC8F30DEC85C1DFA6D72A73E6ACA'),
    'tornado-greatsword': ('1.0.0', 1, '0322D96260F54203848B9C5E47631D9C2FB23BB760A257A98B79A1B0D1658296'),
    'fire-dragon-synthesis': ('1.1', 3, 'BB284B81B39B9AAC441B738189C1C9C80BEEEF263820A088A798857DD88DE318'),
    'dual-blades-overhaul': ('1.0.0', 2, '04E32BF33DFD632EFEF6F3C55804C6AFA52DBFDD07A23C415769AFB76E432D23'),
    'icebound-wand-tuner': ('0.4.3', 1, '0BE8C4FF2595A1785CEE82825BC17AE0485BD07ECC09A0F479486D4F35A002F3'),
    'unified-tools': ('1.0.0', 1, '9DB7675D86935E3033FBF014FC260D21DDC78D837C493F4F0DD256C9A869DA4C'),
    'master-craftsman-cannon': ('0.1.0', 1, '06213B8FEE7681380CF6D174B84BC67038424541D80A4F984B4E74E0AC6FD8C3'),
    'weapon-picker': ('1.2.6', 1, '0384C2B7725E82F1B18350FFAC808A7D56F2910696EFF9483F6A2BC66ACF4F1F'),
    'loot-combat-enhancement': ('2.8.0', 1, '4D6CA50762804119595B396C1C2017498501CCC22A4CBC44E7E7AB21BB09DB69'),
    'dark-matter-black-hole': ('1.0.0', 1, '90EB82BEA30130A1A562A919A435752631C558F7AEB263201FF9C5761B503902'),
    'goblin-cannon-dark-matter': ('1.0.0', 1, '2C58ED28BAB6F98EF7CA085C720C78D43B79F6CCBE4E82BF1FDC8842AE845024'),
}


class CommunityModUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ModCatalog.from_file(CATALOG_PATH)

    def require_payloads(self, *mod_ids: str) -> None:
        for mod_id in mod_ids:
            descriptor = self.catalog.get(mod_id)
            for spec in descriptor.operation.files:
                if not (PROJECT_ROOT / 'third_party' / descriptor.operation.bundle_dir / spec.path).is_file():
                    self.skipTest('Git-ignored local community payloads are not provisioned')

    def manager(self, root: Path) -> ModManager:
        game = root / 'game'
        (game / 'BepInEx/plugins').mkdir(parents=True)
        exe = game / 'LostCastle2.exe'
        exe.write_bytes(b'fixture; never executed')
        return ModManager(self.catalog, root / 'managed', PROJECT_ROOT / 'third_party', game_exe_provider=lambda: exe)

    def test_selected_versions_payload_sets_and_visible_copy(self) -> None:
        raw = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
        for mod_id, (version, file_count, primary_sha) in SELECTED.items():
            with self.subTest(mod_id=mod_id):
                descriptor = self.catalog.get(mod_id)
                self.assertEqual(descriptor.display.version, version)
                self.assertEqual(len(descriptor.operation.files), file_count)
                self.assertEqual(descriptor.integrity_policy.sha256, primary_sha)
                entry = next(e for e in raw['entries'] if e['id'] == mod_id)
                display = json.dumps(entry['display'], ensure_ascii=False)
                for internal in ('sha256', 'redistribution_status', 'BepInPlugin', 'signature_status', 'source_sha256'):
                    self.assertNotIn(internal, display)
                for spec in descriptor.operation.files:
                    self.assertEqual(Path(spec.path).name, spec.path)
                    self.assertTrue(spec.path.endswith('.dll'))
                traversal = copy.deepcopy(entry)
                traversal['operation']['files'][0]['path'] = '../outside.dll'
                with self.assertRaises(ModManagerError):
                    ModCatalog.from_payload({'schema_version': 2, 'entries': [traversal]})
        loot = self.catalog.get('loot-combat-enhancement')
        self.assertEqual(loot.operation.superseded_files[0].sha256, '524342AC2C0A49AAC13C582AC79DBC11B1BCAA293A25CB345C896EC88CCB563C')
        self.assertEqual(loot.operation.superseded_files[0].path, loot.operation.expected_filename)
        self.assertIn('1.2.7', self.catalog.get('weapon-picker').display.usage_hint)
        self.assertIn('测试版', self.catalog.get('fire-dragon-synthesis').display.name)
        self.assertNotIn('半成品完整版v2.1', json.dumps(raw, ensure_ascii=False))

    def test_missing_companion_dll_is_rejected_before_any_install_write(self) -> None:
        grouped = ('fire-dragon-enhancement', 'dual-blades-overhaul', 'fire-dragon-synthesis')
        self.require_payloads(*grouped)
        for mod_id in grouped:
            descriptor = self.catalog.get(mod_id)
            for omitted in descriptor.operation.files:
                with self.subTest(mod_id=mod_id, omitted=omitted.path), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    manager = self.manager(root)
                    marker = root / 'game/BepInEx/plugins/unrelated.txt'
                    marker.write_text('keep', encoding='utf-8')
                    partial = root / 'partial'
                    partial.mkdir()
                    for spec in descriptor.operation.files:
                        if spec == omitted:
                            continue
                        source = PROJECT_ROOT / 'third_party' / descriptor.operation.bundle_dir / spec.path
                        (partial / spec.path).write_bytes(source.read_bytes())
                    with self.assertRaises(ModIntegrityError):
                        manager.install(mod_id, partial)
                    self.assertEqual(marker.read_text(encoding='utf-8'), 'keep')
                    self.assertEqual(list((root / 'game/BepInEx/plugins').rglob('*.dll')), [])

    def test_unified_and_legacy_modules_are_mutually_exclusive_both_directions(self) -> None:
        legacy = ('monster-treasure', 'inventory-source-panel', 'player-live-stats')
        self.require_payloads('unified-tools', *legacy)
        for mod_id in legacy:
            with self.subTest(mod_id=mod_id), tempfile.TemporaryDirectory() as temporary:
                manager = self.manager(Path(temporary))
                old_path = manager.install(mod_id)
                original = old_path.read_bytes()
                with self.assertRaises(ModConflictError):
                    manager.install('unified-tools')
                self.assertEqual(old_path.read_bytes(), original)
                self.assertFalse(manager.status('unified-tools').present)
                manager.uninstall(mod_id)
                unified_path = manager.install('unified-tools')
                with self.assertRaises(ModConflictError):
                    manager.install(mod_id)
                self.assertTrue(unified_path.is_file())
                manager.uninstall('unified-tools')
                manager.install(mod_id)
                self.assertTrue(manager.status(mod_id).installed)

    def test_all_registered_plugin_guids_include_companions_without_duplicates(self) -> None:
        self.require_payloads(*(entry.mod_id for entry in self.catalog.entries))
        by_guid: dict[str, str] = {}
        for entry in self.catalog.entries:
            for spec in entry.operation.files:
                if not spec.path.endswith('.dll'):
                    continue
                payload = PROJECT_ROOT / 'third_party' / entry.operation.bundle_dir / spec.path
                metadata = _bepin_plugin_metadata(payload.read_bytes())
                self.assertIsNotNone(metadata, payload.name)
                assert metadata is not None
                guid = metadata[0].casefold()
                self.assertNotIn(guid, by_guid, f'{entry.mod_id}/{spec.path} duplicates {by_guid.get(guid)}')
                by_guid[guid] = f'{entry.mod_id}/{spec.path}'
        self.assertEqual(len(by_guid), 77)


if __name__ == '__main__':
    unittest.main()
