from __future__ import annotations

import unittest

from toolbox.windows_input import (
    WindowsInputError,
    parse_hotkey_chord,
    send_hotkey,
)


class FakeBackend:
    def __init__(self, *, foreground: bool = True) -> None:
        self.foreground = foreground
        self.events: list[tuple[str, str]] = []

    def is_target_foreground(self) -> bool:
        return self.foreground

    def key_down(self, key: str) -> None:
        self.events.append(("down", key))

    def key_up(self, key: str) -> None:
        self.events.append(("up", key))


class WindowsInputHotkeyTests(unittest.TestCase):
    def test_insert_alias_and_modifier_chord_are_normalized(self) -> None:
        self.assertEqual(parse_hotkey_chord("Insert"), ("INS",))
        self.assertEqual(parse_hotkey_chord("Alt + 1"), ("ALT", "1"))

    def test_invalid_or_unsupported_chords_fail_closed(self) -> None:
        for value in ("", "F13", "CTRL", "A+CTRL", "CTRL+CTRL+F5"):
            with self.subTest(value=value), self.assertRaises(WindowsInputError):
                parse_hotkey_chord(value)

    def test_send_hotkey_requires_game_foreground_and_releases_in_reverse(self) -> None:
        backend = FakeBackend()
        send_hotkey(backend, "Alt+1", hold_seconds=0)
        self.assertEqual(
            backend.events,
            [("down", "ALT"), ("down", "1"), ("up", "1"), ("up", "ALT")],
        )

        background = FakeBackend(foreground=False)
        with self.assertRaises(WindowsInputError):
            send_hotkey(background, "INS", hold_seconds=0)
        self.assertEqual(background.events, [])


if __name__ == "__main__":
    unittest.main()
