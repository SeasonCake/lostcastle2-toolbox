from __future__ import annotations

import unittest

from toolbox.macro_engine import MacroState
from toolbox.macro_ui import (
    BAD,
    PAUSED,
    captured_key_for_target,
    key_from_tk_keysym,
    milliseconds_from_seconds_text,
    runtime_presentation,
    seconds_text_from_milliseconds,
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


if __name__ == "__main__":
    unittest.main()
