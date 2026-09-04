from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import win32file
import win32pipe


PIPE_NAME = r"\\.\pipe\LostCastle2Toolbox.Combat.v2"


def status_event(
    sequence: int,
    status: str,
    *,
    session_id: str = "qa-archive-session",
) -> dict[str, object]:
    return {
        "schema_version": 2,
        "event_id": f"{session_id}:{sequence}",
        "event_type": "status",
        "session_id": session_id,
        "sequence": sequence,
        "monotonic_ms": sequence * 100,
        "room_id": None,
        "aggregate": False,
        "hook_path": "qa.archive",
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ready-file", required=True, type=Path)
    parser.add_argument("--orphan-end-count", type=int, default=0)
    parser.add_argument("--hold-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.orphan_end_count < 0 or args.orphan_end_count > 1000:
        parser.error("--orphan-end-count must be between 0 and 1000")
    if args.hold_seconds < 0 or args.hold_seconds > 60:
        parser.error("--hold-seconds must be between 0 and 60")
    handle = win32pipe.CreateNamedPipe(
        PIPE_NAME,
        win32pipe.PIPE_ACCESS_OUTBOUND,
        win32pipe.PIPE_TYPE_BYTE
        | win32pipe.PIPE_READMODE_BYTE
        | win32pipe.PIPE_WAIT,
        1,
        8192,
        8192,
        0,
        None,
    )
    args.ready_file.parent.mkdir(parents=True, exist_ok=True)
    args.ready_file.write_text("ready\n", encoding="utf-8")
    try:
        win32pipe.ConnectNamedPipe(handle, None)
        payloads = [
            status_event(
                sequence,
                "session_ended",
                session_id="qa-orphan-ended-session",
            )
            for sequence in range(args.orphan_end_count)
        ]
        payloads.extend(
            [
                status_event(0, "session_started"),
                status_event(1, "session_ended"),
            ]
        )
        for event in payloads:
            payload = json.dumps(
                event,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8") + b"\n"
            win32file.WriteFile(handle, payload)
            time.sleep(0.01)
        time.sleep(args.hold_seconds)
    finally:
        try:
            win32pipe.DisconnectNamedPipe(handle)
        except Exception:
            pass
        win32file.CloseHandle(handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
