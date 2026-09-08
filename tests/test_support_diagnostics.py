from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tests.test_mod_manager import plugin_catalog_payload
from toolbox.support_diagnostics import DiagnosticRedactor, SupportDiagnostics


def fixture(root: Path, *, game_present: bool = True, bundled: bool = False) -> tuple[SupportDiagnostics, Path]:
    resource = root / "toolbox"
    assets = resource / "assets"
    assets.mkdir(parents=True)
    config = root / "config"
    config.mkdir()
    (resource / "keyview.py").write_bytes(b"source-fixture")
    (assets / "build_profile.json").write_text(json.dumps({
        "schema_version": 1, "profile_id": "distribution", "combat_diagnostics_available": False,
        "bridge_diagnostics_enabled": False, "default_recording_enabled": False,
    }), encoding="utf-8")
    payload = plugin_catalog_payload(b"plugin")
    operation = payload["entries"][0]["operation"]
    operation.update(bundled=bundled, files=[{"path": "fixture.dll", "size_bytes": 6, "sha256": hashlib.sha256(b"plugin").hexdigest().upper()}])
    if bundled:
        operation["bundle_dir"] = "community_mods/fixture-plugin"
    (assets / "mod_catalog.json").write_text(json.dumps(payload), encoding="utf-8")
    (assets / "community_mod_catalog.json").write_text(json.dumps(payload), encoding="utf-8")
    game = root / "game/LostCastle2.exe"
    game.parent.mkdir()
    if game_present:
        game.write_bytes(b"game")
    core = game.parent / "BepInEx/core/core.dll"
    core.parent.mkdir(parents=True)
    core.write_bytes(b"core")
    manifest = {
        "schema_version": 1, "runtime_version": "fixture-runtime",
        "required_paths": ["BepInEx/core/core.dll"],
        "runtime_files": [{"path": "BepInEx/core/core.dll", "size_bytes": 4, "sha256": hashlib.sha256(b"core").hexdigest().upper()}],
        "bridge": {}, "runtime_archive": {},
    }
    (assets / "lc2_runtime_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    exporter = SupportDiagnostics(
        resource, resource, config, app_version="1.7.7",
        game_exe_provider=lambda: game if game_present else None,
        output_directory=root / "reports", process_probe=lambda _game, _timeout: {"state": "not_running"},
    )
    return exporter, game


def read_report(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("report.json"))


