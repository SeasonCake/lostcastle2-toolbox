from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, ValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_combat_v2_contract_covers_damage_resources_effects_and_status(self) -> None:
        schema = json.loads(
            (PROJECT_ROOT / "contracts" / "combat_event.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        common = {
            "schema_version": 2,
            "event_id": "qa-session:1",
            "session_id": "qa-session",
            "sequence": 1,
            "monotonic_ms": 250,
            "room_id": "room-1",
            "aggregate": True,
            "hook_path": "qa.fixture",
        }
        validator.validate(
            {
                **common,
                "event_type": "damage_resolution",
                "damage_direction": "dealt",
                "hit_id": 10,
                "target_id": "enemy-1",
                "pre_mitigation_damage": 128.4,
                "post_mitigation_damage": 125.0,
                "applied_hp_damage": 110.0,
                "settlement_damage": 125,
                "mitigated_damage": 3.4,
                "overkill_damage": 15.0,
                "damage_outcome": "applied",
                "is_boss": False,
            }
        )
        validator.validate(
            {
                **common,
                "event_id": "qa-session:2",
                "sequence": 2,
                "event_type": "resource_change",
                "resource": "mp",
                "resource_operation": "attempt",
                "requested_delta": 20,
                "effective_delta": 0,
                "value_before": 0,
                "value_after": 0,
                "max_before": 120,
                "max_after": 120,
                "blocked": True,
                "overflow": 0,
            }
        )
        validator.validate(
            {
                **common,
                "event_id": "qa-session:3",
                "sequence": 3,
                "event_type": "effect_stack",
                "effect_token": "P4-019",
                "effect_kind": "shield_charge",
                "stacks_before": 2,
                "stacks_after": 1,
                "stack_delta": -1,
            }
        )
        validator.validate(
            {
                **common,
                "event_id": "qa-session:4",
                "sequence": 4,
                "event_type": "status",
                "status": "live",
            }
        )
        validator.validate(
            {
                **common,
                "event_id": "qa-session:5",
                "sequence": 5,
                "event_type": "status",
                "status": "room_started",
                "room_id": "L2:MudSwamp:4:Map_MS_Battle_A003",
                "stage_level": 2,
                "scenario_id": "MudSwamp",
                "room_index": 4,
                "map_file_name": "Map_MS_Battle_A003",
            }
        )

        invalid_room_start = {
            **common,
            "event_id": "qa-session:6",
            "sequence": 6,
            "event_type": "status",
            "status": "room_started",
        }
        with self.assertRaises(ValidationError):
            validator.validate(invalid_room_start)

        invalid_room_index = {
            **common,
            "event_id": "qa-session:7",
            "sequence": 7,
            "event_type": "status",
            "status": "room_started",
            "room_id": "L2:MudSwamp:42:invalid",
            "stage_level": 2,
            "scenario_id": "MudSwamp",
            "room_index": 42,
            "map_file_name": "invalid",
        }
        with self.assertRaises(ValidationError):
            validator.validate(invalid_room_index)

        invalid_resource = {
            **common,
            "event_type": "resource_change",
            "resource": "hp",
        }
        with self.assertRaises(ValidationError):
            validator.validate(invalid_resource)

    def test_combat_source_registry_matches_its_contract(self) -> None:
        schema = json.loads(
            (
                PROJECT_ROOT / "contracts" / "combat_source_registry.schema.json"
            ).read_text(encoding="utf-8")
        )
        registry = json.loads(
            (PROJECT_ROOT / "assets" / "combat_sources.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)
        self.assertEqual(registry["entries"]["ExhaustProps#Banana_0"]["label"], "香蕉")
        self.assertEqual(registry["entries"]["P4-019"]["effect_kind"], "shield_charge")

    def test_game_location_registry_matches_current_game_names_and_routes(self) -> None:
        registry = json.loads(
            (PROJECT_ROOT / "assets" / "game_locations.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(registry["schema_version"], 1)
        self.assertEqual(
            registry["localization_source"],
            "StreamingAssets/Localization/UI_UniformType.json::ScenarioName_*",
        )
        self.assertEqual(
            registry["active_campaign_routes"],
            {
                "1": ["DarkForest"],
                "2": ["RuinedCemetery", "SaltpetreDesert", "MudSwamp"],
                "3": ["CrystalMountain", "IceCavern"],
                "4": ["CastleBridge", "Sewer"],
                "5": ["MainCastle"],
                "6": ["MageTower"],
            },
        )
        entries = registry["entries"]
        self.assertEqual(entries["DarkForest"]["label_zh_cn"], "黑森林")
        self.assertEqual(entries["RuinedCemetery"]["label_zh_cn"], "废村")
        self.assertEqual(entries["MudSwamp"]["stage_level"], 2)
        self.assertEqual(entries["SaltpetreDesert"]["stage_level"], 2)
        self.assertEqual(entries["CrystalMountain"]["stage_level"], 3)
        self.assertEqual(entries["IceCavern"]["stage_level"], 3)
        self.assertEqual(entries["CastleBridge"]["stage_level"], 4)
        self.assertEqual(entries["Sewer"]["stage_level"], 4)
        self.assertEqual(entries["MainCastle"]["stage_level"], 5)
        self.assertEqual(entries["MageTower"]["stage_level"], 6)
        self.assertIsNone(entries["MagmaCave"]["stage_level"])
        self.assertEqual(
            registry["localized_but_not_active_in_verified_package"],
            ["MagmaCave"],
        )

    def test_damage_event_contract_has_required_identity_and_damage_fields(self) -> None:
        schema = json.loads(
            (PROJECT_ROOT / "contracts" / "damage_event.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertIn("sequence", schema["required"])
        self.assertIn("hook_path", schema["required"])
        self.assertIn("applied_damage", schema["properties"])
        self.assertIn("settlement_damage", schema["properties"])
        self.assertIn("overkill_damage", schema["properties"])
        self.assertIn("target_hp_before", schema["properties"])
        self.assertIn("parent_hit_id", schema["properties"])
        self.assertIn("nesting_depth", schema["properties"])
        self.assertIn("checkpoint_totals", schema["properties"])
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(
            {
                "schema_version": 1,
                "event_type": "damage",
                "session_id": "qa-session",
                "sequence": 1,
                "monotonic_ms": 250,
                "room_id": "room-1",
                "target_id": "enemy-1",
                "applied_damage": 125.0,
                "settlement_damage": 125,
                "overkill_damage": 10.0,
                "target_hp_before": 125.0,
                "target_hp_after": 0.0,
                "parent_hit_id": None,
                "nesting_depth": 0,
                "is_boss": False,
                "hook_path": "OnHitActual.postfix",
            }
        )

    def test_macro_contract_is_bounded_and_foreground_only(self) -> None:
        schema = json.loads(
            (PROJECT_ROOT / "contracts" / "macro_profile.schema.json").read_text(
                encoding="utf-8"
            )
        )
        limits = schema["properties"]["limits"]["properties"]
        steps = schema["properties"]["steps"]
        self.assertTrue(limits["foreground_only"]["const"])
        self.assertGreaterEqual(limits["repeat_delay_ms"]["minimum"], 20)
        self.assertLessEqual(steps["maxItems"], 256)
        self.assertEqual(
            set(schema["properties"]["trigger"]["properties"]["mode"]["enum"]),
            {"once", "hold_repeat", "toggle_repeat"},
        )
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        valid_profile = {
            "schema_version": 1,
            "id": "qa-combo",
            "name": "QA Combo",
            "enabled": False,
            "trigger": {"key": "F6", "modifiers": [], "mode": "once"},
            "limits": {
                "foreground_only": True,
                "max_runtime_ms": 5000,
                "repeat_delay_ms": 80,
            },
            "steps": [{"type": "key", "key": "J", "action": "tap", "hold_ms": 60}],
        }
        validator.validate(valid_profile)
        valid_profile["limits"]["foreground_only"] = False
        with self.assertRaises(ValidationError):
            validator.validate(valid_profile)


if __name__ == "__main__":
    unittest.main()
