from __future__ import annotations

from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests.test_mod_sources import make_manager
from toolbox.app_shell import ToolboxShell
from toolbox.mod_manager import ModIntegrityError
from toolbox.support_diagnostics import SupportExport


class ImmediateThread:
    def __init__(self, *, target, **_kwargs):
        self.target = target

    def start(self):
        self.target()


class SupportUiTests(unittest.TestCase):
    def test_public_mod_picker_reaches_real_installer_and_records_source_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"good"})
            selected = root / "fixture.dll"
            selected.write_bytes(b"good")
            journal = []
            results = []
            shell = SimpleNamespace(
                root=None, _mod_busy=False, mod_manager=manager,
                _choose_mod_source=lambda _descriptor: selected,
                _record_support_event=lambda event, **details: journal.append((event, details)),
                ensure_game_runtime=lambda: True, _refresh_mod_page=lambda: None,
                _finish_mod_action=lambda success, error: results.append((success, error)),
            )
            with patch("toolbox.app_shell.messagebox.askyesno", return_value=True), patch("toolbox.app_shell.threading.Thread", ImmediateThread):
                ToolboxShell._configure_mod(shell, "fixture-plugin")
            self.assertEqual(results, [(True, None)])
            self.assertEqual(manager.installed_path("fixture-plugin").read_bytes(), b"good")
            self.assertFalse(journal[0][1]["bundled_source_found"])
            self.assertEqual(journal[1][1]["source_kind"], ".dll")
            self.assertEqual(journal[-1][0], "mod_install_complete")

    def test_wrong_source_reaches_specific_failure_and_keeps_original(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = make_manager(root, {"fixture.dll": b"good"})
            selected = root / "fixture.dll"
            selected.write_bytes(b"evil")
            results = []
            journal = []
            shell = SimpleNamespace(
                root=None, _mod_busy=False, mod_manager=manager,
                _choose_mod_source=lambda _descriptor: selected,
                _record_support_event=lambda event, **details: journal.append((event, details)),
                ensure_game_runtime=lambda: True, _refresh_mod_page=lambda: None,
                _finish_mod_action=lambda success, error: results.append((success, error)),
            )
            with patch("toolbox.app_shell.messagebox.askyesno", return_value=True), patch("toolbox.app_shell.threading.Thread", ImmediateThread):
                ToolboxShell._configure_mod(shell, "fixture-plugin")
            self.assertFalse(results[0][0])
            self.assertEqual(journal[-1][1]["code"], "source_hash_mismatch")
            self.assertIn("文件内容", ToolboxShell._mod_error_text(results[0][1]))
            self.assertEqual(selected.read_bytes(), b"evil")
            self.assertFalse(manager.installed_path("fixture-plugin").exists())

    def test_missing_member_and_multi_file_errors_do_not_claim_wrong_version(self) -> None:
        missing = ToolboxShell._mod_error_text(ModIntegrityError("missing", code="source_member_missing", path="panel.dll"))
        multi = ToolboxShell._mod_error_text(ModIntegrityError("multi", code="source_requires_package"))
        self.assertIn("panel.dll", missing)
        self.assertNotIn("版本不一致", missing)
        self.assertIn("多个文件", multi)
        self.assertNotIn("版本不一致", multi)

    def test_repeated_export_click_does_not_start_another_worker(self) -> None:
        shell = SimpleNamespace(support_exporter=object(), _support_export_busy=True)
        with patch("toolbox.app_shell.threading.Thread") as thread:
            ToolboxShell._export_support_diagnostics(shell)
            thread.assert_not_called()

    def test_partial_completion_restores_export_button_and_exposes_saved_file(self) -> None:
        results = queue.Queue()
        path = Path("report.zip")
        results.put(("progress", "读取日志"))
        results.put(("complete", SupportExport(path, True, 1)))
        shell = SimpleNamespace(
            _support_export_results=results, _support_export_busy=True,
            support_export_button=Mock(), _support_export_status=Mock(),
            _support_export_open=Mock(), last_support_export=None,
        )
        ToolboxShell._drain_support_export_results(shell)
        self.assertFalse(shell._support_export_busy)
        self.assertEqual(shell.last_support_export, path)
        shell.support_export_button.configure.assert_called_with(state="normal", text="导出诊断")
        self.assertIn("部分信息", shell._support_export_status.configure.call_args.kwargs["text"])
        shell._support_export_open.configure.assert_called_with(state="normal")

    def test_export_failure_releases_busy_state_for_retry(self) -> None:
        results = queue.Queue()
        results.put(("error", PermissionError("not writable")))
        shell = SimpleNamespace(
            _support_export_results=results, _support_export_busy=True,
            support_export_button=Mock(), _support_export_status=Mock(), _support_export_open=Mock(),
        )
        ToolboxShell._drain_support_export_results(shell)
        self.assertFalse(shell._support_export_busy)
        self.assertIn("未能保存", shell._support_export_status.configure.call_args.kwargs["text"])
        shell._support_export_open.configure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
