from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT_FILES = {".doorstop_version", "doorstop_config.ini", "winhttp.dll"}
ALLOWED_PREFIXES = ("BepInEx/core/", "BepInEx/unity-libs/", "dotnet/")
CONFIG_PATH = "BepInEx/config/BepInEx.cfg"
CONSOLE_SECTION = "Logging.Console"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a clean, pinned LC2 BepInEx/HUD runtime bundle."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="A validated game root/runtime directory, or a compatible ZIP source.",
    )
    parser.add_argument("--bridge", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalize_member(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    path = PurePosixPath(normalized)
    if not normalized or normalized.endswith("/"):
        return ""
    if path.is_absolute() or ".." in path.parts or ":" in normalized:
        raise ValueError(f"Unsafe runtime archive member: {name}")
    return path.as_posix()


def update_ini_value(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    section_pattern = re.compile(r"^\s*\[([^]]+)\]\s*$")
    key_pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*).*$", re.IGNORECASE)
    current_section = ""
    found_section = False
    for index, line in enumerate(lines):
        section_match = section_pattern.match(line)
        if section_match:
            current_section = section_match.group(1).strip()
            if current_section.casefold() == section.casefold():
                found_section = True
            continue
        if current_section.casefold() != section.casefold():
            continue
        key_match = key_pattern.match(line)
        if key_match:
            lines[index] = f"{key_match.group(1)}{value}"
            return "\n".join(lines) + "\n"
    if lines and lines[-1]:
        lines.append("")
    if not found_section:
        lines.append(f"[{section}]")
    lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def clean_bepinex_config(content: bytes) -> bytes:
    text = content.decode("utf-8-sig")
    text = update_ini_value(text, CONSOLE_SECTION, "Enabled", "false")
    text = update_ini_value(text, "IL2CPP", "UnityBaseLibrariesSource", "6000.3.16.zip")
    return text.encode("utf-8")


def member_is_allowed(normalized: str) -> bool:
    return (
        normalized in ALLOWED_ROOT_FILES
        or normalized.startswith(ALLOWED_PREFIXES)
        or normalized == CONFIG_PATH
    )


def selected_archive_members(source_archive: Path) -> dict[str, bytes]:
    selected: dict[str, bytes] = {}
    source_names: dict[str, str] = {}
    with zipfile.ZipFile(source_archive) as archive:
        for info in archive.infolist():
            normalized = normalize_member(info.filename)
            if not normalized:
                continue
            if not member_is_allowed(normalized):
                continue
            folded = normalized.casefold()
            if folded in source_names:
                raise ValueError(
                    f"Duplicate runtime member after normalization: {normalized}"
                )
            content = archive.read(info)
            if normalized == CONFIG_PATH:
                content = clean_bepinex_config(content)
            source_names[folded] = normalized
            selected[normalized] = content
    validate_selected_members(selected)
    return selected


def selected_directory_members(source_root: Path) -> dict[str, bytes]:
    selected: dict[str, bytes] = {}
    resolved_root = source_root.resolve()
    for item in source_root.rglob("*"):
        if not item.is_file() or item.is_symlink():
            continue
        resolved = item.resolve()
        try:
            relative = resolved.relative_to(resolved_root).as_posix()
        except ValueError as exception:
            raise ValueError("Runtime source escaped its root.") from exception
        normalized = normalize_member(relative)
        if not member_is_allowed(normalized):
            continue
        folded = normalized.casefold()
        if folded in {path.casefold() for path in selected}:
            raise ValueError(
                f"Duplicate runtime member after normalization: {normalized}"
            )
        content = resolved.read_bytes()
        if normalized == CONFIG_PATH:
            content = clean_bepinex_config(content)
        selected[normalized] = content
    validate_selected_members(selected)
    return selected


def validate_selected_members(selected: dict[str, bytes]) -> None:
    required = {
        ".doorstop_version",
        "doorstop_config.ini",
        "winhttp.dll",
        "BepInEx/core/BepInEx.Core.dll",
        "BepInEx/core/BepInEx.Unity.IL2CPP.dll",
        "BepInEx/unity-libs/6000.3.16.zip",
        "dotnet/coreclr.dll",
        CONFIG_PATH,
    }
    missing = sorted(required - selected.keys())
    if missing:
        raise ValueError(f"Runtime source is missing required members: {missing}")
    forbidden = [
        path
        for path in selected
        if path.startswith(("BepInEx/plugins/", "BepInEx/cache/", "BepInEx/interop/"))
    ]
    if forbidden:
        raise ValueError(f"Prepared runtime unexpectedly contains plugins/cache: {forbidden}")


def source_tree_sha256(members: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(members.items(), key=lambda item: item[0].casefold()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(len(content).to_bytes(8, "little"))
        digest.update(content)
    return digest.hexdigest().upper()


def prepare(args: argparse.Namespace) -> dict[str, object]:
    source = args.source.resolve()
    bridge = args.bridge.resolve()
    if not source.exists() or not bridge.is_file():
        raise ValueError("Runtime source and Bridge DLL must exist.")
    output_root = args.output_root.resolve()
    expected_root = (PROJECT_ROOT / "third_party" / "lc2_runtime").resolve()
    if output_root != expected_root:
        raise ValueError("Refusing to replace an unexpected runtime output root.")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    if source.is_dir():
        members = selected_directory_members(source)
        source_identity = {
            "kind": "validated_game_runtime",
            "file_count": len(members),
            "uncompressed_bytes": sum(len(content) for content in members.values()),
            "tree_sha256": source_tree_sha256(members),
        }
    elif source.is_file() and source.suffix.casefold() == ".zip":
        members = selected_archive_members(source)
        source_identity = {
            "kind": "zip_archive",
            "filename": source.name,
            "size_bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        }
    else:
        raise ValueError("Runtime source must be a directory or ZIP archive.")
    runtime_zip = output_root / "bepinex-runtime.zip"
    with zipfile.ZipFile(
        runtime_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for relative, content in sorted(members.items(), key=lambda item: item[0].casefold()):
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 29, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)

    bridge_target = output_root / "LC2CombatBridge.dll"
    shutil.copyfile(bridge, bridge_target)
    specs = [
        {
            "path": relative,
            "size_bytes": len(content),
            "sha256": sha256_bytes(content),
        }
        for relative, content in sorted(members.items(), key=lambda item: item[0].casefold())
    ]
    manifest = {
        "schema_version": 1,
        "runtime_version": "BepInEx 6.0.0-be.785 + LC2CombatBridge 0.4.5",
        "source_identity": source_identity,
        "runtime_archive": {
            "filename": runtime_zip.name,
            "size_bytes": runtime_zip.stat().st_size,
            "sha256": sha256_file(runtime_zip),
        },
        "runtime_files": specs,
        "required_paths": [
            ".doorstop_version",
            "doorstop_config.ini",
            "winhttp.dll",
            "BepInEx/core/BepInEx.Core.dll",
            "BepInEx/core/BepInEx.Unity.IL2CPP.dll",
            "BepInEx/unity-libs/6000.3.16.zip",
            "dotnet/coreclr.dll",
            CONFIG_PATH,
        ],
        "bridge": {
            "filename": bridge_target.name,
            "target": "BepInEx/plugins/LC2CombatBridge/LC2CombatBridge.dll",
            "size_bytes": bridge_target.stat().st_size,
            "sha256": sha256_file(bridge_target),
        },
        "excluded_source_prefixes": [
            "BepInEx/plugins/",
            "BepInEx/cache/",
            "BepInEx/interop/",
        ],
        "runtime_file_count": len(specs),
        "runtime_uncompressed_bytes": sum(len(content) for content in members.values()),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    manifest = prepare(parse_args())
    sys.stdout.buffer.write(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
