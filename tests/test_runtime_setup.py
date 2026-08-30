from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from toolbox.runtime_setup import (
    RuntimeSetupConflict,
    RuntimeSetupError,
    RuntimeSetupGameRunning,
    RuntimeSetupManager,
    console_is_enabled,
    disable_console,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest().upper()


def runtime_fixture(root: Path) -> tuple[Path, Path, dict[str, bytes]]:
    bundle = root / "bundle"
    bundle.mkdir()
    files = {
        ".doorstop_version": b"4.5.0",
        "doorstop_config.ini": b"[General]\nenabled = true\n",
        "BepInEx/config/BepInEx.cfg": (
            b"[Logging.Console]\nEnabled = false\n\n"
            b"[Logging.Disk]\nEnabled = true\n"
        ),
        "BepInEx/core/BepInEx.Core.dll": b"core",
        "BepInEx/core/BepInEx.Unity.IL2CPP.dll": b"il2cpp",
        "BepInEx/unity-libs/6000.3.16.zip": b"unity libs",
        "dotnet/coreclr.dll": b"core clr",
        "winhttp.dll": b"doorstop",
    }
    archive = bundle / "bepinex-runtime.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for relative, content in files.items():
            output.writestr(relative, content)
    bridge = b"read-only bridge"
    (bundle / "LC2CombatBridge.dll").write_bytes(bridge)
    manifest = {
        "schema_version": 1,
        "runtime_archive": {
            "filename": archive.name,
            "size_bytes": archive.stat().st_size,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest().upper(),
        },
        "runtime_files": [
            {"path": path, "size_bytes": len(content), "sha256": sha256(content)}
            for path, content in files.items()
        ],
        "required_paths": list(files),
        "bridge": {
            "filename": "LC2CombatBridge.dll",
            "target": "BepInEx/plugins/LC2CombatBridge/LC2CombatBridge.dll",
            "size_bytes": len(bridge),
            "sha256": sha256(bridge),
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, bundle, files


class RuntimeSetupTests(unittest.TestCase):
    def test_fresh_game_gets_only_runtime_and_read_only_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest, bundle, _files = runtime_fixture(root)
            game = root / "game"
            game.mkdir()
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            unrelated = game / "BepInEx" / "plugins" / "existing" / "keep.dll"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_bytes(b"keep")
            manager = RuntimeSetupManager(
                manifest,
                bundle,
                lambda: game_exe,
                backup_root=root / "backups",
            )

            self.assertEqual(manager.status().state, "missing")
            manager.verify_bundle()
            self.assertTrue(manager.install().ready)
            self.assertTrue(manager.status().ready)
            self.assertTrue(unrelated.is_file())
            self.assertTrue(
                (game / "BepInEx/plugins/LC2CombatBridge/LC2CombatBridge.dll").is_file()
            )
            self.assertFalse(
                console_is_enabled(
                    (game / "BepInEx/config/BepInEx.cfg").read_text(encoding="utf-8")
                )
            )
            plugin_files = {
                path.relative_to(game / "BepInEx/plugins").as_posix()
                for path in (game / "BepInEx/plugins").rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                plugin_files,
                {"existing/keep.dll", "LC2CombatBridge/LC2CombatBridge.dll"},
            )
            self.assertTrue(manager.install().ready)

    def test_existing_config_is_backed_up_and_only_console_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest, bundle, _files = runtime_fixture(root)
            game = root / "game"
            game.mkdir()
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            config = game / "BepInEx/config/BepInEx.cfg"
            config.parent.mkdir(parents=True)
            config.write_text(
                "[Logging.Console]\nEnabled = true\n\n"
                "[Logging.Disk]\nEnabled = true\nCustom = keep\n",
                encoding="utf-8",
            )
            backups = root / "backups"
            manager = RuntimeSetupManager(
                manifest, bundle, lambda: game_exe, backup_root=backups
            )

            manager.install()

            updated = config.read_text(encoding="utf-8")
            self.assertFalse(console_is_enabled(updated))
            self.assertIn("[Logging.Disk]\nEnabled = true\nCustom = keep", updated)
            self.assertEqual(len(list(backups.glob("BepInEx.cfg.*.bak"))), 1)

    def test_conflicting_core_fails_before_writing_any_runtime_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest, bundle, _files = runtime_fixture(root)
            game = root / "game"
            game.mkdir()
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            conflict = game / "BepInEx/core/BepInEx.Core.dll"
            conflict.parent.mkdir(parents=True)
            conflict.write_bytes(b"different")
            manager = RuntimeSetupManager(manifest, bundle, lambda: game_exe)

            with self.assertRaises(RuntimeSetupConflict):
                manager.install()

            self.assertEqual(conflict.read_bytes(), b"different")
            self.assertFalse((game / "winhttp.dll").exists())
            self.assertFalse(
                (game / "BepInEx/plugins/LC2CombatBridge/LC2CombatBridge.dll").exists()
            )

    def test_running_game_blocks_setup_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest, bundle, _files = runtime_fixture(root)
            game = root / "game"
            game.mkdir()
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            manager = RuntimeSetupManager(
                manifest,
                bundle,
                lambda: game_exe,
                game_running_provider=lambda path: path == game_exe.resolve(),
            )

            with self.assertRaises(RuntimeSetupGameRunning):
                manager.install()
            self.assertEqual(list(game.iterdir()), [game_exe])

    def test_console_edit_does_not_change_disk_logging_section(self) -> None:
        original = (
            "[Logging.Console]\nEnabled = true\n\n"
            "[Logging.Disk]\nEnabled = true\n"
        )
        updated = disable_console(original)
        self.assertFalse(console_is_enabled(updated))
        self.assertIn("[Logging.Disk]\nEnabled = true", updated)

    def test_real_bundle_contains_no_plugins_cache_or_debug_probe(self) -> None:
        manifest = json.loads(
            (PROJECT_ROOT / "assets/lc2_runtime_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        paths = [entry["path"] for entry in manifest["runtime_files"]]
        folded = [path.casefold() for path in paths]
        self.assertFalse(any(path.startswith("bepinex/plugins/") for path in folded))
        self.assertFalse(any(path.startswith("bepinex/cache/") for path in folded))
        self.assertFalse(any("damageprobe" in path or "maxplayers" in path for path in folded))
        self.assertEqual(
            manifest["bridge"]["sha256"],
            "3229359A7D901CEBCD523109261A034704CA06B0E3EAD0829ADC5B19ED976D8D",
        )
        self.assertEqual(manifest["bridge"]["size_bytes"], 52736)
        self.assertIn("LC2CombatBridge 0.4.12", manifest["runtime_version"])


if __name__ == "__main__":
    unittest.main()
