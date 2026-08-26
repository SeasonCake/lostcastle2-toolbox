from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

import keyview


class KeyViewTests(unittest.TestCase):
    def test_z_order_helper_detects_only_candidate_above_reference(self) -> None:
        previous = {40: 30, 30: 20, 20: 10, 10: 0}
        getter = lambda hwnd: previous.get(hwnd, 0)
        self.assertTrue(keyview.hwnd_is_above(20, 40, getter))
        self.assertTrue(keyview.hwnd_is_above(10, 40, getter))
        self.assertFalse(keyview.hwnd_is_above(40, 20, getter))
        self.assertFalse(keyview.hwnd_is_above(20, 20, getter))

    def test_layout_and_virtual_keys_match(self) -> None:
        self.assertEqual(set(keyview.LOST_CASTLE_KEYS), set(keyview.DEFAULT_KEY_LAYOUT))
        self.assertEqual(set(keyview.PHYSICAL_KEY_GEOMETRY), set(keyview.KEY_DEFINITIONS))
        self.assertEqual(
            len({definition[1] for definition in keyview.KEY_DEFINITIONS.values()}),
            len(keyview.KEY_DEFINITIONS),
        )
        for key_only in (False, True):
            layout = keyview.layout_for_keys(keyview.LOST_CASTLE_KEYS, key_only=key_only)
            overlay_height = keyview.overlay_height(layout, key_only=key_only)
            for x, y, width, height in layout.values():
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                self.assertLessEqual(x + width, keyview.WINDOW_WIDTH)
                self.assertLessEqual(y + height, overlay_height)

    def test_custom_layout_is_bounded(self) -> None:
        keys = list(keyview.KEY_DEFINITIONS)[: keyview.MAX_DISPLAY_KEYS]
        layout = keyview.layout_for_keys(keys)
        overlay_height = keyview.overlay_height(layout, key_only=False)
        self.assertEqual(set(layout), set(keys))
        for x, y, width, height in layout.values():
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + width, keyview.WINDOW_WIDTH)
            self.assertLessEqual(y + height, overlay_height)

    def test_custom_layout_preserves_wide_keys_and_spacing(self) -> None:
        keys = ["W", "A", "S", "D", "I", "J", "K", "L", "SPACE", "U"]
        layout = keyview.layout_for_keys(keys)
        self.assertGreater(layout["SPACE"][2], layout["W"][2])
        rows: dict[int, list[tuple[int, int]]] = {}
        for x, y, width, _height in layout.values():
            rows.setdefault(y, []).append((x, x + width))
        for intervals in rows.values():
            ordered = sorted(intervals)
            for left, right in zip(ordered, ordered[1:]):
                self.assertGreaterEqual(right[0] - left[1], 10)
        self.assertLess(layout["W"][1], layout["A"][1])
        self.assertEqual(layout["U"][1], layout["I"][1])
        self.assertEqual(layout, keyview.layout_for_keys(list(reversed(keys))))

    def test_game_layout_keeps_core_landmarks_when_accessories_are_added(self) -> None:
        core = list(keyview.LOST_CASTLE_KEYS)
        baseline = keyview.layout_for_keys(core)
        mixed = keyview.layout_for_keys(
            core + ["TAB", "ALT", "M", "ENTER", "RIGHT"]
        )
        for key in keyview.GAME_LAYOUT_KEYS.intersection(core):
            if key != "SPACE":
                self.assertEqual(mixed[key], baseline[key])
        self.assertEqual(set(mixed), set(core + ["TAB", "ALT", "M", "ENTER", "RIGHT"]))
        self.assertEqual(
            len({mixed[key][1] for key in ("TAB", "ALT", "M", "ENTER", "RIGHT")}),
            1,
        )
        self.assertGreater(mixed["SPACE"][2], mixed["TAB"][2])
        self.assertGreater(mixed["SPACE"][1], mixed["TAB"][1])

    def test_selected_tab_is_rendered_in_game_layout(self) -> None:
        selected = list(keyview.LOST_CASTLE_KEYS) + ["TAB"]
        layout = keyview.layout_for_keys(selected)
        self.assertIn("TAB", layout)
        self.assertEqual(set(layout), set(selected))

    def test_general_layout_follows_physical_keyboard_rows(self) -> None:
        layout = keyview.layout_for_keys(["T", "Q", "L", "A", "LMB", "SPACE"])
        self.assertEqual(layout["Q"][1], layout["T"][1])
        self.assertLess(layout["Q"][0], layout["T"][0])
        self.assertLess(layout["Q"][1], layout["A"][1])
        self.assertLess(layout["A"][1], layout["SPACE"][1])
        self.assertLessEqual(layout["SPACE"][1], layout["LMB"][1])

    def test_representative_layouts_cover_keys_without_overlap(self) -> None:
        cases = (
            list(keyview.LOST_CASTLE_KEYS),
            list(keyview.LOST_CASTLE_KEYS) + ["TAB"],
            list(keyview.LOST_CASTLE_KEYS) + ["ALT", "M", "ENTER", "RIGHT"],
            ["Q", "W", "E", "A", "S", "D", "Z", "X", "C", "SPACE"],
            ["TAB", "Q", "T", "A", "G", "M", "SPACE", "LEFT", "UP", "RIGHT"],
            list(keyview.KEY_DEFINITIONS)[: keyview.MAX_DISPLAY_KEYS],
        )
        rng = random.Random(20260825)
        keys = list(keyview.KEY_DEFINITIONS)
        cases += tuple(
            rng.sample(keys, rng.randint(1, keyview.MAX_DISPLAY_KEYS))
            for _ in range(1000)
        )
        for selected in cases:
            for key_only in (False, True):
                layout = keyview.layout_for_keys(selected, key_only=key_only)
                self.assertEqual(set(layout), set(selected))
                height = keyview.overlay_height(layout, key_only=key_only)
                rectangles = list(layout.items())
                for key, (x, y, width, key_height) in rectangles:
                    self.assertGreaterEqual(x, 0, key)
                    self.assertGreaterEqual(y, 0, key)
                    self.assertLessEqual(x + width, keyview.WINDOW_WIDTH, key)
                    self.assertLessEqual(y + key_height, height, key)
                for index, (left_key, left) in enumerate(rectangles):
                    lx, ly, lw, lh = left
                    for right_key, right in rectangles[index + 1 :]:
                        rx, ry, rw, rh = right
                        overlaps = not (
                            lx + lw <= rx
                            or rx + rw <= lx
                            or ly + lh <= ry
                            or ry + rh <= ly
                        )
                        self.assertFalse(overlaps, (left_key, right_key, selected, layout))

    def test_color_presets_are_complete(self) -> None:
        required = {
            "name",
            "background",
            "panel_outline",
            "idle",
            "idle_outline",
            "inner_outline",
            "key_text",
            "active",
            "active_outline",
            "active_text",
        }
        self.assertIn(keyview.DEFAULT_COLOR_PRESET, keyview.COLOR_PRESETS)
        for preset in keyview.COLOR_PRESETS.values():
            self.assertEqual(set(preset), required)

    def test_settings_roundtrip_and_opacity_clamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            keyview.save_settings(
                {
                    "background_opacity": 2.5,
                    "x": 100,
                    "y": 200,
                    "selected_keys": ["W", "A", "W", "NOT_A_KEY"],
                },
                path,
            )
            loaded = keyview.load_settings(path)
            self.assertEqual(loaded["background_opacity"], 1.0)
            self.assertEqual((loaded["x"], loaded["y"]), (100, 200))
            self.assertEqual(loaded["selected_keys"], ["W", "A"])
            self.assertEqual(loaded["color_preset"], keyview.DEFAULT_COLOR_PRESET)
            self.assertEqual(loaded["ui_scale"], 1.0)
            json.loads(path.read_text(encoding="utf-8"))

    def test_settings_theme_fallback_and_scale_clamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text(
                '{"color_preset":"missing","ui_scale":9}', encoding="utf-8"
            )
            loaded = keyview.load_settings(path)
            self.assertEqual(loaded["color_preset"], keyview.DEFAULT_COLOR_PRESET)
            self.assertEqual(loaded["ui_scale"], 1.8)

    def test_v1_settings_migrate_opacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text('{"opacity": 0.7}', encoding="utf-8")
            loaded = keyview.load_settings(path)
            self.assertEqual(loaded["background_opacity"], 0.7)
            self.assertNotIn("opacity", loaded)

    def test_configured_game_path_resolves_without_local_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_exe = Path(temp_dir) / "LostCastle2.exe"
            game_exe.touch()
            with mock.patch.object(keyview, "steam_install_location", return_value=None):
                result = keyview.resolve_game_exe(game_exe)
        self.assertEqual(result, game_exe.resolve())

    def test_missing_game_path_returns_none(self) -> None:
        missing = Path("Z:/does-not-exist/LostCastle2.exe")
        with mock.patch.object(keyview, "steam_install_location", return_value=None):
            result = keyview.resolve_game_exe(missing)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
