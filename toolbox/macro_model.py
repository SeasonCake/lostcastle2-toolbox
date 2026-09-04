from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
TRIGGER_MODES = frozenset({"once", "hold_repeat", "toggle_repeat"})
MODIFIERS = frozenset({"CTRL", "ALT", "SHIFT"})
KEY_ACTIONS = frozenset({"down", "up", "tap"})
MIN_WAIT_MS = 20
MAX_WAIT_MS = 60_000
MAX_HOLD_MS = 10_000
MAX_RUNTIME_MS = 600_000
MAX_STEPS = 256


class MacroProfileError(ValueError):
    """Raised when a macro profile violates the runtime safety contract."""


@dataclass(frozen=True)
class MacroTrigger:
    key: str
    modifiers: tuple[str, ...]
    mode: str


@dataclass(frozen=True)
class MacroLimits:
    foreground_only: bool
    max_runtime_ms: int
    repeat_delay_ms: int


@dataclass(frozen=True)
class KeyStep:
    key: str
    action: str
    hold_ms: int = 40
    type: str = "key"


@dataclass(frozen=True)
class WaitStep:
    duration_ms: int
    type: str = "wait"


MacroStep = KeyStep | WaitStep


@dataclass(frozen=True)
class MacroProfile:
    schema_version: int
    id: str
    name: str
    enabled: bool
    trigger: MacroTrigger
    limits: MacroLimits
    steps: tuple[MacroStep, ...]


def normalize_key(value: Any, field: str = "key") -> str:
    if not isinstance(value, str):
        raise MacroProfileError(f"{field} 必须是字符串")
    key = value.strip().upper()
    aliases = {
        " ": "SPACE",
        "CONTROL": "CTRL",
        "ESCAPE": "ESC",
        "RETURN": "ENTER",
        "BACKSPACE": "BACK",
        "CAPSLOCK": "CAPS",
        "MOUSE1": "LMB",
        "MOUSE2": "RMB",
        "MOUSE3": "MMB",
    }
    key = aliases.get(key, key)
    if not key or len(key) > 16:
        raise MacroProfileError(f"{field} 长度必须为 1–16")
    return key


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MacroProfileError(f"{field} 必须是对象")
    return value


def _require_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MacroProfileError(f"{field} 必须是整数")
    if not minimum <= value <= maximum:
        raise MacroProfileError(f"{field} 必须在 {minimum}–{maximum} 之间")
    return value


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise MacroProfileError(f"{field} 包含未知字段：{', '.join(unknown)}")


