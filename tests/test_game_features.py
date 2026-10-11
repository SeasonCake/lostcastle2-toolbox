from pathlib import Path
import json
import tempfile
import time
import unittest

from toolbox.game_features import (
    FEATURE_DIRECTORY, GameFeatureError, GameFeatureService,
    feature_value, parse_feature_snapshot,
)


def payload(now: int, *, pid: int = 42) -> dict:
    return {
        "schema_version": 1, "game_pid": pid, "captured_at": now,
        "state": "ready", "team": [{
            "slot": 1, "name": "队友", "is_local": False, "resources_state": "not_synced",
            "resources": {"gold": 0}, "items": [], "inscriptions": [],
        }],
        "loadout": {"in_camp": True, "equipment": [{"id": "Sword_001", "name": "测试武器", "kind": "Weapon"}], "inscriptions": [], "gems": [], "enchantments": []},
    }


class GameFeatureTests(unittest.TestCase):
    def test_unsynced_zero_is_presented_as_unknown_while_known_zero_remains_zero(self):
        raw = payload(10000)
        parsed = parse_feature_snapshot(raw, 42, 10001)
        self.assertEqual(parsed.state, "ready")
        self.assertEqual(feature_value(parsed.team[0]["resources"]["gold"]), "未同步")
        raw["team"][0]["resources_state"] = "ready"
        self.assertEqual(feature_value(parse_feature_snapshot(raw, 42, 10001).team[0]["resources"]["gold"]), "0")
        self.assertEqual(feature_value(float("nan")), "未同步")

    def test_old_process_stale_future_and_colliding_roster_are_not_live_data(self):
        for patch, expected in (({"game_pid": 43}, "waiting"), ({"captured_at": 0}, "stale"), ({"captured_at": 10001}, "stale")):
            raw = payload(10000); raw.update(patch)
            self.assertEqual(parse_feature_snapshot(raw, 42, 10000).state, expected)
        raw = payload(10000); raw["team"] *= 2
        self.assertEqual(parse_feature_snapshot(raw, 42, 10000).state, "invalid")

    def test_partial_and_bad_loadout_do_not_become_ready(self):
        for key in ("equipment", "inscriptions", "gems", "enchantments"):
            raw = payload(10000); raw["loadout"][key] = "invalid"
            self.assertEqual(parse_feature_snapshot(raw, 42, 10000).state, "invalid")

    def test_team_defaults_off_loadout_viewing_on_and_switches_preserve_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "LostCastle2.exe"; game.write_bytes(b"fixture")
            service = GameFeatureService(lambda: game)
            self.assertEqual(service.settings(), {"team_enabled": False, "loadout_enabled": True})
            service.set_enabled("team_enabled", True)
            service.set_enabled("loadout_enabled", True)
            service.set_enabled("team_enabled", False)
            self.assertEqual(service.settings(), {"team_enabled": False, "loadout_enabled": True})
            with self.assertRaises(GameFeatureError):
                service.set_enabled("unknown", True)

    def test_request_requires_enabled_feature_fresh_camp_and_preserves_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "LostCastle2.exe"; game.write_bytes(b"fixture")
            service = GameFeatureService(lambda: game)
            service.set_enabled("loadout_enabled", False)
            with self.assertRaises(GameFeatureError):
                service.request("equipment", 42, item_id="Sword_001")
            service.set_enabled("loadout_enabled", True)
            directory = game.parent / FEATURE_DIRECTORY
            raw = payload(round(time.time() * 1000)); raw["loadout"]["in_camp"] = False
            (directory / "snapshot.json").write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(GameFeatureError):
                service.request("equipment", 42, item_id="Sword_001")
            raw["loadout"]["in_camp"] = True
            (directory / "snapshot.json").write_text(json.dumps(raw), encoding="utf-8")
            request = service.request("equipment", 42, item_id="Sword_001")
            written = json.loads((directory / "request.json").read_text(encoding="utf-8"))
            self.assertEqual(written["request_id"], request)
            self.assertEqual(written["item_id"], "Sword_001")
            self.assertEqual(written["game_pid"], 42)
            with self.assertRaises(GameFeatureError):
                service.request("equipment", 42, item_id="Sword_002")

    def test_old_result_is_not_confirmation_of_current_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "LostCastle2.exe"; game.write_bytes(b"fixture")
            service = GameFeatureService(lambda: game)
            service.last_request_id = "a" * 32
            directory = game.parent / FEATURE_DIRECTORY; directory.mkdir(parents=True)
            path = directory / "result.json"
            path.write_text(json.dumps({"request_id": "b" * 32, "game_pid": 42, "state": "complete"}), encoding="utf-8")
            self.assertIsNone(service.result(42))
            path.write_text(json.dumps({"request_id": "a" * 32, "game_pid": 42, "state": "error", "message": "未就绪"}), encoding="utf-8")
            self.assertEqual(service.result(42)["state"], "error")

    def test_oversized_snapshot_is_not_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "LostCastle2.exe"; game.write_bytes(b"fixture")
            directory = game.parent / FEATURE_DIRECTORY; directory.mkdir(parents=True)
            (directory / "snapshot.json").write_bytes(b" " * (2 * 1024 * 1024 + 1))
            self.assertEqual(GameFeatureService(lambda: game).snapshot(42).state, "invalid")

    def test_malformed_nested_data_and_duplicate_choices_are_not_exposed(self):
        for patch in ({"equipment": [{"name": "缺失身份"}]}, {"equipment": [{"id": "s", "name": [], "kind": "Weapon"}]}, {"gems": [{"id": True, "name": "石头"}]}, {"inscriptions": [{"id": "i", "name": "刻印", "slots": [{"slot": 0}, {"slot": 0}]}]}, {"in_camp": "true"}):
            with self.subTest(patch=patch):
                raw = payload(10000); raw["loadout"].update(patch)
                self.assertEqual(parse_feature_snapshot(raw, 42, 10000).state, "invalid")
        raw = payload(10000); raw["loadout"]["equipment"] *= 2
        self.assertEqual(parse_feature_snapshot(raw, 42, 10000).state, "invalid")
        raw = payload(10000); raw["team"][0]["inscriptions"] = [{"name": "刻印", "gems": ["invalid"]}]
        self.assertEqual(parse_feature_snapshot(raw, 42, 10000).state, "invalid")

    def test_selection_must_still_exist_and_timeout_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / "LostCastle2.exe"; game.write_bytes(b"fixture")
            service = GameFeatureService(lambda: game)
            directory = game.parent / FEATURE_DIRECTORY; directory.mkdir(parents=True)
            (directory / "snapshot.json").write_text(json.dumps(payload(round(time.time() * 1000))), encoding="utf-8")
            with self.assertRaises(GameFeatureError):
                service.request("equipment", 42, item_id="Removed_Item")
            self.assertFalse((directory / "request.json").exists())
            service.request("equipment", 42, item_id="Sword_001")
            self.assertIsNone(service.result(42))
            service.last_request_time -= 16000
            self.assertEqual(service.result(42)["state"], "error")
            self.assertIn("不会自动重复", service.result(42)["message"])


if __name__ == "__main__":
    unittest.main()
