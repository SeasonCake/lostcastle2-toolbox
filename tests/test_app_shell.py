from __future__ import annotations

import unittest

from pathlib import Path

from toolbox.app_shell import (
    boss_damage_share,
    clamp_main_window_size,
    combat_state_label,
    combat_hud_size,
    combat_table_numeric_width,
    format_location_label,
    format_metric,
    format_room_area,
    format_stage_location,
    macro_rows,
    metric_font_size,
    hud_panel_height,
    main_metric_card_height,
    main_window_min_size,
    ordered_keyboard_keys,
    seed_demo_combat,
)
from toolbox.combat_aggregator import CombatAggregator, ScenarioRegistry, SourceRegistry
from toolbox.macro_config import default_profile_data
from toolbox.macro_model import parse_macro_profile


class AppShellModelTests(unittest.TestCase):
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
        self.assertEqual(combat_hud_size(1.5), (350, 426))
        self.assertEqual(combat_hud_size(2.0), (370, 462))
        self.assertEqual(combat_hud_size(2.5), (390, 498))
        self.assertEqual(hud_panel_height(112, 1.5), 112)
        self.assertEqual(hud_panel_height(112, 2.0), 118)
        self.assertEqual(hud_panel_height(88, 2.0, high_dpi_gain=24), 100)

    def test_main_combat_layout_reserves_high_dpi_subtitles_and_numbers(self) -> None:
        self.assertEqual(main_window_min_size(1.5), (780, 560))
        self.assertEqual(main_window_min_size(2.0), (840, 600))
        self.assertEqual(main_metric_card_height(1.5), 133)
        self.assertEqual(main_metric_card_height(2.0), 151)
        self.assertEqual(combat_table_numeric_width(1.5), 90)
        self.assertEqual(combat_table_numeric_width(2.0), 105)

    def test_main_window_presets_respect_minimum_and_screen_bounds(self) -> None:
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
            (840, 600),
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


if __name__ == "__main__":
    unittest.main()
