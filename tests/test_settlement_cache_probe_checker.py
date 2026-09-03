from __future__ import annotations

import unittest

from tools.check_lc2_settlement_cache_probe import (
    evaluate_settlement_cache_probe,
)


def _slots(values: dict[int, tuple[float, float]]) -> str:
    if not values:
        return "none"
    return ",".join(
        f"{slot}:{damage}:{boss}"
        for slot, (damage, boss) in sorted(values.items())
    )


def _sample(
    *,
    sample: int,
    room: int = 1,
    point: str = "attacker_post",
    values: dict[int, tuple[float, float]] | None = None,
    cache: dict[int, tuple[float, float]] | None = None,
    active: dict[int, tuple[float, float]] | None = None,
    trigger: int | None = None,
    humans: int = 2,
    records: int = 2,
    matched: int = 2,
    unmatched: int = 0,
    duplicate: int = 0,
    collisions: int = 0,
    failures: int = 0,
    invalid: int = 0,
    complete: bool = True,
) -> str:
    values = values or {0: (0, 0), 1: (0, 0)}
    cache = values if cache is None else cache
    active = active or {0: (100, 10), 1: (200, 20)}
    mapped = len(values) if complete else max(0, len(values) - 1)
    return (
        "[Info] [LC2CB-SETTLEMENT-CACHE] kind=sample "
        f"run=1 room_epoch={room} sample={sample} call={sample} "
        f"point={point} combat=true trigger_slot="
        f"{'null' if trigger is None else trigger} local_slot=1 damage_calls={sample} "
        f"humans={humans} dict_available=true dict_records={records} "
        f"dict_matched={matched} dict_unmatched={unmatched} "
        f"dict_duplicate_slots={duplicate} dict_collisions={collisions} "
        f"dict_read_failures={failures} dict_invalid={invalid} "
        f"human_mapped={mapped} human_complete={str(complete).lower()} "
        f"changed=true dict_basis=player_id:{matched} "
        f"dict_slots={_slots(values)} cache_list_available=true "
        f"cache_list_records={records} cache_list_slots={_slots(cache)} "
        f"active_available=true active_records={humans} active_slots={_slots(active)} "
        "stat_identity_matches=4 stat_identity_unmatched=0 "
        "stat_identity_collisions=0 stat_read_failures=0 "
        "singleton_available=true singleton_invalid=false singleton=300:30"
    )


