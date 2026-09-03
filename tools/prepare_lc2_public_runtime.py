from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (PROJECT_ROOT / "third_party" / "lc2_public_runtime").resolve()
MANIFEST_PATH = (PROJECT_ROOT / "assets" / "lc2_public_runtime_manifest.json").resolve()

OFFICIAL_BUILD = 785
OFFICIAL_VERSION = "6.0.0-be.785+6abdba4"
OFFICIAL_COMMIT = "6abdba47eeebe08552282e7a58ef0f4a9ab60b62"
OFFICIAL_FILENAME = (
    "BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip"
)
OFFICIAL_URL = (
    "https://builds.bepinex.dev/projects/bepinex_be/785/"
    "BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip"
)
OFFICIAL_SIZE = 34_335_572
OFFICIAL_SHA256 = (
    "2A7CBF74D26ABE4765C3E662DB1721B923BAC39849EBFEF2CA5DC7DE7E2D9B7F"
)

BRIDGE_FILENAME = "LC2CombatBridge.dll"
BRIDGE_TARGET = "BepInEx/plugins/LC2CombatBridge/LC2CombatBridge.dll"
BRIDGE_SIZE = 102_400
BRIDGE_SHA256 = (
    "190B8B4A8C661C73A32ADF15DF56487E57473E591BFA25520D172A7E188E7DED"
)
RUNTIME_ARCHIVE_FILENAME = "bepinex-runtime.zip"
CONFIG_PATH = "BepInEx/config/BepInEx.cfg"
UNITY_LIBRARIES_SOURCE = "https://unity.bepinex.dev/libraries/{VERSION}.zip"
REQUIRED_PATHS = (
    ".doorstop_version",
    "doorstop_config.ini",
    "winhttp.dll",
    "BepInEx/core/BepInEx.Core.dll",
    "BepInEx/core/BepInEx.Unity.IL2CPP.dll",
    "dotnet/coreclr.dll",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the exact official LC2 public BepInEx runtime bundle."
    )
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--bridge", required=True, type=Path)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_member(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.endswith("/")
        or path.is_absolute()
        or ".." in path.parts
        or ":" in normalized
    ):
        raise ValueError(f"Unsafe official runtime member: {name}")
    return path.as_posix()


def inspect_official_archive(source: Path) -> tuple[list[dict[str, object]], int]:
    source = source.resolve()
    if not source.is_file():
        raise ValueError("Official BepInEx archive is missing.")
    if source.name != OFFICIAL_FILENAME:
        raise ValueError("Official BepInEx archive filename is unexpected.")
    if source.stat().st_size != OFFICIAL_SIZE or sha256_file(source) != OFFICIAL_SHA256:
        raise ValueError("Official BepInEx archive identity does not match build 785.")

    specs: list[dict[str, object]] = []
    seen: set[str] = set()
    uncompressed_bytes = 0
    with zipfile.ZipFile(source) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = normalized_member(info.filename)
            folded = member.casefold()
            if folded in seen:
                raise ValueError(
                    f"Duplicate official runtime member after normalization: {member}"
                )
            content = archive.read(info)
            if len(content) != info.file_size:
                raise ValueError(f"Official runtime member size changed while reading: {member}")
            seen.add(folded)
            uncompressed_bytes += len(content)
            specs.append(
                {
                    "path": member,
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest().upper(),
                }
            )

    missing = [path for path in REQUIRED_PATHS if path.casefold() not in seen]
    if missing:
        raise ValueError(f"Official BepInEx archive is missing required members: {missing}")
    specs.sort(key=lambda item: str(item["path"]).casefold())
    return specs, uncompressed_bytes


def build_manifest(
    source: Path,
    bridge: Path,
) -> dict[str, object]:
    bridge = bridge.resolve()
    if (
        not bridge.is_file()
        or bridge.stat().st_size != BRIDGE_SIZE
        or sha256_file(bridge) != BRIDGE_SHA256
    ):
        raise ValueError("LC2CombatBridge public candidate identity is unexpected.")
    specs, uncompressed_bytes = inspect_official_archive(source)
    return {
        "schema_version": 1,
        "build_profile": "distribution",
        "runtime_version": (
            "Official BepInEx 6.0.0-be.785 + LC2CombatBridge 1.7.4"
        ),
        "source_identity": {
            "kind": "official_bepinex_build",
            "project": "bepinex_be",
            "build": OFFICIAL_BUILD,
            "version": OFFICIAL_VERSION,
            "commit": OFFICIAL_COMMIT,
            "url": OFFICIAL_URL,
            "filename": OFFICIAL_FILENAME,
            "size_bytes": OFFICIAL_SIZE,
            "sha256": OFFICIAL_SHA256,
        },
        "runtime_archive": {
            "filename": RUNTIME_ARCHIVE_FILENAME,
            "size_bytes": OFFICIAL_SIZE,
            "sha256": OFFICIAL_SHA256,
        },
        "runtime_files": specs,
        "required_paths": list(REQUIRED_PATHS),
        "configuration": {
            "path": CONFIG_PATH,
            "fresh_console_enabled": False,
            "fresh_unity_base_libraries_source": UNITY_LIBRARIES_SOURCE,
        },
        "bridge": {
            "filename": BRIDGE_FILENAME,
            "target": BRIDGE_TARGET,
            "size_bytes": BRIDGE_SIZE,
            "sha256": BRIDGE_SHA256,
            "diagnostics_enabled": False,
        },
        "runtime_file_count": len(specs),
        "runtime_uncompressed_bytes": uncompressed_bytes,
    }


def copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def prepare(args: argparse.Namespace) -> dict[str, object]:
    source = args.source.resolve()
    bridge = args.bridge.resolve()
    output_root = args.output_root.resolve()
    manifest_path = args.manifest.resolve()
    if output_root != OUTPUT_ROOT:
        raise ValueError("Refusing to replace an unexpected public runtime output root.")
    if manifest_path != MANIFEST_PATH:
        raise ValueError("Refusing to replace an unexpected public runtime manifest.")

    manifest = build_manifest(source, bridge)
    output_root.mkdir(parents=True, exist_ok=True)
    allowed_outputs = {RUNTIME_ARCHIVE_FILENAME, BRIDGE_FILENAME}
    unexpected = sorted(
        item.name for item in output_root.iterdir() if item.name not in allowed_outputs
    )
    if unexpected:
        raise ValueError(f"Public runtime output root contains unexpected files: {unexpected}")

    runtime_target = output_root / RUNTIME_ARCHIVE_FILENAME
    bridge_target = output_root / BRIDGE_FILENAME
    copy_atomic(source, runtime_target)
    copy_atomic(bridge, bridge_target)
    if (
        runtime_target.stat().st_size != OFFICIAL_SIZE
        or sha256_file(runtime_target) != OFFICIAL_SHA256
    ):
        raise ValueError("Copied public runtime is not byte-identical to the official ZIP.")
    if bridge_target.stat().st_size != BRIDGE_SIZE or sha256_file(bridge_target) != BRIDGE_SHA256:
        raise ValueError("Copied public Bridge identity is unexpected.")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    manifest = prepare(parse_args())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
