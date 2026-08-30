from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
from itertools import combinations
import json
from pathlib import Path
import random
import sys
import tempfile
import time
import unittest
from unittest import mock

import keyview


class KeyViewTests(unittest.TestCase):
    def test_app_window_uses_the_packaged_toolbox_icon(self) -> None:
        root = mock.Mock()
        keyview.apply_app_window_icon(root)
        root.iconbitmap.assert_called_once_with(
            default=str(keyview.RESOURCE_DIR / "assets" / "keyview.ico")
        )
        build_source = (Path(__file__).resolve().parents[1] / "build.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("assets\\keyview.ico;assets", build_source)

        from PIL import Image

        with Image.open(
            Path(__file__).resolve().parents[1] / "assets" / "keyview.ico"
        ) as icon:
            sizes = icon.info.get("sizes", set())
        self.assertTrue(
            {
                (16, 16),
                (20, 20),
                (24, 24),
                (32, 32),
                (40, 40),
                (48, 48),
                (64, 64),
                (96, 96),
                (128, 128),
                (256, 256),
            }.issubset(sizes)
        )

    def test_windows_fixed_and_string_versions_match_the_app_version(self) -> None:
        version_source = (
            Path(__file__).resolve().parents[1] / "version_info.txt"
        ).read_text(encoding="utf-8")
        numeric_version = tuple(int(part) for part in keyview.APP_VERSION.split(".")) + (0,)
        rendered_numeric = ", ".join(str(part) for part in numeric_version)
        self.assertIn(f"filevers=({rendered_numeric})", version_source)
        self.assertIn(f"prodvers=({rendered_numeric})", version_source)
        self.assertIn(
            f"StringStruct('FileVersion', '{keyview.APP_VERSION}')",
            version_source,
        )
        self.assertIn(
            f"StringStruct('ProductVersion', '{keyview.APP_VERSION}')",
            version_source,
        )

    def test_process_path_query_preserves_full_64_bit_handle_identity(self) -> None:
        observed = keyview._process_executable_path(keyview.os.getpid())
        self.assertIsNotNone(observed)
        self.assertEqual(
            str(observed).casefold(),
            str(Path(sys.executable).resolve()).casefold(),
        )

    def test_process_creation_time_uses_same_epoch_as_file_mtime(self) -> None:
        created_ns = keyview._process_creation_time_ns(keyview.os.getpid())
        self.assertIsNotNone(created_ns)
        assert created_ns is not None
        self.assertLess(created_ns, keyview.time.time_ns())

    def test_mod_panel_hotkey_requires_exact_game_path_and_foreground(self) -> None:
        app = keyview.KeyViewApp.__new__(keyview.KeyViewApp)
        app.game_process_id = 42
        app.settings = {"game_path": r"C:\Games\Lost Castle 2\LostCastle2.exe"}
        expected = Path(app.settings["game_path"])
        backend = object()
        with mock.patch.object(keyview, "resolve_game_exe", return_value=expected), mock.patch.object(
            keyview, "_process_executable_path", return_value=expected
        ), mock.patch.object(keyview, "focus_process_window", return_value=True), mock.patch.object(
            keyview, "WindowsSendInputBackend", return_value=backend
        ), mock.patch.object(keyview, "send_hotkey") as sender, mock.patch.object(
            keyview.time, "sleep"
        ):
            self.assertTrue(app.open_game_panel_hotkey("INS"))
        sender.assert_called_once_with(backend, "INS")

        with mock.patch.object(keyview, "resolve_game_exe", return_value=expected), mock.patch.object(
            keyview, "_process_executable_path", return_value=Path(r"C:\Other\LostCastle2.exe")
        ), mock.patch.object(keyview, "focus_process_window") as focus:
            self.assertFalse(app.open_game_panel_hotkey("INS"))
        focus.assert_not_called()

    def test_game_process_enumeration_failure_freezes_runtime_setup(self) -> None:
        with mock.patch.object(
            keyview.kernel32, "CreateToolhelp32Snapshot", return_value=123
        ), mock.patch.object(
            keyview.kernel32, "Process32FirstW", return_value=False
        ), mock.patch.object(keyview.kernel32, "CloseHandle") as close_handle:
            running_or_unknown = keyview.is_exact_game_process_running(
                Path(r"C:\fixture\Lost Castle 2\LostCastle2.exe")
            )

        self.assertTrue(running_or_unknown)
        close_handle.assert_called_once_with(123)

    def test_game_launch_preflight_can_stop_start_before_steam_or_exe(self) -> None:
        app = keyview.KeyViewApp.__new__(keyview.KeyViewApp)
        app.game_process_id = None
        app.before_game_launch = lambda: False
        app.settings = {}

        with mock.patch.object(keyview.os, "startfile") as startfile, mock.patch.object(
            keyview.subprocess, "Popen"
        ) as popen:
            keyview.KeyViewApp.launch_game(app)

        startfile.assert_not_called()
        popen.assert_not_called()

    def test_restore_interaction_recovers_hidden_pure_click_through_overlay(self) -> None:
        actions: list[object] = []

        class Root:
            def lift(self) -> None:
                actions.append("lift")

        app = mock.Mock()
        app.click_through = True
        app.key_only = True
        app.visible = False
        app.root = Root()
        app._set_click_through.side_effect = lambda value: setattr(app, "click_through", value)
        app._set_clean_mode.side_effect = lambda value, save=False: setattr(app, "key_only", value)
        app.toggle_visible.side_effect = lambda: setattr(app, "visible", True)

        keyview.KeyViewApp.restore_interaction(app)

        app._set_click_through.assert_called_once_with(False)
        app._set_clean_mode.assert_called_once_with(False, save=False)
        app.toggle_visible.assert_called_once_with()
        app._sync_background_layer.assert_called_once_with()
        app._save_current_settings.assert_called_once_with()
        self.assertTrue(app.visible)
        self.assertFalse(app.key_only)
        self.assertFalse(app.click_through)
        self.assertEqual(actions, ["lift"])

    def test_self_test_reports_game_presence_without_exposing_local_path(self) -> None:
        private_path = Path("private-install") / "LostCastle2.exe"
        output = io.StringIO()
        with mock.patch.object(keyview, "resolve_game_exe", return_value=private_path):
            with redirect_stdout(output):
                self.assertEqual(keyview.self_test(), 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["game_exe_found"])
        self.assertNotIn("game_exe", payload)
        self.assertNotIn(str(private_path), output.getvalue())

    def test_window_size_parser_accepts_bounded_qa_geometry(self) -> None:
        self.assertEqual(keyview.parse_window_size("780x560"), (780, 560))
        with self.assertRaises(argparse.ArgumentTypeError):
            keyview.parse_window_size("500x300")

    def test_qa_receipt_requires_a_paired_png_capture(self) -> None:
        args = keyview.parse_args(
            [
                "--qa-ui-receipt",
                "receipt.json",
                "--qa-ui-screenshot",
                "capture.png",
                "--qa-ui-window",
                "hud",
            ]
        )
        self.assertEqual(args.qa_ui_window, "hud")
        self.assertEqual(args.qa_ui_receipt, Path("receipt.json"))
        self.assertIsNone(args.qa_select_mod)
        selected = keyview.parse_args(["--qa-select-mod", "player-live-stats"])
        self.assertEqual(selected.qa_select_mod, "player-live-stats")
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            keyview.parse_args(["--qa-ui-receipt", "receipt.json"])

    def test_png_dimensions_reads_the_capture_header(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            capture = Path(temporary_directory) / "capture.png"
            capture.write_bytes(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                b"\x00\x00\x01\x72\x00\x00\x02\x04"
            )
            self.assertEqual(keyview._png_dimensions(capture), (370, 516))

    def test_bounded_window_message_returns_quickly_for_invalid_handle(self) -> None:
        started = time.perf_counter()
        self.assertEqual(
            keyview._send_window_message_bounded(
                0,
                0x007F,
                0,
                timeout_ms=10,
            ),
            0,
        )
        self.assertLess(time.perf_counter() - started, 0.5)

    def test_combat_hud_opens_by_default_with_an_explicit_startup_opt_out(self) -> None:
        self.assertTrue(keyview.parse_args([]).show_combat_hud)
        self.assertTrue(keyview.parse_args(["--show-combat-hud"]).show_combat_hud)
        self.assertFalse(
            keyview.parse_args(["--hide-combat-hud-on-start"]).show_combat_hud
        )

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
            ["ESC", "RMB"],
            ["F1", "RIGHT"],
            ["BACKSPACE", "SHIFT", "LMB"],
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

    def test_every_two_key_distance_pair_stays_bounded_and_non_overlapping(self) -> None:
        for selected in combinations(keyview.KEY_DEFINITIONS, 2):
            for key_only in (False, True):
                layout = keyview.layout_for_keys(selected, key_only=key_only)
                self.assertEqual(set(layout), set(selected))
                height = keyview.overlay_height(layout, key_only=key_only)
                left, right = layout.values()
                for x, y, width, key_height in (left, right):
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(x + width, keyview.WINDOW_WIDTH)
                    self.assertLessEqual(y + key_height, height)
                lx, ly, lw, lh = left
                rx, ry, rw, rh = right
                self.assertTrue(
                    lx + lw <= rx
                    or rx + rw <= lx
                    or ly + lh <= ry
                    or ry + rh <= ly,
                    (selected, layout),
                )

    def test_gamepad_layout_is_complete_bounded_and_non_overlapping(self) -> None:
        for key_only in (False, True):
            layout = keyview.gamepad_layout(key_only=key_only)
            self.assertEqual(set(layout), set(keyview.GAMEPAD_LABELS))
            height = keyview.overlay_height(layout, key_only=key_only)
            rectangles = list(layout.items())
            for key, (x, y, width, key_height) in rectangles:
                self.assertGreaterEqual(x, 0, key)
                self.assertGreaterEqual(y, 0, key)
                self.assertLessEqual(x + width, keyview.WINDOW_WIDTH, key)
                self.assertLessEqual(y + key_height, height, key)
            for index, (left_key, (lx, ly, lw, lh)) in enumerate(rectangles):
                for right_key, (rx, ry, rw, rh) in rectangles[index + 1 :]:
                    overlaps = not (
                        lx + lw <= rx
                        or rx + rw <= lx
                        or ly + lh <= ry
                        or ry + rh <= ly
                    )
                    self.assertFalse(overlaps, (left_key, right_key, layout))

    def test_xinput_state_maps_buttons_triggers_and_stick_motion(self) -> None:
        class FakeXInput:
            @staticmethod
            def XInputGetState(index: int, pointer: object) -> int:
                self.assertEqual(index, 0)
                state = pointer._obj
                state.gamepad.buttons = (
                    keyview.XINPUT_BUTTONS["PAD_A"]
                    | keyview.XINPUT_BUTTONS["PAD_LB"]
                )
                state.gamepad.left_trigger = 31
                state.gamepad.right_thumb_x = 9000
                return 0

        with mock.patch.object(keyview, "XINPUT", FakeXInput()):
            connected, active = keyview.read_gamepad_state()
        self.assertTrue(connected)
        self.assertTrue(active["PAD_A"])
        self.assertTrue(active["PAD_LB"])
        self.assertTrue(active["PAD_LT"])
        self.assertTrue(active["PAD_RS"])
        self.assertFalse(active["PAD_B"])

        with mock.patch.object(keyview, "XINPUT", None):
            connected, active = keyview.read_gamepad_state()
        self.assertFalse(connected)
        self.assertFalse(any(active.values()))

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
            self.assertEqual(
                (loaded["toolbox_width"], loaded["toolbox_height"]),
                (1280, 900),
            )
            self.assertEqual(loaded["input_display_mode"], "keyboard")
            self.assertEqual(loaded["toolbox_ui_scale"], 1.15)
            self.assertEqual(loaded["hud_ui_scale"], 1.0)
            json.loads(path.read_text(encoding="utf-8"))

    def test_settings_theme_fallback_and_scale_clamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text(
                '{"color_preset":"missing","ui_scale":9,'
                '"input_display_mode":"unknown","toolbox_ui_scale":8,'
                '"hud_ui_scale":0.1}',
                encoding="utf-8",
            )
            loaded = keyview.load_settings(path)
            self.assertEqual(loaded["color_preset"], keyview.DEFAULT_COLOR_PRESET)
            self.assertEqual(loaded["ui_scale"], 1.8)
            self.assertEqual(loaded["input_display_mode"], "keyboard")
            self.assertEqual(loaded["toolbox_ui_scale"], 1.15)
            self.assertEqual(loaded["hud_ui_scale"], 0.85)

    def test_toolbox_window_size_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            path.write_text(
                '{"toolbox_width":99999,"toolbox_height":12}',
                encoding="utf-8",
            )
            loaded = keyview.load_settings(path)
            self.assertEqual((loaded["toolbox_width"], loaded["toolbox_height"]), (1400, 560))

    def test_fresh_settings_default_to_the_spacious_toolbox_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            loaded = keyview.load_settings(Path(temp_dir) / "missing-settings.json")
        self.assertEqual(
            (loaded["toolbox_width"], loaded["toolbox_height"]),
            (1280, 900),
        )
        self.assertEqual(loaded["toolbox_ui_scale"], 1.15)

    def test_legacy_default_and_spacious_profiles_migrate_to_the_new_default(self) -> None:
        profiles = ((900, 650, 1.0), (1160, 840, 1.15))
        for width, height, scale in profiles:
            with self.subTest(profile=(width, height, scale)):
                with tempfile.TemporaryDirectory() as temp_dir:
                    path = Path(temp_dir) / "settings.json"
                    path.write_text(
                        json.dumps(
                            {
                                "toolbox_width": width,
                                "toolbox_height": height,
                                "toolbox_ui_scale": scale,
                            }
                        ),
                        encoding="utf-8",
                    )
                    loaded = keyview.load_settings(path)
                self.assertEqual(
                    (loaded["toolbox_width"], loaded["toolbox_height"]),
                    (1280, 900),
                )
                self.assertEqual(loaded["toolbox_ui_scale"], 1.15)

    def test_standard_and_custom_toolbox_profiles_are_not_migrated(self) -> None:
        profiles = ((1000, 720, 1.0), (1080, 760, 1.0))
        for width, height, scale in profiles:
            with self.subTest(profile=(width, height, scale)):
                with tempfile.TemporaryDirectory() as temp_dir:
                    path = Path(temp_dir) / "settings.json"
                    path.write_text(
                        json.dumps(
                            {
                                "toolbox_width": width,
                                "toolbox_height": height,
                                "toolbox_ui_scale": scale,
                            }
                        ),
                        encoding="utf-8",
                    )
                    loaded = keyview.load_settings(path)
                self.assertEqual(
                    (loaded["toolbox_width"], loaded["toolbox_height"]),
                    (width, height),
                )
                self.assertEqual(loaded["toolbox_ui_scale"], scale)

    def test_toolbox_window_size_setter_updates_persisted_state(self) -> None:
        app = object.__new__(keyview.KeyViewApp)
        app.settings = {}
        with mock.patch.object(keyview.KeyViewApp, "_save_current_settings") as save:
            app.set_toolbox_window_size(1080, 760)
        self.assertEqual(app.toolbox_window_size, (1080, 760))
        self.assertEqual(
            (app.settings["toolbox_width"], app.settings["toolbox_height"]),
            (1080, 760),
        )
        save.assert_called_once()

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
