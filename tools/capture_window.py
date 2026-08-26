from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path

from PIL import ImageGrab


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        user32.SetProcessDPIAware()
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        if buffer.value == args.title and user32.IsWindowVisible(hwnd):
            matches.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    if not matches:
        raise SystemExit(f"window not found: {args.title}")
    rect = wintypes.RECT()
    if not user32.GetWindowRect(matches[0], ctypes.byref(rect)):
        raise SystemExit("GetWindowRect failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True)
    image.save(args.output)
    print(f"{args.output} {image.width}x{image.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
