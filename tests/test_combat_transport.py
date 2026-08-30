from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import unittest
import uuid

from toolbox.combat_aggregator import CombatAggregator
from toolbox.combat_transport import (
    CombatBridgeClient,
    CombatEventPump,
    CombatEventValidator,
    CombatInbox,
    CombatLineDecoder,
    NamedPipeConnector,
    CombatProtocolError,
    CombatSchemaError,
    TransportNotice,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def status_event(sequence: int = 0, **fields: object) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": 2,
        "event_id": f"session-a:{sequence}",
        "event_type": "status",
        "session_id": "session-a",
        "sequence": sequence,
        "monotonic_ms": sequence * 100,
        "room_id": None,
        "aggregate": False,
        "hook_path": "bridge.lifecycle",
        "status": "session_started" if sequence == 0 else "live",
    }
    event.update(fields)
    return event


class FakeStream:
    def __init__(self, chunks: list[bytes], read_event: threading.Event | None = None) -> None:
        self.chunks = list(chunks)
        self.read_event = read_event
        self.closed = False

    def read(self, _size: int) -> bytes:
        if self.chunks:
            chunk = self.chunks.pop(0)
            if self.read_event is not None:
                self.read_event.set()
            return chunk
        return b""

    def close(self) -> None:
        self.closed = True


class IdleStream(FakeStream):
    def read(self, _size: int) -> bytes | None:
        if self.closed:
            return b""
        time.sleep(0.005)
        return None


