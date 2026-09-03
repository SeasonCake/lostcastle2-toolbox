from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from toolbox.runtime_setup import (
    RuntimeSetupConflict,
    RuntimeSetupManager,
    console_is_enabled,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify packaged clean-game BepInEx/HUD initialization."
    )
    parser.add_argument("--package", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    package = parse_args().package.resolve()
    internal = package / "_internal"
    manifest = internal / "assets" / "lc2_runtime_manifest.json"
    profile_path = internal / "assets" / "build_profile.json"
    bundle = internal / "third_party" / "lc2_runtime"
    if not manifest.is_file() or not profile_path.is_file() or not bundle.is_dir():
        raise RuntimeError("Packaged runtime resources are missing.")
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
    profile_id = profile_payload.get("profile_id")
    expected_diagnostics = profile_id == "diagnostic"
    profile_fields = (
        profile_payload.get("combat_diagnostics_available"),
        profile_payload.get("bridge_diagnostics_enabled"),
        profile_payload.get("default_recording_enabled"),
    )
    if (
        profile_payload.get("schema_version") != 1
        or profile_id not in {"diagnostic", "distribution"}
        or any(not isinstance(value, bool) for value in profile_fields)
        or profile_fields
        != (expected_diagnostics, expected_diagnostics, expected_diagnostics)
        or manifest_payload.get("build_profile") != profile_id
        or (manifest_payload.get("bridge") or {}).get("diagnostics_enabled")
        is not expected_diagnostics
    ):
        raise RuntimeError("Packaged build profile is missing or inconsistent.")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        game = root / "fresh-game"
        game.mkdir()
        game_exe = game / "LostCastle2.exe"
        game_exe.write_bytes(b"fixture game executable")
        unrelated = game / "BepInEx" / "plugins" / "unrelated" / "keep.dll"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b"keep")
        manager = RuntimeSetupManager(
            manifest,
            bundle,
            lambda: game_exe,
            backup_root=root / "backups",
        )
        before = manager.status().state
        manager.verify_bundle()
        installed = manager.install()
        repeated = manager.install()
        config = game / "BepInEx" / "config" / "BepInEx.cfg"
        plugin_files = sorted(
            path.relative_to(game / "BepInEx" / "plugins").as_posix()
            for path in (game / "BepInEx" / "plugins").rglob("*")
            if path.is_file()
        )
        expected_plugins = [
            "LC2CombatBridge/LC2CombatBridge.dll",
            "unrelated/keep.dll",
        ]
        if plugin_files != expected_plugins:
            raise RuntimeError(f"Unexpected packaged setup plugins: {plugin_files}")
        if console_is_enabled(config.read_text(encoding="utf-8-sig")):
            raise RuntimeError("Packaged setup left the BepInEx console enabled.")
        if not unrelated.is_file() or not installed.ready or not repeated.ready:
            raise RuntimeError("Packaged setup did not reach an idempotent ready state.")

        conflict_game = root / "conflict-game"
        conflict_game.mkdir()
        conflict_exe = conflict_game / "LostCastle2.exe"
        conflict_exe.write_bytes(b"fixture game executable")
        conflict_core = conflict_game / "BepInEx" / "core" / "BepInEx.Core.dll"
        conflict_core.parent.mkdir(parents=True)
        conflict_core.write_bytes(b"different existing runtime")
        conflict_manager = RuntimeSetupManager(
            manifest, bundle, lambda: conflict_exe
        )
        conflict_blocked = False
        try:
            conflict_manager.install()
        except RuntimeSetupConflict:
            conflict_blocked = True
        if not conflict_blocked or (conflict_game / "winhttp.dll").exists():
            raise RuntimeError("Conflicting runtime did not fail before writes.")

        report = {
            "build_profile": profile_id,
            "combat_diagnostics_available": expected_diagnostics,
            "runtime_version": manifest_payload["runtime_version"],
            "runtime_archive_sha256": manifest_payload["runtime_archive"]["sha256"],
            "runtime_files": manifest_payload["runtime_file_count"],
            "fresh_status_before": before,
            "fresh_install": installed.state,
            "repeated_install": repeated.state,
            "console_enabled": False,
            "plugins_after_setup": plugin_files,
            "community_mods_auto_enabled": False,
            "conflicting_core_blocked_before_write": conflict_blocked,
        }
        sys.stdout.buffer.write(
            (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
