from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from toolbox.mod_inspector import ModInspectionError, ModPackageInspector, SUPPORTED_ARCHIVES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Statically inspect a local LC2 MOD library.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--seven-zip", required=True, type=Path)
    parser.add_argument("--json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inspector = ModPackageInspector(args.seven_zip)
    records: list[dict[str, object]] = []
    candidates = sorted(
        (
            item
            for item in args.source.iterdir()
            if item.is_dir()
            or item.suffix.casefold() == ".dll"
            or item.suffix.casefold() in SUPPORTED_ARCHIVES
        ),
        key=lambda item: item.name.casefold(),
    )
    for source in candidates:
        try:
            draft = inspector.inspect(source)
        except ModInspectionError as exception:
            records.append(
                {
                    "source": source.name,
                    "supported": False,
                    "error": str(exception),
                }
            )
            continue
        record = asdict(draft)
        record["source"] = source.name
        record["supported"] = True
        record["payload_bytes"] = sum(item.size_bytes for item in draft.payload)
        record["payload_files"] = len(draft.payload)
        record["payload_dlls"] = sum(
            item.target_path.casefold().endswith(".dll") for item in draft.payload
        )
        record["dll_files"] = [
            {
                "path": item.target_path,
                "size_bytes": item.size_bytes,
                "sha256": item.sha256,
            }
            for item in draft.payload
            if item.target_path.casefold().endswith(".dll")
        ]
        record.pop("manifest", None)
        record.pop("payload", None)
        record.pop("source_kind", None)
        record.pop("suggested_id", None)
        record.pop("evidence", None)
        records.append(record)

    supported = [record for record in records if record["supported"]]
    summary = {
        "inputs": len(records),
        "supported": len(supported),
        "unsupported": len(records) - len(supported),
        "with_author_evidence": sum(
            record.get("author") != "社区未署名" for record in supported
        ),
        "with_hotkeys": sum(bool(record.get("hotkeys")) for record in supported),
        "with_warnings": sum(bool(record.get("warnings")) for record in supported),
        "payload_bytes": sum(int(record.get("payload_bytes", 0)) for record in supported),
    }
    result = {"summary": summary, "records": records}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered + "\n", encoding="utf-8")
    sys.stdout.buffer.write((rendered + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
