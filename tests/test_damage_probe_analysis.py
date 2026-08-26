from __future__ import annotations

import unittest

from toolbox.damage_probe_analysis import parse_probe_fields, summarize_probe_lines


class DamageProbeAnalysisTests(unittest.TestCase):
    def test_non_probe_line_is_ignored(self) -> None:
        self.assertIsNone(parse_probe_fields("ordinary game log"))

    def test_summary_separates_paths_and_detects_cross_path_duplicate(self) -> None:
        lines = [
            "[Info] [LC2DAMAGE] kind=hit path=official_attacker hit_id=7 "
            "attacker_entity=10 attacker_owner_entity=1 defender_entity=20 applied=25",
            "[Info] [LC2DAMAGE] kind=hit path=official_defender hit_id=7 "
            "attacker_entity=10 attacker_owner_entity=1 defender_entity=20 applied=25",
            "[Info] [LC2DAMAGE] kind=hit path=monster_record hit_id=8 "
            "attacker_entity=11 attacker_owner_entity=null defender_entity=21 applied=0",
            "[Info] [LC2DAMAGE] kind=boundary state=room_end normal=50 skill=0 throw=0",
            "[Info] [LC2DAMAGE] kind=hp_snapshot hit_id=7 could_damage=true "
            "parent_hit_id=null depth=0 defender_entity=20 "
            "hp_before=20 hp_after=0 hp_max=100 applied=25 lethal=True",
            "[Info] [LC2DAMAGE] kind=hp_snapshot hit_id=9 could_damage=true "
            "parent_hit_id=7 depth=1 defender_entity=20 "
            "hp_before=15 hp_after=10 hp_max=100 applied=5 lethal=False",
            "unrelated",
        ]
        summary = summarize_probe_lines(lines)
        self.assertEqual(summary.probe_lines, 6)
        self.assertEqual(summary.hit_events, 3)
        self.assertEqual(summary.boundary_events, 1)
        self.assertEqual(summary.unique_hit_fingerprints, 2)
        self.assertEqual(summary.multi_path_fingerprints, 1)
        self.assertEqual(summary.nonpositive_applied_events, 1)
        self.assertEqual(summary.missing_owner_events, 1)
        self.assertEqual(summary.applied_sum_by_path["official_attacker"], 25.0)
        self.assertEqual(summary.hp_snapshot_events, 2)
        self.assertEqual(summary.hp_snapshot_complete, 2)
        self.assertEqual(summary.hp_snapshot_hp_delta_sum, 25.0)
        self.assertEqual(summary.hp_snapshot_excess_sum, 5.0)
        self.assertEqual(summary.hp_snapshot_depth_known, 2)
        self.assertEqual(summary.hp_snapshot_root_events, 1)
        self.assertEqual(summary.hp_snapshot_nested_events, 1)
        self.assertEqual(summary.hp_snapshot_root_hp_delta_sum, 20.0)
        self.assertEqual(summary.hp_snapshot_root_settlement_sum, 20)


if __name__ == "__main__":
    unittest.main()
