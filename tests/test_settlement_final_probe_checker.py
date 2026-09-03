from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools.check_lc2_settlement_final_probe import (
    EXPECTED_TARGETS,
    evaluate_settlement_final_probe,
    main,
)


def _hooks(*, fail_open_target: str | None = None) -> list[str]:
    lines = []
    for target in EXPECTED_TARGETS:
        installed = target != fail_open_target
        error = " error=MissingMethodException" if not installed else ""
        lines.append(
            "[Info] [LC2CB-SETTLEMENT-FINAL-PROBE] kind=hook "
            f"target={target} installed={str(installed).lower()} "
            f"fail_open=true{error}"
        )
    return lines


def _boundary(
    *,
    seq: int,
    phase: str,
    run: int = 1,
    room: int = 9,
    network_samples: int = 0,
    save: str | None = None,
) -> str:
    if save is None:
        save = "empty" if phase == "prefix" else "slot-0:1000:100,slot-1:2000:200"
    save_records = 0 if save == "empty" else len(save.split(","))
    active = "slot-0:900:90,slot-1:1800:180" if phase == "prefix" else "empty"
    active_records = 2 if phase == "prefix" else 0
    cache = "slot-0:100:10,slot-1:200:20" if phase == "prefix" else "empty"
    cache_records = 2 if phase == "prefix" else 0
    return (
        "[Info] [LC2CB-SETTLEMENT-FINAL-PROBE] kind=boundary "
        f"seq={seq} phase={phase} run={run} room_epoch={room} "
        f"active_available=true active_records={active_records} "
        f"active_read_failures=0 active_truncated=false active={active} "
        f"cache_available=true cache_records={cache_records} "
        f"cache_read_failures=0 cache_truncated=false cache={cache} "
        f"save_available=true save_records={save_records} "
        f"save_read_failures=0 save_truncated=false save={save} "
        "network_available=true network_records=0 "
        "network_read_failures=0 network_truncated=false network=empty "
        f"network_samples={network_samples} duplicate_calls=0 suppressed_calls=0"
    )


def _record(
    *,
    seq: int,
    samples: int,
    surface: str = "SyncSettlementData_ClientResult",
    identity: str = "slot-0",
    damage: str = "1000",
    boss: str = "100",
    read_failure: bool = False,
) -> str:
    return (
        "[Info] [LC2CB-SETTLEMENT-FINAL-PROBE] kind=record "
        f"seq={seq} phase=prefix surface={surface} identity={identity} "
        f"damage={damage} boss={boss} "
        f"read_failure={str(read_failure).lower()} network_samples={samples} "
        "duplicate_calls=0 suppressed_calls=0"
    )


def _official(*, p0: int = 1000, p1: int = 2000) -> str:
    return (
        "[Info] [LC2CB-OFFICIAL] kind=summary members=2 "
        "final_ready=true final_records=2 final_invalid_slots=0 "
        "final_duplicate_slots=0 final_raw_indices=0,1 "
        "final_identity_matches=2 final_identity_unmatched=0 "
        "final_identity_collisions=0 final_index_mismatches=0 "
        "final_expected_slots=2 final_published_slots=2 "
        "final_accepted=true slot_basis=platform_identity_hmac "
        f"slot=0:damage={p0}:boss=100 slot=1:damage={p1}:boss=200"
    )


def _known_good(*, fail_open_target: str | None = None) -> list[str]:
    return [
        *_hooks(fail_open_target=fail_open_target),
        _boundary(seq=1, phase="prefix", network_samples=0),
        _record(seq=2, samples=1),
        _record(
            seq=3,
            samples=2,
            surface="SyncSettlementData2_Rpc",
            identity="slot-1",
            damage="2000",
            boss="200",
        ),
        _boundary(seq=4, phase="postfix", network_samples=2),
        _official(),
    ]


