from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import queue
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

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


BG = "#10151B"
PANEL = "#171E26"
CONTROL = "#222C37"
CONTROL_HOVER = "#2D3946"
OUTLINE = "#3B4857"
TEXT = "#F2F6FA"
MUTED = "#8E9CAC"
ACCENT = "#E7BD5A"
ACCENT_DARK = "#3B311A"
GOOD = "#77D99B"
BAD = "#FF837B"

MODE_LABELS = {
    "once": "按一次：执行一遍",
    "hold_repeat": "按住：持续循环",
    "toggle_repeat": "开关：再按一次停止",
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
        self._loading_form = False
        self._dirty = False
        self._emergency_down = False
        self._rearm_required = False
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
        window.minsize(780, 590)
        window.attributes("-topmost", False)

        header = tk.Frame(window, bg=BG, padx=20, pady=16)
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
            text="● 待命",
            bg=BG,
            fg=GOOD,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        self.runtime_label.pack(side="right", pady=(8, 0))

        notice = tk.Frame(window, bg="#211C10", padx=14, pady=9)
        notice.pack(fill="x", padx=20)
        tk.Label(
            notice,
            text="紧急停止  Ctrl + Shift + F12",
            bg="#211C10",
            fg="#FFE08A",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side="left")
        tk.Label(
            notice,
            text="切出游戏、退出或修改配置时也会立即停止并释放按键。",
            bg="#211C10",
            fg="#C4B98F",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")

        content = tk.Frame(window, bg=BG, padx=20, pady=14)
        content.pack(fill="both", expand=True)
        left = tk.Frame(content, bg=PANEL, width=240, padx=12, pady=12)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        right = tk.Frame(content, bg=PANEL, padx=16, pady=14)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        tk.Label(
            left,
            text="宏方案",
            bg=PANEL,
            fg=ACCENT,
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        self.profile_list = tk.Listbox(
            left,
            bg="#121820",
            fg=TEXT,
            selectbackground="#3A311B",
            selectforeground="#FFE28A",
            activestyle="none",
            highlightthickness=1,
            highlightbackground=OUTLINE,
            relief="flat",
            bd=0,
            font=("Microsoft YaHei UI", 9),
        )
        self.profile_list.pack(fill="both", expand=True)
        self.profile_list.bind("<<ListboxSelect>>", self._on_profile_select)

        self._button(left, "＋ 新建单次宏", lambda: self._new_profile("once")).pack(
            fill="x", pady=(10, 0)
        )
        self._button(
            left, "＋ 新建按住宏", lambda: self._new_profile("hold_repeat")
        ).pack(fill="x", pady=(5, 0))
        self._button(
            left, "＋ 新建开关宏", lambda: self._new_profile("toggle_repeat")
        ).pack(fill="x", pady=(5, 0))
        self._button(left, "删除所选", self._delete_selected, danger=True).pack(
            fill="x", pady=(7, 0)
        )

        self._build_editor(right)

        footer = tk.Frame(window, bg=BG, padx=20, pady=0)
        footer.pack(fill="x")
        self.status_label = tk.Label(
            footer,
            text="",
            bg=BG,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
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
        footer.pack(side="bottom", fill="x", pady=(0, 16))
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
        height = min(760, max(590, window.winfo_screenheight() - 120))
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
            "max_runtime_ms": tk.StringVar(value="10000"),
            "repeat_delay_ms": tk.StringVar(value="80"),
            "step_action": tk.StringVar(value=ACTION_LABELS["tap"]),
            "step_key": tk.StringVar(value="J"),
            "step_ms": tk.StringVar(value="50"),
        }
        self.modifier_vars = {
            key: tk.BooleanVar(value=False) for key in ("CTRL", "ALT", "SHIFT")
        }
        for variable in (*self.vars.values(), *self.modifier_vars.values()):
            variable.trace_add("write", self._mark_dirty)

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

        trigger = tk.Frame(parent, bg="#131A22", padx=12, pady=10)
        trigger.pack(fill="x", pady=(12, 10))
        tk.Label(
            trigger,
            text="触发方式",
            bg="#131A22",
            fg=ACCENT,
            font=("Microsoft YaHei UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 7))
        self._combo(trigger, self.vars["trigger_key"], TRIGGER_KEYS, width=10).grid(
            row=1, column=0, sticky="ew"
        )
        for column, modifier in enumerate(("CTRL", "ALT", "SHIFT"), start=1):
            tk.Checkbutton(
                trigger,
                text=modifier,
                variable=self.modifier_vars[modifier],
                bg="#131A22",
                fg=TEXT,
                activebackground="#131A22",
                activeforeground=TEXT,
                selectcolor=ACCENT_DARK,
                highlightthickness=0,
                bd=0,
                font=("Segoe UI", 8, "bold"),
            ).grid(row=1, column=column, padx=(8, 0))
        self._combo(trigger, self.vars["mode"], tuple(MODE_IDS), width=22).grid(
            row=1, column=4, sticky="e", padx=(16, 0)
        )
        trigger.grid_columnconfigure(4, weight=1)

        limits = tk.Frame(trigger, bg="#131A22")
        limits.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(9, 0))
        tk.Label(limits, text="最长运行 (ms)", bg="#131A22", fg=MUTED).pack(side="left")
        self._entry(limits, self.vars["max_runtime_ms"], width=9).pack(
            side="left", padx=(6, 18)
        )
        tk.Label(limits, text="每轮间隔 (ms)", bg="#131A22", fg=MUTED).pack(side="left")
        self._entry(limits, self.vars["repeat_delay_ms"], width=9).pack(
            side="left", padx=(6, 0)
        )

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
            text="按下的键必须在后续抬起；停止路径会兜底释放",
            bg=PANEL,
            fg=MUTED,
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right")

        style = ttk.Style(parent)
        style.theme_use("clam")
        style.configure(
            "Macro.Treeview",
            background="#121820",
            fieldbackground="#121820",
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
            font=("Microsoft YaHei UI", 8, "bold"),
        )
        style.map("Macro.Treeview", background=[("selected", "#4A3D1D")])
        tree_host = tk.Frame(parent, bg=OUTLINE, padx=1, pady=1)
        tree_host.pack(fill="both", expand=True)
        self.step_tree = ttk.Treeview(
            tree_host,
            columns=("index", "action", "key", "duration"),
            show="headings",
            selectmode="browse",
            style="Macro.Treeview",
            height=6,
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
        self.step_tree.bind("<<TreeviewSelect>>", self._load_selected_step)

        editor = tk.Frame(parent, bg=PANEL)
        editor.pack(fill="x", pady=(9, 0))
        self._combo(editor, self.vars["step_action"], tuple(ACTION_IDS), width=10).pack(
            side="left"
        )
        self._combo(editor, self.vars["step_key"], STEP_KEYS, width=10).pack(
            side="left", padx=(7, 0)
        )
        self._entry(editor, self.vars["step_ms"], width=8).pack(side="left", padx=(7, 0))
        tk.Label(editor, text="ms", bg=PANEL, fg=MUTED).pack(side="left", padx=(4, 10))
        self._button(editor, "添加", self._add_step, accent=True, width=6).pack(side="left")
        self._button(editor, "替换", self._replace_step, width=6).pack(side="left", padx=5)
        self._button(editor, "删除", self._remove_step, danger=True, width=6).pack(side="left")
        self._button(editor, "↑", lambda: self._move_step(-1), width=3).pack(
            side="right", padx=(5, 0)
        )
        self._button(editor, "↓", lambda: self._move_step(1), width=3).pack(side="right")

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
            fg="#FFE28A" if accent else BAD if danger else TEXT,
            activebackground="#514321" if accent else CONTROL_HOVER,
            activeforeground=TEXT,
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
            selectbackground="#5A4820",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=OUTLINE,
            highlightcolor=ACCENT,
            font=("Microsoft YaHei UI", 9),
        )

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
            font=("Microsoft YaHei UI", 8),
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
        if self.errors or self._rearm_required:
            for profile in enabled:
                self.controller.update_trigger(profile, False)
            if self._rearm_required and not emergency and not any(chord_states.values()):
                self._rearm_required = False
                self._set_runtime("● 已重新待命", GOOD)
        else:
            for profile in enabled:
                self.controller.update_trigger(profile, chord_states[profile.id])
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
        labels = {
            MacroState.RUNNING: "● 宏运行中",
            MacroState.BLOCKED_FOCUS: "● 非游戏前台，已拦截",
            MacroState.TIME_LIMIT: "● 已到最长运行时间",
            MacroState.ERROR: "● 宏执行错误",
            MacroState.STOPPING: "● 正在停止",
            MacroState.STOPPED: "● 已停止",
            MacroState.COMPLETED: "● 已完成",
            MacroState.TRIGGER_RELEASED: "● 已松开停止",
        }
        text = labels.get(latest.state, "● 待命")
        color = BAD if latest.state in {MacroState.ERROR, MacroState.BLOCKED_FOCUS} else GOOD
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
        self._set_status("● 修改未保存", error=False)

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

    def _on_profile_select(self, _event: tk.Event[Any]) -> None:
        if self._loading_form or self.profile_list is None:
            return
        selection = self.profile_list.curselection()
        if not selection:
            return
        next_index = int(selection[0])
        if next_index == self._selected_index:
            return
        if self._dirty and not messagebox.askyesno(
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
        self._loading_form = True
        self.vars["name"].set(profile.name)
        self.vars["enabled"].set(profile.enabled)
        self.vars["trigger_key"].set(profile.trigger.key)
        self.vars["mode"].set(MODE_LABELS[profile.trigger.mode])
        self.vars["max_runtime_ms"].set(str(profile.limits.max_runtime_ms))
        self.vars["repeat_delay_ms"].set(str(profile.limits.repeat_delay_ms))
        for modifier, variable in self.modifier_vars.items():
            variable.set(modifier in profile.trigger.modifiers)
        self._editing_steps = macro_profile_to_dict(profile)["steps"]
        self._refresh_steps()
        self._loading_form = False
        self._dirty = False
        self._set_status("已载入；修改后点击“保存当前宏”才会生效。", error=False)

    def _clear_form(self) -> None:
        if not self.vars:
            return
        self._loading_form = True
        self.vars["name"].set("")
        self.vars["enabled"].set(False)
        self._editing_steps = []
        self._refresh_steps()
        self._loading_form = False

    def _new_profile(self, mode: str) -> None:
        if self.errors:
            self._set_status("配置文件含错误；为避免覆盖原内容，暂不允许新建。", error=True)
            return
        if self._dirty and not messagebox.askyesno(
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
                    "max_runtime_ms": int(str(self.vars["max_runtime_ms"].get())),
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
        self._mark_dirty()

    def _remove_step(self) -> None:
        index = self._selected_step_index()
        if index is None:
            return
        del self._editing_steps[index]
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
        index = self._selected_step_index()
        if index is None:
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

    def _close_window(self, *, force: bool = False) -> None:
        if self.window is None:
            return
        if not force and self._dirty and not messagebox.askyesno(
            "未保存修改", "当前宏有未保存修改，是否放弃并关闭？", parent=self.window
        ):
            return
        try:
            self.window.destroy()
        except tk.TclError:
            pass
        self.window = None
        self.profile_list = None
        self.status_label = None
        self.runtime_label = None
        self.step_tree = None
        self.vars.clear()
        self.modifier_vars.clear()
        self._editing_steps.clear()
        self._selected_index = None
        self._dirty = False
