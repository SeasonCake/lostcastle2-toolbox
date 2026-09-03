from __future__ import annotations

import json
import unittest

from tools.check_lc2_leave_team_identity import evaluate_leave_team_identity


def _event(sequence: int, members: list[dict[str, object]]) -> str:
    return json.dumps(
        {
            "event_type": "status",
            "status": "party_updated",
            "session_id": "same-session",
            "sequence": sequence,
            "party_members": members,
        },
        separators=(",", ":"),
    )


class LeaveTeamIdentityCheckerTests(unittest.TestCase):
    def test_stable_local_id_current_slot_and_live_pass(self) -> None:
        verdict = evaluate_leave_team_identity(
            [
                _event(
                    1,
                    [
                        {
                            "player_id": "player-1",
                            "player_slot": 0,
                            "is_local": False,
                            "live_damage": 1928,
                        },
                        {
                            "player_id": "player-3",
                            "player_slot": 2,
                            "is_local": True,
                            "live_damage": 13827,
                        },
                    ],
                ),
                _event(
                    2,
                    [
                        {
                            "player_id": "player-3",
                            "player_slot": 0,
                            "is_local": True,
                            "live_damage": 13827,
                        }
                    ],
                ),
            ]
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.previous_local_slot, 2)
        self.assertEqual(verdict.singleton_local_slot, 0)
        self.assertEqual(verdict.singleton_local_live, 13827)

    def test_r19_new_token_and_old_p1_live_are_known_red(self) -> None:
        verdict = evaluate_leave_team_identity(
            [
                _event(
                    1,
                    [
                        {
                            "player_id": "player-1",
                            "player_slot": 0,
                            "is_local": False,
                            "live_damage": 45888,
                        },
                        {
                            "player_id": "player-4",
                            "player_slot": 3,
                            "is_local": True,
                            "live_damage": 3338,
                        },
                    ],
                ),
                _event(
                    2,
                    [
                        {
                            "player_id": "player-5",
                            "player_slot": 0,
                            "is_local": True,
                            "live_damage": 45888,
                        }
                    ],
                ),
            ]
        )

        self.assertFalse(verdict.passed)
        self.assertIn("local_player_id_changed", verdict.reasons)
        self.assertIn("local_live_damage_changed_on_leave", verdict.reasons)
        self.assertIn("singleton_inherited_departed_live", verdict.reasons)
        self.assertEqual(verdict.inherited_departed_player_id, "player-1")


if __name__ == "__main__":
    unittest.main()
