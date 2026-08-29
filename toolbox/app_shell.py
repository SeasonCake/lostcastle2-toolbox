from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Iterable, Mapping, Protocol
import webbrowser

from .combat_aggregator import CombatAggregator, CombatSnapshot
from .combat_transport import CombatEventPump
from .macro_model import MacroProfile
from .mod_manager import (
    ModConflictError,
    ModGamePathRequired,
    ModIntegrityError,
    ModManager,
    ModManagerError,
)
from .mod_inspector import ModDraft, ModInspectionError, ModPackageInspector
from .user_mod_registry import UserModRegistry, UserModRegistryError, draft_fingerprint


BG = "#F3EEE3"
SURFACE = "#FBF9F4"
SIDEBAR = "#E9E1D4"
BORDER = "#D7CAB7"
TEXT = "#292725"
MUTED = "#7F766B"
ACCENT = "#D86F4C"
ACCENT_HOVER = "#C86040"
GREEN = "#397B64"
RED = "#C34B37"
BLUE = "#3F739A"
GOLD = "#B4790D"
HUD_TRANSPARENT = "#010203"
TOOLBOX_AUTHOR = "加菲_barista"
TOOLBOX_REPOSITORY_URL = "https://github.com/SeasonCake/lostcastle2-toolbox"
TOOLBOX_BILIBILI_URL = "https://space.bilibili.com/88048665?"
HUD_LEFT_MOD_CLEARANCE = 500
SUPPORT_LABEL = "投喂"
SUPPORT_TITLE = "一起为热爱投喂猫罐头"
SUPPORT_NOTE = (
    "我们都是因为喜欢《失落城堡2》聚在这里。愿意支持加菲、顺便催催更新的话，"
    "可以自愿投喂一点猫罐头。"
)
SUPPORT_QR_FILENAME = "微信赞助码.png"
TAKEN_DAMAGE_LABEL = "受击承伤"
COMBAT_ROUNDING_HINT = "法力按底层小数累计，界面最终取整；与逐次整数相加可能有少量差异。"

TOOLBOX_WINDOW_PRESETS = {
    "compact": (840, 650),
    "standard": (1000, 720),
    "spacious": (1280, 900),
}
TOOLBOX_UI_SCALES = {
    "compact": 0.9,
    "standard": 1.0,
    "spacious": 1.15,
}
DEFAULT_TOOLBOX_WINDOW_PRESET = "spacious"


MODE_SHORT_LABELS = {
    "once": "单次",
    "hold_repeat": "按住循环",
    "toggle_repeat": "开关循环",
}


def toolbox_author_label() -> str:
    return f"作者：{TOOLBOX_AUTHOR}"


def combat_hud_initial_position(
    screen_width: int,
    screen_height: int,
    hud_width: int,
    hud_height: int,
    *,
    ui_scale: float = 1.0,
) -> tuple[int, int]:
    """Return a visible top-left first-run position in Tk screen coordinates."""

    margin = max(10, round(16 * min(1.25, max(0.85, float(ui_scale)))))
    maximum_x = max(0, int(screen_width) - int(hud_width) - margin)
    return (
        min(max(margin, HUD_LEFT_MOD_CLEARANCE), maximum_x),
        min(margin, max(0, int(screen_height) - int(hud_height))),
    )


def mod_tree_column_widths(available_width: int) -> dict[str, int]:
    """Allocate readable MOD columns without letting author/version run together."""

    total = max(420, int(available_width))
    version = 76
    status = 82
    author = min(220, max(136, round(total * 0.24)))
    name = max(126, total - version - author - status)
    return {
        "name": name,
        "version": version,
        "author": author,
        "status": status,
    }


@dataclass(frozen=True)
class ModLaunchAction:
    kind: str
    label: str
    enabled: bool


def mod_launch_action(
    operation: Any,
    *,
    installed: bool,
    busy: bool,
    game_process_id: int | None,
    game_started_ns: int | None,
    installed_mtime_ns: int | None,
) -> ModLaunchAction:
    if operation.launchable:
        return ModLaunchAction("launch_external", "启动", installed and not busy)
    if not operation.has_game_panel:
        return ModLaunchAction("launch_game", "启动游戏", installed and not busy)
    if not installed:
        return ModLaunchAction("install_required", "打开 MOD 面板", not busy)
    if game_process_id is None:
        return ModLaunchAction("launch_game", "启动游戏", not busy)
    if (
        game_started_ns is None
        or installed_mtime_ns is None
        or installed_mtime_ns >= game_started_ns
    ):
        return ModLaunchAction("restart_game", "需重启游戏", not busy)
    return ModLaunchAction("open_panel", "打开 MOD 面板", not busy)


def combat_state_label(state: str, *, compact: bool = False) -> str:
    labels = {
        "live": ("● 实时", "● 实时记录中"),
        "connecting": ("● 连接中", "● 正在连接战斗桥接"),
        "stale": ("● 延迟", "● 战斗桥接响应延迟"),
        "error": ("● 异常", "● 战斗数据异常，本轮统计已停止"),
        "ended": ("● 已结束", "● 本轮战斗已结束"),
        "disconnected": ("● 等待数据", "● 等待战斗桥接数据"),
    }
    short, full = labels.get(state, labels["disconnected"])
    return short if compact else full


def combat_state_color(state: str) -> str:
    if state == "live":
        return GREEN
    if state == "error":
        return RED
    if state == "stale":
        return GOLD
    return MUTED


def clamp_main_window_size(
    width: int,
    height: int,
    *,
    screen_width: int,
    screen_height: int,
    tk_scaling: float,
) -> tuple[int, int]:
    minimum_width, minimum_height = main_window_min_size(tk_scaling)
    maximum_width = max(minimum_width, screen_width - 80)
    maximum_height = max(minimum_height, screen_height - 80)
    return (
        min(maximum_width, max(minimum_width, int(width))),
        min(maximum_height, max(minimum_height, int(height))),
    )


class KeyboardModule(Protocol):
    visible: bool
    selected_keys: list[str]
    display_mode: str
    color_preset: str
    ui_scale: float
    background_opacity: float
    click_through: bool
    key_only: bool
    game_process_id: int | None
    game_process_started_ns: int | None
    toolbox_window_size: tuple[int, int]
    toolbox_ui_scale: float
    hud_ui_scale: float

    def toggle_visible(self) -> None: ...

    def open_settings(self) -> None: ...

    def set_ui_scale(self, value: float) -> None: ...

    def restore_interaction(self) -> None: ...

    def set_display_mode(self, mode: str) -> None: ...

    def set_toolbox_window_size(self, width: int, height: int) -> None: ...

    def set_toolbox_ui_scale(self, value: float) -> None: ...

    def set_hud_ui_scale(self, value: float) -> None: ...

    def open_game_panel_hotkey(self, hotkey: str) -> bool: ...


class MacroModule(Protocol):
    profiles: tuple[MacroProfile, ...]
    errors: list[str]

    def open_window(self) -> None: ...

    @property
    def controller(self) -> Any: ...


@dataclass(frozen=True)
class MacroRow:
    enabled_label: str
    name: str
    trigger: str
    mode: str
    steps: int
    description: str


def format_trigger(profile: MacroProfile) -> str:
    parts = (*profile.trigger.modifiers, profile.trigger.key)
    return " + ".join(parts)


def macro_rows(profiles: Iterable[MacroProfile]) -> tuple[MacroRow, ...]:
    rows: list[MacroRow] = []
    for profile in profiles:
        trigger = format_trigger(profile)
        mode = MODE_SHORT_LABELS.get(profile.trigger.mode, profile.trigger.mode)
        enabled = "已启用" if profile.enabled else "已停用"
        rows.append(
            MacroRow(
                enabled_label=enabled,
                name=profile.name,
                trigger=trigger,
                mode=mode,
                steps=len(profile.steps),
                description=(
                    f"{profile.name} · {enabled} · {trigger} · {mode} · "
                    f"{len(profile.steps)} 个步骤 · 最长 {profile.limits.max_runtime_ms} ms"
                ),
            )
        )
    return tuple(rows)


def ordered_keyboard_keys(
    items: Iterable[tuple[str, str, tuple[int, int, int, int]]]
) -> tuple[str, ...]:
    """Return labels in physical row/column order, independent of selection order."""

    return tuple(
        label
        for _key_id, label, _geometry in sorted(
            items,
            key=lambda item: (
                item[2][1],
                item[2][0],
                item[0],
            ),
        )
    )


def format_metric(value: float | int) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return f"{int(numeric):,}"
    return f"{numeric:,.1f}".rstrip("0").rstrip(".")


def format_whole_metric(value: float | int) -> str:
    """Format player-visible resource values using the game's integer presentation."""

    numeric = max(0.0, float(value))
    return f"{int(numeric + 0.5):,}"


def format_room_area(room_index: int | None) -> str | None:
    if room_index is None:
        return None
    special = {
        0: "入口",
        99: "首领前区域",
        100: "BOSS 区域",
        101: "准备区",
    }
    return special.get(room_index, f"第 {room_index} 区")


def format_location_label(snapshot: CombatSnapshot) -> str:
    scenario = snapshot.current_scenario_label
    area = format_room_area(snapshot.current_room_index)
    if scenario and area:
        return f"{scenario} · {area}"
    if scenario:
        return scenario
    if area:
        return area
    return "尚未进入地图"


def format_stage_location(snapshot: CombatSnapshot) -> str:
    location = format_location_label(snapshot)
    if snapshot.current_stage_level is None or snapshot.current_stage_level <= 0:
        return location
    return f"第 {snapshot.current_stage_level} 阶段 · {location}"


def boss_damage_share(total_damage: float | int, boss_damage: float | int) -> float:
    """Return a safe 0..1 composition ratio for the HUD damage bar."""

    total = float(total_damage)
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, float(boss_damage) / total))


def combat_hud_size(
    tk_scaling: float,
    ui_scale: float = 1.0,
    *,
    player_count: int = 1,
) -> tuple[int, int]:
    """Keep the compact HUD readable when Windows uses high-DPI fonts."""

    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    scale = min(1.25, max(0.85, float(ui_scale)))
    teammate_column_width = 0
    if int(player_count) >= 2:
        teammate_column_width = round((230 + 20 * high_dpi) * scale)
    height_gain = 160 if int(player_count) >= 2 else 84
    return (
        round((350 + 40 * high_dpi) * scale) + teammate_column_width,
        round((474 + height_gain * high_dpi) * scale),
    )


def hud_panel_height(
    base_height: int,
    tk_scaling: float,
    *,
    high_dpi_gain: int = 12,
) -> int:
    """Reserve enough card height for high-DPI label baselines."""

    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    return int(base_height) + round(high_dpi_gain * high_dpi)


def main_window_min_size(tk_scaling: float) -> tuple[int, int]:
    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    return 780 + round(840 * high_dpi), 700 + round(280 * high_dpi)


def main_metric_card_height(tk_scaling: float) -> int:
    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    return 133 + round(36 * high_dpi)


def main_team_panel_height(tk_scaling: float) -> int:
    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    return 115 + round(36 * high_dpi)


def hud_teammate_card_height(tk_scaling: float) -> int:
    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    return 150 + round(56 * high_dpi)


def combat_table_numeric_width(tk_scaling: float, ui_scale: float = 1.0) -> int:
    high_dpi = max(0.0, min(1.0, float(tk_scaling) - 1.5))
    base_width = 90 + round(30 * high_dpi)
    return round(base_width * max(1.0, min(1.15, float(ui_scale))))


def combat_table_source_width(tk_scaling: float) -> int:
    high_dpi = max(0.0, min(1.0, (float(tk_scaling) - 1.25) / 0.75))
    return 110 + round(22 * high_dpi)


def metric_font_size(
    text: str,
    *,
    base_size: int,
    characters_at_base: int,
    minimum_size: int = 10,
) -> int:
    visible_length = max(1, len(text))
    if visible_length <= characters_at_base:
        return base_size
    return max(
        minimum_size,
        min(base_size, int(base_size * characters_at_base / visible_length)),
    )


def _set_metric_label(
    label: tk.Label,
    text: str,
    *,
    base_size: int,
    characters_at_base: int,
    minimum_size: int = 10,
) -> None:
    available_width = int(label.winfo_width()) - 6
    if available_width > 20:
        # Once Tk has laid the label out, use the actual pixel width. Starting
        # from the preferred size avoids making wide HUDs look unnecessarily
        # small merely because a formatted number contains separators.
        size = base_size
        measured_font = tkfont.Font(
            root=label,
            family="Segoe UI",
            size=size,
            weight="bold",
        )
        while size > minimum_size and measured_font.measure(text) > available_width:
            size -= 1
            measured_font.configure(size=size)
    else:
        # The first refresh can happen before geometry propagation. Keep a
        # deterministic length-based fallback until a real width is available.
        size = metric_font_size(
            text,
            base_size=base_size,
            characters_at_base=characters_at_base,
            minimum_size=minimum_size,
        )
    label.configure(text=text, font=("Segoe UI", size, "bold"))


def _set_fitting_text(
    label: tk.Label,
    text: str,
    *,
    base_size: int = 8,
    minimum_size: int = 6,
) -> None:
    size = base_size
    available_width = int(label.winfo_width()) - 6
    if available_width > 20:
        measured_font = tkfont.Font(
            root=label,
            family="Microsoft YaHei UI",
            size=size,
        )
        while size > minimum_size and measured_font.measure(text) > available_width:
            size -= 1
            measured_font.configure(size=size)
    elif len(text) > 12:
        size = max(minimum_size, base_size - 1)
    # Location identity is operational data. Keep the complete scenario/area
    # text visible; the recent card reserves a dedicated column for it below.
    label.configure(text=text, font=("Microsoft YaHei UI", size))


def combat_team_rows(
    snapshot: CombatSnapshot,
    *,
    maximum: int = 4,
) -> list[tuple[str, int, int, float]]:
    """Return active privacy-safe party rows in stable display order."""

    rows: list[tuple[str, int, int, float]] = []
    for values in snapshot.player_breakdown.values():
        if not values.get("active", False):
            continue
        rows.append(
            (
                str(values.get("label") or "队友"),
                int(values.get("damage_dealt") or 0),
                int(values.get("boss_damage") or 0),
                max(0.0, min(1.0, float(values.get("damage_share") or 0.0))),
            )
        )
        if len(rows) >= max(1, int(maximum)):
            break
    return rows


def combat_teammate_rows(
    snapshot: CombatSnapshot,
) -> list[tuple[str, int, int, float]]:
    """Return only active remote players for the HUD side cards."""

    rows: list[tuple[str, int, int, float]] = []
    for values in snapshot.player_breakdown.values():
        if not values.get("active", False) or values.get("is_local", False):
            continue
        rows.append(
            (
                str(values.get("label") or f"队友 {len(rows) + 1}"),
                int(values.get("damage_dealt") or 0),
                int(values.get("boss_damage") or 0),
                max(0.0, min(1.0, float(values.get("damage_share") or 0.0))),
            )
        )
        if len(rows) >= 3:
            break
    return rows


