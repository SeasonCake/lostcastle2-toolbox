from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REDISTRIBUTION_STATUS = "public_core_user_supplied_required"
FORBIDDEN_LOCAL_KEYS = {
    "bundle_dir",
    "bundled_path",
    "local_path",
    "payload_path",
    "source_path",
    "source_root",
}


class PublicCatalogError(ValueError):
    """Raised when a public catalog would depend on a local bundled payload."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate payload-free Lost Castle 2 public MOD catalogs."
    )
    parser.add_argument(
        "--core-source",
        type=Path,
        default=PROJECT_ROOT / "assets" / "mod_catalog.json",
    )
    parser.add_argument(
        "--community-source",
        type=Path,
        default=PROJECT_ROOT / "assets" / "community_mod_catalog.json",
    )
    parser.add_argument(
        "--core-output",
        type=Path,
        default=PROJECT_ROOT / "assets" / "mod_catalog.public.json",
    )
    parser.add_argument(
        "--community-output",
        type=Path,
        default=PROJECT_ROOT / "assets" / "community_mod_catalog.public.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed outputs exactly match deterministic generation.",
    )
    return parser.parse_args()


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicCatalogError(f"{label} must be an object.")
    return value


def _required_entries(payload: Any) -> list[dict[str, Any]]:
    catalog = _required_mapping(payload, "catalog")
    if catalog.get("schema_version") != 2:
        raise PublicCatalogError("Public MOD catalogs require schema_version 2.")
    raw_entries = catalog.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise PublicCatalogError("Public MOD catalog entries must be non-empty.")
    return [_required_mapping(entry, "catalog entry") for entry in raw_entries]


def _validate_relative_identity(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PublicCatalogError(f"{label} must be a non-empty relative path.")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise PublicCatalogError(f"{label} must stay inside the selected source folder.")
    if ":" in path.parts[0]:
        raise PublicCatalogError(f"{label} must not contain a drive-qualified path.")


def _reject_local_path_fields(value: Any, label: str = "catalog") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in FORBIDDEN_LOCAL_KEYS:
                raise PublicCatalogError(f"{label} contains local payload field {key!r}.")
            _reject_local_path_fields(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_local_path_fields(child, f"{label}[{index}]")


def validate_public_catalog(payload: Any) -> None:
    entries = _required_entries(payload)
    _reject_local_path_fields(payload)
    for entry in entries:
        operation = _required_mapping(entry.get("operation"), "operation")
        policy = _required_mapping(entry.get("integrity_policy"), "integrity_policy")
        if operation.get("bundled") is not False:
            raise PublicCatalogError("Every public MOD operation must set bundled=false.")
        if policy.get("redistribution_status") != PUBLIC_REDISTRIBUTION_STATUS:
            raise PublicCatalogError(
                "Public MOD redistribution_status must require a user-supplied source."
            )
        source_status = policy.get("source_redistribution_status")
        if not isinstance(source_status, str) or not source_status.strip():
            raise PublicCatalogError(
                "Public MOD metadata must retain source_redistribution_status."
            )
        expected_filename = operation.get("expected_filename")
        _validate_relative_identity(expected_filename, "operation.expected_filename")
        if PurePosixPath(str(expected_filename)).name != expected_filename:
            raise PublicCatalogError("operation.expected_filename must be one filename.")
        files = operation.get("files")
        if files is not None:
            if not isinstance(files, list) or not files:
                raise PublicCatalogError("operation.files must be a non-empty array.")
            for spec in files:
                file_spec = _required_mapping(spec, "operation.files entry")
                _validate_relative_identity(file_spec.get("path"), "operation.files.path")


def public_catalog_from_payload(payload: Any) -> dict[str, Any]:
    public_payload = copy.deepcopy(_required_mapping(payload, "catalog"))
    for entry in _required_entries(public_payload):
        operation = _required_mapping(entry.get("operation"), "operation")
        policy = _required_mapping(entry.get("integrity_policy"), "integrity_policy")
        operation["bundled"] = False
        operation.pop("bundle_dir", None)
        source_status = policy.get("source_redistribution_status")
        if source_status is None:
            source_status = policy.get("redistribution_status")
        if not isinstance(source_status, str) or not source_status.strip():
            raise PublicCatalogError(
                "Source catalog redistribution_status must be a non-empty string."
            )
        policy["source_redistribution_status"] = source_status.strip()
        policy["redistribution_status"] = PUBLIC_REDISTRIBUTION_STATUS
    validate_public_catalog(public_payload)
    return public_payload


def render_catalog(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def prepare_catalog(source: Path) -> str:
    payload = json.loads(source.read_text(encoding="utf-8"))
    return render_catalog(public_catalog_from_payload(payload))


def _write_or_check(path: Path, expected: str, *, check: bool) -> None:
    if check:
        if not path.is_file():
            raise PublicCatalogError(f"Public catalog is missing: {path}")
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            raise PublicCatalogError(f"Public catalog is stale: {path}")
        validate_public_catalog(json.loads(actual))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8", newline="\n")


def main() -> int:
    args = parse_args()
    outputs = (
        (args.core_output, prepare_catalog(args.core_source)),
        (args.community_output, prepare_catalog(args.community_source)),
    )
    for path, expected in outputs:
        _write_or_check(path, expected, check=args.check)
    action = "verified" if args.check else "generated"
    sys.stdout.write(
        json.dumps(
            {
                "status": action,
                "outputs": [str(path.resolve()) for path, _expected in outputs],
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