class SettlementCacheProbeCheckerTests(unittest.TestCase):
    def test_same_room_two_human_slots_change_and_npc_unmatched_passes(self) -> None:
        active = {0: (100, 10), 1: (200, 20)}
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(
                    sample=1,
                    point="room_entry",
                    records=3,
                    unmatched=1,
                    values={0: (0, 0), 1: (0, 0)},
                    active=active,
                ),
                _sample(
                    sample=2,
                    trigger=0,
                    records=3,
                    unmatched=1,
                    values={0: (12, 0), 1: (0, 0)},
                    active=active,
                ),
                _sample(
                    sample=3,
                    trigger=1,
                    records=3,
                    unmatched=1,
                    values={0: (12, 0), 1: (25, 0)},
                    active=active,
                ),
            ]
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.raw_damage_realtime, "PASS")
        self.assertEqual(verdict.changing_human_slots, (0, 1))
        self.assertEqual(verdict.dict_relation, "DELTA_MATCHES_CACHE_LIST")
        self.assertEqual(verdict.boss_realtime, "NOT_RUN")
        self.assertEqual(verdict.rollover, "NOT_RUN")

    def test_only_room_transition_change_rejects_realtime(self) -> None:
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(sample=1, room=1, point="room_entry"),
                _sample(sample=2, room=1, point="room_exit"),
                _sample(
                    sample=3,
                    room=2,
                    point="room_entry",
                    values={0: (10, 0), 1: (20, 0)},
                ),
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("same_room_multi_human_change_missing", verdict.reasons)

    def test_universal_zero_after_hits_rejects(self) -> None:
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(sample=1, trigger=0),
                _sample(sample=2, trigger=1),
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.changing_human_slots, ())

    def test_duplicate_collision_read_failure_and_invalid_each_reject(self) -> None:
        for field, value, reason in (
            ("duplicate", 1, "dict_duplicate_slot"),
            ("collisions", 1, "dict_identity_collision"),
            ("failures", 1, "dict_read_failure"),
            ("invalid", 1, "invalid_damage_value"),
        ):
            with self.subTest(field=field):
                kwargs = {field: value}
                verdict = evaluate_settlement_cache_probe(
                    [_sample(sample=1, **kwargs), _sample(sample=2, **kwargs)]
                )
                self.assertFalse(verdict.passed)
                self.assertIn(reason, verdict.reasons)

    def test_dict_cache_list_disagreement_is_classified_not_prejudged(self) -> None:
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(sample=1),
                _sample(
                    sample=2,
                    values={0: (10, 0), 1: (20, 0)},
                    cache={0: (11.5, 0), 1: (20, 0)},
                ),
            ]
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.dict_relation, "UNKNOWN_DIFFERENT")
        self.assertNotIn("dict_cache_list_disagreement", verdict.reasons)

    def test_missing_cache_list_crosscheck_does_not_fake_a_dict_failure(self) -> None:
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(sample=1, cache={}),
                _sample(
                    sample=2,
                    values={0: (10, 0), 1: (20, 0)},
                    cache={},
                ),
            ]
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.dict_relation, "UNKNOWN_DIFFERENT")
        self.assertEqual(verdict.cache_crosscheck_samples, 0)

    def test_same_room_regression_and_nonfinite_values_reject(self) -> None:
        regression = evaluate_settlement_cache_probe(
            [
                _sample(sample=1, values={0: (20, 0), 1: (30, 0)}),
                _sample(sample=2, values={0: (10, 0), 1: (40, 0)}),
            ],
            minimum_changing_human_slots=1,
        )
        nonfinite = evaluate_settlement_cache_probe(
            [
                _sample(
                    sample=1,
                    values={0: (float("nan"), 0), 1: (0, 0)},
                )
            ]
        )

        self.assertFalse(regression.passed)
        self.assertIn("same_room_value_regression", regression.reasons)
        self.assertFalse(nonfinite.passed)
        self.assertIn("invalid_damage_value", nonfinite.reasons)

    def test_known_r15_rollover_conserves_active_plus_one_delta(self) -> None:
        old_active = {
            0: (173125, 25436),
            1: (99020, 25916),
            2: (207555, 39715),
            3: (59804, 5993),
        }
        old_delta = {
            0: (1610, 0),
            1: (955, 0),
            2: (0, 0),
            3: (1087, 0),
        }
        new_active = {
            0: (174735, 25436),
            1: (99975, 25916),
            2: (207555, 39715),
            3: (60891, 5993),
        }
        zero_delta = {slot: (0, 0) for slot in range(4)}
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(
                    sample=1,
                    room=1,
                    point="room_exit",
                    humans=4,
                    records=4,
                    matched=4,
                    values=old_delta,
                    active=old_active,
                ),
                _sample(
                    sample=2,
                    room=2,
                    point="room_entry",
                    humans=4,
                    records=4,
                    matched=4,
                    values=zero_delta,
                    active=new_active,
                ),
            ],
            minimum_human_slots=4,
            minimum_changing_human_slots=0,
            require_rollover_observation=True,
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.rollover, "OBSERVED")
        self.assertEqual(verdict.rollover_relation, "ACTIVE_PLUS_DICT_EQUAL")
        self.assertEqual(verdict.rollover_transitions, 1)

    def test_rollover_difference_is_reported_without_predeclaring_failure(self) -> None:
        verdict = evaluate_settlement_cache_probe(
            [
                _sample(
                    sample=1,
                    room=1,
                    point="room_exit",
                    values={0: (10, 0), 1: (20, 0)},
                    active={0: (100, 10), 1: (200, 20)},
                ),
                _sample(
                    sample=2,
                    room=2,
                    point="room_entry",
                    values={0: (0, 0), 1: (0, 0)},
                    active={0: (105, 10), 1: (205, 20)},
                ),
            ],
            minimum_changing_human_slots=0,
            require_rollover_observation=True,
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.rollover, "OBSERVED")
        self.assertEqual(verdict.rollover_relation, "ACTIVE_PLUS_DICT_DIFFERENT")

    def test_final_official_only_cannot_satisfy_realtime_gate(self) -> None:
        verdict = evaluate_settlement_cache_probe(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary final_ready=true "
                "final_accepted=true"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("probe_sample_missing", verdict.reasons)


if __name__ == "__main__":
    unittest.main()
