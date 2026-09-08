from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import zipfile
from unittest import mock

from toolbox.combat_aggregator import CombatAggregator
from toolbox.combat_archive import CombatDiagnosticsController, CombatMatchArchiver
from toolbox.combat_transport import (
    CombatBridgeClient, CombatEventPump, CombatEventValidator, CombatInbox,
    CombatLineDecoder, CombatSchemaError, TransportNotice,
)
from toolbox.app_shell import GOLD, combat_status_presentation
from tests.test_combat_transport import FakeStream, PROJECT_ROOT, status_event
from tests.test_support_diagnostics import fixture, read_report


def damage(sequence: int, amount: int = 7, **fields: object) -> dict:
    event = status_event(
        sequence, event_type="damage_resolution", aggregate=True,
        hook_path="settlement.official_attacker", damage_direction="dealt",
        hit_id=sequence, target_id=f"target-{sequence}", pre_mitigation_damage=amount,
        post_mitigation_damage=amount, applied_hp_damage=amount,
        settlement_damage=amount, mitigated_damage=0, overkill_damage=0,
        damage_outcome="applied", is_boss=False, owner_player_id="player-0",
        source_token="combat.player.normal", **fields,
    )
    event.pop("status")
    return event


def encoded(*events: dict) -> bytes:
    return b"".join(json.dumps(event).encode() + b"\n" for event in events)


class StreamWithIdleTail(FakeStream):
    def read(self, size: int) -> bytes | None:
        if self.closed:
            return b""
        if self.chunks:
            return super().read(size)
        time.sleep(0.002)
        return None


class CombatRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = CombatEventValidator.from_file(PROJECT_ROOT / "contracts/combat_event.schema.json")

    def wait_for(self, predicate, seconds: float = 3) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.005)
        self.fail("Timed out waiting for the exercised recovery path")

    def test_decoder_isolates_each_bad_line_and_preserves_both_neighbors(self) -> None:
        for raw, code in (
            (b"\xff", "invalid_utf8"), (b"{broken}", "invalid_json"),
            (b"[]", "event_not_object"), (b'{"x":NaN}', "invalid_json"),
            (b'{"x":1e999}', "invalid_json"),
        ):
            with self.subTest(code=code, raw=raw):
                decoder = CombatLineDecoder(recover=True)
                items = decoder.feed(encoded(status_event()) + raw + b"\n" + encoded(status_event(2)))
                self.assertEqual(items[0], status_event())
                self.assertEqual(items[1].detail_code, code)
                self.assertTrue(items[1].sample)
                self.assertEqual(items[2], status_event(2))
                self.assertIsNone(decoder.finish())

    def test_oversize_line_retains_bounded_sample_and_resyncs_only_at_newline(self) -> None:
        decoder = CombatLineDecoder(max_line_bytes=16, recover=True)
        self.assertEqual(decoder.feed(b"x" * 16), [])
        issue = decoder.feed(b"x" * 10000)[0]
        self.assertEqual(issue.detail_code, "line_too_long")
        self.assertLessEqual(len(issue.sample), 4096)
        self.assertEqual(decoder.feed(b'{"forged":1}'), [])
        self.assertEqual(decoder.feed(b'\n{"valid":2}\n'), [{"valid": 2}])
        decoder.feed(b'{"tail":')
        self.assertEqual(decoder.finish().detail_code, "unterminated_line")

    def test_nonfinite_values_cannot_poison_direct_inbox_statistics(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(CombatSchemaError):
                self.validator.validate(damage(1, applied_hp_damage_unused=value))

    def test_escaped_surrogate_isolation_preserves_both_neighbors_and_exportable_evidence(self) -> None:
        for use_decoder in (False, True):
            for invalid in ("invalid", chr(0xd800), chr(0xdc00)):
                with self.subTest(decoder=use_decoder, invalid=repr(invalid)):
                    inbox, aggregator, accepted = CombatInbox(), CombatAggregator(), []
                    pump = CombatEventPump(inbox, self.validator, aggregator,
                                           event_batch_sink=lambda events: accepted.extend(events))
                    bad = damage(2)
                    bad["settlement_damage"] = invalid
                    events = [status_event(), damage(1, 11), bad, damage(3, 17)]
                    items = CombatLineDecoder(recover=True).feed(encoded(*events)) if use_decoder else events
                    for item in items:
                        if isinstance(item, TransportNotice):
                            inbox.publish_notice(item.state, item.detail_code, sample=item.sample)
                        else:
                            inbox.publish_event(item)
                    report = pump.drain()
                    self.assertEqual(report.processed_events, 3)
                    self.assertEqual(aggregator.snapshot().total_damage, 28)
                    self.assertEqual(aggregator.snapshot().last_sequence, 3)
                    self.assertEqual([event["sequence"] for event in accepted], [0, 1, 3])
                    self.assertTrue(aggregator.snapshot().data_incomplete)
                    diagnostics = pump.diagnostic_state()
                    self.assertEqual(diagnostics["counts"]["rejected"], 1)
                    self.assertEqual(json.loads(diagnostics["recent_issues"][0]["sample"]), bad)
                    json.dumps(diagnostics, ensure_ascii=False).encode("utf-8", errors="strict")

    def test_valid_unicode_remains_accepted_but_invalid_unicode_in_status_cannot_poison_snapshot(self) -> None:
        self.validator.validate(status_event(1, detail="继续采集 😀"))
        with self.assertRaisesRegex(CombatSchemaError, "invalid_unicode"):
            self.validator.validate(status_event(1, detail=chr(0xd800)))
        inbox, aggregator = CombatInbox(), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        inbox.publish_event(status_event())
        inbox.publish_notice("degraded", "invalid_json", sample=chr(0xd800))
        inbox.publish_event(damage(1, 17))
        self.assertEqual(pump.drain().processed_events, 2)
        self.assertEqual(aggregator.snapshot().total_damage, 17)
        self.assertEqual(pump.diagnostic_state()["recent_issues"][0]["sample"], r"\ud800")

    def test_single_bad_record_keeps_valid_totals_and_next_room_with_bounded_evidence(self) -> None:
        inbox, aggregator = CombatInbox(), CombatAggregator()
        journal = []
        accepted = []
        pump = CombatEventPump(inbox, self.validator, aggregator,
                               event_batch_sink=lambda batch: accepted.extend(batch),
                               diagnostic_sink=lambda event, **data: journal.append((event, data)))
        bad = damage(2)
        bad["settlement_damage"] = "not a number"
        for event in (status_event(), damage(1, 11), bad, damage(3, 17), status_event(4, status="room_started",
                      room_id="castle-room-2", stage_level=5, scenario_id="Castle", room_index=2, map_file_name="castle")):
            inbox.publish_event(event)
        report = pump.drain()
        snapshot = aggregator.snapshot()
        self.assertEqual(report.processed_events, 4)
        self.assertIsNone(report.fault_code)
        self.assertEqual(snapshot.total_damage, 28)
        self.assertEqual(snapshot.current_room_id, "castle-room-2")
        self.assertTrue(snapshot.data_incomplete)
        self.assertEqual([event["sequence"] for event in accepted], [0, 1, 3, 4])
        diagnostics = pump.diagnostic_state()
        self.assertEqual(json.loads(diagnostics["recent_issues"][0]["sample"]), bad)
        self.assertEqual(diagnostics["counts"]["rejected"], 1)
        self.assertEqual(diagnostics["recovery_count"], 1)
        self.assertIn("combat_transport_issue", [row[0] for row in journal])
        self.assertIn("combat_transport_recovered", [row[0] for row in journal])
        for index in range(30):
            inbox.publish_event({"schema_version": 2, "detail": "x" * 10000})
            pump.drain()
        issues = pump.diagnostic_state()["recent_issues"]
        self.assertEqual(len(issues), 16)
        self.assertTrue(all(len(issue["sample"]) <= 4096 for issue in issues))
        self.assertGreater(pump.diagnostic_state()["suppressed_journal_events"], 0)

    def test_foreign_and_reused_sequence_records_are_quarantined_new_session_clears_quality(self) -> None:
        inbox, aggregator = CombatInbox(), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        for event in (status_event(), damage(1, 11), damage(2, 100, session_id="foreign"),
                      damage(1, 100, event_id="different-id"), damage(3, 17)):
            inbox.publish_event(event)
        pump.drain()
        self.assertEqual(aggregator.snapshot().total_damage, 28)
        self.assertEqual(pump.diagnostic_state()["counts"]["rejected"], 2)
        self.assertTrue(aggregator.snapshot().data_incomplete)
        inbox.publish_event(status_event(0, session_id="new-session", event_id="new-session:0"))
        pump.drain()
        self.assertFalse(aggregator.snapshot().data_incomplete)
        self.assertEqual(aggregator.snapshot().total_damage, 0)
        self.assertEqual(len(pump.diagnostic_state()["recent_issues"]), 2)

    def test_overflow_keeps_prefix_then_exposes_gap_before_accepting_later_data(self) -> None:
        inbox, aggregator = CombatInbox(max_items=2), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        inbox.publish_event(status_event())
        inbox.publish_event(damage(1, 11))
        self.assertFalse(inbox.publish_event(damage(2, 100)))
        pump.drain(limit=1)
        self.assertFalse(inbox.accepting)
        pump.drain(limit=1)
        self.assertEqual(aggregator.snapshot().total_damage, 11)
        self.assertFalse(inbox.accepting)
        pump.drain(limit=1)
        self.assertTrue(inbox.accepting)
        self.assertTrue(aggregator.snapshot().data_incomplete)
        inbox.publish_event(damage(3, 17))
        pump.drain()
        self.assertEqual(aggregator.snapshot().total_damage, 28)
        self.assertIsNone(pump.fault_code)
        self.assertTrue(aggregator.snapshot().data_incomplete)

    def test_background_consumer_handles_burst_without_any_ui_drains(self) -> None:
        inbox, aggregator = CombatInbox(max_items=8), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        stream = StreamWithIdleTail([encoded(status_event(), *(damage(i) for i in range(1, 1002)))])
        client = CombatBridgeClient(inbox, connector=lambda: stream, reconnect_delay=0.01)
        pump.note_ui_tick()
        pump.start()
        client.start()
        try:
            self.wait_for(lambda: aggregator.snapshot().last_sequence == 1001)
            state = pump.diagnostic_state()
            self.assertEqual(aggregator.snapshot().total_damage, 7007)
            self.assertFalse(aggregator.snapshot().data_incomplete)
            self.assertEqual(state["counts"]["processed"], 1002)
            self.assertLessEqual(state["inbox"]["high_water"], 8)
            self.assertEqual(state["inbox"]["dropped_lower_bound"], 0)
            self.assertGreater(state["ui_tick_age_seconds"], 0)
            self.assertTrue(pump.running)
        finally:
            client.stop()
            self.assertTrue(pump.stop())

    def test_client_remains_alive_and_resumes_after_forced_overflow(self) -> None:
        inbox, aggregator = CombatInbox(max_items=3), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        first = StreamWithIdleTail([encoded(status_event(), damage(1, 11), damage(2, 100))])
        second = StreamWithIdleTail([encoded(status_event(3, status="session_started", detail="degraded:transport_reconnected"), damage(4, 17))])
        streams = iter((first, second))
        client = CombatBridgeClient(inbox, connector=lambda: next(streams), reconnect_delay=0.01)
        client.start()
        try:
            self.wait_for(lambda: inbox.diagnostic_state()["overflow_pending"])
            self.assertTrue(client.running)
            pump.start()
            self.wait_for(lambda: aggregator.snapshot().last_sequence == 4)
            self.assertTrue(first.closed)
            self.assertFalse(second.closed)
            self.assertEqual(aggregator.snapshot().total_damage, 28)
            self.assertTrue(aggregator.snapshot().data_incomplete)
            self.assertTrue(any(row["code"] == "queue_overflow" for row in pump.diagnostic_state()["recent_issues"]))
            self.assertTrue(client.running)
        finally:
            client.stop()
            self.assertTrue(pump.stop())

    def test_bridge_error_reconnects_and_does_not_lock_the_session(self) -> None:
        inbox, aggregator = CombatInbox(), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        first = StreamWithIdleTail([encoded(status_event(), damage(1, 11), status_event(2, status="error", detail="bridge_queue_full"))])
        second = StreamWithIdleTail([encoded(status_event(3, status="session_started", detail="degraded:transport_reconnected"), damage(4, 17))])
        streams = iter((first, second))
        client = CombatBridgeClient(inbox, connector=lambda: next(streams), reconnect_delay=0.01)
        pump.start()
        client.start()
        try:
            self.wait_for(lambda: aggregator.snapshot().last_sequence == 4)
            self.assertEqual(aggregator.snapshot().total_damage, 28)
            self.assertTrue(aggregator.snapshot().data_incomplete)
            self.assertEqual(aggregator.snapshot().connection_state, "live")
            self.assertEqual(pump.diagnostic_state()["last_fault_code"], "bridge_queue_full")
            self.assertIsNone(pump.fault_code)
        finally:
            client.stop()
            self.assertTrue(pump.stop())

    def test_gap_resets_recent_dps_and_survives_room_and_official_status(self) -> None:
        aggregator = CombatAggregator(clock_ms=lambda: 0)
        aggregator.ingest(status_event())
        aggregator.ingest(damage(1, 20))
        self.assertGreater(aggregator.snapshot().recent_dps, 0)
        aggregator.mark_data_gap("missing_record")
        self.assertEqual(aggregator.snapshot().recent_dps, 0)
        aggregator.ingest(status_event(2, status="party_updated", party_members=[{
            "player_id": "player-0", "player_slot": 0, "is_local": True,
            "official_damage": 100, "official_boss_damage": 0, "official_taken_damage": 0,
        }]))
        aggregator.ingest(status_event(3, status="session_ended"))
        snapshot = aggregator.snapshot()
        self.assertEqual(snapshot.total_damage, 100)
        self.assertTrue(snapshot.official_damage_complete)
        self.assertTrue(snapshot.data_incomplete)
        compact = combat_status_presentation(snapshot, compact=True)
        self.assertEqual(compact.label, "● 数据有缺口")
        self.assertEqual(compact.color, GOLD)
        self.assertIn("结算值已更新", combat_status_presentation(snapshot).explanation)
        aggregator.apply_transport_state("connecting")
        self.assertEqual(combat_status_presentation(aggregator.snapshot(), compact=True).label, "● 重连中")

    def test_idle_reconnect_does_not_reclassify_a_completed_session_as_incomplete(self) -> None:
        inbox, aggregator = CombatInbox(), CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        inbox.publish_event(status_event())
        inbox.publish_event(status_event(1, status="session_ended"))
        for state in ("disconnected", "connecting", "disconnected", "stale"):
            inbox.publish_notice(state, "pipe_idle")
        pump.drain()
        self.assertEqual(aggregator.snapshot().connection_state, "ended")
        self.assertFalse(aggregator.snapshot().data_incomplete)
        self.assertIsNone(pump.fault_code)

    def test_missing_end_boundary_still_archives_the_previous_valid_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inbox, aggregator = CombatInbox(), CombatAggregator()
            archiver = CombatMatchArchiver(Path(directory), app_version="1.7.7", snapshot_provider=aggregator.snapshot)
            controller = CombatDiagnosticsController(archiver)
            pump = CombatEventPump(inbox, self.validator, aggregator,
                                   event_batch_sink=controller.record_events,
                                   event_batch_context=controller.capture_batch)
            for event in (status_event(), damage(1, 11), status_event(0, session_id="next", event_id="next:0")):
                inbox.publish_event(event)
            pump.drain()
            self.assertIsNone(controller.last_error)
            paths = list(Path(directory).glob("*.zip"))
            self.assertEqual(len(paths), 1)
            with zipfile.ZipFile(paths[0]) as archive:
                summary = json.loads(archive.read("summary.json"))
                self.assertEqual(summary["session_id"], "session-a")
                self.assertEqual(summary["total_damage"], 11)
                self.assertEqual(len(archive.read("events.jsonl").splitlines()), 2)

    def test_export_reports_active_fault_and_persistent_gap_without_marking_collection_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            exporter, _game = fixture(Path(directory), game_present=False)
            report = read_report(exporter.export({
                "combat": {"data_incomplete": True, "last_data_gap": "sequence_gap"},
                "transport": {"fault_code": "queue_overflow", "recent_issues": [{"sample": "bad record"}]},
            }).path)
            self.assertFalse(report["partial"])
            self.assertEqual({row["code"] for row in report["findings"]}, {"combat_transport_fault", "combat_data_incomplete"})
            recovered = read_report(exporter.export({"combat": {"data_incomplete": True}, "transport": {"fault_code": None}}).path)
            self.assertEqual([row["code"] for row in recovered["findings"]], ["combat_data_incomplete"])

    def test_controller_serializes_disable_with_inflight_event_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archiver = CombatMatchArchiver(Path(directory), app_version="1.7.7", snapshot_provider=CombatAggregator().snapshot)
            controller = CombatDiagnosticsController(archiver)
            entered, release, disabled = threading.Event(), threading.Event(), threading.Event()
            def write(_events):
                entered.set()
                release.wait(2)
            with mock.patch.object(archiver, "record_events", side_effect=write), mock.patch.object(archiver, "checkpoint") as checkpoint:
                writer = threading.Thread(target=lambda: controller.record_events([status_event()]))
                toggle = threading.Thread(target=lambda: (controller.set_enabled(False), disabled.set()))
                writer.start()
                self.assertTrue(entered.wait(1))
                toggle.start()
                self.assertFalse(disabled.wait(0.05))
                release.set()
                writer.join(1)
                toggle.join(1)
                self.assertTrue(disabled.is_set())
                self.assertFalse(controller.enabled)
                checkpoint.assert_called_once()

    def test_manual_export_cannot_capture_totals_ahead_of_the_recorded_event_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inbox, aggregator = CombatInbox(), CombatAggregator()
            archiver = CombatMatchArchiver(Path(directory), app_version="1.7.7", snapshot_provider=aggregator.snapshot)
            controller = CombatDiagnosticsController(archiver)
            entered, release, exported = threading.Event(), threading.Event(), threading.Event()
            paths = []
            def sink(events):
                entered.set()
                release.wait(2)
                controller.record_events(events)
            def export():
                paths.append(controller.export_manual())
                exported.set()
            pump = CombatEventPump(inbox, self.validator, aggregator, event_batch_sink=sink,
                                   event_batch_context=controller.capture_batch)
            inbox.publish_event(status_event())
            inbox.publish_event(damage(1, 11))
            pump.start()
            export_thread = threading.Thread(target=export)
            try:
                self.assertTrue(entered.wait(1))
                self.assertEqual(aggregator.snapshot().total_damage, 11)
                export_thread.start()
                self.assertFalse(exported.wait(0.05))
                release.set()
                export_thread.join(2)
                self.assertTrue(exported.is_set())
                with zipfile.ZipFile(paths[0]) as archive:
                    summary = json.loads(archive.read("summary.json"))
                    events = [json.loads(line) for line in archive.read("events.jsonl").splitlines()]
                self.assertEqual(summary["total_damage"], 11)
                self.assertEqual(summary["last_sequence"], 1)
                self.assertEqual([event["sequence"] for event in events], [0, 1])
            finally:
                release.set()
                self.assertTrue(pump.stop())
                if export_thread.ident is not None:
                    export_thread.join(2)


if __name__ == "__main__":
    unittest.main()
