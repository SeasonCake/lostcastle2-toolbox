from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from toolbox.mod_manager import ModCatalog, ModIntegrityError, ModManager, ModManagerError


def file_spec(path: str, data: bytes) -> dict:
    return {'path': path, 'sha256': hashlib.sha256(data).hexdigest().upper(), 'size_bytes': len(data)}


def catalog_payload() -> dict:
    current = file_spec('feature.dll', b'current feature')
    return {'schema_version': 2, 'entries': [{
        'id': 'history-fixture',
        'display': {'name': 'History fixture', 'version': '3.0', 'author': 'Fixture', 'summary': 'Fixture'},
        'operation': {
            'kind': 'bepinex_plugin', 'expected_filename': 'feature.dll', 'bundled': False,
            'files': [current],
            'superseded_files': [file_spec('feature.dll', b'old version one'), file_spec('FEATURE.dll', b'old version two')],
        },
        'integrity_policy': {
            'sha256': current['sha256'], 'size_bytes': current['size_bytes'],
            'version_note': 'test fixture', 'author_source': 'test fixture', 'author_channel': 'local',
            'signature_status': 'not_assessed', 'risk_level': 'high', 'capabilities': ['test fixture'],
            'redistribution_status': 'test_only',
        },
    }]}


class SamePathHistoryTests(unittest.TestCase):
    def test_distinct_history_hashes_share_case_insensitive_path(self):
        descriptor = ModCatalog.from_payload(catalog_payload()).get('history-fixture')
        self.assertEqual(len(descriptor.operation.superseded_files), 2)

    def test_current_payload_paths_remain_unique(self):
        payload = catalog_payload()
        payload['entries'][0]['operation']['files'].append(file_spec('FEATURE.dll', b'other current'))
        with self.assertRaises(ModManagerError):
            ModCatalog.from_payload(payload)

    def test_duplicate_history_identity_rejected_even_with_different_size(self):
        for size_delta in [0, 1]:
            with self.subTest(size_delta=size_delta):
                payload = catalog_payload()
                history = payload['entries'][0]['operation']['superseded_files']
                duplicate = dict(history[0], path='FEATURE.dll', sha256=history[0]['sha256'].lower())
                duplicate['size_bytes'] += size_delta
                history.append(duplicate)
                with self.assertRaises(ModManagerError):
                    ModCatalog.from_payload(payload)

    def test_invalid_history_paths_hashes_and_sizes_rejected(self):
        mutations = [('path', '../outside.dll'), ('path', 'C:/outside.dll'), ('path', 'a/../outside.dll'),
                     ('sha256', 'invalid'), ('size_bytes', 0), ('size_bytes', -1), ('size_bytes', True), ('size_bytes', '12')]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                payload = catalog_payload()
                payload['entries'][0]['operation']['superseded_files'][0][field] = value
                with self.assertRaises(ModManagerError):
                    ModCatalog.from_payload(payload)

    def test_current_payload_cannot_be_declared_historical(self):
        for size_delta in [0, 1]:
            with self.subTest(size_delta=size_delta):
                payload = catalog_payload()
                operation = payload['entries'][0]['operation']
                duplicate = dict(operation['files'][0], path='FEATURE.dll')
                duplicate['size_bytes'] += size_delta
                operation['superseded_files'].append(duplicate)
                with self.assertRaises(ModManagerError):
                    ModCatalog.from_payload(payload)

    def _fixture(self, root, payload):
        game = root/'game'
        plugins = game/'BepInEx/plugins/history-fixture'
        plugins.mkdir(parents=True)
        exe = game/'LostCastle2.exe'
        exe.write_bytes(b'isolated test file; never executed')
        source = root/'source'
        source.mkdir()
        (source/'feature.dll').write_bytes(b'current feature')
        manager = ModManager(ModCatalog.from_payload(payload), root/'managed', root/'bundled', game_exe_provider=lambda: exe)
        return manager, plugins, source

    def test_either_history_variant_upgrades_and_current_survives_cleanup(self):
        for old in [b'old version one', b'old version two']:
            with self.subTest(old=old), tempfile.TemporaryDirectory(prefix='lc2-history-') as tmp:
                manager, plugins, source = self._fixture(Path(tmp), catalog_payload())
                target = plugins/'feature.dll'
                target.write_bytes(old)
                sibling = plugins/'unrelated.dll'
                sibling.write_bytes(b'keep')
                manager.install('history-fixture', source)
                self.assertEqual(target.read_bytes(), b'current feature')
                self.assertTrue(manager.status('history-fixture').installed)
                self.assertFalse(manager._remove_exact_superseded_files(manager.descriptor('history-fixture')))
                self.assertEqual(target.read_bytes(), b'current feature')
                self.assertEqual(sibling.read_bytes(), b'keep')

    def test_modified_current_path_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory(prefix='lc2-history-') as tmp:
            manager, plugins, source = self._fixture(Path(tmp), catalog_payload())
            target = plugins/'feature.dll'
            target.write_bytes(b'unknown modified bytes')
            with self.assertRaises(ModIntegrityError):
                manager.install('history-fixture', source)
            self.assertEqual(target.read_bytes(), b'unknown modified bytes')

    def test_retired_path_removes_only_matching_history_and_preserves_changed_bytes(self):
        for actual, removed in [(b'old version one', True), (b'old version two', True), (b'modified old', False)]:
            with self.subTest(actual=actual), tempfile.TemporaryDirectory(prefix='lc2-history-') as tmp:
                payload = catalog_payload()
                for spec in payload['entries'][0]['operation']['superseded_files']:
                    spec['path'] = 'retired.dll'
                manager, plugins, source = self._fixture(Path(tmp), payload)
                retired = plugins/'retired.dll'
                retired.write_bytes(actual)
                manager.install('history-fixture', source)
                self.assertEqual(retired.exists(), not removed)
                if not removed:
                    self.assertEqual(retired.read_bytes(), actual)
                    self.assertEqual(manager.status('history-fixture').state, 'integrity_error')
                else:
                    self.assertTrue(manager.status('history-fixture').installed)
                self.assertEqual((plugins/'feature.dll').read_bytes(), b'current feature')

    def test_wrong_declared_history_size_does_not_authorize_overwrite_or_cleanup(self):
        payload = catalog_payload()
        for spec in payload['entries'][0]['operation']['superseded_files']:
            spec['size_bytes'] += 1
        with tempfile.TemporaryDirectory(prefix='lc2-history-') as tmp:
            manager, plugins, source = self._fixture(Path(tmp), payload)
            target = plugins/'feature.dll'
            target.write_bytes(b'old version one')
            with self.assertRaises(ModIntegrityError):
                manager.install('history-fixture', source)
            self.assertFalse(manager._remove_exact_superseded_files(manager.descriptor('history-fixture')))
            self.assertEqual(target.read_bytes(), b'old version one')


if __name__ == '__main__':
    unittest.main()
