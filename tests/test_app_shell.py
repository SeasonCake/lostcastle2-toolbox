from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pathlib import Path

from toolbox.app_shell import (
    DEFAULT_TOOLBOX_WINDOW_PRESET,
    TOOLBOX_WINDOW_PRESETS,
    TOOLBOX_UI_SCALES,
    TOOLBOX_REPOSITORY_URL,
    TAKEN_DAMAGE_LABEL,
    ToolboxShell,
    boss_damage_share,
    clamp_main_window_size,
    combat_state_label,
    combat_hud_size,
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
    main_metric_card_height,
    main_window_min_size,
    ordered_keyboard_keys,
    seed_demo_combat,
    toolbox_author_label,
)
from toolbox.combat_aggregator import CombatAggregator, ScenarioRegistry, SourceRegistry
from toolbox.macro_config import default_profile_data
from toolbox.macro_model import parse_macro_profile


class AppShellModelTests(unittest.TestCase):
    def test_public_taken_damage_label_uses_player_facing_language(self) -> None:
        self.assertEqual(TAKEN_DAMAGE_LABEL, "受击承伤")

    def test_toolbox_attribution_and_repository_action_are_stable(self) -> None:
        self.assertEqual(toolbox_author_label(), "作者：加菲_barista")
        shell = SimpleNamespace(root=None)
        with patch("toolbox.app_shell.webbrowser.open", return_value=True) as opener:
            ToolboxShell._open_repository(shell)
        opener.assert_called_once_with(TOOLBOX_REPOSITORY_URL, new=2)

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
        self.assertEqual(snapshot.taken_settlement_damage, 264)
        self.assertEqual(snapshot.hp_damage_taken, 183)
        self.assertEqual(snapshot.hp_loss_other, 18)
        self.assertEqual(snapshot.effective_healing, 94)
        self.assertEqual(snapshot.mp_spent, 168)
        self.assertEqual(snapshot.mp_gained, 140)

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
        self.assertEqual(combat_state_label("connecting"), "● 正在连接战斗桥接")
        self.assertIn("异常", combat_state_label("error"))
        self.assertNotEqual(combat_state_label("stale"), combat_state_label("disconnected"))

    def test_combat_hud_size_adds_only_needed_high_dpi_room(self) -> None:
        self.assertEqual(combat_hud_size(1.5), (350, 456))
        self.assertEqual(combat_hud_size(2.0), (370, 492))
        self.assertEqual(combat_hud_size(2.5), (390, 528))
        self.assertEqual(combat_hud_size(1.5, 0.85), (298, 388))
        self.assertEqual(combat_hud_size(1.5, 1.25), (438, 570))
        self.assertEqual(hud_panel_height(112, 1.5), 112)
        self.assertEqual(hud_panel_height(112, 2.0), 118)
        self.assertEqual(hud_panel_height(88, 2.0, high_dpi_gain=24), 100)

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
        self.assertEqual(main_window_min_size(1.5), (780, 610))
        self.assertEqual(main_window_min_size(2.0), (840, 700))
        self.assertEqual(main_metric_card_height(1.5), 133)
        self.assertEqual(main_metric_card_height(2.0), 151)
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
            (900, 650),
        )
        self.assertEqual(
            clamp_main_window_size(
                400,
                300,
                screen_width=1920,
                screen_height=1080,
                tk_scaling=2.0,
            ),
            (840, 700),
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
