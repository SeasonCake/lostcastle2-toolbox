from __future__ import annotations

import unittest

from tools.analyze_lc2_damage_divergence import analyze_damage_events


def damage_event(
    sequence: int,
    owner: str,
    damage: int,
    *,
    room: str = "L1:Test:1",
    actor: str = "entity:1",
    pre: float | None = None,
    post: float | None = None,
    applied: float | None = None,
    boss: bool = False,
) -> dict[str, object]:
    return {
        "event_type": "damage_resolution",
        "damage_direction": "dealt",
        "aggregate": True,
        "sequence": sequence,
        "monotonic_ms": sequence * 10,
        "room_id": room,
        "actor_entity_id": actor,
        "owner_player_id": owner,
        "source_token": "combat.player.normal",
        "settlement_damage": damage,
        "pre_mitigation_damage": damage if pre is None else pre,
        "post_mitigation_damage": damage if post is None else post,
        "applied_hp_damage": damage if applied is None else applied,
        "overkill_damage": 0,
        "is_boss": boss,
    }


class DamageDivergenceAnalyzerTests(unittest.TestCase):
    def test_reports_fallback_formula_deltas_and_first_proven_crossing(self) -> None:
        summary = {
            "session_id": "test-session",
            "official_damage_complete": True,
            "official_boss_damage_complete": True,
            "player_breakdown": {
                "player-1": {
                    "player_slot": 0,
                    "official_damage": 90,
                    "official_boss_damage": 50,
                }
            },
        }
        result = analyze_damage_events(
            [
                damage_event(1, "player-1", 60, pre=60, post=0, applied=0),
                damage_event(2, "player-1", 40, boss=True),
                damage_event(3, "player-1", 20, boss=True),
            ],
            summary,
        )

        player = result["players"]["player-1"]
        self.assertEqual(player["fallback_events"], 1)
        self.assertEqual(player["fallback_damage"], 60)
        self.assertEqual(player["damage_delta"], 30)
        self.assertEqual(player["boss_delta"], 10)
        self.assertEqual(
            player["first_damage_above_official_final"]["sequence"],
            2,
        )
        self.assertEqual(
            player["first_boss_above_official_final"]["sequence"],
            3,
        )

    def test_bounds_same_room_actor_owner_switching(self) -> None:
        summary = {
            "official_damage_complete": True,
            "official_boss_damage_complete": True,
            "player_breakdown": {},
        }
        result = analyze_damage_events(
            [
                damage_event(1, "player-1", 30, actor="entity:boomerang"),
                damage_event(2, "player-2", 40, actor="entity:boomerang"),
                damage_event(
                    3,
                    "player-2",
                    50,
                    room="L1:Test:2",
                    actor="entity:boomerang",
                ),
            ],
            summary,
        )

        shared = result["shared_room_actor"]
        self.assertEqual(shared["count"], 1)
        self.assertEqual(shared["damage"], 70)
        self.assertEqual(shared["owner_damage"], {"player-1": 30, "player-2": 40})


if __name__ == "__main__":
    unittest.main()
