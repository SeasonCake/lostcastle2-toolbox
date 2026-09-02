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
    def test_foreign_terminal_receipt_is_an_explicit_safe_boundary(self) -> None:
        aggregator = CombatAggregator()
        aggregator.ingest(
            common_event("status", 0, session_id="session-a", status="session_started")
        )
        aggregator.ingest(
            common_event("status", 73, session_id="session-b", status="session_ended")
        )

        snapshot = aggregator.snapshot()
        self.assertEqual(snapshot.session_id, "session-b")
        self.assertEqual(snapshot.connection_state, "ended")
        self.assertEqual(snapshot.personal_damage, 0)

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
        self.assertEqual(snapshot.personal_damage, 125)
        self.assertEqual(snapshot.personal_boss_damage, 125)
        self.assertEqual(snapshot.personal_recent_dps, 12.5)
        self.assertEqual(snapshot.taken_settlement_damage, 65)
        self.assertEqual(snapshot.hp_damage_taken, 44)
        self.assertEqual(snapshot.mitigated_damage, 21)
        self.assertEqual(snapshot.overkill_damage, 0)
        self.assertEqual(snapshot.shield_absorbs, 1)
        self.assertEqual(snapshot.recent_dps, 12.5)
        self.assertEqual(snapshot.unknown_sources["summon.wisp"], 1)
        self.assertEqual(snapshot.unattributed_damage, 125)

    def test_party_damage_is_owned_without_guessing_unattributed_events(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "opaque-local", "player_slot": 0, "is_local": True},
                    {"player_id": "opaque-peer", "player_slot": 1, "is_local": False},
                ],
            )
        )
        for sequence, damage, boss, owner in (
            (2, 120, False, "opaque-local"),
            (3, 80, True, "opaque-peer"),
            (4, 20, False, None),
        ):
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=boss,
                    owner_player_id=owner,
                    source_token="combat.player.normal",
                )
            )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.detected_player_count, 2)
        self.assertEqual(snapshot.total_damage, 220)
        self.assertEqual(snapshot.personal_damage, 120)
        self.assertEqual(snapshot.personal_boss_damage, 0)
        self.assertEqual(snapshot.personal_recent_dps, 12.0)
        self.assertEqual(snapshot.unattributed_damage, 20)
        self.assertEqual(snapshot.unattributed_boss_damage, 0)
        self.assertEqual(snapshot.player_breakdown["opaque-local"]["label"], "自己 · P1")
        self.assertEqual(snapshot.player_breakdown["opaque-local"]["damage_dealt"], 120)
        self.assertAlmostEqual(
            snapshot.player_breakdown["opaque-local"]["damage_share"],
            120 / 220,
        )
        self.assertEqual(snapshot.player_breakdown["opaque-peer"]["label"], "P2")
        self.assertEqual(snapshot.player_breakdown["opaque-peer"]["boss_damage"], 80)
        self.assertEqual(
            snapshot.personal_source_breakdown["combat.player.normal"]["damage_dealt"],
            120,
        )
        self.assertNotIn("nickname", str(snapshot.to_dict()).lower())

        self.aggregator.ingest(
            common_event(
                "status",
                5,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "opaque-local", "player_slot": 0, "is_local": True},
                ],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.detected_player_count, 1)
        self.assertFalse(snapshot.player_breakdown["opaque-peer"]["active"])
        self.assertEqual(snapshot.player_breakdown["opaque-peer"]["damage_dealt"], 80)

    def test_live_party_totals_replace_and_final_can_correct_downward(self) -> None:
        members = [
            {"player_id": "opaque-local", "player_slot": 0, "is_local": True},
            {"player_id": "opaque-peer", "player_slot": 1, "is_local": False},
        ]
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=members,
            )
        )
        for sequence, owner, damage in (
            (2, "opaque-local", 120),
            (3, "opaque-peer", 80),
        ):
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=False,
                    owner_player_id=owner,
                    source_token="combat.player.normal",
                )
            )
        self.aggregator.ingest(
            common_event(
                "status",
                4,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {**members[0], "live_damage": 150, "live_boss_damage": 20},
                    {**members[1], "live_damage": 240, "live_boss_damage": 40},
                ],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertTrue(snapshot.live_damage_complete)
        self.assertFalse(snapshot.official_damage_complete)
        self.assertEqual(snapshot.total_damage, 390)
        self.assertEqual(snapshot.boss_damage, 60)

        # Between room-boundary cache anchors, accepted per-hit deltas stay live.
        for sequence, owner, damage in (
            (5, "opaque-local", 30),
            (6, "opaque-peer", 20),
        ):
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=False,
                    owner_player_id=owner,
                    source_token="combat.player.normal",
                )
            )
        self.assertEqual(self.aggregator.snapshot().total_damage, 440)

        # Repeating the same anchor for a roster refresh must not erase the delta.
        self.aggregator.ingest(
            common_event(
                "status",
                7,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {**members[0], "live_damage": 150, "live_boss_damage": 20},
                    {**members[1], "live_damage": 240, "live_boss_damage": 40},
                ],
            )
        )
        self.assertEqual(self.aggregator.snapshot().total_damage, 440)

        # A room boundary without a changed live snapshot preserves delayed
        # official-cache deltas (observed in the real MainCastle story room).
        self.aggregator.ingest(
            common_event(
                "status",
                8,
                status="room_started",
                aggregate=False,
                room_id="L1:Test:2",
                stage_level=1,
                scenario_id="Test",
                room_index=2,
                map_file_name="Map_Test_2",
            )
        )
        self.assertEqual(self.aggregator.snapshot().total_damage, 440)

        # If any slot receives a changed live snapshot, every slot re-anchors;
        # unchanged slots must not retain the prior provisional room delta.
        self.aggregator.ingest(
            common_event(
                "status",
                9,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {**members[0], "live_damage": 150, "live_boss_damage": 20},
                    {**members[1], "live_damage": 220, "live_boss_damage": 40},
                ],
            )
        )
        self.assertEqual(self.aggregator.snapshot().total_damage, 370)

        # Live cache snapshots are replaceable, including a downward correction.
        self.aggregator.ingest(
            common_event(
                "status",
                10,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {**members[0], "live_damage": 140, "live_boss_damage": 10},
                    {**members[1], "live_damage": 220, "live_boss_damage": 30},
                ],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 360)
        self.assertEqual(snapshot.boss_damage, 40)

        # Exact SyncEnd official values remain authoritative even when lower.
        self.aggregator.ingest(
            common_event(
                "status",
                11,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        **members[0],
                        "official_damage": 100,
                        "official_boss_damage": 5,
                    },
                    {
                        **members[1],
                        "official_damage": 200,
                        "official_boss_damage": 15,
                    },
                ],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertTrue(snapshot.official_damage_complete)
        self.assertEqual(snapshot.total_damage, 300)
        self.assertEqual(snapshot.boss_damage, 20)
        self.assertEqual(
            snapshot.player_breakdown["opaque-local"]["live_damage"],
            None,
        )
        self.assertEqual(
            snapshot.player_breakdown["opaque-local"]["last_live_damage"],
            140,
        )
        self.assertEqual(
            snapshot.player_breakdown["opaque-local"]["official_damage"],
            100,
        )
        self.assertEqual(
            snapshot.player_breakdown["opaque-local"]["observed_damage_dealt"],
            150,
        )

    def test_missing_live_snapshot_falls_back_to_observed(self) -> None:
        member = {"player_id": "opaque-local", "player_slot": 0, "is_local": True}
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[member],
            )
        )
        self.aggregator.ingest(
            common_event(
                "damage_resolution",
                2,
                damage_direction="dealt",
                settlement_damage=120,
                applied_hp_damage=120,
                mitigated_damage=0,
                overkill_damage=0,
                is_boss=True,
                owner_player_id="opaque-local",
                source_token="combat.player.normal",
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                3,
                status="party_updated",
                aggregate=False,
                party_members=[{**member, "live_damage": 90, "live_boss_damage": 30}],
            )
        )
        self.assertEqual(self.aggregator.snapshot().total_damage, 90)

        self.aggregator.ingest(
            common_event(
                "status",
                4,
                status="party_updated",
                aggregate=False,
                party_members=[member],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertFalse(snapshot.live_damage_complete)
        self.assertEqual(snapshot.total_damage, 120)
        self.assertEqual(snapshot.boss_damage, 120)

    def test_official_party_totals_override_observed_damage_without_rewriting_sources(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "opaque-local",
                        "player_slot": 0,
                        "is_local": True,
                    },
                    {
                        "player_id": "opaque-peer",
                        "player_slot": 1,
                        "is_local": False,
                    },
                ],
            )
        )
        for sequence, owner, damage, boss in (
            (2, "opaque-local", 120, True),
            (3, "opaque-peer", 80, False),
            (4, None, 20, False),
        ):
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=boss,
                    owner_player_id=owner,
                    source_token="combat.player.normal",
                )
            )
        self.aggregator.ingest(
            common_event(
                "status",
                5,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "opaque-local",
                        "player_slot": 0,
                        "is_local": True,
                        "official_damage": 150,
                        "official_boss_damage": 30,
                    },
                    {
                        "player_id": "opaque-peer",
                        "player_slot": 1,
                        "is_local": False,
                        "official_damage": 240,
                        "official_boss_damage": 90,
                    },
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertTrue(snapshot.official_damage_complete)
        self.assertTrue(snapshot.official_boss_damage_complete)
        self.assertEqual(snapshot.total_damage, 390)
        self.assertEqual(snapshot.boss_damage, 120)
        self.assertEqual(snapshot.personal_damage, 150)
        self.assertEqual(snapshot.personal_boss_damage, 30)
        self.assertEqual(
            snapshot.player_breakdown["opaque-local"]["observed_damage_dealt"],
            120,
        )
        self.assertEqual(
            snapshot.player_breakdown["opaque-local"]["official_damage"],
            150,
        )
        self.assertEqual(
            snapshot.personal_source_breakdown["combat.player.normal"]["damage_dealt"],
            120,
        )
        self.assertEqual(snapshot.unattributed_damage, 20)
        self.assertAlmostEqual(
            snapshot.player_breakdown["opaque-peer"]["damage_share"],
            240 / 390,
        )

        # A transient stale network snapshot must not roll cumulative official
        # totals backwards.
        self.aggregator.ingest(
            common_event(
                "status",
                6,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "opaque-local",
                        "player_slot": 0,
                        "is_local": True,
                        "official_damage": 140,
                        "official_boss_damage": 20,
                    },
                    {
                        "player_id": "opaque-peer",
                        "player_slot": 1,
                        "is_local": False,
                        "official_damage": 220,
                        "official_boss_damage": 80,
                    },
                ],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 390)
        self.assertEqual(snapshot.boss_damage, 120)

    def test_partial_official_coverage_keeps_team_denominator_consistent(self) -> None:
        members = [
            {
                "player_id": f"player-{index}",
                "player_slot": index,
                "is_local": index == 0,
            }
            for index in range(4)
        ]
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=members,
            )
        )
        observed = (11_412, 1_635, 10_008, 8_780)
        for sequence, (member, damage) in enumerate(
            zip(members, observed, strict=True),
            start=2,
        ):
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=False,
                    owner_player_id=member["player_id"],
                    source_token="combat.player.normal",
                )
            )
        self.aggregator.ingest(
            common_event(
                "status",
                6,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {**members[0], "official_damage": 31_835},
                    *members[1:],
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertFalse(snapshot.official_damage_complete)
        self.assertEqual(snapshot.personal_damage, 31_835)
        self.assertEqual(snapshot.total_damage, 52_258)
        self.assertAlmostEqual(combat_personal_share := (
            snapshot.personal_damage / snapshot.total_damage
        ), 31_835 / 52_258)
        self.assertLess(combat_personal_share, 1.0)
        self.assertAlmostEqual(
            sum(row["damage_share"] for row in snapshot.player_breakdown.values()),
            1.0,
        )
        self.assertEqual(
            [row["label"] for row in snapshot.player_breakdown.values()],
            ["自己 · P1", "P2", "P3", "P4"],
        )

    def test_departed_player_keeps_history_but_leaves_visible_team_total(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "local",
                        "player_slot": 0,
                        "is_local": True,
                        "official_damage": 100,
                        "official_boss_damage": 40,
                    },
                    {
                        "player_id": "peer",
                        "player_slot": 1,
                        "is_local": False,
                        "official_damage": 200,
                        "official_boss_damage": 80,
                    },
                ],
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                2,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "local",
                        "player_slot": 0,
                        "is_local": True,
                        "official_damage": 160,
                        "official_boss_damage": 60,
                    },
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 160)
        self.assertEqual(snapshot.boss_damage, 60)
        self.assertEqual(snapshot.personal_damage, 160)
        self.assertFalse(snapshot.player_breakdown["peer"]["active"])
        self.assertEqual(snapshot.player_breakdown["peer"]["damage_dealt"], 200)

    def test_real_0412_multiplayer_gap_is_closed_by_official_party_totals(self) -> None:
        observed = (
            ("local", 7_293_748, 2_465_442),
            ("peer-1", 9_924_156, 5_062_190),
            ("peer-2", 9_597_741, 4_646_284),
        )
        official = (
            ("local", 8_475_632, 2_331_390),
            ("peer-1", 10_035_357, 4_012_909),
            ("peer-2", 13_163_701, 5_770_246),
        )
        members = [
            {
                "player_id": player_id,
                "player_slot": slot,
                "is_local": slot == 0,
            }
            for slot, (player_id, _damage, _boss) in enumerate(observed)
        ]
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=members,
            )
        )
        sequence = 2
        for player_id, damage, boss in observed:
            for value, is_boss in ((boss, True), (damage - boss, False)):
                self.aggregator.ingest(
                    common_event(
                        "damage_resolution",
                        sequence,
                        damage_direction="dealt",
                        settlement_damage=value,
                        applied_hp_damage=value,
                        mitigated_damage=0,
                        overkill_damage=0,
                        is_boss=is_boss,
                        owner_player_id=player_id,
                        source_token="combat.player.normal",
                    )
                )
                sequence += 1
        self.aggregator.ingest(
            common_event(
                "status",
                sequence,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        **members[slot],
                        "official_damage": damage,
                        "official_boss_damage": boss,
                    }
                    for slot, (_player_id, damage, boss) in enumerate(official)
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 31_674_690)
        self.assertEqual(snapshot.boss_damage, 12_114_545)
        self.assertEqual(snapshot.personal_damage, 8_475_632)
        self.assertEqual(snapshot.personal_boss_damage, 2_331_390)
        self.assertEqual(
            snapshot.total_damage - sum(item[1] for item in observed),
            4_859_045,
        )
        for player_id, damage, boss in official:
            row = snapshot.player_breakdown[player_id]
            self.assertEqual(row["damage_dealt"], damage)
            self.assertEqual(row["boss_damage"], boss)

    def test_non_host_local_player_is_bound_by_flag_not_slot_zero(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "remote-host", "player_slot": 0, "is_local": False},
                    {"player_id": "local-client", "player_slot": 2, "is_local": True},
                ],
            )
        )
        for sequence, owner, damage, boss in (
            (2, "remote-host", 90, True),
            (3, "local-client", 140, False),
            (4, None, 30, False),
        ):
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=boss,
                    owner_player_id=owner,
                    source_token="combat.player.normal",
                )
            )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 260)
        self.assertEqual(snapshot.personal_damage, 140)
        self.assertEqual(snapshot.personal_boss_damage, 0)
        self.assertEqual(snapshot.player_breakdown["local-client"]["label"], "自己 · P3")
        self.assertEqual(snapshot.player_breakdown["local-client"]["player_slot"], 2)
        self.assertFalse(snapshot.player_breakdown["remote-host"]["is_local"])

    def test_inactive_identity_does_not_create_a_teammate_number_gap(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "local", "player_slot": 2, "is_local": True},
                    {"player_id": "peer-old", "player_slot": 0, "is_local": False},
                ],
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                2,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "local", "player_slot": 2, "is_local": True},
                    {"player_id": "peer-new", "player_slot": 0, "is_local": False},
                ],
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.player_breakdown["peer-old"]["label"], "P1（离队）")
        self.assertEqual(snapshot.player_breakdown["peer-new"]["label"], "P1")

    def test_replaced_token_in_same_slot_does_not_double_official_team_total(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "local",
                        "player_slot": 2,
                        "is_local": True,
                        "official_damage": 50,
                        "official_boss_damage": 10,
                    },
                    {
                        "player_id": "peer-old",
                        "player_slot": 0,
                        "is_local": False,
                        "official_damage": 100,
                        "official_boss_damage": 20,
                    },
                ],
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                2,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "local",
                        "player_slot": 2,
                        "is_local": True,
                        "official_damage": 60,
                        "official_boss_damage": 15,
                    },
                    {
                        "player_id": "peer-new",
                        "player_slot": 0,
                        "is_local": False,
                        "official_damage": 150,
                        "official_boss_damage": 30,
                    },
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 210)
        self.assertEqual(snapshot.boss_damage, 45)
        self.assertEqual(snapshot.personal_damage, 60)
        self.assertFalse(snapshot.player_breakdown["peer-old"]["active"])
        self.assertTrue(snapshot.player_breakdown["peer-new"]["active"])

    def test_departed_slot_is_not_kept_in_the_visible_team_denominator(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "local", "player_slot": 0, "is_local": True},
                    {"player_id": "peer-2", "player_slot": 1, "is_local": False},
                    {"player_id": "peer-3", "player_slot": 2, "is_local": False},
                    {"player_id": "peer-4", "player_slot": 3, "is_local": False},
                ],
            )
        )
        self.aggregator.ingest(
            common_event(
                "damage_resolution",
                2,
                damage_direction="dealt",
                settlement_damage=16_606_274,
                applied_hp_damage=16_606_274,
                mitigated_damage=0,
                overkill_damage=0,
                is_boss=True,
                owner_player_id="peer-4",
                source_token="combat.player.normal",
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                3,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "local", "player_slot": 0, "is_local": True},
                    {"player_id": "peer-2", "player_slot": 1, "is_local": False},
                    {"player_id": "peer-3", "player_slot": 2, "is_local": False},
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 0)
        self.assertFalse(snapshot.player_breakdown["peer-4"]["active"])
        self.assertEqual(
            sum(
                row["damage_dealt"]
                for row in snapshot.player_breakdown.values()
                if row["active"]
            ),
            snapshot.total_damage,
        )

    def test_local_token_replacement_excludes_the_inactive_local_history(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {"player_id": "local-old", "player_slot": 0, "is_local": True},
                    {"player_id": "remote", "player_slot": 1, "is_local": False},
                ],
            )
        )
        for sequence, owner, damage in (
            (2, "local-old", 100),
            (4, "local-new", 20),
        ):
            if sequence == 4:
                self.aggregator.ingest(
                    common_event(
                        "status",
                        3,
                        status="party_updated",
                        aggregate=False,
                        party_members=[
                            {"player_id": "local-new", "player_slot": 0, "is_local": True},
                            {"player_id": "remote", "player_slot": 1, "is_local": False},
                        ],
                    )
                )
            self.aggregator.ingest(
                common_event(
                    "damage_resolution",
                    sequence,
                    damage_direction="dealt",
                    settlement_damage=damage,
                    applied_hp_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    is_boss=False,
                    owner_player_id=owner,
                    source_token="combat.player.normal",
                )
            )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 20)
        self.assertEqual(snapshot.personal_damage, 20)
        self.assertFalse(snapshot.player_breakdown["local-old"]["active"])
        self.assertTrue(snapshot.player_breakdown["local-new"]["active"])

    def test_same_session_local_slot_change_keeps_stable_identity_and_live_total(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "player-1",
                        "player_slot": 0,
                        "is_local": False,
                        "live_damage": 45888,
                        "live_boss_damage": 0,
                    },
                    {
                        "player_id": "player-2",
                        "player_slot": 1,
                        "is_local": False,
                        "live_damage": 35652,
                        "live_boss_damage": 0,
                    },
                    {
                        "player_id": "player-3",
                        "player_slot": 2,
                        "is_local": False,
                        "live_damage": 41555,
                        "live_boss_damage": 0,
                    },
                    {
                        "player_id": "player-4",
                        "player_slot": 3,
                        "is_local": True,
                        "live_damage": 3338,
                        "live_boss_damage": 0,
                    },
                ],
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                2,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "player-4",
                        "player_slot": 0,
                        "is_local": True,
                        "live_damage": 3338,
                        "live_boss_damage": 0,
                    }
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.personal_damage, 3338)
        self.assertEqual(snapshot.total_damage, 3338)
        self.assertTrue(snapshot.player_breakdown["player-4"]["active"])
        self.assertEqual(snapshot.player_breakdown["player-4"]["player_slot"], 0)
        self.assertFalse(snapshot.player_breakdown["player-1"]["active"])

    def test_r19_new_local_token_positive_control_reproduces_45888(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "player-1",
                        "player_slot": 0,
                        "is_local": False,
                        "live_damage": 45888,
                        "live_boss_damage": 0,
                    },
                    {
                        "player_id": "player-4",
                        "player_slot": 3,
                        "is_local": True,
                        "live_damage": 3338,
                        "live_boss_damage": 0,
                    },
                ],
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                2,
                status="party_updated",
                aggregate=False,
                party_members=[
                    {
                        "player_id": "player-5",
                        "player_slot": 0,
                        "is_local": True,
                        "live_damage": 45888,
                        "live_boss_damage": 0,
                    }
                ],
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.personal_damage, 45888)
        self.assertTrue(snapshot.player_breakdown["player-5"]["active"])
        self.assertFalse(snapshot.player_breakdown["player-4"]["active"])

    def test_party_update_rejects_duplicate_player_slot(self) -> None:
        with self.assertRaises(CombatEventError):
            self.aggregator.ingest(
                common_event(
                    "status",
                    1,
                    status="party_updated",
                    aggregate=False,
                    party_members=[
                        {"player_id": "local", "player_slot": 3, "is_local": True},
                        {"player_id": "peer", "player_slot": 3, "is_local": False},
                    ],
                )
            )

    def test_party_update_rejects_duplicate_player_identity(self) -> None:
        with self.assertRaises(CombatEventError):
            self.aggregator.ingest(
                common_event(
                    "status",
                    1,
                    status="party_updated",
                    aggregate=False,
                    party_members=[
                        {"player_id": "same", "player_slot": 0, "is_local": True},
                        {"player_id": "same", "player_slot": 1, "is_local": False},
                    ],
                )
            )

    def test_recoverable_bridge_issue_stays_live_and_visible(self) -> None:
        self.aggregator.ingest(
            common_event(
                "status",
                1,
                status="live",
                detail="degraded:damage_snapshot_missing",
                aggregate=False,
            )
        )
        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.connection_state, "live")
        self.assertEqual(
            snapshot.diagnostic_warning,
            "degraded:damage_snapshot_missing",
        )

    def test_two_to_sixteen_player_rosters_keep_every_owner_distinct(self) -> None:
        for party_size in range(2, 17):
            with self.subTest(party_size=party_size):
                registry = SourceRegistry.from_file(
                    PROJECT_ROOT / "assets" / "combat_sources.json"
                )
                scenarios = ScenarioRegistry.from_file(
                    PROJECT_ROOT / "assets" / "game_locations.json"
                )
                aggregator = CombatAggregator(
                    registry=registry,
                    scenario_registry=scenarios,
                )
                aggregator.ingest(
                    common_event("status", 0, monotonic_ms=0, status="session_started")
                )
                members = [
                    {
                        "player_id": f"opaque-player-{index}",
                        "player_slot": index,
                        "is_local": index == 0,
                    }
                    for index in range(party_size)
                ]
                aggregator.ingest(
                    common_event(
                        "status",
                        1,
                        status="party_updated",
                        aggregate=False,
                        party_members=members,
                    )
                )
                sequence = 2
                expected: dict[str, int] = {
                    str(member["player_id"]): 0 for member in members
                }
                for round_index in range(250):
                    for player_index, member in enumerate(members):
                        damage = (player_index + 1) * 10 + round_index % 3
                        player_id = str(member["player_id"])
                        expected[player_id] += damage
                        aggregator.ingest(
                            common_event(
                                "damage_resolution",
                                sequence,
                                damage_direction="dealt",
                                settlement_damage=damage,
                                applied_hp_damage=damage,
                                mitigated_damage=0,
                                overkill_damage=0,
                                is_boss=round_index % 10 == 0,
                                owner_player_id=player_id,
                                source_token="combat.player.normal",
                            )
                        )
                        sequence += 1

                snapshot = aggregator.snapshot(monotonic_ms=sequence * 1_000)
                self.assertEqual(snapshot.detected_player_count, party_size)
                self.assertEqual(snapshot.total_damage, sum(expected.values()))
                self.assertEqual(snapshot.unattributed_damage, 0)
                for player_index, member in enumerate(members):
                    player_id = str(member["player_id"])
                    row = snapshot.player_breakdown[player_id]
                    self.assertTrue(row["active"])
                    self.assertEqual(row["damage_dealt"], expected[player_id])
                    self.assertEqual(
                        row["label"],
                        "自己 · P1" if player_index == 0 else f"P{player_index + 1}",
                    )

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

    def test_same_session_transport_resume_keeps_totals_and_marks_gap(self) -> None:
        self.aggregator.ingest(
            common_event(
                "damage_resolution",
                1,
                damage_direction="dealt",
                settlement_damage=120,
                applied_hp_damage=120,
                mitigated_damage=0,
                overkill_damage=0,
                is_boss=False,
                source_token="combat.player.normal",
            )
        )
        self.aggregator.ingest(
            common_event(
                "status",
                2,
                status="session_started",
                detail="degraded:transport_reconnected",
                aggregate=False,
            )
        )

        snapshot = self.aggregator.snapshot()
        self.assertEqual(snapshot.session_id, "session-a")
        self.assertEqual(snapshot.total_damage, 120)
        self.assertEqual(
            snapshot.diagnostic_warning,
            "degraded:transport_reconnected",
        )
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
