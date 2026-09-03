from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
import re

import dnfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify an LC2 Combat Bridge build profile without loading it."
    )
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument(
        "--profile",
        choices=("diagnostic", "distribution"),
        required=True,
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def user_strings(path: Path) -> tuple[str, ...]:
    logger = logging.getLogger("dnfile.stream")
    previous_level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        image = dnfile.dnPE(str(path))
        if image.net is None:
            raise ValueError("Bridge is not a managed assembly.")
        heap = image.net.metadata.streams.get(b"#US")
        if heap is None:
            raise ValueError("Bridge has no managed user-string heap.")
        values: list[str] = []
        offset = 1
        while offset < heap.sizeof():
            item = heap.get(offset)
            if item is None or item.raw_size <= 0:
                break
            value = item.value_bytes().decode("utf-16-le", errors="replace").rstrip("\x00")
            if value:
                values.append(value)
            offset += item.raw_size
        return tuple(values)
    finally:
        logger.setLevel(previous_level)


def main() -> int:
    args = parse_args()
    bridge = args.bridge.resolve()
    if not bridge.is_file():
        raise ValueError("Bridge DLL is missing.")
    strings = user_strings(bridge)
    expected = args.profile
    alternate = (
        "distribution"
        if args.profile == "diagnostic"
        else "diagnostic"
    )
    if "profile=" not in strings or expected not in strings or alternate in strings:
        raise ValueError("Bridge profile marker is missing or ambiguous.")
    raw = bridge.read_bytes()
    ascii_paths = re.findall(rb"(?i)(?:[a-z]:[\\/]|\\\\)[\x20-\x7e]{4,240}", raw)
    utf16_paths = re.findall(
        r"(?i)(?:[a-z]:[\\/]|\\\\)[^\x00\r\n]{4,240}",
        raw.decode("utf-16-le", errors="ignore"),
    )
    if ascii_paths or utf16_paths or b".pdb" in raw.lower():
        raise ValueError("Bridge contains a machine-local path or PDB reference.")
    print(
        json.dumps(
            {
                "profile": args.profile,
                "size_bytes": bridge.stat().st_size,
                "sha256": sha256(bridge),
                "machine_local_paths": 0,
                "pdb_references": 0,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
