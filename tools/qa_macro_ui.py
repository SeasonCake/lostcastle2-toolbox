from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import font as tkfont
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from toolbox.macro_engine import MacroState
from toolbox.macro_ui import ACTION_LABELS, MacroFeature, runtime_presentation


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def top_level_rect(window: tk.Misc) -> tuple[int, int, int, int, int]:
    user32 = ctypes.windll.user32
    client = int(window.winfo_id())
    hwnd = int(user32.GetAncestor(client, 2) or client)
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise OSError("GetWindowRect failed")
    return hwnd, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def widget_receipt(widget: tk.Misc, *, left: int, top: int) -> dict[str, object]:
    widget_font = tkfont.Font(root=widget, font=widget.cget("font"))
    text = str(widget.cget("text"))
    requested_width = widget.winfo_reqwidth()
    requested_height = widget.winfo_reqheight()
    measured_text_width = widget_font.measure(text)
    font_linespace = widget_font.metrics("linespace")
    return {
        "actual": {
            "x": widget.winfo_rootx() - left,
            "y": widget.winfo_rooty() - top,
            "width": widget.winfo_width(),
            "height": widget.winfo_height(),
        },
        "requested": {
            "width": requested_width,
            "height": requested_height,
        },
        "font": {
            "measure": measured_text_width,
            "linespace": font_linespace,
        },
        "requested_width": requested_width,
        "requested_height": requested_height,
        "measured_text_width": measured_text_width,
        "font_linespace": font_linespace,
        "text": text,
    }


def find_text_widget(parent: tk.Misc, text: str) -> tk.Misc | None:
    for child in parent.winfo_children():
        try:
            if str(child.cget("text")) == text:
                return child
        except tk.TclError:
            pass
        nested = find_text_widget(child, text)
        if nested is not None:
            return nested
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--window-size", default="980x820")
    parser.add_argument("--tk-scaling", type=float, default=1.0)
    parser.add_argument(
        "--state",
        choices=(
            "idle",
            "armed-trigger",
            "armed-step",
            "accepted-trigger",
            "invalid",
            "wait",
            "down",
            "blocked",
            "advanced",
        ),
        default="idle",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_ns = time.time_ns()
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
    root = tk.Tk()
    root.withdraw()
    root.tk.call("tk", "scaling", args.tk_scaling)
    temporary = tempfile.TemporaryDirectory(prefix="lc2-macro-ui-qa-")
    feature = MacroFeature(root, Path(temporary.name))
    feature.open_window()
    window = feature.window
    if window is None:
        raise RuntimeError("macro window was not created")
    title = f"LC2 Macro QA {os.getpid()} {args.state} {args.tk_scaling:g}"
    window.title(title)
    window.geometry(args.window_size)
    window.update_idletasks()

    if args.state == "armed-trigger":
        feature._toggle_key_capture("trigger_key")
    elif args.state == "armed-step":
        feature._toggle_key_capture("step_key")
    elif args.state == "accepted-trigger":
        feature._toggle_key_capture("trigger_key")
        feature._capture_keypress("trigger_key", SimpleNamespace(keysym="F6"))
    elif args.state == "invalid":
        feature._toggle_key_capture("trigger_key")
        feature._capture_keypress("trigger_key", SimpleNamespace(keysym="F13"))
    elif args.state == "wait":
        feature.vars["step_action"].set(ACTION_LABELS["wait"])
    elif args.state == "down":
        feature.vars["step_action"].set(ACTION_LABELS["down"])
    elif args.state == "blocked":
        feature._set_runtime(*runtime_presentation(MacroState.BLOCKED_FOCUS))
    elif args.state == "advanced":
        feature._toggle_advanced_settings()
    window.update_idletasks()
    print(f"PID={os.getpid()} TITLE={title}", flush=True)

    deadline = time.monotonic() + args.timeout
    last_size: int | None = None
    attempts = 0
    last_probe: dict[str, object] = {}

    def finish() -> None:
        nonlocal attempts, last_probe, last_size
        attempts += 1
        screenshot = args.screenshot.resolve()
        try:
            stat = screenshot.stat()
            last_probe = {
                "path": str(screenshot),
                "mtime_ns": stat.st_mtime_ns,
                "started_ns": started_ns,
                "size": stat.st_size,
                "previous_size": last_size,
            }
            ready = (
                stat.st_mtime_ns >= started_ns
                and stat.st_size > 0
                and last_size == stat.st_size
            )
            last_size = stat.st_size
        except OSError:
            ready = False
            last_probe = {"path": str(screenshot), "missing": True}
        if not ready:
            if time.monotonic() < deadline:
                root.after(150, finish)
                return
            print(
                "QA screenshot timeout "
                + json.dumps(
                    {"attempts": attempts, "last_probe": last_probe},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )
            feature.close()
            root.destroy()
            return

        window.update_idletasks()
        hwnd, left, top, width, height = top_level_rect(window)
        with Image.open(screenshot) as image:
            screenshot_width, screenshot_height = image.size
        labels: dict[str, tk.Misc] = {
            "runtime": feature.runtime_label,
            "status": feature.status_label,
            "trigger_capture": feature._capture_buttons["trigger_key"],
            "step_capture": feature._capture_buttons["step_key"],
            "step_key_label": feature.step_key_label,
            "step_ms_label": feature.step_ms_label,
        }
        for key, text in (
            ("runtime_limit", "最长运行"),
            ("runtime_unit", "秒"),
            ("trigger_label", "主按键"),
            ("mode_label", "运行方式"),
        ):
            widget = find_text_widget(window, text)
            if widget is not None:
                labels[key] = widget
        payload = {
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "process": {
                "pid": os.getpid(),
                "executable": str(Path(sys.executable).resolve()),
                "command_line": subprocess.list2cmdline([sys.executable, *sys.argv]),
                "hwnd": hwnd,
            },
            "source": {
                "root": str(ROOT),
                "files": {
                    path.relative_to(ROOT).as_posix(): sha256(path)
                    for path in (
                        ROOT / "toolbox" / "macro_ui.py",
                        ROOT / "toolbox" / "macro_config.py",
                        Path(__file__).resolve(),
                    )
                },
            },
            "window": {"title": title, "width": width, "height": height},
            "screenshot": {
                "path": str(screenshot),
                "bytes": screenshot.stat().st_size,
                "sha256": sha256(screenshot),
                "width": screenshot_width,
                "height": screenshot_height,
            },
            "labels": {
                key: widget_receipt(widget, left=left, top=top)
                for key, widget in labels.items()
                if widget is not None and widget.winfo_ismapped()
            },
            "state": args.state,
            "tk_scaling": args.tk_scaling,
        }
        destination = args.receipt.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"RECEIPT={destination}", flush=True)
        feature.close()
        root.destroy()

    root.after(150, finish)
    try:
        root.mainloop()
    finally:
        temporary.cleanup()
    return 0 if args.receipt.resolve().is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
