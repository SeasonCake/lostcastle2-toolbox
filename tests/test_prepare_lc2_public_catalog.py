from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from toolbox.mod_manager import ModCatalog, ModIntegrityError, ModManager
from tools.prepare_lc2_public_catalog import (
    PUBLIC_REDISTRIBUTION_STATUS,
    PublicCatalogError,
    prepare_catalog,
    public_catalog_from_payload,
    render_catalog,
    validate_public_catalog,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PublicCatalogTests(unittest.TestCase):
    def test_tracked_public_catalogs_are_exact_deterministic_derivatives(self) -> None:
        pairs = (
            ("mod_catalog.json", "mod_catalog.public.json", 2),
            ("community_mod_catalog.json", "community_mod_catalog.public.json", 60),
        )
        for source_name, public_name, expected_count in pairs:
            with self.subTest(public_name=public_name):
                source_path = PROJECT_ROOT / "assets" / source_name
                public_path = PROJECT_ROOT / "assets" / public_name
                source = json.loads(source_path.read_text(encoding="utf-8"))
                public = json.loads(public_path.read_text(encoding="utf-8"))

                self.assertEqual(public_path.read_text(encoding="utf-8"), prepare_catalog(source_path))
                self.assertEqual(len(public["entries"]), expected_count)
                self.assertEqual(
                    [entry["id"] for entry in public["entries"]],
                    [entry["id"] for entry in source["entries"]],
                )
                validate_public_catalog(public)
                self.assertEqual(len(ModCatalog.from_file(public_path).entries), expected_count)

                for source_entry, public_entry in zip(
                    source["entries"], public["entries"], strict=True
                ):
                    self.assertEqual(public_entry["display"], source_entry["display"])
                    source_operation = copy.deepcopy(source_entry["operation"])
                    source_operation["bundled"] = False
                    source_operation.pop("bundle_dir", None)
                    self.assertEqual(public_entry["operation"], source_operation)
                    source_policy = source_entry["integrity_policy"]
                    public_policy = public_entry["integrity_policy"]
                    self.assertEqual(
                        public_policy["source_redistribution_status"],
                        source_policy["redistribution_status"],
                    )
                    self.assertEqual(
                        public_policy["redistribution_status"],
                        PUBLIC_REDISTRIBUTION_STATUS,
                    )
                    for key, value in source_policy.items():
                        if key != "redistribution_status":
                            self.assertEqual(public_policy[key], value)

    def test_generation_does_not_require_local_payload_files(self) -> None:
        content = b"fixture"
        digest = hashlib.sha256(content).hexdigest().upper()
        payload = {
            "schema_version": 2,
            "entries": [
                {
                    "id": "fixture-plugin",
                    "display": {
                        "name": "Fixture",
                        "version": "1.0",
                        "author": "Author",
                        "summary": "Purpose",
                    },
                    "operation": {
                        "kind": "bepinex_plugin",
                        "expected_filename": "fixture.dll",
                        "bundled": True,
                        "bundle_dir": "community_mods/fixture-plugin",
                        "files": [
                            {
                                "path": "fixture.dll",
                                "sha256": digest,
                                "size_bytes": len(content),
                            }
                        ],
                        "superseded_files": [
                            {
                                "path": "fixture-v0.dll",
                                "sha256": digest,
                                "size_bytes": len(content),
                            }
                        ],
                        "hotkeys": ["F6"],
                    },
                    "integrity_policy": {
                        "version_note": "1.0",
                        "author_source": "source note",
                        "author_channel": "source channel",
                        "sha256": digest,
                        "size_bytes": len(content),
                        "signature_status": "not_assessed",
                        "risk_level": "high",
                        "capabilities": ["gameplay modification"],
                        "redistribution_status": "source_evidence_value",
                    },
                }
            ],
        }

        public = public_catalog_from_payload(payload)
        self.assertNotIn("bundle_dir", public["entries"][0]["operation"])
        self.assertFalse(public["entries"][0]["operation"]["bundled"])
        self.assertEqual(public["entries"][0]["operation"]["files"][0]["sha256"], digest)
        self.assertEqual(
            public["entries"][0]["operation"]["superseded_files"][0]["path"],
            "fixture-v0.dll",
        )
        self.assertEqual(render_catalog(public), render_catalog(public_catalog_from_payload(payload)))

    def test_public_validator_rejects_bundles_and_local_payload_paths(self) -> None:
        source = json.loads(
            (PROJECT_ROOT / "assets" / "mod_catalog.json").read_text(encoding="utf-8")
        )
        public = public_catalog_from_payload(source)
        bundled = copy.deepcopy(public)
        bundled["entries"][0]["operation"]["bundled"] = True
        with self.assertRaises(PublicCatalogError):
            validate_public_catalog(bundled)

        local_path = copy.deepcopy(public)
        local_path["entries"][0]["operation"]["source_path"] = "C:/private/tool.exe"
        with self.assertRaises(PublicCatalogError):
            validate_public_catalog(local_path)

        bundle_dir = copy.deepcopy(public)
        bundle_dir["entries"][0]["operation"]["bundle_dir"] = "community_mods/tool"
        with self.assertRaises(PublicCatalogError):
            validate_public_catalog(bundle_dir)

    def test_public_validator_rejects_unsafe_superseded_identities(self) -> None:
        source = json.loads(
            (PROJECT_ROOT / "assets" / "community_mod_catalog.json").read_text(
                encoding="utf-8"
            )
        )
        public = public_catalog_from_payload(source)
        entry = next(
            item for item in public["entries"] if item["id"] == "damage-meter"
        )
        for field, value in (
            ("path", "../legacy.dll"),
            ("path", "legacy//plugin.dll"),
            ("size_bytes", 0),
            ("sha256", "not-a-hash"),
        ):
            with self.subTest(field=field, value=value):
                invalid = copy.deepcopy(public)
                target = next(
                    item for item in invalid["entries"] if item["id"] == entry["id"]
                )
                target["operation"]["superseded_files"][0][field] = value
                with self.assertRaises(PublicCatalogError):
                    validate_public_catalog(invalid)

    def test_user_supplied_multifile_directory_installs_and_tamper_fails_closed(self) -> None:
        first = b"fixture primary"
        second = b"fixture dependency"
        first_hash = hashlib.sha256(first).hexdigest().upper()
        second_hash = hashlib.sha256(second).hexdigest().upper()
        payload = {
            "schema_version": 2,
            "entries": [
                {
                    "id": "fixture-plugin",
                    "display": {
                        "name": "Fixture",
                        "version": "1.0",
                        "author": "Author",
                        "summary": "Purpose",
                    },
                    "operation": {
                        "kind": "bepinex_plugin",
                        "expected_filename": "fixture.dll",
                        "bundled": False,
                        "files": [
                            {"path": "fixture.dll", "sha256": first_hash, "size_bytes": len(first)},
                            {"path": "libs/dependency.dll", "sha256": second_hash, "size_bytes": len(second)},
                        ],
                        "provides": ["fixture.dll", "dependency.dll"],
                        "hotkeys": [],
                    },
                    "integrity_policy": {
                        "version_note": "1.0",
                        "author_source": "source note",
                        "author_channel": "source channel",
                        "sha256": first_hash,
                        "size_bytes": len(first),
                        "signature_status": "not_assessed",
                        "risk_level": "high",
                        "capabilities": ["gameplay modification"],
                        "redistribution_status": PUBLIC_REDISTRIBUTION_STATUS,
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "unpacked"
            (source / "libs").mkdir(parents=True)
            (source / "fixture.dll").write_bytes(first)
            (source / "libs" / "dependency.dll").write_bytes(second)
            game = root / "game"
            (game / "BepInEx" / "plugins").mkdir(parents=True)
            game_exe = game / "LostCastle2.exe"
            game_exe.write_bytes(b"game")
            manager = ModManager(
                ModCatalog.from_payload(payload),
                root / "managed",
                root / "empty-bundled-root",
                game_exe_provider=lambda: game_exe,
            )

            target = manager.install("fixture-plugin", source)
            self.assertEqual(target.read_bytes(), first)
            self.assertTrue(manager.status("fixture-plugin").installed)
            self.assertTrue(manager.uninstall("fixture-plugin"))

            (source / "libs" / "dependency.dll").write_bytes(second + b"tampered")
            with self.assertRaises(ModIntegrityError):
                manager.install("fixture-plugin", source)
            self.assertEqual(manager.status("fixture-plugin").state, "not_installed")


if __name__ == "__main__":
    unittest.main()
