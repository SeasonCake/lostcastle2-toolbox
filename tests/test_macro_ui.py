from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
from unittest import mock

from toolbox.macro_engine import MacroState
from toolbox.macro_ui import (
    BAD,
    PAUSED,
    captured_key_for_target,
    key_from_tk_keysym,
    milliseconds_from_seconds_text,
    runtime_presentation,
    seconds_text_from_milliseconds,
    MacroFeature,
)


class MacroKeyCaptureTests(unittest.TestCase):
    def test_keyboard_events_map_to_existing_macro_tokens(self) -> None:
        expected = {
            "a": "A",
            "7": "7",
            "F5": "F5",
            "Return": "ENTER",
            "KP_Enter": "ENTER",
            "space": "SPACE",
            "Tab": "TAB",
            "Caps_Lock": "CAPS",
            "Escape": "ESC",
            "BackSpace": "BACK",
            "Left": "LEFT",
            "Control_L": "CTRL",
            "Shift_R": "SHIFT",
            "Alt_L": "ALT",
        }
        for keysym, token in expected.items():
            with self.subTest(keysym=keysym):
                self.assertEqual(key_from_tk_keysym(keysym), token)

    def test_unsupported_or_ambiguous_keys_fail_closed(self) -> None:
        for keysym in ("", "F13", "semicolon", "Super_L", "MouseWheel"):
            with self.subTest(keysym=keysym):
                self.assertIsNone(key_from_tk_keysym(keysym))

    def test_capture_respects_each_fields_existing_options(self) -> None:
        self.assertEqual(captured_key_for_target("trigger_key", "F7"), "F7")
        self.assertIsNone(captured_key_for_target("trigger_key", "F8"))
        self.assertIsNone(captured_key_for_target("trigger_key", "Escape"))
        self.assertEqual(captured_key_for_target("step_key", "F12"), "F12")
        self.assertEqual(captured_key_for_target("step_key", "Escape"), "ESC")
        self.assertEqual(captured_key_for_target("step_key", "BackSpace"), "BACK")
        self.assertIsNone(captured_key_for_target("unknown", "A"))


class MacroRuntimePresentationTests(unittest.TestCase):
    def test_foreground_block_is_a_pause_not_an_execution_error(self) -> None:
        text, color = runtime_presentation(MacroState.BLOCKED_FOCUS)
        self.assertIn("安全暂停", text)
        self.assertIn("重按", text)
        self.assertEqual(color, PAUSED)
        self.assertNotEqual(color, BAD)

    def test_real_execution_error_remains_red(self) -> None:
        text, color = runtime_presentation(MacroState.ERROR)
        self.assertIn("执行错误", text)
        self.assertEqual(color, BAD)


class MacroRuntimeLimitUiTests(unittest.TestCase):
    def test_seconds_roundtrip_preserves_millisecond_config_values(self) -> None:
        for milliseconds in (100, 10_000, 60_000, 600_000):
            with self.subTest(milliseconds=milliseconds):
                text = seconds_text_from_milliseconds(milliseconds)
                self.assertEqual(milliseconds_from_seconds_text(text), milliseconds)

    def test_seconds_parser_rejects_non_finite_or_sub_millisecond_values(self) -> None:
        for value in ("", "abc", "NaN", "Infinity", "0.0001"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    milliseconds_from_seconds_text(value)


class MacroCreationTests(unittest.TestCase):
    def test_new_profiles_start_disabled_with_no_example_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            feature = object.__new__(MacroFeature)
            feature.errors = []
            feature._dirty = False
            feature._step_draft_dirty = False
            feature.window = None
            feature.profiles = ()
            feature.config_path = Path(temp_dir) / "macros.json"
            feature.controller = mock.Mock()
            feature._refresh_profile_list = mock.Mock()
            feature._set_status = mock.Mock()

            for mode in ("once", "hold_repeat", "toggle_repeat"):
                feature._new_profile(mode)

            self.assertEqual(len(feature.profiles), 3)
            self.assertEqual(len({profile.id for profile in feature.profiles}), 3)
            for profile in feature.profiles:
                self.assertFalse(profile.enabled)
                self.assertEqual(profile.steps, ())
            stored = feature.config_path.read_text(encoding="utf-8")
            self.assertNotIn('"key": "J",\n        "action": "tap"', stored)
            feature.controller.stop_all.assert_called_with("config_changed")

    def test_unapplied_step_draft_is_not_silently_replaced(self) -> None:
        class FakeTree:
            def __init__(self) -> None:
                self.current = ("1",)

            def selection(self) -> tuple[str, ...]:
                return self.current

            def selection_remove(self, *_items: str) -> None:
                self.current = ()

            def selection_set(self, item: str) -> None:
                self.current = (item,)

            def focus(self, _item: str) -> None:
                return None

        feature = object.__new__(MacroFeature)
        feature._loading_form = False
        feature._step_draft_dirty = True
        feature._loaded_step_index = 0
        feature._editing_steps = [
            {"type": "key", "key": "J", "action": "tap", "hold_ms": 50},
            {"type": "key", "key": "K", "action": "tap", "hold_ms": 50},
        ]
        feature.step_tree = FakeTree()
        feature.window = None
        feature.vars = {
            "step_action": mock.Mock(),
            "step_key": mock.Mock(),
            "step_ms": mock.Mock(),
        }
        feature._sync_step_editor_state = mock.Mock()

        with mock.patch("toolbox.macro_ui.messagebox.askyesno", return_value=False):
            feature._load_selected_step(None)

        self.assertEqual(feature.step_tree.selection(), ("0",))
        self.assertTrue(feature._step_draft_dirty)
        for variable in feature.vars.values():
            variable.set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
