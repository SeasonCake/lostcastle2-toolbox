from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageGrab
import win32gui
import win32ui


def capture_with_print_window(hwnd: int, width: int, height: int) -> Image.Image | None:
    """Capture an occluded window without moving the user's pointer or focus."""

    window_dc = win32gui.GetWindowDC(hwnd)
    source_dc = win32ui.CreateDCFromHandle(window_dc)
    memory_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    try:
        bitmap.CreateCompatibleBitmap(source_dc, width, height)
        memory_dc.SelectObject(bitmap)
        if not ctypes.windll.user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 0x00000002):
            return None
        info = bitmap.GetInfo()
        bits = bitmap.GetBitmapBits(True)
        return Image.frombuffer(
            "RGB",
            (info["bmWidth"], info["bmHeight"]),
            bits,
            "raw",
            "BGRX",
            0,
            1,
        ).copy()
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        memory_dc.DeleteDC()
        # CreateDCFromHandle wraps a borrowed HDC returned by GetWindowDC.
        # Releasing it with DeleteDC is invalid and can fail after a successful
        # capture; ReleaseDC below is the matching lifetime operation.
        win32gui.ReleaseDC(hwnd, window_dc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--screen",
        action="store_true",
        help="Capture screen pixels instead of PrintWindow target content.",
    )
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
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    image = None if args.screen else capture_with_print_window(matches[0], width, height)
    if image is None:
        image = ImageGrab.grab(
            bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True
        )
    image.save(args.output)
    print(f"{args.output} {image.width}x{image.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
