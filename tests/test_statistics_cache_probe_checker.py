from __future__ import annotations

import unittest

from tools.check_lc2_statistics_cache_probe import (
    evaluate_statistics_cache_probe,
)


def _slots(values: dict[int, tuple[int, int]]) -> str:
    return ",".join(
        f"{slot}:{damage}:{boss}"
        for slot, (damage, boss) in sorted(values.items())
    )


def _sample(
    *,
    sample: int,
    room: int,
    point: str,
    cache: dict[int, tuple[int, int]],
    active: dict[int, tuple[int, int]],
    trigger: int | None = None,
    local_slot: int = 1,
    combat: bool = True,
    humans: int = 2,
    records: int | None = None,
    stat_unmatched: int = 0,
    stat_collisions: int = 0,
    stat_failures: int = 0,
) -> str:
    records = humans if records is None else records
    return (
        "[Info] [LC2CB-SETTLEMENT-CACHE] kind=sample "
        f"run=1 room_epoch={room} sample={sample} call={sample} "
        f"point={point} ordinary_samples={sample} ordinary_suppressed=false "
        f"throttled_calls=0 combat={str(combat).lower()} "
        f"trigger_slot={'null' if trigger is None else trigger} "
        f"local_slot={local_slot} damage_calls={sample} humans={humans} "
        "dict_available=true dict_records=0 dict_matched=0 dict_unmatched=0 "
        "dict_duplicate_slots=0 dict_collisions=0 dict_read_failures=0 "
        "dict_invalid=0 human_mapped=0 human_complete=false changed=true "
        "dict_basis=none dict_opaque=none dict_slots=none "
        f"cache_list_available=true cache_list_records={records} "
        f"cache_list_slots={_slots(cache)} active_available=true "
        f"active_records={records} active_slots={_slots(active)} "
        f"stat_identity_matches={humans * 2} "
        f"stat_identity_unmatched={stat_unmatched} "
        f"stat_identity_collisions={stat_collisions} "
        f"stat_read_failures={stat_failures} "
        "singleton_available=true singleton_invalid=false singleton=0:0"
    )


def _known_good_lines() -> list[str]:
    zero = {0: (0, 0), 1: (0, 0)}
    room_one_active = zero
    room_one_final = {0: (20, 0), 1: (0, 0)}
    room_two_active = room_one_final
    return [
        _sample(
            sample=1,
            room=1,
            point="room_entry",
            cache=zero,
            active=room_one_active,
        ),
        _sample(
            sample=2,
            room=1,
            point="attacker_post",
            trigger=0,
            cache={0: (10, 0), 1: (0, 0)},
            active=room_one_active,
        ),
        _sample(
            sample=3,
            room=1,
            point="room_exit",
            trigger=0,
            cache=room_one_final,
            active=room_one_active,
        ),
        _sample(
            sample=4,
            room=2,
            point="room_entry",
            cache=zero,
            active=room_two_active,
        ),
        _sample(
            sample=5,
            room=2,
            point="attacker_post",
            trigger=1,
            cache={0: (0, 0), 1: (5, 0)},
            active=room_two_active,
        ),
        _sample(
            sample=6,
            room=2,
            point="attacker_post",
            trigger=0,
            cache={0: (10, 0), 1: (5, 0)},
            active=room_two_active,
        ),
    ]


class StatisticsCacheProbeCheckerTests(unittest.TestCase):
    def test_remote_only_local_damage_and_exact_rollover_pass(self) -> None:
        verdict = evaluate_statistics_cache_probe(_known_good_lines())

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.raw_damage_realtime, "PASS")
        self.assertEqual(verdict.rollover, "PASS")
        self.assertEqual(verdict.changing_human_slots, (0, 1))
        self.assertEqual(verdict.remote_only_rooms, (1,))
        self.assertEqual(verdict.local_damage_rooms, (2,))
        self.assertEqual(verdict.boss_realtime, "NOT_RUN")

    def test_extra_npc_records_and_unmatched_are_allowed(self) -> None:
        lines = [
            line.replace("cache_list_records=2", "cache_list_records=3")
            .replace("active_records=2", "active_records=3")
            .replace("stat_identity_unmatched=0", "stat_identity_unmatched=2")
            for line in _known_good_lines()
        ]

        verdict = evaluate_statistics_cache_probe(lines)

        self.assertTrue(verdict.passed)

    def test_throttled_last_hit_without_force_boundary_keeps_rollover_not_run(self) -> None:
        lines = [line for index, line in enumerate(_known_good_lines()) if index != 2]

        verdict = evaluate_statistics_cache_probe(lines, require_rollover=False)

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.raw_damage_realtime, "PASS")
        self.assertEqual(verdict.rollover, "NOT_RUN")

    def test_same_room_active_cache_partition_move_preserves_combined(self) -> None:
        lines = _known_good_lines()
        lines[1] = _sample(
            sample=2,
            room=1,
            point="attacker_post",
            trigger=0,
            cache={0: (5, 0), 1: (0, 0)},
            active={0: (5, 0), 1: (0, 0)},
        )

        verdict = evaluate_statistics_cache_probe(lines)

        self.assertTrue(verdict.passed)

    def test_same_room_combined_regression_rejects_realtime_formula(self) -> None:
        lines = _known_good_lines()
        lines.insert(
            2,
            _sample(
                sample=20,
                room=1,
                point="attacker_post",
                trigger=0,
                cache={0: (9, 0), 1: (0, 0)},
                active={0: (0, 0), 1: (0, 0)},
            ),
        )

        verdict = evaluate_statistics_cache_probe(lines)

        self.assertFalse(verdict.passed)
        self.assertIn("same_room_combined_regression", verdict.reasons)

    def test_rollover_loss_or_double_count_rejects(self) -> None:
        lines = _known_good_lines()
        lines[3] = _sample(
            sample=4,
            room=2,
            point="room_entry",
            cache={0: (0, 0), 1: (0, 0)},
            active={0: (21, 0), 1: (0, 0)},
        )

        verdict = evaluate_statistics_cache_probe(lines)

        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.rollover, "FAIL")
        self.assertIn("active_plus_cache_rollover_mismatch", verdict.reasons)

    def test_identity_collision_and_nonzero_initial_combined_reject(self) -> None:
        collision_lines = [
            line.replace(
                "stat_identity_collisions=0",
                "stat_identity_collisions=1",
            )
            for line in _known_good_lines()
        ]
        nonzero_entry = _known_good_lines()
        nonzero_entry[0] = _sample(
            sample=1,
            room=1,
            point="room_entry",
            cache={0: (1, 0), 1: (0, 0)},
            active={0: (0, 0), 1: (0, 0)},
        )

        collision = evaluate_statistics_cache_probe(collision_lines)
        nonzero = evaluate_statistics_cache_probe(nonzero_entry)

        self.assertFalse(collision.passed)
        self.assertIn("statistics_identity_collision", collision.reasons)
        self.assertFalse(nonzero.passed)
        self.assertIn("initial_room_entry_combined_not_zero", nonzero.reasons)

    def test_nonzero_later_room_entry_cache_is_allowed_when_combined_rolls_over(self) -> None:
        lines = _known_good_lines()
        lines[3] = _sample(
            sample=4,
            room=2,
            point="room_entry",
            cache={0: (5, 0), 1: (0, 0)},
            active={0: (15, 0), 1: (0, 0)},
        )

        verdict = evaluate_statistics_cache_probe(lines)

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.rollover, "PASS")


if __name__ == "__main__":
    unittest.main()
