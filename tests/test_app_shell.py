from __future__ import annotations

import inspect
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from pathlib import Path

from toolbox.app_shell import (
    COMBAT_ROUNDING_HINT,
    DEFAULT_TOOLBOX_WINDOW_PRESET,
    GOLD,
    GREEN,
    TOOLBOX_WINDOW_PRESETS,
    TOOLBOX_UI_SCALES,
    TOOLBOX_REPOSITORY_URL,
    TOOLBOX_BILIBILI_URL,
    SUPPORT_LABEL,
    SUPPORT_NOTE,
    SUPPORT_QR_FILENAME,
    TAKEN_DAMAGE_LABEL,
    ToolboxShell,
    boss_damage_share,
    clamp_main_window_size,
    combat_state_label,
    combat_teammate_rows,
    combat_team_rows,
    combat_uses_personal_scope,
    combat_hud_size,
    combat_hud_initial_position,
    combat_personal_share,
    combat_status_presentation,
    combat_team_grid_layout,
    combat_table_source_width,
    combat_table_numeric_width,
    format_location_label,
    format_metric,
    format_whole_metric,
    format_room_area,
    format_stage_location,
    macro_rows,
    metric_font_size,
    hud_panel_height,
    hud_recent_panel_height,
    hud_teammate_card_height,
    main_metric_card_height,
    main_team_panel_height,
    main_window_min_size,
    mod_tree_column_widths,
    mod_launch_action,
    ordered_keyboard_keys,
    seed_demo_combat,
    toolbox_author_label,
)
from toolbox.combat_aggregator import CombatAggregator, ScenarioRegistry, SourceRegistry
from toolbox.macro_config import default_profile_data
from toolbox.macro_model import parse_macro_profile


