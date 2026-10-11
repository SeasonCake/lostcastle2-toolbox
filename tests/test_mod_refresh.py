from pathlib import Path
from types import SimpleNamespace
import json
import queue
import tempfile
import threading
import unittest

from toolbox.app_shell import ToolboxShell
from toolbox.mod_manager import ModCatalog, ModManager, ModStatus
import tests.test_mod_manager as fixtures


class ResultQueue(queue.Queue):
    def __init__(self):
        super().__init__()
        self.ready = threading.Event()

    def put(self, value, *args, **kwargs):
        super().put(value, *args, **kwargs)
        self.ready.set()


class Tree:
    def __init__(self):
        self.rows = {key: [key, "1", "author", "待查看"] for key in ("a", "b")}

    def get_children(self, _parent=""):
        return tuple(self.rows)

    def item(self, key, option=None, **kwargs):
        if "values" in kwargs:
            self.rows[key] = kwargs["values"]
        return self.rows[key] if option == "values" else {"values": self.rows[key]}


class Reader:
    def __init__(self, manager, game):
        self.manager, self.game = manager, game
        self.catalog = manager.catalog
        self.installed = manager.installed
        self.fail = manager.fail

    def status(self, _mod_id):
        assert threading.get_ident() != self.manager.main_thread, "Full scan ran on the UI thread"
        self.manager.scanning.set()
        if not self.manager.release.wait(2):
            raise TimeoutError("Fixture worker was not released")
        if self.fail:
            raise OSError("Fixture unreadable directory")
        return ModStatus("installed" if self.installed and self.game == Path("game-a") else "not_installed", False, self.installed and self.game == Path("game-a"))


class Manager:
    def __init__(self, shell):
        self.shell = shell
        self.main_thread = threading.get_ident()
        self.scanning, self.release = threading.Event(), threading.Event()
        self.catalog = SimpleNamespace(entries=tuple(SimpleNamespace(mod_id=k, operation=SimpleNamespace(is_game_plugin=True)) for k in ("a", "b")))
        self.game_exe_provider = lambda: Path(shell.keyboard.settings["game_path"])
        self.installed, self.fail = False, False
        self.readers = []

    def status_reader(self, game):
        reader = Reader(self, game)
        self.readers.append(reader)
        return reader

    def descriptor(self, key):
        return next(e for e in self.catalog.entries if e.mod_id == key)


