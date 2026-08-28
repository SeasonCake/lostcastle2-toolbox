from __future__ import annotations

from pathlib import Path
import unittest

from toolbox.combat_aggregator import (
    CombatAggregator,
    CombatEventError,
    ScenarioRegistry,
    SequenceError,
    SessionMismatchError,
    SourceRegistry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def common_event(event_type: str, sequence: int, **fields: object) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": 2,
        "event_id": f"session-a:{sequence}",
        "event_type": event_type,
        "session_id": "session-a",
        "sequence": sequence,
        "monotonic_ms": sequence * 1_000,
        "room_id": "room-1",
        "aggregate": True,
        "hook_path": "qa.fixture",
    }
    event.update(fields)
    return event


class CombatAggregatorTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = SourceRegistry.from_file(PROJECT_ROOT / "assets" / "combat_sources.json")
        scenario_registry = ScenarioRegistry.from_file(
            PROJECT_ROOT / "assets" / "game_locations.json"
        )
        self.aggregator = CombatAggregator(
            registry=registry,
            scenario_registry=scenario_registry,
        )
        self.aggregator.ingest(
            common_event("status", 0, monotonic_ms=0, status="session_started")
        )

    def test_damage_uses_explicit_aggregate_and_separates_settlement_from_hp_loss(self) -> None:
        dealt = common_event(
            "damage_resolution",
            1,
            damage_direction="dealt",
            settlement_damage=125,
            applied_hp_damage=110,
            mitigated_damage=0,
            overkill_damage=15,
            is_boss=True,
            source_token="summon.wisp",
        )
        nested_copy = {
            **dealt,
            "event_id": "session-a:2",
            "sequence": 2,
            "monotonic_ms": 1_001,
            "aggregate": False,
            "nesting_depth": 1,
        }
        taken = common_event(
            "damage_resolution",
            3,
            damage_direction="taken",
            settlement_damage=45,
            applied_hp_damage=44,
            mitigated_damage=1,
            overkill_damage=0,
            damage_outcome="applied",
            is_boss=False,
            source_token="enemy.melee",
        )
        absorbed = common_event(
            "damage_resolution",
            4,
            damage_direction="taken",
            settlement_damage=20,
            applied_hp_damage=0,
            mitigated_damage=20,
            overkill_damage=0,
            damage_outcome="absorbed",
            is_boss=False,
            source_token="enemy.projectile",
        )

        for event in (dealt, nested_copy, taken, absorbed):
            self.assertTrue(self.aggregator.ingest(event))

        snapshot = self.aggregator.snapshot(monotonic_ms=4_000)
        self.assertEqual(snapshot.total_damage, 125)
        self.assertEqual(snapshot.boss_damage, 125)
        self.assertEqual(snapshot.taken_settlement_damage, 65)
        self.assertEqual(snapshot.hp_damage_taken, 44)
        self.assertEqual(snapshot.mitigated_damage, 21)
        self.assertEqual(snapshot.overkill_damage, 0)
        self.assertEqual(snapshot.shield_absorbs, 1)
        self.assertEqual(snapshot.recent_dps, 12.5)
        self.assertEqual(snapshot.unknown_sources["summon.wisp"], 1)

    def test_hp_mp_overflow_blocking_and_shield_layers_are_generic_events(self) -> None:
        events = (
            common_event(
                "resource_change",
                1,
                resource="hp",
                effective_delta=32,
                blocked=False,
                overflow=3,
                source_token="ExhaustProps#Banana_0",
            ),
            common_event(
                "resource_change",
                2,
                resource="hp",
                effective_delta=-4,
                blocked=False,
                overflow=0,
                source_token="hp.settlement.adjustment",
            ),
            common_event(
                "resource_change",
                3,
                resource="mp",
                effective_delta=-24,
                blocked=False,
                overflow=0,
                source_token="skill.cost",
            ),
            common_event(
                "resource_change",
                4,
                resource="mp",
                effective_delta=20,
                blocked=False,
                overflow=5,
                source_token="mana.regen",
            ),
            common_event(
                "resource_change",
                5,
                resource="mp",
                effective_delta=0,
                blocked=True,
                overflow=0,
                source_token="curse.no_mana_regen",
            ),
            common_event(
                "effect_stack",
                6,
                effect_token="P4-019",
                effect_kind="shield_charge",
                stacks_after=1,
                stack_delta=-1,
                trigger_kind="hit_received",
                source_token="P4-019",
            ),
        )
        for event in events:
            self.aggregator.ingest(event)

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.effective_healing, 32)
        self.assertEqual(snapshot.hp_loss_other, 4)
        self.assertEqual(snapshot.mp_spent, 24)
        self.assertEqual(snapshot.mp_gained, 20)
        self.assertEqual(snapshot.mp_net, -4)
        self.assertEqual(snapshot.resource_blocked_attempts, 1)
        self.assertEqual(snapshot.resource_overflow, 8)
        self.assertEqual(snapshot.effect_stacks["P4-019"], 1)
        self.assertEqual(snapshot.shield_layers_consumed, 1)
        self.assertTrue(snapshot.source_breakdown["P4-019"]["known"])
        self.assertEqual(snapshot.source_breakdown["P4-019"]["label"], "护盾充能器")
        self.assertEqual(snapshot.source_breakdown["P4-019"]["effect_event_count"], 1)

    def test_official_mana_spend_wins_over_low_level_net_delta_and_new_round_resets(self) -> None:
        self.aggregator.ingest(
            common_event(
                "resource_change",
                1,
                aggregate=False,
                resource="mp",
                effective_delta=-12,
                blocked=False,
                overflow=0,
                source_token="resource.skill_cost",
            )
        )
        self.aggregator.ingest(
            common_event(
                "resource_change",
                2,
                resource="mp",
                effective_delta=-24,
                blocked=False,
                overflow=0,
                source_token="resource.skill_cost",
            )
        )
        self.aggregator.ingest(
            common_event(
                "resource_change",
                3,
                resource="mp",
                effective_delta=24,
                blocked=False,
                overflow=0,
                source_token="resource.mana_recovery",
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.mp_spent, 24)
        self.assertEqual(snapshot.mp_gained, 24)

        self.aggregator.ingest(
            common_event(
                "status",
                0,
                event_id="session-b:0",
                session_id="session-b",
                monotonic_ms=0,
                status="session_started",
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.mp_spent, 0)
        self.assertEqual(snapshot.mp_gained, 0)

    def test_fractional_mana_events_accumulate_before_ui_rounding(self) -> None:
        for sequence, delta in enumerate((-2.4, -2.4, -2.4, 0.987358, 9.2565), start=1):
            self.aggregator.ingest(
                common_event(
                    "resource_change",
                    sequence,
                    resource="mp",
                    effective_delta=delta,
                    blocked=False,
                    overflow=0,
                    source_token=(
                        "resource.skill_cost"
                        if delta < 0
                        else "resource.mana_recovery"
                    ),
                )
            )

        snapshot = self.aggregator.snapshot()
        self.assertAlmostEqual(snapshot.mp_spent, 7.2)
        self.assertAlmostEqual(snapshot.mp_gained, 10.243858)
        self.assertAlmostEqual(snapshot.mp_net, 3.043858)

    def test_ended_round_keeps_totals_until_the_next_session(self) -> None:
        now = [1_000]
        self.aggregator.clock_ms = lambda: now[0]
        self.aggregator.ingest(
            common_event(
                "resource_change",
                1,
                resource="mp",
                effective_delta=-24,
                blocked=False,
                overflow=0,
                source_token="resource.skill_cost",
            )
        )
        self.aggregator.ingest(
            common_event("status", 2, status="session_ended")
        )

        now[0] += 300_000
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.connection_state, "ended")
        self.assertEqual(snapshot.mp_spent, 24)

        self.aggregator.ingest(
            common_event(
                "status",
                0,
                event_id="session-b:0",
                session_id="session-b",
                monotonic_ms=0,
                status="session_started",
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.mp_spent, 0)

    def test_trigger_sources_do_not_need_aggregator_code_changes(self) -> None:
        self.aggregator.ingest(
            common_event(
                "trigger",
                1,
                trigger_kind="summon_kill",
                owner_player_id="player-1",
                source_token="gem.proc.on_summon_kill",
            )
        )
        snapshot = self.aggregator.snapshot()
        source = snapshot.source_breakdown["gem.proc.on_summon_kill"]
        self.assertEqual(source["trigger_count"], 1)
        self.assertFalse(source["known"])

    def test_duplicate_event_is_ignored_but_sequence_reuse_is_rejected(self) -> None:
        event = common_event("status", 1, status="live")
        self.assertTrue(self.aggregator.ingest(event))
        self.assertFalse(self.aggregator.ingest(event))
        with self.assertRaises(SequenceError):
            self.aggregator.ingest(
                common_event("status", 1, event_id="different-id", status="live")
            )

    def test_foreign_session_requires_an_explicit_start_boundary(self) -> None:
        with self.assertRaises(SessionMismatchError):
            self.aggregator.ingest(
                common_event("status", 1, session_id="session-b", status="live")
            )

        start = common_event(
            "status",
            0,
            event_id="session-b:0",
            session_id="session-b",
            monotonic_ms=0,
            status="session_started",
        )
        self.assertTrue(self.aggregator.ingest(start))
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.session_id, "session-b")
        self.assertEqual(snapshot.total_damage, 0)
        self.assertEqual(snapshot.connection_state, "live")

    def test_recent_dps_is_a_ten_second_average_and_expires_outside_window(self) -> None:
        self.aggregator.ingest(
            common_event(
                "damage_resolution",
                1,
                damage_direction="dealt",
                settlement_damage=90,
                applied_hp_damage=90,
                mitigated_damage=0,
                overkill_damage=0,
                is_boss=False,
            )
        )
        self.assertEqual(self.aggregator.snapshot(monotonic_ms=10_999).recent_dps, 9)
        self.assertEqual(self.aggregator.snapshot(monotonic_ms=11_001).recent_dps, 0)

    def test_room_started_keeps_stage_scenario_room_and_map_identity_separate(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                room_id="L4:CastleBridge:100:Map_CB_Boss_KnightMaster",
                status="room_started",
                stage_level=4,
                scenario_id="CastleBridge",
                room_index=100,
                map_file_name="Map_CB_Boss_KnightMaster",
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.current_stage_level, 4)
        self.assertEqual(snapshot.current_scenario_label, "黑城堡大桥")
        self.assertEqual(snapshot.current_room_index, 100)
        self.assertEqual(snapshot.current_map_file_name, "Map_CB_Boss_KnightMaster")

    def test_scenario_registry_preserves_current_branch_routes(self) -> None:
        self.assertEqual(
            self.aggregator.scenario_registry.route_ids_for_stage(2),
            ("RuinedCemetery", "SaltpetreDesert", "MudSwamp"),
        )
        self.assertEqual(
            self.aggregator.scenario_registry.route_ids_for_stage(3),
            ("CrystalMountain", "IceCavern"),
        )
        self.assertEqual(
            self.aggregator.scenario_registry.route_ids_for_stage(4),
            ("CastleBridge", "Sewer"),
        )

    def test_room_started_rejects_invalid_location_identity(self) -> None:
        with self.assertRaises(CombatEventError):
            self.aggregator.ingest(
                common_event(
                    "status",
                    1,
                    room_id="L2:MudSwamp:42:invalid",
                    status="room_started",
                    stage_level=2,
                    scenario_id="MudSwamp",
                    room_index=42,
                    map_file_name="invalid",
                )
            )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.connection_state, "live")
        self.assertEqual(snapshot.last_sequence, 0)
        self.assertIsNone(snapshot.current_room_id)

    def test_unknown_scenario_remains_visible_instead_of_using_a_wrong_name(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                room_id="L6:FutureMap:1:Map_FM_Battle_001",
                status="room_started",
                stage_level=6,
                scenario_id="FutureMap",
                room_index=1,
                map_file_name="Map_FM_Battle_001",
            )
        )
        self.assertEqual(
            self.aggregator.snapshot().current_scenario_label,
            "未知地图 · FutureMap",
        )


if __name__ == "__main__":
    unittest.main()
