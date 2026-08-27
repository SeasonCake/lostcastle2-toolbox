from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
from typing import Any
import winreg

from toolbox.app_shell import ToolboxShell, seed_demo_combat
from toolbox.combat_aggregator import CombatAggregator, ScenarioRegistry, SourceRegistry
from toolbox.combat_transport import (
    CombatBridgeClient,
    CombatEventPump,
    CombatEventValidator,
    CombatInbox,
)
from toolbox.macro_ui import MacroFeature
from toolbox.mod_manager import ModCatalog, ModManager


APP_NAME = "失落城堡2工具箱"
APP_VERSION = "1.5.3"
STEAM_APP_ID = "2445690"
DEFAULT_GAME_EXE = Path(
    os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
) / Path(
    r"Steam\steamapps\common\Lost Castle 2\LostCastle2.exe"
)
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 365
TRANSPARENT_COLOR = "#010203"
APP_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
RESOURCE_DIR = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)
CONFIG_DIR = Path(os.environ.get("KEYVIEW_CONFIG_DIR", APP_DIR / "config"))
CONFIG_FILE = CONFIG_DIR / "settings.json"
LEGACY_CONFIG_FILE = (
    Path(os.environ.get("LOCALAPPDATA", Path.home()))
    / "LostCastle2KeyView"
    / "settings.json"
)

DEFAULT_KEY_LAYOUT = {
    "W": (127, 84, 66, 64),
    "A": (51, 156, 66, 64),
    "S": (127, 156, 66, 64),
    "D": (203, 156, 66, 64),
    "I": (358, 84, 66, 64),
    "O": (434, 84, 66, 64),
    "J": (320, 156, 66, 64),
    "K": (396, 156, 66, 64),
    "L": (472, 156, 66, 64),
    "SPACE": (166, 228, 268, 64),
}

LOST_CASTLE_KEYS = ("W", "A", "S", "D", "I", "O", "J", "K", "L", "SPACE")
WASD_KEYS = ("W", "A", "S", "D", "SPACE", "SHIFT", "CTRL")
MAX_DISPLAY_KEYS = 20
GAME_LAYOUT_KEYS = frozenset(("W", "A", "S", "D", "U", "I", "O", "J", "K", "L", "SPACE"))
DEFAULT_COLOR_PRESET = "soft_mist"

COLOR_PRESETS: dict[str, dict[str, str]] = {
    "soft_mist": {
        "name": "柔雾",
        "background": "#1B242E",
        "panel_outline": "#667587",
        "idle": "#2E3945",
        "idle_outline": "#A9B7C5",
        "inner_outline": "#536273",
        "key_text": "#FAFCFF",
        "active": "#F2C861",
        "active_outline": "#FFE6A0",
        "active_text": "#2B2109",
    },
    "ice_blue": {
        "name": "冰蓝",
        "background": "#172838",
        "panel_outline": "#6A98BC",
        "idle": "#31516B",
        "idle_outline": "#9BC6E7",
        "inner_outline": "#46708E",
        "key_text": "#F5FBFF",
        "active": "#72BDF3",
        "active_outline": "#C6E9FF",
        "active_text": "#0A2539",
    },
    "mint": {
        "name": "薄荷",
        "background": "#18322E",
        "panel_outline": "#69A89A",
        "idle": "#31574F",
        "idle_outline": "#98CFC1",
        "inner_outline": "#467468",
        "key_text": "#F4FFFC",
        "active": "#65D5B5",
        "active_outline": "#C4F5E6",
        "active_text": "#09271F",
    },
    "warm_sand": {
        "name": "暖砂",
        "background": "#332A22",
        "panel_outline": "#A18468",
        "idle": "#5B4C3E",
        "idle_outline": "#D2BDA7",
        "inner_outline": "#796653",
        "key_text": "#FFF9F0",
        "active": "#EAAF58",
        "active_outline": "#FFE0A6",
        "active_text": "#2B1908",
    },
    "berry": {
        "name": "莓紫",
        "background": "#2D2234",
        "panel_outline": "#9B7AA8",
        "idle": "#554260",
        "idle_outline": "#C8ADD2",
        "inner_outline": "#725A80",
        "key_text": "#FFF8FF",
        "active": "#D69BEA",
        "active_outline": "#F3D3FF",
        "active_text": "#2A1232",
    },
    "classic": {
        "name": "经典",
        "background": "#0F1217",
        "panel_outline": "#2B313B",
        "idle": "#191D23",
        "idle_outline": "#929BAA",
        "inner_outline": "#353C47",
        "key_text": "#F4F6F9",
        "active": "#F4C74D",
        "active_outline": "#FFE8A1",
        "active_text": "#211A08",
    },
}

KEY_DEFINITIONS: dict[str, tuple[str, int]] = {
    **{chr(code): (chr(code), code) for code in range(0x41, 0x5B)},
    **{str(number): (str(number), 0x30 + number) for number in range(10)},
    "SPACE": ("SPACE", 0x20),
    "SHIFT": ("SHIFT", 0x10),
    "CTRL": ("CTRL", 0x11),
    "ALT": ("ALT", 0x12),
    "TAB": ("TAB", 0x09),
    "ESC": ("ESC", 0x1B),
    "ENTER": ("ENTER", 0x0D),
    "BACKSPACE": ("BACK", 0x08),
    "CAPS": ("CAPS", 0x14),
    "LEFT": ("←", 0x25),
    "UP": ("↑", 0x26),
    "RIGHT": ("→", 0x27),
    "DOWN": ("↓", 0x28),
    "LMB": ("LMB", 0x01),
    "RMB": ("RMB", 0x02),
    "MMB": ("MMB", 0x04),
    **{
        f"F{number}": (f"F{number}", 0x6F + number)
        for number in (*range(1, 8), 12)
    },
}

GAMEPAD_LABELS: dict[str, str] = {
    "PAD_LT": "LT",
    "PAD_LB": "LB",
    "PAD_RB": "RB",
    "PAD_RT": "RT",
    "PAD_UP": "↑",
    "PAD_LEFT": "←",
    "PAD_RIGHT": "→",
    "PAD_DOWN": "↓",
    "PAD_LS": "L摇杆",
    "PAD_VIEW": "视图",
    "PAD_MENU": "菜单",
    "PAD_RS": "R摇杆",
    "PAD_X": "X",
    "PAD_Y": "Y",
    "PAD_A": "A",
    "PAD_B": "B",
}

GAMEPAD_LAYOUT = {
    "PAD_LT": (38, 84, 88, 54),
    "PAD_LB": (136, 84, 88, 54),
    "PAD_RB": (376, 84, 88, 54),
    "PAD_RT": (474, 84, 88, 54),
    "PAD_UP": (86, 160, 54, 54),
    "PAD_LEFT": (28, 218, 54, 54),
    "PAD_RIGHT": (144, 218, 54, 54),
    "PAD_DOWN": (86, 276, 54, 54),
    "PAD_LS": (218, 174, 78, 78),
    "PAD_VIEW": (248, 278, 66, 46),
    "PAD_MENU": (326, 278, 66, 46),
    "PAD_RS": (334, 174, 78, 78),
    "PAD_Y": (470, 160, 54, 54),
    "PAD_X": (412, 218, 54, 54),
    "PAD_B": (528, 218, 54, 54),
    "PAD_A": (470, 276, 54, 54),
}


def gamepad_layout(*, key_only: bool = False) -> dict[str, tuple[int, int, int, int]]:
    y_offset = -70 if key_only else 0
    return {
        key: (x, y + y_offset, width, height)
        for key, (x, y, width, height) in GAMEPAD_LAYOUT.items()
    }


def display_label(input_id: str) -> str:
    if input_id in GAMEPAD_LABELS:
        return GAMEPAD_LABELS[input_id]
    return KEY_DEFINITIONS[input_id][0]

KEY_GROUPS = (
    ("字母", tuple("QWERTYUIOP") + tuple("ASDFGHJKL") + tuple("ZXCVBNM")),
    ("数字", tuple(str(number) for number in range(1, 10)) + ("0",)),
    (
        "常用",
        (
            "SPACE",
            "SHIFT",
            "CTRL",
            "ALT",
            "TAB",
            "ESC",
            "ENTER",
            "BACKSPACE",
            "CAPS",
            "LEFT",
            "UP",
            "DOWN",
            "RIGHT",
            "LMB",
            "RMB",
            "MMB",
        ),
    ),
    ("功能键", tuple(f"F{number}" for number in (*range(1, 8), 12))),
)

def build_physical_key_geometry() -> dict[str, tuple[int, float, float]]:
    geometry: dict[str, tuple[int, float, float]] = {
        "ESC": (0, 0.0, 1.25),
        "BACKSPACE": (1, 11.4, 2.0),
        "TAB": (2, 0.0, 1.55),
        "CAPS": (3, 0.0, 1.75),
        "ENTER": (3, 11.7, 1.9),
        "SHIFT": (4, 0.0, 2.2),
        "CTRL": (5, 0.0, 1.45),
        "ALT": (5, 1.6, 1.45),
        "SPACE": (5, 3.2, 5.0),
        "UP": (5, 9.7, 1.0),
        "LEFT": (6, 8.55, 1.0),
        "DOWN": (6, 9.7, 1.0),
        "RIGHT": (6, 10.85, 1.0),
        "LMB": (7, 4.25, 1.45),
        "MMB": (7, 5.85, 1.45),
        "RMB": (7, 7.45, 1.45),
    }
    function_keys = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F12")
    for index, key in enumerate(function_keys):
        geometry[key] = (0, 1.7 + index * 1.25, 1.0)
    for index, key in enumerate(tuple("1234567890")):
        geometry[key] = (1, 0.6 + index * 1.08, 1.0)
    for index, key in enumerate(tuple("QWERTYUIOP")):
        geometry[key] = (2, 1.72 + index * 1.08, 1.0)
    for index, key in enumerate(tuple("ASDFGHJKL")):
        geometry[key] = (3, 1.92 + index * 1.08, 1.0)
    for index, key in enumerate(tuple("ZXCVBNM")):
        geometry[key] = (4, 2.38 + index * 1.08, 1.0)
    return geometry


PHYSICAL_KEY_GEOMETRY = build_physical_key_geometry()

