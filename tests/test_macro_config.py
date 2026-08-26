from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from toolbox.macro_config import (
    default_profile_data,
    load_macro_config,
    save_macro_config,
    validate_profiles,
)
from toolbox.macro_model import MacroProfileError, parse_macro_profile


class MacroConfigTests(unittest.TestCase):
    def test_defaults_cover_all_modes_and_start_disabled(self) -> None:
        profiles = validate_profiles(default_profile_data())
        self.assertEqual(
            {profile.trigger.mode for profile in profiles},
            {"once", "hold_repeat", "toggle_repeat"},
        )
        self.assertTrue(all(not profile.enabled for profile in profiles))

    def test_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config" / "macros.json"
            profiles = tuple(parse_macro_profile(item) for item in default_profile_data())
            save_macro_config(path, profiles)
            loaded, errors = load_macro_config(path)
            self.assertEqual(errors, [])
            self.assertEqual(loaded, profiles)
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_duplicate_enabled_trigger_is_rejected(self) -> None:
        first, second = deepcopy(default_profile_data()[:2])
        first["enabled"] = True
        second["enabled"] = True
        second["trigger"] = deepcopy(first["trigger"])
        with self.assertRaises(MacroProfileError):
            validate_profiles([first, second])

    def test_corrupt_file_returns_error_without_replacing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "macros.json"
            path.write_text("{broken", encoding="utf-8")
            loaded, errors = load_macro_config(path)
            self.assertEqual(loaded, ())
            self.assertTrue(errors)
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
