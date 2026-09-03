from __future__ import annotations

import unittest

from tools.check_lc2_multiplayer_probe import (
    evaluate_final_official_sync,
    evaluate_final_observed_match,
    evaluate_short_probe,
    has_next_run_blocked_by_closing_gate,
    has_phantom_exit_session,
)


class MultiplayerProbeCheckerTests(unittest.TestCase):
    def test_known_good_real_0_4_5_finished_damage_matches_official(self) -> None:
        # Frozen real-run source:
        # artifacts/runtime-captures/2026-08-30-no-watch-selfheal-finished-0.4.5
        # The retained result screen and log establish the same 125226/23027 pair.
        verdict = evaluate_final_observed_match(
            {
                "session_id": "real-0.4.5-finished",
                "official_damage_complete": True,
                "official_boss_damage_complete": True,
                "player_breakdown": {
                    "player-1": {
                        "player_slot": 0,
                        "observed_damage_dealt": 125226,
                        "official_damage": 125226,
                        "observed_boss_damage": 23027,
                        "official_boss_damage": 23027,
                    }
                },
            }
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.reasons, ())
        self.assertEqual(verdict.team_damage_delta, 0)
        self.assertEqual(verdict.team_boss_delta, 0)

    def test_known_red_real_r11_process_totals_mismatch_official(self) -> None:
        # Frozen real-run source:
        # artifacts/runtime-captures/2026-09-01-r11-process-owner-mismatch-final-correct
        verdict = evaluate_final_observed_match(
            {
                "session_id": "0c734120817a4499baf742f13048fb92",
                "official_damage_complete": True,
                "official_boss_damage_complete": True,
                "player_breakdown": {
                    "player-1": {
                        "player_slot": 0,
                        "observed_damage_dealt": 12257746,
                        "official_damage": 15548016,
                        "observed_boss_damage": 6002508,
                        "official_boss_damage": 6750769,
                    },
                    "player-2": {
                        "player_slot": 1,
                        "observed_damage_dealt": 2400402,
                        "official_damage": 2647181,
                        "observed_boss_damage": 1182422,
                        "official_boss_damage": 1050188,
                    },
                    "player-3": {
                        "player_slot": 2,
                        "observed_damage_dealt": 1770725,
                        "official_damage": 1845895,
                        "observed_boss_damage": 997673,
                        "official_boss_damage": 711310,
                    },
                    "player-4": {
                        "player_slot": 3,
                        "observed_damage_dealt": 11610684,
                        "official_damage": 9732171,
                        "observed_boss_damage": 5569826,
                        "official_boss_damage": 3779095,
                    },
                },
            }
        )

        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.process_basis, "per_hit_observed")
        self.assertEqual(verdict.mismatch_slots, (0, 1, 2, 3))
        self.assertEqual(verdict.slots[3].damage_delta, 1878513)
        self.assertEqual(verdict.slots[0].damage_delta, -3290270)
        self.assertEqual(verdict.team_damage_delta, -1733706)
        self.assertEqual(verdict.team_boss_delta, 1461067)
        self.assertIn("final_observed_damage_mismatch", verdict.reasons)
        self.assertIn("final_observed_boss_mismatch", verdict.reasons)

    def test_live_official_cache_is_the_process_gate_when_retained(self) -> None:
        verdict = evaluate_final_observed_match(
            {
                "session_id": "live-cache-final-control",
                "official_damage_complete": True,
                "official_boss_damage_complete": True,
                "player_breakdown": {
                    "player-1": {
                        "player_slot": 0,
                        "observed_damage_dealt": 130,
                        "observed_boss_damage": 70,
                        "last_live_damage": 100,
                        "last_live_boss_damage": 40,
                        "last_live_observed_damage_anchor": 80,
                        "last_live_observed_boss_anchor": 60,
                        "official_damage": 150,
                        "official_boss_damage": 50,
                    },
                    "player-2": {
                        "player_slot": 1,
                        "observed_damage_dealt": 150,
                        "observed_boss_damage": 60,
                        "last_live_damage": 200,
                        "last_live_boss_damage": 50,
                        "last_live_observed_damage_anchor": 150,
                        "last_live_observed_boss_anchor": 60,
                        "official_damage": 200,
                        "official_boss_damage": 50,
                    },
                },
            }
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(
            verdict.process_basis,
            "live_official_anchor_plus_observed_delta",
        )
        self.assertEqual(verdict.team_damage_delta, 0)
        self.assertEqual(verdict.team_boss_delta, 0)

    def test_raw_live_matching_final_does_not_hide_unanchored_process_delta(self) -> None:
        verdict = evaluate_final_observed_match(
            {
                "official_damage_complete": True,
                "official_boss_damage_complete": True,
                "player_breakdown": {
                    "player-1": {
                        "player_slot": 0,
                        "observed_damage_dealt": 130,
                        "observed_boss_damage": 70,
                        "last_live_damage": 100,
                        "last_live_boss_damage": 40,
                        "last_live_observed_damage_anchor": 80,
                        "last_live_observed_boss_anchor": 60,
                        "official_damage": 100,
                        "official_boss_damage": 40,
                    }
                },
            }
        )

        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.slots[0].damage_delta, 50)
        self.assertEqual(verdict.slots[0].boss_delta, 10)

    def test_known_red_real_r22_live_estimate_diverges_both_directions(self) -> None:
        # Frozen real-run source:
        # artifacts/runtime-captures/2026-09-02-r22-two-player-full-run-live-final-divergence
        verdict = evaluate_final_observed_match(
            {
                "session_id": "52147703a7b0443fb70245f9e6be328b",
                "official_damage_complete": True,
                "official_boss_damage_complete": True,
                "player_breakdown": {
                    "player-1": {
                        "player_slot": 0,
                        "observed_damage_dealt": 11_085_685,
                        "observed_boss_damage": 4_965_690,
                        "last_live_damage": 11_057_093,
                        "last_live_boss_damage": 4_326_570,
                        "last_live_observed_damage_anchor": 11_085_685,
                        "last_live_observed_boss_anchor": 4_965_690,
                        "official_damage": 10_440_726,
                        "official_boss_damage": 4_129_298,
                    },
                    "player-2": {
                        "player_slot": 1,
                        "observed_damage_dealt": 8_525_063,
                        "observed_boss_damage": 4_243_647,
                        "last_live_damage": 8_520_510,
                        "last_live_boss_damage": 2_949_130,
                        "last_live_observed_damage_anchor": 8_414_700,
                        "last_live_observed_boss_anchor": 4_133_284,
                        "official_damage": 8_829_890,
                        "official_boss_damage": 2_974_693,
                    },
                },
            }
        )

        self.assertFalse(verdict.passed)
        self.assertEqual(
            verdict.process_basis,
            "live_official_anchor_plus_observed_delta",
        )
        self.assertEqual(verdict.slots[0].damage_delta, 616_367)
        self.assertEqual(verdict.slots[1].damage_delta, -199_017)
        self.assertEqual(verdict.team_damage_delta, 417_350)
        self.assertEqual(verdict.team_boss_delta, 282_072)
        self.assertIn("final_observed_damage_mismatch", verdict.reasons)
        self.assertIn("final_observed_boss_mismatch", verdict.reasons)

    def test_incomplete_official_summary_cannot_pass_observed_gate(self) -> None:
        verdict = evaluate_final_observed_match(
            {
                "official_damage_complete": False,
                "official_boss_damage_complete": False,
                "player_breakdown": {},
            }
        )

        self.assertFalse(verdict.passed)
        self.assertIn(
            "final_observed_official_damage_incomplete",
            verdict.reasons,
        )
        self.assertIn("final_observed_player_breakdown_missing", verdict.reasons)

    def test_positive_control_two_distinct_new_rooms_blocked_after_preload_fails(self) -> None:
        lines = [
            "[Info] [LC2CB-ROOM] callback=round_end_preload_camp valid=False "
            "is_camp=False stage=1 scenario=DarkForest room_index=1 map=old-battle",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=False "
            "is_camp=False stage=1 scenario=DarkForest room_index=0 map=new-entrance",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=False "
            "is_camp=False stage=1 scenario=DarkForest room_index=1 map=new-battle",
        ]

        self.assertTrue(has_next_run_blocked_by_closing_gate(lines))

    def test_known_good_one_stale_room_then_valid_new_room_is_not_blocked(self) -> None:
        lines = [
            "[Info] [LC2CB-ROOM] callback=round_end_preload_camp valid=False "
            "is_camp=False stage=1 scenario=DarkForest room_index=3 map=old-battle",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=False "
            "is_camp=False stage=1 scenario=DarkForest room_index=3 map=old-battle",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=True "
            "is_camp=False stage=1 scenario=DarkForest room_index=0 map=new-entrance",
        ]

        self.assertFalse(has_next_run_blocked_by_closing_gate(lines))

    def test_known_good_all_zero_indices_with_unique_identity_mapping_pass(self) -> None:
        verdict = evaluate_final_official_sync(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary members=4 "
                "final_ready=true final_records=4 final_invalid_slots=0 "
                "final_duplicate_slots=0 final_raw_indices=0,0,0,0 "
                "final_identity_matches=4 final_identity_unmatched=0 "
                "final_identity_collisions=0 final_index_mismatches=3 "
                "final_expected_slots=4 final_published_slots=4 "
                "final_accepted=true slot_basis=platform_identity_hmac "
                "slot=0:damage=100:boss=10 slot=1:damage=200:boss=20 "
                "slot=2:damage=300:boss=30 slot=3:damage=400:boss=40"
            ]
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.index_mismatches, 3)
        self.assertFalse(verdict.roster_collapsed_to_single)

    def test_positive_control_frozen_r6_mindex_collapse_fails(self) -> None:
        verdict = evaluate_final_official_sync(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary members=4 "
                "final_ready=true final_records=4 final_invalid_slots=0 "
                "final_duplicate_slots=1 final_raw_indices=0,0,0,0 "
                "final_expected_slots=4 final_published_slots=0 "
                "final_accepted=false slot_basis=mIndex_zero_based "
                "slot=0:damage=null:boss=null slot=1:damage=null:boss=null "
                "slot=2:damage=null:boss=null slot=3:damage=null:boss=null"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("final_identity_basis_missing", verdict.reasons)
        self.assertIn("final_official_rejected", verdict.reasons)

    def test_positive_control_identity_collision_fails(self) -> None:
        verdict = evaluate_final_official_sync(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary members=2 "
                "final_ready=true final_records=2 final_duplicate_slots=0 "
                "final_identity_matches=1 final_identity_unmatched=1 "
                "final_identity_collisions=1 final_index_mismatches=0 "
                "final_expected_slots=2 final_published_slots=0 "
                "final_accepted=false slot_basis=platform_identity_hmac "
                "slot=0:damage=null:boss=null slot=1:damage=null:boss=null"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("final_identity_collision", verdict.reasons)

    def test_positive_control_multiplayer_exit_folded_to_single_is_not_final(self) -> None:
        verdict = evaluate_final_official_sync(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary members=4 "
                "final_ready=false final_records=0 final_expected_slots=0 "
                "final_published_slots=0 final_accepted=false "
                "slot_basis=platform_identity_hmac",
                "[Info] [LC2CB-ROOM] callback=round_start valid=False is_camp=True",
                "[Info] [LC2CB-OFFICIAL] kind=summary members=1 "
                "final_ready=false final_records=0 final_expected_slots=0 "
                "final_published_slots=0 final_accepted=false "
                "slot_basis=platform_identity_hmac",
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertTrue(verdict.roster_collapsed_to_single)
        self.assertIn(
            "multiplayer_roster_collapsed_to_single_without_final_sync",
            verdict.reasons,
        )

    def test_positive_control_final_acceptance_must_not_regress(self) -> None:
        verdict = evaluate_final_official_sync(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary members=4 "
                "final_ready=true final_records=4 final_duplicate_slots=0 "
                "final_identity_matches=4 final_identity_unmatched=0 "
                "final_identity_collisions=0 final_index_mismatches=2 "
                "final_expected_slots=4 final_published_slots=4 "
                "final_accepted=true slot_basis=platform_identity_hmac "
                "slot=0:damage=10:boss=1 slot=1:damage=20:boss=2 "
                "slot=2:damage=30:boss=3 slot=3:damage=40:boss=4",
                "[Info] [LC2CB-OFFICIAL] kind=summary members=3 "
                "final_ready=true final_records=4 final_duplicate_slots=0 "
                "final_identity_matches=2 final_identity_unmatched=2 "
                "final_identity_collisions=1 final_index_mismatches=1 "
                "final_expected_slots=4 final_published_slots=0 "
                "final_accepted=false slot_basis=platform_identity_hmac "
                "slot=0:damage=null:boss=null slot=1:damage=null:boss=null "
                "slot=2:damage=null:boss=null"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("final_acceptance_regressed", verdict.reasons)

    def test_known_good_two_remote_slots_and_forwarded_hit_pass(self) -> None:
        verdict = evaluate_short_probe(
            [
                "[Info] [LC2CB-OWNER-CHECK] point=change_room_end local_slot=0 "
                "settlement_unique=9 registered_unique=9 matched_unique=9 "
                "duplicate_callback_conflicts=0 "
                "slot=0:events=3:unique=3:matched=3:forwarded=0:owner_match=3:conflict=0:unresolved=0 "
                "slot=1:events=3:unique=3:matched=3:forwarded=0:owner_match=3:conflict=0:unresolved=0 "
                "slot=2:events=3:unique=3:matched=3:forwarded=2:owner_match=3:conflict=0:unresolved=0"
            ]
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.reasons, ())

    def test_positive_control_missing_second_remote_slot_fails(self) -> None:
        verdict = evaluate_short_probe(
            [
                "[Info] [LC2CB-OWNER-CHECK] point=change_room_end local_slot=0 "
                "settlement_unique=4 registered_unique=4 matched_unique=4 "
                "duplicate_callback_conflicts=0 "
                "slot=0:events=2:unique=2:matched=2:forwarded=0:owner_match=2:conflict=0:unresolved=0 "
                "slot=1:events=2:unique=2:matched=2:forwarded=1:owner_match=2:conflict=0:unresolved=0"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("remote_slot_coverage_insufficient", verdict.reasons)

    def test_positive_control_owner_conflict_fails_even_when_counts_match(self) -> None:
        verdict = evaluate_short_probe(
            [
                "[Info] [LC2CB-OWNER-CHECK] point=change_room_end local_slot=0 "
                "settlement_unique=6 registered_unique=6 matched_unique=6 "
                "duplicate_callback_conflicts=0 "
                "slot=1:events=3:unique=3:matched=3:forwarded=1:owner_match=2:conflict=1:unresolved=0 "
                "slot=2:events=3:unique=3:matched=3:forwarded=0:owner_match=3:conflict=0:unresolved=0"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("registered_owner_slot_conflict", verdict.reasons)

    def test_frozen_r3_without_owner_check_is_rejected(self) -> None:
        verdict = evaluate_short_probe(
            [
                "[Info] [LC2CB-OFFICIAL] kind=summary members=3 "
                "network_records=0 fallback_records=1"
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("owner_check_missing", verdict.reasons)

    def test_positive_control_exit_stale_room_reentry_fails(self) -> None:
        lines = [
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=True is_camp=False",
            "[Info] [LC2CB-ROOM] callback=round_start valid=False is_camp=True",
            "[Info] [LC2CB-OWNER-CHECK] point=change_room_end local_slot=0 "
            "settlement_unique=6 registered_unique=6 matched_unique=6 "
            "duplicate_callback_conflicts=0 "
            "slot=1:events=3:unique=3:matched=3:forwarded=1:owner_match=3:conflict=0:unresolved=0 "
            "slot=2:events=3:unique=3:matched=3:forwarded=1:owner_match=3:conflict=0:unresolved=0",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=True is_camp=False",
            "[Info] [LC2CB-ROOM] callback=round_end_preload_camp valid=False",
        ]

        self.assertTrue(has_phantom_exit_session(lines))
        verdict = evaluate_short_probe(lines)
        self.assertFalse(verdict.passed)
        self.assertIn("phantom_session_after_round_start", verdict.reasons)

    def test_known_good_log_start_then_first_legal_room_is_not_phantom(self) -> None:
        lines = [
            "[Info] [LC2CB-ROOM] callback=round_start valid=False is_camp=True",
            "[Info] [LC2CB-ROOM] callback=round_start valid=False is_camp=True",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=True is_camp=False",
        ]

        self.assertFalse(has_phantom_exit_session(lines))

    def test_known_good_preload_closes_old_run_before_new_legal_room(self) -> None:
        lines = [
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=True is_camp=False",
            "[Info] [LC2CB-ROOM] callback=round_end_preload_camp valid=False",
            "[Info] [LC2CB-ROOM] callback=round_start valid=False is_camp=True",
            "[Info] [LC2CB-ROOM] callback=change_room_end valid=True is_camp=False",
        ]

        self.assertFalse(has_phantom_exit_session(lines))


if __name__ == "__main__":
    unittest.main()
