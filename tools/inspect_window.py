from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    args = parser.parse_args()
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        user32.SetProcessDPIAware()
    user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.GetWindowLongW.restype = wintypes.LONG
    matches: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        if buffer.value == args.title:
            matches.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    if not matches:
        print(json.dumps({"found": False}))
        return 1
    windows = []
    for hwnd in matches:
        style = int(user32.GetWindowLongW(hwnd, -20)) & 0xFFFFFFFF
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        windows.append(
            {
                "visible": bool(user32.IsWindowVisible(hwnd)),
                "toolwindow": bool(style & 0x00000080),
                "appwindow": bool(style & 0x00040000),
                "click_through": bool(style & 0x00000020),
                "extended_style": f"0x{style:08X}",
                "rect": [rect.left, rect.top, rect.right, rect.bottom],
            }
        )
    print(
        json.dumps(
            {
                "found": True,
                "windows": windows,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
