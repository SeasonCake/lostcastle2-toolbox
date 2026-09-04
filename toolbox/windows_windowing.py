from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any


MONITOR_DEFAULTTONEAREST = 0x00000002
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200


class MonitorInfo(ctypes.Structure):
    _fields_ = (
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    )


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.MonitorFromRect.argtypes = (ctypes.POINTER(wintypes.RECT), wintypes.DWORD)
_user32.MonitorFromRect.restype = wintypes.HANDLE
_user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
_user32.GetMonitorInfoW.restype = wintypes.BOOL
_user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
_user32.GetAncestor.restype = wintypes.HWND
_user32.SetWindowPos.argtypes = (
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
)
_user32.SetWindowPos.restype = wintypes.BOOL


def clamp_window_position(
    x: int,
    y: int,
    width: int,
    height: int,
    work_area: tuple[int, int, int, int],
) -> tuple[int, int]:
    """Clamp a top-level window to one monitor's (left, top, right, bottom) work area."""

    left, top, right, bottom = (int(value) for value in work_area)
    usable_width = max(0, right - left)
    usable_height = max(0, bottom - top)
    maximum_x = left + max(0, usable_width - max(1, int(width)))
    maximum_y = top + max(0, usable_height - max(1, int(height)))
    return (
        min(maximum_x, max(left, int(x))),
        min(maximum_y, max(top, int(y))),
    )


def nearest_monitor_work_area(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    fallback_width: int,
    fallback_height: int,
) -> tuple[int, int, int, int]:
    """Return the nearest monitor work area, falling back to Tk's primary-screen size."""

    fallback = (0, 0, max(1, int(fallback_width)), max(1, int(fallback_height)))
    rect = wintypes.RECT(
        int(x),
        int(y),
        int(x) + max(1, int(width)),
        int(y) + max(1, int(height)),
    )
    try:
        monitor = _user32.MonitorFromRect(ctypes.byref(rect), MONITOR_DEFAULTTONEAREST)
        if not monitor:
            return fallback
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(MonitorInfo)
        if not _user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return fallback
        work = info.rcWork
        result = (int(work.left), int(work.top), int(work.right), int(work.bottom))
        if result[2] <= result[0] or result[3] <= result[1]:
            return fallback
        return result
    except (AttributeError, OSError, ValueError):
        return fallback


def clamp_to_nearest_work_area(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    fallback_width: int,
    fallback_height: int,
) -> tuple[int, int]:
    work_area = nearest_monitor_work_area(
        x,
        y,
        width,
        height,
        fallback_width=fallback_width,
        fallback_height=fallback_height,
    )
    return clamp_window_position(x, y, width, height, work_area)


def tk_geometry(width: int, height: int, x: int, y: int) -> str:
    return f"{max(1, int(width))}x{max(1, int(height))}{int(x):+d}{int(y):+d}"


def move_tk_window_no_activate(window: Any, x: int, y: int) -> bool:
    """Place a mapped Tk top-level at an absolute virtual-screen coordinate."""

    try:
        window.update_idletasks()
        client_hwnd = int(window.winfo_toplevel().winfo_id())
        hwnd = int(_user32.GetAncestor(client_hwnd, 2) or client_hwnd)
        return bool(
            _user32.SetWindowPos(
                hwnd,
                0,
                int(x),
                int(y),
                0,
                0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER,
            )
        )
    except (AttributeError, OSError, ValueError):
        return False


def place_tk_window(
    window: Any,
    width: int,
    height: int,
    x: int,
    y: int,
) -> None:
    """Set Tk client size and then enforce the absolute virtual-screen position."""

    window.geometry(tk_geometry(width, height, x, y))
    move_tk_window_no_activate(window, x, y)
