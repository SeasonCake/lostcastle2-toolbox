from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import re
import time
from typing import Protocol


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", INPUT_UNION)]


VK_CODES = {
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{str(number): 0x30 + number for number in range(10)},
    **{f"F{number}": 0x6F + number for number in range(1, 13)},
    "BACK": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "SHIFT": 0x10,
    "CTRL": 0x11,
    "ALT": 0x12,
    "CAPS": 0x14,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "INS": 0x2D,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
}

MOUSE_FLAGS = {
    "LMB": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "RMB": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "MMB": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


class WindowsInputError(RuntimeError):
    pass


class HotkeyInputBackend(Protocol):
    def is_target_foreground(self) -> bool: ...

    def key_down(self, key: str) -> None: ...

    def key_up(self, key: str) -> None: ...


def parse_hotkey_chord(value: str) -> tuple[str, ...]:
    normalized = re.sub(r"\s+", "", value).upper()
    parts = tuple("INS" if part == "INSERT" else part for part in normalized.split("+"))
    if not parts or any(not part for part in parts):
        raise WindowsInputError("MOD 面板快捷键为空或格式不正确。")
    modifiers = {"CTRL", "ALT", "SHIFT"}
    if any(part not in modifiers for part in parts[:-1]) or parts[-1] in modifiers:
        raise WindowsInputError("MOD 面板快捷键格式不正确。")
    if len(set(parts)) != len(parts) or any(part not in VK_CODES for part in parts):
        raise WindowsInputError("MOD 面板快捷键不受支持。")
    return parts


def send_hotkey(
    backend: HotkeyInputBackend, value: str, *, hold_seconds: float = 0.04
) -> None:
    keys = parse_hotkey_chord(value)
    if not backend.is_target_foreground():
        raise WindowsInputError("游戏窗口未处于前台，未发送快捷键。")
    pressed: list[str] = []
    try:
        for key in keys:
            backend.key_down(key)
            pressed.append(key)
        if hold_seconds > 0:
            time.sleep(hold_seconds)
    finally:
        for key in reversed(pressed):
            backend.key_up(key)


class WindowsSendInputBackend:
    """SendInput backend restricted to one foreground executable name."""

    def __init__(self, target_exe_name: str = "LostCastle2.exe") -> None:
        self.target_exe_name = target_exe_name.casefold()
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def is_target_foreground(self) -> bool:
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return False
        process_id = wintypes.DWORD()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if not process_id.value:
            return False
        handle = self._kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value
        )
        if not handle:
            return False
        try:
            buffer = ctypes.create_unicode_buffer(32_768)
            size = wintypes.DWORD(len(buffer))
            if not self._kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(size)
            ):
                return False
            return Path(buffer.value).name.casefold() == self.target_exe_name
        finally:
            self._kernel32.CloseHandle(handle)

    def key_down(self, key: str) -> None:
        self._send(key, key_up=False)

    def key_up(self, key: str) -> None:
        self._send(key, key_up=True)

    def _send(self, key: str, *, key_up: bool) -> None:
        if key in MOUSE_FLAGS:
            flags = MOUSE_FLAGS[key][1 if key_up else 0]
            value = INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dwFlags=flags))
        else:
            virtual_key = VK_CODES.get(key)
            if virtual_key is None:
                raise WindowsInputError(f"不支持的按键：{key}")
            flags = KEYEVENTF_KEYUP if key_up else 0
            value = INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(wVk=virtual_key, dwFlags=flags),
            )
        sent = self._user32.SendInput(1, ctypes.byref(value), ctypes.sizeof(INPUT))
        if sent != 1:
            raise WindowsInputError(f"SendInput 失败：{ctypes.get_last_error()}")
