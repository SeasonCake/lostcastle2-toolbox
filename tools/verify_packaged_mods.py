from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from toolbox.mod_inspector import ModPackageInspector
from toolbox.mod_manager import ModCatalog, ModManager
from toolbox.user_mod_registry import UserModRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--import-source", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = args.package.resolve()
    internal = package / "_internal"
    catalog = ModCatalog.from_file(internal / "assets" / "community_mod_catalog.json")
    inspector = ModPackageInspector(internal / "third_party" / "7zip" / "7z.exe")
    draft = inspector.inspect(args.import_source)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        game = root / "game"
        plugins = game / "BepInEx" / "plugins"
        plugins.mkdir(parents=True)
        game_exe = game / "LostCastle2.exe"
        game_exe.write_bytes(b"game")
        sibling = plugins / "unrelated" / "keep.dll"
        sibling.parent.mkdir()
        sibling.write_bytes(b"keep")
        manager = ModManager(
            catalog,
            root / "managed",
            internal / "third_party",
            game_exe_provider=lambda: game_exe,
        )
        for descriptor in catalog.entries:
            manager.install(descriptor.mod_id)
            if not manager.status(descriptor.mod_id).installed:
                raise RuntimeError(f"Packaged MOD status failed: {descriptor.mod_id}")
            manager.uninstall(descriptor.mod_id)
            if manager.status(descriptor.mod_id).state != "not_installed":
                raise RuntimeError(f"Packaged MOD uninstall failed: {descriptor.mod_id}")
            if not sibling.is_file():
                raise RuntimeError("Packaged MOD uninstall removed an unrelated plugin.")

        registry = UserModRegistry(root / "user-registry", inspector)
        registered = registry.register(
            draft,
            {
                "name": draft.name,
                "version": draft.version,
                "author": draft.author,
                "summary": draft.summary,
                "usage_hint": draft.usage_hint,
            },
            reserved_ids={entry.mod_id for entry in catalog.entries},
        )
        user_catalog, overrides = registry.load()
        if user_catalog is None or registered.descriptor.mod_id not in overrides:
            raise RuntimeError("Packaged archive import did not persist its registry.")

    result = {
        "community_entries": len(catalog.entries),
        "community_install_uninstall": "passed",
        "unrelated_plugin_retained": True,
        "import_source": args.import_source.name,
        "import_payload_files": len(draft.payload),
        "import_name": draft.name,
        "import_version": draft.version,
        "import_author": draft.author,
        "import_registry": "passed",
    }
    sys.stdout.buffer.write(
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
