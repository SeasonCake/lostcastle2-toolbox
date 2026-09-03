from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "build-public.ps1"
PUBLIC_README = PROJECT_ROOT / "package_assets" / "public-core.README.txt"
PUBLIC_MOD_CATALOG = PROJECT_ROOT / "assets" / "mod_catalog.public.json"
PUBLIC_COMMUNITY_CATALOG = (
    PROJECT_ROOT / "assets" / "community_mod_catalog.public.json"
)
PUBLIC_RUNTIME_MANIFEST = (
    PROJECT_ROOT / "assets" / "lc2_public_runtime_manifest.json"
)
PUBLIC_RUNTIME_ROOT = PROJECT_ROOT / "third_party" / "lc2_public_runtime"

PUBLIC_MOD_CATALOG_SHA256 = (
    "879388326B33DCCE722DCC4E4FD76802DC5628787713ED51D6EAA0999E12BE0C"
)
PUBLIC_COMMUNITY_CATALOG_SHA256 = (
    "747438843AA01B1E1B5D8A1260D9FB31C5B5FBE07A7B57386B40BFE2DE0B9C6A"
)
PUBLIC_RUNTIME_MANIFEST_SHA256 = (
    "5265F0D56DA5CF6979BA937AE3FD683A2277B69648D0821C91240AA3CF1549BB"
)
OFFICIAL_RUNTIME_SHA256 = (
    "2A7CBF74D26ABE4765C3E662DB1721B923BAC39849EBFEF2CA5DC7DE7E2D9B7F"
)
BRIDGE_SHA256 = (
    "190B8B4A8C661C73A32ADF15DF56487E57473E591BFA25520D172A7E188E7DED"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


class PublicBuildTests(unittest.TestCase):
    def test_public_build_uses_isolated_roots_and_an_explicit_allowlist(self) -> None:
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("失落城堡2工具箱1.7.4-public-core", script)
        self.assertIn("$publicBuildParent = Join-Path $projectRoot 'build'", script)
        self.assertIn(
            "$publicBuildRoot = Join-Path $publicBuildParent 'public-core'", script
        )
        self.assertIn("$publicDistParent = Join-Path $projectRoot 'dist'", script)
        self.assertIn(
            "$publicDistRoot = Join-Path $publicDistParent 'public-core'", script
        )
        self.assertIn("package\\public-core", script)
        self.assertNotIn("& .\\build.ps1", script)
        self.assertNotIn("Invoke-Expression", script)

        arguments = script.split("$pyInstallerArguments = @(", 1)[1].split(
            "Invoke-PythonChecked $pyInstallerArguments", 1
        )[0]
        self.assertIn("$publicStageAssets 'mod_catalog.json'", arguments)
        self.assertIn("$publicStageAssets 'community_mod_catalog.json'", arguments)
        self.assertIn("$publicStageAssets 'lc2_runtime_manifest.json'", arguments)
        self.assertIn(
            '"$publicRuntimeSource;third_party/lc2_runtime"', arguments
        )
        self.assertIn('"$sevenZipSource;third_party/7zip"', arguments)
        self.assertNotIn("community_mods", arguments)
        self.assertNotIn("LC2GoldFree.dll", arguments)
        self.assertNotIn("LostCastle2SoulStoneTrainer", arguments)

        self.assertIn(
            "PUBLIC_CORE_THIRD_PARTY_NOTICES.md", script
        )
        self.assertIn("Get-ForbiddenPayloadHashes", script)
        self.assertIn("--self-test", script)
        self.assertIn("FileVersion", script)
        self.assertIn("Fresh config directory is not empty", script)
        self.assertIn("Public distribution package must not contain exports", script)

    def test_public_readme_states_the_distribution_and_data_boundaries(self) -> None:
        text = PUBLIC_README.read_text(encoding="utf-8")
        for expected in (
            "public-core",
            "不包含灵魂石修改器",
            "金币编辑器 DLL",
            "不包含任何社区 MOD",
            "用户自行提供原包",
            "实时估算",
            "官方结算",
            OFFICIAL_RUNTIME_SHA256,
            BRIDGE_SHA256,
            "THIRD_PARTY_NOTICES.md",
        ):
            self.assertIn(expected, text)

    def test_frozen_public_manifests_are_nonbundled_and_official(self) -> None:
        self.assertEqual(sha256(PUBLIC_MOD_CATALOG), PUBLIC_MOD_CATALOG_SHA256)
        self.assertEqual(
            sha256(PUBLIC_COMMUNITY_CATALOG), PUBLIC_COMMUNITY_CATALOG_SHA256
        )
        self.assertEqual(
            sha256(PUBLIC_RUNTIME_MANIFEST), PUBLIC_RUNTIME_MANIFEST_SHA256
        )

        catalogs = (
            (PUBLIC_MOD_CATALOG, 2),
            (PUBLIC_COMMUNITY_CATALOG, 60),
        )
        for path, expected_count in catalogs:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 2)
            self.assertEqual(len(payload["entries"]), expected_count)
            for entry in payload["entries"]:
                operation = entry["operation"]
                self.assertIs(operation["bundled"], False)
                self.assertNotIn("bundle_dir", operation)
                self.assertEqual(
                    entry["integrity_policy"]["redistribution_status"],
                    "public_core_user_supplied_required",
                )
                self.assertIn(
                    "source_redistribution_status", entry["integrity_policy"]
                )
                self.assertNotIn(
                    "third_party/", json.dumps(entry, ensure_ascii=False).lower()
                )

        runtime = json.loads(PUBLIC_RUNTIME_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(runtime["source_identity"]["kind"], "official_bepinex_build")
        self.assertEqual(runtime["source_identity"]["build"], 785)
        self.assertEqual(runtime["source_identity"]["sha256"], OFFICIAL_RUNTIME_SHA256)
        self.assertEqual(runtime["runtime_archive"]["sha256"], OFFICIAL_RUNTIME_SHA256)
        self.assertEqual(runtime["runtime_archive"]["size_bytes"], 34_335_572)
        self.assertEqual(runtime["runtime_file_count"], 228)
        self.assertEqual(len(runtime["runtime_files"]), 228)
        self.assertEqual(runtime["runtime_uncompressed_bytes"], 75_665_788)
        self.assertEqual(runtime["build_profile"], "distribution")
        self.assertEqual(runtime["bridge"]["sha256"], BRIDGE_SHA256)
        self.assertEqual(runtime["bridge"]["size_bytes"], 102_400)
        self.assertIs(runtime["bridge"]["diagnostics_enabled"], False)
        lowered = [spec["path"].lower() for spec in runtime["runtime_files"]]
        for forbidden_prefix in (
            "bepinex/plugins/",
            "bepinex/cache/",
            "bepinex/interop/",
            "bepinex/unity-libs/",
            "bepinex/config/",
        ):
            self.assertFalse(
                any(path.startswith(forbidden_prefix) for path in lowered),
                forbidden_prefix,
            )

    def test_validate_only_runs_when_ignored_binary_inputs_are_present(self) -> None:
        runtime_archive = PUBLIC_RUNTIME_ROOT / "bepinex-runtime.zip"
        bridge = PUBLIC_RUNTIME_ROOT / "LC2CombatBridge.dll"
        if not runtime_archive.is_file() or not bridge.is_file():
            self.skipTest("ignored public runtime binaries are absent in this checkout")
        self.assertEqual(runtime_archive.stat().st_size, 34_335_572)
        self.assertEqual(sha256(runtime_archive), OFFICIAL_RUNTIME_SHA256)
        self.assertEqual(bridge.stat().st_size, 102_400)
        self.assertEqual(sha256(bridge), BRIDGE_SHA256)

        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is unavailable")
        completed = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(BUILD_SCRIPT),
                "-ValidateOnly",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )
        self.assertIn('"status": "validated"', completed.stdout)
        self.assertIn('"runtime_members": 228', completed.stdout)


if __name__ == "__main__":
    unittest.main()
