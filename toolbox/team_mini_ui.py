from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .feature_ui import ITEM_KIND_LABELS, inline_name
from .game_features import GameFeatureError, feature_value
from .windows_windowing import clamp_window_position, nearest_monitor_work_area, place_tk_window, prepare_tk_overlay, show_tk_window_no_activate, tk_window_is_visible, window_dpi
from .ui_theme import SURFACE, SIDEBAR, TEXT, MUTED, ACCENT, ACCENT_HOVER, ACCENT_TEXT, SELECTION


class TeamMiniWindow:
    """A read-only team view that can stay beside the combat HUD."""

    def __init__(self, owner: tk.Misc, service: Any, game_pid: Callable[[], int | None], toggle_enabled: Callable[[], None], visibility_changed: Callable[[bool], None]) -> None:
        self.owner = owner
        self.service = service
        self.game_pid = game_pid
        self.toggle_enabled = toggle_enabled
        self.visibility_changed = visibility_changed
        self.window: tk.Toplevel | None = None
        self.selected_slot: int | None = None
        self._team: list[dict[str, Any]] = []
        self._inventory_identity = ""
        self._dpi = 96
        self._locked = False
        self._fonts: list[tuple[tk.Misc, int, str]] = []

    def is_visible(self) -> bool:
        try:
            return self.window is not None and tk_window_is_visible(self.window)
        except tk.TclError:
            return False

    def toggle(self, anchor: tk.Misc | None = None) -> None:
        if self.is_visible():
            self.hide()
            return
        if self.window is None:
            self._build(anchor)
        assert self.window is not None
        self._locked = False
        self.lock_button.configure(text="锁定")
        prepare_tk_overlay(self.window)
        show_tk_window_no_activate(self.window)
        self.visibility_changed(True)
        self.refresh()

    def hide(self) -> None:
        if self.window is not None:
            self.window.withdraw()
        self.visibility_changed(False)

    def close(self) -> None:
        if self.window is not None:
            self.window.destroy()
        self.window = None
        self._fonts.clear()
        self.visibility_changed(False)

    def _font(self, size: int, weight: str = "normal") -> tuple[str, int, str]:
        return "Microsoft YaHei UI", -round(size*self._dpi/72), weight

    def _label(self, parent: tk.Misc, text: str, *, size: int = 12, bold: bool = False, muted: bool = False) -> tk.Label:
        label = tk.Label(parent, text=text, bg=SURFACE, fg=MUTED if muted else TEXT, anchor="w", justify="left", font=self._font(size, "bold" if bold else "normal"))
        self._fonts.append((label, size, "bold" if bold else "normal"))
        label.bind("<Configure>", lambda event: event.widget.configure(wraplength=max(80, event.width-8)))
        return label

    def _build(self, anchor: tk.Misc | None) -> None:
        self._dpi = window_dpi(anchor or self.owner)
        density = self._dpi/96
        window = tk.Toplevel(self.owner)
        window.withdraw()
        self.window = window
        window.title("LC2 队伍小窗")
        window.configure(bg=SURFACE)
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        window.attributes("-alpha", .86)
        try:
            window.attributes("-toolwindow", True)
        except tk.TclError:
            pass
        window.protocol("WM_DELETE_WINDOW", self.hide)
        ref = anchor or self.owner
        ref_x, ref_y = ref.winfo_x(), ref.winfo_y()
        x, y = ref_x+ref.winfo_width()+12, ref_y
        work = nearest_monitor_work_area(ref_x, ref_y, ref.winfo_width(), ref.winfo_height(), fallback_width=window.winfo_screenwidth(), fallback_height=window.winfo_screenheight())
        width, height = min(round(300*density), work[2]-work[0]-24), min(round(320*density), work[3]-work[1]-64)
        if x+width > work[2]:
            x = ref_x-width-12
        x, y = clamp_window_position(x, y, width, height, work)
        place_tk_window(window, width, height, x, y)
        window.minsize(round(260*density), round(260*density))
        content = tk.Frame(window, bg=SURFACE, padx=round(8*density), pady=round(6*density))
        content.pack(fill="both", expand=True)
        bar = tk.Frame(content, bg=SURFACE)
        bar.pack(fill="x", pady=(0, round(4*density)))
        close = tk.Button(bar, text="×", command=self.hide, relief="flat", bd=0, bg=SURFACE, fg=MUTED, activebackground=SELECTION, font=self._font(12), padx=5)
        close.pack(side="right", padx=(4, 0))
        self._fonts.append((close, 12, "normal"))
        self.lock_button = tk.Button(bar, text="锁定", command=self._lock, relief="flat", bd=0, bg=SIDEBAR, fg=TEXT, font=self._font(11), padx=6, pady=5)
        self.lock_button.pack(side="right", padx=(4, 0))
        self._fonts.append((self.lock_button, 11, "normal"))
        self.enable_button = tk.Button(bar, text="启用", command=self._toggle_enabled, relief="flat", bd=0, bg=ACCENT, fg=ACCENT_TEXT, activebackground=ACCENT_HOVER, activeforeground=ACCENT_TEXT, font=self._font(11, "bold"), padx=10, pady=5)
        self.enable_button.pack(side="right")
        self._fonts.append((self.enable_button, 11, "bold"))
        title = self._label(bar, "队伍", size=12, bold=True)
        title.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.status = self._label(content, "队伍状态已关闭", size=11, muted=True)
        self.status.pack(fill="x", pady=(0, 4))
        for widget in (bar, title):
            widget.bind("<ButtonPress-1>", self._begin_drag)
            widget.bind("<B1-Motion>", self._drag)
        member_row = tk.Frame(content, bg=SURFACE)
        member_row.pack(fill="x", pady=(0, 6))
        self.previous_member = tk.Button(member_row, text="‹", command=lambda:self._move_player(-1), relief="flat", bd=0, bg=SIDEBAR, fg=TEXT, font=self._font(12), padx=7)
        self.previous_member.pack(side="left")
        self.next_member = tk.Button(member_row, text="›", command=lambda:self._move_player(1), relief="flat", bd=0, bg=SIDEBAR, fg=TEXT, font=self._font(12), padx=7)
        self.next_member.pack(side="right")
        self._fonts.extend((button, 12, "normal") for button in (self.previous_member, self.next_member))
        self.members = self._label(member_row, "等待队伍数据", size=12, bold=True)
        self.members.pack(side="left", fill="x", expand=True, padx=6)
        self.vitals = self._label(content, "生命 —    法力 —", bold=True)
        self.vitals.pack(fill="x", pady=(0, 6))
        self.resources = self._label(content, "", size=11, muted=True)
        self.resources.pack(fill="x", pady=(0, 6))
        table = tk.Frame(content, bg=SURFACE)
        self.inventory = ttk.Treeview(table, columns=("detail",), show="tree headings", style="LC2TeamMini.Treeview", selectmode="browse")
        self.inventory.heading("#0", text="背包 / 刻印")
        self.inventory.heading("detail", text="数量 / 效果")
        self.inventory.column("#0", minwidth=100)
        self.inventory.column("detail", minwidth=90)
        self.inventory.bind("<Configure>", self._size_columns)
        self.inventory.bind("<<TreeviewSelect>>", self._select_item)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.inventory.yview)
        self.inventory.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.inventory.pack(fill="both", expand=True)
        self.item_detail = self._label(content, "选择物品查看完整名称和效果。", size=11, muted=True)
        self.item_detail.pack(side="bottom", fill="x", pady=(8, 0))
        table.pack(fill="both", expand=True)
        self._apply_fonts()
        prepare_tk_overlay(window)

    def _lock(self) -> None:
        assert self.window is not None
        self._locked = True
        self.lock_button.configure(text="已锁定")
        prepare_tk_overlay(self.window, click_through=True)
        self.refresh()

    def _begin_drag(self, event: Any) -> None:
        assert self.window is not None
        self._drag_origin = (event.x_root, event.y_root, self.window.winfo_x(), self.window.winfo_y())

    def _drag(self, event: Any) -> None:
        assert self.window is not None
        x, y, left, top = self._drag_origin
        place_tk_window(self.window, self.window.winfo_width(), self.window.winfo_height(), left+event.x_root-x, top+event.y_root-y)

    def _apply_fonts(self) -> None:
        assert self.window is not None
        self._dpi = window_dpi(self.window)
        for widget, size, weight in self._fonts:
            widget.configure(font=self._font(size, weight))
        style = ttk.Style(self.window)
        style.configure("LC2TeamMini.Treeview", font=self._font(12), rowheight=round(34*self._dpi/96), background=SURFACE, fieldbackground=SURFACE, foreground=TEXT)
        style.configure("LC2TeamMini.Treeview.Heading", font=self._font(11, "bold"))
        style.map("LC2TeamMini.Treeview", background=[("selected", SELECTION)], foreground=[("selected", TEXT)])

    def _size_columns(self, event: Any) -> None:
        width = max(200, event.width-4)
        self.inventory.column("#0", width=round(width*.55))
        self.inventory.column("detail", width=round(width*.45))

    def _toggle_enabled(self) -> None:
        try:
            self.toggle_enabled()
        except (GameFeatureError, OSError) as error:
            self.status.configure(text=str(error))
        else:
            self.refresh()

    def refresh(self) -> None:
        if not self.is_visible() or self.service is None:
            return
        assert self.window is not None
        if window_dpi(self.window) != self._dpi:
            self._apply_fonts()
        enabled = self.service.settings()["team_enabled"]
        self.enable_button.configure(text="暂停" if enabled else "启用")
        snapshot = self.service.snapshot(self.game_pid()) if enabled else None
        detail = snapshot.detail if snapshot is not None else "队伍状态已关闭 · 点击启用"
        self.status.configure(text=detail + (" · 已锁定" if self._locked else ""))
        self._team = list(snapshot.team) if snapshot is not None and snapshot.state == "ready" else []
        slots = [player["slot"] for player in self._team]
        if self.selected_slot not in slots:
            self.selected_slot = next((player["slot"] for player in self._team if not player.get("is_local")), slots[0] if slots else None)
        for button in (self.previous_member, self.next_member):
            button.configure(state="normal" if len(slots)>1 else "disabled")
        self._show_player()

    def _move_player(self, delta: int) -> None:
        slots = [player["slot"] for player in self._team]
        if slots:
            index = slots.index(self.selected_slot) if self.selected_slot in slots else 0
            self.selected_slot = slots[(index+delta)%len(slots)]
        self._show_player()

    def _show_player(self) -> None:
        player = next((row for row in self._team if row["slot"] == self.selected_slot), None)
        if player is None:
            self.members.configure(text="等待队伍数据")
            self.vitals.configure(text="生命 —    法力 —")
            self.resources.configure(text="等待队伍同步数据")
            self.inventory.delete(*self.inventory.get_children())
            self.item_detail.configure(text="选择物品查看完整名称和效果。")
            self._inventory_identity = ""
            return
        self.members.configure(text=inline_name(player.get("name") or "玩家") + (" · 自己" if player.get("is_local") else ""))
        self.vitals.configure(text=f"生命 {feature_value(player.get('hp'))} / {feature_value(player.get('max_hp'))}    法力 {feature_value(player.get('mp'))} / {feature_value(player.get('max_mp'))}")
        resources = player.get("resources", {})
        self.resources.configure(text="    ".join(f"{label} {feature_value(resources.get(key))}" for key, label in (("gold", "金币"), ("crystal", "魂晶"), ("iron", "魔铁锭"), ("coins", "虚灵硬币"))))
        identity = json.dumps([self.selected_slot, player.get("inventory_state"), player.get("items"), player.get("inscriptions")], ensure_ascii=False, sort_keys=True)
        if identity == self._inventory_identity:
            return
        self._inventory_identity = identity
        opened = {item: self.inventory.item(item, "open") for item in self.inventory.get_children()}
        position = self.inventory.yview()[0]
        self.inventory.delete(*self.inventory.get_children())
        bag = self.inventory.insert("", "end", iid="bag", text="背包", open=opened.get("bag", True))
        if player.get("inventory_state") != "ready":
            self.inventory.insert(bag, "end", text="背包暂不可读")
        elif not player.get("items"):
            self.inventory.insert(bag, "end", text="未发现已同步物品")
        for item in player.get("items", []):
            self.inventory.insert(bag, "end", text=f"{ITEM_KIND_LABELS.get(item.get('kind'), '物品')} · {inline_name(item.get('name', '未命名物品'))}", values=(f"× {feature_value(item.get('count'))}",))
        for index, inscription in enumerate(player.get("inscriptions", [])):
            iid = f"inscription-{index}"
            parent = self.inventory.insert("", "end", iid=iid, text=f"刻印 · {inscription.get('name', '')}", open=opened.get(iid, True))
            for gem in inscription.get("gems", []):
                self.inventory.insert(parent, "end", text=gem.get("name", "灵魂石"), values=(" / ".join(gem.get(key, "") for key in ("main", "sub") if gem.get(key)),))
        self.inventory.yview_moveto(position)
        self.item_detail.configure(text="选择物品查看完整名称和效果。")

    def _select_item(self, _event: Any = None) -> None:
        selected = self.inventory.selection()
        if not selected:
            return
        item = self.inventory.item(selected[0])
        self.item_detail.configure(text=" · ".join([item["text"], *(str(value) for value in item.get("values", []) if value)]))
