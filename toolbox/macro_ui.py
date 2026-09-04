from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
import queue
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .app_shell import RoundedPanel
from .macro_config import (
    EMERGENCY_KEY,
    EMERGENCY_MODIFIERS,
    default_profile_data,
    load_macro_config,
    save_macro_config,
)
from .macro_engine import MacroController, MacroState, MacroStatus
from .macro_model import (
    MacroProfile,
    MacroProfileError,
    macro_profile_to_dict,
    parse_macro_profile,
)
from .windows_input import MOUSE_FLAGS, VK_CODES, WindowsSendInputBackend


BG = "#F3EEE3"
PANEL = "#FBF9F4"
CONTROL = "#F3EBDD"
CONTROL_HOVER = "#E8DDCD"
CAPTURE_CONTROL = "#E3D6C4"
CAPTURE_HOVER = "#D8C9B5"
OUTLINE = "#D7CAB7"
TEXT = "#292725"
MUTED = "#6F675E"
ACCENT = "#D86F4C"
ACCENT_DARK = "#D86F4C"
GOOD = "#397B64"
PAUSED = "#956B38"
BAD = "#C34B37"

MODE_LABELS = {
    "once": "按一次：执行一遍",
    "hold_repeat": "按住：持续循环",
    "toggle_repeat": "开关：再次按下或到时停止",
}
MODE_IDS = {label: mode for mode, label in MODE_LABELS.items()}
ACTION_LABELS = {
    "tap": "按一下",
    "down": "按下",
    "up": "抬起",
    "wait": "等待",
}
ACTION_IDS = {label: action for action, label in ACTION_LABELS.items()}
TRIGGER_KEYS = tuple(
    [f"F{number}" for number in range(1, 8)]
    + list("QWERTYUIOPASDFGHJKLZXCVBNM")
    + [str(number) for number in range(10)]
    + ["TAB", "CAPS", "SPACE", "ENTER"]
)
STEP_KEYS = tuple(
    list("QWERTYUIOPASDFGHJKLZXCVBNM")
    + [str(number) for number in range(10)]
    + ["SPACE", "SHIFT", "CTRL", "ALT", "TAB", "ESC", "ENTER", "BACK"]
    + ["LEFT", "UP", "DOWN", "RIGHT", "LMB", "RMB", "MMB"]
    + [f"F{number}" for number in range(1, 13)]
)

KEYSYM_ALIASES = {
    "RETURN": "ENTER",
    "KP_ENTER": "ENTER",
    "SPACE": "SPACE",
    "TAB": "TAB",
    "CAPS_LOCK": "CAPS",
    "ESCAPE": "ESC",
    "BACKSPACE": "BACK",
    "LEFT": "LEFT",
    "UP": "UP",
    "DOWN": "DOWN",
    "RIGHT": "RIGHT",
    "CONTROL_L": "CTRL",
    "CONTROL_R": "CTRL",
    "SHIFT_L": "SHIFT",
    "SHIFT_R": "SHIFT",
    "ALT_L": "ALT",
    "ALT_R": "ALT",
}


def key_from_tk_keysym(keysym: str) -> str | None:
    """Translate one Tk key event into the macro key vocabulary."""
    normalized = str(keysym).strip().upper()
    if not normalized:
        return None
    alias = KEYSYM_ALIASES.get(normalized)
    if alias is not None:
        return alias
    if len(normalized) == 1 and normalized in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        return normalized
    if normalized.startswith("F") and normalized[1:].isdigit():
        number = int(normalized[1:])
        if 1 <= number <= 12:
            return f"F{number}"
    return None


def captured_key_for_target(target: str, keysym: str) -> str | None:
    key = key_from_tk_keysym(keysym)
    if key is None:
        return None
    allowed = TRIGGER_KEYS if target == "trigger_key" else STEP_KEYS if target == "step_key" else ()
    return key if key in allowed else None


def seconds_text_from_milliseconds(milliseconds: int) -> str:
    seconds = Decimal(milliseconds) / Decimal(1000)
    return format(seconds.normalize(), "f")


def milliseconds_from_seconds_text(value: str) -> int:
    try:
        seconds = Decimal(str(value).strip())
    except InvalidOperation as exception:
        raise ValueError("最长运行时间必须是秒数") from exception
    if not seconds.is_finite():
        raise ValueError("最长运行时间必须是有限秒数")
    milliseconds = seconds * Decimal(1000)
    if milliseconds != milliseconds.to_integral_value():
        raise ValueError("最长运行时间最多保留三位小数")
    return int(milliseconds)


def runtime_presentation(state: MacroState) -> tuple[str, str]:
    labels = {
        MacroState.RUNNING: "● 宏运行中",
        MacroState.BLOCKED_FOCUS: "● 安全暂停 · 请回游戏后重按",
        MacroState.TIME_LIMIT: "● 已到最长运行时间",
        MacroState.ERROR: "● 宏执行错误",
        MacroState.STOPPING: "● 正在停止",
        MacroState.STOPPED: "● 已停止",
        MacroState.COMPLETED: "● 已完成",
        MacroState.TRIGGER_RELEASED: "● 已松开停止",
    }
    text = labels.get(state, "● 待命 · 仅在游戏前台执行")
    if state is MacroState.ERROR:
        return text, BAD
    if state in {MacroState.BLOCKED_FOCUS, MacroState.TIME_LIMIT, MacroState.STOPPING}:
        return text, PAUSED
    return text, GOOD