def parse_macro_profile(data: Mapping[str, Any]) -> MacroProfile:
    data = _require_mapping(data, "profile")
    _reject_unknown(
        data,
        {"schema_version", "id", "name", "enabled", "trigger", "limits", "steps"},
        "profile",
    )

    if data.get("schema_version") != SCHEMA_VERSION:
        raise MacroProfileError(f"schema_version 必须为 {SCHEMA_VERSION}")

    profile_id = data.get("id")
    if not isinstance(profile_id, str) or not profile_id or len(profile_id) > 64:
        raise MacroProfileError("id 长度必须为 1–64")
    if not profile_id[0].isalnum() or any(
        not (character.islower() or character.isdigit() or character in "_-")
        for character in profile_id
    ):
        raise MacroProfileError("id 只能使用小写字母、数字、下划线和短横线")

    name = data.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64:
        raise MacroProfileError("name 长度必须为 1–64")
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise MacroProfileError("enabled 必须是布尔值")

    trigger_data = _require_mapping(data.get("trigger"), "trigger")
    _reject_unknown(trigger_data, {"key", "modifiers", "mode"}, "trigger")
    mode = trigger_data.get("mode")
    if mode not in TRIGGER_MODES:
        raise MacroProfileError("trigger.mode 不受支持")
    modifiers_data = trigger_data.get("modifiers")
    if not isinstance(modifiers_data, Sequence) or isinstance(modifiers_data, (str, bytes)):
        raise MacroProfileError("trigger.modifiers 必须是数组")
    modifiers: list[str] = []
    for value in modifiers_data:
        modifier = normalize_key(value, "trigger.modifiers")
        if modifier not in MODIFIERS:
            raise MacroProfileError(f"不支持的修饰键：{modifier}")
        if modifier in modifiers:
            raise MacroProfileError(f"修饰键重复：{modifier}")
        modifiers.append(modifier)

    limits_data = _require_mapping(data.get("limits"), "limits")
    _reject_unknown(
        limits_data,
        {"foreground_only", "max_runtime_ms", "repeat_delay_ms"},
        "limits",
    )
    if limits_data.get("foreground_only") is not True:
        raise MacroProfileError("foreground_only 必须为 true")
    limits = MacroLimits(
        foreground_only=True,
        max_runtime_ms=_require_int(
            limits_data.get("max_runtime_ms"), "limits.max_runtime_ms", 100, MAX_RUNTIME_MS
        ),
        repeat_delay_ms=_require_int(
            limits_data.get("repeat_delay_ms"),
            "limits.repeat_delay_ms",
            MIN_WAIT_MS,
            MAX_WAIT_MS,
        ),
    )

    steps_data = data.get("steps")
    if not isinstance(steps_data, Sequence) or isinstance(steps_data, (str, bytes)):
        raise MacroProfileError("steps 必须是数组")
    if len(steps_data) > MAX_STEPS:
        raise MacroProfileError(f"steps 数量不能超过 {MAX_STEPS}")
    if enabled and not steps_data:
        raise MacroProfileError("启用的宏至少需要 1 个动作步骤")
    steps: list[MacroStep] = []
    for index, raw_step in enumerate(steps_data):
        step_data = _require_mapping(raw_step, f"steps[{index}]")
        step_type = step_data.get("type")
        if step_type == "key":
            _reject_unknown(step_data, {"type", "key", "action", "hold_ms"}, f"steps[{index}]")
            action = step_data.get("action")
            if action not in KEY_ACTIONS:
                raise MacroProfileError(f"steps[{index}].action 不受支持")
            hold_ms = step_data.get("hold_ms") if action == "tap" else 40
            if action != "tap" and "hold_ms" in step_data:
                raise MacroProfileError(f"steps[{index}].hold_ms 只适用于 tap")
            steps.append(
                KeyStep(
                    key=normalize_key(step_data.get("key"), f"steps[{index}].key"),
                    action=action,
                    hold_ms=_require_int(hold_ms, f"steps[{index}].hold_ms", MIN_WAIT_MS, MAX_HOLD_MS),
                )
            )
        elif step_type == "wait":
            _reject_unknown(step_data, {"type", "duration_ms"}, f"steps[{index}]")
            steps.append(
                WaitStep(
                    duration_ms=_require_int(
                        step_data.get("duration_ms"),
                        f"steps[{index}].duration_ms",
                        MIN_WAIT_MS,
                        MAX_WAIT_MS,
                    )
                )
            )
        else:
            raise MacroProfileError(f"steps[{index}].type 不受支持")

    return MacroProfile(
        schema_version=SCHEMA_VERSION,
        id=profile_id,
        name=name.strip(),
        enabled=enabled,
        trigger=MacroTrigger(
            key=normalize_key(trigger_data.get("key"), "trigger.key"),
            modifiers=tuple(modifiers),
            mode=mode,
        ),
        limits=limits,
        steps=tuple(steps),
    )


def macro_profile_to_dict(profile: MacroProfile) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for step in profile.steps:
        if isinstance(step, KeyStep):
            item: dict[str, Any] = {
                "type": "key",
                "key": step.key,
                "action": step.action,
            }
            if step.action == "tap":
                item["hold_ms"] = step.hold_ms
            steps.append(item)
        else:
            steps.append({"type": "wait", "duration_ms": step.duration_ms})
    return {
        "schema_version": profile.schema_version,
        "id": profile.id,
        "name": profile.name,
        "enabled": profile.enabled,
        "trigger": {
            "key": profile.trigger.key,
            "modifiers": list(profile.trigger.modifiers),
            "mode": profile.trigger.mode,
        },
        "limits": {
            "foreground_only": profile.limits.foreground_only,
            "max_runtime_ms": profile.limits.max_runtime_ms,
            "repeat_delay_ms": profile.limits.repeat_delay_ms,
        },
        "steps": steps,
    }