class AppShellModelTests(unittest.TestCase):
    def test_header_has_no_test_only_manual_export_control(self) -> None:
        constructor = inspect.getsource(ToolboxShell.__init__)
        header_builder = inspect.getsource(ToolboxShell._build)
        self.assertNotIn("combat_archiver", constructor)
        self.assertNotIn("archive_button", constructor)
        self.assertNotIn("手动导出", header_builder)
        self.assertFalse(hasattr(ToolboxShell, "_manual_export"))

    def test_main_combat_page_explains_final_rounding_without_claiming_an_error(self) -> None:
        self.assertIn("底层小数累计", COMBAT_ROUNDING_HINT)
        self.assertIn("界面最终取整", COMBAT_ROUNDING_HINT)
        self.assertIn("少量差异", COMBAT_ROUNDING_HINT)
        self.assertNotIn("漏记", COMBAT_ROUNDING_HINT)
        self.assertNotIn("异常", COMBAT_ROUNDING_HINT)

    def test_public_taken_damage_label_uses_player_facing_language(self) -> None:
        self.assertEqual(TAKEN_DAMAGE_LABEL, "受击承伤")

    def test_toolbox_attribution_and_repository_action_are_stable(self) -> None:
        self.assertEqual(toolbox_author_label(), "作者：加菲_barista")
        shell = SimpleNamespace(root=None)
        with patch("toolbox.app_shell.webbrowser.open", return_value=True) as opener:
            ToolboxShell._open_repository(shell)
        opener.assert_called_once_with(TOOLBOX_REPOSITORY_URL, new=2)
        with patch("toolbox.app_shell.webbrowser.open", return_value=True) as opener:
            ToolboxShell._open_bilibili(shell)
        opener.assert_called_once_with(TOOLBOX_BILIBILI_URL, new=2)

    def test_support_entry_keeps_the_product_free_and_opens_local_assets(self) -> None:
        self.assertEqual(SUPPORT_LABEL, "投喂")
        self.assertIn("喜欢《失落城堡2》", SUPPORT_NOTE)
        self.assertIn("自愿", SUPPORT_NOTE)
        self.assertNotIn("解锁", SUPPORT_NOTE)
        self.assertNotIn("token", SUPPORT_NOTE)
        self.assertNotIn("订阅", SUPPORT_NOTE)
        self.assertNotIn("续费", SUPPORT_NOTE)
        self.assertEqual(SUPPORT_QR_FILENAME, "微信赞助码.png")
        with tempfile.TemporaryDirectory() as temp_dir:
            support_directory = Path(temp_dir) / "赞助与投喂"
            support_directory.mkdir()
            shell = SimpleNamespace(support_directory=support_directory, root=None)
            with patch("toolbox.app_shell.os.startfile") as starter:
                ToolboxShell._open_support_directory(shell)
            starter.assert_called_once_with(str(support_directory.resolve()))

    def test_game_loaded_mod_launch_reuses_existing_game_launcher(self) -> None:
        actions: list[str] = []
        shell = SimpleNamespace(
            mod_manager=SimpleNamespace(
                status=lambda _mod_id: SimpleNamespace(installed=True)
            ),
            launch_game=lambda: actions.append("launch_game"),
        )
        ToolboxShell._launch_game_for_mod(shell, "gold-editor-f5")
        self.assertEqual(actions, ["launch_game"])

        shell.mod_manager.status = lambda _mod_id: SimpleNamespace(installed=False)
        ToolboxShell._launch_game_for_mod(shell, "gold-editor-f5")
        self.assertEqual(actions, ["launch_game"])

    def test_ready_mod_panel_action_focuses_game_and_sends_declared_hotkey(self) -> None:
        actions: list[str] = []
        operation = SimpleNamespace(
            launchable=False,
            has_game_panel=True,
            panel_hotkey="INS",
        )
        descriptor = SimpleNamespace(operation=operation)
        manager = SimpleNamespace(
            descriptor=lambda _mod_id: descriptor,
            status=lambda _mod_id: SimpleNamespace(installed=True),
            installed_mtime_ns=lambda _mod_id: 50,
        )
        keyboard = SimpleNamespace(
            game_process_id=42,
            game_process_started_ns=100,
            open_game_panel_hotkey=lambda key: actions.append(key) or True,
        )
        shell = SimpleNamespace(
            mod_manager=manager,
            keyboard=keyboard,
            _mod_busy=False,
            root=None,
        )
        with patch("toolbox.app_shell.messagebox.showerror") as showerror:
            ToolboxShell._launch_selected_mod(shell, "fixture")
        self.assertEqual(actions, ["INS"])
        showerror.assert_not_called()

    def test_mod_panel_action_explains_install_and_restart_requirements(self) -> None:
        operation = SimpleNamespace(
            launchable=False,
            has_game_panel=True,
            panel_hotkey="INS",
        )
        descriptor = SimpleNamespace(operation=operation)
        status = SimpleNamespace(installed=False)
        manager = SimpleNamespace(
            descriptor=lambda _mod_id: descriptor,
            status=lambda _mod_id: status,
            installed_mtime_ns=lambda _mod_id: 150,
        )
        keyboard = SimpleNamespace(
            game_process_id=None,
            game_process_started_ns=None,
            open_game_panel_hotkey=lambda _key: False,
        )
        shell = SimpleNamespace(
            mod_manager=manager,
            keyboard=keyboard,
            _mod_busy=False,
            root=None,
        )
        with patch("toolbox.app_shell.messagebox.showinfo") as showinfo:
            ToolboxShell._launch_selected_mod(shell, "fixture")
        self.assertIn("先安装", showinfo.call_args.args[0])

        status.installed = True
        keyboard.game_process_id = 42
        keyboard.game_process_started_ns = 100
        with patch("toolbox.app_shell.messagebox.showinfo") as showinfo:
            ToolboxShell._launch_selected_mod(shell, "fixture")
        self.assertIn("重启游戏", showinfo.call_args.args[0])

    def test_demo_combat_state_is_deterministic_and_complete_for_ui_qa(self) -> None:
        root = Path(__file__).resolve().parents[1]
        aggregator = CombatAggregator(
            registry=SourceRegistry.from_file(root / "assets" / "combat_sources.json"),
            scenario_registry=ScenarioRegistry.from_file(
                root / "assets" / "game_locations.json"
            ),
        )
        seed_demo_combat(aggregator)
        snapshot = aggregator.snapshot()
        self.assertEqual(snapshot.connection_state, "live")
        self.assertEqual(snapshot.current_room_id, "L2:MudSwamp:4:Demo_MudSwamp_4")
        self.assertEqual(snapshot.current_stage_level, 2)
        self.assertEqual(snapshot.current_scenario_id, "MudSwamp")
        self.assertEqual(snapshot.current_scenario_label, "泥鱼沼泽")
        self.assertEqual(snapshot.current_room_index, 4)
        self.assertEqual(snapshot.current_map_file_name, "Demo_MudSwamp_4")
        self.assertEqual(format_location_label(snapshot), "泥鱼沼泽 · 第 4 区")
        self.assertEqual(format_stage_location(snapshot), "第 2 阶段 · 泥鱼沼泽 · 第 4 区")
        self.assertEqual(snapshot.total_damage, 34_328)
        self.assertEqual(snapshot.boss_damage, 8_940)
        self.assertEqual(snapshot.personal_damage, 34_328)
        self.assertEqual(snapshot.personal_boss_damage, 8_940)
        self.assertFalse(combat_uses_personal_scope(snapshot))
        self.assertEqual(snapshot.taken_settlement_damage, 264)
        self.assertEqual(snapshot.hp_damage_taken, 183)
        self.assertEqual(snapshot.hp_loss_other, 18)
        self.assertEqual(snapshot.effective_healing, 94)
        self.assertEqual(snapshot.mp_spent, 168)
        self.assertEqual(snapshot.mp_gained, 140)
        self.assertEqual(snapshot.detected_player_count, 1)

    def test_demo_multiplayer_rows_are_conditional_private_and_complete(self) -> None:
        root = Path(__file__).resolve().parents[1]
        aggregator = CombatAggregator(
            registry=SourceRegistry.from_file(root / "assets" / "combat_sources.json"),
            scenario_registry=ScenarioRegistry.from_file(
                root / "assets" / "game_locations.json"
            ),
        )
        seed_demo_combat(aggregator, party_size=4)
        snapshot = aggregator.snapshot()
        rows = combat_team_rows(snapshot)
        self.assertEqual(snapshot.detected_player_count, 4)
        self.assertTrue(combat_uses_personal_scope(snapshot))
        self.assertEqual(snapshot.personal_damage, rows[0][1])
        self.assertLess(snapshot.personal_damage, snapshot.total_damage)
        self.assertAlmostEqual(
            combat_personal_share(snapshot),
            snapshot.personal_damage / snapshot.total_damage,
        )
        self.assertEqual([row[0] for row in rows], ["自己 · P1", "P2", "P3", "P4"])
        self.assertEqual(sum(row[1] for row in rows), snapshot.total_damage)
        self.assertAlmostEqual(sum(row[3] for row in rows), 1.0)
        self.assertNotIn("demo-player", str(rows))
        teammates = combat_teammate_rows(snapshot)
        self.assertEqual([row[0] for row in teammates], ["P2", "P3", "P4"])

    def test_demo_client_slot_is_still_rendered_as_self(self) -> None:
        root = Path(__file__).resolve().parents[1]
        aggregator = CombatAggregator(
            registry=SourceRegistry.from_file(root / "assets" / "combat_sources.json"),
            scenario_registry=ScenarioRegistry.from_file(
                root / "assets" / "game_locations.json"
            ),
        )
        seed_demo_combat(aggregator, party_size=4, local_player_slot=2)
        snapshot = aggregator.snapshot()
        rows = combat_team_rows(snapshot)
        self.assertEqual(rows[0][0], "自己 · P3")
        local_rows = [
            values
            for values in snapshot.player_breakdown.values()
            if values["is_local"]
        ]
        self.assertEqual(len(local_rows), 1)
        self.assertEqual(local_rows[0]["player_slot"], 2)
        self.assertEqual(snapshot.personal_damage, local_rows[0]["damage_dealt"])

    def test_demo_sixteen_player_hud_keeps_three_rows_per_column(self) -> None:
        root = Path(__file__).resolve().parents[1]
        aggregator = CombatAggregator(
            registry=SourceRegistry.from_file(root / "assets" / "combat_sources.json"),
            scenario_registry=ScenarioRegistry.from_file(
                root / "assets" / "game_locations.json"
            ),
        )
        seed_demo_combat(aggregator, party_size=16, local_player_slot=12)
        snapshot = aggregator.snapshot()
        teammates = combat_teammate_rows(snapshot)
        main_rows = combat_team_rows(snapshot, maximum=16)
        self.assertEqual(snapshot.detected_player_count, 16)
        self.assertEqual(len(teammates), 15)
        self.assertEqual(len(main_rows), 16)
        self.assertEqual(main_rows[0][0], "自己 · P13")
        self.assertEqual(
            [row[0] for row in teammates],
            [
                *[f"P{index}" for index in range(1, 13)],
                "P14",
                "P15",
                "P16",
            ],
        )

    def test_main_team_panel_scrolls_horizontally_after_four_players(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "toolbox" / "app_shell.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('orient="horizontal"', source)
        self.assertIn("maximum=MAX_PARTY_MEMBERS", source)
        self.assertIn("self.combat_team_canvas.xview", source)
        self.assertIn("needs_scroll = combat_team_grid_layout(", source)

        self.assertEqual(
            combat_team_grid_layout(4, 560, 1.15),
            (172, 688, True),
        )
        self.assertEqual(
            combat_team_grid_layout(2, 560, 1.15),
            (172, 688, False),
        )
        self.assertEqual(
            combat_team_grid_layout(4, 800, 1.15),
            (200, 800, False),
        )
        self.assertEqual(
            combat_team_grid_layout(5, 800, 1.15),
            (200, 1_000, True),
        )

    def test_demo_degraded_state_remains_live_and_explicit(self) -> None:
        root = Path(__file__).resolve().parents[1]
        aggregator = CombatAggregator(
            registry=SourceRegistry.from_file(root / "assets" / "combat_sources.json"),
            scenario_registry=ScenarioRegistry.from_file(
                root / "assets" / "game_locations.json"
            ),
        )
        seed_demo_combat(
            aggregator,
            party_size=4,
            local_player_slot=2,
            diagnostic_warning="damage_snapshot_missing",
        )
        snapshot = aggregator.snapshot()
        self.assertEqual(snapshot.connection_state, "live")
        self.assertEqual(
            snapshot.diagnostic_warning,
            "degraded:damage_snapshot_missing",
        )

    def test_keyboard_preview_order_follows_geometry_not_selection_order(self) -> None:
        shuffled = (
            ("D", "D", (203, 156, 66, 64)),
            ("W", "W", (127, 84, 66, 64)),
            ("A", "A", (51, 156, 66, 64)),
            ("S", "S", (127, 156, 66, 64)),
            ("SPACE", "SPACE", (166, 228, 268, 64)),
        )
        self.assertEqual(
            ordered_keyboard_keys(shuffled),
            ("W", "A", "S", "D", "SPACE"),
        )
        self.assertEqual(
            ordered_keyboard_keys(reversed(shuffled)),
            ("W", "A", "S", "D", "SPACE"),
        )

    def test_macro_rows_keep_a_fixed_reading_order_and_full_description(self) -> None:
        profiles = tuple(parse_macro_profile(item) for item in default_profile_data())
        rows = macro_rows(profiles)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].enabled_label, "已停用")
        self.assertEqual(rows[0].trigger, "F5")
        self.assertEqual(rows[0].mode, "单次")
        self.assertIn(rows[0].name, rows[0].description)
        self.assertIn("最长", rows[0].description)

    def test_metric_format_handles_zero_large_and_fractional_values(self) -> None:
        self.assertEqual(format_metric(0), "0")
        self.assertEqual(format_metric(34_328), "34,328")
        self.assertEqual(format_metric(1.25), "1.2")
        self.assertEqual(format_whole_metric(52.8), "53")
        self.assertEqual(format_whole_metric(15.8), "16")

    def test_room_area_uses_game_special_indices(self) -> None:
        self.assertEqual(format_room_area(0), "入口")
        self.assertEqual(format_room_area(4), "第 4 区")
        self.assertEqual(format_room_area(99), "首领前区域")
        self.assertEqual(format_room_area(100), "BOSS 区域")
        self.assertEqual(format_room_area(101), "准备区")

    def test_metric_font_size_shrinks_for_million_scale_values(self) -> None:
        self.assertEqual(
            metric_font_size("34,328", base_size=19, characters_at_base=7),
            19,
        )
        million_size = metric_font_size(
            "34,328,000",
            base_size=19,
            characters_at_base=7,
        )
        self.assertLess(million_size, 19)
        self.assertGreaterEqual(million_size, 10)

    def test_boss_damage_share_is_safe_for_empty_and_inconsistent_data(self) -> None:
        self.assertEqual(boss_damage_share(0, 0), 0.0)
        self.assertAlmostEqual(boss_damage_share(34_328, 8_940), 8_940 / 34_328)
        self.assertEqual(boss_damage_share(100, 140), 1.0)
        self.assertEqual(boss_damage_share(100, -5), 0.0)

    def test_combat_connection_states_remain_distinct(self) -> None:
        self.assertEqual(combat_state_label("live", compact=True), "● 实时")
        self.assertEqual(combat_state_label("live"), "● 实时估算")
        self.assertEqual(combat_state_label("connecting"), "● 正在连接战斗桥接")
        self.assertIn("异常", combat_state_label("error"))
        self.assertNotEqual(combat_state_label("stale"), combat_state_label("disconnected"))

    @staticmethod
    def _combat_status_snapshot(
        *,
        state: str = "live",
        damage: int = 0,
        boss_damage: int = 0,
        official_damage_complete: bool = False,
        official_boss_damage_complete: bool = False,
        degraded: bool = False,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            connection_state=state,
            diagnostic_warning="degraded:event_gap" if degraded else None,
            official_damage_complete=official_damage_complete,
            official_boss_damage_complete=official_boss_damage_complete,
            personal_damage=damage,
            personal_boss_damage=boss_damage,
        )

    def test_live_damage_is_an_amber_estimate_for_zero_and_large_values(self) -> None:
        for damage, boss_damage in ((0, 0), (11_057_093, 4_000_000)):
            with self.subTest(damage=damage):
                snapshot = self._combat_status_snapshot(
                    damage=damage,
                    boss_damage=boss_damage,
                )
                full = combat_status_presentation(snapshot)
                compact = combat_status_presentation(snapshot, compact=True)
                self.assertEqual(full.kind, "estimate")
                self.assertEqual(full.label, "● 实时估算")
                self.assertEqual(full.explanation, "结算可能校正")
                self.assertEqual(full.color, GOLD)
                self.assertEqual(
                    format_metric(snapshot.personal_damage),
                    f"{damage:,}",
                )
                self.assertEqual(compact.label, "● 实时")
                self.assertEqual(compact.explanation, "")
                self.assertEqual(compact.color, GREEN)
                self.assertNotIn("结算可能校正", compact.text)

    def test_complete_official_values_win_for_upward_and_downward_finals(self) -> None:
        corrections = (
            (11_057_093, 10_440_726),
            (8_520_510, 8_829_890),
        )
        for live_damage, final_damage in corrections:
            with self.subTest(live=live_damage, final=final_damage):
                live = self._combat_status_snapshot(damage=live_damage)
                final = self._combat_status_snapshot(
                    state="ended",
                    damage=final_damage,
                    official_damage_complete=True,
                    official_boss_damage_complete=True,
                )
                self.assertEqual(combat_status_presentation(live).kind, "estimate")
                official = combat_status_presentation(final)
                self.assertEqual(official.kind, "official")
                self.assertEqual(official.text, "● 官方结算")
                self.assertEqual(official.color, GREEN)
                self.assertEqual(format_metric(final.personal_damage), f"{final_damage:,}")
                self.assertEqual(
                    combat_status_presentation(final, compact=True).text,
                    "● 官方",
                )

        partial = self._combat_status_snapshot(
            damage=10_440_726,
            official_damage_complete=True,
            official_boss_damage_complete=False,
        )
        self.assertEqual(combat_status_presentation(partial).kind, "estimate")

    def test_degraded_and_transport_states_are_not_hidden_by_estimate_status(self) -> None:
        degraded = combat_status_presentation(
            self._combat_status_snapshot(degraded=True)
        )
        self.assertEqual(
            degraded.text,
            "● 实时估算（有事件跳过） · 结算可能校正",
        )
        self.assertEqual(degraded.color, GOLD)
        self.assertEqual(
            combat_status_presentation(
                self._combat_status_snapshot(degraded=True),
                compact=True,
            ).text,
            "● 实时 · 跳过",
        )
        self.assertEqual(
            combat_status_presentation(
                self._combat_status_snapshot(degraded=True),
                compact=True,
            ).color,
            GOLD,
        )
        official_degraded = combat_status_presentation(
            self._combat_status_snapshot(
                state="ended",
                official_damage_complete=True,
                official_boss_damage_complete=True,
                degraded=True,
            )
        )
        self.assertEqual(official_degraded.text, "● 官方结算（有事件跳过）")
        self.assertEqual(official_degraded.color, GREEN)

        expected = {
            "connecting": "● 正在连接战斗桥接",
            "stale": "● 战斗桥接响应延迟",
            "error": "● 战斗数据异常，本轮统计已停止",
            "disconnected": "● 等待战斗桥接数据",
        }
        for state, label in expected.items():
            with self.subTest(state=state):
                status = combat_status_presentation(
                    self._combat_status_snapshot(state=state)
                )
                self.assertEqual(status.kind, state)
                self.assertEqual(status.text, label)
                self.assertNotIn("估算", status.text)

        ended = combat_status_presentation(
            self._combat_status_snapshot(state="ended")
        )
        self.assertEqual(ended.kind, "ended")
        self.assertIn("已结束", ended.text)
        self.assertIn("实时估算", ended.text)

    def test_combat_hud_size_adds_only_needed_high_dpi_room(self) -> None:
        self.assertEqual(combat_hud_size(1.5), (350, 474))
        self.assertEqual(combat_hud_size(2.0), (370, 516))
        self.assertEqual(combat_hud_size(2.5), (390, 558))
        self.assertEqual(combat_hud_size(1.5, 0.85), (298, 403))
        self.assertEqual(combat_hud_size(1.5, 1.25), (438, 592))
        self.assertEqual(combat_hud_size(1.25, player_count=2), (580, 484))
        self.assertEqual(combat_hud_size(1.5, player_count=2), (580, 494))
        self.assertEqual(combat_hud_size(2.0, player_count=4), (610, 564))
        self.assertEqual(combat_hud_size(1.5, player_count=5), (810, 494))
        self.assertEqual(combat_hud_size(1.5, player_count=8), (1040, 494))
        self.assertEqual(combat_hud_size(1.5, player_count=11), (1270, 494))
        self.assertEqual(combat_hud_size(1.5, player_count=16), (1500, 494))
        self.assertEqual(combat_hud_size(2.0, player_count=16), (1570, 564))
        self.assertEqual(hud_panel_height(112, 1.5), 112)
        self.assertEqual(hud_panel_height(112, 2.0), 118)
        self.assertEqual(hud_panel_height(88, 2.0, high_dpi_gain=24), 100)
        self.assertEqual(hud_recent_panel_height(1.5, multiplayer=False), 114)
        self.assertEqual(hud_recent_panel_height(1.25, multiplayer=True), 124)
        self.assertEqual(hud_recent_panel_height(1.5, multiplayer=True), 134)
        self.assertEqual(hud_recent_panel_height(2.0, multiplayer=False), 131)
        self.assertEqual(hud_recent_panel_height(2.0, multiplayer=True), 170)

    def test_damage_panel_reserves_structural_space_above_composition_bar(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "toolbox" / "app_shell.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('height=126, panel_key="damage"', source)
        self.assertIn('pady=(self._px(8), 0)', source)
        self.assertIn('pady=(self._px(1), self._px(5))', source)

    def test_combat_hud_first_run_uses_visible_top_left_margin(self) -> None:
        self.assertEqual(
            combat_hud_initial_position(1920, 1080, 350, 456),
            (500, 16),
        )
        self.assertEqual(
            combat_hud_initial_position(800, 600, 350, 456),
            (434, 16),
        )
        self.assertEqual(
            combat_hud_initial_position(320, 300, 350, 456, ui_scale=1.25),
            (0, 0),
        )

    def test_mod_columns_keep_version_author_and_status_structurally_separate(self) -> None:
        compact = mod_tree_column_widths(420)
        spacious = mod_tree_column_widths(1000)
        self.assertEqual(sum(compact.values()), 420)
        self.assertEqual(sum(spacious.values()), 1000)
        self.assertGreaterEqual(compact["version"], 76)
        self.assertGreaterEqual(compact["author"], 136)
        self.assertGreater(spacious["name"], compact["name"])
        self.assertGreater(spacious["author"], compact["author"])

        source = (
            Path(__file__).resolve().parents[1] / "toolbox" / "app_shell.py"
        ).read_text(encoding="utf-8")
        self.assertIn('tree.heading("author", text="作者", anchor="center")', source)
        author_column = source.split('tree.column(\n            "author",', 1)[1].split(
            "        )", 1
        )[0]
        self.assertIn('anchor="center"', author_column)

    def test_mod_detail_panel_uses_content_driven_height(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "toolbox" / "app_shell.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "detail_panel = RoundedPanel(\n            mod_content,\n            height=None,",
            source,
        )

    def test_mod_panel_action_tracks_install_and_game_load_order(self) -> None:
        operation = SimpleNamespace(launchable=False, has_game_panel=True)
        install_required = mod_launch_action(
            operation,
            installed=False,
            busy=False,
            game_process_id=None,
            game_started_ns=None,
            installed_mtime_ns=None,
        )
        self.assertEqual(install_required.kind, "install_required")
        self.assertEqual(install_required.label, "打开 MOD 面板")
        self.assertTrue(install_required.enabled)

        launch_game = mod_launch_action(
            operation,
            installed=True,
            busy=False,
            game_process_id=None,
            game_started_ns=None,
            installed_mtime_ns=50,
        )
        self.assertEqual(launch_game.kind, "launch_game")
        self.assertEqual(launch_game.label, "启动游戏")

        ready = mod_launch_action(
            operation,
            installed=True,
            busy=False,
            game_process_id=42,
            game_started_ns=100,
            installed_mtime_ns=50,
        )
        self.assertEqual(ready.kind, "open_panel")
        self.assertEqual(ready.label, "打开 MOD 面板")

        restart = mod_launch_action(
            operation,
            installed=True,
            busy=False,
            game_process_id=42,
            game_started_ns=100,
            installed_mtime_ns=150,
        )
        self.assertEqual(restart.kind, "restart_game")
        self.assertEqual(restart.label, "需重启游戏")

        busy = mod_launch_action(
            operation,
            installed=True,
            busy=True,
            game_process_id=42,
            game_started_ns=100,
            installed_mtime_ns=50,
        )
        self.assertFalse(busy.enabled)

    def test_hud_location_reserves_a_column_and_never_invents_an_ellipsis(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "toolbox" / "app_shell.py").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "row.grid_columnconfigure(1, weight=0, minsize=self._px(150))",
            source,
        )
        self.assertIn("label.configure(text=text, font=", source)
        self.assertNotIn('rendered_text = "…"', source)

    def test_main_combat_layout_reserves_high_dpi_subtitles_and_numbers(self) -> None:
        self.assertEqual(main_window_min_size(1.25), (780, 710))
        self.assertEqual(main_window_min_size(1.5), (780, 720))
        self.assertEqual(main_window_min_size(2.0), (1200, 850))
        self.assertEqual(main_metric_card_height(1.5), 133)
        self.assertEqual(main_metric_card_height(2.0), 151)
        self.assertEqual(main_team_panel_height(1.5), 115)
        self.assertEqual(main_team_panel_height(2.0), 133)
        self.assertEqual(hud_teammate_card_height(1.5), 150)
        self.assertEqual(hud_teammate_card_height(2.0), 178)
        for tk_scaling in (1.5, 2.0, 2.5):
            _width, hud_height = combat_hud_size(tk_scaling, player_count=16)
            self.assertGreaterEqual(
                hud_height,
                3 * hud_teammate_card_height(tk_scaling) + 15,
            )
        self.assertEqual(combat_table_numeric_width(1.5), 90)
        self.assertEqual(combat_table_numeric_width(2.0), 105)
        self.assertEqual(combat_table_numeric_width(1.5, 1.15), 103)
        self.assertEqual(combat_table_numeric_width(2.0, 1.15), 121)
        self.assertEqual(combat_table_source_width(1.25), 110)
        self.assertEqual(combat_table_source_width(1.75), 125)
        self.assertEqual(combat_table_source_width(2.0), 132)
        self.assertLessEqual(
            combat_table_source_width(1.25)
            + 4 * combat_table_numeric_width(1.25, 1.15),
            525,
        )

    def test_main_window_presets_respect_minimum_and_screen_bounds(self) -> None:
        ordered = [TOOLBOX_WINDOW_PRESETS[name] for name in ("compact", "standard", "spacious")]
        scales = [TOOLBOX_UI_SCALES[name] for name in ("compact", "standard", "spacious")]
        self.assertEqual(DEFAULT_TOOLBOX_WINDOW_PRESET, "spacious")
        self.assertEqual(TOOLBOX_WINDOW_PRESETS["spacious"], (1280, 900))
        self.assertEqual(TOOLBOX_UI_SCALES["spacious"], 1.15)
        self.assertTrue(all(left[0] < right[0] for left, right in zip(ordered, ordered[1:])))
        self.assertTrue(all(left[1] < right[1] for left, right in zip(ordered, ordered[1:])))
        self.assertTrue(all(left < right for left, right in zip(scales, scales[1:])))
        self.assertEqual(
            clamp_main_window_size(
                900,
                650,
                screen_width=1920,
                screen_height=1080,
                tk_scaling=1.5,
            ),
            (900, 720),
        )
        self.assertEqual(
            clamp_main_window_size(
                400,
                300,
                screen_width=1920,
                screen_height=1080,
                tk_scaling=2.0,
            ),
            (1200, 850),
        )
        self.assertEqual(
            clamp_main_window_size(
                1400,
                1000,
                screen_width=1280,
                screen_height=800,
                tk_scaling=1.5,
            ),
            (1200, 720),
        )

    def test_keyboard_scale_action_restores_and_reveals_overlay_before_resizing(self) -> None:
        actions: list[object] = []

        class Keyboard:
            ui_scale = 0.8

            def restore_interaction(self) -> None:
                actions.append("restore")

            def set_ui_scale(self, value: float) -> None:
                actions.append(("scale", value))
                self.ui_scale = value

        shell = SimpleNamespace(
            keyboard=Keyboard(),
            _refresh_display_settings=lambda: actions.append("refresh"),
        )
        ToolboxShell._set_keyboard_scale(shell, 0.1)
        self.assertEqual(actions, ["restore", ("scale", 0.9), "refresh"])

    def test_input_mode_action_restores_overlay_and_refreshes_preview(self) -> None:
        actions: list[object] = []
        keyboard = SimpleNamespace(
            restore_interaction=lambda: actions.append("restore"),
            set_display_mode=lambda mode: actions.append(("mode", mode)),
        )
        shell = SimpleNamespace(
            keyboard=keyboard,
            _draw_keyboard_preview=lambda: actions.append("preview"),
            _refresh_module_statuses=lambda: actions.append("modules"),
            _refresh_display_settings=lambda: actions.append("settings"),
        )
        ToolboxShell._set_input_display_mode(shell, "gamepad")
        self.assertEqual(
            actions,
            ["restore", ("mode", "gamepad"), "preview", "modules", "settings"],
        )

    def test_hud_scale_action_persists_effective_scale_and_opens_hud(self) -> None:
        actions: list[object] = []

        class Hud:
            ui_scale = 1.0

            def set_ui_scale(self, value: float) -> None:
                self.ui_scale = value
                actions.append(("scale", value))

            def show(self) -> None:
                actions.append("show")

        keyboard = SimpleNamespace(
            set_hud_ui_scale=lambda value: actions.append(("save", value))
        )
        shell = SimpleNamespace(
            hud=Hud(),
            keyboard=keyboard,
            _refresh_display_settings=lambda: actions.append("refresh"),
        )
        ToolboxShell._set_hud_scale(shell, 0.1)
        self.assertEqual(
            actions,
            [("scale", 1.1), ("save", 1.1), "show", "refresh"],
        )


if __name__ == "__main__":
    unittest.main()
