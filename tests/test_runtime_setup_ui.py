from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import keyview
from tests.test_runtime_setup import runtime_fixture
from toolbox.runtime_setup import RuntimeSetupManager


class ImmediateThread:
    def __init__(self, *, target, **_kwargs):
        self.target = target

    def start(self):
        self.target()


class RuntimeSetupUiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        manifest, bundle, self.expected = runtime_fixture(self.directory)
        self.game = self.directory / 'game/LostCastle2.exe'
        self.game.parent.mkdir()
        self.game.write_bytes(b'isolated fixture, never executed')
        self.manager = RuntimeSetupManager(manifest, bundle, lambda:self.game, backup_root=self.directory/'backups')
        self.root = Mock()
        self.journal = Mock()
        self.stack = self.enterContext(ExitStack())
        self.ask = self.stack.enter_context(patch.object(keyview.messagebox,'askyesno',return_value=False))
        self.error = self.stack.enter_context(patch.object(keyview.messagebox,'showerror'))
        self.info = self.stack.enter_context(patch.object(keyview.messagebox,'showinfo'))
        for name in ('Toplevel','Label','BooleanVar'):
            self.stack.enter_context(patch.object(keyview.tk,name))
        self.stack.enter_context(patch.object(keyview.ttk,'Progressbar'))
        self.stack.enter_context(patch.object(keyview.threading,'Thread',ImmediateThread))

    def existing_runtime(self):
        self.manager.install()
        self.core = self.game.parent/'BepInEx/core/BepInEx.Core.dll'
        self.il2cpp = self.game.parent/'BepInEx/core/BepInEx.Unity.IL2CPP.dll'
        self.core.write_bytes(b'preinstalled other BepInEx core')
        self.il2cpp.write_bytes(b'preinstalled other IL2CPP loader')
        self.user_mod = self.game.parent/'BepInEx/plugins/user/keep.dll'
        self.user_mod.parent.mkdir(parents=True)
        self.user_mod.write_bytes(b'user mod')
        self.config = self.game.parent/'BepInEx/config/user.cfg'
        self.config.write_text('[User]\nValue = keep\n',encoding='utf-8')

    def run_action(self):
        return keyview.ensure_runtime_for_action(self.root,self.manager,self.journal)

    def test_other_bepinex_is_replaced_without_another_confirmation(self):
        self.existing_runtime()
        self.assertTrue(self.run_action())
        self.ask.assert_not_called()
        self.error.assert_not_called()
        self.assertEqual(self.core.read_bytes(),self.expected['BepInEx/core/BepInEx.Core.dll'])
        self.assertEqual(self.il2cpp.read_bytes(),self.expected['BepInEx/core/BepInEx.Unity.IL2CPP.dll'])
        backup = self.manager.last_backup_path
        self.assertEqual((backup/'original/BepInEx/core/BepInEx.Core.dll').read_bytes(),b'preinstalled other BepInEx core')
        self.assertEqual(self.user_mod.read_bytes(),b'user mod')
        self.assertEqual(self.config.read_text(encoding='utf-8'),'[User]\nValue = keep\n')
        self.assertEqual(json.loads((backup/'manifest.json').read_text(encoding='utf-8'))['state'],'complete')

    def test_running_or_unknown_game_does_not_replace_existing_files(self):
        self.existing_runtime()
        for running in (True,None):
            with self.subTest(running=running):
                self.manager.game_running_provider = lambda _path:running
                self.assertFalse(self.run_action())
                self.assertEqual(self.core.read_bytes(),b'preinstalled other BepInEx core')
                self.assertFalse((self.directory/'backups').exists())
        self.ask.assert_not_called()
        self.info.assert_not_called()
        self.assertEqual(self.error.call_count,2)

    def test_automatic_update_write_error_restores_original_and_reports_failure(self):
        self.existing_runtime()
        writer = self.manager._write_atomic
        failed = False
        def fail_once(path,content):
            nonlocal failed
            if path == self.il2cpp and not failed:
                failed = True
                raise OSError('isolated write failure')
            writer(path,content)
        with patch.object(self.manager,'_write_atomic',side_effect=fail_once):
            self.assertFalse(self.run_action())
        self.ask.assert_not_called()
        self.info.assert_not_called()
        self.error.assert_called_once()
        self.assertIn('已恢复原文件',self.error.call_args.args[1])
        self.assertEqual(self.core.read_bytes(),b'preinstalled other BepInEx core')
        self.assertEqual(self.il2cpp.read_bytes(),b'preinstalled other IL2CPP loader')

    def test_ready_runtime_continues_without_writes_or_prompts(self):
        self.manager.install()
        with patch.object(self.manager,'install',wraps=self.manager.install) as install:
            self.assertTrue(self.run_action())
        install.assert_not_called()
        self.ask.assert_not_called()
        self.info.assert_not_called()

    def test_fresh_initialization_retains_existing_opt_in(self):
        self.assertFalse(self.run_action())
        self.ask.assert_called_once()
        self.assertEqual(self.ask.call_args.args[0],'首次初始化')
        self.assertEqual(list(self.game.parent.iterdir()),[self.game])
        self.info.assert_not_called()

    def test_accepted_fresh_initialization_still_installs(self):
        self.ask.return_value = True
        self.assertTrue(self.run_action())
        self.ask.assert_called_once()
        self.error.assert_not_called()
        self.assertTrue(self.manager.status().ready)


if __name__ == '__main__':
    unittest.main()
