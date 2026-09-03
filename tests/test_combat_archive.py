from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from toolbox.combat_archive import (
    DEFAULT_MAX_EVENT_BYTES,
    CombatArchiveError,
    CombatDiagnosticsController,
    CombatMatchArchiver,
    check_combat_archive_consistency,
)
from toolbox.combat_aggregator import CombatAggregator


FIXED_NOW = datetime(2026, 9, 1, 2, 30, 45, tzinfo=timezone.utc)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWN_RED_R22_ARCHIVE = (
    PROJECT_ROOT
    / "artifacts"
    / "runtime-captures"
    / "2026-09-02-r22-two-player-full-run-live-final-divergence"
    / "2026-09-02_113803_恢复_55BCED8198.zip"
)
R22_EVENT_SESSION_ID = "52147703a7b0443fb70245f9e6be328b"
R22_WRONG_SUMMARY_SESSION_ID = "c0b279f7314f43dda329bb3676180f25"


def event(
    sequence: int,
    status: str,
    *,
    session_id: str = "session-a",
) -> dict[str, object]:
    return {
        "schema_version": 2,
        "event_id": f"{session_id}:{sequence}",
        "event_type": "status",
        "session_id": session_id,
        "sequence": sequence,
        "monotonic_ms": sequence * 100,
        "room_id": None,
        "aggregate": False,
        "hook_path": "bridge.lifecycle",
        "status": status,
    }