class SupportDiagnosticsTests(unittest.TestCase):
    def test_cli_export_works_before_ui_and_profile_startup_validation(self) -> None:
        import keyview
        with tempfile.TemporaryDirectory() as temporary:
            exporter, _game = fixture(Path(temporary), game_present=False)
            with patch("keyview.resolve_game_exe", return_value=None), patch("keyview.load_settings", return_value={}), patch("keyview.load_build_profile", side_effect=AssertionError("UI startup must not run")), patch("keyview.tk.Tk", side_effect=AssertionError("must not create UI")), patch("sys.stdout", new_callable=io.StringIO) as output:
                code = keyview.main(["--export-diagnostics"], support_exporter=exporter)
            self.assertEqual(code, 0)
            self.assertTrue(Path(output.getvalue().strip()).is_file())

    def test_distribution_exports_without_game_or_detailed_recording(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exporter, _game = fixture(root, game_present=False)
            result = exporter.export()
            report = read_report(result.path)
            self.assertFalse(result.partial)
            self.assertEqual(report["modules"]["runtime"]["data"]["state"], "game_not_configured")
            profile = report["modules"]["application"]["data"]["build_profile"]
            self.assertFalse(profile["default_recording_enabled"])
            self.assertEqual(report["scope"]["detailed_combat_events"], "not_included")
            self.assertFalse((exporter.app_dir / "exports/对局诊断").exists())

    def test_broken_unity_zip_and_good_zip_are_distinguished(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exporter, game = fixture(root)
            library = game.parent / "BepInEx/unity-libs/6000.3.16.zip"
            library.parent.mkdir()
            library.write_bytes(b"truncated ZIP")
            bad = read_report(exporter.export().path)
            self.assertIn("unity_base_zip_invalid", [finding["code"] for finding in bad["findings"]])
            with zipfile.ZipFile(library, "w") as archive:
                archive.writestr("UnityEngine.CoreModule.dll", b"fixture")
            good = read_report(exporter.export().path)
            self.assertNotIn("unity_base_zip_invalid", [finding["code"] for finding in good["findings"]])
            self.assertEqual(good["modules"]["runtime"]["data"]["unity_library_caches"][0]["zip_status"], "valid")

    def test_unreadable_runtime_manifest_keeps_mods_logs_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exporter, _game = fixture(Path(temporary))
            (exporter.resource_dir / "assets/lc2_runtime_manifest.json").write_text("broken JSON", encoding="utf-8")
            result = exporter.export({"combat": {"connection_state": "disconnected"}})
            report = read_report(result.path)
            self.assertTrue(result.partial)
            self.assertEqual(report["modules"]["runtime"]["status"], "not_collected")
            self.assertEqual(report["modules"]["mods"]["status"], "collected")
            self.assertEqual(report["modules"]["logs"]["status"], "collected")
            self.assertEqual(report["live_snapshot"]["combat"]["connection_state"], "disconnected")

    def test_missing_bundled_source_is_not_public_core(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exporter, _game = fixture(Path(temporary), bundled=True)
            report = read_report(exporter.export().path)
            mods = report["modules"]["mods"]["data"]
            self.assertEqual(mods["package_kind"], "bundled")
            self.assertEqual(mods["mods"][0]["source_state"], "missing_or_different")
            self.assertEqual(mods["mods"][0]["source_files"][0]["status"], "missing")

    def test_report_retains_failure_identity_while_redacting_personal_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exporter, game = fixture(Path(temporary))
            log = game.parent / "BepInEx/LogOutput.log"
            log.write_text('player_name="Alice" token="abc def"\nEnd of Central Directory: 6000.3.16.zip\nAlice failed\n', encoding="utf-8")
            exporter.record_event("mod_install_failed", mod_id="fixture-plugin", code="source_member_missing", path="panel.dll", token="top secret")
            result = exporter.export({"player_name": "Alice", "error_path": str(game.parent / "BepInEx/unity-libs/6000.3.16.zip")})
            with zipfile.ZipFile(result.path) as archive:
                text = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist())
                self.assertNotIn("abc def", text)
                self.assertNotIn("top secret", text)
                self.assertNotIn("Alice", text)
                self.assertNotIn(str(game.parent), text)
                self.assertIn("6000.3.16.zip", text)
                self.assertIn("source_member_missing", text)
                self.assertIn("panel.dll", text)
                report = json.loads(archive.read("report.json"))
                self.assertEqual(report["live_snapshot"]["player_name"], "<player-1>")
                for line in archive.read("logs/toolbox-operations.jsonl").decode("utf-8").splitlines():
                    json.loads(line)

    def test_time_budget_produces_explicit_partial_report_not_false_green(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exporter, _game = fixture(Path(temporary))
            exporter.seconds = 0
            result = exporter.export()
            self.assertTrue(result.partial)
            report = read_report(result.path)
            self.assertEqual(report["modules"]["runtime"]["status"], "not_collected")
            self.assertEqual(report["modules"]["runtime"]["reason"], "time_limit")

    def test_archive_manifest_matches_delivered_bytes_and_exports_do_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exporter, _game = fixture(Path(temporary), game_present=False)
            first, second = exporter.export(), exporter.export()
            self.assertNotEqual(first.path, second.path)
            for result in (first, second):
                with zipfile.ZipFile(result.path) as archive:
                    manifest = json.loads(archive.read("manifest.json"))
                    self.assertEqual(set(archive.namelist()), {"manifest.json", *(row["path"] for row in manifest["files"])})
                    for row in manifest["files"]:
                        data = archive.read(row["path"])
                        self.assertEqual(len(data), row["bytes"])
                        self.assertEqual(hashlib.sha256(data).hexdigest().upper(), row["sha256"])

    def test_plain_redaction_preserves_valid_json_and_windows_relative_paths(self) -> None:
        redactor = DiagnosticRedactor({Path(r"C:\Users\Alice\Toolbox"): "<toolbox>"})
        original = {"error": r"C:\Users\Alice\Toolbox\_internal\sample.dll", "token": "secret with spaces"}
        cleaned = redactor.text(json.dumps(original))
        parsed = json.loads(cleaned)
        self.assertEqual(parsed["token"], "<redacted>")
        self.assertIn("sample.dll", parsed["error"])
        self.assertNotIn("Alice", cleaned)


if __name__ == "__main__":
    unittest.main()
