from types import SimpleNamespace
from unittest.mock import Mock
import ctypes
import os
import tkinter as tk
import unittest

import keyview
from toolbox.app_shell import CombatHudWindow, ToolboxShell, responsive_pair
from toolbox.combat_aggregator import CombatAggregator
from toolbox.game_features import DemoGameFeatureService, FeatureSnapshot
from toolbox.team_mini_ui import TeamMiniWindow


class TeamMiniTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.tk_errors = []
        self.root.report_callback_exception = lambda _kind, error, _trace: self.tk_errors.append(str(error))
        self.root.withdraw()
        self.service = DemoGameFeatureService()
        self.changed = Mock()
        self.mini = TeamMiniWindow(self.root, self.service, lambda:42, self.enable, self.changed)

    def enable(self):
        self.service.set_enabled('team_enabled', not self.service.settings()['team_enabled'])

    def tearDown(self):
        self.mini.close()
        self.root.destroy()
        self.assertFalse(self.tk_errors)

    def test_open_hide_reopen_is_independent_of_reading_and_preserves_selected_member(self):
        self.assertFalse(self.mini.is_visible())
        self.mini.toggle()
        self.root.update()
        self.assertTrue(self.mini.is_visible())
        self.assertFalse(self.service.settings()['team_enabled'])
        self.assertFalse(self.mini._team)
        self.mini.enable_button.invoke()
        self.assertEqual(self.mini.selected_slot, 1)
        self.mini.toggle()
        self.assertFalse(self.mini.is_visible())
        self.assertTrue(self.service.settings()['team_enabled'])
        self.mini.toggle()
        self.assertEqual(self.mini.selected_slot, 1)
        self.assertIn('一位很长名字', self.mini.members.cget('text'))
        self.changed.assert_called_with(True)

    def test_known_zero_unknown_resource_and_full_item_description_remain_distinct(self):
        self.enable()
        self.mini.toggle()
        self.root.update()
        self.mini.previous_member.invoke()
        self.assertIn('金币 0', self.mini.resources.cget('text'))
        item = self.mini.inventory.get_children('inscription-0')[0]
        self.mini.inventory.selection_set(item)
        self.mini._select_item()
        self.assertIn('攻击力提升 / 生命上限提升', self.mini.item_detail.cget('text'))
        self.mini.next_member.invoke()
        self.assertIn('金币 未同步', self.mini.resources.cget('text'))
        self.assertNotIn('金币 0', self.mini.resources.cget('text'))

    def test_refresh_keeps_tree_context_then_discards_stale_data_and_recovers(self):
        self.enable()
        self.mini.toggle()
        self.root.update()
        self.mini.previous_member.invoke()
        self.mini.inventory.item('bag', open=False)
        self.mini.refresh()
        self.assertFalse(self.mini.inventory.item('bag', 'open'))
        snapshot = self.service.snapshot
        self.service.snapshot = lambda _pid: FeatureSnapshot('stale', '数据暂未更新')
        self.mini.refresh()
        self.assertFalse(self.mini.inventory.get_children())
        self.assertEqual(self.mini.members.cget('text'), '等待队伍数据')
        self.assertNotIn('256', self.mini.vitals.cget('text'))
        self.service.snapshot = snapshot
        self.mini.refresh()
        self.assertTrue(self.mini.inventory.get_children())
        self.assertIn('95', self.mini.vitals.cget('text'))

    def test_hud_starts_automatically_unless_explicitly_hidden_for_preview(self):
        self.assertTrue(keyview.parse_args([]).show_combat_hud)
        self.assertFalse(keyview.parse_args(['--hide-combat-hud-on-start']).show_combat_hud)

    def test_compact_translucent_mini_does_not_map_or_activate_its_main_owner(self):
        # The toolbox has displayed its main window on startup before the
        # player returns to the game or minimizes it and uses the HUD.
        self.root.deiconify()
        self.root.update()
        self.root.withdraw()
        self.root.update()
        def assert_no_focus_theft(before):
            after = keyview.user32.GetForegroundWindow()
            if after != before:
                pid = keyview.wintypes.DWORD()
                keyview.user32.GetWindowThreadProcessId(after, ctypes.byref(pid))
                # Other user-owned windows may change during the test; the
                # overlay must never become the foreground process itself.
                self.assertNotEqual(pid.value, os.getpid(), (before, after, pid.value))
        before = keyview.user32.GetForegroundWindow()
        self.mini.toggle()
        self.root.update()
        assert_no_focus_theft(before)

        self.assertEqual(self.root.state(), 'withdrawn')
        self.assertAlmostEqual(float(self.mini.window.attributes('-alpha')), .86, places=2)
        self.assertLessEqual(self.mini.window.winfo_width(), round(300*self.mini._dpi/96))
        self.assertLessEqual(self.mini.window.winfo_height(), round(320*self.mini._dpi/96))
        hwnd = int(keyview.user32.GetAncestor(self.mini.window.winfo_id(), 2))
        self.assertTrue(keyview.user32.GetWindowLongW(hwnd, -20) & 0x08000000)
        self.mini.hide()
        self.root.update()
        assert_no_focus_theft(before)
        self.mini.toggle()
        self.root.update()
        assert_no_focus_theft(before)

    def test_locked_mini_passes_mouse_through_and_hud_reopen_restores_controls(self):
        self.mini.toggle()
        self.mini.lock_button.invoke()
        hwnd = int(keyview.user32.GetAncestor(self.mini.window.winfo_id(), 2))
        self.assertTrue(keyview.user32.GetWindowLongW(hwnd, -20) & 0x20)
        self.mini.toggle()
        self.mini.toggle()
        self.assertFalse(keyview.user32.GetWindowLongW(hwnd, -20) & 0x20)
        self.assertTrue(keyview.user32.GetWindowLongW(hwnd, -20) & 0x08000000)

    def test_controller_updates_visible_team_data_without_switching_main_pages(self):
        self.enable()
        self.mini.toggle()
        self.root.update()
        self.assertIn('95', self.mini.vitals.cget('text'))
        original = self.service.snapshot
        def changed_snapshot(pid):
            snapshot = original(pid)
            team = tuple(dict(player, hp=67) if player['slot']==1 else player for player in snapshot.team)
            return FeatureSnapshot(snapshot.state, snapshot.detail, team, snapshot.loadout, snapshot.captured_at)
        self.service.snapshot = changed_snapshot
        shell = ToolboxShell.__new__(ToolboxShell)
        for name in ('_refresh_module_statuses','_refresh_combat','_refresh_macro_rows','_refresh_mod_page','_refresh_display_settings','_draw_keyboard_preview'):
            setattr(shell,name,lambda:None)
        shell.hud = SimpleNamespace(refresh=lambda:None)
        shell.feature_pages = None
        shell.team_mini = self.mini
        ToolboxShell.refresh(shell)
        self.assertIn('67', self.mini.vitals.cget('text'))

    def test_hud_team_and_toolbox_buttons_control_different_windows(self):
        self.root.deiconify()
        self.root.update()
        shell = ToolboxShell.__new__(ToolboxShell)
        shell.root = self.root
        shell.team_mini = self.mini
        hud = CombatHudWindow(self.root,CombatAggregator(),toggle_team_mini=lambda:ToolboxShell._toggle_team_mini(shell),show_toolbox=lambda:ToolboxShell._show_toolbox(shell))
        shell.hud = hud
        try:
            hud.show()
            self.root.update()
            self.root.iconify()
            self.root.update()
            hud.team_mini_button.invoke()
            self.root.update()
            self.assertTrue(self.mini.is_visible())
            self.assertEqual(self.root.state(),'iconic')
            hud.team_mini_button.invoke()
            self.root.update()
            self.assertFalse(self.mini.is_visible())
            self.assertEqual(self.root.state(),'iconic')
            buttons = [widget for widget in ToolboxShell._walk_widgets(hud.window) if isinstance(widget,tk.Button) and widget.cget('text')=='盒子']
            self.assertEqual(len(buttons),1)
            buttons[0].invoke()
            self.root.update()
            self.assertEqual(self.root.state(),'normal')
        finally:
            hud.close()

    def test_small_control_row_stacks_copy_and_wraps_actions_without_clipping_values(self):
        self.root.deiconify()
        self.root.geometry('340x300')
        row = tk.Frame(self.root)
        row.pack(fill='x')
        copy = tk.Frame(row)
        label = tk.Label(copy, text='字号与按钮 115% · 显示器 150%', font=('Microsoft YaHei UI', 12))
        label.pack()
        controls = tk.Frame(row)
        for text in ('缩小', '默认', '放大', '恢复拖动'):
            tk.Button(controls, text=text, font=('Microsoft YaHei UI', 12), width=8).pack(side='left')
        responsive_pair(row, copy, controls, wrap_controls=True)
        self.root.update()
        self.assertGreater(controls.winfo_y(), copy.winfo_y(), (self.root.winfo_width(), row.winfo_width(), copy.winfo_reqwidth(), controls.winfo_reqwidth(), copy.grid_info(), controls.grid_info()))
        self.assertGreaterEqual(label.winfo_width(), label.winfo_reqwidth())
        for button in controls.winfo_children():
            self.assertLessEqual(button.winfo_x()+button.winfo_width(), controls.winfo_width())
        self.root.geometry('1600x300')
        self.root.update()
        self.assertEqual(controls.grid_info()['row'], copy.grid_info()['row'])


if __name__ == '__main__':
    unittest.main()