class CombatMatchArchiverTests(unittest.TestCase):
    def test_default_event_budget_covers_recorded_full_run(self) -> None:
        self.assertEqual(DEFAULT_MAX_EVENT_BYTES, 128 * 1024 * 1024)

    def snapshot(self) -> dict[str, object]:
        return {
            "session_id": "session-a",
            "connection_state": "ended",
            "personal_damage": 1234,
            "player_breakdown": {
                "player-1": {"player_slot": 0, "official_damage": 1234}
            },
        }

    def make_archiver(
        self,
        root: Path,
        *,
        max_event_bytes: int = DEFAULT_MAX_EVENT_BYTES,
        snapshot_provider=None,
    ) -> CombatMatchArchiver:
        return CombatMatchArchiver(
            root,
            app_version="1.6.3",
            snapshot_provider=snapshot_provider or self.snapshot,
            max_event_bytes=max_event_bytes,
            now=lambda: FIXED_NOW,
        )

    @staticmethod
    def session_snapshot(
        session_id: str | None,
        *,
        damage: int,
        connection_state: str = "live",
    ) -> dict[str, object]:
        return {
            "session_id": session_id,
            "connection_state": connection_state,
            "personal_damage": damage,
            "player_breakdown": {},
        }

    @staticmethod
    def read_archive(
        path: Path,
    ) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            summary = json.loads(archive.read("summary.json"))
            events = [
                json.loads(line)
                for line in archive.read("events.jsonl").decode("utf-8").splitlines()
            ]
        return manifest, summary, events

    @staticmethod
    def write_archive_fixture(
        path: Path,
        *,
        manifest_session_id: str,
        summary_session_id: str,
        events_session_id: str,
        duplicate_event_id: bool = False,
        archive_reason: str = "superseded",
    ) -> None:
        event_items = [event(0, "live", session_id=events_session_id)]
        if duplicate_event_id:
            event_items.append(dict(event_items[0]))
        events_bytes = "".join(
            json.dumps(item, separators=(",", ":")) + "\n"
            for item in event_items
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "app_version": "1.6.3",
            "archive_reason": archive_reason,
            "session_key": CombatMatchArchiver._session_key(manifest_session_id),
            "started_at": FIXED_NOW.isoformat(),
            "archived_at": FIXED_NOW.isoformat(),
            "event_count": len(event_items),
            "event_bytes": len(events_bytes),
            "events_truncated": False,
            "events_sha256": hashlib.sha256(events_bytes).hexdigest().upper(),
            "privacy": "anonymous_protocol_tokens_only",
        }
        summary = CombatMatchArchiverTests.session_snapshot(
            summary_session_id,
            damage=0,
        )
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("summary.json", json.dumps(summary))
            archive.writestr("events.jsonl", events_bytes)

    def test_known_red_r22_cross_session_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            portable_red = Path(temp_dir) / "r22-known-red.zip"
            self.write_archive_fixture(
                portable_red,
                manifest_session_id=R22_EVENT_SESSION_ID,
                summary_session_id=R22_WRONG_SUMMARY_SESSION_ID,
                events_session_id=R22_EVENT_SESSION_ID,
            )
            self.assertEqual(
                CombatMatchArchiver._session_key(R22_EVENT_SESSION_ID),
                "55BCED8198",
            )

            with self.assertRaisesRegex(
                CombatArchiveError,
                "archive_summary_session_mismatch",
            ):
                check_combat_archive_consistency(portable_red)

        if KNOWN_RED_R22_ARCHIVE.is_file():
            with self.assertRaisesRegex(
                CombatArchiveError,
                "archive_summary_session_mismatch",
            ):
                check_combat_archive_consistency(KNOWN_RED_R22_ARCHIVE)

    def test_checker_rejects_events_from_a_different_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "events-cross-session.zip"
            self.write_archive_fixture(
                archive_path,
                manifest_session_id="session-a",
                summary_session_id="session-a",
                events_session_id="session-b",
            )

            with self.assertRaisesRegex(
                CombatArchiveError,
                "archive_events_session_mismatch",
            ):
                check_combat_archive_consistency(archive_path)

    def test_checker_rejects_duplicate_event_ids_within_one_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "duplicate-event-id.zip"
            self.write_archive_fixture(
                archive_path,
                manifest_session_id="session-a",
                summary_session_id="session-a",
                events_session_id="session-a",
                duplicate_event_id=True,
            )

            with self.assertRaisesRegex(
                CombatArchiveError,
                "archive_duplicate_event_id",
            ):
                check_combat_archive_consistency(archive_path)

    def test_invalid_existing_automatic_archive_does_not_finalize_its_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            root.mkdir(parents=True)
            invalid_archive = root / "invalid-automatic.zip"
            self.write_archive_fixture(
                invalid_archive,
                manifest_session_id="session-a",
                summary_session_id="session-a",
                events_session_id="session-b",
                archive_reason="automatic",
            )
            archiver = self.make_archiver(root)

            archiver.record_events([event(0, "session_started")])

            self.assertEqual(
                archiver.active_session_key,
                CombatMatchArchiver._session_key("session-a"),
            )
            self.assertEqual(len(list(root.glob("_partial_*"))), 1)
            self.assertIsNone(archiver.last_error)

    def test_known_good_session_end_creates_one_complete_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            archiver.record_events(
                [event(0, "session_started"), event(1, "session_ended")]
            )

            archives = list(root.glob("*.zip"))
            self.assertEqual(len(archives), 1)
            self.assertFalse(list(root.glob("_partial_*")))
            with zipfile.ZipFile(archives[0]) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"manifest.json", "summary.json", "events.jsonl"},
                )
                manifest = json.loads(archive.read("manifest.json"))
                summary = json.loads(archive.read("summary.json"))
                lines = archive.read("events.jsonl").decode("utf-8").splitlines()
            self.assertEqual(manifest["archive_reason"], "automatic")
            self.assertEqual(manifest["event_count"], 2)
            self.assertFalse(manifest["events_truncated"])
            self.assertEqual(manifest["privacy"], "anonymous_protocol_tokens_only")
            self.assertEqual(summary["personal_damage"], 1234)
            self.assertEqual(len(lines), 2)
            result = check_combat_archive_consistency(archives[0])
            self.assertEqual(result.session_key, manifest["session_key"])
            self.assertEqual(result.summary_session_id, "session-a")

    def test_official_three_field_final_and_session_end_archive_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            aggregator = CombatAggregator(ended_retention_ms=None)
            archiver = self.make_archiver(
                root,
                snapshot_provider=lambda: aggregator.snapshot().to_dict(),
            )
            party = event(1, "party_updated")
            party["party_members"] = [
                {
                    "player_id": "player-1",
                    "player_slot": 0,
                    "is_local": True,
                    "official_damage": 1_451_098,
                    "official_boss_damage": 240_540,
                    "official_taken_damage": 387,
                }
            ]
            events = [event(0, "session_started"), party, event(2, "session_ended")]
            for item in events:
                aggregator.ingest(item)
                archiver.record_events([item])

            archive_path = next(root.glob("*.zip"))
            manifest, summary, archived_events = self.read_archive(archive_path)
            self.assertEqual(manifest["archive_reason"], "automatic")
            self.assertEqual(len(archived_events), 3)
            self.assertEqual(summary["connection_state"], "ended")
            self.assertTrue(summary["official_damage_complete"])
            self.assertTrue(summary["official_boss_damage_complete"])
            self.assertTrue(summary["official_taken_damage_complete"])
            self.assertEqual(summary["total_damage"], 1_451_098)
            self.assertEqual(summary["boss_damage"], 240_540)
            self.assertEqual(summary["taken_settlement_damage"], 387)
            check_combat_archive_consistency(archive_path)

    def test_manual_export_is_repeatable_without_ending_active_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            archiver.record_events([event(0, "session_started")])

            first = archiver.export_manual()
            second = archiver.export_manual()

            self.assertNotEqual(first, second)
            self.assertTrue(first.is_file())
            self.assertTrue(second.is_file())
            self.assertIsNotNone(archiver.active_session_key)
            self.assertEqual(len(list(root.glob("_partial_*"))), 1)
            with zipfile.ZipFile(first) as archive:
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["archive_reason"], "manual")

    def test_positive_control_stale_partial_is_recovered_on_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            state = self.session_snapshot("session-a", damage=100)
            first = self.make_archiver(root, snapshot_provider=lambda: state)
            first.record_events([event(0, "session_started")])
            self.assertEqual(len(list(root.glob("_partial_*"))), 1)

            state = self.session_snapshot("session-b", damage=0)
            recovered = self.make_archiver(root, snapshot_provider=lambda: state)

            self.assertIsNone(recovered.last_error)
            self.assertFalse(list(root.glob("_partial_*")))
            archives = list(root.glob("*.zip"))
            self.assertEqual(len(archives), 1)
            manifest, summary, events = self.read_archive(archives[0])
            self.assertEqual(manifest["archive_reason"], "recovered")
            self.assertEqual(summary["session_id"], "session-a")
            self.assertEqual(summary["personal_damage"], 100)
            self.assertEqual({item["session_id"] for item in events}, {"session-a"})
            check_combat_archive_consistency(archives[0])

    def test_cross_session_stale_partial_is_refused_instead_of_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            state = self.session_snapshot("session-a", damage=100)
            first = self.make_archiver(root, snapshot_provider=lambda: state)
            first.record_events([event(0, "session_started")])
            partial = next(root.glob("_partial_*"))
            (partial / "summary.json").write_text(
                json.dumps(
                    self.session_snapshot("session-b", damage=0),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            recovered = self.make_archiver(
                root,
                snapshot_provider=lambda: self.session_snapshot("session-b", damage=0),
            )

            self.assertFalse(list(root.glob("*.zip")))
            self.assertTrue(partial.is_dir())
            self.assertEqual(recovered.last_error, "CombatArchiveError")

    def test_positive_control_event_limit_marks_archive_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root, max_event_bytes=1)
            archiver.record_events(
                [event(0, "session_started"), event(1, "session_ended")]
            )

            archive_path = next(root.glob("*.zip"))
            with zipfile.ZipFile(archive_path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                event_bytes = archive.read("events.jsonl")
            self.assertTrue(manifest["events_truncated"])
            self.assertEqual(manifest["event_count"], 2)
            self.assertEqual(event_bytes, b"")

    def test_manual_export_without_session_still_writes_current_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)

            archive_path = archiver.export_manual()

            with zipfile.ZipFile(archive_path) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                summary = json.loads(archive.read("summary.json"))
            self.assertEqual(manifest["archive_reason"], "manual")
            self.assertEqual(
                manifest["session_key"],
                CombatMatchArchiver._session_key("session-a"),
            )
            self.assertEqual(summary["personal_damage"], 1234)
            check_combat_archive_consistency(archive_path)

    def test_manual_export_without_a_snapshot_session_uses_no_session_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(
                root,
                snapshot_provider=lambda: self.session_snapshot(None, damage=0),
            )

            archive_path = archiver.export_manual()

            manifest, summary, events = self.read_archive(archive_path)
            self.assertEqual(manifest["session_key"], "no-session")
            self.assertIsNone(summary["session_id"])
            self.assertEqual(events, [])
            check_combat_archive_consistency(archive_path)

    def test_manual_export_after_auto_final_returns_complete_last_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            archiver.record_events(
                [event(0, "session_started"), event(1, "session_ended")]
            )
            automatic = next(root.glob("*.zip"))

            manual_result = archiver.export_manual()

            self.assertEqual(manual_result, automatic)
            with zipfile.ZipFile(manual_result) as archive:
                self.assertEqual(
                    len(archive.read("events.jsonl").decode("utf-8").splitlines()),
                    2,
                )

    def test_positive_control_orphan_session_end_storm_creates_no_archives(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            endings = [event(sequence, "session_ended") for sequence in range(74)]

            archiver.record_events(endings)

            self.assertFalse(list(root.glob("*.zip")))
            self.assertFalse(list(root.glob("_partial_*")))
            self.assertIsNone(archiver.active_session_key)
            self.assertIsNone(archiver.last_error)

    def test_late_events_do_not_reopen_an_automatically_finalized_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            archiver.record_events(
                [event(0, "session_started"), event(1, "session_ended")]
            )
            archiver.record_events(
                [event(2, "session_ended"), event(3, "party_updated")]
            )

            self.assertEqual(len(list(root.glob("*.zip"))), 1)
            self.assertFalse(list(root.glob("_partial_*")))

    def test_recovered_partial_can_continue_the_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            first = self.make_archiver(root)
            first.record_events([event(0, "session_started")])
            recovered = self.make_archiver(root)
            resumed = event(1, "session_started")

            recovered.record_events([resumed])

            self.assertEqual(len(list(root.glob("*.zip"))), 1)
            self.assertIsNotNone(recovered.active_session_key)
            self.assertEqual(len(list(root.glob("_partial_*"))), 1)

    def test_superseded_archive_keeps_old_frozen_summary_when_new_session_is_current(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            state = self.session_snapshot("session-a", damage=100)
            archiver = self.make_archiver(root, snapshot_provider=lambda: state)
            archiver.record_events([event(0, "session_started")])

            state = self.session_snapshot("session-b", damage=0)
            archiver.record_events(
                [
                    event(1, "live"),
                    event(0, "session_started", session_id="session-b"),
                ]
            )

            superseded = next(root.glob("*.zip"))
            manifest, summary, events = self.read_archive(superseded)
            self.assertEqual(manifest["archive_reason"], "superseded")
            self.assertEqual(summary["session_id"], "session-a")
            self.assertEqual(summary["personal_damage"], 100)
            self.assertEqual({item["session_id"] for item in events}, {"session-a"})
            self.assertEqual(
                archiver.active_session_key,
                CombatMatchArchiver._session_key("session-b"),
            )
            check_combat_archive_consistency(superseded)

    def test_interleave_without_an_old_frozen_summary_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            state = self.session_snapshot("session-b", damage=0)
            archiver = self.make_archiver(root, snapshot_provider=lambda: state)

            archiver.record_events(
                [
                    event(0, "session_started"),
                    event(0, "session_started", session_id="session-b"),
                ]
            )

            self.assertFalse(list(root.glob("*.zip")))
            self.assertEqual(len(list(root.glob("_partial_*"))), 1)
            self.assertEqual(archiver.last_error, "CombatArchiveError")
            self.assertEqual(
                archiver.active_session_key,
                CombatMatchArchiver._session_key("session-a"),
            )

    def test_new_session_interleave_finalizes_each_session_with_its_own_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            state = self.session_snapshot("session-a", damage=100)
            archiver = self.make_archiver(root, snapshot_provider=lambda: state)
            archiver.record_events([event(0, "session_started")])

            state = self.session_snapshot("session-b", damage=20)
            archiver.record_events(
                [
                    event(1, "live"),
                    event(0, "session_started", session_id="session-b"),
                ]
            )
            state = self.session_snapshot(
                "session-b",
                damage=250,
                connection_state="ended",
            )
            archiver.record_events([event(1, "session_ended", session_id="session-b")])

            archives = sorted(root.glob("*.zip"))
            self.assertEqual(len(archives), 2)
            by_reason = {}
            for archive_path in archives:
                manifest, summary, events = self.read_archive(archive_path)
                by_reason[manifest["archive_reason"]] = (summary, events)
                check_combat_archive_consistency(archive_path)
            old_summary, old_events = by_reason["superseded"]
            final_summary, final_events = by_reason["automatic"]
            self.assertEqual(old_summary["session_id"], "session-a")
            self.assertEqual({item["session_id"] for item in old_events}, {"session-a"})
            self.assertEqual(final_summary["session_id"], "session-b")
            self.assertEqual(final_summary["personal_damage"], 250)
            self.assertEqual({item["session_id"] for item in final_events}, {"session-b"})

    def test_repeated_manual_exports_preserve_active_frozen_summary_on_provider_mismatch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            state = self.session_snapshot("session-a", damage=100)
            archiver = self.make_archiver(root, snapshot_provider=lambda: state)
            archiver.record_events([event(0, "session_started")])

            state = self.session_snapshot("session-b", damage=0)
            first = archiver.export_manual()
            second = archiver.export_manual()

            self.assertNotEqual(first, second)
            for archive_path in (first, second):
                manifest, summary, events = self.read_archive(archive_path)
                self.assertEqual(manifest["archive_reason"], "manual")
                self.assertEqual(summary["session_id"], "session-a")
                self.assertEqual(summary["personal_damage"], 100)
                self.assertEqual({item["session_id"] for item in events}, {"session-a"})
                check_combat_archive_consistency(archive_path)

    def test_snapshot_provider_failure_reuses_verified_frozen_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            control = {"fail": False}
            snapshot = self.session_snapshot("session-a", damage=100)

            def provider():
                if control["fail"]:
                    raise RuntimeError("snapshot unavailable")
                return snapshot

            archiver = self.make_archiver(root, snapshot_provider=provider)
            archiver.record_events([event(0, "session_started")])
            control["fail"] = True

            archive_path = archiver.export_manual()

            _manifest, summary, events = self.read_archive(archive_path)
            self.assertEqual(summary["session_id"], "session-a")
            self.assertEqual(summary["personal_damage"], 100)
            self.assertEqual({item["session_id"] for item in events}, {"session-a"})
            self.assertIsNone(archiver.last_error)
            check_combat_archive_consistency(archive_path)

    def test_snapshot_provider_failure_without_frozen_summary_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"

            def provider():
                raise RuntimeError("snapshot unavailable")

            archiver = self.make_archiver(root, snapshot_provider=provider)

            archiver.record_events([event(0, "session_started")])

            self.assertFalse(list(root.glob("*.zip")))
            self.assertEqual(len(list(root.glob("_partial_*"))), 1)
            self.assertEqual(archiver.last_error, "CombatArchiveError")
            with self.assertRaisesRegex(CombatArchiveError, "manual_export_failed"):
                archiver.export_manual()

    def test_disabled_diagnostics_controller_does_not_start_a_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            controller = CombatDiagnosticsController(archiver, enabled=False)

            controller.record_events(
                [event(0, "session_started"), event(1, "session_ended")]
            )

            self.assertFalse(list(root.glob("*.zip")))
            self.assertFalse(list(root.glob("_partial_*")))
            self.assertFalse(controller.enabled)

    def test_paused_controller_closes_an_existing_session_without_recording_the_gap(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            changes: list[bool] = []
            controller = CombatDiagnosticsController(
                archiver,
                enabled=True,
                on_enabled_changed=changes.append,
            )
            controller.record_events([event(0, "session_started")])

            controller.set_enabled(False)
            controller.record_events([event(1, "live")])
            controller.record_events([event(2, "session_ended")])

            archive_path = next(root.glob("*.zip"))
            manifest, _summary, events = self.read_archive(archive_path)
            self.assertEqual(manifest["archive_reason"], "automatic")
            self.assertEqual([item["sequence"] for item in events], [0, 2])
            self.assertEqual(changes, [False])
            self.assertFalse(controller.enabled)
            self.assertEqual(controller.root, root.resolve())

    def test_diagnostics_controller_can_resume_and_export_manually(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "对局归档"
            archiver = self.make_archiver(root)
            controller = CombatDiagnosticsController(archiver, enabled=False)

            controller.set_enabled(True)
            controller.record_events([event(0, "session_started")])
            exported = controller.export_manual()

            self.assertTrue(controller.enabled)
            self.assertTrue(exported.is_file())
            manifest, _summary, events = self.read_archive(exported)
            self.assertEqual(manifest["archive_reason"], "manual")
            self.assertEqual([item["sequence"] for item in events], [0])


if __name__ == "__main__":
    unittest.main()