def seed_demo_combat(
    aggregator: CombatAggregator,
    *,
    scale: int = 1,
    scenario_id: str = "MudSwamp",
    room_index: int = 4,
    party_size: int = 1,
) -> None:
    """Load deterministic synthetic data for visual QA; never used in normal mode."""

    if scale <= 0:
        raise ValueError("scale must be positive")
    if not scenario_id:
        raise ValueError("scenario_id must not be empty")
    if not 0 <= room_index <= 101:
        raise ValueError("room_index must be between 0 and 101")
    if not 1 <= party_size <= 4:
        raise ValueError("party_size must be between 1 and 4")

    scenario = aggregator.scenario_registry.resolve(scenario_id)
    stage_level = scenario.stage_level if scenario.stage_level is not None else 0
    map_file_name = f"Demo_{scenario_id}_{room_index}"

    common: dict[str, Any] = {
        "schema_version": 2,
        "session_id": "demo-session",
        "room_id": f"L{stage_level}:{scenario_id}:{room_index}:{map_file_name}",
        "stage_level": stage_level,
        "scenario_id": scenario_id,
        "room_index": room_index,
        "map_file_name": map_file_name,
        "aggregate": True,
        "hook_path": "demo.fixture",
    }
    sequence = 0

    def ingest(event_type: str, **values: Any) -> None:
        nonlocal sequence
        event = {
            **common,
            "event_id": f"demo-session:{sequence}",
            "event_type": event_type,
            "sequence": sequence,
            "monotonic_ms": sequence * 500,
            **values,
        }
        aggregator.ingest(event)
        sequence += 1

    ingest("status", status="session_started")
    ingest("status", status="room_started")
    ingest(
        "status",
        status="party_updated",
        aggregate=False,
        party_members=[
            {
                "player_id": f"demo-player-{index + 1}",
                "player_slot": index,
                "is_local": index == 0,
            }
            for index in range(party_size)
        ],
    )
    for damage_index, (damage, source, is_boss) in enumerate((
        (18_760 * scale, "combat.player.normal", False),
        (8_940 * scale, "combat.player.element", True),
        (480 * scale, "combat.player.element", False),
        (6_148 * scale, "combat.summon", False),
    )):
        ingest(
            "damage_resolution",
            damage_direction="dealt",
            settlement_damage=damage,
            applied_hp_damage=damage,
            mitigated_damage=0,
            overkill_damage=0,
            damage_outcome="applied",
            is_boss=is_boss,
            source_token=source,
            owner_player_id=f"demo-player-{damage_index % party_size + 1}",
        )
    ingest(
        "damage_resolution",
        damage_direction="taken",
        settlement_damage=264 * scale,
        applied_hp_damage=183 * scale,
        mitigated_damage=63 * scale,
        overkill_damage=0,
        damage_outcome="applied",
        is_boss=False,
        source_token="enemy.damage",
    )
    for resource, delta, source, overflow in (
        ("hp", -18 * scale, "resource.self_damage", 0),
        ("hp", 32 * scale, "ExhaustProps#Banana_0", 4 * scale),
        ("hp", 62 * scale, "Gem#A_015_2", 0),
        ("mp", -168 * scale, "resource.skill_cost", 0),
        ("mp", 140 * scale, "resource.mana_recovery", 0),
    ):
        ingest(
            "resource_change",
            resource=resource,
            effective_delta=delta,
            blocked=False,
            overflow=overflow,
            source_token=source,
        )