class ModRefreshTests(unittest.TestCase):
    def setUp(self):
        self.shell = ToolboxShell.__new__(ToolboxShell)
        s = self.shell
        s.keyboard = SimpleNamespace(settings={"game_path": "game-a"})
        s.mod_manager = Manager(s)
        s.mod_tree = Tree()
        s.current_page = "mods"
        s._mod_busy = s._closed = s._mod_scan_error = False
        s._mod_status_cache = {}
        s._mod_status_cache_time = 0.0
        s._mod_game_identity = s._mod_scan_job = s._mod_scan_reader = None
        s._mod_scan_generation = 0
        s._mod_scan_results = ResultQueue()
        self.count_text = {}
        s.mod_count_label = SimpleNamespace(configure=lambda **kw: self.count_text.update(kw))
        s._update_mod_detail = lambda: None
        s._filtered_mod_descriptors = lambda: s.mod_manager.catalog.entries
        s._populate_mod_tree = lambda: None

    def tearDown(self):
        self.shell.mod_manager.release.set()
        if self.shell._mod_scan_job is not None:
            self.shell._mod_scan_results.ready.wait(2)
        self.shell._closed = True

    def receive(self):
        self.assertTrue(self.shell._mod_scan_results.ready.wait(2))
        self.shell._mod_scan_results.ready.clear()
        self.shell._refresh_mod_page()

    def test_ui_returns_and_remains_callable_while_full_scan_is_blocked(self):
        self.shell.mod_manager.installed = True
        self.shell._refresh_mod_page()
        self.assertTrue(self.shell.mod_manager.scanning.wait(2))
        self.assertEqual(self.shell._mod_status_cache, {})
        self.shell._refresh_mod_page()
        self.assertEqual(len(self.shell.mod_manager.readers), 1)
        self.shell.mod_manager.release.set()
        self.receive()
        self.assertTrue(all(status.installed for status in self.shell._mod_status_cache.values()))
        self.assertEqual(self.shell.mod_tree.rows["a"][3], "已安装")

    def test_old_game_result_cannot_replace_new_directory_state(self):
        self.shell.mod_manager.installed = True
        self.shell._refresh_mod_page()
        self.assertTrue(self.shell.mod_manager.scanning.wait(2))
        self.shell.keyboard.settings["game_path"] = "game-b"
        self.shell._refresh_mod_page()
        self.shell.mod_manager.release.set()
        self.receive()
        self.assertEqual(self.shell._mod_status_cache, {})
        self.receive()
        self.assertFalse(any(status.installed for status in self.shell._mod_status_cache.values()))
        self.assertEqual([r.game for r in self.shell.mod_manager.readers], [Path("game-a"), Path("game-b")])

    def test_catalog_replacement_discards_in_flight_snapshot(self):
        self.shell._refresh_mod_page()
        self.assertTrue(self.shell.mod_manager.scanning.wait(2))
        self.shell.mod_manager.catalog = SimpleNamespace(entries=self.shell.mod_manager.catalog.entries)
        self.shell._refresh_mod_page()
        self.shell.mod_manager.release.set()
        self.receive()
        self.assertEqual(self.shell._mod_status_cache, {})
        self.receive()
        self.assertEqual(set(self.shell._mod_status_cache), {"a", "b"})

    def test_install_and_remove_invalidate_results_and_defer_scan_while_busy(self):
        for installed in (True, False):
            with self.subTest(installed=installed):
                self.shell.mod_manager.release.clear()
                self.shell.mod_manager.scanning.clear()
                self.shell._refresh_mod_page(force=True)
                self.assertTrue(self.shell.mod_manager.scanning.wait(2))
                self.shell._mod_busy = True
                self.shell.mod_manager.installed = installed
                self.shell._refresh_mod_page(force=True)
                self.shell.mod_manager.release.set()
                before = dict(self.shell._mod_status_cache)
                self.receive()
                self.assertEqual(self.shell._mod_status_cache, before)
                self.assertIsNone(self.shell._mod_scan_job)
                self.shell._mod_busy = False
                self.shell._refresh_mod_page(force=True)
                self.receive()
                self.assertEqual(self.shell._mod_status_cache["a"].installed, installed)

    def test_off_page_never_starts_status_scan(self):
        self.shell.current_page = "home"
        self.shell._refresh_mod_page(force=True)
        self.assertEqual(self.shell.mod_manager.readers, [])
        self.shell.current_page = "mods"
        self.shell.mod_manager.release.set()
        self.shell._refresh_mod_page()
        self.receive()
        self.assertEqual(len(self.shell.mod_manager.readers), 1)

    def test_worker_failure_is_reported_and_next_refresh_can_recover(self):
        self.shell.mod_manager.fail = True
        self.shell.mod_manager.release.set()
        self.shell._refresh_mod_page()
        self.receive()
        self.assertTrue(self.shell._mod_scan_error)
        self.assertIn("状态刷新失败", self.count_text["text"])
        self.assertIsNone(self.shell._mod_scan_job)
        self.shell.mod_manager.fail = False
        self.shell._refresh_mod_page(force=True)
        self.receive()
        self.assertFalse(self.shell._mod_scan_error)
        self.assertNotIn("失败", self.count_text["text"])

    def test_real_reader_freezes_game_path_without_sharing_hash_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            games = [root / name / "LostCastle2.exe" for name in ("a", "b")]
            for game in games:
                game.parent.mkdir()
                game.write_bytes(b"fixture; never execute")
                (game.parent / "BepInEx").mkdir()
            content = b"exact plugin fixture"
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps(fixtures.plugin_catalog_payload(content)), encoding="utf-8")
            selected = [games[0]]
            manager = ModManager(ModCatalog.from_file(catalog_path), root / "managed", root / "bundled", lambda: selected[0])
            target = manager.installed_path("fixture-plugin")
            target.parent.mkdir(parents=True)
            target.write_bytes(content)
            reader = manager.status_reader(games[0])
            selected[0] = games[1]
            self.assertTrue(reader.status("fixture-plugin").installed)
            self.assertFalse(manager.status("fixture-plugin").installed)
            self.assertIsNot(reader._hash_cache, manager._hash_cache)


if __name__ == "__main__":
    unittest.main()
