from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from .macro_model import MacroProfile, MacroProfileError, macro_profile_to_dict, parse_macro_profile


CONFIG_SCHEMA_VERSION = 1
EMERGENCY_KEY = "F12"
EMERGENCY_MODIFIERS = ("CTRL", "SHIFT")


def default_profile_data() -> list[dict[str, Any]]:
    common_limits = {
        "foreground_only": True,
        "max_runtime_ms": 60_000,
        "repeat_delay_ms": 80,
    }
    return [
        {
            "schema_version": 1,
            "id": "single-combo",
            "name": "单次连段示例",
            "enabled": False,
            "trigger": {"key": "F5", "modifiers": [], "mode": "once"},
            "limits": dict(common_limits),
            "steps": [
                {"type": "key", "key": "J", "action": "tap", "hold_ms": 50},
                {"type": "wait", "duration_ms": 80},
                {"type": "key", "key": "K", "action": "tap", "hold_ms": 50},
            ],
        },
        {
            "schema_version": 1,
            "id": "hold-repeat",
            "name": "按住连发示例",
            "enabled": False,
            "trigger": {"key": "F6", "modifiers": [], "mode": "hold_repeat"},
            "limits": dict(common_limits),
            "steps": [
                {"type": "key", "key": "J", "action": "tap", "hold_ms": 40}
            ],
        },
        {
            "schema_version": 1,
            "id": "toggle-repeat",
            "name": "开关循环示例",
            "enabled": False,
            "trigger": {"key": "F7", "modifiers": [], "mode": "toggle_repeat"},
            "limits": dict(common_limits),
            "steps": [
                {"type": "key", "key": "I", "action": "tap", "hold_ms": 40},
                {"type": "wait", "duration_ms": 120},
            ],
        },
    ]


def default_config_data() -> dict[str, Any]:
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "emergency_stop": {
            "key": EMERGENCY_KEY,
            "modifiers": list(EMERGENCY_MODIFIERS),
        },
        "profiles": default_profile_data(),
    }


def validate_profiles(profiles: Iterable[Mapping[str, Any]]) -> tuple[MacroProfile, ...]:
    parsed = tuple(parse_macro_profile(profile) for profile in profiles)
    ids: set[str] = set()
    active_chords: dict[tuple[str, tuple[str, ...]], str] = {}
    for profile in parsed:
        if profile.id in ids:
            raise MacroProfileError(f"宏 ID 重复：{profile.id}")
        ids.add(profile.id)
        if not profile.enabled:
            continue
        chord = (profile.trigger.key, tuple(sorted(profile.trigger.modifiers)))
        emergency = (EMERGENCY_KEY, tuple(sorted(EMERGENCY_MODIFIERS)))
        if chord == emergency:
            raise MacroProfileError(f"{profile.name} 占用了紧急停止键")
        existing = active_chords.get(chord)
        if existing is not None:
            raise MacroProfileError(f"{profile.name} 与 {existing} 使用相同触发键")
        active_chords[chord] = profile.name
    return parsed


def load_macro_config(path: Path) -> tuple[tuple[MacroProfile, ...], list[str]]:
    if not path.exists():
        return validate_profiles(default_profile_data()), []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exception:
        return (), [f"无法读取 macros.json：{type(exception).__name__}"]
    if not isinstance(raw, Mapping) or raw.get("schema_version") != CONFIG_SCHEMA_VERSION:
        return (), ["macros.json 版本不受支持"]
    profiles = raw.get("profiles")
    if not isinstance(profiles, list):
        return (), ["macros.json 缺少 profiles 数组"]
    parsed: list[MacroProfile] = []
    errors: list[str] = []
    for index, profile in enumerate(profiles):
        try:
            parsed.append(parse_macro_profile(profile))
        except MacroProfileError as exception:
            errors.append(f"第 {index + 1} 个宏：{exception}")
    try:
        validate_profiles(macro_profile_to_dict(profile) for profile in parsed)
    except MacroProfileError as exception:
        errors.append(str(exception))
    if errors:
        # A partially valid configuration is still shown in the editor, but no
        # profile runs until the full file passes validation.
        return tuple(parsed), errors
    return tuple(parsed), []


def save_macro_config(path: Path, profiles: Iterable[MacroProfile]) -> None:
    parsed = validate_profiles(macro_profile_to_dict(profile) for profile in profiles)
    payload = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "emergency_stop": {
            "key": EMERGENCY_KEY,
            "modifiers": list(EMERGENCY_MODIFIERS),
        },
        "profiles": [macro_profile_to_dict(profile) for profile in parsed],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