class SettlementFinalProbeCheckerTests(unittest.TestCase):
    def test_known_good_complete_sync_and_explicit_slot_mapping_pass(self) -> None:
        verdict = evaluate_settlement_final_probe(_known_good())

        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.status, "PASS")
        self.assertEqual(verdict.hooks, "PASS")
        self.assertEqual(verdict.sync_end, "PASS")
        self.assertEqual(verdict.official_match, "PASS")
        self.assertEqual(verdict.mapped_slot_count, 2)
        self.assertEqual(verdict.reasons, ())

    def test_explicit_optional_hook_fail_open_classification_passes(self) -> None:
        verdict = evaluate_settlement_final_probe(
            _known_good(fail_open_target="SyncSettlementData2_Rpc")
        )

        self.assertTrue(verdict.passed)
        self.assertEqual(
            verdict.fail_open_targets,
            ("SyncSettlementData2_Rpc",),
        )

    def test_missing_probe_and_incomplete_sync_end_are_not_run(self) -> None:
        missing = evaluate_settlement_final_probe(
            ["[Info] [LC2CB-OFFICIAL] kind=summary final_ready=true"]
        )
        prefix_only = evaluate_settlement_final_probe(
            [*_hooks(), _boundary(seq=1, phase="prefix")]
        )

        self.assertEqual(missing.status, "NOT_RUN")
        self.assertIn("settlement_final_probe_missing", missing.reasons)
        self.assertEqual(prefix_only.status, "NOT_RUN")
        self.assertEqual(prefix_only.sync_end, "NOT_RUN")
        self.assertIn("complete_sync_end_missing", prefix_only.reasons)

    def test_missing_one_exact_hook_target_fails(self) -> None:
        lines = _known_good()
        lines.pop(1)
        verdict = evaluate_settlement_final_probe(lines)

        self.assertEqual(verdict.status, "FAIL")
        self.assertEqual(verdict.hooks, "FAIL")
        self.assertIn("hook_target_classification_incomplete", verdict.reasons)

    def test_sequence_must_be_strictly_increasing(self) -> None:
        lines = _known_good()
        lines[5] = _record(seq=2, samples=2, identity="slot-1")
        verdict = evaluate_settlement_final_probe(lines)

        self.assertEqual(verdict.sequence, "FAIL")
        self.assertIn("probe_sequence_not_strictly_increasing", verdict.reasons)

    def test_prefix_and_postfix_must_share_run_and_room(self) -> None:
        lines = _known_good()
        lines[6] = _boundary(
            seq=4,
            phase="postfix",
            run=2,
            room=9,
            network_samples=2,
        )
        verdict = evaluate_settlement_final_probe(lines)

        self.assertEqual(verdict.status, "FAIL")
        self.assertEqual(verdict.sync_end, "FAIL")
        self.assertIn("sync_end_boundary_identity_mismatch", verdict.reasons)

    def test_postfix_before_prefix_is_an_ordering_failure(self) -> None:
        verdict = evaluate_settlement_final_probe(
            [
                *_hooks(),
                _boundary(seq=1, phase="postfix"),
                _boundary(seq=2, phase="prefix"),
            ]
        )

        self.assertEqual(verdict.status, "FAIL")
        self.assertEqual(verdict.sync_end, "FAIL")
        self.assertIn("sync_end_boundary_order_invalid", verdict.reasons)

    def test_boundary_record_limit_truncation_and_read_failure_each_fail(self) -> None:
        replacements = (
            (
                "save_records=2",
                "save_records=33",
                "postfix_save_record_limit_exceeded",
            ),
            (
                "save_truncated=false",
                "save_truncated=true",
                "postfix_save_truncated",
            ),
            (
                "save_read_failures=0",
                "save_read_failures=1",
                "postfix_save_read_failure",
            ),
        )
        for before, after, reason in replacements:
            with self.subTest(reason=reason):
                lines = _known_good()
                lines[6] = lines[6].replace(before, after)
                verdict = evaluate_settlement_final_probe(lines)
                self.assertEqual(verdict.status, "FAIL")
                self.assertIn(reason, verdict.reasons)

    def test_invalid_identity_nonfinite_negative_and_boss_over_damage_fail(self) -> None:
        mutations = (
            ("identity=slot-0", "identity=steam-123"),
            ("damage=1000", "damage=NaN"),
            ("damage=1000", "damage=-1"),
            ("boss=100", "boss=1001"),
        )
        for before, after in mutations:
            with self.subTest(after=after):
                lines = _known_good()
                lines[4] = lines[4].replace(before, after, 1)
                verdict = evaluate_settlement_final_probe(lines)
                self.assertEqual(verdict.status, "FAIL")
                self.assertGreater(verdict.parse_error_count, 0)

    def test_collision_and_record_read_failure_are_rejected(self) -> None:
        collision_lines = _known_good()
        collision_lines[4] = collision_lines[4].replace(
            "identity=slot-0", "identity=collision"
        )
        read_failure_lines = _known_good()
        read_failure_lines[4] = _record(
            seq=2,
            samples=1,
            identity="read-failure",
            damage="read-failure",
            boss="read-failure",
            read_failure=True,
        )

        collision = evaluate_settlement_final_probe(collision_lines)
        read_failure = evaluate_settlement_final_probe(read_failure_lines)
        self.assertIn("network_record_identity_collision", collision.reasons)
        self.assertIn("network_record_read_failure", read_failure.reasons)
        self.assertEqual(collision.status, "FAIL")
        self.assertEqual(read_failure.status, "FAIL")

    def test_network_sample_and_suppression_limits_are_enforced(self) -> None:
        sample_lines = _known_good()
        sample_lines[4] = sample_lines[4].replace(
            "network_samples=1", "network_samples=129"
        )
        suppression_lines = _known_good()
        suppression_lines.insert(
            6,
            "[Warning] [LC2CB-SETTLEMENT-FINAL-PROBE] kind=suppressed "
            "seq=4 max_network_samples=129 "
            "sync_end_boundaries_preserved=false",
        )
        suppression_lines[7] = suppression_lines[7].replace("seq=4", "seq=5")

        sample = evaluate_settlement_final_probe(sample_lines)
        suppression = evaluate_settlement_final_probe(suppression_lines)
        self.assertIn("network_sample_limit_invalid", sample.reasons)
        self.assertIn("suppression_limit_invalid", suppression.reasons)
        self.assertIn(
            "suppression_boundary_preservation_missing",
            suppression.reasons,
        )

    def test_official_summary_must_follow_postfix(self) -> None:
        lines = _known_good()
        official = lines.pop()
        lines.insert(3, official)
        verdict = evaluate_settlement_final_probe(lines)

        self.assertEqual(verdict.status, "NOT_RUN")
        self.assertEqual(verdict.official_match, "NOT_RUN")
        self.assertIn(
            "final_official_summary_after_postfix_missing",
            verdict.reasons,
        )

    def test_unmapped_player_identities_are_not_fake_per_slot_pass(self) -> None:
        lines = _known_good()
        lines[6] = _boundary(
            seq=4,
            phase="postfix",
            network_samples=2,
            save="player-1:1000:100,player-2:2000:200",
        )
        verdict = evaluate_settlement_final_probe(lines)

        self.assertEqual(verdict.status, "NOT_RUN")
        self.assertEqual(verdict.official_match, "NOT_RUN")
        self.assertEqual(verdict.mapped_slot_count, 0)
        self.assertIn(
            "postfix_save_slot_mapping_not_available",
            verdict.reasons,
        )

    def test_explicit_per_slot_value_mismatch_fails(self) -> None:
        verdict = evaluate_settlement_final_probe(_known_good()[:-1] + [_official(p1=2001)])

        self.assertEqual(verdict.status, "FAIL")
        self.assertEqual(verdict.official_match, "FAIL")
        self.assertEqual(verdict.mismatch_slots, (1,))
        self.assertIn("postfix_official_slot_value_mismatch", verdict.reasons)

    def test_cli_json_and_human_outputs_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "LogOutput.log"
            log_path.write_text("\n".join(_known_good()), encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                pass_code = main([str(log_path), "--json"])
            payload = json.loads(stdout.getvalue())

            missing_stdout = io.StringIO()
            with redirect_stdout(missing_stdout):
                not_run_code = main([])

        self.assertEqual(pass_code, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(not_run_code, 2)
        self.assertIn("NOT_RUN", missing_stdout.getvalue())
        self.assertIn("input_missing", missing_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
