from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import os
from pathlib import Path

from PIL import Image, ImageGrab
import win32gui
import win32process
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


def save_png_atomic(image: Image.Image, output: Path) -> None:
    """Expose a capture only after its complete PNG bytes are on disk."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp.png")
    try:
        image.save(temporary, format="PNG")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--screen",
        action="store_true",
        help="Capture screen pixels instead of PrintWindow target content.",
    )
    parser.add_argument(
        "--pid",
        type=int,
        help="Match a visible top-level window by exact process id instead of title.",
    )
    parser.add_argument(
        "--smallest",
        action="store_true",
        help="When a process owns multiple visible windows, capture the smallest one.",
    )
    parser.add_argument("--min-width", type=int, default=1)
    parser.add_argument("--min-height", type=int, default=1)
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
        process_matches = (
            args.pid is not None
            and win32process.GetWindowThreadProcessId(hwnd)[1] == args.pid
        )
        title_matches = args.pid is None and buffer.value == args.title
        if (process_matches or title_matches) and user32.IsWindowVisible(hwnd):
            candidate = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(candidate)):
                return True
            width = candidate.right - candidate.left
            height = candidate.bottom - candidate.top
            if width >= args.min_width and height >= args.min_height:
                matches.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    if not matches:
        target = f"pid={args.pid}" if args.pid is not None else args.title
        raise SystemExit(f"window not found: {target}")
    if args.smallest and len(matches) > 1:
        def window_area(hwnd: int) -> int:
            candidate = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(candidate)):
                return 2**63 - 1
            return max(0, candidate.right - candidate.left) * max(
                0, candidate.bottom - candidate.top
            )

        matches.sort(key=window_area)
    rect = wintypes.RECT()
    if not user32.GetWindowRect(matches[0], ctypes.byref(rect)):
        raise SystemExit("GetWindowRect failed")
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    image = None if args.screen else capture_with_print_window(matches[0], width, height)
    if image is None:
        image = ImageGrab.grab(
            bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True
        )
    save_png_atomic(image, args.output)
    print(f"{args.output} {image.width}x{image.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
