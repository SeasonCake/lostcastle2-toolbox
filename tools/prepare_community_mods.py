from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from toolbox.mod_inspector import ModPackageInspector, normalize_member_path


ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the curated LC2 community MOD bundle.")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--definition", required=True, type=Path)
    parser.add_argument("--seven-zip", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def clean_generated_root(output_root: Path) -> None:
    resolved = output_root.resolve()
    expected_parent = (PROJECT_ROOT / "third_party").resolve()
    if resolved.name != "community_mods" or resolved.parent != expected_parent:
        raise ValueError("Refusing to replace an unexpected community MOD output root.")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def require_text(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Community MOD definition field {key!r} must be non-empty.")
    return value.strip()


def selected_payload(
    raw: dict[str, object], payload: dict[str, bytes]
) -> dict[str, bytes]:
    include = raw.get("include")
    if include is None:
        return dict(payload)
    if not isinstance(include, list) or not include:
        raise ValueError("Community MOD include must be a non-empty array.")
    by_path = {path.casefold(): (path, content) for path, content in payload.items()}
    selected: dict[str, bytes] = {}
    for item in include:
        if isinstance(item, str):
            source_path = normalize_member_path(item)
            target_path = PurePosixPath(source_path).name
            matched = by_path.get(source_path.casefold())
        elif isinstance(item, dict):
            target_path = normalize_member_path(require_text(item, "target"))
            source_hash = item.get("sha256")
            if source_hash is not None:
                if (
                    not isinstance(source_hash, str)
                    or not re.fullmatch(r"[0-9A-Fa-f]{64}", source_hash.strip())
                ):
                    raise ValueError("Community MOD include sha256 must be 64 hex digits.")
                matches = [
                    (path, content)
                    for path, content in payload.items()
                    if hashlib.sha256(content).hexdigest().casefold()
                    == source_hash.strip().casefold()
                ]
                if len(matches) != 1:
                    raise ValueError(
                        "Community MOD include sha256 must select exactly one payload member."
                    )
                matched = matches[0]
                source_path = matched[0]
            else:
                source_path = normalize_member_path(require_text(item, "source"))
                matched = by_path.get(source_path.casefold())
        else:
            raise ValueError("Community MOD include entries must be paths or mappings.")
        if matched is None:
            raise ValueError(f"Prepared payload member not found: {source_path}")
        if target_path.casefold() in {path.casefold() for path in selected}:
            raise ValueError(f"Duplicate prepared target path: {target_path}")
        selected[target_path] = matched[1]
    return selected


def main() -> int:
    args = parse_args()
    definition = json.loads(args.definition.read_text(encoding="utf-8"))
    if not isinstance(definition, dict) or definition.get("schema_version") != 1:
        raise ValueError("Unsupported community MOD source definition.")
    raw_entries = definition.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ValueError("Community MOD source definition has no entries.")

    inspector = ModPackageInspector(args.seven_zip)
    clean_generated_root(args.output_root)
    cache: dict[Path, tuple[object, dict[str, bytes]]] = {}
    catalog_entries: list[dict[str, object]] = []
    report_entries: list[dict[str, object]] = []
    ids: set[str] = set()

    ranked_entries: list[tuple[int, int, dict[str, object]]] = []
    for source_index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            raise ValueError("Community MOD source entry must be an object.")
        sort_priority = raw.get("sort_priority", 500)
        if type(sort_priority) is not int or not 0 <= sort_priority <= 999:
            raise ValueError("Community MOD sort_priority must be an integer from 0 to 999.")
        ranked_entries.append((sort_priority, source_index, raw))

    for _sort_priority, _source_index, raw in sorted(ranked_entries):
        mod_id = require_text(raw, "id")
        if not ID_PATTERN.fullmatch(mod_id) or mod_id in ids:
            raise ValueError(f"Invalid or duplicate community MOD id: {mod_id}")
        ids.add(mod_id)
        source_name = require_text(raw, "source")
        source = (args.source_root / source_name).resolve()
        try:
            source.relative_to(args.source_root.resolve())
        except ValueError as exception:
            raise ValueError("Community MOD source escaped source root.") from exception
        if source not in cache:
            draft = inspector.inspect(source)
            cache[source] = (draft, inspector.read_payload(draft))
        draft, payload = cache[source]
        files = selected_payload(raw, payload)
        primary = normalize_member_path(require_text(raw, "primary"))
        if primary.casefold() not in {path.casefold() for path in files}:
            raise ValueError(f"Primary payload is missing for {mod_id}: {primary}")

        destination = (args.output_root / mod_id).resolve()
        destination.mkdir(parents=True)
        specs: list[dict[str, object]] = []
        primary_spec: dict[str, object] | None = None
        for relative, content in sorted(files.items(), key=lambda item: item[0].casefold()):
            target = destination.joinpath(*PurePosixPath(relative).parts).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exception:
                raise ValueError("Prepared community MOD target escaped its directory.") from exception
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            spec = {
                "path": relative,
                "sha256": hashlib.sha256(content).hexdigest().upper(),
                "size_bytes": len(content),
            }
            specs.append(spec)
            if relative.casefold() == primary.casefold():
                primary_spec = spec
        if primary_spec is None:
            raise ValueError(f"Unable to resolve primary payload for {mod_id}.")

        hotkeys = raw.get("hotkeys", [])
        if not isinstance(hotkeys, list) or not all(
            isinstance(item, str) and item.strip() for item in hotkeys
        ):
            raise ValueError(f"Invalid hotkeys for {mod_id}.")
        panel_hotkey = raw.get("panel_hotkey")
        if panel_hotkey is not None and (
            not isinstance(panel_hotkey, str) or not panel_hotkey.strip()
        ):
            raise ValueError(f"Invalid panel_hotkey for {mod_id}.")
        provides = raw.get("provides")
        if provides is None:
            provides = [
                PurePosixPath(path).name.casefold()
                for path in files
                if path.casefold().endswith(".dll")
            ]
        if not isinstance(provides, list) or not all(
            isinstance(item, str) and item.strip() for item in provides
        ):
            raise ValueError(f"Invalid provides list for {mod_id}.")
        display = {
            "name": require_text(raw, "name"),
            "version": require_text(raw, "version"),
            "author": require_text(raw, "author"),
            "summary": require_text(raw, "summary"),
            "usage_hint": require_text(raw, "usage_hint"),
        }
        operation = {
            "kind": "bepinex_plugin",
            "expected_filename": PurePosixPath(primary).name,
            "bundled": True,
            "bundle_dir": f"community_mods/{mod_id}",
            "files": specs,
            "provides": list(dict.fromkeys(item.strip() for item in provides)),
            "hotkeys": list(dict.fromkeys(item.strip() for item in hotkeys)),
        }
        if panel_hotkey is not None:
            operation["panel_hotkey"] = panel_hotkey.strip()
        catalog_entries.append(
            {
                "id": mod_id,
                "display": display,
                "operation": operation,
                "integrity_policy": {
                    "version_note": f"curated community bundle {display['version']}",
                    "author_source": require_text(raw, "author_source"),
                    "author_channel": "local community package",
                    "sha256": primary_spec["sha256"],
                    "size_bytes": primary_spec["size_bytes"],
                    "signature_status": "not_assessed",
                    "risk_level": "high",
                    "capabilities": ["gameplay modification"],
                    "redistribution_status": "maintainer_selected_for_local_bundle_2026-08-28",
                },
            }
        )
        report_entries.append(
            {
                "id": mod_id,
                "source": source_name,
                "source_size_bytes": source.stat().st_size if source.is_file() else None,
                "source_sha256": file_sha256(source) if source.is_file() else None,
                "primary": primary,
                "selection_mode": (
                    "explicit_include" if raw.get("include") is not None else "inspector_default"
                ),
                "payload_files": len(specs),
                "payload_bytes": sum(int(spec["size_bytes"]) for spec in specs),
                "warnings": list(getattr(draft, "warnings")),
            }
        )

    catalog = {"schema_version": 2, "entries": catalog_entries}
    args.catalog.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = {
        "schema_version": 1,
        "entries": report_entries,
        "total_entries": len(report_entries),
        "total_payload_files": sum(int(entry["payload_files"]) for entry in report_entries),
        "total_payload_bytes": sum(int(entry["payload_bytes"]) for entry in report_entries),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sys.stdout.buffer.write(
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
