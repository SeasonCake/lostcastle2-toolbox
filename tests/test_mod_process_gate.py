from pathlib import Path
import tempfile
import unittest

from tests import test_mod_history as history
from toolbox.mod_manager import ModManagerError


class ModProcessGateTests(unittest.TestCase):
    def fixture(self, root, observations):
        manager, plugins, source = history.SamePathHistoryTests()._fixture(root, history.catalog_payload())
        calls = []
        def running(game):
            calls.append(game)
            value = next(observations)
            if isinstance(value, Exception):
                raise value
            return value
        manager.game_running_provider = running
        target = plugins / 'feature.dll'
        target.write_bytes(b'old version one')
        return manager, target, source, calls

    def test_running_unknown_or_second_observation_blocks_before_changes(self):
        for values in ((True,), (None,), (False, True), (False, RuntimeError('collector failed'))):
            with self.subTest(values=values), tempfile.TemporaryDirectory() as tmp:
                manager, target, source, calls = self.fixture(Path(tmp), iter(values))
                with self.assertRaises(ModManagerError):
                    manager.install('history-fixture', source)
                self.assertEqual(target.read_bytes(), b'old version one')
                self.assertFalse(target.with_name(target.name + '.installing').exists())

    def test_process_start_during_source_read_blocks_at_write_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager, target, source, calls = self.fixture(Path(tmp), iter((False, False, False, True)))
            with self.assertRaises(ModManagerError):
                manager.install('history-fixture', source)
            self.assertEqual(len(calls), 4)
            self.assertEqual(target.read_bytes(), b'old version one')

    def test_stopped_twice_allows_upgrade_and_uninstall_is_also_guarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager, target, source, calls = self.fixture(Path(tmp), iter((False, False, False, False, False, True)))
            manager.install('history-fixture', source)
            self.assertEqual(target.read_bytes(), b'current feature')
            with self.assertRaises(ModManagerError):
                manager.uninstall('history-fixture')
            self.assertEqual(target.read_bytes(), b'current feature')
            self.assertEqual(len(calls), 6)

    def test_uninstall_preserves_modified_current_dll_after_stopped_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager, target, source, calls = self.fixture(Path(tmp), iter((False, False)))
            target.write_bytes(b'user-edited current DLL')
            self.assertFalse(manager.uninstall('history-fixture'))
            self.assertEqual(target.read_bytes(), b'user-edited current DLL')


if __name__ == '__main__':
    unittest.main()