class RoundedPanel(tk.Canvas):
    """Small dependency-free rounded surface shared by the toolbox and HUD."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        fill: str = SURFACE,
        outline: str = BORDER,
        radius: int = 12,
        height: int | None = 76,
        content_padx: int = 10,
        content_pady: int = 8,
    ) -> None:
        parent_bg = str(parent.cget("bg"))
        super().__init__(
            parent,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            height=height or 1,
        )
        self._fill = fill
        self._outline = outline
        self._radius = radius
        self._inset = max(6, radius // 2)
        self._auto_height = height is None
        self.content = tk.Frame(
            self,
            bg=fill,
            padx=content_padx,
            pady=content_pady,
        )
        self._content_window = self.create_window(
            self._inset,
            self._inset,
            anchor="nw",
            window=self.content,
            tags=("content",),
        )
        self.bind("<Configure>", self._redraw)
        if self._auto_height:
            self.content.bind("<Configure>", self._resize_to_content)

    def _resize_to_content(self, _event: tk.Event[Any] | None = None) -> None:
        target = max(2, self.content.winfo_reqheight() + self._inset * 2)
        if int(float(self.cget("height"))) != target:
            self.configure(height=target)

    def _redraw(self, event: tk.Event[Any]) -> None:
        width = max(2, int(event.width))
        height = max(2, int(event.height))
        radius = min(self._radius, width // 2, height // 2)
        self.delete("surface")
        points = (
            radius,
            1,
            radius,
            1,
            width - radius,
            1,
            width - radius,
            1,
            width - 1,
            1,
            width - 1,
            radius,
            width - 1,
            height - radius,
            width - 1,
            height - 1,
            width - radius,
            height - 1,
            radius,
            height - 1,
            1,
            height - 1,
            1,
            height - radius,
            1,
            radius,
            1,
            1,
            radius,
            1,
        )
        surface = self.create_polygon(
            points,
            smooth=True,
            splinesteps=24,
            fill=self._fill,
            outline=self._outline,
            width=1,
            tags=("surface",),
        )
        self.tag_lower(surface)
        self.coords(self._content_window, self._inset, self._inset)
        dimensions: dict[str, int] = {
            "width": max(1, width - self._inset * 2),
        }
        if not self._auto_height:
            dimensions["height"] = max(1, height - self._inset * 2)
        self.itemconfigure(self._content_window, **dimensions)
        if self._auto_height:
            self.after_idle(self._resize_to_content)


class CombatHudWindow:
    """Compact B-style readout; all values come from the shared aggregator."""

    def __init__(
        self,
        owner: tk.Misc,
        aggregator: CombatAggregator,
        *,
        ui_scale: float = 1.0,
    ) -> None:
        self.owner = owner
        self.aggregator = aggregator
        self.window: tk.Toplevel | None = None
        self.labels: dict[str, tk.Label] = {}
        self._drag_origin: tuple[int, int, int, int] | None = None
        self._boss_share = 0.0
        self.boss_share_bar: tk.Canvas | None = None
        self.panels: dict[str, RoundedPanel] = {}
        self.team_side_host: tk.Frame | None = None
        self.teammate_panels: list[RoundedPanel] = []
        self.teammate_labels: list[
            tuple[tk.Label, tk.Label, tk.Label, tk.Label]
        ] = []
        self.teammate_bars: list[tk.Canvas] = []
        self._teammate_shares = [0.0, 0.0, 0.0]
        self._team_visible = False
        self._last_player_count = 1
        self._tk_scaling = 1.5
        self.ui_scale = min(1.25, max(0.85, float(ui_scale)))

    def _px(self, value: int) -> int:
        return max(1, round(value * self.ui_scale))

    def _font(self, family: str, size: int, weight: str = "normal") -> tuple[str, int, str]:
        return family, max(6, round(size * self.ui_scale)), weight

    def set_ui_scale(self, value: float) -> None:
        next_scale = round(min(1.25, max(0.85, float(value))) / 0.05) * 0.05
        if abs(next_scale - self.ui_scale) < 0.001:
            self.show()
            return
        position: tuple[int, int] | None = None
        was_visible = False
        if self.window is not None:
            try:
                position = (self.window.winfo_x(), self.window.winfo_y())
                was_visible = self.window.state() != "withdrawn"
            except tk.TclError:
                position = None
            self.close()
        self.ui_scale = next_scale
        if was_visible:
            self.show()
            if self.window is not None and position is not None:
                width, height = combat_hud_size(
                    self._tk_scaling,
                    self.ui_scale,
                    player_count=self._last_player_count,
                )
                x = min(
                    max(0, position[0]),
                    max(0, self.window.winfo_screenwidth() - width),
                )
                y = min(
                    max(0, position[1]),
                    max(0, self.window.winfo_screenheight() - height),
                )
                self.window.geometry(f"+{x}+{y}")

    def show(self) -> None:
        if self.window is not None:
            try:
                self.window.deiconify()
                self.window.lift()
                return
            except tk.TclError:
                self.window = None
        window = tk.Toplevel(self.owner)
        self.window = window
        self._tk_scaling = float(window.tk.call("tk", "scaling"))
        window.title("LC2 战斗 HUD")
        window.configure(bg=HUD_TRANSPARENT)
        window.geometry(self._initial_geometry(window))
        window.minsize(self._px(330), self._px(380))
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        try:
            window.attributes("-toolwindow", True)
            window.attributes("-transparentcolor", HUD_TRANSPARENT)
        except tk.TclError:
            pass

        self.panels.clear()
        self.teammate_panels.clear()
        self.teammate_labels.clear()
        self.teammate_bars.clear()
        self._team_visible = False
        self._last_player_count = 1
        layout = tk.Frame(window, bg=HUD_TRANSPARENT)
        layout.pack(fill="both", expand=True)
        base_width, base_height = combat_hud_size(
            self._tk_scaling,
            self.ui_scale,
            player_count=1,
        )
        left_host = tk.Frame(
            layout,
            bg=HUD_TRANSPARENT,
            width=base_width,
            height=base_height,
        )
        left_host.pack(side="left", fill="y")
        left_host.pack_propagate(False)

        outer = RoundedPanel(
            left_host,
            fill="#F8F4EB",
            outline="#E9DED0",
            radius=self._px(18),
            height=self._px(400),
            content_padx=0,
            content_pady=0,
        )
        outer.pack(fill="both", expand=True)
        surface = outer.content
        header = tk.Frame(surface, bg="#F8F4EB", padx=self._px(10), pady=self._px(7))
        header.pack(fill="x")
        title_label = tk.Label(
            header,
            text="LC2 战斗",
            bg="#F8F4EB",
            fg=TEXT,
            font=self._font("Microsoft YaHei UI", 11, "bold"),
        )
        title_label.pack(side="left")
        self.labels["hud_status"] = tk.Label(
            header,
            text="● 等待数据",
            bg="#F8F4EB",
            fg=MUTED,
            font=self._font("Microsoft YaHei UI", 9),
        )
        self.labels["hud_status"].pack(side="left", padx=(self._px(10), 0))
        tk.Button(
            header,
            text="隐藏",
            command=window.withdraw,
            bg="#EEE5D8",
            fg=MUTED,
            activebackground="#E4D8C7",
            relief="flat",
            bd=0,
            padx=self._px(9),
            pady=self._px(3),
            cursor="hand2",
            font=self._font("Microsoft YaHei UI", 9),
        ).pack(side="right")
        for widget in (header, title_label, self.labels["hud_status"]):
            widget.bind("<ButtonPress-1>", self._begin_drag)
            widget.bind("<B1-Motion>", self._drag_window)

        body = tk.Frame(surface, bg="#F8F4EB", padx=self._px(5), pady=self._px(5))
        body.pack(fill="both", expand=True)
        self._build_damage_group(body)
        self._build_resource_group(body)
        self._build_recent_group(body)
        self._build_teammate_side(layout)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        # Commit the single-player geometry before a demo/live party snapshot
        # expands only the transparent window surface to the right.
        window.update_idletasks()
        self.refresh()

    def _begin_drag(self, event: tk.Event[Any]) -> None:
        if self.window is None:
            return
        self._drag_origin = (
            event.x_root,
            event.y_root,
            self.window.winfo_x(),
            self.window.winfo_y(),
        )

    def _drag_window(self, event: tk.Event[Any]) -> None:
        if self.window is None or self._drag_origin is None:
            return
        start_x, start_y, window_x, window_y = self._drag_origin
        self.window.geometry(
            f"+{window_x + event.x_root - start_x}+{window_y + event.y_root - start_y}"
        )

    def _hud_panel(
        self,
        parent: tk.Frame,
        *,
        height: int,
        high_dpi_gain: int = 12,
        panel_key: str | None = None,
    ) -> tk.Frame:
        panel = RoundedPanel(
            parent,
            fill="#FCFAF6",
            outline="#EFE5D8",
            radius=14,
            height=self._px(
                hud_panel_height(
                    height,
                    self._tk_scaling,
                    high_dpi_gain=high_dpi_gain,
                )
            ),
            content_padx=self._px(10),
            content_pady=self._px(7),
        )
        panel.pack(fill="x", pady=(0, self._px(5)))
        if panel_key is not None:
            self.panels[panel_key] = panel
        return panel.content

    def _build_damage_group(self, parent: tk.Frame) -> None:
        cell = self._hud_panel(parent, height=126, panel_key="damage")
        tk.Frame(cell, bg=GOLD, height=self._px(2)).pack(
            fill="x", pady=(0, self._px(5))
        )
        self.boss_share_bar = tk.Canvas(
            cell,
            bg="#FCFAF6",
            height=self._px(8),
            highlightthickness=0,
            bd=0,
        )
        # Reserve the composition bar first; the expanding number columns may
        # then use only the space that truly remains at every DPI.
        self.boss_share_bar.pack(side="bottom", fill="x", pady=(self._px(8), 0))
        self.boss_share_bar.bind("<Configure>", self._draw_boss_share)
        columns = tk.Frame(cell, bg="#FCFAF6")
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=1, uniform="damage")
        columns.grid_columnconfigure(1, weight=1, uniform="damage")
        total = tk.Frame(columns, bg="#FCFAF6")
        total.grid(row=0, column=0, sticky="nsew", padx=(0, self._px(6)))
        tk.Label(
            total,
            text="总伤害",
            bg="#FCFAF6",
            fg=MUTED,
            anchor="w",
            font=self._font("Microsoft YaHei UI", 9),
        ).pack(fill="x")
        self.labels["damage"] = tk.Label(
            total,
            text="—",
            bg="#FCFAF6",
            fg=GOLD,
            anchor="w",
            font=self._font("Segoe UI", 19, "bold"),
        )
        self.labels["damage"].pack(fill="x", pady=(self._px(1), self._px(5)))
        boss = tk.Frame(columns, bg="#FCFAF6", padx=self._px(8))
        boss.grid(row=0, column=1, sticky="nsew", padx=(self._px(6), 0))
        tk.Label(
            boss,
            text="BOSS 伤害",
            bg="#FCFAF6",
            fg=RED,
            anchor="e",
            font=self._font("Microsoft YaHei UI", 9, "bold"),
        ).pack(fill="x")
        self.labels["boss"] = tk.Label(
            boss,
            text="—",
            bg="#FCFAF6",
            fg=RED,
            anchor="e",
            font=self._font("Segoe UI", 16, "bold"),
        )
        self.labels["boss"].pack(fill="x", pady=(0, self._px(5)))

    def _build_teammate_side(self, parent: tk.Frame) -> None:
        full_width, _ = combat_hud_size(
            self._tk_scaling,
            self.ui_scale,
            player_count=2,
        )
        base_width, _ = combat_hud_size(
            self._tk_scaling,
            self.ui_scale,
            player_count=1,
        )
        host = tk.Frame(
            parent,
            bg=HUD_TRANSPARENT,
            width=max(self._px(210), full_width - base_width),
            padx=self._px(8),
        )
        host.pack_propagate(False)
        self.team_side_host = host
        card_height = self._px(hud_teammate_card_height(self._tk_scaling))
        for index in range(3):
            panel = RoundedPanel(
                host,
                fill="#FCFAF6",
                outline="#E9DED0",
                radius=self._px(14),
                height=card_height,
                content_padx=self._px(10),
                content_pady=self._px(7),
            )
            cell = panel.content
            name = tk.Label(
                cell,
                text=f"队友 {index + 1}",
                bg="#FCFAF6",
                fg=TEXT,
                anchor="w",
                font=self._font("Microsoft YaHei UI", 10, "bold"),
            )
            name.pack(fill="x")
            damage = tk.Label(
                cell,
                text="0",
                bg="#FCFAF6",
                fg=GOLD,
                anchor="w",
                font=self._font("Segoe UI", 14, "bold"),
            )
            damage.pack(fill="x", pady=(self._px(2), 0))
            share = tk.Label(
                cell,
                text="队伍占比 0%",
                bg="#FCFAF6",
                fg=MUTED,
                anchor="w",
                font=self._font("Microsoft YaHei UI", 8),
            )
            share.pack(fill="x")
            bar = tk.Canvas(
                cell,
                bg="#FCFAF6",
                height=self._px(8),
                highlightthickness=0,
                bd=0,
            )
            bar.pack(fill="x", pady=(self._px(3), self._px(3)))
            bar.bind(
                "<Configure>",
                lambda _event, bar_index=index: self._draw_teammate_share(bar_index),
            )
            boss = tk.Label(
                cell,
                text="Boss 0",
                bg="#FCFAF6",
                fg=RED,
                anchor="w",
                font=self._font("Microsoft YaHei UI", 9),
            )
            boss.pack(fill="x")
            self.teammate_panels.append(panel)
            self.teammate_labels.append((name, damage, share, boss))
            self.teammate_bars.append(bar)

    def _draw_boss_share(self, _event: tk.Event[Any] | None = None) -> None:
        bar = self.boss_share_bar
        if bar is None:
            return
        width = max(1, bar.winfo_width())
        height = max(1, bar.winfo_height())
        left, right = 4, max(4, width - 4)
        y = height / 2
        bar.delete("all")
        # The full gold track is total damage; the red segment is the subset
        # dealt to bosses. Colours match the two figures directly above it.
        bar.create_line(
            left,
            y,
            right,
            y,
            fill="#D8B76F",
            width=self._px(6),
            capstyle=tk.ROUND,
        )
        if self._boss_share > 0:
            boss_left = right - (right - left) * self._boss_share
            bar.create_line(
                boss_left,
                y,
                right,
                y,
                fill=RED,
                width=self._px(6),
                capstyle=tk.ROUND,
            )

    def _draw_teammate_share(self, index: int) -> None:
        if not 0 <= index < len(self.teammate_bars):
            return
        bar = self.teammate_bars[index]
        width = max(1, bar.winfo_width())
        height = max(1, bar.winfo_height())
        left, right = 4, max(4, width - 4)
        y = height / 2
        share = max(0.0, min(1.0, self._teammate_shares[index]))
        bar.delete("all")
        bar.create_line(
            left,
            y,
            right,
            y,
            fill="#E4D8C7",
            width=self._px(6),
            capstyle=tk.ROUND,
        )
        if share > 0:
            bar.create_line(
                left,
                y,
                left + (right - left) * share,
                y,
                fill=GOLD,
                width=self._px(6),
                capstyle=tk.ROUND,
            )

    def _build_resource_group(self, parent: tk.Frame) -> None:
        cell = self._hud_panel(parent, height=152, panel_key="resource")
        columns = tk.Frame(cell, bg="#FCFAF6")
        columns.pack(fill="both", expand=True)
        for column in range(3):
            columns.grid_columnconfigure(column, weight=1 if column != 1 else 0)
        hp = tk.Frame(columns, bg="#FCFAF6")
        hp.grid(row=0, column=0, sticky="nsew", padx=(0, self._px(8)))
        tk.Frame(hp, bg=RED, height=self._px(2)).pack(
            fill="x", pady=(0, self._px(5))
        )
        tk.Label(
            hp,
            text=TAKEN_DAMAGE_LABEL,
            bg="#FCFAF6",
            fg=MUTED,
            anchor="w",
            font=self._font("Microsoft YaHei UI", 9),
        ).pack(fill="x")
        self.labels["hp_loss"] = tk.Label(
            hp,
            text="—",
            bg="#FCFAF6",
            fg=RED,
            anchor="w",
            font=self._font("Segoe UI", 17, "bold"),
        )
        self.labels["hp_loss"].pack(fill="x")
        self.labels["healing"] = tk.Label(
            hp,
            text="回复 +0",
            bg="#FCFAF6",
            fg=GREEN,
            anchor="w",
            font=self._font("Microsoft YaHei UI", 9),
        )
        self.labels["healing"].pack(fill="x")
        tk.Frame(columns, bg="#E9DED0", width=self._px(1)).grid(
            row=0, column=1, sticky="ns"
        )
        mp = tk.Frame(columns, bg="#FCFAF6")
        mp.grid(row=0, column=2, sticky="nsew", padx=(self._px(8), 0))
        tk.Frame(mp, bg=BLUE, height=self._px(2)).pack(
            fill="x", pady=(0, self._px(5))
        )
        tk.Label(
            mp,
            text="法力消耗",
            bg="#FCFAF6",
            fg=MUTED,
            anchor="w",
            font=self._font("Microsoft YaHei UI", 9),
        ).pack(fill="x")
        self.labels["mp_spent"] = tk.Label(
            mp,
            text="—",
            bg="#FCFAF6",
            fg=BLUE,
            anchor="w",
            font=self._font("Segoe UI", 17, "bold"),
        )
        self.labels["mp_spent"].pack(fill="x")
        self.labels["mp_gained"] = tk.Label(
            mp,
            text="恢复 +0",
            bg="#FCFAF6",
            fg=BLUE,
            anchor="w",
            font=self._font("Microsoft YaHei UI", 9),
        )
        self.labels["mp_gained"].pack(fill="x")

    def _build_recent_group(self, parent: tk.Frame) -> None:
        cell = self._hud_panel(
            parent,
            height=114,
            high_dpi_gain=34,
            panel_key="recent",
        )
        tk.Frame(cell, bg=GREEN, height=self._px(2)).pack(
            fill="x", pady=(0, self._px(4))
        )
        row = tk.Frame(cell, bg="#FCFAF6")
        row.pack(fill="both", expand=True)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0, minsize=self._px(150))
        row.grid_rowconfigure(0, weight=1)
        copy = tk.Frame(row, bg="#FCFAF6")
        copy.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            copy,
            text="近 10 秒平均秒伤",
            bg="#FCFAF6",
            fg=MUTED,
            anchor="w",
            font=self._font("Microsoft YaHei UI", 9),
        ).pack(fill="x")
        self.labels["dps"] = tk.Label(
            copy,
            text="—",
            bg="#FCFAF6",
            fg=GREEN,
            anchor="w",
            font=self._font("Segoe UI", 16, "bold"),
        )
        self.labels["dps"].pack(fill="x")
        self.labels["room"] = tk.Label(
            row,
            text="尚未进入地图",
            bg="#FCFAF6",
            fg=MUTED,
            anchor="e",
            font=self._font("Microsoft YaHei UI", 9),
        )
        self.labels["room"].grid(
            row=0,
            column=1,
            sticky="e",
            padx=(self._px(8), 0),
        )

    def refresh(self) -> None:
        if self.window is None:
            return
        try:
            snapshot = self.aggregator.snapshot()
            self.labels["hud_status"].configure(
                text=combat_state_label(snapshot.connection_state, compact=True),
                fg=combat_state_color(snapshot.connection_state),
            )
            _set_metric_label(
                self.labels["damage"],
                format_metric(snapshot.total_damage),
                base_size=max(8, round(19 * self.ui_scale)),
                characters_at_base=7,
            )
            _set_metric_label(
                self.labels["boss"],
                format_metric(snapshot.boss_damage),
                base_size=max(8, round(16 * self.ui_scale)),
                characters_at_base=6,
            )
            self._boss_share = boss_damage_share(
                snapshot.total_damage,
                snapshot.boss_damage,
            )
            self._draw_boss_share()
            _set_metric_label(
                self.labels["hp_loss"],
                format_whole_metric(snapshot.taken_settlement_damage),
                base_size=max(8, round(17 * self.ui_scale)),
                characters_at_base=7,
            )
            self.labels["healing"].configure(
                text=f"回复 +{format_whole_metric(snapshot.effective_healing)}"
            )
            _set_metric_label(
                self.labels["mp_spent"],
                format_whole_metric(snapshot.mp_spent),
                base_size=max(8, round(17 * self.ui_scale)),
                characters_at_base=7,
            )
            self.labels["mp_gained"].configure(
                text=f"恢复 +{format_whole_metric(snapshot.mp_gained)}"
            )
            _set_metric_label(
                self.labels["dps"],
                format_metric(snapshot.recent_dps),
                base_size=max(8, round(16 * self.ui_scale)),
                characters_at_base=9,
            )
            _set_fitting_text(
                self.labels["room"],
                format_location_label(snapshot),
                base_size=max(8, round(9 * self.ui_scale)),
                minimum_size=max(7, round(7 * self.ui_scale)),
            )
            self._refresh_team(snapshot)
        except tk.TclError:
            self.window = None

    def _refresh_team(self, snapshot: CombatSnapshot) -> None:
        rows = combat_teammate_rows(snapshot)
        player_count = 1 + len(rows)
        visible = bool(rows)
        if visible != self._team_visible:
            self._team_visible = visible
            self._last_player_count = player_count if visible else 1
            if self.team_side_host is not None:
                if visible:
                    self.team_side_host.pack(side="left", fill="y")
                else:
                    self.team_side_host.pack_forget()
            self._resize_for_party()
        elif visible:
            self._last_player_count = player_count

        for index, panel in enumerate(self.teammate_panels):
            if visible and index < len(rows):
                label, damage, boss, share = rows[index]
                name_label, damage_label, share_label, boss_label = self.teammate_labels[index]
                name_label.configure(text=label)
                _set_metric_label(
                    damage_label,
                    format_metric(damage),
                    base_size=max(8, round(14 * self.ui_scale)),
                    characters_at_base=10,
                    minimum_size=max(7, round(9 * self.ui_scale)),
                )
                share_label.configure(text=f"队伍占比 {round(share * 100)}%")
                boss_label.configure(text=f"Boss {format_metric(boss)}")
                self._teammate_shares[index] = share
                panel.pack(fill="x", pady=(0, self._px(5)))
                self._draw_teammate_share(index)
            else:
                self._teammate_shares[index] = 0.0
                panel.pack_forget()

    def _resize_for_party(self) -> None:
        if self.window is None:
            return
        width, height = combat_hud_size(
            self._tk_scaling,
            self.ui_scale,
            player_count=self._last_player_count,
        )
        x = min(
            max(0, self.window.winfo_x()),
            max(0, self.window.winfo_screenwidth() - width),
        )
        y = min(
            max(0, self.window.winfo_y()),
            max(0, self.window.winfo_screenheight() - height),
        )
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def close(self) -> None:
        if self.window is not None:
            try:
                self.window.destroy()
            except tk.TclError:
                pass
        self.window = None

    def _initial_geometry(self, window: tk.Toplevel) -> str:
        # Still vertically grouped, but wide enough to keep million-scale
        # damage and resource values legible without wasting height. High-DPI
        # fonts receive only the extra pixels they need instead of a permanent
        # empty footer on lower-scale displays.
        width, height = combat_hud_size(
            float(window.tk.call("tk", "scaling")),
            self.ui_scale,
            player_count=self._last_player_count,
        )
        x, y = combat_hud_initial_position(
            window.winfo_screenwidth(),
            window.winfo_screenheight(),
            width,
            height,
            ui_scale=self.ui_scale,
        )
        return f"{width}x{height}+{x}+{y}"


class ToolboxShell:
    """Calculator-style application shell for the independent LC2 modules."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        keyboard: KeyboardModule,
        macro_feature: MacroModule,
        mod_manager: ModManager,
        mod_inspector: ModPackageInspector,
        user_mod_registry: UserModRegistry,
        mod_inbox: Path,
        support_directory: Path | None = None,
        combat_aggregator: CombatAggregator,
        combat_event_pump: CombatEventPump | None,
        keyboard_preview_provider: Callable[
            [], Iterable[tuple[str, str, tuple[int, int, int, int]]]
        ],
        launch_game: Callable[[], None],
        ensure_game_runtime: Callable[[], bool],
        choose_game_path: Callable[[], None],
        close_command: Callable[[], None],
        app_version: str,
        persist_window_geometry: bool = True,
    ) -> None:
        self.root = root
        self.keyboard = keyboard
        self.macro_feature = macro_feature
        self.mod_manager = mod_manager
        self.mod_inspector = mod_inspector
        self.user_mod_registry = user_mod_registry
        self.mod_inbox = mod_inbox.resolve()
        self.mod_help_file = self.mod_inbox.parent / "MOD自动添加说明.txt"
        self.support_directory = (
            support_directory.resolve() if support_directory is not None else None
        )
        self.combat_aggregator = combat_aggregator
        self.combat_event_pump = combat_event_pump
        self.keyboard_preview_provider = keyboard_preview_provider
        self.launch_game = launch_game
        self.ensure_game_runtime = ensure_game_runtime
        self.choose_game_path = choose_game_path
        self.close_command = close_command
        self.app_version = app_version
        self.persist_window_geometry = persist_window_geometry
        self.main_ui_scale = min(1.15, max(0.9, float(keyboard.toolbox_ui_scale)))
        self.hud = CombatHudWindow(
            root,
            combat_aggregator,
            ui_scale=keyboard.hud_ui_scale,
        )
        self.pages: dict[str, tk.Frame] = {}
        self.nav_buttons: dict[str, tk.Button] = {}
        self.labels: dict[str, tk.Label] = {}
        self._macro_row_descriptions: list[str] = []
        self.mod_buttons: dict[str, dict[str, tk.Button]] = {}
        self.mod_tree: ttk.Treeview | None = None
        self.mod_search_var = tk.StringVar(value="")
        self.mod_selected_id: str | None = None
        self.mod_detail_labels: dict[str, tk.Label] = {}
        self.mod_action_buttons: dict[str, tk.Button] = {}
        self.input_mode_buttons: dict[str, tk.Button] = {}
        self.combat_team_panel: RoundedPanel | None = None
        self.combat_detail_panel: RoundedPanel | None = None
        self.combat_team_cells: list[tk.Frame] = []
        self.combat_team_labels: list[tuple[tk.Label, tk.Label, tk.Label]] = []
        self.combat_team_bars: list[tk.Canvas] = []
        self._combat_team_shares = [0.0, 0.0, 0.0, 0.0]
        self._mod_busy = False
        self._mod_results: queue.Queue[tuple[bool, Exception | None]] = queue.Queue()
        self._mod_import_results: queue.Queue[
            tuple[list[ModDraft], list[tuple[str, str]]]
        ] = queue.Queue()
        self._after_id: str | None = None
        self._support_hide_after_id: str | None = None
        self._support_popup: tk.Toplevel | None = None
        self._support_qr_image: tk.PhotoImage | None = None
        self._support_button: tk.Button | None = None
        self._closed = False
        self._main_roots: list[tk.Misc] = []
        self._main_font_bases: dict[tk.Misc, tuple[str, int, str, str]] = {}
        self._main_padding_bases: dict[tuple[tk.Misc, str], int] = {}
        self._main_panel_height_bases: dict[RoundedPanel, int] = {}

        root.title("失落城堡 2 工具箱")
        root.configure(bg=BG)
        root.geometry(self._initial_geometry(root, *keyboard.toolbox_window_size))
        root.minsize(*main_window_min_size(float(root.tk.call("tk", "scaling"))))
        root.protocol("WM_DELETE_WINDOW", close_command)
        self._configure_tree_style()
        self._build()
        self._capture_main_ui_bases()
        self._apply_main_ui_scale()
        self.show_page("home")
        self.refresh()
        self._after_id = root.after(500, self._tick)

    def _configure_tree_style(self) -> None:
        scale = self.main_ui_scale
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Toolbox.Treeview",
            background=SURFACE,
            fieldbackground=SURFACE,
            foreground=TEXT,
            rowheight=round(30 * scale),
            bordercolor=BORDER,
            font=("Microsoft YaHei UI", max(7, round(9 * scale))),
        )
        style.configure(
            "Toolbox.Treeview.Heading",
            background=SIDEBAR,
            foreground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", max(7, round(8 * scale)), "bold"),
        )
        style.map(
            "Toolbox.Treeview",
            background=[("selected", "#E4D6C4")],
            foreground=[("selected", TEXT)],
        )

    @staticmethod
    def _walk_widgets(root: tk.Misc) -> Iterable[tk.Misc]:
        yield root
        for child in root.winfo_children():
            yield from ToolboxShell._walk_widgets(child)

    def _capture_main_ui_bases(self) -> None:
        self._main_font_bases.clear()
        self._main_padding_bases.clear()
        self._main_panel_height_bases.clear()
        for root in self._main_roots:
            for widget in self._walk_widgets(root):
                try:
                    font_value = widget.cget("font")
                    if font_value:
                        font = tkfont.Font(root=self.root, font=font_value)
                        self._main_font_bases[widget] = (
                            str(font.actual("family")),
                            abs(int(font.actual("size"))),
                            str(font.actual("weight")),
                            str(font.actual("slant")),
                        )
                except (KeyError, tk.TclError, TypeError, ValueError):
                    pass
                for option in ("padx", "pady"):
                    try:
                        value = int(float(widget.cget(option)))
                    except (KeyError, tk.TclError, TypeError, ValueError):
                        continue
                    self._main_padding_bases[(widget, option)] = value
                if isinstance(widget, RoundedPanel) and not widget._auto_height:
                    self._main_panel_height_bases[widget] = int(float(widget.cget("height")))

    def _apply_main_ui_scale(self) -> None:
        scale = self.main_ui_scale
        for widget, (family, size, weight, slant) in list(self._main_font_bases.items()):
            try:
                widget.configure(
                    font=(family, max(6, round(size * scale)), weight, slant)
                )
            except tk.TclError:
                pass
        for (widget, option), base in list(self._main_padding_bases.items()):
            try:
                widget.configure(**{option: round(base * scale)})
            except tk.TclError:
                pass
        for panel, base_height in list(self._main_panel_height_bases.items()):
            try:
                # Compact mode may reduce typography and padding, but fixed data
                # cards keep their proven baseline height so secondary lines are
                # never squeezed below their requested font geometry.
                panel.configure(height=round(base_height * max(1.0, scale)))
            except tk.TclError:
                pass
        self.sidebar.configure(width=round(150 * scale))
        self._configure_tree_style()
        self.root.update_idletasks()

    def _build(self) -> None:
        header = tk.Frame(self.root, bg="#F8F4EB", padx=20, pady=14)
        header.pack(fill="x")
        self._main_roots.append(header)
        title = tk.Frame(header, bg="#F8F4EB")
        title.pack(side="left", fill="x", expand=True)
        tk.Label(
            title,
            text="失落城堡 2 工具箱",
            bg="#F8F4EB",
            fg=TEXT,
            font=("Microsoft YaHei UI", 17, "bold"),
        ).pack(anchor="w")
        header_actions = tk.Frame(header, bg="#F8F4EB")
        header_actions.pack(side="right")
        self._button(
            header_actions,
            "启动游戏",
            self.launch_game,
            accent=True,
            width=10,
        ).pack(side="right")
        self.labels["app_version"] = tk.Label(
            header_actions,
            text=f"v{self.app_version}",
            bg="#F8F4EB",
            fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        )
        self.labels["app_version"].pack(side="right", padx=(0, 12))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(body, bg=SIDEBAR, width=150, padx=9, pady=12)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._main_roots.append(self.sidebar)
        for page_id, label in (
            ("home", "概览"),
            ("combat", "战斗统计"),
            ("keyboard", "按键显示"),
            ("macro", "按键宏"),
            ("mods", "MOD 管理"),
            ("settings", "设置"),
        ):
            button = tk.Button(
                self.sidebar,
                text=label,
                command=lambda target=page_id: self.show_page(target),
                bg=SIDEBAR,
                fg=TEXT,
                activebackground="#DED3C3",
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                anchor="w",
                padx=12,
                pady=9,
                cursor="hand2",
                font=("Microsoft YaHei UI", 9),
            )
            button.pack(fill="x", pady=2)
            self.nav_buttons[page_id] = button
        tk.Frame(self.sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
        self.labels["sidebar_game"] = tk.Label(
            self.sidebar,
            text="● 正在检测游戏",
            bg=SIDEBAR,
            fg=MUTED,
            anchor="w",
            justify="left",
            wraplength=126,
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["sidebar_game"].pack(fill="x", padx=6, pady=(4, 2))

        self.content = tk.Frame(body, bg=BG, padx=18, pady=16)
        self.content.pack(side="left", fill="both", expand=True)
        self._main_roots.append(self.content)
        self._build_home_page()
        self._build_combat_page()
        self._build_keyboard_page()
        self._build_macro_page()
        self._build_mod_page()
        self._build_settings_page()

        footer = tk.Frame(self.root, bg="#F8F4EB", padx=18, pady=7)
        footer.pack(fill="x")
        self._main_roots.append(footer)
        footer_meta = tk.Frame(footer, bg="#F8F4EB")
        footer_meta.pack(side="left")
        tk.Label(
            footer_meta,
            text=toolbox_author_label(),
            bg="#F8F4EB",
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(side="left")
        tk.Button(
            footer_meta,
            text="GitHub 仓库",
            command=self._open_repository,
            bg="#F8F4EB",
            fg=BLUE,
            activebackground="#EEE5D8",
            activeforeground=BLUE,
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            footer_meta,
            text="bilibili",
            command=self._open_bilibili,
            bg="#F8F4EB",
            fg="#E05A72",
            activebackground="#F4E4E7",
            activeforeground="#C8435B",
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="left", padx=(4, 0))
        self._support_button = tk.Button(
            footer_meta,
            text=SUPPORT_LABEL,
            command=self._open_support_directory,
            bg="#F8F4EB",
            fg=GOLD,
            activebackground="#F4E8CC",
            activeforeground=GOLD,
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        self._support_button.pack(side="left", padx=(4, 0))
        self._support_button.bind("<Enter>", self._show_support_popup)
        self._support_button.bind("<Leave>", self._schedule_support_popup_hide)
        tk.Button(
            footer,
            text="退出工具箱",
            command=self.close_command,
            bg="#F8F4EB",
            fg=MUTED,
            activebackground="#EEE5D8",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")
        body.pack_forget()
        footer.pack_forget()
        footer.pack(side="bottom", fill="x")
        body.pack(fill="both", expand=True)

    def _new_page(self, page_id: str) -> tk.Frame:
        page = tk.Frame(self.content, bg=BG)
        self.pages[page_id] = page
        return page

    def _page_heading(
        self,
        parent: tk.Frame,
        title: str,
        subtitle: str,
        *,
        action: tuple[str, Callable[[], None]] | None = None,
    ) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 13))
        copy = tk.Frame(row, bg=BG)
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            copy,
            text=title,
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 15, "bold"),
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                copy,
                text=subtitle,
                bg=BG,
                fg=MUTED,
                font=("Microsoft YaHei UI", 8),
            ).pack(anchor="w", pady=(3, 0))
        if action is not None:
            self._button(row, action[0], action[1], accent=True, width=12).pack(side="right")

    def _build_home_page(self) -> None:
        page = self._new_page("home")
        self._page_heading(page, "工具箱概览", "从这里打开和管理各个独立功能。")
        self._module_card(
            page,
            "战",
            "战斗统计",
            "combat_status",
            "combat_summary",
            ("查看详情", lambda: self.show_page("combat")),
            ("打开 HUD", self.hud.show),
        )
        self._module_card(
            page,
            "键",
            "按键显示",
            "keyboard_status",
            "keyboard_summary",
            ("外观设置", lambda: self.show_page("keyboard")),
            ("显示 / 隐藏", self.keyboard.toggle_visible),
        )
        self._module_card(
            page,
            "宏",
            "按键宏",
            "macro_status",
            "macro_summary",
            ("查看方案", lambda: self.show_page("macro")),
            ("编辑宏", self.macro_feature.open_window),
        )
        notice = tk.Frame(page, bg=SIDEBAR, padx=12, pady=10)
        notice.pack(fill="x", pady=(3, 0))
        tk.Label(
            notice,
            text="安全边界",
            bg=SIDEBAR,
            fg=TEXT,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            notice,
            text="宏只在 LostCastle2.exe 为前台时执行；Ctrl + Shift + F12 可随时紧急停止。",
            bg=SIDEBAR,
            fg=MUTED,
            justify="left",
            wraplength=610,
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w", pady=(4, 0))

    def _module_card(
        self,
        parent: tk.Frame,
        mark: str,
        title: str,
        status_key: str,
        summary_key: str,
        secondary_action: tuple[str, Callable[[], None]],
        primary_action: tuple[str, Callable[[], None]],
    ) -> None:
        panel = RoundedPanel(
            parent,
            height=None,
            content_padx=12,
            content_pady=10,
        )
        panel.pack(fill="x", pady=(0, 9))
        card = panel.content
        marker = tk.Label(
            card,
            text=mark,
            width=3,
            height=2,
            bg="#EEE2C7" if mark == "战" else "#DFE8EC" if mark == "键" else "#E8DFEF",
            fg=GOLD if mark == "战" else BLUE if mark == "键" else "#755895",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        marker.pack(side="left", padx=(0, 10))
        copy = tk.Frame(card, bg=SURFACE)
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            copy,
            text=title,
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(fill="x")
        self.labels[status_key] = tk.Label(
            copy,
            text="正在读取状态…",
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels[status_key].pack(fill="x", pady=(3, 0))
        self.labels[summary_key] = tk.Label(
            card,
            text="—",
            bg=SURFACE,
            fg=TEXT,
            width=36,
            anchor="e",
            justify="right",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels[summary_key].pack(side="left", padx=12)
        actions = tk.Frame(card, bg=SURFACE)
        actions.pack(side="right")
        self._button(actions, secondary_action[0], secondary_action[1], width=10).pack(
            side="left", padx=(0, 5)
        )
        self._button(
            actions,
            primary_action[0],
            primary_action[1],
            accent=True,
            width=10,
        ).pack(side="left")

    def _build_combat_page(self) -> None:
        page = self._new_page("combat")
        self._page_heading(
            page,
            "战斗统计",
            "完整详情在主窗口；游戏中只保留紧凑 HUD。",
            action=("打开紧凑 HUD", self.hud.show),
        )
        self.labels["combat_connection"] = tk.Label(
            page,
            text="● 等待战斗桥接数据",
            bg="#EEE5D8",
            fg=MUTED,
            anchor="w",
            padx=11,
            pady=8,
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        self.labels["combat_connection"].pack(fill="x", pady=(0, 9))
        cards = tk.Frame(page, bg=BG)
        cards.pack(fill="x")
        for column in range(3):
            cards.grid_columnconfigure(column, weight=1, uniform="combat")
        self._metric_card(cards, 0, "造成伤害", "combat_damage", "combat_boss", GOLD)
        self._metric_card(cards, 1, TAKEN_DAMAGE_LABEL, "combat_hp", "combat_heal", RED)
        self._metric_card(cards, 2, "法力消耗", "combat_mp", "combat_mp_gain", BLUE)
        self.labels["combat_rounding_hint"] = tk.Label(
            page,
            text=COMBAT_ROUNDING_HINT,
            bg=BG,
            fg=MUTED,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["combat_rounding_hint"].pack(fill="x", pady=(5, 0))

        team_panel = RoundedPanel(
            page,
            height=main_team_panel_height(
                float(self.root.tk.call("tk", "scaling"))
            ),
            content_padx=12,
            content_pady=6,
        )
        self.combat_team_panel = team_panel
        team = team_panel.content
        team_heading = tk.Frame(team, bg=SURFACE)
        team_heading.pack(fill="x", pady=(0, 4))
        self.labels["combat_team_heading"] = tk.Label(
            team_heading,
            text="队伍伤害",
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.labels["combat_team_heading"].pack(side="left")
        self.labels["combat_team_unattributed"] = tk.Label(
            team_heading,
            text="",
            bg=SURFACE,
            fg=MUTED,
            anchor="e",
            font=("Microsoft YaHei UI", 7),
        )
        self.labels["combat_team_unattributed"].pack(side="right")
        team_grid = tk.Frame(team, bg=SURFACE)
        team_grid.pack(fill="both", expand=True)
        for column in range(4):
            team_grid.grid_columnconfigure(column, weight=1, uniform="party")
        for index in range(4):
            player = tk.Frame(team_grid, bg=SURFACE)
            player.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0 if index == 0 else 7, 7 if index < 3 else 0),
            )
            player_heading = tk.Frame(player, bg=SURFACE)
            player_heading.pack(fill="x")
            name = tk.Label(
                player_heading,
                text="队友",
                bg=SURFACE,
                fg=TEXT,
                anchor="w",
                font=("Microsoft YaHei UI", 9, "bold"),
            )
            name.pack(side="left")
            boss = tk.Label(
                player_heading,
                text="Boss 0",
                bg=SURFACE,
                fg=RED,
                anchor="e",
                font=("Microsoft YaHei UI", 7),
            )
            boss.pack(side="right")
            damage = tk.Label(
                player,
                text="伤害 0 · 0%",
                bg=SURFACE,
                fg=GOLD,
                anchor="w",
                font=("Microsoft YaHei UI", 8),
            )
            damage.pack(fill="x")
            share_bar = tk.Canvas(
                player,
                bg=SURFACE,
                height=max(4, round(7 * self.main_ui_scale)),
                highlightthickness=0,
                bd=0,
            )
            share_bar.pack(fill="x", pady=(2, 2))
            share_bar.bind(
                "<Configure>",
                lambda _event, bar_index=index: self._draw_combat_team_share(bar_index),
            )
            self.combat_team_cells.append(player)
            self.combat_team_labels.append((name, damage, boss))
            self.combat_team_bars.append(share_bar)

        detail_panel = RoundedPanel(
            page,
            height=265,
            content_padx=12,
            content_pady=5,
        )
        self.combat_detail_panel = detail_panel
        detail_panel.pack(fill="both", expand=True, pady=(9, 0))
        detail = detail_panel.content
        heading = tk.Frame(detail, bg=SURFACE)
        heading.pack(fill="x", pady=(0, 4))
        tk.Label(
            heading,
            text="来源明细",
            bg=SURFACE,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left")
        self.labels["combat_detail_hint"] = tk.Label(
            heading,
            text="尚无事件；连接后按来源显示有效值",
            bg=SURFACE,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["combat_detail_hint"].pack(side="right")
        tree_host = tk.Frame(detail, bg=SURFACE)
        self.combat_tree = ttk.Treeview(
            tree_host,
            columns=("source", "damage", "healing", "mp_spent", "mp_gained"),
            show="headings",
            style="Toolbox.Treeview",
            # Keep a small requested height so the rows remain visible at the
            # supported minimum window size.  The packed widget still expands
            # to show more rows whenever the page has room.
            height=3,
        )
        tk_scaling = float(self.root.tk.call("tk", "scaling"))
        numeric_width = max(
            combat_table_numeric_width(tk_scaling, self.main_ui_scale),
            tkfont.Font(
                root=self.root,
                family="Microsoft YaHei UI",
                size=max(7, round(9 * self.main_ui_scale)),
            ).measure("999,999,999")
            + 18,
        )
        for column, title, width, anchor in (
            ("source", "来源", combat_table_source_width(tk_scaling), "w"),
            ("damage", "伤害", numeric_width, "e"),
            ("healing", "有效回复", numeric_width, "e"),
            ("mp_spent", "法力消耗", numeric_width, "e"),
            ("mp_gained", "法力恢复", numeric_width, "e"),
        ):
            self.combat_tree.heading(column, text=title)
            self.combat_tree.column(column, width=width, anchor=anchor, stretch=column == "source")
        combat_scrollbar = ttk.Scrollbar(
            tree_host,
            orient="vertical",
            command=self.combat_tree.yview,
        )
        self.combat_tree.configure(yscrollcommand=combat_scrollbar.set)
        self.combat_tree.pack(side="left", fill="both", expand=True)
        combat_scrollbar.pack(side="right", fill="y")
        self.labels["combat_totals"] = tk.Label(
            detail,
            text=f"{TAKEN_DAMAGE_LABEL}、实际战斗掉血、减伤与治疗溢出会分列，不互相替代。",
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["combat_totals"].pack(side="bottom", fill="x", pady=(4, 0))
        tree_host.pack(fill="both", expand=True)

    def _metric_card(
        self,
        parent: tk.Frame,
        column: int,
        title: str,
        value_key: str,
        detail_key: str,
        accent: str,
    ) -> None:
        panel = RoundedPanel(
            parent,
            height=main_metric_card_height(
                float(self.root.tk.call("tk", "scaling"))
            ),
            content_padx=11,
            content_pady=7,
        )
        panel.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 0))
        card = panel.content
        tk.Frame(card, bg=accent, height=2).pack(fill="x", pady=(0, 6))
        tk.Label(card, text=title, bg=SURFACE, fg=MUTED, anchor="w", font=("Microsoft YaHei UI", 8)).pack(fill="x")
        self.labels[value_key] = tk.Label(
            card,
            text="0",
            bg=SURFACE,
            fg=accent,
            anchor="w",
            font=("Segoe UI", 22, "bold"),
        )
        self.labels[value_key].pack(fill="x", pady=(2, 0))
        self.labels[detail_key] = tk.Label(
            card,
            text="等待数据",
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            justify="left",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels[detail_key].pack(fill="x")

    def _build_keyboard_page(self) -> None:
        page = self._new_page("keyboard")
        self._page_heading(
            page,
            "按键显示",
            "按键按设备的真实物理位置排列；可切换键盘或手柄。",
            action=("显示 / 隐藏", self.keyboard.toggle_visible),
        )
        preview_panel = RoundedPanel(
            page,
            fill="#202B35",
            outline="#526674",
            radius=14,
            height=310,
            content_padx=10,
            content_pady=9,
        )
        preview_panel.pack(fill="both", expand=True)
        preview_host = preview_panel.content
        top = tk.Frame(preview_host, bg="#202B35")
        top.pack(fill="x")
        self.labels["keyboard_page_status"] = tk.Label(
            top,
            text="● 悬浮窗已隐藏",
            bg="#202B35",
            fg="#9FB1BD",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["keyboard_page_status"].pack(side="left")
        tk.Label(
            top,
            text="半镂空预览",
            bg="#202B35",
            fg="#9FB1BD",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")
        self.keyboard_canvas = tk.Canvas(
            preview_host,
            bg="#202B35",
            highlightthickness=0,
            height=255,
        )
        self.keyboard_canvas.pack(fill="both", expand=True, pady=(5, 0))
        self.keyboard_canvas.bind("<Configure>", lambda _event: self._draw_keyboard_preview())

        controls = tk.Frame(page, bg=BG)
        controls.pack(fill="x", pady=(9, 0))
        self.labels["keyboard_page_summary"] = tk.Label(
            controls,
            text="正在读取设置…",
            bg=BG,
            fg=MUTED,
            anchor="w",
            justify="left",
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["keyboard_page_summary"].pack(side="left", fill="x", expand=True)
        self.input_mode_buttons["keyboard"] = self._button(
            controls,
            "键盘",
            lambda: self._set_input_display_mode("keyboard"),
            width=7,
        )
        self.input_mode_buttons["gamepad"] = self._button(
            controls,
            "手柄",
            lambda: self._set_input_display_mode("gamepad"),
            width=7,
        )
        self.input_mode_buttons["gamepad"].pack(side="right", padx=(5, 0))
        self.input_mode_buttons["keyboard"].pack(side="right", padx=(5, 0))
        self._button(controls, "打开完整设置", self.keyboard.open_settings, width=13).pack(
            side="right"
        )

    def _build_macro_page(self) -> None:
        page = self._new_page("macro")
        self._page_heading(
            page,
            "按键宏",
            "先看状态、触发组合和运行方式，再编辑具体步骤。",
            action=("编辑宏", self.macro_feature.open_window),
        )
        safety = tk.Frame(page, bg="#EEE2D2", padx=11, pady=8)
        safety.pack(fill="x", pady=(0, 9))
        tk.Label(
            safety,
            text="紧急停止：Ctrl + Shift + F12",
            bg="#EEE2D2",
            fg="#7A573F",
            font=("Microsoft YaHei UI", 8, "bold"),
        ).pack(side="left")
        tk.Label(
            safety,
            text="切出游戏、游戏退出或修改配置时也会停止并释放按键。",
            bg="#EEE2D2",
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")

        tree_host = tk.Frame(page, bg=BORDER, padx=1, pady=1)
        tree_host.pack(fill="both", expand=True)
        self.macro_tree = ttk.Treeview(
            tree_host,
            columns=("enabled", "name", "trigger", "mode", "steps"),
            show="headings",
            style="Toolbox.Treeview",
            height=9,
            selectmode="browse",
        )
        for column, title, width, anchor in (
            ("enabled", "状态", 70, "center"),
            ("name", "名称", 190, "w"),
            ("trigger", "触发组合", 145, "center"),
            ("mode", "运行方式", 110, "center"),
            ("steps", "步骤", 65, "center"),
        ):
            self.macro_tree.heading(column, text=title)
            self.macro_tree.column(column, width=width, anchor=anchor, stretch=column == "name")
        self.macro_tree.pack(fill="both", expand=True)
        self.macro_tree.bind("<<TreeviewSelect>>", self._show_full_macro_description)
        self.macro_tree.bind("<Double-1>", lambda _event: self.macro_feature.open_window())
        self.labels["macro_full_description"] = tk.Label(
            page,
            text="选择一个方案后，这里显示完整名称与限制。",
            bg=BG,
            fg=MUTED,
            anchor="w",
            justify="left",
            wraplength=630,
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["macro_full_description"].pack(fill="x", pady=(8, 0))
        actions = tk.Frame(page, bg=BG)
        actions.pack(fill="x", pady=(8, 0))
        self.labels["macro_page_status"] = tk.Label(
            actions,
            text="所有示例默认停用。",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        self.labels["macro_page_status"].pack(side="left")
        self._button(
            actions,
            "停止全部",
            lambda: self.macro_feature.controller.stop_all("toolbox_stop"),
            width=10,
        ).pack(side="right")

    def _build_mod_page(self) -> None:
        page = self._new_page("mods")
        self._page_heading(page, "MOD 管理", "")

        toolbar = tk.Frame(page, bg=BG)
        toolbar.pack(fill="x", pady=(0, 8))
        tk.Label(
            toolbar,
            text="搜索",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(side="left")
        search = tk.Entry(
            toolbar,
            textvariable=self.mod_search_var,
            relief="solid",
            bd=1,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            font=("Microsoft YaHei UI", 9),
        )
        self._button(toolbar, "打开目录", self._open_mod_inbox, width=9).pack(
            side="right", padx=(6, 0)
        )
        self._button(toolbar, "格式说明", self._open_mod_help, width=9).pack(
            side="right", padx=(6, 0)
        )
        self._button(toolbar, "添加 MOD", self._add_user_mod, accent=True, width=10).pack(
            side="right"
        )
        search.pack(side="left", fill="x", expand=True, padx=(6, 10), ipady=4)

        mod_content = tk.Frame(page, bg=BG)
        mod_content.pack(fill="both", expand=True)
        mod_content.columnconfigure(0, weight=1)
        mod_content.rowconfigure(0, weight=1)
        mod_content.rowconfigure(1, weight=0)
        list_panel = RoundedPanel(mod_content, height=160, content_padx=8, content_pady=8)
        list_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        list_frame = list_panel.content
        tree = ttk.Treeview(
            list_frame,
            columns=("name", "version", "author", "status"),
            show="headings",
            height=5,
            style="Toolbox.Treeview",
            selectmode="browse",
        )
        tree.heading("name", text="MOD")
        tree.heading("version", text="版本")
        tree.heading("author", text="作者")
        tree.heading("status", text="状态")
        initial_widths = mod_tree_column_widths(560)
        tree.column(
            "name", width=initial_widths["name"], minwidth=126, stretch=False, anchor="w"
        )
        tree.column(
            "version",
            width=initial_widths["version"],
            minwidth=68,
            stretch=False,
            anchor="center",
        )
        tree.column(
            "author",
            width=initial_widths["author"],
            minwidth=118,
            stretch=False,
            anchor="w",
        )
        tree.column(
            "status",
            width=initial_widths["status"],
            minwidth=72,
            stretch=False,
            anchor="center",
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        tree.bind("<<TreeviewSelect>>", self._on_mod_selected)
        tree.bind("<Configure>", self._resize_mod_tree_columns)
        self.mod_tree = tree

        detail_panel = RoundedPanel(
            mod_content,
            height=None,
            content_padx=14,
            content_pady=10,
        )
        detail_panel.grid(row=1, column=0, sticky="ew")
        detail = detail_panel.content
        top = tk.Frame(detail, bg=SURFACE)
        top.pack(fill="x")
        self.mod_detail_labels["title"] = tk.Label(
            top,
            text="请选择一个 MOD",
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 11, "bold"),
        )
        self.mod_detail_labels["title"].pack(side="left", fill="x", expand=True)
        self.mod_detail_labels["status"] = tk.Label(
            top,
            text="",
            bg=SURFACE,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        self.mod_detail_labels["status"].pack(side="right", padx=(12, 0))
        self.mod_detail_labels["author"] = tk.Label(
            detail,
            text="",
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        self.mod_detail_labels["author"].pack(fill="x", pady=(2, 0))
        self.mod_detail_labels["summary"] = tk.Label(
            detail,
            text="",
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
            justify="left",
            font=("Microsoft YaHei UI", 8),
        )
        self.mod_detail_labels["summary"].pack(fill="x", pady=(7, 0))
        self.mod_detail_labels["usage"] = tk.Label(
            detail,
            text="",
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
            justify="left",
            font=("Microsoft YaHei UI", 8),
        )
        self.mod_detail_labels["usage"].pack(fill="x", pady=(3, 8))
        actions = tk.Frame(detail, bg=SURFACE)
        actions.pack(fill="x")
        self.mod_action_buttons["remove"] = self._button(
            actions,
            "卸载",
            lambda: self.mod_selected_id and self._remove_mod(self.mod_selected_id),
            width=10,
        )
        self.mod_action_buttons["remove"].pack(side="right")
        self.mod_action_buttons["launch"] = self._button(
            actions,
            "启动游戏",
            lambda: self.mod_selected_id
            and self._launch_selected_mod(self.mod_selected_id),
            width=10,
        )
        self.mod_action_buttons["launch"].pack(side="right", padx=(0, 6))
        self.mod_action_buttons["configure"] = self._button(
            actions,
            "一键安装",
            lambda: self.mod_selected_id
            and self._configure_mod(self.mod_selected_id),
            accent=True,
            width=10,
        )
        self.mod_action_buttons["configure"].pack(side="right", padx=(0, 6))

        def wrap_detail(_event: tk.Event[Any]) -> None:
            width = max(180, detail.winfo_width() - 24)
            self.mod_detail_labels["summary"].configure(wraplength=width)
            self.mod_detail_labels["usage"].configure(wraplength=width)

        detail.bind("<Configure>", wrap_detail)
        self.mod_search_var.trace_add("write", lambda *_args: self._populate_mod_tree())
        self._populate_mod_tree()

    def _populate_mod_tree(self) -> None:
        tree = self.mod_tree
        if tree is None:
            return
        selected = self.mod_selected_id
        query = self.mod_search_var.get().strip().casefold()
        for item in tree.get_children(""):
            tree.delete(item)
        visible_ids: list[str] = []
        for descriptor in self.mod_manager.catalog.entries:
            haystack = "\n".join(
                (
                    descriptor.display.name,
                    descriptor.display.author,
                    descriptor.display.summary,
                    descriptor.display.usage_hint,
                )
            ).casefold()
            if query and query not in haystack:
                continue
            status = self.mod_manager.status(descriptor.mod_id)
            label, _color = self._mod_status_text(descriptor, status.state)
            tree.insert(
                "",
                "end",
                iid=descriptor.mod_id,
                values=(
                    descriptor.display.name,
                    descriptor.display.version,
                    descriptor.display.author,
                    label.replace("● ", ""),
                ),
            )
            visible_ids.append(descriptor.mod_id)
        if selected not in visible_ids:
            selected = visible_ids[0] if visible_ids else None
        self.mod_selected_id = selected
        if selected is not None:
            tree.selection_set(selected)
            tree.focus(selected)
            tree.see(selected)
        self._update_mod_detail()

    def _on_mod_selected(self, _event: tk.Event[Any] | None = None) -> None:
        if self.mod_tree is None:
            return
        selected = self.mod_tree.selection()
        self.mod_selected_id = selected[0] if selected else None
        self._update_mod_detail()

    @staticmethod
    def _mod_status_text(descriptor: Any, state: str) -> tuple[str, str]:
        is_plugin = descriptor.operation.is_game_plugin
        if state == "installed":
            return ("● 已安装" if is_plugin else "● 已配置"), GREEN
        if state == "integrity_error":
            return "● 文件校验失败", RED
        if state == "game_not_configured":
            return "● 未定位游戏", MUTED
        return ("● 未安装" if is_plugin else "● 未配置"), MUTED

    def _update_mod_detail(self) -> None:
        if not self.mod_detail_labels:
            return
        if self.mod_selected_id is None:
            self.mod_detail_labels["title"].configure(text="没有匹配的 MOD")
            for key in ("status", "author", "summary", "usage"):
                self.mod_detail_labels[key].configure(text="")
            for button in self.mod_action_buttons.values():
                button.configure(state="disabled")
            return
        descriptor = self.mod_manager.descriptor(self.mod_selected_id)
        status = self.mod_manager.status(descriptor.mod_id)
        label, color = self._mod_status_text(descriptor, status.state)
        if self._mod_busy:
            label, color = "● 操作中", GOLD
        self.mod_detail_labels["title"].configure(
            text=f"{descriptor.display.name}  v{descriptor.display.version}"
        )
        self.mod_detail_labels["status"].configure(text=label, fg=color)
        self.mod_detail_labels["author"].configure(
            text=f"作者：{descriptor.display.author}"
        )
        self.mod_detail_labels["summary"].configure(text=descriptor.display.summary)
        self.mod_detail_labels["usage"].configure(
            text=descriptor.display.usage_hint
        )
        any_copy = status.state in {"installed", "integrity_error"}
        is_plugin = descriptor.operation.is_game_plugin
        installed_mtime_ns = (
            self.mod_manager.installed_mtime_ns(descriptor.mod_id)
            if status.installed and descriptor.operation.has_game_panel
            else None
        )
        launch_action = mod_launch_action(
            descriptor.operation,
            installed=status.installed,
            busy=self._mod_busy,
            game_process_id=self.keyboard.game_process_id,
            game_started_ns=self.keyboard.game_process_started_ns,
            installed_mtime_ns=installed_mtime_ns,
        )
        self.mod_action_buttons["configure"].configure(
            text=("重新安装" if is_plugin else "重新配置")
            if any_copy
            else ("一键安装" if is_plugin else "一键配置"),
            state="disabled" if self._mod_busy else "normal",
        )
        self.mod_action_buttons["launch"].configure(
            text=launch_action.label,
            state="normal" if launch_action.enabled else "disabled",
        )
        self.mod_action_buttons["remove"].configure(
            text="卸载" if is_plugin else "删除副本",
            state="normal" if any_copy and not self._mod_busy else "disabled",
        )

    def _launch_selected_mod(self, mod_id: str) -> None:
        descriptor = self.mod_manager.descriptor(mod_id)
        status = self.mod_manager.status(mod_id)
        installed_mtime_ns = (
            self.mod_manager.installed_mtime_ns(mod_id)
            if status.installed and descriptor.operation.has_game_panel
            else None
        )
        action = mod_launch_action(
            descriptor.operation,
            installed=status.installed,
            busy=self._mod_busy,
            game_process_id=self.keyboard.game_process_id,
            game_started_ns=self.keyboard.game_process_started_ns,
            installed_mtime_ns=installed_mtime_ns,
        )
        if not action.enabled:
            return
        if action.kind == "launch_external":
            self._launch_mod(mod_id)
        elif action.kind == "install_required":
            messagebox.showinfo(
                "请先安装 MOD",
                "请先点击“一键安装”，安装完成后再启动游戏。",
                parent=self.root,
            )
        elif action.kind == "launch_game":
            self._launch_game_for_mod(mod_id)
        elif action.kind == "restart_game":
            messagebox.showinfo(
                "需要重启游戏",
                "该 MOD 尚未在本次游戏进程中加载。请关闭游戏，再从工具箱启动。",
                parent=self.root,
            )
        elif action.kind == "open_panel":
            hotkey = descriptor.operation.panel_hotkey
            if hotkey is None or not self.keyboard.open_game_panel_hotkey(hotkey):
                messagebox.showerror(
                    "无法打开 MOD 面板",
                    "未能切换到游戏并打开面板；请确认游戏窗口已正常进入，并重试。",
                    parent=self.root,
                )

    def _open_mod_inbox(self) -> None:
        try:
            self.mod_inbox.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.mod_inbox))
        except OSError as exception:
            messagebox.showerror(
                "无法打开目录", f"无法打开用户 MOD 目录：\n{exception}", parent=self.root
            )

    def _open_mod_help(self) -> None:
        help_file = self.mod_help_file
        if not help_file.is_file():
            fallback = (
                Path(__file__).resolve().parents[1]
                / "package_assets"
                / "MOD自动添加说明.txt"
            )
            help_file = fallback if fallback.is_file() else help_file
        try:
            os.startfile(str(help_file))
        except OSError as exception:
            messagebox.showerror(
                "无法打开说明", f"无法打开 MOD 格式说明：\n{exception}", parent=self.root
            )

    def _add_user_mod(self) -> None:
        if self._mod_busy:
            return
        self.mod_inbox.mkdir(parents=True, exist_ok=True)
        candidates = [
            item
            for item in sorted(self.mod_inbox.iterdir(), key=lambda path: path.name.casefold())
            if item.is_dir()
            or item.suffix.casefold() in {".dll", ".zip", ".7z", ".rar"}
        ]
        if not candidates:
            messagebox.showinfo(
                "没有待添加 MOD",
                "请先把 DLL、ZIP、7Z、RAR 或 MOD 文件夹放入“用户MOD”目录。",
                parent=self.root,
            )
            return
        registered = self.user_mod_registry.registered_fingerprints()
        self._mod_busy = True
        self._update_mod_detail()

        def inspect_candidates() -> None:
            drafts: list[ModDraft] = []
            errors: list[tuple[str, str]] = []
            for source in candidates:
                try:
                    draft = self.mod_inspector.inspect(source)
                    if draft_fingerprint(draft) in registered:
                        continue
                    drafts.append(draft)
                except (ModInspectionError, OSError) as exception:
                    errors.append((source.name, str(exception)))
            self._mod_import_results.put((drafts, errors))

        threading.Thread(
            target=inspect_candidates, name="LC2ModInspect", daemon=True
        ).start()

    def _drain_mod_import_results(self) -> None:
        try:
            drafts, errors = self._mod_import_results.get_nowait()
        except queue.Empty:
            return
        self._mod_busy = False
        self._update_mod_detail()
        if drafts:
            self._open_mod_import_dialog(drafts, errors)
            return
        if errors:
            details = "\n".join(f"• {name}：{error}" for name, error in errors[:6])
            if len(errors) > 6:
                details += f"\n• 另有 {len(errors) - 6} 项未通过识别"
            messagebox.showerror("没有可添加的 MOD", details, parent=self.root)
        else:
            messagebox.showinfo(
                "没有新的 MOD",
                "投放目录中的可识别内容都已经添加。",
                parent=self.root,
            )

    def _open_mod_import_dialog(
        self, drafts: list[ModDraft], errors: list[tuple[str, str]]
    ) -> None:
        pending = list(drafts)
        dialog = tk.Toplevel(self.root)
        dialog.title("添加用户 MOD")
        dialog.configure(bg=BG)
        dialog.geometry("760x520")
        dialog.minsize(640, 460)
        dialog.transient(self.root)
        dialog.grab_set()

        body = tk.Frame(dialog, bg=BG, padx=16, pady=14)
        body.pack(fill="both", expand=True)
        tk.Label(
            body,
            text="检查识别结果",
            bg=BG,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(fill="x")
        tk.Label(
            body,
            text="确认作者与操作方式；证据不足时保留“社区未署名”。识别阶段不会启动 MOD。",
            bg=BG,
            fg=MUTED,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        ).pack(fill="x", pady=(3, 10))

        source_var = tk.StringVar()
        selector = ttk.Combobox(body, textvariable=source_var, state="readonly")
        selector.pack(fill="x", pady=(0, 10))

        form = tk.Frame(body, bg=BG)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        name_var = tk.StringVar()
        version_var = tk.StringVar()
        author_var = tk.StringVar()

        def add_entry(row: int, label: str, variable: tk.StringVar) -> None:
            tk.Label(
                form,
                text=label,
                bg=BG,
                fg=TEXT,
                anchor="w",
                font=("Microsoft YaHei UI", 9, "bold"),
            ).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=4)
            tk.Entry(
                form,
                textvariable=variable,
                relief="solid",
                bd=1,
                bg=SURFACE,
                fg=TEXT,
                insertbackground=TEXT,
                font=("Microsoft YaHei UI", 9),
            ).grid(row=row, column=1, sticky="ew", pady=4, ipady=4)

        add_entry(0, "名称", name_var)
        add_entry(1, "版本", version_var)
        add_entry(2, "作者", author_var)
        tk.Label(
            form,
            text="功能",
            bg=BG,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=3, column=0, sticky="nw", padx=(0, 10), pady=4)
        summary_text = tk.Text(
            form,
            height=3,
            wrap="word",
            relief="solid",
            bd=1,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            font=("Microsoft YaHei UI", 9),
        )
        summary_text.grid(row=3, column=1, sticky="nsew", pady=4)
        tk.Label(
            form,
            text="使用方法",
            bg=BG,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=4, column=0, sticky="nw", padx=(0, 10), pady=4)
        usage_text = tk.Text(
            form,
            height=4,
            wrap="word",
            relief="solid",
            bd=1,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            font=("Microsoft YaHei UI", 9),
        )
        usage_text.grid(row=4, column=1, sticky="nsew", pady=4)
        form.rowconfigure(3, weight=1)
        form.rowconfigure(4, weight=1)
        evidence_label = tk.Label(
            body,
            text="",
            bg=BG,
            fg=MUTED,
            anchor="w",
            justify="left",
            font=("Microsoft YaHei UI", 8),
        )
        evidence_label.pack(fill="x", pady=(6, 4))
        result_label = tk.Label(
            body,
            text=(f"另有 {len(errors)} 项未通过自动识别。" if errors else ""),
            bg=BG,
            fg=RED if errors else GREEN,
            anchor="w",
            font=("Microsoft YaHei UI", 8),
        )
        result_label.pack(fill="x")

        def current_draft() -> ModDraft:
            index = max(0, selector.current())
            return pending[index]

        def load_selection(_event: tk.Event[Any] | None = None) -> None:
            if not pending:
                return
            draft = current_draft()
            source_var.set(draft.source.name)
            name_var.set(draft.name)
            version_var.set(draft.version)
            author_var.set(draft.author)
            summary_text.delete("1.0", "end")
            summary_text.insert("1.0", draft.summary)
            usage_text.delete("1.0", "end")
            usage_text.insert("1.0", draft.usage_hint)
            notes = [
                f"识别依据：{'、'.join(draft.evidence)}",
                f"载荷：{len(draft.payload)} 个文件 / {sum(item.size_bytes for item in draft.payload):,} 字节",
            ]
            if draft.warnings:
                notes.append("注意：" + "；".join(draft.warnings))
            evidence_label.configure(text="  ·  ".join(notes))

        selector.bind("<<ComboboxSelected>>", load_selection)

        actions = tk.Frame(body, bg=BG)
        actions.pack(fill="x", pady=(10, 0))

        def close_dialog() -> None:
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def register_current() -> None:
            draft = current_draft()
            display = {
                "name": name_var.get(),
                "version": version_var.get(),
                "author": author_var.get(),
                "summary": summary_text.get("1.0", "end").strip(),
                "usage_hint": usage_text.get("1.0", "end").strip(),
            }
            try:
                registered = self.user_mod_registry.register(
                    draft,
                    display,
                    reserved_ids={
                        entry.mod_id for entry in self.mod_manager.catalog.entries
                    },
                )
                self.mod_manager.add_descriptor(
                    registered.descriptor, registered.payload_root
                )
            except (ModManagerError, OSError) as exception:
                messagebox.showerror(
                    "添加失败", str(exception), parent=dialog
                )
                return
            self.mod_selected_id = registered.descriptor.mod_id
            pending.remove(draft)
            self._populate_mod_tree()
            if not pending:
                close_dialog()
                messagebox.showinfo(
                    "添加完成",
                    "MOD 已加入本地列表，可返回 MOD 管理执行一键安装。",
                    parent=self.root,
                )
                return
            selector.configure(values=[item.source.name for item in pending])
            selector.current(0)
            result_label.configure(
                text=f"已添加“{registered.descriptor.display.name}”；还有 {len(pending)} 项待确认。",
                fg=GREEN,
            )
            load_selection()

        self._button(actions, "取消", close_dialog, width=10).pack(side="right")
        self._button(
            actions, "确认添加", register_current, accent=True, width=12
        ).pack(side="right", padx=(0, 8))
        selector.configure(values=[item.source.name for item in pending])
        selector.current(0)
        load_selection()

    def _configure_mod(self, mod_id: str) -> None:
        if self._mod_busy:
            return
        descriptor = self.mod_manager.descriptor(mod_id)
        source = self.mod_manager.bundled_source(mod_id)
        if source is None:
            archive = descriptor.operation.archive_source
            filetypes = [("MOD 文件", "*.dll")]
            if archive is not None:
                filetypes[0] = ("MOD 文件", "*.dll *.7z *.zip *.rar")
            if descriptor.operation.kind == "external_trainer":
                filetypes[0] = ("Windows 应用程序", "*.exe")
            filetypes.append(("所有文件", "*.*"))
            selected = filedialog.askopenfilename(
                parent=self.root,
                title=f"选择 {descriptor.display.name} 文件",
                filetypes=tuple(filetypes),
            )
            if not selected:
                return
            source = Path(selected)
        if descriptor.operation.kind == "bepinex_plugin" and not messagebox.askyesno(
            "安装游戏插件",
            f"将“{descriptor.display.name}”安装到游戏插件目录。\n\n安装后需重启游戏，是否继续？",
            parent=self.root,
        ):
            return
        if (
            descriptor.operation.kind == "bepinex_plugin"
            and not self.ensure_game_runtime()
        ):
            return
        self._mod_busy = True
        self._refresh_mod_page()

        def install() -> None:
            try:
                self.mod_manager.install(mod_id, source)
            except Exception as exception:
                self._finish_mod_action(False, exception)
            else:
                self._finish_mod_action(True, None)

        threading.Thread(target=install, name="LC2ModInstall", daemon=True).start()

    def _finish_mod_action(self, success: bool, error: Exception | None) -> None:
        self._mod_results.put((success, error))

    def _drain_mod_results(self) -> None:
        try:
            success, error = self._mod_results.get_nowait()
        except queue.Empty:
            return
        self._mod_busy = False
        self._refresh_mod_page()
        if success:
            messagebox.showinfo("配置完成", "MOD 已配置。", parent=self.root)
        else:
            messagebox.showerror("配置失败", self._mod_error_text(error), parent=self.root)

    @staticmethod
    def _mod_error_text(error: Exception | None) -> str:
        if isinstance(error, ModConflictError):
            names = "、".join(error.conflicts)
            return f"检测到提供同名插件的已安装 MOD：{names}。请先卸载冲突项。"
        if isinstance(error, ModIntegrityError):
            return "所选文件与登记版本不一致；请重新选择对应版本。"
        if isinstance(error, ModGamePathRequired):
            return "未找到可用的游戏或 BepInEx 目录；请先在设置中定位游戏程序。"
        if isinstance(error, (ModManagerError, OSError)):
            return "无法完成 MOD 操作；请确认文件仍存在且目录可写。"
        return "MOD 管理发生未预期错误，未启动第三方程序。"

    def _launch_mod(self, mod_id: str) -> None:
        descriptor = self.mod_manager.descriptor(mod_id)
        confirmed = messagebox.askyesno(
            "启动第三方修改器",
            (
                f"即将启动“{descriptor.display.name}”。\n\n"
                "该工具会修改游戏数据。是否继续？"
            ),
            parent=self.root,
        )
        if not confirmed:
            return
        try:
            self.mod_manager.launch(mod_id)
        except Exception as exception:
            messagebox.showerror("启动失败", self._mod_error_text(exception), parent=self.root)

    def _launch_game_for_mod(self, mod_id: str) -> None:
        if not self.mod_manager.status(mod_id).installed:
            return
        self.launch_game()

    def _remove_mod(self, mod_id: str) -> None:
        if self._mod_busy:
            return
        descriptor = self.mod_manager.descriptor(mod_id)
        is_plugin = descriptor.operation.kind == "bepinex_plugin"
        if not messagebox.askyesno(
            "卸载游戏插件" if is_plugin else "删除盒子副本",
            "从游戏插件目录卸载？" if is_plugin else "删除已配置的本地副本？",
            parent=self.root,
        ):
            return
        try:
            removed = self.mod_manager.uninstall(mod_id)
        except Exception as exception:
            messagebox.showerror("删除失败", self._mod_error_text(exception), parent=self.root)
            return
        self._refresh_mod_page()
        if removed:
            messagebox.showinfo(
                "已卸载" if is_plugin else "已删除",
                "游戏插件已卸载。" if is_plugin else "本地副本已删除。",
                parent=self.root,
            )

    def _refresh_mod_page(self) -> None:
        tree = self.mod_tree
        if tree is None:
            return
        visible = set(tree.get_children(""))
        query = self.mod_search_var.get().strip().casefold()
        expected = {
            descriptor.mod_id
            for descriptor in self.mod_manager.catalog.entries
            if not query
            or query
            in "\n".join(
                (
                    descriptor.display.name,
                    descriptor.display.author,
                    descriptor.display.summary,
                    descriptor.display.usage_hint,
                )
            ).casefold()
        }
        if visible != expected:
            self._populate_mod_tree()
            return
        for mod_id in visible:
            descriptor = self.mod_manager.descriptor(mod_id)
            status = self.mod_manager.status(mod_id)
            label, _color = self._mod_status_text(descriptor, status.state)
            values = list(tree.item(mod_id, "values"))
            if len(values) == 4 and values[3] != label.replace("● ", ""):
                values[3] = label.replace("● ", "")
                tree.item(mod_id, values=values)
        self._update_mod_detail()

    def _build_settings_page(self) -> None:
        page = self._new_page("settings")
        self._page_heading(page, "设置", "")

        display_panel = RoundedPanel(
            page,
            height=None,
            content_padx=12,
            content_pady=5,
        )
        display_panel.pack(fill="x", pady=(0, 9))
        display = display_panel.content
        self._display_control_row(
            display,
            "主窗口",
            "toolbox_window_size",
            (
                ("紧凑", lambda: self._set_toolbox_window_preset("compact")),
                ("标准", lambda: self._set_toolbox_window_preset("standard")),
                ("宽敞", lambda: self._set_toolbox_window_preset("spacious")),
            ),
        )
        tk.Frame(display, bg="#E2D9CC", height=1).pack(fill="x")
        self._display_control_row(
            display,
            "按键显示设备",
            "input_display_mode",
            (
                ("键盘", lambda: self._set_input_display_mode("keyboard")),
                ("手柄", lambda: self._set_input_display_mode("gamepad")),
            ),
        )
        tk.Frame(display, bg="#E2D9CC", height=1).pack(fill="x")
        self._display_control_row(
            display,
            "按键显示缩放",
            "keyboard_scale",
            (
                ("缩小", lambda: self._set_keyboard_scale(-0.1)),
                ("重置", lambda: self._set_keyboard_scale(0.0)),
                ("放大", lambda: self._set_keyboard_scale(0.1)),
                ("恢复拖动", self._restore_keyboard_interaction),
            ),
        )
        tk.Frame(display, bg="#E2D9CC", height=1).pack(fill="x")
        self._display_control_row(
            display,
            "战斗 HUD 缩放",
            "hud_scale",
            (
                ("缩小", lambda: self._set_hud_scale(-0.1)),
                ("重置", lambda: self._set_hud_scale(0.0)),
                ("放大", lambda: self._set_hud_scale(0.1)),
            ),
        )

        settings_panel = RoundedPanel(
            page,
            height=None,
            content_padx=12,
            content_pady=2,
        )
        settings_panel.pack(fill="x")
        panel = settings_panel.content
        self._settings_row(panel, "游戏程序", "", "重新定位", self.choose_game_path)
        self._settings_row(panel, "按键显示", "", "完整设置", self.keyboard.open_settings)
        self._settings_row(panel, "按键宏", "", "编辑宏", self.macro_feature.open_window)
        self._settings_row(panel, "战斗统计", "", "打开 HUD", self.hud.show, last=True)

    def _open_repository(self) -> None:
        if webbrowser.open(TOOLBOX_REPOSITORY_URL, new=2):
            return
        messagebox.showerror(
            "无法打开仓库",
            f"请手动访问：\n{TOOLBOX_REPOSITORY_URL}",
            parent=self.root,
        )

    def _open_bilibili(self) -> None:
        if webbrowser.open(TOOLBOX_BILIBILI_URL, new=2):
            return
        messagebox.showerror(
            "无法打开 Bilibili",
            f"请手动访问：\n{TOOLBOX_BILIBILI_URL}",
            parent=self.root,
        )

    def _open_support_directory(self) -> None:
        directory = self.support_directory
        if directory is None or not directory.is_dir():
            messagebox.showinfo(
                "赞助与投喂",
                f"{SUPPORT_NOTE}\n\n当前副本未找到赞助素材目录。",
                parent=self.root,
            )
            return
        try:
            os.startfile(str(directory))
        except OSError:
            messagebox.showerror(
                "无法打开目录",
                f"请手动打开：\n{directory}",
                parent=self.root,
            )

    def _show_support_popup(self, _event: tk.Event[Any] | None = None) -> None:
        self._cancel_support_popup_hide()
        if self._support_popup is not None:
            try:
                self._support_popup.deiconify()
                self._position_support_popup()
                return
            except tk.TclError:
                self._support_popup = None

        popup = tk.Toplevel(self.root)
        self._support_popup = popup
        popup.title("赞助与投喂")
        popup.overrideredirect(True)
        popup.transient(self.root)
        try:
            popup.attributes("-topmost", True)
        except tk.TclError:
            pass
        panel = tk.Frame(
            popup,
            bg=SURFACE,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        panel.pack(fill="both", expand=True)
        tk.Label(
            panel,
            text=SUPPORT_TITLE,
            bg=SURFACE,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            panel,
            text=SUPPORT_NOTE,
            bg=SURFACE,
            fg=MUTED,
            justify="left",
            wraplength=300,
            font=("Microsoft YaHei UI", 8),
        ).pack(anchor="w", pady=(5, 8))

        qr_path = (
            self.support_directory / SUPPORT_QR_FILENAME
            if self.support_directory is not None
            else None
        )
        if qr_path is not None and qr_path.is_file():
            try:
                image = tk.PhotoImage(file=str(qr_path))
                factor = max(
                    1,
                    (image.width() + 259) // 260,
                    (image.height() + 359) // 360,
                )
                if factor > 1:
                    image = image.subsample(factor, factor)
                self._support_qr_image = image
                tk.Label(panel, image=image, bg=SURFACE, cursor="hand2").pack()
            except tk.TclError:
                self._support_qr_image = None
        if self._support_qr_image is None:
            tk.Label(
                panel,
                text="点击打开本地赞助说明与收款码",
                bg="#F4E8CC",
                fg=GOLD,
                padx=12,
                pady=10,
                font=("Microsoft YaHei UI", 8, "bold"),
                cursor="hand2",
            ).pack(fill="x")
        tk.Label(
            panel,
            text="点击查看微信 / 支付宝与完整说明",
            bg=SURFACE,
            fg=GOLD,
            font=("Microsoft YaHei UI", 8),
            cursor="hand2",
        ).pack(pady=(8, 0))

        def bind_popup_tree(widget: tk.Misc) -> None:
            widget.bind("<Enter>", self._cancel_support_popup_hide, add="+")
            widget.bind("<Leave>", self._schedule_support_popup_hide, add="+")
            widget.bind("<Button-1>", lambda _click: self._open_support_directory(), add="+")
            for child in widget.winfo_children():
                bind_popup_tree(child)

        bind_popup_tree(popup)
        popup.update_idletasks()
        self._position_support_popup()

    def _position_support_popup(self) -> None:
        popup = self._support_popup
        button = self._support_button
        if popup is None or button is None:
            return
        try:
            popup.update_idletasks()
            width = popup.winfo_reqwidth()
            height = popup.winfo_reqheight()
            x = button.winfo_rootx()
            y = button.winfo_rooty() - height - 8
            x = min(max(8, x), max(8, popup.winfo_screenwidth() - width - 8))
            y = min(max(8, y), max(8, popup.winfo_screenheight() - height - 8))
            popup.geometry(f"+{x}+{y}")
        except tk.TclError:
            self._support_popup = None

    def _schedule_support_popup_hide(self, _event: tk.Event[Any] | None = None) -> None:
        self._cancel_support_popup_hide()
        try:
            self._support_hide_after_id = self.root.after(
                220, self._hide_support_popup
            )
        except tk.TclError:
            self._support_hide_after_id = None

    def _cancel_support_popup_hide(self, _event: tk.Event[Any] | None = None) -> None:
        if self._support_hide_after_id is None:
            return
        try:
            self.root.after_cancel(self._support_hide_after_id)
        except tk.TclError:
            pass
        self._support_hide_after_id = None

    def _hide_support_popup(self) -> None:
        self._support_hide_after_id = None
        if self._support_popup is not None:
            try:
                self._support_popup.withdraw()
            except tk.TclError:
                self._support_popup = None

    def _resize_mod_tree_columns(self, event: tk.Event[Any]) -> None:
        tree = self.mod_tree
        if tree is None or event.widget is not tree:
            return
        widths = mod_tree_column_widths(event.width)
        for column, width in widths.items():
            tree.column(column, width=width)

    def _display_control_row(
        self,
        parent: tk.Frame,
        title: str,
        value_key: str,
        actions: tuple[tuple[str, Callable[[], None]], ...],
    ) -> None:
        row = tk.Frame(parent, bg=SURFACE, pady=4)
        row.pack(fill="x")
        controls = tk.Frame(row, bg=SURFACE)
        controls.pack(side="right")
        for index, (label, command) in enumerate(actions):
            self._button(controls, label, command, width=6).pack(
                side="left",
                padx=(0 if index == 0 else 5, 0),
            )
        copy = tk.Frame(row, bg=SURFACE)
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            copy,
            text=title,
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 9, "bold"),
        ).pack(side="left")
        self.labels[value_key] = tk.Label(
            copy,
            text="—",
            bg=SURFACE,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        self.labels[value_key].pack(side="left", padx=(10, 0))

    def _settings_row(
        self,
        parent: tk.Frame,
        title: str,
        detail: str,
        action_text: str,
        command: Callable[[], None],
        *,
        last: bool = False,
    ) -> None:
        row = tk.Frame(parent, bg=SURFACE, pady=5)
        row.pack(fill="x")
        copy = tk.Frame(row, bg=SURFACE)
        copy.pack(side="left", fill="x", expand=True)
        tk.Label(copy, text=title, bg=SURFACE, fg=TEXT, anchor="w", font=("Microsoft YaHei UI", 9, "bold")).pack(fill="x")
        if detail:
            tk.Label(copy, text=detail, bg=SURFACE, fg=MUTED, anchor="w", font=("Microsoft YaHei UI", 8)).pack(fill="x", pady=(3, 0))
        self._button(row, action_text, command, width=11).pack(side="right")
        if not last:
            tk.Frame(parent, bg="#E2D9CC", height=1).pack(fill="x")

    def _set_toolbox_window_preset(self, preset: str) -> None:
        requested_width, requested_height = TOOLBOX_WINDOW_PRESETS[preset]
        width, height = clamp_main_window_size(
            requested_width,
            requested_height,
            screen_width=self.root.winfo_screenwidth(),
            screen_height=self.root.winfo_screenheight(),
            tk_scaling=float(self.root.tk.call("tk", "scaling")),
        )
        self.root.state("normal")
        x = min(max(0, self.root.winfo_x()), max(0, self.root.winfo_screenwidth() - width))
        y = min(max(0, self.root.winfo_y()), max(0, self.root.winfo_screenheight() - height))
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.main_ui_scale = TOOLBOX_UI_SCALES[preset]
        self._apply_main_ui_scale()
        self.root.update_idletasks()
        self.keyboard.set_toolbox_window_size(width, height)
        self.keyboard.set_toolbox_ui_scale(self.main_ui_scale)
        self._refresh_display_settings()

    def _set_keyboard_scale(self, change: float) -> None:
        # A scale command is also an explicit request to inspect the overlay.
        # Bring it back to an interactive, visible state before resizing so the
        # user gets immediate feedback instead of changing an off-screen/hidden layer.
        self.keyboard.restore_interaction()
        target = 1.0 if abs(change) < 0.001 else self.keyboard.ui_scale + change
        self.keyboard.set_ui_scale(target)
        self._refresh_display_settings()

    def _set_input_display_mode(self, mode: str) -> None:
        self.keyboard.restore_interaction()
        self.keyboard.set_display_mode(mode)
        self._draw_keyboard_preview()
        self._refresh_module_statuses()
        self._refresh_display_settings()

    def _restore_keyboard_interaction(self) -> None:
        self.keyboard.restore_interaction()
        self._refresh_display_settings()

    def _set_hud_scale(self, change: float) -> None:
        target = 1.0 if abs(change) < 0.001 else self.hud.ui_scale + change
        self.hud.set_ui_scale(target)
        self.keyboard.set_hud_ui_scale(self.hud.ui_scale)
        self.hud.show()
        self._refresh_display_settings()

    def _refresh_display_settings(self) -> None:
        width, height = self.root.winfo_width(), self.root.winfo_height()
        if width <= 1 or height <= 1:
            width, height = self.keyboard.toolbox_window_size
        self.labels["toolbox_window_size"].configure(
            text=f"{width} × {height} · {round(self.main_ui_scale * 100)}%"
        )
        modes = []
        if self.keyboard.key_only:
            modes.append("纯净")
        if self.keyboard.click_through:
            modes.append("穿透")
        suffix = f" · {' / '.join(modes)}" if modes else " · 可拖动"
        self.labels["keyboard_scale"].configure(
            text=f"{round(self.keyboard.ui_scale * 100)}%{suffix}"
        )
        self.labels["input_display_mode"].configure(
            text="键盘" if self.keyboard.display_mode == "keyboard" else "手柄"
        )
        self.labels["hud_scale"].configure(
            text=f"{round(self.hud.ui_scale * 100)}%"
        )

    def _button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        accent: bool = False,
        width: int = 10,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=ACCENT if accent else "#F3EBDD",
            fg="#FFFAF5" if accent else "#665C51",
            activebackground=ACCENT_HOVER if accent else "#E8DDCD",
            activeforeground="#FFFAF5" if accent else TEXT,
            relief="flat",
            bd=0,
            padx=8,
            pady=7,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8, "bold"),
        )

    def show_page(self, page_id: str) -> None:
        if page_id not in self.pages:
            raise KeyError(page_id)
        for current_id, page in self.pages.items():
            if current_id == page_id:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        for current_id, button in self.nav_buttons.items():
            selected = current_id == page_id
            button.configure(
                bg=ACCENT if selected else SIDEBAR,
                fg="#FFFAF5" if selected else TEXT,
                font=(
                    "Microsoft YaHei UI",
                    max(7, round(9 * self.main_ui_scale)),
                    "bold" if selected else "normal",
                ),
            )
        if page_id == "keyboard":
            self._draw_keyboard_preview()
        elif page_id == "macro":
            self._refresh_macro_rows()
        elif page_id == "combat":
            self._refresh_combat()
        elif page_id == "mods":
            self._refresh_mod_page()

    def refresh(self) -> None:
        self._refresh_module_statuses()
        self._refresh_combat()
        self._refresh_macro_rows()
        self._refresh_mod_page()
        self._refresh_display_settings()
        self._draw_keyboard_preview()
        self.hud.refresh()

    def _refresh_module_statuses(self) -> None:
        game_running = bool(self.keyboard.game_process_id)
        self.labels["sidebar_game"].configure(
            text="● 游戏运行中" if game_running else "● 游戏未运行\n可从顶部启动",
            fg=GREEN if game_running else MUTED,
        )
        snapshot = self.combat_aggregator.snapshot()
        self.labels["combat_status"].configure(
            text=combat_state_label(snapshot.connection_state),
            fg=combat_state_color(snapshot.connection_state),
        )
        self.labels["combat_summary"].configure(
            text=(
                f"总伤害 {format_metric(snapshot.total_damage)}\n"
                f"{TAKEN_DAMAGE_LABEL} / 回复 "
                f"{format_whole_metric(snapshot.taken_settlement_damage)} / "
                f"{format_whole_metric(snapshot.effective_healing)}"
            )
        )
        self.labels["keyboard_status"].configure(
            text="● 悬浮窗已显示" if self.keyboard.visible else "● 悬浮窗已隐藏",
            fg=GREEN if self.keyboard.visible else MUTED,
        )
        preview_items = tuple(self.keyboard_preview_provider())
        if self.keyboard.display_mode == "gamepad":
            self.labels["keyboard_summary"].configure(text="手柄模式\n常用按键")
        else:
            ordered = ordered_keyboard_keys(preview_items)
            core_keys = {"W", "A", "S", "D", "U", "I", "O", "J", "K", "L", "SPACE"}
            compact_keys = " · ".join(
                group
                for group in (
                    "".join(key for key in ("W", "A", "S", "D") if key in ordered),
                    "".join(key for key in ("U", "I", "O", "J", "K", "L") if key in ordered),
                    "SPACE" if "SPACE" in ordered else "",
                )
                if group
            )
            remaining = sum(key not in core_keys for key in ordered)
            if remaining:
                compact_keys = f"{compact_keys} · +{remaining}" if compact_keys else f"+{remaining}"
            self.labels["keyboard_summary"].configure(
                text=(f"{len(ordered)} 个按键\n{compact_keys}" if ordered else "未选择按键")
            )
        profiles = tuple(self.macro_feature.profiles)
        enabled = sum(profile.enabled for profile in profiles)
        self.labels["macro_status"].configure(
            text="● 配置错误" if self.macro_feature.errors else "● 前台限定 · 默认停用",
            fg=RED if self.macro_feature.errors else MUTED,
        )
        self.labels["macro_summary"].configure(text=f"{len(profiles)} 个方案\n{enabled} 个已启用")
        self.labels["keyboard_page_status"].configure(
            text="● 悬浮窗已显示" if self.keyboard.visible else "● 悬浮窗已隐藏",
            fg="#77D99B" if self.keyboard.visible else "#9FB1BD",
        )
        mode_copy = (
            "手柄"
            if self.keyboard.display_mode == "gamepad"
            else f"键盘 · 已选择 {len(self.keyboard.selected_keys)} 个按键"
        )
        self.labels["keyboard_page_summary"].configure(
            text=(
                f"{mode_copy} · 预设 {self.keyboard.color_preset} · "
                f"缩放 {round(self.keyboard.ui_scale * 100)}% · "
                f"背景 {round(self.keyboard.background_opacity * 100)}%"
            )
        )
        for mode, button in self.input_mode_buttons.items():
            selected = mode == self.keyboard.display_mode
            button.configure(
                bg=ACCENT if selected else "#F3EBDD",
                fg="#FFFAF5" if selected else "#665C51",
            )

    def _refresh_combat(self) -> None:
        snapshot = self.combat_aggregator.snapshot()
        live = snapshot.connection_state == "live"
        self.labels["combat_connection"].configure(
            text=(
                f"● 实时 · {format_stage_location(snapshot)}"
                if live
                else f"{combat_state_label(snapshot.connection_state)}；键盘和宏不受影响"
            ),
            fg=combat_state_color(snapshot.connection_state),
        )
        _set_metric_label(
            self.labels["combat_damage"],
            format_metric(snapshot.total_damage),
            base_size=max(8, round(22 * self.main_ui_scale)),
            characters_at_base=10,
        )
        self.labels["combat_boss"].configure(text=f"Boss {format_metric(snapshot.boss_damage)}")
        _set_metric_label(
            self.labels["combat_hp"],
            format_whole_metric(snapshot.taken_settlement_damage),
            base_size=max(8, round(22 * self.main_ui_scale)),
            characters_at_base=10,
        )
        self.labels["combat_heal"].configure(
            text=f"回复 +{format_whole_metric(snapshot.effective_healing)}"
        )
        _set_metric_label(
            self.labels["combat_mp"],
            format_whole_metric(snapshot.mp_spent),
            base_size=max(8, round(22 * self.main_ui_scale)),
            characters_at_base=10,
        )
        self.labels["combat_mp_gain"].configure(
            text=f"恢复 +{format_whole_metric(snapshot.mp_gained)}"
        )
        team_rows = combat_team_rows(snapshot)
        team_visible = snapshot.detected_player_count >= 2 and len(team_rows) >= 2
        if self.combat_team_panel is not None:
            if team_visible and not self.combat_team_panel.winfo_manager():
                self.combat_team_panel.pack(
                    fill="x",
                    pady=(9, 0),
                    before=self.combat_detail_panel,
                )
            elif not team_visible and self.combat_team_panel.winfo_manager():
                self.combat_team_panel.pack_forget()
        self.labels["combat_team_heading"].configure(
            text=f"队伍伤害 · {max(1, snapshot.detected_player_count)} 人"
        )
        self.labels["combat_team_unattributed"].configure(
            text=(
                f"未归属 {format_metric(snapshot.unattributed_damage)}"
                if snapshot.unattributed_damage > 0
                else ""
            )
        )
        for index, cell in enumerate(self.combat_team_cells):
            if team_visible and index < len(team_rows):
                label, damage, boss, share = team_rows[index]
                name_label, damage_label, boss_label = self.combat_team_labels[index]
                name_label.configure(text=label)
                damage_label.configure(
                    text=f"伤害 {format_metric(damage)} · {round(share * 100)}%"
                )
                boss_label.configure(text=f"Boss {format_metric(boss)}")
                self._combat_team_shares[index] = share
                cell.grid()
                self._draw_combat_team_share(index)
            else:
                self._combat_team_shares[index] = 0.0
                cell.grid_remove()
        for item_id in self.combat_tree.get_children():
            self.combat_tree.delete(item_id)
        ranked = sorted(
            snapshot.source_breakdown.items(),
            key=lambda item: (
                item[1].get("damage_dealt", 0)
                + item[1].get("effective_healing", 0)
                + item[1].get("mp_spent", 0)
                + item[1].get("mp_gained", 0)
            ),
            reverse=True,
        )
        for _token, values in ranked:
            self.combat_tree.insert(
                "",
                "end",
                values=(
                    values.get("label", "未知来源"),
                    format_metric(values.get("damage_dealt", 0)),
                    format_whole_metric(values.get("effective_healing", 0)),
                    format_whole_metric(values.get("mp_spent", 0)),
                    format_whole_metric(values.get("mp_gained", 0)),
                ),
            )
        self.labels["combat_detail_hint"].configure(
            text=(f"{len(ranked)} 个来源" if ranked else "尚无事件；连接后按来源显示有效值")
        )
        self.labels["combat_totals"].configure(
            text=(
                f"{TAKEN_DAMAGE_LABEL} {format_whole_metric(snapshot.taken_settlement_damage)} · "
                f"实际战斗掉血 {format_whole_metric(snapshot.hp_damage_taken)} · "
                f"减伤 {format_whole_metric(snapshot.mitigated_damage)} · "
                f"治疗溢出 {format_whole_metric(snapshot.resource_overflow)}"
            )
        )

    def _draw_combat_team_share(self, index: int) -> None:
        if not 0 <= index < len(self.combat_team_bars):
            return
        bar = self.combat_team_bars[index]
        width = max(1, bar.winfo_width())
        height = max(1, bar.winfo_height())
        left, right = 3, max(3, width - 3)
        y = height / 2
        share = max(0.0, min(1.0, self._combat_team_shares[index]))
        line_width = max(3, round(5 * self.main_ui_scale))
        bar.delete("all")
        bar.create_line(
            left,
            y,
            right,
            y,
            fill="#E4D8C7",
            width=line_width,
            capstyle=tk.ROUND,
        )
        if share > 0:
            bar.create_line(
                left,
                y,
                left + (right - left) * share,
                y,
                fill=GOLD,
                width=line_width,
                capstyle=tk.ROUND,
            )

    def _refresh_macro_rows(self) -> None:
        rows = macro_rows(self.macro_feature.profiles)
        current_selection = self.macro_tree.selection()
        selected_index = self.macro_tree.index(current_selection[0]) if current_selection else None
        for item_id in self.macro_tree.get_children():
            self.macro_tree.delete(item_id)
        self._macro_row_descriptions = [row.description for row in rows]
        for row in rows:
            self.macro_tree.insert(
                "",
                "end",
                values=(row.enabled_label, row.name, row.trigger, row.mode, row.steps),
            )
        if selected_index is not None and selected_index < len(rows):
            item_id = self.macro_tree.get_children()[selected_index]
            self.macro_tree.selection_set(item_id)
            self.macro_tree.focus(item_id)
            self._show_full_macro_description(None)
        elif not rows:
            self.labels["macro_full_description"].configure(text="尚无宏方案；可打开完整编辑器新建。")
        if self.macro_feature.errors:
            self.labels["macro_page_status"].configure(
                text="配置存在错误：" + "；".join(self.macro_feature.errors), fg=RED
            )
        else:
            enabled = sum(profile.enabled for profile in self.macro_feature.profiles)
            self.labels["macro_page_status"].configure(
                text=f"{len(rows)} 个方案 · {enabled} 个已启用 · 所有方案只在游戏前台生效",
                fg=MUTED,
            )

    def _show_full_macro_description(self, _event: tk.Event[Any] | None) -> None:
        selection = self.macro_tree.selection()
        if not selection:
            return
        index = self.macro_tree.index(selection[0])
        if 0 <= index < len(self._macro_row_descriptions):
            self.labels["macro_full_description"].configure(
                text=self._macro_row_descriptions[index]
            )

    def _draw_keyboard_preview(self) -> None:
        if not hasattr(self, "keyboard_canvas"):
            return
        canvas = self.keyboard_canvas
        try:
            width = max(1, canvas.winfo_width())
            height = max(1, canvas.winfo_height())
        except tk.TclError:
            return
        items = tuple(self.keyboard_preview_provider())
        canvas.delete("all")
        if not items:
            canvas.create_text(
                width / 2,
                height / 2,
                text="未选择显示按键",
                fill="#9FB1BD",
                font=("Microsoft YaHei UI", 10),
            )
            return
        max_x = max(x + key_width for _key, _label, (x, _y, key_width, _height) in items)
        max_y = max(y + key_height for _key, _label, (_x, y, _width, key_height) in items)
        scale = min((width - 34) / max_x, (height - 24) / max_y, 0.9)
        offset_x = (width - max_x * scale) / 2
        offset_y = (height - max_y * scale) / 2
        for _key_id, label, (x, y, key_width, key_height) in sorted(
            items, key=lambda item: (item[2][1], item[2][0], item[0])
        ):
            x1 = offset_x + x * scale
            y1 = offset_y + y * scale
            x2 = x1 + key_width * scale
            y2 = y1 + key_height * scale
            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill="#293844",
                outline="#A6BAC6",
                width=1,
            )
            inset = max(2, 4 * scale)
            canvas.create_rectangle(
                x1 + inset,
                y1 + inset,
                x2 - inset,
                y2 - inset,
                fill="",
                outline="#536F7D",
                width=1,
            )
            canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=label,
                fill="#F3F7F9",
                font=("Segoe UI", max(7, round(11 * scale)), "bold"),
            )

    def _tick(self) -> None:
        if self._closed:
            return
        if self.combat_event_pump is not None:
            self.combat_event_pump.drain()
        self._drain_mod_results()
        self._drain_mod_import_results()
        self.refresh()
        self._after_id = self.root.after(500, self._tick)

    def close(self) -> None:
        self._closed = True
        self._cancel_support_popup_hide()
        if self._support_popup is not None:
            try:
                self._support_popup.destroy()
            except tk.TclError:
                pass
            self._support_popup = None
        self._support_qr_image = None
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
        if self.persist_window_geometry:
            try:
                if self.root.state() == "normal":
                    self.keyboard.set_toolbox_window_size(
                        self.root.winfo_width(),
                        self.root.winfo_height(),
                    )
            except tk.TclError:
                pass
        self.hud.close()

    @staticmethod
    def _initial_geometry(root: tk.Tk, requested_width: int, requested_height: int) -> str:
        width, height = clamp_main_window_size(
            requested_width,
            requested_height,
            screen_width=root.winfo_screenwidth(),
            screen_height=root.winfo_screenheight(),
            tk_scaling=float(root.tk.call("tk", "scaling")),
        )
        x = max(20, (root.winfo_screenwidth() - width) // 2)
        y = max(20, (root.winfo_screenheight() - height) // 2)
        return f"{width}x{height}+{x}+{y}"
