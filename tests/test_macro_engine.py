from __future__ import annotations

import time
import unittest

from toolbox.macro_engine import MacroController, MacroState, MacroStatus
from toolbox.macro_model import MacroProfileError, parse_macro_profile


def profile_data(mode: str = "once", *, enabled: bool = True) -> dict:
    return {
        "schema_version": 1,
        "id": f"qa-{mode.replace('_', '-')}",
        "name": f"QA {mode}",
        "enabled": enabled,
        "trigger": {"key": "F6", "modifiers": [], "mode": mode},
        "limits": {
            "foreground_only": True,
            "max_runtime_ms": 400,
            "repeat_delay_ms": 20,
        },
        "steps": [
            {"type": "key", "key": "J", "action": "tap", "hold_ms": 20},
            {"type": "wait", "duration_ms": 20},
        ],
    }


class FakeBackend:
    def __init__(self) -> None:
        self.foreground = True
        self.events: list[tuple[str, str]] = []
        self.down: set[str] = set()
        self.raise_on_down = False

    def is_target_foreground(self) -> bool:
        return self.foreground

    def key_down(self, key: str) -> None:
        if self.raise_on_down:
            raise RuntimeError("injected failure")
        self.down.add(key)
        self.events.append(("down", key))

    def key_up(self, key: str) -> None:
        self.down.discard(key)
        self.events.append(("up", key))


class MacroModelTests(unittest.TestCase):
    def test_profile_parser_normalizes_keys_and_preserves_all_modes(self) -> None:
        for mode in ("once", "hold_repeat", "toggle_repeat"):
            data = profile_data(mode)
            data["trigger"]["key"] = "f6"
            data["steps"][0]["key"] = "j"
            profile = parse_macro_profile(data)
            self.assertEqual(profile.trigger.key, "F6")
            self.assertEqual(profile.steps[0].key, "J")
            self.assertEqual(profile.trigger.mode, mode)

    def test_profile_parser_rejects_unbounded_or_ambiguous_steps(self) -> None:
        bad = profile_data()
        bad["limits"]["foreground_only"] = False
        with self.assertRaises(MacroProfileError):
            parse_macro_profile(bad)
        bad = profile_data()
        del bad["steps"][0]["hold_ms"]
        with self.assertRaises(MacroProfileError):
            parse_macro_profile(bad)
        bad = profile_data()
        bad["steps"][0] = {"type": "key", "key": "J", "action": "down", "hold_ms": 40}
        with self.assertRaises(MacroProfileError):
            parse_macro_profile(bad)


class MacroControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakeBackend()
        self.statuses: list[MacroStatus] = []
        self.controller = MacroController(self.backend, self.statuses.append)

    def tearDown(self) -> None:
        self.controller.close()

    def test_once_runs_exactly_one_sequence_and_releases_key(self) -> None:
        profile = parse_macro_profile(profile_data("once"))
        self.assertEqual(self.controller.update_trigger(profile, True), MacroState.RUNNING)
        self.assertTrue(self.controller.wait_for_idle(profile.id))
        self.assertEqual(self.backend.events, [("down", "J"), ("up", "J")])
        self.assertFalse(self.backend.down)
        self.assertEqual(self.statuses[-1].state, MacroState.COMPLETED)

    def test_hold_repeat_stops_on_release(self) -> None:
        profile = parse_macro_profile(profile_data("hold_repeat"))
        self.controller.update_trigger(profile, True)
        time.sleep(0.09)
        self.controller.update_trigger(profile, False)
        self.assertTrue(self.controller.wait_for_idle(profile.id))
        self.assertGreaterEqual(self.backend.events.count(("down", "J")), 1)
        self.assertFalse(self.backend.down)
        self.assertIn(self.statuses[-1].state, {MacroState.STOPPED, MacroState.TRIGGER_RELEASED})

    def test_toggle_repeat_stops_on_second_rising_edge(self) -> None:
        profile = parse_macro_profile(profile_data("toggle_repeat"))
        self.controller.update_trigger(profile, True)
        self.controller.update_trigger(profile, False)
        time.sleep(0.06)
        self.assertEqual(self.controller.update_trigger(profile, True), MacroState.STOPPING)
        self.assertTrue(self.controller.wait_for_idle(profile.id))
        self.assertFalse(self.backend.down)

    def test_disabled_or_unfocused_macro_sends_nothing(self) -> None:
        disabled = parse_macro_profile(profile_data("once", enabled=False))
        self.assertEqual(self.controller.update_trigger(disabled, True), MacroState.DISABLED)
        self.backend.foreground = False
        enabled = parse_macro_profile(profile_data("once"))
        # Enabling while the physical trigger is still held must not synthesize a
        # new rising edge. The user has to release and press again.
        self.assertEqual(self.controller.update_trigger(enabled, True), MacroState.IDLE)
        self.controller.update_trigger(enabled, False)
        self.assertEqual(self.controller.update_trigger(enabled, True), MacroState.BLOCKED_FOCUS)
        self.assertEqual(self.backend.events, [])

    def test_focus_loss_during_wait_releases_pressed_key(self) -> None:
        data = profile_data("once")
        data["steps"] = [
            {"type": "key", "key": "J", "action": "down"},
            {"type": "wait", "duration_ms": 200},
        ]
        profile = parse_macro_profile(data)
        self.controller.update_trigger(profile, True)
        time.sleep(0.04)
        self.backend.foreground = False
        self.assertTrue(self.controller.wait_for_idle(profile.id))
        self.assertFalse(self.backend.down)
        self.assertEqual(self.statuses[-1].state, MacroState.BLOCKED_FOCUS)

    def test_emergency_stop_interrupts_wait_and_releases_keys(self) -> None:
        data = profile_data("toggle_repeat")
        data["steps"] = [
            {"type": "key", "key": "J", "action": "down"},
            {"type": "wait", "duration_ms": 300},
        ]
        profile = parse_macro_profile(data)
        self.controller.update_trigger(profile, True)
        time.sleep(0.04)
        self.controller.stop_all()
        self.assertTrue(self.controller.wait_for_idle(profile.id))
        self.assertFalse(self.backend.down)
        self.assertEqual(self.statuses[-1].state, MacroState.STOPPED)

    def test_backend_failure_ends_in_error_without_stuck_key(self) -> None:
        self.backend.raise_on_down = True
        profile = parse_macro_profile(profile_data("once"))
        self.controller.update_trigger(profile, True)
        self.assertTrue(self.controller.wait_for_idle(profile.id))
        self.assertFalse(self.backend.down)
        self.assertEqual(self.statuses[-1].state, MacroState.ERROR)

    def test_stopping_one_macro_does_not_release_another_macros_key(self) -> None:
        first_data = profile_data("toggle_repeat")
        first_data["steps"] = [
            {"type": "key", "key": "J", "action": "down"},
            {"type": "wait", "duration_ms": 300},
        ]
        second_data = profile_data("toggle_repeat")
        second_data["id"] = "qa-toggle-second"
        second_data["trigger"]["key"] = "F7"
        second_data["steps"] = [
            {"type": "key", "key": "K", "action": "down"},
            {"type": "wait", "duration_ms": 300},
        ]
        first = parse_macro_profile(first_data)
        second = parse_macro_profile(second_data)
        self.controller.update_trigger(first, True)
        self.controller.update_trigger(first, False)
        self.controller.update_trigger(second, True)
        self.controller.update_trigger(second, False)
        time.sleep(0.05)
        self.assertEqual(self.backend.down, {"J", "K"})
        self.controller.stop(first.id)
        self.assertTrue(self.controller.wait_for_idle(first.id))
        self.assertEqual(self.backend.down, {"K"})
        self.controller.stop_all()
        self.assertTrue(self.controller.wait_for_idle(second.id))
        self.assertFalse(self.backend.down)


if __name__ == "__main__":
    unittest.main()