class CombatLineDecoderTests(unittest.TestCase):
    def test_partial_and_multiple_lines_are_preserved_in_order(self) -> None:
        decoder = CombatLineDecoder()
        self.assertEqual(decoder.feed(b'{"first":'), [])
        self.assertEqual(
            decoder.feed(b'1}\n{"second":2}\r\n'),
            [{"first": 1}, {"second": 2}],
        )
        decoder.finish()

    def test_invalid_utf8_json_and_non_object_are_rejected(self) -> None:
        cases = (
            (b'\xff\n', "invalid_utf8"),
            (b'{broken}\n', "invalid_json"),
            (b'[1,2]\n', "event_not_object"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(CombatProtocolError, code):
                    CombatLineDecoder().feed(payload)

    def test_overlong_and_unterminated_lines_fail_closed(self) -> None:
        with self.assertRaisesRegex(CombatProtocolError, "line_too_long"):
            CombatLineDecoder(max_line_bytes=8).feed(b"123456789")
        decoder = CombatLineDecoder()
        decoder.feed(b'{"partial":true}')
        with self.assertRaisesRegex(CombatProtocolError, "unterminated_line"):
            decoder.finish()


class CombatTransportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = CombatEventValidator.from_file(
            PROJECT_ROOT / "contracts" / "combat_event.schema.json"
        )

    def test_schema_validator_accepts_minimal_status_event(self) -> None:
        self.validator.validate(status_event())

    def test_schema_accepts_official_mana_spend_without_snapshot_values(self) -> None:
        event = status_event(
            1,
            event_type="resource_change",
            aggregate=True,
            hook_path="settlement.official_mana_spend",
            resource="mp",
            resource_operation="spend",
            requested_delta=-24,
            effective_delta=-24,
            value_before=None,
            value_after=None,
            max_before=None,
            max_after=None,
            blocked=False,
            overflow=0,
            source_token="resource.skill_cost",
            trigger_kind="skill_use",
            parent_operation_id=None,
            nesting_depth=0,
        )
        event.pop("status")
        self.validator.validate(event)

    def test_schema_accepts_official_mana_recovery_without_snapshot_values(self) -> None:
        event = status_event(
            1,
            event_type="resource_change",
            aggregate=True,
            hook_path="player.official_mana_recovery",
            resource="mp",
            resource_operation="gain",
            requested_delta=24,
            effective_delta=24,
            value_before=None,
            value_after=None,
            max_before=None,
            max_after=None,
            blocked=False,
            overflow=0,
            source_token="resource.mana_recovery",
            parent_operation_id=None,
            nesting_depth=0,
        )
        event.pop("status")
        self.validator.validate(event)

    def test_schema_accepts_low_level_mana_recovery_fallback(self) -> None:
        event = status_event(
            1,
            event_type="resource_change",
            aggregate=True,
            hook_path="runtime.update_mp",
            resource="mp",
            resource_operation="gain",
            requested_delta=29.75,
            effective_delta=29.75,
            value_before=100.25,
            value_after=130,
            max_before=130,
            max_after=130,
            blocked=False,
            overflow=0,
            source_token="resource.mana_recovery",
            parent_operation_id=None,
            nesting_depth=0,
        )
        event.pop("status")
        self.validator.validate(event)

    def test_hp_lock_loss_is_valid_for_all_observed_nightmare_tiers(self) -> None:
        for locked_ratio, value_after in ((0.20, 112), (0.40, 84), (0.65, 49)):
            with self.subTest(locked_ratio=locked_ratio):
                event = status_event(
                    1,
                    event_type="resource_change",
                    aggregate=True,
                    hook_path="runtime.set_cur_hp",
                    resource="hp",
                    resource_operation="loss",
                    requested_delta=value_after - 140,
                    effective_delta=value_after - 140,
                    value_before=140,
                    value_after=value_after,
                    max_before=140,
                    max_after=140,
                    blocked=False,
                    overflow=0,
                    source_token="set_cur_hp",
                    parent_operation_id=None,
                    nesting_depth=0,
                )
                event.pop("status")
                self.validator.validate(event)

                inbox = CombatInbox()
                aggregator = CombatAggregator()
                pump = CombatEventPump(inbox, self.validator, aggregator)
                inbox.publish_event(status_event())
                inbox.publish_event(event)
                report = pump.drain()
                self.assertIsNone(report.fault_code)
                self.assertEqual(aggregator.snapshot().connection_state, "live")
                self.assertEqual(
                    aggregator.snapshot().hp_loss_other,
                    140 - value_after,
                )

        invalid = dict(event)
        invalid["resource_operation"] = "drain"
        with self.assertRaisesRegex(CombatSchemaError, "/resource_operation:enum"):
            self.validator.validate(invalid)

    def test_hp_state_transitions_cover_max_hp_curse_cleanse_and_potions(self) -> None:
        cases = (
            # Champion belt: maximum HP itself falls from 100 to 60.
            ("champion_belt_apply", "loss", 100, 60, 100, 60, -40),
            # Cleansing/removing a curse may restore the cap without healing current HP.
            ("champion_belt_cleanse", "set", 60, 60, 60, 100, 0),
            # Generic room potion/treasure maximum-HP increase without a current-HP heal.
            ("potion_max_hp_up", "set", 60, 60, 100, 140, 0),
            # Direct HP costs and ordinary recovery use the same bounded contract.
            ("direct_hp_cost", "loss", 60, 45, 60, 60, -15),
            ("potion_heal", "gain", 45, 55, 60, 60, 10),
        )
        for name, operation, before, after, max_before, max_after, delta in cases:
            with self.subTest(name=name):
                event = status_event(
                    1,
                    event_type="resource_change",
                    aggregate=True,
                    hook_path=f"qa.{name}",
                    resource="hp",
                    resource_operation=operation,
                    requested_delta=delta,
                    effective_delta=delta,
                    value_before=before,
                    value_after=after,
                    max_before=max_before,
                    max_after=max_after,
                    blocked=False,
                    overflow=0,
                    source_token=name,
                    parent_operation_id=None,
                    nesting_depth=0,
                )
                event.pop("status")
                self.validator.validate(event)
                inbox = CombatInbox()
                aggregator = CombatAggregator()
                pump = CombatEventPump(inbox, self.validator, aggregator)
                inbox.publish_event(status_event())
                inbox.publish_event(event)
                report = pump.drain()
                self.assertIsNone(report.fault_code)
                self.assertEqual(aggregator.snapshot().connection_state, "live")

    def test_schema_error_reports_only_path_and_keyword(self) -> None:
        event = status_event(session_id="private-account-token" * 20)
        with self.assertRaises(CombatSchemaError) as caught:
            self.validator.validate(event)
        message = str(caught.exception)
        self.assertIn("/session_id:maxLength", message)
        self.assertNotIn("private-account-token", message)

    def test_schema_accepts_sixteen_players_and_rejects_seventeen(self) -> None:
        members = [
            {
                "player_id": f"opaque-player-{index}",
                "player_slot": index,
                "is_local": index == 15,
            }
            for index in range(16)
        ]
        self.validator.validate(
            status_event(1, status="party_updated", party_members=members)
        )
        with self.assertRaises(CombatSchemaError):
            self.validator.validate(
                status_event(
                    2,
                    status="party_updated",
                    party_members=[
                        *members,
                        {
                            "player_id": "opaque-player-16",
                            "player_slot": None,
                            "is_local": False,
                        },
                    ],
                )
            )

    def test_bounded_inbox_surfaces_overflow_instead_of_dropping_silently(self) -> None:
        inbox = CombatInbox(max_items=2)
        self.assertTrue(inbox.publish_event(status_event()))
        self.assertTrue(inbox.publish_event(status_event(1)))
        self.assertFalse(inbox.publish_event(status_event(2)))
        self.assertFalse(inbox.accepting)
        self.assertEqual(
            inbox.drain(),
            [TransportNotice("error", "queue_overflow")],
        )

    def test_sixteen_player_batched_event_pump_stays_live_under_load(self) -> None:
        inbox = CombatInbox()
        aggregator = CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        members = [
            {
                "player_id": f"opaque-player-{index}",
                "player_slot": index,
                # Exercise a client: slot 0 is the remote host and the local
                # player occupies slot 12.
                "is_local": index == 12,
            }
            for index in range(16)
        ]
        self.assertTrue(inbox.publish_event(status_event()))
        self.assertTrue(
            inbox.publish_event(
                status_event(
                    1,
                    status="party_updated",
                    party_members=members,
                )
            )
        )
        first_report = pump.drain()
        self.assertEqual(first_report.processed_events, 2)
        self.assertIsNone(first_report.fault_code)

        sequence = 2
        expected = {str(member["player_id"]): 0 for member in members}
        started = time.perf_counter()
        for _batch in range(10):
            for _event_index in range(320):
                player_index = sequence % 16
                player_id = f"opaque-player-{player_index}"
                damage = player_index + 1
                expected[player_id] += damage
                event = status_event(
                    sequence,
                    event_type="damage_resolution",
                    aggregate=True,
                    hook_path="settlement.official_attacker",
                    damage_direction="dealt",
                    hit_id=sequence,
                    target_id=f"target-{sequence}",
                    pre_mitigation_damage=damage,
                    post_mitigation_damage=damage,
                    applied_hp_damage=damage,
                    settlement_damage=damage,
                    mitigated_damage=0,
                    overkill_damage=0,
                    damage_outcome="applied",
                    is_boss=sequence % 25 == 0,
                    owner_player_id=player_id,
                    source_token="combat.player.normal",
                )
                event.pop("status")
                self.assertTrue(inbox.publish_event(event))
                sequence += 1
            report = pump.drain()
            self.assertEqual(report.processed_events, 320)
            self.assertIsNone(report.fault_code)

        elapsed = time.perf_counter() - started
        snapshot = aggregator.snapshot(monotonic_ms=sequence * 100)
        self.assertLess(elapsed, 5.0)
        self.assertEqual(snapshot.connection_state, "live")
        self.assertEqual(snapshot.detected_player_count, 16)
        self.assertEqual(snapshot.total_damage, sum(expected.values()))
        self.assertEqual(snapshot.personal_damage, expected["opaque-player-12"])
        self.assertEqual(snapshot.unattributed_damage, 0)
        for player_id, damage in expected.items():
            self.assertEqual(snapshot.player_breakdown[player_id]["damage_dealt"], damage)

    def test_pump_applies_notices_and_events_only_when_drained(self) -> None:
        inbox = CombatInbox()
        aggregator = CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        inbox.publish_notice("connecting", "pipe_connecting")
        inbox.publish_event(status_event())
        self.assertEqual(aggregator.snapshot().connection_state, "disconnected")
        report = pump.drain()
        self.assertEqual(report.processed_events, 1)
        self.assertEqual(report.notices, 1)
        self.assertIsNone(report.fault_code)
        self.assertEqual(aggregator.snapshot().connection_state, "live")

    def test_schema_failure_stops_further_aggregation(self) -> None:
        inbox = CombatInbox()
        aggregator = CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        inbox.publish_event({"schema_version": 2})
        inbox.publish_event(status_event())
        report = pump.drain()
        self.assertEqual(report.processed_events, 0)
        self.assertIsNotNone(report.fault_code)
        self.assertEqual(aggregator.snapshot().connection_state, "error")
        self.assertIsNone(aggregator.snapshot().session_id)

    def test_client_thread_never_mutates_aggregator(self) -> None:
        inbox = CombatInbox()
        aggregator = CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        delivered = threading.Event()
        line = json.dumps(status_event()).encode("utf-8") + b"\n"
        stream = FakeStream([line], delivered)
        client = CombatBridgeClient(
            inbox,
            connector=lambda: stream,
            reconnect_delay=10,
        )
        client.start()
        self.assertTrue(delivered.wait(1.0))
        client.stop()
        self.assertIsNone(aggregator.snapshot().session_id)
        report = pump.drain()
        self.assertEqual(report.processed_events, 1)
        self.assertEqual(aggregator.snapshot().session_id, "session-a")

    def test_client_surfaces_a_missing_heartbeat_as_stale(self) -> None:
        inbox = CombatInbox()
        stream = IdleStream([])
        client = CombatBridgeClient(
            inbox,
            connector=lambda: stream,
            reconnect_delay=10,
            stale_after=0.02,
        )
        client.start()
        deadline = time.monotonic() + 1.0
        notices: list[object] = []
        while time.monotonic() < deadline:
            notices.extend(inbox.drain())
            if TransportNotice("stale", "heartbeat_timeout") in notices:
                break
            time.sleep(0.01)
        client.stop()
        self.assertIn(TransportNotice("stale", "heartbeat_timeout"), notices)

    @unittest.skipUnless(os.name == "nt", "Windows named pipes are required")
    def test_real_named_pipe_roundtrip_reaches_the_main_thread_pump(self) -> None:
        try:
            import win32file
            import win32pipe
        except ImportError:
            self.skipTest("pywin32 is not installed")

        pipe_name = rf"\\.\pipe\LC2CombatBridge.Test.{uuid.uuid4().hex}"
        ready = threading.Event()
        line = json.dumps(status_event()).encode("utf-8") + b"\n"

        def serve() -> None:
            handle = win32pipe.CreateNamedPipe(
                pipe_name,
                win32pipe.PIPE_ACCESS_OUTBOUND,
                win32pipe.PIPE_TYPE_BYTE
                | win32pipe.PIPE_READMODE_BYTE
                | win32pipe.PIPE_WAIT,
                1,
                8192,
                8192,
                0,
                None,
            )
            ready.set()
            try:
                win32pipe.ConnectNamedPipe(handle, None)
                win32file.WriteFile(handle, line)
                time.sleep(0.1)
            finally:
                try:
                    win32pipe.DisconnectNamedPipe(handle)
                except Exception:
                    pass
                win32file.CloseHandle(handle)

        server = threading.Thread(target=serve, daemon=True)
        server.start()
        self.assertTrue(ready.wait(1.0))
        inbox = CombatInbox()
        aggregator = CombatAggregator()
        pump = CombatEventPump(inbox, self.validator, aggregator)
        client = CombatBridgeClient(
            inbox,
            connector=NamedPipeConnector(pipe_name),
            reconnect_delay=10,
        )
        client.start()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and aggregator.snapshot().session_id is None:
            pump.drain()
            time.sleep(0.01)
        client.stop()
        server.join(1.0)
        self.assertEqual(aggregator.snapshot().session_id, "session-a")


if __name__ == "__main__":
    unittest.main()
