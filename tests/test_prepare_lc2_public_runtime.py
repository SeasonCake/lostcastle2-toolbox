from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.prepare_lc2_public_runtime import (
    BRIDGE_SHA256,
    OFFICIAL_SHA256,
    build_manifest,
    normalized_member,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_INPUT = (
    PROJECT_ROOT
    / "artifacts/public-release-inputs/bepinex-6.0.0-be.785-official"
    / "BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip"
)
BRIDGE_INPUT = (
    PROJECT_ROOT
    / "third_party/lc2_public_runtime/LC2CombatBridge.dll"
)


class PublicRuntimePreparationTests(unittest.TestCase):
    def test_tracked_manifest_is_exact_deterministic_official_derivative(self) -> None:
        if not OFFICIAL_INPUT.is_file() or not BRIDGE_INPUT.is_file():
            self.skipTest("ignored official input or local Bridge build is unavailable")
        expected = json.loads(
            (PROJECT_ROOT / "assets/lc2_public_runtime_manifest.json").read_text(
                encoding="utf-8"
            )
        )

        actual = build_manifest(OFFICIAL_INPUT, BRIDGE_INPUT)

        self.assertEqual(actual, expected)
        self.assertEqual(actual["source_identity"]["sha256"], OFFICIAL_SHA256)
        self.assertEqual(actual["runtime_archive"]["sha256"], OFFICIAL_SHA256)
        self.assertEqual(actual["bridge"]["sha256"], BRIDGE_SHA256)

    def test_wrong_bridge_and_unsafe_members_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wrong_bridge = Path(temp_dir) / "LC2CombatBridge.dll"
            wrong_bridge.write_bytes(b"not the public candidate")
            with self.assertRaisesRegex(ValueError, "Bridge public candidate"):
                build_manifest(OFFICIAL_INPUT, wrong_bridge)
        for value in ("../escape.dll", "/absolute.dll", "C:/drive.dll", "folder/"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalized_member(value)


if __name__ == "__main__":
    unittest.main()