def _is_key_down(key: str) -> bool:
    import ctypes

    if key in MOUSE_FLAGS:
        virtual_key = {"LMB": 0x01, "RMB": 0x02, "MMB": 0x04}[key]
    else:
        virtual_key = VK_CODES.get(key)
    return bool(virtual_key and ctypes.windll.user32.GetAsyncKeyState(virtual_key) & 0x8000)


class MacroFeature:
    """Owns macro configuration, global trigger polling and the editor window."""

    def __init__(self, root: tk.Misc, config_dir: Path) -> None:
        self.root = root
        self.config_path = config_dir / "macros.json"
        self.profiles, self.errors = load_macro_config(self.config_path)
        if not self.config_path.exists() and not self.errors:
            try:
                save_macro_config(self.config_path, self.profiles)
            except OSError as exception:
                self.errors = [f"无法创建 macros.json：{type(exception).__name__}"]
        self._status_queue: queue.SimpleQueue[MacroStatus] = queue.SimpleQueue()
        self.controller = MacroController(
            WindowsSendInputBackend("LostCastle2.exe"), self._status_queue.put
        )
        self.window: tk.Toplevel | None = None
        self.profile_list: tk.Listbox | None = None
        self.status_label: tk.Label | None = None
        self.runtime_label: tk.Label | None = None
        self.step_tree: ttk.Treeview | None = None
        self.vars: dict[str, tk.Variable] = {}
        self.modifier_vars: dict[str, tk.BooleanVar] = {}
        self._editing_steps: list[dict[str, Any]] = []
        self._selected_index: int | None = None
        self._loaded_step_index: int | None = None
        self._loading_form = False
        self._dirty = False
        self._step_draft_dirty = False
        self._emergency_down = False
        self._rearm_required = False
        self._advanced_visible = False
        self.advanced_window: tk.Toplevel | None = None
        self.advanced_button: tk.Button | None = None
        self._key_combos: dict[str, ttk.Combobox] = {}
        self._capture_buttons: dict[str, tk.Button] = {}
        self._capture_target: str | None = None
        self._capture_release_key: str | None = None
        self._runtime_state: MacroState | None = None
        self.step_key_label: tk.Label | None = None
        self.step_ms_label: tk.Label | None = None
        self.step_ms_entry: tk.Entry | None = None
        self._closed = False
        self._after_id = self.root.after(20, self._tick)

    def open_window(self) -> None:
        if self.window is not None:
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.focus_force()
                return
            except tk.TclError:
                self.window = None
        window = tk.Toplevel(self.root)
        self.window = window
        window.title("失落城堡2工具箱 · 宏")
        window.configure(bg=BG)
        window.geometry(self._initial_geometry(window))
        window.minsize(780, 680)
        window.attributes("-topmost", False)

        header = tk.Frame(window, bg=BG, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text="按键宏",
            bg=BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 18, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="只在 LostCastle2.exe 为前台时执行",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left", padx=(12, 0), pady=(8, 0))
        self.runtime_label = tk.Label(
            header,
            text="● 待命 · 仅在游戏前台执行",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.runtime_label.pack(side="right", pady=(8, 0))

        notice_panel = RoundedPanel(
            window,
            fill="#EEE2D2",
            outline="#DDCBB8",
            height=44,
            content_padx=14,
            content_pady=4,
        )
        notice_panel.pack(fill="x", padx=20)
        notice = notice_panel.content
        tk.Label(
            notice,
            text="紧急停止  Ctrl + Shift + F12",
            bg="#EEE2D2",
            fg="#7A573F",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left")
        tk.Label(
            notice,
            text="切出游戏、退出或修改配置时也会立即停止并释放按键。",
            bg="#EEE2D2",
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side="right")

        content = tk.Frame(window, bg=BG, padx=20, pady=10)
        content.pack(fill="both", expand=True)
        left_panel = RoundedPanel(
            content,
            fill=PANEL,
            outline=OUTLINE,
            height=520,
            content_padx=12,
            content_pady=12,
        )
        left_panel.configure(width=240)
        left_panel.pack(side="left", fill="y")
        left = left_panel.content
        right_panel = RoundedPanel(
            content,
            fill=PANEL,
            outline=OUTLINE,
            height=520,
            content_padx=16,
            content_pady=14,
        )
        right_panel.pack(side="left", fill="both", expand=True, padx=(12, 0))
        right = right_panel.content

        tk.Label(
            left,
            text="宏方案",
            bg=PANEL,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        self.profile_list = tk.Listbox(
            left,
            bg="#F7F2E9",
            fg=TEXT,
            selectbackground="#E4D6C4",
            selectforeground=TEXT,
            activestyle="none",
            highlightthickness=1,
            highlightbackground=OUTLINE,
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 9),
        )
        self.profile_list.pack(fill="both", expand=True)
        self.profile_list.bind("<<ListboxSelect>>", self._on_profile_select)

        self._button(left, "＋ 新建宏", lambda: self._new_profile("once"), accent=True).pack(
            fill="x", pady=(10, 0)
        )
        self._button(left, "删除所选", self._delete_selected, danger=True).pack(
            fill="x", pady=(7, 0)
        )

        self._advanced_visible = False
        self._build_editor(right)

        footer = tk.Frame(window, bg=BG, padx=20, pady=0)
        footer.pack(fill="x")
        self.status_label = tk.Label(
            footer,
            text="",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)
        self._button(footer, "停止全部", lambda: self.controller.stop_all("ui_stop")).pack(
            side="right", padx=(8, 0)
        )
        self._button(footer, "保存当前宏", self._save_selected, accent=True, width=12).pack(
            side="right"
        )

        # Reserve the action bar from the bottom before allowing the editor to
        # consume the remaining height. This keeps Save/Stop visible at min size.
        content.pack_forget()
        footer.pack_forget()
        footer.pack(side="bottom", fill="x", pady=(0, 12))
        content.pack(fill="both", expand=True)

        self._refresh_profile_list(select=0 if self.profiles else None)
        if self.errors:
            self._set_status("；".join(self.errors), error=True)
        window.protocol("WM_DELETE_WINDOW", self._close_window)

    def close(self) -> None:
        self._closed = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self.controller.close()
        self._close_window(force=True)

    def _initial_geometry(self, window: tk.Toplevel) -> str:
        width = min(980, max(780, window.winfo_screenwidth() - 120))
        height = min(820, max(680, window.winfo_screenheight() - 100))
        x = max(20, (window.winfo_screenwidth() - width) // 2)
        y = max(20, (window.winfo_screenheight() - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _build_editor(self, parent: tk.Frame) -> None:
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x")
        self.vars = {
            "name": tk.StringVar(),
            "enabled": tk.BooleanVar(),
            "trigger_key": tk.StringVar(value="F5"),
            "mode": tk.StringVar(value=MODE_LABELS["once"]),
            "max_runtime_seconds": tk.StringVar(value="60"),
            "repeat_delay_ms": tk.StringVar(value="80"),
            "step_action": tk.StringVar(value=ACTION_LABELS["tap"]),
            "step_key": tk.StringVar(value="J"),
            "step_ms": tk.StringVar(value="50"),
        }
        self.modifier_vars = {
            key: tk.BooleanVar(value=False) for key in ("CTRL", "ALT", "SHIFT")
        }
        for name in (
            "name",
            "enabled",
            "trigger_key",
            "mode",
            "max_runtime_seconds",
            "repeat_delay_ms",
        ):
            self.vars[name].trace_add("write", self._mark_dirty)
        for variable in self.modifier_vars.values():
            variable.trace_add("write", self._mark_dirty)
        self.vars["step_action"].trace_add("write", self._on_step_editor_change)
        self.vars["step_key"].trace_add("write", self._mark_step_draft)
        self.vars["step_ms"].trace_add("write", self._mark_step_draft)

        tk.Label(top, text="名称", bg=PANEL, fg=MUTED, font=("Microsoft YaHei UI", 8)).grid(
            row=0, column=0, sticky="w"
        )
        name_entry = self._entry(top, self.vars["name"])
        name_entry.grid(row=1, column=0, columnspan=3, sticky="ew", padx=(0, 10))
        tk.Checkbutton(
            top,
            text="启用",
            variable=self.vars["enabled"],
            bg=PANEL,
            fg=TEXT,
            activebackground=PANEL,
            activeforeground=TEXT,
            selectcolor=ACCENT_DARK,
            highlightthickness=0,
            bd=0,
            font=("Microsoft YaHei UI", 9, "bold"),
        ).grid(row=1, column=3, sticky="e")
        top.grid_columnconfigure(0, weight=1)

        trigger = tk.Frame(parent, bg=CONTROL, padx=12, pady=10)
        trigger.pack(fill="x", pady=(12, 10))
        tk.Label(
            trigger,
            text="如何启动这个宏",
            bg=CONTROL,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 7))
        tk.Label(trigger, text="主按键", bg=CONTROL, fg=MUTED).grid(
            row=1, column=0, sticky="w", pady=(0, 3)
        )
        tk.Label(trigger, text="同时按（可选）", bg=CONTROL, fg=MUTED).grid(
            row=1, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(0, 3)
        )
        self._key_picker(
            trigger,
            target="trigger_key",
            variable=self.vars["trigger_key"],
            values=TRIGGER_KEYS,
            width=7,
        ).grid(row=2, column=0, sticky="ew")
        for column, modifier in enumerate(("CTRL", "ALT", "SHIFT"), start=1):
            tk.Checkbutton(
                trigger,
                text=modifier,
                variable=self.modifier_vars[modifier],
                bg=CONTROL,
                fg=TEXT,
                activebackground=CONTROL,
                activeforeground=TEXT,
                selectcolor=ACCENT_DARK,
                highlightthickness=0,
                bd=0,
                font=("Segoe UI", 8, "bold"),
            ).grid(row=2, column=column, padx=(8, 0))
        trigger.grid_columnconfigure(4, weight=1)

        runtime_limit = tk.Frame(trigger, bg=CONTROL)
        runtime_limit.grid(row=3, column=0, columnspan=6, sticky="ew", pady=(9, 0))
        tk.Label(
            runtime_limit,
            text="运行方式",
            bg=CONTROL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left")
        self._combo(runtime_limit, self.vars["mode"], tuple(MODE_IDS), width=17).pack(
            side="left", padx=(7, 12)
        )
        tk.Label(
            runtime_limit,
            text="最长运行",
            bg=CONTROL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left")
        self._entry(runtime_limit, self.vars["max_runtime_seconds"], width=5).pack(
            side="left", padx=(7, 5)
        )
        tk.Label(
            runtime_limit,
            text="秒",
            bg=CONTROL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).pack(side="left")

        self.advanced_button = self._button(
            runtime_limit,
            "更多",
            self._toggle_advanced_settings,
            width=4,
        )
        self.advanced_button.pack(side="right")
        steps_header = tk.Frame(parent, bg=PANEL)
        steps_header.pack(fill="x", pady=(2, 6))
        tk.Label(
            steps_header,
            text="动作步骤",
            bg=PANEL,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left")
        tk.Label(
            steps_header,
            text="按执行顺序从上到下排列",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")

        style = ttk.Style(parent)
        style.theme_use("clam")
        style.configure(
            "Macro.Treeview",
            background="#F7F2E9",
            fieldbackground="#F7F2E9",
            foreground=TEXT,
            bordercolor=OUTLINE,
            rowheight=28,
            font=("Microsoft YaHei UI", 9),
        )
        style.configure(
            "Macro.Treeview.Heading",
            background=CONTROL,
            foreground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        style.map(
            "Macro.Treeview",
            background=[("selected", "#E4D6C4")],
            foreground=[("selected", TEXT)],
        )
        tree_host = tk.Frame(parent, bg=OUTLINE, padx=1, pady=1)
        self.step_tree = ttk.Treeview(
            tree_host,
            columns=("index", "action", "key", "duration"),
            show="headings",
            selectmode="browse",
            style="Macro.Treeview",
            # Two visible rows are the supported minimum; the packed tree
            # expands to show more rows whenever the editor has room.
            height=2,
        )
        for column, title, width, anchor in (
            ("index", "#", 38, "center"),
            ("action", "动作", 100, "w"),
            ("key", "按键", 100, "center"),
            ("duration", "时长 / 等待", 130, "center"),
        ):
            self.step_tree.heading(column, text=title)
            self.step_tree.column(column, width=width, anchor=anchor, stretch=column == "action")
        self.step_tree.pack(fill="both", expand=True)
        step_scrollbar = ttk.Scrollbar(
            tree_host,
            orient="vertical",
            command=self.step_tree.yview,
        )
        self.step_tree.configure(yscrollcommand=step_scrollbar.set)
        self.step_tree.pack_forget()
        self.step_tree.pack(side="left", fill="both", expand=True)
        step_scrollbar.pack(side="right", fill="y")
        self.step_tree.bind("<<TreeviewSelect>>", self._load_selected_step)

        editor = tk.Frame(parent, bg=PANEL)
        editor.pack(side="bottom", fill="x", pady=(9, 0))
        fields = tk.Frame(editor, bg=PANEL)
        fields.pack(fill="x")
        tk.Label(fields, text="动作", bg=PANEL, fg=MUTED).grid(row=0, column=0, sticky="w")
        self.step_key_label = tk.Label(fields, text="按键", bg=PANEL, fg=MUTED)
        self.step_key_label.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.step_ms_label = tk.Label(fields, text="按住时长 (ms)", bg=PANEL, fg=MUTED)
        self.step_ms_label.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._combo(fields, self.vars["step_action"], tuple(ACTION_IDS), width=10).grid(row=1, column=0, sticky="ew")
        self._key_picker(
            fields,
            target="step_key",
            variable=self.vars["step_key"],
            values=STEP_KEYS,
            width=7,
        ).grid(row=1, column=1, sticky="ew", padx=(8, 0))
        self.step_ms_entry = self._entry(fields, self.vars["step_ms"], width=12)
        self.step_ms_entry.grid(row=1, column=2, sticky="ew", padx=(8, 0))
        fields.grid_columnconfigure(0, weight=1)
        fields.grid_columnconfigure(1, weight=1)
        fields.grid_columnconfigure(2, weight=1)
        actions = tk.Frame(editor, bg=PANEL)
        actions.pack(fill="x", pady=(8, 0))
        self._button(actions, "添加到末尾", self._add_step, accent=True, width=10).pack(side="left")
        self._button(actions, "替换所选", self._replace_step, width=9).pack(side="left", padx=5)
        self._button(actions, "删除所选", self._remove_step, danger=True, width=9).pack(side="left")
        self._button(actions, "下移", lambda: self._move_step(1), width=6).pack(side="right")
        self._button(actions, "上移", lambda: self._move_step(-1), width=6).pack(side="right", padx=(0, 5))
        tree_host.pack(fill="both", expand=True)
        self._sync_step_editor_state()

    def _toggle_advanced_settings(self) -> None:
        if self.advanced_button is None or self.window is None:
            return
        if self.advanced_window is not None:
            self._close_advanced_settings()
            return
        dialog = tk.Toplevel(self.window)
        self.advanced_window = dialog
        self._advanced_visible = True
        self.advanced_button.configure(text="收起")
        dialog.title("宏高级设置")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.geometry(f"360x155+{self.window.winfo_rootx() + 90}+{self.window.winfo_rooty() + 150}")
        body = tk.Frame(dialog, bg=PANEL, padx=18, pady=16)
        body.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(
            body,
            text="循环间隔",
            bg=PANEL,
            fg=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(
            body,
            text="每轮间隔",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(12, 0))
        self._entry(body, self.vars["repeat_delay_ms"], width=9).grid(
            row=1, column=1, sticky="w", padx=(8, 5), pady=(12, 0)
        )
        tk.Label(body, text="ms", bg=PANEL, fg=MUTED).grid(
            row=1, column=2, sticky="w", pady=(12, 0)
        )
        tk.Label(
            body,
            text="仅循环模式使用；最长运行时间仍由主界面的秒数控制。",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))
        dialog.protocol("WM_DELETE_WINDOW", self._close_advanced_settings)
        dialog.lift()

    def _close_advanced_settings(self) -> None:
        dialog = self.advanced_window
        self.advanced_window = None
        self._advanced_visible = False
        if self.advanced_button is not None:
            try:
                self.advanced_button.configure(text="更多")
            except tk.TclError:
                pass
        if dialog is not None:
            try:
                dialog.destroy()
            except tk.TclError:
                pass

    def _button(
        self,
        parent: tk.Misc,
        text: str,
        command: Any,
        *,
        accent: bool = False,
        danger: bool = False,
        width: int = 10,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT_DARK if accent else CONTROL,
            fg="#FFFAF5" if accent else BAD if danger else TEXT,
            activebackground="#C86040" if accent else CONTROL_HOVER,
            activeforeground="#FFFAF5" if accent else TEXT,
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
            width=width,
            cursor="hand2",
            font=("Microsoft YaHei UI", 8, "bold"),
        )

    def _entry(
        self, parent: tk.Misc, variable: tk.Variable, *, width: int = 20
    ) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            bg=CONTROL,
            fg=TEXT,
            insertbackground=TEXT,
            selectbackground="#E4D6C4",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=OUTLINE,
            highlightcolor=ACCENT,
            font=("Microsoft YaHei UI", 9),
        )

    def _key_picker(
        self,
        parent: tk.Misc,
        *,
        target: str,
        variable: tk.Variable,
        values: tuple[str, ...],
        width: int,
    ) -> tk.Frame:
        host = tk.Frame(parent, bg=CONTROL if parent.cget("bg") == CONTROL else PANEL)
        combo = self._combo(host, variable, values, width=width)
        combo.pack(side="left", fill="x", expand=True)
        button = self._button(
            host,
            "录入",
            lambda selected=target: self._toggle_key_capture(selected),
            width=5,
        )
        button.configure(bg=CAPTURE_CONTROL, activebackground=CAPTURE_HOVER)
        button.pack(side="left", padx=(5, 0))
        button.bind(
            "<KeyPress>",
            lambda event, selected=target: self._capture_keypress(selected, event),
        )
        button.bind(
            "<FocusOut>",
            lambda _event, selected=target: self._cancel_key_capture(
                target=selected, silent=True
            ),
        )
        self._key_combos[target] = combo
        self._capture_buttons[target] = button
        return host

    def _toggle_key_capture(self, target: str) -> None:
        if self._capture_target == target:
            self._cancel_key_capture(target=target, silent=False)
            return
        self._cancel_key_capture(silent=True)
        button = self._capture_buttons.get(target)
        if button is None:
            return
        self.controller.stop_all("capture_key")
        self._capture_target = target
        self._capture_release_key = None
        button.configure(
            text="等待…",
            bg="#DDE8E2",
            activebackground="#D3E1DA",
            fg=GOOD,
        )
        button.focus_set()
        self._set_runtime("● 正在录入按键", PAUSED)
        self._set_status(
            "请直接按下目标键；再次点击“等待…”或移开焦点可取消。",
            error=False,
        )

    def _capture_keypress(self, target: str, event: tk.Event[Any]) -> str | None:
        if self._capture_target != target:
            return None
        raw_key = key_from_tk_keysym(str(event.keysym))
        key = captured_key_for_target(target, str(event.keysym))
        if key is None:
            shown = raw_key or str(event.keysym)
            self._set_status(f"不支持录入“{shown}”；原值未更改，可继续按键或用下拉框。", error=True)
            return "break"
        unchanged = str(self.vars[target].get()) == key
        if not unchanged:
            self.vars[target].set(key)
        self._cancel_key_capture(target=target, silent=True, release_key=key)
        if unchanged:
            self._set_status(f"按键仍为 {key}；未产生新修改。", error=False)
        elif target == "step_key":
            self._set_status(f"已录入 {key}；请添加到末尾或替换所选。", error=False)
        else:
            self._set_status(f"已录入 {key}；修改尚未保存。", error=False)
        return "break"

    def _cancel_key_capture(
        self,
        *,
        target: str | None = None,
        silent: bool,
        release_key: str | None = None,
    ) -> None:
        if self._capture_target is None:
            return
        if target is not None and target != self._capture_target:
            return
        active = self._capture_target
        self._capture_target = None
        button = self._capture_buttons.get(active)
        if button is not None:
            try:
                button.configure(
                    text="录入",
                    bg=CAPTURE_CONTROL,
                    activebackground=CAPTURE_HOVER,
                    fg=TEXT,
                )
            except tk.TclError:
                pass
        self._capture_release_key = release_key
        self._rearm_required = True
        if not silent:
            self._set_status("已取消按键录入；原值未更改。", error=False)

    def _combo(
        self, parent: tk.Misc, variable: tk.Variable, values: tuple[str, ...], *, width: int
    ) -> ttk.Combobox:
        style = ttk.Style(parent)
        style.configure(
            "Macro.TCombobox",
            fieldbackground=CONTROL,
            background=CONTROL,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=OUTLINE,
        )
        style.map(
            "Macro.TCombobox",
            fieldbackground=[("readonly", CONTROL)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", CONTROL)],
            selectforeground=[("readonly", TEXT)],
        )
        return ttk.Combobox(
            parent,
            textvariable=variable,
            values=values,
            state="readonly",
            width=width,
            style="Macro.TCombobox",
            font=("Microsoft YaHei UI", 9),
        )

    def _tick(self) -> None:
        if self._closed:
            return
        self._drain_statuses()
        emergency = _is_key_down(EMERGENCY_KEY) and all(
            _is_key_down(modifier) for modifier in EMERGENCY_MODIFIERS
        )
        if emergency and not self._emergency_down:
            self.controller.stop_all("emergency_stop")
            self._rearm_required = True
            self._set_runtime("● 已紧急停止", BAD)
        self._emergency_down = emergency

        enabled = tuple(profile for profile in self.profiles if profile.enabled)
        chord_states = {
            profile.id: _is_key_down(profile.trigger.key)
            and all(_is_key_down(modifier) for modifier in profile.trigger.modifiers)
            for profile in enabled
        }
        captured_key_down = bool(
            self._capture_release_key and _is_key_down(self._capture_release_key)
        )
        if self._capture_target is not None:
            for profile in enabled:
                self.controller.update_trigger(profile, False)
            self._set_runtime("● 正在录入按键", PAUSED)
        elif self.errors or self._rearm_required:
            for profile in enabled:
                self.controller.update_trigger(profile, False)
            if (
                self._rearm_required
                and not emergency
                and not captured_key_down
                and not any(chord_states.values())
            ):
                self._rearm_required = False
                self._capture_release_key = None
                self._set_runtime("● 已重新待命", GOOD)
        else:
            for profile in enabled:
                self.controller.update_trigger(profile, chord_states[profile.id])
        if (
            self._runtime_state is MacroState.BLOCKED_FOCUS
            and not any(chord_states.values())
            and self._capture_target is None
        ):
            self._runtime_state = None
            self._set_runtime("● 待命 · 仅在游戏前台执行", MUTED)
        self._after_id = self.root.after(20, self._tick)

    def _drain_statuses(self) -> None:
        latest: MacroStatus | None = None
        while True:
            try:
                latest = self._status_queue.get_nowait()
            except queue.Empty:
                break
        if latest is None:
            return
        self._runtime_state = latest.state
        text, color = runtime_presentation(latest.state)
        self._set_runtime(text, color)

    def _set_runtime(self, text: str, color: str) -> None:
        if self.runtime_label is not None:
            try:
                self.runtime_label.configure(text=text, fg=color)
            except tk.TclError:
                pass

    def _mark_dirty(self, *_args: Any) -> None:
        if self._loading_form:
            return
        self._dirty = True
        if self._step_draft_dirty:
            self._set_status("● 宏有修改；当前步骤草稿还需添加或替换。", error=False)
        else:
            self._set_status("● 修改未保存", error=False)

    def _on_step_editor_change(self, *_args: Any) -> None:
        self._sync_step_editor_state()
        self._mark_step_draft()

    def _mark_step_draft(self, *_args: Any) -> None:
        if self._loading_form:
            return
        self._step_draft_dirty = True
        self._set_status("● 当前步骤尚未应用，请点击“添加到末尾”或“替换所选”。", error=False)

    def _sync_step_editor_state(self) -> None:
        if not self.vars:
            return
        action = ACTION_IDS.get(str(self.vars["step_action"].get()), "tap")
        combo = self._key_combos.get("step_key")
        capture = self._capture_buttons.get("step_key")
        if action == "wait" and self._capture_target == "step_key":
            self._cancel_key_capture(target="step_key", silent=True)
        if combo is not None:
            combo.configure(state="disabled" if action == "wait" else "readonly")
        if capture is not None:
            capture.configure(state="disabled" if action == "wait" else "normal")
        if self.step_key_label is not None:
            self.step_key_label.configure(
                text="按键（等待时忽略）" if action == "wait" else "按键"
            )
        if self.step_ms_label is not None:
            self.step_ms_label.configure(
                text={
                    "tap": "按住时长 (ms)",
                    "wait": "等待时间 (ms)",
                    "down": "无需填写时长",
                    "up": "无需填写时长",
                }[action]
            )
        if self.step_ms_entry is not None:
            self.step_ms_entry.configure(
                state="normal" if action in {"tap", "wait"} else "disabled"
            )

    def _set_status(self, text: str, *, error: bool) -> None:
        if self.status_label is not None:
            self.status_label.configure(text=text, fg=BAD if error else MUTED)

    def _refresh_profile_list(self, *, select: int | None = None) -> None:
        if self.profile_list is None:
            return
        self._loading_form = True
        self.profile_list.delete(0, "end")
        for profile in self.profiles:
            marker = "●" if profile.enabled else "○"
            self.profile_list.insert("end", f"{marker}  {profile.name}")
        self.profile_list.selection_clear(0, "end")
        if select is not None and 0 <= select < len(self.profiles):
            self.profile_list.selection_set(select)
            self.profile_list.activate(select)
            self._selected_index = select
            self._load_profile(self.profiles[select])
        else:
            self._selected_index = None
            self._clear_form()
        self._loading_form = False
        self._dirty = False
        self._step_draft_dirty = False

    def _on_profile_select(self, _event: tk.Event[Any]) -> None:
        if self._loading_form or self.profile_list is None:
            return
        selection = self.profile_list.curselection()
        if not selection:
            return
        next_index = int(selection[0])
        if next_index == self._selected_index:
            return
        if (self._dirty or self._step_draft_dirty) and not messagebox.askyesno(
            "未保存修改", "当前宏有未保存修改，是否放弃并切换？", parent=self.window
        ):
            self._loading_form = True
            self.profile_list.selection_clear(0, "end")
            if self._selected_index is not None:
                self.profile_list.selection_set(self._selected_index)
            self._loading_form = False
            return
        self._selected_index = next_index
        self._load_profile(self.profiles[next_index])

    def _load_profile(self, profile: MacroProfile) -> None:
        self._cancel_key_capture(silent=True)
        self._loading_form = True
        self.vars["name"].set(profile.name)
        self.vars["enabled"].set(profile.enabled)
        self.vars["trigger_key"].set(profile.trigger.key)
        self.vars["mode"].set(MODE_LABELS[profile.trigger.mode])
        self.vars["max_runtime_seconds"].set(
            seconds_text_from_milliseconds(profile.limits.max_runtime_ms)
        )
        self.vars["repeat_delay_ms"].set(str(profile.limits.repeat_delay_ms))
        for modifier, variable in self.modifier_vars.items():
            variable.set(modifier in profile.trigger.modifiers)
        self._editing_steps = macro_profile_to_dict(profile)["steps"]
        self._loaded_step_index = None
        self._refresh_steps()
        self._loading_form = False
        self._dirty = False
        self._step_draft_dirty = False
        self._set_status("已载入；修改后点击“保存当前宏”才会生效。", error=False)

    def _clear_form(self) -> None:
        if not self.vars:
            return
        self._cancel_key_capture(silent=True)
        self._loading_form = True
        self.vars["name"].set("")
        self.vars["enabled"].set(False)
        self.vars["trigger_key"].set("F5")
        self.vars["mode"].set(MODE_LABELS["once"])
        self.vars["max_runtime_seconds"].set("60")
        self.vars["repeat_delay_ms"].set("80")
        self._editing_steps = []
        self._loaded_step_index = None
        self._refresh_steps()
        self._loading_form = False
        self._dirty = False
        self._step_draft_dirty = False

    def _new_profile(self, mode: str) -> None:
        if self.errors:
            self._set_status("配置文件含错误；为避免覆盖原内容，暂不允许新建。", error=True)
            return
        if (self._dirty or self._step_draft_dirty) and not messagebox.askyesno(
            "未保存修改", "当前修改尚未保存，是否放弃并新建？", parent=self.window
        ):
            return
        template_index = {"once": 0, "hold_repeat": 1, "toggle_repeat": 2}[mode]
        data = deepcopy(default_profile_data()[template_index])
        existing_ids = {profile.id for profile in self.profiles}
        counter = 1
        base_id = mode.replace("_repeat", "")
        while f"{base_id}-{counter}" in existing_ids:
            counter += 1
        data["id"] = f"{base_id}-{counter}"
        data["name"] = {"once": "新建单次宏", "hold_repeat": "新建按住宏", "toggle_repeat": "新建开关宏"}[mode]
        data["enabled"] = False
        data["steps"] = []
        profile = parse_macro_profile(data)
        self.profiles = (*self.profiles, profile)
        try:
            save_macro_config(self.config_path, self.profiles)
        except (OSError, MacroProfileError) as exception:
            self.profiles = self.profiles[:-1]
            self._set_status(f"新建失败：{exception}", error=True)
            return
        self.errors = []
        self.controller.stop_all("config_changed")
        self._refresh_profile_list(select=len(self.profiles) - 1)

    def _delete_selected(self) -> None:
        if self.errors:
            self._set_status("配置文件含错误；为避免覆盖原内容，暂不允许删除。", error=True)
            return
        if self._selected_index is None:
            return
        profile = self.profiles[self._selected_index]
        if not messagebox.askyesno(
            "删除宏", f"确定删除“{profile.name}”吗？", parent=self.window
        ):
            return
        remaining = tuple(
            item for index, item in enumerate(self.profiles) if index != self._selected_index
        )
        try:
            save_macro_config(self.config_path, remaining)
        except (OSError, MacroProfileError) as exception:
            self._set_status(f"删除失败：{exception}", error=True)
            return
        self.profiles = remaining
        self.errors = []
        self.controller.stop_all("config_changed")
        next_index = min(self._selected_index, len(remaining) - 1) if remaining else None
        self._refresh_profile_list(select=next_index)

    def _save_selected(self) -> None:
        if self.errors:
            self._set_status("配置文件含错误；为避免覆盖原内容，暂不允许保存。", error=True)
            return
        if self._selected_index is None:
            self._set_status("请先选择或新建一个宏。", error=True)
            return
        if self._step_draft_dirty:
            self._set_status(
                "当前步骤设置尚未应用；请先点击“添加到末尾”或“替换所选”。",
                error=True,
            )
            return
        original = self.profiles[self._selected_index]
        try:
            data = {
                "schema_version": 1,
                "id": original.id,
                "name": str(self.vars["name"].get()),
                "enabled": bool(self.vars["enabled"].get()),
                "trigger": {
                    "key": str(self.vars["trigger_key"].get()),
                    "modifiers": [
                        modifier
                        for modifier, variable in self.modifier_vars.items()
                        if variable.get()
                    ],
                    "mode": MODE_IDS[str(self.vars["mode"].get())],
                },
                "limits": {
                    "foreground_only": True,
                    "max_runtime_ms": milliseconds_from_seconds_text(
                        str(self.vars["max_runtime_seconds"].get())
                    ),
                    "repeat_delay_ms": int(str(self.vars["repeat_delay_ms"].get())),
                },
                "steps": deepcopy(self._editing_steps),
            }
            updated = parse_macro_profile(data)
            profiles = list(self.profiles)
            profiles[self._selected_index] = updated
            save_macro_config(self.config_path, profiles)
        except (KeyError, ValueError, OSError, MacroProfileError) as exception:
            self._set_status(f"无法保存：{exception}", error=True)
            return
        self.controller.stop_all("config_changed")
        self.profiles = tuple(profiles)
        self.errors = []
        self._dirty = False
        self._step_draft_dirty = False
        self._refresh_profile_list(select=self._selected_index)
        self._set_status("已保存；启用的宏将在游戏前台生效。", error=False)

    def _step_from_editor(self) -> dict[str, Any]:
        action = ACTION_IDS[str(self.vars["step_action"].get())]
        if action == "wait":
            return {"type": "wait", "duration_ms": int(str(self.vars["step_ms"].get()))}
        step: dict[str, Any] = {
            "type": "key",
            "key": str(self.vars["step_key"].get()),
            "action": action,
        }
        if action == "tap":
            step["hold_ms"] = int(str(self.vars["step_ms"].get()))
        return step

    def _add_step(self) -> None:
        try:
            step = self._step_from_editor()
        except ValueError:
            self._set_status("时长必须是整数毫秒。", error=True)
            return
        self._editing_steps.append(step)
        self._refresh_steps(select=len(self._editing_steps) - 1)
        self._loaded_step_index = len(self._editing_steps) - 1
        self._step_draft_dirty = False
        self._mark_dirty()

    def _replace_step(self) -> None:
        index = self._selected_step_index()
        if index is None:
            self._set_status("请先选择要替换的步骤。", error=True)
            return
        try:
            self._editing_steps[index] = self._step_from_editor()
        except ValueError:
            self._set_status("时长必须是整数毫秒。", error=True)
            return
        self._refresh_steps(select=index)
        self._loaded_step_index = index
        self._step_draft_dirty = False
        self._mark_dirty()

    def _remove_step(self) -> None:
        index = self._selected_step_index()
        if index is None:
            return
        del self._editing_steps[index]
        self._loaded_step_index = None
        self._refresh_steps(select=min(index, len(self._editing_steps) - 1))
        self._mark_dirty()

    def _move_step(self, direction: int) -> None:
        index = self._selected_step_index()
        if index is None:
            return
        target = index + direction
        if not 0 <= target < len(self._editing_steps):
            return
        self._editing_steps[index], self._editing_steps[target] = (
            self._editing_steps[target],
            self._editing_steps[index],
        )
        self._refresh_steps(select=target)
        self._loaded_step_index = target
        self._mark_dirty()

    def _selected_step_index(self) -> int | None:
        if self.step_tree is None:
            return None
        selection = self.step_tree.selection()
        return int(selection[0]) if selection else None

    def _refresh_steps(self, *, select: int | None = None) -> None:
        if self.step_tree is None:
            return
        children = self.step_tree.get_children()
        if children:
            self.step_tree.delete(*children)
        for index, step in enumerate(self._editing_steps):
            if step["type"] == "wait":
                values = (index + 1, ACTION_LABELS["wait"], "—", f"{step['duration_ms']} ms")
            else:
                duration = f"{step.get('hold_ms', '—')} ms" if step["action"] == "tap" else "—"
                values = (index + 1, ACTION_LABELS[step["action"]], step["key"], duration)
            self.step_tree.insert("", "end", iid=str(index), values=values)
        if select is not None and 0 <= select < len(self._editing_steps):
            self.step_tree.selection_set(str(select))
            self.step_tree.focus(str(select))

    def _load_selected_step(self, _event: tk.Event[Any]) -> None:
        if self._loading_form:
            return
        index = self._selected_step_index()
        if index is None:
            return
        if self._step_draft_dirty and index == self._loaded_step_index:
            return
        if self._step_draft_dirty and not messagebox.askyesno(
            "步骤尚未应用",
            "当前步骤设置尚未添加或替换，是否放弃并查看其他步骤？",
            parent=self.window,
        ):
            if self.step_tree is not None:
                self._loading_form = True
                selection = self.step_tree.selection()
                if selection:
                    self.step_tree.selection_remove(*selection)
                if (
                    self._loaded_step_index is not None
                    and 0 <= self._loaded_step_index < len(self._editing_steps)
                ):
                    self.step_tree.selection_set(str(self._loaded_step_index))
                    self.step_tree.focus(str(self._loaded_step_index))
                self._loading_form = False
            return
        step = self._editing_steps[index]
        self._loading_form = True
        if step["type"] == "wait":
            self.vars["step_action"].set(ACTION_LABELS["wait"])
            self.vars["step_ms"].set(str(step["duration_ms"]))
        else:
            self.vars["step_action"].set(ACTION_LABELS[step["action"]])
            self.vars["step_key"].set(step["key"])
            if step["action"] == "tap":
                self.vars["step_ms"].set(str(step["hold_ms"]))
        self._loading_form = False
        self._loaded_step_index = index
        self._step_draft_dirty = False
        self._sync_step_editor_state()

    def _close_window(self, *, force: bool = False) -> None:
        if self.window is None:
            return
        if not force and (self._dirty or self._step_draft_dirty) and not messagebox.askyesno(
            "未保存修改", "当前宏有未保存修改，是否放弃并关闭？", parent=self.window
        ):
            return
        self._cancel_key_capture(silent=True)
        self._close_advanced_settings()
        try:
            self.window.destroy()
        except tk.TclError:
            pass
        self.window = None
        self.profile_list = None
        self.status_label = None
        self.runtime_label = None
        self.step_tree = None
        self.advanced_window = None
        self.advanced_button = None
        self.step_key_label = None
        self.step_ms_label = None
        self.step_ms_entry = None
        self._key_combos.clear()
        self._capture_buttons.clear()
        self._capture_target = None
        self._capture_release_key = None
        self._advanced_visible = False
        self.vars.clear()
        self.modifier_vars.clear()
        self._editing_steps.clear()
        self._selected_index = None
        self._loaded_step_index = None
        self._dirty = False
        self._step_draft_dirty = False