ACCESSORY_KEY_GROUPS = (
    ("modifier", ("TAB", "SHIFT", "CTRL", "ALT", "ESC", "CAPS")),
    ("letter", tuple("QWERTYUIOPASDFGHJKLZXCVBNM")),
    ("commit", ("ENTER", "BACKSPACE")),
    ("navigation", ("LEFT", "UP", "DOWN", "RIGHT")),
    ("mouse", ("LMB", "MMB", "RMB")),
    ("number", tuple("1234567890")),
    ("function", ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F12")),
)


def accessory_key_width(key: str) -> int:
    return {
        "SHIFT": 88,
        "CTRL": 82,
        "ALT": 74,
        "TAB": 74,
        "ENTER": 92,
        "BACKSPACE": 92,
        "CAPS": 78,
        "LMB": 74,
        "MMB": 74,
        "RMB": 74,
    }.get(key, 64)


def layout_for_keys(
    selected_keys: list[str] | tuple[str, ...], *, key_only: bool = False
) -> dict[str, tuple[int, int, int, int]]:
    selected = [key for key in selected_keys if key in KEY_DEFINITIONS]
    selected_set = set(selected)
    y_offset = -70 if key_only else 0
    game_key_count = len(selected_set.intersection(GAME_LAYOUT_KEYS))
    if selected and game_key_count >= 4:
        layout: dict[str, tuple[int, int, int, int]] = {}
        for key in ("W", "A", "S", "D"):
            if key in selected_set:
                x, y, width, height = DEFAULT_KEY_LAYOUT[key]
                layout[key] = (x, y + y_offset, width, height)
        for row_keys, y in (("UIO", 84), ("JKL", 156)):
            present = [key for key in row_keys if key in selected_set]
            row_width = len(present) * 66 + max(0, len(present) - 1) * 10
            start_x = 320 + (218 - row_width) // 2
            for index, key in enumerate(present):
                layout[key] = (start_x + index * 76, y + y_offset, 66, 64)
        accessory_keys = selected_set - GAME_LAYOUT_KEYS
        ordered_accessories: list[tuple[str, str]] = []
        for group_name, group_keys in ACCESSORY_KEY_GROUPS:
            ordered_accessories.extend(
                (key, group_name) for key in group_keys if key in accessory_keys
            )
        accessory_rows: list[list[tuple[str, int, str]]] = []
        current_row: list[tuple[str, int, str]] = []
        current_width = 0
        previous_group = ""
        for key, group_name in ordered_accessories:
            key_width = accessory_key_width(key)
            gap = 0 if not current_row else 10 if group_name == previous_group else 24
            if current_row and current_width + gap + key_width > 520:
                accessory_rows.append(current_row)
                current_row = []
                current_width = 0
                gap = 0
            current_row.append((key, key_width, group_name))
            current_width += gap + key_width
            previous_group = group_name
        if current_row:
            accessory_rows.append(current_row)

        accessory_start_y = 228 + y_offset
        for row_index, row_entries in enumerate(accessory_rows):
            row_width = 0
            previous_group = ""
            for _key, key_width, group_name in row_entries:
                if row_width:
                    row_width += 10 if group_name == previous_group else 24
                row_width += key_width
                previous_group = group_name
            cursor_x = (WINDOW_WIDTH - row_width) // 2
            previous_group = ""
            for key, key_width, group_name in row_entries:
                if previous_group:
                    cursor_x += 10 if group_name == previous_group else 24
                layout[key] = (
                    cursor_x,
                    accessory_start_y + row_index * 74,
                    key_width,
                    60,
                )
                cursor_x += key_width
                previous_group = group_name

        if "SPACE" in selected_set:
            x, y, width, height = DEFAULT_KEY_LAYOUT["SPACE"]
            space_y = y + y_offset + len(accessory_rows) * 74
            layout["SPACE"] = (x, space_y, width, height)
        return layout
    if not selected:
        return {}
    selected_geometry = {
        key: PHYSICAL_KEY_GEOMETRY[key]
        for key in selected
        if key in PHYSICAL_KEY_GEOMETRY
    }
    if not selected_geometry:
        return {}
    used_rows = sorted({row for row, _x, _width in selected_geometry.values()})
    main_rows = [row for row in used_rows if row < 5]
    row_entries: dict[int, list[tuple[str, float, float]]] = {}
    for key in selected:
        row, x, width = selected_geometry[key]
        row_entries.setdefault(row, []).append((key, x, width))
    for entries in row_entries.values():
        entries.sort(key=lambda entry: entry[1])

    def row_width_units(entries: list[tuple[str, float, float]]) -> float:
        width_units = sum(width for _key, _x, width in entries)
        for left, right in zip(entries, entries[1:]):
            _left_key, left_x, left_width = left
            _right_key, right_x, _right_width = right
            physical_gap = max(0.0, right_x - (left_x + left_width))
            width_units += 0.18 if physical_gap < 0.25 else 0.32 if physical_gap < 1.4 else 0.48
        return width_units

    maximum_row_units = max(
        (row_width_units(row_entries[row]) for row in main_rows), default=9.0
    )
    unit = min(58.0, 520.0 / max(1.0, maximum_row_units))
    key_height = max(42, min(60, round(unit * 1.05)))
    vertical_gap = max(10, round(key_height * 0.2))
    layout: dict[str, tuple[int, int, int, int]] = {}
    start_y = 18 if key_only else 94
    row_stagger = {2: -10, 3: 0, 4: 10}
    for row_index, row in enumerate(main_rows):
        entries = row_entries[row]
        widths = [max(38, round(width * unit)) for _key, _x, width in entries]
        gaps: list[int] = []
        for left, right in zip(entries, entries[1:]):
            _left_key, left_x, left_width = left
            _right_key, right_x, _right_width = right
            physical_gap = max(0.0, right_x - (left_x + left_width))
            gap_units = 0.18 if physical_gap < 0.25 else 0.32 if physical_gap < 1.4 else 0.48
            gaps.append(max(8, round(gap_units * unit)))
        row_width = sum(widths) + sum(gaps)
        stagger = row_stagger.get(row, 0)
        cursor_x = min(
            max(40, (WINDOW_WIDTH - row_width) // 2 + stagger),
            WINDOW_WIDTH - 40 - row_width,
        )
        row_y = start_y + row_index * (key_height + vertical_gap)
        for index, (key, _x, _width) in enumerate(entries):
            layout[key] = (cursor_x, row_y, widths[index], key_height)
            cursor_x += widths[index]
            if index < len(gaps):
                cursor_x += gaps[index]

    utility_groups = (
        ("modifier", ("CTRL", "ALT", "SPACE")),
        ("navigation", ("LEFT", "UP", "DOWN", "RIGHT")),
        ("mouse", ("LMB", "MMB", "RMB")),
    )
    utility_rows: list[list[tuple[str, int, str]]] = []
    current_utility_row: list[tuple[str, int, str]] = []
    current_utility_width = 0
    previous_group = ""
    for group_name, group_keys in utility_groups:
        for key in group_keys:
            if key not in selected_geometry:
                continue
            _row, _x, width_units = selected_geometry[key]
            key_width = max(38, round(width_units * unit))
            gap = (
                0
                if not current_utility_row
                else 10
                if group_name == previous_group
                else 24
            )
            if current_utility_row and current_utility_width + gap + key_width > 520:
                utility_rows.append(current_utility_row)
                current_utility_row = []
                current_utility_width = 0
                gap = 0
            current_utility_row.append((key, key_width, group_name))
            current_utility_width += gap + key_width
            previous_group = group_name
    if current_utility_row:
        utility_rows.append(current_utility_row)

    utility_start_y = start_y + len(main_rows) * (key_height + vertical_gap)
    for row_index, entries in enumerate(utility_rows):
        row_width = 0
        previous_group = ""
        for _key, key_width, group_name in entries:
            if row_width:
                row_width += 10 if group_name == previous_group else 24
            row_width += key_width
            previous_group = group_name
        cursor_x = (WINDOW_WIDTH - row_width) // 2
        previous_group = ""
        for key, key_width, group_name in entries:
            if previous_group:
                cursor_x += 10 if group_name == previous_group else 24
            layout[key] = (
                cursor_x,
                utility_start_y + row_index * (key_height + vertical_gap),
                key_width,
                key_height,
            )
            cursor_x += key_width
            previous_group = group_name
    return layout


def overlay_height(layout: dict[str, tuple[int, int, int, int]], *, key_only: bool) -> int:
    bottom = max((y + height for _x, y, _width, height in layout.values()), default=90)
    if key_only:
        return max(110, bottom + 14)
    return max(WINDOW_HEIGHT, bottom + 72)


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class XInputGamepad(ctypes.Structure):
    _fields_ = (
        ("buttons", wintypes.WORD),
        ("left_trigger", wintypes.BYTE),
        ("right_trigger", wintypes.BYTE),
        ("left_thumb_x", ctypes.c_short),
        ("left_thumb_y", ctypes.c_short),
        ("right_thumb_x", ctypes.c_short),
        ("right_thumb_y", ctypes.c_short),
    )


class XInputState(ctypes.Structure):
    _fields_ = (("packet_number", wintypes.DWORD), ("gamepad", XInputGamepad))


XINPUT_BUTTONS = {
    "PAD_UP": 0x0001,
    "PAD_DOWN": 0x0002,
    "PAD_LEFT": 0x0004,
    "PAD_RIGHT": 0x0008,
    "PAD_MENU": 0x0010,
    "PAD_VIEW": 0x0020,
    "PAD_LS": 0x0040,
    "PAD_RS": 0x0080,
    "PAD_LB": 0x0100,
    "PAD_RB": 0x0200,
    "PAD_A": 0x1000,
    "PAD_B": 0x2000,
    "PAD_X": 0x4000,
    "PAD_Y": 0x8000,
}


def _load_xinput() -> Any | None:
    for library_name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
        try:
            library = ctypes.WinDLL(library_name)
            library.XInputGetState.argtypes = (wintypes.DWORD, ctypes.POINTER(XInputState))
            library.XInputGetState.restype = wintypes.DWORD
            return library
        except (OSError, AttributeError):
            continue
    return None


XINPUT = _load_xinput()


def read_gamepad_state(index: int = 0) -> tuple[bool, dict[str, bool]]:
    state = XInputState()
    if XINPUT is None or XINPUT.XInputGetState(index, ctypes.byref(state)) != 0:
        return False, {key: False for key in GAMEPAD_LABELS}
    gamepad = state.gamepad
    active = {
        key: bool(gamepad.buttons & mask)
        for key, mask in XINPUT_BUTTONS.items()
    }
    active["PAD_LT"] = gamepad.left_trigger > 30
    active["PAD_RT"] = gamepad.right_trigger > 30
    active["PAD_LS"] = active["PAD_LS"] or (
        abs(gamepad.left_thumb_x) > 7849 or abs(gamepad.left_thumb_y) > 7849
    )
    active["PAD_RS"] = active["PAD_RS"] or (
        abs(gamepad.right_thumb_x) > 8689 or abs(gamepad.right_thumb_y) > 8689
    )
    return True, active

kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.GetLastError.argtypes = ()
kernel32.GetLastError.restype = wintypes.DWORD
user32.GetParent.argtypes = (wintypes.HWND,)
user32.GetParent.restype = wintypes.HWND
user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
user32.GetAncestor.restype = wintypes.HWND
user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
user32.GetWindowLongW.restype = wintypes.LONG
user32.SetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.LONG)
user32.SetWindowLongW.restype = wintypes.LONG
user32.SetWindowPos.argtypes = (
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
)
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetWindow.argtypes = (wintypes.HWND, wintypes.UINT)
user32.GetWindow.restype = wintypes.HWND
user32.IsWindow.argtypes = (wintypes.HWND,)
user32.IsWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
user32.ShowWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
user32.SetForegroundWindow.restype = wintypes.BOOL


def enable_dpi_awareness() -> None:
    """Keep geometry crisp and predictable on scaled Windows displays."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            user32.SetProcessDPIAware()


def hwnd_is_above(
    candidate: int,
    reference: int,
    get_previous: Any | None = None,
) -> bool:
    """Return whether candidate precedes reference in the Windows Z order."""
    if not candidate or not reference or candidate == reference:
        return False
    previous = get_previous or (lambda hwnd: user32.GetWindow(hwnd, 3))
    current = reference
    visited: set[int] = set()
    for _index in range(1024):
        current = int(previous(current) or 0)
        if not current or current in visited:
            return False
        if current == candidate:
            return True
        visited.add(current)
    return False


def load_settings(path: Path = CONFIG_FILE) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "x": None,
        "y": 90,
        "background_opacity": 0.88,
        "show_background": True,
        "key_only": False,
        "selected_keys": list(LOST_CASTLE_KEYS),
        "input_display_mode": "keyboard",
        "color_preset": DEFAULT_COLOR_PRESET,
        "ui_scale": 1.0,
        "toolbox_width": 900,
        "toolbox_height": 650,
        "toolbox_ui_scale": 1.0,
        "hud_ui_scale": 1.0,
        "always_on_top": True,
        "game_path": str(DEFAULT_GAME_EXE),
    }
    source_path = path
    if path == CONFIG_FILE and not path.exists() and LEGACY_CONFIG_FILE.exists():
        source_path = LEGACY_CONFIG_FILE
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            defaults.update(data)
            if "background_opacity" not in data and "opacity" in data:
                defaults["background_opacity"] = data["opacity"]
    except (OSError, ValueError, TypeError):
        pass
    defaults.pop("opacity", None)

    def bounded_float(key: str, default: float, minimum: float, maximum: float) -> float:
        try:
            value = float(defaults.get(key, default))
        except (TypeError, ValueError):
            value = default
        return min(maximum, max(minimum, value))

    defaults["background_opacity"] = bounded_float(
        "background_opacity", 0.88, 0.0, 1.0
    )
    selected: list[str] = []
    for key in defaults.get("selected_keys", LOST_CASTLE_KEYS):
        key_id = str(key).upper()
        if key_id in KEY_DEFINITIONS and key_id not in selected:
            selected.append(key_id)
    defaults["selected_keys"] = (selected or list(LOST_CASTLE_KEYS))[:MAX_DISPLAY_KEYS]
    input_display_mode = str(defaults.get("input_display_mode", "keyboard"))
    defaults["input_display_mode"] = (
        input_display_mode if input_display_mode in {"keyboard", "gamepad"} else "keyboard"
    )
    color_preset = str(defaults.get("color_preset", DEFAULT_COLOR_PRESET))
    defaults["color_preset"] = (
        color_preset if color_preset in COLOR_PRESETS else DEFAULT_COLOR_PRESET
    )
    defaults["ui_scale"] = bounded_float("ui_scale", 1.0, 0.6, 1.8)
    try:
        toolbox_width = int(defaults.get("toolbox_width", 900))
        toolbox_height = int(defaults.get("toolbox_height", 650))
    except (TypeError, ValueError):
        toolbox_width, toolbox_height = 900, 650
    defaults["toolbox_width"] = min(1400, max(780, toolbox_width))
    defaults["toolbox_height"] = min(1000, max(560, toolbox_height))
    defaults["toolbox_ui_scale"] = bounded_float(
        "toolbox_ui_scale", 1.0, 0.9, 1.15
    )
    defaults["hud_ui_scale"] = bounded_float("hud_ui_scale", 1.0, 0.85, 1.25)
    defaults["show_background"] = bool(defaults.get("show_background", True))
    defaults["key_only"] = bool(defaults.get("key_only", False))
    return defaults


def save_settings(settings: dict[str, Any], path: Path = CONFIG_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_path.replace(path)


def steam_install_location() -> Path | None:
    uninstall_keys = (
        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {STEAM_APP_ID}",
        rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {STEAM_APP_ID}",
    )
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_name in uninstall_keys:
            try:
                with winreg.OpenKey(hive, key_name) as key:
                    value, _ = winreg.QueryValueEx(key, "InstallLocation")
                    if value:
                        return Path(value)
            except OSError:
                continue
    return None


def resolve_game_exe(configured_path: str | os.PathLike[str] | None) -> Path | None:
    candidates: list[Path] = []
    if configured_path:
        candidates.append(Path(configured_path))
    candidates.append(DEFAULT_GAME_EXE)
    install_location = steam_install_location()
    if install_location:
        candidates.append(install_location / "LostCastle2.exe")
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.resolve()
        except OSError:
            continue
    return None


class ProcessEntry32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


kernel32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W))
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(ProcessEntry32W))
kernel32.Process32NextW.restype = wintypes.BOOL


def find_game_process_id() -> int | None:
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot in (0, ctypes.c_void_p(-1).value):
        return None
    entry = ProcessEntry32W()
    entry.dwSize = ctypes.sizeof(ProcessEntry32W)
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return None
        while True:
            if entry.szExeFile.casefold() == "lostcastle2.exe":
                return int(entry.th32ProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    return None


def focus_process_window(process_id: int) -> bool:
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process_id and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback, 0)
    if not found:
        return False
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    return True


def is_key_down(vk_code: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)


def rounded_rectangle(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    **kwargs: Any,
) -> int:
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class KeyViewApp:
    BG = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["background"]
    PANEL_OUTLINE = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["panel_outline"]
    MUTED = "#87909F"
    TEXT = "#F4F6F9"
    IDLE_KEY = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["idle"]
    IDLE_OUTLINE = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["idle_outline"]
    INNER_OUTLINE = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["inner_outline"]
    KEY_TEXT = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["key_text"]
    ACTIVE = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["active"]
    ACTIVE_OUTLINE = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["active_outline"]
    ACTIVE_TEXT = COLOR_PRESETS[DEFAULT_COLOR_PRESET]["active_text"]
    DANGER = "#FF7C73"

    def __init__(
        self,
        root: tk.Misc,
        *,
        demo: bool = False,
        macro_feature: MacroFeature | None = None,
        on_request_close: Any | None = None,
    ) -> None:
        self.root = root
        self.demo = demo
        self.started_at = time.monotonic()
        self.settings = load_settings()
        self.background_opacity = float(self.settings["background_opacity"])
        self.show_background = bool(self.settings["show_background"])
        self.key_only = bool(self.settings["key_only"])
        self.selected_keys = list(self.settings["selected_keys"])
        self.display_mode = str(self.settings["input_display_mode"])
        self.color_preset = str(self.settings["color_preset"])
        self.ui_scale = float(self.settings["ui_scale"])
        self.toolbox_width = int(self.settings["toolbox_width"])
        self.toolbox_height = int(self.settings["toolbox_height"])
        self.toolbox_ui_scale = float(self.settings["toolbox_ui_scale"])
        self.hud_ui_scale = float(self.settings["hud_ui_scale"])
        self.applied_scale = 1.0
        self.canvas_font_bases: dict[int, tuple[str, int, str, str]] = {}
        self.resize_origin: tuple[int, int, float] | None = None
        self._apply_theme_values()
        self.always_on_top = bool(self.settings.get("always_on_top", True))
        self.click_through = False
        self.visible = True
        self.current_layout = self._layout_for_display()
        self.current_height = overlay_height(self.current_layout, key_only=self.key_only)
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.key_items: dict[str, tuple[int, int, int, int]] = {}
        self.key_state: dict[str, bool] = {
            key: False for key in (*KEY_DEFINITIONS, *GAMEPAD_LABELS)
        }
        self.hotkey_state = {"F8": False, "F9": False, "F10": False, "F11": False}
        self.last_process_check = 0.0
        self.last_layer_order_check = 0.0
        self.game_process_id: int | None = None
        self.settings_window: tk.Toplevel | None = None
        self.settings_vars: dict[str, tk.Variable] = {}
        self.key_toggle_buttons: dict[str, tk.Button] = {}
        self.theme_buttons: dict[str, tk.Button] = {}
        self._owns_macro_feature = macro_feature is None
        self.macro_feature = macro_feature or MacroFeature(root, CONFIG_DIR)
        self._on_request_close = on_request_close

        root.title(os.environ.get("KEYVIEW_WINDOW_TITLE", APP_NAME))
        root.overrideredirect(True)
        root.configure(bg=TRANSPARENT_COLOR)
        root.attributes("-transparentcolor", TRANSPARENT_COLOR)
        root.attributes("-alpha", 1.0)
        root.attributes("-topmost", self.always_on_top)
        try:
            root.attributes("-toolwindow", True)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            root,
            width=round(WINDOW_WIDTH * self.ui_scale),
            height=round(self.current_height * self.ui_scale),
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._position_window()
        self._create_background_layer()
        self._build_ui()
        self._build_context_menu()
        self._apply_display_mode(save=False)

        for surface in (self.canvas, self.background_canvas):
            surface.bind("<ButtonPress-1>", self._begin_drag)
            surface.bind("<B1-Motion>", self._drag_window)
            surface.bind("<ButtonRelease-1>", self._end_drag)
            surface.bind("<Button-3>", self._show_context_menu)
        root.bind("<Escape>", lambda _event: self.toggle_visible())
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after_idle(self._apply_window_roles)
        root.after(16, self._tick)

    def _apply_theme_values(self) -> None:
        theme = COLOR_PRESETS[self.color_preset]
        self.BG = theme["background"]
        self.PANEL_OUTLINE = theme["panel_outline"]
        self.IDLE_KEY = theme["idle"]
        self.IDLE_OUTLINE = theme["idle_outline"]
        self.INNER_OUTLINE = theme["inner_outline"]
        self.KEY_TEXT = theme["key_text"]
        self.ACTIVE = theme["active"]
        self.ACTIVE_OUTLINE = theme["active_outline"]
        self.ACTIVE_TEXT = theme["active_text"]

    def _scaled_dimensions(self) -> tuple[int, int]:
        return (
            round(WINDOW_WIDTH * self.ui_scale),
            round(self.current_height * self.ui_scale),
        )

    def _layout_for_display(self) -> dict[str, tuple[int, int, int, int]]:
        if self.display_mode == "gamepad":
            return gamepad_layout(key_only=self.key_only)
        return layout_for_keys(self.selected_keys, key_only=self.key_only)

    def _visible_input_ids(self) -> tuple[str, ...]:
        if self.display_mode == "gamepad":
            return tuple(GAMEPAD_LABELS)
        return tuple(self.selected_keys)

    def _position_window(self) -> None:
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        configured_x = self.settings.get("x")
        configured_y = self.settings.get("y", 90)
        scaled_width, scaled_height = self._scaled_dimensions()
        x = int(configured_x) if configured_x is not None else (screen_w - scaled_width) // 2
        y = int(configured_y)
        x = min(max(0, x), max(0, screen_w - scaled_width))
        y = min(max(0, y), max(0, screen_h - scaled_height))
        self.root.geometry(f"{scaled_width}x{scaled_height}+{x}+{y}")
        self.root.update_idletasks()

    def _create_background_layer(self) -> None:
        self.background_window = tk.Toplevel(self.root)
        self.background_window.withdraw()
        self.background_window.overrideredirect(True)
        self.background_window.configure(bg=TRANSPARENT_COLOR)
        self.background_window.attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.background_window.attributes("-alpha", self.background_opacity)
        self.background_window.attributes("-topmost", self.always_on_top)
        try:
            self.background_window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        self.background_canvas = tk.Canvas(
            self.background_window,
            width=round(WINDOW_WIDTH * self.ui_scale),
            height=round(self.current_height * self.ui_scale),
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
            bd=0,
        )
        self.background_canvas.pack(fill="both", expand=True)
        self._redraw_background()

    def _redraw_background(self) -> None:
        self.background_canvas.delete("all")
        rounded_rectangle(
            self.background_canvas,
            4,
            4,
            WINDOW_WIDTH - 4,
            self.current_height - 4,
            24,
            fill=self.BG,
            outline=self.PANEL_OUTLINE,
            width=2,
            tags=("background-panel",),
        )

    def _remember_canvas_fonts(self) -> None:
        for item in self.canvas.find_all():
            if self.canvas.type(item) != "text" or item in self.canvas_font_bases:
                continue
            font = tkfont.Font(font=self.canvas.itemcget(item, "font"))
            self.canvas_font_bases[item] = (
                str(font.actual("family")),
                abs(int(font.actual("size"))),
                str(font.actual("weight")),
                str(font.actual("slant")),
            )

    def _scale_canvas_contents(self, target_scale: float) -> None:
        target_scale = min(1.8, max(0.6, float(target_scale)))
        ratio = target_scale / self.applied_scale
        if abs(ratio - 1.0) > 0.0001:
            self.canvas.scale("all", 0, 0, ratio, ratio)
            self.background_canvas.scale("all", 0, 0, ratio, ratio)
        self._remember_canvas_fonts()
        for item, (family, base_size, weight, slant) in list(
            self.canvas_font_bases.items()
        ):
            if self.canvas.type(item) != "text":
                continue
            self.canvas.itemconfigure(
                item,
                font=(
                    family,
                    max(5, round(base_size * target_scale)),
                    weight,
                    slant,
                ),
            )
        self.applied_scale = target_scale
        self.background_canvas.itemconfigure(
            "background-panel", width=max(1, round(2 * target_scale))
        )
        for key_id in self.key_items:
            self._set_key_visual(key_id, self.key_state.get(key_id, False))

    def _resize_windows_to_scale(self) -> None:
        scaled_width, scaled_height = self._scaled_dimensions()
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.canvas.configure(width=scaled_width, height=scaled_height)
        self.background_canvas.configure(width=scaled_width, height=scaled_height)
        self.root.geometry(f"{scaled_width}x{scaled_height}+{x}+{y}")
        self.root.update_idletasks()
        self._sync_background_layer()

    def _set_ui_scale(self, value: float, *, save: bool = True) -> None:
        next_scale = round(min(1.8, max(0.6, float(value))) / 0.05) * 0.05
        if abs(next_scale - self.ui_scale) < 0.001:
            return
        self.ui_scale = next_scale
        # Rebuild from unscaled geometry so repeated controls cannot accumulate
        # canvas drift or leave the foreground/background layers at different sizes.
        self._apply_display_mode(save=False)
        variable = self.settings_vars.get("ui_scale")
        if variable is not None:
            variable.set(round(self.ui_scale * 100))
        if hasattr(self, "ui_scale_value"):
            self.ui_scale_value.configure(text=f"{round(self.ui_scale * 100)}%")
        if save:
            self._save_current_settings()

    def set_ui_scale(self, value: float) -> None:
        self._set_ui_scale(value)

    def set_display_mode(self, mode: str) -> None:
        if mode not in {"keyboard", "gamepad"}:
            raise ValueError(f"Unsupported display mode: {mode}")
        if mode == self.display_mode:
            if not self.visible:
                self.toggle_visible()
            self.root.lift()
            return
        for input_id in self._visible_input_ids():
            self.key_state[input_id] = False
        self.display_mode = mode
        self._apply_display_mode(save=False)
        if not self.visible:
            self.toggle_visible()
        self.root.lift()
        self._sync_background_layer()
        self._save_current_settings()

    @property
    def toolbox_window_size(self) -> tuple[int, int]:
        return self.toolbox_width, self.toolbox_height

    def set_toolbox_window_size(self, width: int, height: int) -> None:
        self.toolbox_width = min(1400, max(780, int(width)))
        self.toolbox_height = min(1000, max(560, int(height)))
        self.settings["toolbox_width"] = self.toolbox_width
        self.settings["toolbox_height"] = self.toolbox_height
        self._save_current_settings()

    def set_toolbox_ui_scale(self, value: float) -> None:
        self.toolbox_ui_scale = min(1.15, max(0.9, float(value)))
        self.settings["toolbox_ui_scale"] = self.toolbox_ui_scale
        self._save_current_settings()

    def set_hud_ui_scale(self, value: float) -> None:
        self.hud_ui_scale = min(1.25, max(0.85, float(value)))
        self.settings["hud_ui_scale"] = self.hud_ui_scale
        self._save_current_settings()

    def _shell_hwnd(self, widget: tk.Misc) -> int:
        widget.update_idletasks()
        hwnd = int(widget.winfo_toplevel().winfo_id())
        return int(user32.GetParent(hwnd) or user32.GetAncestor(hwnd, 2) or hwnd)

    def _apply_toolwindow_style(
        self, widget: tk.Misc, *, click_through: bool, no_activate: bool = False
    ) -> None:
        try:
            widget.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        hwnd = self._shell_hwnd(widget)
        style = user32.GetWindowLongW(hwnd, -20)
        style |= 0x00000080
        style &= ~0x00040000
        if click_through:
            style |= 0x00000020
        else:
            style &= ~0x00000020
        if no_activate:
            style |= 0x08000000
        else:
            style &= ~0x08000000
        user32.SetWindowLongW(hwnd, -20, style)
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0037)

    def _apply_window_roles(self) -> None:
        self._apply_toolwindow_style(self.root, click_through=self.click_through)
        self._apply_toolwindow_style(
            self.background_window,
            click_through=self.click_through,
            no_activate=self.click_through,
        )
        self._apply_topmost_state()
        self._sync_background_layer()

    def _sync_background_layer(self) -> None:
        if (
            not self.visible
            or self.key_only
            or not self.show_background
            or self.background_opacity <= 0
        ):
            self.background_window.withdraw()
            return
        scaled_width, scaled_height = self._scaled_dimensions()
        geometry = f"{scaled_width}x{scaled_height}+{self.root.winfo_x()}+{self.root.winfo_y()}"
        self.background_window.geometry(geometry)
        self.background_window.attributes("-alpha", self.background_opacity)
        self.background_window.attributes("-topmost", self.always_on_top)
        self.background_window.deiconify()
        self.root.lift(self.background_window)
        self._ensure_layer_order(force=True)

    def _ensure_layer_order(self, *, force: bool = False) -> bool:
        """Keep the translucent backdrop behind the foreground without focus theft."""
        if (
            not self.visible
            or self.key_only
            or not self.show_background
            or self.background_opacity <= 0
        ):
            return False
        try:
            foreground = self._shell_hwnd(self.root)
            background = self._shell_hwnd(self.background_window)
        except tk.TclError:
            return False
        if not user32.IsWindow(foreground) or not user32.IsWindow(background):
            return False
        if not force and not hwnd_is_above(background, foreground):
            return False
        flags = 0x0001 | 0x0002 | 0x0010 | 0x0200
        return bool(user32.SetWindowPos(background, foreground, 0, 0, 0, 0, flags))

    def _build_ui(self) -> None:
        self.canvas.create_text(
            24,
            18,
            text="按键显示",
            fill=self.TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
            anchor="nw",
            tags=("drag-region", "chrome"),
        )
        self.canvas.create_text(
            25,
            50,
            text="LOST CASTLE 2",
            fill=self.MUTED,
            font=("Segoe UI", 8, "bold"),
            anchor="nw",
            tags=("drag-region", "chrome"),
        )
        self.canvas.create_line(
            22, 72, 578, 72, fill="#3A424E", width=1, tags=("chrome",)
        )

        self.launch_button = self._draw_button(
            314, 17, 126, 40, "▶  启动游戏", "launch-button", accent=True
        )
        self.settings_button = self._draw_button(
            446, 17, 40, 40, "⚙", "settings-button", compact=True
        )
        self.topmost_button = self._draw_button(
            492, 17, 40, 40, "T", "topmost-button", compact=True
        )
        self._draw_button(538, 17, 26, 40, "—", "hide-button", compact=True)
        self._draw_button(568, 17, 26, 40, "×", "close-button", compact=True)

        self._bind_button("launch-button", self.launch_game)
        self._bind_button("settings-button", self.open_settings)
        self._bind_button("topmost-button", self.toggle_topmost)
        self._bind_button("hide-button", self.toggle_visible)
        self._bind_button("close-button", self.close)
        self._update_topmost_button_visual()
        self._rebuild_keys()

        self.status_text = self.canvas.create_text(
            24,
            333,
            text="拖动移动  ·  F8 显示/隐藏  ·  F9 鼠标穿透",
            fill=self.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            tags=("drag-region", "chrome"),
        )
        self.running_text = self.canvas.create_text(
            576,
            333,
            text="● 就绪",
            fill="#7DDC9B",
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="e",
            tags=("drag-region", "chrome"),
        )
        self.resize_grip = self.canvas.create_text(
            586,
            self.current_height - 12,
            text="◢",
            fill=self.MUTED,
            font=("Segoe UI Symbol", 11),
            tags=("resize-grip", "control", "chrome"),
        )
        self.canvas.tag_bind("resize-grip", "<ButtonPress-1>", self._begin_resize)
        self.canvas.tag_bind("resize-grip", "<B1-Motion>", self._resize_window)
        self.canvas.tag_bind("resize-grip", "<ButtonRelease-1>", self._end_resize)
        self.canvas.tag_bind(
            "resize-grip", "<Enter>", lambda _event: self.canvas.configure(cursor="size_nw_se")
        )
        self.canvas.tag_bind(
            "resize-grip", "<Leave>", lambda _event: self.canvas.configure(cursor="")
        )
        self._update_status_text()

    def _draw_button(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        tag: str,
        *,
        accent: bool = False,
        compact: bool = False,
    ) -> tuple[int, int]:
        fill = "#332A13" if accent else "#181C22"
        outline = "#8E762B" if accent else "#343B46"
        text_color = "#FFE28A" if accent else self.TEXT
        shape = rounded_rectangle(
            self.canvas,
            x,
            y,
            x + width,
            y + height,
            10,
            fill=fill,
            outline=outline,
            width=1,
            tags=(tag, "control", "chrome"),
        )
        label = self.canvas.create_text(
            x + width / 2,
            y + height / 2,
            text=text,
            fill=text_color,
            font=("Microsoft YaHei UI", 9 if compact else 10, "bold"),
            tags=(tag, "control", "chrome"),
        )
        return shape, label

    def _bind_button(self, tag: str, command: Any) -> None:
        self.canvas.tag_bind(tag, "<Button-1>", lambda _event: command())
        self.canvas.tag_bind(tag, "<Enter>", lambda _event: self.canvas.configure(cursor="hand2"))
        self.canvas.tag_bind(tag, "<Leave>", lambda _event: self.canvas.configure(cursor=""))

    def _draw_key(
        self, key_id: str, x: int, y: int, width: int, height: int
    ) -> None:
        label = display_label(key_id)
        label_size = 18 if len(label) == 1 else 14 if len(label) <= 4 else 11
        shadow = rounded_rectangle(
            self.canvas,
            x,
            y + 4,
            x + width,
            y + height + 4,
            13,
            fill="#05070A",
            outline="",
            tags=("key-item", "drag-region"),
        )
        key = rounded_rectangle(
            self.canvas,
            x,
            y,
            x + width,
            y + height,
            13,
            fill=self.IDLE_KEY,
            outline=self.IDLE_OUTLINE,
            width=2,
            tags=("key-item", "drag-region"),
        )
        inner = rounded_rectangle(
            self.canvas,
            x + 5,
            y + 5,
            x + width - 5,
            y + height - 5,
            9,
            fill="",
            outline=self.INNER_OUTLINE,
            width=1,
            tags=("key-item", "drag-region"),
        )
        text = self.canvas.create_text(
            x + width / 2,
            y + height / 2 - 1,
            text=label,
            fill=self.KEY_TEXT,
            font=("Segoe UI", label_size, "bold"),
            tags=("key-item", "drag-region"),
        )
        self.key_items[key_id] = (shadow, key, inner, text)

    def _rebuild_keys(self) -> None:
        self.canvas.delete("key-item")
        self.key_items.clear()
        self.current_layout = self._layout_for_display()
        for key_id, (x, y, width, height) in self.current_layout.items():
            self._draw_key(key_id, x, y, width, height)

    def _apply_display_mode(self, *, save: bool = True) -> None:
        target_scale = self.ui_scale
        self._scale_canvas_contents(1.0)
        self.current_layout = self._layout_for_display()
        self.current_height = overlay_height(self.current_layout, key_only=self.key_only)
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{WINDOW_WIDTH}x{self.current_height}+{x}+{y}")
        self.canvas.configure(width=WINDOW_WIDTH, height=self.current_height)
        self.background_canvas.configure(width=WINDOW_WIDTH, height=self.current_height)
        self.canvas.itemconfigure("chrome", state="hidden" if self.key_only else "normal")
        footer_y = self.current_height - 32
        self.canvas.coords(self.status_text, 24, footer_y)
        self.canvas.coords(self.running_text, 576, footer_y)
        self.canvas.coords(self.resize_grip, 586, self.current_height - 12)
        self._rebuild_keys()
        self._redraw_background()
        self._scale_canvas_contents(target_scale)
        self._resize_windows_to_scale()
        if save:
            self._save_current_settings()

    def _build_context_menu(self) -> None:
        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="启动 Lost Castle 2", command=self.launch_game)
        self.menu.add_command(label="显示设置（F10）", command=self.open_settings)
        self.menu.add_command(label="宏设置", command=self.macro_feature.open_window)
        self.menu.add_command(label="切换纯净模式（F11）", command=self.toggle_clean_mode)
        self.menu.add_separator()
        self.menu.add_command(label="切换置顶", command=self.toggle_topmost)
        self.menu.add_command(label="切换鼠标穿透（F9）", command=self.toggle_click_through)
        self.menu.add_command(label="切换显示（F8）", command=self.toggle_visible)
        self.menu.add_command(label="恢复默认位置", command=self.reset_position)
        self.menu.add_command(label="重新定位游戏程序…", command=self.choose_game_path)
        self.menu.add_separator()
        self.menu.add_command(
            label="关闭按键显示" if self._on_request_close is not None else "退出",
            command=self.close,
        )

    def _show_context_menu(self, event: tk.Event[Any]) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)

    def _begin_drag(self, event: tk.Event[Any]) -> None:
        surface = event.widget
        tags = surface.gettags("current") if isinstance(surface, tk.Canvas) else ()
        if "control" in tags:
            return
        if event.widget is self.background_canvas:
            self.root.lift(self.background_window)
        self.drag_origin = (
            event.x_root,
            event.y_root,
            self.root.winfo_x(),
            self.root.winfo_y(),
        )

    def _drag_window(self, event: tk.Event[Any]) -> None:
        if not self.drag_origin:
            return
        start_x, start_y, window_x, window_y = self.drag_origin
        x = window_x + event.x_root - start_x
        y = window_y + event.y_root - start_y
        self.root.geometry(f"+{x}+{y}")
        if self.visible and self.show_background and self.background_opacity > 0:
            scaled_width, scaled_height = self._scaled_dimensions()
            self.background_window.geometry(
                f"{scaled_width}x{scaled_height}+{x}+{y}"
            )

    def _end_drag(self, _event: tk.Event[Any]) -> None:
        if self.drag_origin:
            self.drag_origin = None
            self.root.update_idletasks()
            self._sync_background_layer()
            self._save_current_settings()

    def _begin_resize(self, event: tk.Event[Any]) -> str:
        self.resize_origin = (event.x_root, event.y_root, self.ui_scale)
        return "break"

    def _resize_window(self, event: tk.Event[Any]) -> str:
        if self.resize_origin is None:
            return "break"
        start_x, start_y, start_scale = self.resize_origin
        delta_x = (event.x_root - start_x) / WINDOW_WIDTH
        delta_y = (event.y_root - start_y) / max(1, self.current_height)
        self._set_ui_scale(start_scale + max(delta_x, delta_y), save=False)
        return "break"

    def _end_resize(self, _event: tk.Event[Any]) -> str:
        if self.resize_origin is not None:
            self.resize_origin = None
            self._save_current_settings()
        return "break"

    def _set_key_visual(self, key_id: str, active: bool) -> None:
        if key_id not in self.key_items:
            return
        _shadow, key, inner, text = self.key_items[key_id]
        if active:
            self.canvas.itemconfigure(
                key,
                fill=self.ACTIVE,
                outline=self.ACTIVE_OUTLINE,
                width=max(2, round(3 * self.applied_scale)),
            )
            self.canvas.itemconfigure(text, fill=self.ACTIVE_TEXT)
            self.canvas.itemconfigure(
                inner,
                outline=self.ACTIVE_OUTLINE,
                width=max(1, round(1.5 * self.applied_scale)),
            )
        else:
            self.canvas.itemconfigure(
                key,
                fill=self.IDLE_KEY,
                outline=self.IDLE_OUTLINE,
                width=max(1, round(2 * self.applied_scale)),
            )
            self.canvas.itemconfigure(text, fill=self.KEY_TEXT)
            self.canvas.itemconfigure(
                inner,
                outline=self.INNER_OUTLINE,
                width=max(1, round(1.5 * self.applied_scale)),
            )

    def _demo_key_state(self, key_id: str, now: float) -> bool:
        if self.display_mode == "gamepad":
            sequence = (
                ("PAD_LS", "PAD_X"),
                ("PAD_LS", "PAD_A"),
                ("PAD_LB", "PAD_Y"),
                ("PAD_RT", "PAD_B"),
                ("PAD_UP", "PAD_MENU"),
            )
            return key_id in sequence[int((now - self.started_at) / 0.65) % len(sequence)]
        sequence = (
            ("W", "J"),
            ("W", "L"),
            ("A", "K"),
            ("D", "I"),
            ("S", "O", "SPACE"),
        )
        active = sequence[int((now - self.started_at) / 0.65) % len(sequence)]
        if key_id in active:
            return True
        return bool(self.selected_keys) and key_id == self.selected_keys[
            int((now - self.started_at) / 0.65) % len(self.selected_keys)
        ]

    def _tick(self) -> None:
        now = time.monotonic()
        gamepad_connected, gamepad_state = (
            read_gamepad_state() if self.display_mode == "gamepad" and not self.demo else (False, {})
        )
        for key_id in self._visible_input_ids():
            if self.demo:
                active = self._demo_key_state(key_id, now)
            elif self.display_mode == "gamepad":
                active = gamepad_state.get(key_id, False)
            else:
                active = is_key_down(KEY_DEFINITIONS[key_id][1])
            if active != self.key_state[key_id]:
                self.key_state[key_id] = active
                self._set_key_visual(key_id, active)

        if self.display_mode == "gamepad" and hasattr(self, "status_text"):
            if self.click_through:
                self._update_status_text()
            else:
                status = "手柄已连接" if (gamepad_connected or self.demo) else "等待手柄"
                self.canvas.itemconfigure(
                    self.status_text,
                    text=f"{status}  ·  拖动  ·  F8 隐藏  ·  F9 穿透  ·  F10 设置",
                    fill="#7DDC9B" if (gamepad_connected or self.demo) else self.MUTED,
                )

        self._poll_hotkey("F8", 0x77, self.toggle_visible)
        self._poll_hotkey("F9", 0x78, self.toggle_click_through)
        self._poll_hotkey("F10", 0x79, self.open_settings)
        self._poll_hotkey("F11", 0x7A, self.toggle_clean_mode)

        if now - self.last_layer_order_check >= 0.12:
            self.last_layer_order_check = now
            self._ensure_layer_order()

        if now - self.last_process_check >= 1.5:
            self.last_process_check = now
            self.game_process_id = find_game_process_id()
            self._refresh_game_status()
        self.root.after(16, self._tick)

    def _poll_hotkey(self, name: str, vk_code: int, command: Any) -> None:
        active = is_key_down(vk_code)
        if active and not self.hotkey_state[name]:
            command()
        self.hotkey_state[name] = active

    def _refresh_game_status(self) -> None:
        _shape, label = self.launch_button
        if self.game_process_id:
            self.canvas.itemconfigure(label, text="●  游戏运行中", fill="#A5F0BA")
            self.canvas.itemconfigure(self.running_text, text="● 已连接", fill="#7DDC9B")
        else:
            self.canvas.itemconfigure(label, text="▶  启动游戏", fill="#FFE28A")
            self.canvas.itemconfigure(self.running_text, text="● 就绪", fill="#7DDC9B")

    def launch_game(self) -> None:
        if self.game_process_id and focus_process_window(self.game_process_id):
            return
        game_exe = resolve_game_exe(self.settings.get("game_path"))
        try:
            os.startfile(f"steam://rungameid/{STEAM_APP_ID}")
            self.canvas.itemconfigure(self.running_text, text="● 正在启动", fill="#FFD66B")
            return
        except OSError:
            pass
        if game_exe:
            try:
                subprocess.Popen([str(game_exe)], cwd=str(game_exe.parent))
                self.canvas.itemconfigure(self.running_text, text="● 正在启动", fill="#FFD66B")
                return
            except OSError as exc:
                messagebox.showerror(APP_NAME, f"无法启动游戏：\n{exc}")
                return
        if messagebox.askyesno(APP_NAME, "没有找到 LostCastle2.exe，是否现在手动定位？"):
            self.choose_game_path()

    def choose_game_path(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 LostCastle2.exe",
            filetypes=(("Lost Castle 2", "LostCastle2.exe"), ("可执行文件", "*.exe")),
        )
        if not path:
            return
        if Path(path).name.casefold() != "lostcastle2.exe":
            messagebox.showwarning(APP_NAME, "请选择游戏目录中的 LostCastle2.exe。")
            return
        self.settings["game_path"] = path
        self._save_current_settings()

    def _settings_control_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Any,
        *,
        accent: bool = False,
        width: int = 10,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#3A3018" if accent else "#20252D",
            fg="#FFE28A" if accent else self.TEXT,
            activebackground="#514322" if accent else "#2C333E",
            activeforeground=self.TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            width=width,
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "bold"),
        )

    def _settings_checkbutton(
        self,
        parent: tk.Misc,
        text: str,
        variable: tk.BooleanVar,
        command: Any,
    ) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            bg="#171B21",
            fg=self.TEXT,
            activebackground="#171B21",
            activeforeground=self.TEXT,
            selectcolor="#3A3018",
            highlightthickness=0,
            bd=0,
            padx=2,
            pady=4,
            font=("Microsoft YaHei UI", 10),
            cursor="hand2",
        )

    def open_settings(self) -> None:
        if not self.visible:
            self.toggle_visible()
        if self.settings_window is not None:
            try:
                self.settings_window.deiconify()
                self.settings_window.lift()
                self.settings_window.focus_force()
                return
            except tk.TclError:
                self.settings_window = None

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title(os.environ.get("KEYVIEW_SETTINGS_TITLE", "按键显示设置"))
        window.overrideredirect(True)
        window.configure(bg=self.PANEL_OUTLINE)
        window.attributes("-topmost", True)
        try:
            window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        width = min(730, window.winfo_screenwidth() - 40)
        height = min(900, window.winfo_screenheight() - 40)
        x = max(20, (window.winfo_screenwidth() - width) // 2)
        y = max(20, (window.winfo_screenheight() - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

        shell = tk.Frame(window, bg="#11151A", padx=18, pady=14)
        shell.pack(fill="both", expand=True, padx=1, pady=1)
        header = tk.Frame(shell, bg="#11151A", height=48)
        header.pack(fill="x")
        title = tk.Label(
            header,
            text="显示设置",
            bg="#11151A",
            fg=self.TEXT,
            font=("Microsoft YaHei UI", 17, "bold"),
        )
        title.pack(side="left")
        subtitle = tk.Label(
            header,
            text=f"  KEY VIEW  ·  v{APP_VERSION}",
            bg="#11151A",
            fg=self.MUTED,
            font=("Segoe UI", 9, "bold"),
        )
        subtitle.pack(side="left", pady=(7, 0))
        close_button = self._settings_control_button(
            header, "×", self._close_settings, width=2
        )
        close_button.pack(side="right")

        drag_state: dict[str, tuple[int, int, int, int] | None] = {"origin": None}

        def begin_drag(event: tk.Event[Any]) -> None:
            drag_state["origin"] = (
                event.x_root,
                event.y_root,
                window.winfo_x(),
                window.winfo_y(),
            )

        def drag(event: tk.Event[Any]) -> None:
            origin = drag_state["origin"]
            if origin is None:
                return
            start_x, start_y, window_x, window_y = origin
            window.geometry(
                f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}"
            )

        for widget in (header, title, subtitle):
            widget.bind("<ButtonPress-1>", begin_drag)
            widget.bind("<B1-Motion>", drag)

        body_host = tk.Frame(shell, bg="#11151A")
        body_host.pack(fill="both", expand=True, pady=(10, 0))
        body_canvas = tk.Canvas(
            body_host,
            bg="#11151A",
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        scrollbar_style = ttk.Style(window)
        scrollbar_style.theme_use("clam")
        scrollbar_style.configure(
            "KeyView.Vertical.TScrollbar",
            troughcolor="#11151A",
            background="#343C47",
            bordercolor="#11151A",
            lightcolor="#343C47",
            darkcolor="#343C47",
            arrowcolor="#AAB4C2",
            gripcount=0,
            arrowsize=10,
        )
        scrollbar_style.map(
            "KeyView.Vertical.TScrollbar",
            background=[("active", "#4A5563"), ("pressed", "#596575")],
        )
        body_scrollbar = ttk.Scrollbar(
            body_host,
            orient="vertical",
            command=body_canvas.yview,
            style="KeyView.Vertical.TScrollbar",
        )
        body_canvas.configure(yscrollcommand=body_scrollbar.set)
        body_scrollbar.pack(side="right", fill="y", padx=(8, 0))
        body_canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(body_canvas, bg="#11151A")
        body_window = body_canvas.create_window(0, 0, anchor="nw", window=body)

        def sync_body_scrollregion(_event: tk.Event[Any] | None = None) -> None:
            body_canvas.configure(scrollregion=body_canvas.bbox("all"))

        def fit_body_width(event: tk.Event[Any]) -> None:
            body_canvas.itemconfigure(body_window, width=event.width)

        def scroll_body(event: tk.Event[Any]) -> str:
            if event.delta:
                body_canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"

        body.bind("<Configure>", sync_body_scrollregion)
        body_canvas.bind("<Configure>", fit_body_width)
        window.bind("<MouseWheel>", scroll_body)

        appearance = tk.Frame(body, bg="#171B21", padx=14, pady=10)
        appearance.pack(fill="x", pady=(10, 10))
        tk.Label(
            appearance,
            text="外观与窗口",
            bg="#171B21",
            fg="#FFE28A",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))

        self.settings_vars = {
            "show_background": tk.BooleanVar(value=self.show_background),
            "key_only": tk.BooleanVar(value=self.key_only),
            "always_on_top": tk.BooleanVar(value=self.always_on_top),
            "click_through": tk.BooleanVar(value=self.click_through),
            "background_opacity": tk.DoubleVar(value=round(self.background_opacity * 100)),
            "ui_scale": tk.DoubleVar(value=round(self.ui_scale * 100)),
        }
        checks = (
            ("显示背景", "show_background"),
            ("纯净模式", "key_only"),
            ("始终置顶", "always_on_top"),
            ("鼠标穿透", "click_through"),
        )
        for column, (text, key) in enumerate(checks):
            self._settings_checkbutton(
                appearance,
                text,
                self.settings_vars[key],  # type: ignore[arg-type]
                self._apply_appearance_settings,
            ).grid(row=1, column=column, sticky="w", padx=(0, 18))

        tk.Label(
            appearance,
            text="背景透明度",
            bg="#171B21",
            fg=self.TEXT,
            font=("Microsoft YaHei UI", 10),
        ).grid(row=2, column=0, sticky="w", pady=(9, 0))
        self.background_opacity_value = tk.Label(
            appearance,
            text=f"{round(self.background_opacity * 100)}%",
            bg="#171B21",
            fg="#FFE28A",
            font=("Segoe UI", 10, "bold"),
            width=5,
        )
        self.background_opacity_value.grid(row=2, column=3, sticky="e", pady=(9, 0))
        opacity_scale = tk.Scale(
            appearance,
            from_=0,
            to=100,
            orient="horizontal",
            showvalue=False,
            resolution=1,
            variable=self.settings_vars["background_opacity"],
            command=self._on_background_opacity_change,
            bg="#171B21",
            fg=self.TEXT,
            troughcolor="#2C333D",
            activebackground=self.ACTIVE,
            highlightthickness=0,
            bd=0,
            sliderlength=18,
        )
        opacity_scale.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 3))
        tk.Label(
            appearance,
            text="界面缩放",
            bg="#171B21",
            fg=self.TEXT,
            font=("Microsoft YaHei UI", 10),
        ).grid(row=4, column=0, sticky="w", pady=(7, 0))
        self.ui_scale_value = tk.Label(
            appearance,
            text=f"{round(self.ui_scale * 100)}%",
            bg="#171B21",
            fg="#FFE28A",
            font=("Segoe UI", 10, "bold"),
            width=5,
        )
        self.ui_scale_value.grid(row=4, column=3, sticky="e", pady=(7, 0))
        scale_slider = tk.Scale(
            appearance,
            from_=60,
            to=180,
            orient="horizontal",
            showvalue=False,
            resolution=5,
            variable=self.settings_vars["ui_scale"],
            command=self._on_ui_scale_change,
            bg="#171B21",
            fg=self.TEXT,
            troughcolor="#2C333D",
            activebackground=self.ACTIVE,
            highlightthickness=0,
            bd=0,
            sliderlength=18,
        )
        scale_slider.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 3))
        appearance.grid_columnconfigure(2, weight=1)
        tk.Label(
            appearance,
            text="背景可完全透明；纯净模式只隐藏控件，不改变穿透（F11 返回，F9 穿透）。",
            bg="#171B21",
            fg=self.MUTED,
            font=("Microsoft YaHei UI", 8),
        ).grid(row=6, column=0, columnspan=4, sticky="w")

        theme_panel = tk.Frame(body, bg="#171B21", padx=14, pady=9)
        theme_panel.pack(fill="x", pady=(0, 10))
        theme_header = tk.Frame(theme_panel, bg="#171B21")
        theme_header.pack(fill="x", pady=(0, 6))
        tk.Label(
            theme_header,
            text="按键配色",
            bg="#171B21",
            fg="#FFE28A",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(side="left")
        tk.Label(
            theme_header,
            text="预设会同时调整按键、按下高亮和背景色",
            bg="#171B21",
            fg=self.MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")
        theme_buttons = tk.Frame(theme_panel, bg="#171B21")
        theme_buttons.pack(fill="x")
        self.theme_buttons.clear()
        for index, (preset_id, theme) in enumerate(COLOR_PRESETS.items()):
            button = tk.Button(
                theme_buttons,
                text=theme["name"],
                command=lambda current=preset_id: self._set_color_preset(current),
                bg=theme["idle"],
                fg=theme["key_text"],
                activebackground=theme["active"],
                activeforeground=theme["active_text"],
                relief="flat",
                bd=0,
                padx=8,
                pady=5,
                width=8,
                cursor="hand2",
                font=("Microsoft YaHei UI", 9, "bold"),
            )
            button.grid(
                row=index // 4,
                column=index % 4,
                sticky="ew",
                padx=(0 if index % 4 == 0 else 5, 0),
                pady=(0 if index < 4 else 5, 0),
            )
            self.theme_buttons[preset_id] = button
        self._settings_control_button(
            theme_buttons, "随机抽取", self._randomize_color_preset, width=8
        ).grid(row=1, column=3, sticky="ew", padx=(5, 0), pady=(5, 0))
        for column in range(4):
            theme_buttons.grid_columnconfigure(column, weight=1, uniform="themes")

        key_panel = tk.Frame(body, bg="#171B21", padx=14, pady=10)
        key_panel.pack(fill="both", expand=True)
        key_header = tk.Frame(key_panel, bg="#171B21")
        key_header.pack(fill="x", pady=(0, 7))
        tk.Label(
            key_header,
            text="显示按键",
            bg="#171B21",
            fg="#FFE28A",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(side="left")
        self.selected_count_label = tk.Label(
            key_header,
            text="",
            bg="#171B21",
            fg=self.MUTED,
            font=("Microsoft YaHei UI", 9),
        )
        self.selected_count_label.pack(side="right")

        presets = tk.Frame(key_panel, bg="#171B21")
        presets.pack(fill="x", pady=(0, 8))
        self._settings_control_button(
            presets,
            "失落城堡2",
            lambda: self._apply_key_preset(LOST_CASTLE_KEYS),
            accent=True,
            width=10,
        ).pack(side="left", padx=(0, 7))
        self._settings_control_button(
            presets,
            "WASD 常用",
            lambda: self._apply_key_preset(WASD_KEYS),
            width=10,
        ).pack(side="left", padx=(0, 7))
        self._settings_control_button(
            presets, "恢复默认", self._reset_visual_defaults, width=10
        ).pack(side="left")

        keys_grid = tk.Frame(key_panel, bg="#171B21")
        keys_grid.pack(fill="both", expand=True)
        row_cursor = 0
        self.key_toggle_buttons.clear()
        for group_name, key_ids in KEY_GROUPS:
            tk.Label(
                keys_grid,
                text=group_name,
                bg="#171B21",
                fg=self.MUTED,
                font=("Microsoft YaHei UI", 8, "bold"),
            ).grid(row=row_cursor, column=0, columnspan=10, sticky="w", pady=(3, 2))
            row_cursor += 1
            for index, key_id in enumerate(key_ids):
                button = tk.Button(
                    keys_grid,
                    text=KEY_DEFINITIONS[key_id][0],
                    command=lambda current=key_id: self._toggle_key_selection(current),
                    relief="flat",
                    bd=0,
                    width=6,
                    padx=0,
                    pady=1,
                    cursor="hand2",
                    font=("Segoe UI", 8, "bold"),
                )
                button.grid(
                    row=row_cursor + index // 10,
                    column=index % 10,
                    padx=2,
                    pady=1,
                    sticky="ew",
                )
                self.key_toggle_buttons[key_id] = button
            row_cursor += (len(key_ids) + 9) // 10
        for column in range(10):
            keys_grid.grid_columnconfigure(column, weight=1)

        footer = tk.Frame(shell, bg="#11151A")
        footer.pack(fill="x", pady=(10, 0))
        self.settings_status = tk.Label(
            footer,
            text="F8/F9/F10/F11 为工具快捷键，不占用显示列表。",
            bg="#11151A",
            fg=self.MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        self.settings_status.pack(side="left")
        self._settings_control_button(
            footer, "完成", self._close_settings, accent=True, width=8
        ).pack(side="right")
        self._settings_control_button(
            footer, "宏设置", self.macro_feature.open_window, width=8
        ).pack(side="right", padx=(0, 7))

        self._refresh_key_toggle_styles()
        self._refresh_theme_buttons()
        window.protocol("WM_DELETE_WINDOW", self._close_settings)
        window.bind("<Escape>", lambda _event: self._close_settings())
        window.after_idle(
            lambda: self._apply_toolwindow_style(window, click_through=False)
        )

    def _close_settings(self) -> None:
        if self.settings_window is None:
            return
        try:
            self.settings_window.destroy()
        except tk.TclError:
            pass
        self.settings_window = None
        self.settings_vars.clear()
        self.key_toggle_buttons.clear()
        self.theme_buttons.clear()

    def _on_background_opacity_change(self, value: str) -> None:
        self.background_opacity = min(1.0, max(0.0, float(value) / 100.0))
        if hasattr(self, "background_opacity_value"):
            self.background_opacity_value.configure(
                text=f"{round(self.background_opacity * 100)}%"
            )
        self._sync_background_layer()
        self._save_current_settings()

    def _on_ui_scale_change(self, value: str) -> None:
        self._set_ui_scale(float(value) / 100.0)

    def _set_color_preset(self, preset_id: str, *, save: bool = True) -> None:
        if preset_id not in COLOR_PRESETS:
            return
        self.color_preset = preset_id
        self._apply_theme_values()
        self.background_canvas.itemconfigure(
            "background-panel", fill=self.BG, outline=self.PANEL_OUTLINE
        )
        for key_id in self.key_items:
            self._set_key_visual(key_id, self.key_state.get(key_id, False))
        self._refresh_key_toggle_styles()
        self._refresh_theme_buttons()
        if save:
            self._save_current_settings()

    def _randomize_color_preset(self) -> None:
        choices = [key for key in COLOR_PRESETS if key != self.color_preset]
        self._set_color_preset(random.choice(choices or list(COLOR_PRESETS)))

    def _refresh_theme_buttons(self) -> None:
        for preset_id, button in self.theme_buttons.items():
            theme = COLOR_PRESETS[preset_id]
            selected = preset_id == self.color_preset
            button.configure(
                bg=theme["active"] if selected else theme["idle"],
                fg=theme["active_text"] if selected else theme["key_text"],
                relief="solid" if selected else "flat",
                bd=2 if selected else 0,
            )

    def _apply_appearance_settings(self) -> None:
        if not self.settings_vars:
            return
        self.show_background = bool(self.settings_vars["show_background"].get())
        next_key_only = bool(self.settings_vars["key_only"].get())
        next_topmost = bool(self.settings_vars["always_on_top"].get())
        next_click_through = bool(self.settings_vars["click_through"].get())
        key_only_changed = next_key_only != self.key_only
        if next_topmost != self.always_on_top:
            self._set_topmost(next_topmost)
        if key_only_changed:
            self._set_clean_mode(next_key_only, save=False)
        elif next_click_through != self.click_through:
            self._set_click_through(next_click_through)
        if not key_only_changed:
            self._sync_background_layer()
        self._save_current_settings()

    def _toggle_key_selection(self, key_id: str) -> None:
        if key_id in self.selected_keys:
            if len(self.selected_keys) == 1:
                self.settings_status.configure(
                    text="至少保留一个显示按键。", fg=self.DANGER
                )
                return
            self.selected_keys.remove(key_id)
        else:
            if len(self.selected_keys) >= MAX_DISPLAY_KEYS:
                self.settings_status.configure(
                    text=f"最多同时显示 {MAX_DISPLAY_KEYS} 个按键。", fg=self.DANGER
                )
                return
            self.selected_keys.append(key_id)
        self.settings_status.configure(
            text="选择已实时应用；F8/F9/F10/F11 为工具快捷键。", fg=self.MUTED
        )
        self._refresh_key_toggle_styles()
        self._apply_display_mode()

    def _apply_key_preset(self, keys: tuple[str, ...]) -> None:
        self.selected_keys = list(keys)
        self._refresh_key_toggle_styles()
        self._apply_display_mode()

    def _reset_visual_defaults(self) -> None:
        self.selected_keys = list(LOST_CASTLE_KEYS)
        self.show_background = True
        self.background_opacity = 0.88
        self.key_only = False
        self.display_mode = "keyboard"
        self._set_click_through(False)
        self._set_color_preset(DEFAULT_COLOR_PRESET, save=False)
        self._set_ui_scale(1.0, save=False)
        self.settings_vars["show_background"].set(True)
        self.settings_vars["key_only"].set(False)
        self.settings_vars["background_opacity"].set(88.0)
        self.settings_vars["ui_scale"].set(100.0)
        self._refresh_key_toggle_styles()
        self._apply_display_mode(save=False)
        self._sync_background_layer()
        self._save_current_settings()

    def _refresh_key_toggle_styles(self) -> None:
        selected = set(self.selected_keys)
        for key_id, button in self.key_toggle_buttons.items():
            active = key_id in selected
            button.configure(
                bg=self.ACTIVE if active else "#242A32",
                fg=self.ACTIVE_TEXT if active else self.TEXT,
                activebackground="#FFE08A" if active else "#303843",
                activeforeground=self.ACTIVE_TEXT if active else self.TEXT,
            )
        if hasattr(self, "selected_count_label"):
            self.selected_count_label.configure(
                text=f"已选择 {len(self.selected_keys)} / {MAX_DISPLAY_KEYS}"
            )

    def toggle_visible(self) -> None:
        if self.visible:
            if self.settings_window is not None:
                self._close_settings()
            self.background_window.withdraw()
            self.root.withdraw()
            self.visible = False
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", self.always_on_top)
            self.visible = True
            self._apply_window_roles()

    def _window_handle(self) -> int:
        return self._shell_hwnd(self.root)

    def _update_status_text(self) -> None:
        if self.click_through:
            text = "鼠标穿透已开启  ·  按 F9 解锁  ·  F8 显示/隐藏"
            color = "#FFD66B"
        else:
            topmost = "置顶中" if self.always_on_top else "自由窗口"
            text = f"拖动  ·  {topmost}  ·  F8 隐藏  ·  F9 穿透  ·  F10 设置  ·  F11 纯净"
            color = self.MUTED
        self.canvas.itemconfigure(self.status_text, text=text, fill=color)

    def _set_click_through(self, enabled: bool) -> None:
        self.click_through = bool(enabled)
        self._apply_toolwindow_style(self.root, click_through=self.click_through)
        self._apply_toolwindow_style(
            self.background_window,
            click_through=self.click_through,
            no_activate=self.click_through,
        )
        self._update_status_text()
        variable = self.settings_vars.get("click_through")
        if variable is not None:
            variable.set(self.click_through)

    def toggle_click_through(self) -> None:
        self._set_click_through(not self.click_through)

    def restore_interaction(self) -> None:
        if self.click_through:
            self._set_click_through(False)
        if self.key_only:
            self._set_clean_mode(False, save=False)
        if not self.visible:
            self.toggle_visible()
        self.root.lift()
        self._sync_background_layer()
        self._save_current_settings()

    def _set_clean_mode(self, enabled: bool, *, save: bool = True) -> None:
        enabled = bool(enabled)
        if enabled == self.key_only:
            return
        self.key_only = enabled
        variable = self.settings_vars.get("key_only")
        if variable is not None:
            variable.set(self.key_only)
        self._apply_display_mode(save=save)

    def toggle_clean_mode(self) -> None:
        self._set_clean_mode(not self.key_only)

    def _apply_topmost_state(self) -> None:
        self.root.attributes("-topmost", self.always_on_top)
        self.background_window.attributes("-topmost", self.always_on_top)
        if self.settings_window is not None:
            self.settings_window.attributes("-topmost", True)
        self._sync_background_layer()

    def _update_topmost_button_visual(self) -> None:
        if not hasattr(self, "topmost_button"):
            return
        shape, text = self.topmost_button
        self.canvas.itemconfigure(
            shape,
            fill="#332A13" if self.always_on_top else "#181C22",
            outline="#8E762B" if self.always_on_top else "#343B46",
        )
        self.canvas.itemconfigure(
            text, fill="#FFE28A" if self.always_on_top else self.MUTED
        )

    def _set_topmost(self, enabled: bool) -> None:
        self.always_on_top = bool(enabled)
        self._apply_topmost_state()
        self._update_topmost_button_visual()
        self._update_status_text()
        variable = self.settings_vars.get("always_on_top")
        if variable is not None:
            variable.set(self.always_on_top)
        self._save_current_settings()

    def toggle_topmost(self) -> None:
        self._set_topmost(not self.always_on_top)

    def reset_position(self) -> None:
        screen_w = self.root.winfo_screenwidth()
        scaled_width, _scaled_height = self._scaled_dimensions()
        x = (screen_w - scaled_width) // 2
        self.root.geometry(f"+{x}+90")
        self._sync_background_layer()
        self._save_current_settings()

    def _save_current_settings(self) -> None:
        self.settings.update(
            {
                "x": self.root.winfo_x(),
                "y": self.root.winfo_y(),
                "background_opacity": self.background_opacity,
                "show_background": self.show_background,
                "key_only": self.key_only,
                "selected_keys": self.selected_keys,
                "input_display_mode": self.display_mode,
                "color_preset": self.color_preset,
                "ui_scale": self.ui_scale,
                "toolbox_width": self.toolbox_width,
                "toolbox_height": self.toolbox_height,
                "toolbox_ui_scale": self.toolbox_ui_scale,
                "hud_ui_scale": self.hud_ui_scale,
                "always_on_top": self.always_on_top,
            }
        )
        try:
            save_settings(self.settings)
        except OSError:
            pass

    def close(self) -> None:
        if self._on_request_close is not None:
            self._on_request_close()
            return
        self.shutdown()

    def shutdown(self) -> None:
        self._save_current_settings()
        if self._owns_macro_feature:
            self.macro_feature.close()
        if self.settings_window is not None:
            self.settings_window.destroy()
        self.background_window.destroy()
        self.root.destroy()


def ensure_single_instance() -> int | None:
    mutex_name = os.environ.get(
        "KEYVIEW_INSTANCE_MUTEX", "Local\\LostCastle2KeyView-SingleInstance"
    )
    handle = kernel32.CreateMutexW(None, False, mutex_name)
    if not handle:
        return None
    if kernel32.GetLastError() == 183:
        user32.MessageBoxW(None, "失落城堡 2 工具箱已经在运行。", APP_NAME, 0x40)
        kernel32.CloseHandle(handle)
        return None
    return int(handle)


def parse_window_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (ValueError, AttributeError) as exception:
        raise argparse.ArgumentTypeError("窗口尺寸必须使用 WIDTHxHEIGHT") from exception
    if width < 640 or height < 480:
        raise argparse.ArgumentTypeError("窗口尺寸至少为 640x480")
    return width, height


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--demo", action="store_true", help="循环演示按键高亮")
    parser.add_argument("--show-settings", action="store_true", help="启动后打开设置")
    parser.add_argument("--show-macros", action="store_true", help="启动后打开宏设置")
    parser.add_argument("--show-keyboard", action="store_true", help="启动后同时显示按键悬浮窗")
    parser.add_argument(
        "--show-page",
        choices=("home", "combat", "keyboard", "macro", "mods", "settings"),
        default="home",
        help="开发验证：主窗口直接打开指定页面",
    )
    parser.add_argument(
        "--show-combat-hud",
        action="store_true",
        help="开发验证：启动后直接打开战斗 HUD",
    )
    parser.add_argument(
        "--demo-large-values",
        action="store_true",
        help="开发验证：演示千万级战斗数值的字号适配",
    )
    parser.add_argument(
        "--demo-scenario",
        default="MudSwamp",
        help="开发验证：战斗演示使用的游戏 Scenario 枚举名",
    )
    parser.add_argument(
        "--demo-room-index",
        type=int,
        default=4,
        choices=range(0, 102),
        metavar="0..101",
        help="开发验证：战斗演示使用的区域序号",
    )
    parser.add_argument(
        "--window-size",
        type=parse_window_size,
        help="开发验证：主窗口尺寸，例如 780x560",
    )
    parser.add_argument(
        "--tk-scaling",
        type=float,
        help="开发验证：设置 Tk 字体/控件缩放",
    )
    parser.add_argument("--start-hidden", action="store_true", help="兼容旧版；按键悬浮窗默认隐藏")
    parser.add_argument("--exit-after", type=float, default=0.0, help="若干秒后自动退出")
    parser.add_argument("--self-test", action="store_true", help="运行无界面结构检查")
    return parser.parse_args(argv)


def self_test() -> int:
    assert set(LOST_CASTLE_KEYS) == set(DEFAULT_KEY_LAYOUT)
    assert len({definition[1] for definition in KEY_DEFINITIONS.values()}) == len(
        KEY_DEFINITIONS
    )
    for key_only in (False, True):
        layout = layout_for_keys(LOST_CASTLE_KEYS, key_only=key_only)
        height = overlay_height(layout, key_only=key_only)
        for x, y, width, key_height in layout.values():
            assert x >= 0 and y >= 0
            assert x + width <= WINDOW_WIDTH
            assert y + key_height <= height
        pad_layout = gamepad_layout(key_only=key_only)
        pad_height = overlay_height(pad_layout, key_only=key_only)
        assert set(pad_layout) == set(GAMEPAD_LABELS)
        for x, y, width, key_height in pad_layout.values():
            assert x >= 0 and y >= 0
            assert x + width <= WINDOW_WIDTH
            assert y + key_height <= pad_height
    game_exe = resolve_game_exe(DEFAULT_GAME_EXE)
    print(
        json.dumps(
            {
                "app": APP_NAME,
                "version": APP_VERSION,
                "available_key_count": len(KEY_DEFINITIONS),
                "default_key_count": len(LOST_CASTLE_KEYS),
                "game_exe_found": game_exe is not None,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    enable_dpi_awareness()
    mutex = ensure_single_instance()
    if mutex is None:
        return 0
    root = tk.Tk()
    root.withdraw()
    if args.tk_scaling is not None:
        root.tk.call("tk", "scaling", max(0.75, min(2.5, args.tk_scaling)))
    macro_feature = MacroFeature(root, CONFIG_DIR)
    mod_manager = ModManager(
        ModCatalog.from_file(RESOURCE_DIR / "assets" / "mod_catalog.json"),
        CONFIG_DIR / "managed_mods",
        RESOURCE_DIR / "third_party",
    )
    keyboard_root = tk.Toplevel(root)
    keyboard_app: KeyViewApp
    keyboard_app = KeyViewApp(
        keyboard_root,
        demo=args.demo,
        macro_feature=macro_feature,
        on_request_close=lambda: (
            keyboard_app.toggle_visible() if keyboard_app.visible else None
        ),
    )
    keyboard_app.toggle_visible()
    registry = SourceRegistry.from_file(
        RESOURCE_DIR / "assets" / "combat_sources.json"
    )
    scenario_registry = ScenarioRegistry.from_file(
        RESOURCE_DIR / "assets" / "game_locations.json"
    )
    combat_aggregator = CombatAggregator(
        registry=registry,
        scenario_registry=scenario_registry,
    )
    combat_client: CombatBridgeClient | None = None
    combat_pump: CombatEventPump | None = None
    if args.demo or args.demo_large_values:
        seed_demo_combat(
            combat_aggregator,
            scale=1000 if args.demo_large_values else 1,
            scenario_id=args.demo_scenario,
            room_index=args.demo_room_index,
        )
    else:
        combat_inbox = CombatInbox()
        combat_pump = CombatEventPump(
            combat_inbox,
            CombatEventValidator.from_file(
                RESOURCE_DIR / "contracts" / "combat_event.schema.json"
            ),
            combat_aggregator,
        )
        combat_client = CombatBridgeClient(combat_inbox)
    shell: ToolboxShell | None = None
    closing = False

    def close_all() -> None:
        nonlocal closing
        if closing:
            return
        closing = True
        if combat_client is not None:
            combat_client.stop()
        if shell is not None:
            shell.close()
        keyboard_app.shutdown()
        macro_feature.close()
        try:
            root.destroy()
        except tk.TclError:
            pass

    def keyboard_preview() -> list[tuple[str, str, tuple[int, int, int, int]]]:
        return [
            (key_id, display_label(key_id), geometry)
            for key_id, geometry in keyboard_app.current_layout.items()
        ]

    shell = ToolboxShell(
        root,
        keyboard=keyboard_app,
        macro_feature=macro_feature,
        mod_manager=mod_manager,
        combat_aggregator=combat_aggregator,
        combat_event_pump=combat_pump,
        keyboard_preview_provider=keyboard_preview,
        launch_game=keyboard_app.launch_game,
        choose_game_path=keyboard_app.choose_game_path,
        close_command=close_all,
        app_version=APP_VERSION,
        persist_window_geometry=args.window_size is None,
    )
    if combat_client is not None:
        combat_client.start()
    if args.window_size is not None:
        root.geometry(f"{args.window_size[0]}x{args.window_size[1]}")
    root.deiconify()
    shell.show_page(args.show_page)
    if args.show_settings:
        root.after(250, lambda: (shell.show_page("keyboard"), keyboard_app.open_settings()))
    if args.show_macros:
        root.after(250, lambda: (shell.show_page("macro"), macro_feature.open_window()))
    if args.show_keyboard and not args.start_hidden:
        root.after(250, keyboard_app.toggle_visible)
    if args.show_combat_hud:
        root.after(250, shell.hud.show)
    if args.exit_after > 0:
        root.after(round(args.exit_after * 1000), close_all)
    try:
        root.mainloop()
    finally:
        kernel32.CloseHandle(mutex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
