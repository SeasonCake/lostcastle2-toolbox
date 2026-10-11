from __future__ import annotations

import json
import math
import tkinter as tk
from tkinter import font as tkfont, ttk
from typing import Any, Callable

from .feature_ui import ITEM_KIND_LABELS, inline_name
from .game_features import GameFeatureError, feature_value
from .windows_windowing import clamp_window_position, nearest_monitor_work_area, place_tk_window, prepare_tk_overlay, show_tk_window_no_activate, tk_window_is_visible, window_dpi
from .ui_theme import BG, BORDER, SURFACE, SIDEBAR, TEXT, MUTED, ACCENT, ACCENT_HOVER, ACCENT_TEXT, SELECTION, GREEN


def vital_fraction(value: Any, maximum: Any) -> float | None:
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item) for item in (value, maximum)) or maximum <= 0:
        return None
    return min(1.0, max(0.0, value / maximum))


class TeamVitalMeter(tk.Frame):
    """Exact values with a compact proportional bar; unknown values stay unknown."""

    def __init__(self, parent: tk.Misc, owner: Any, title: str, color: str) -> None:
        super().__init__(parent, bg=SURFACE)
        self.color = color
        self.fraction: float | None = None
        self.title = owner._label(self, title, size=10, muted=True)
        self.title.pack(fill="x")
        self.value = owner._label(self, "—", size=11, bold=True)
        self.value.pack(fill="x")
        self.bar = tk.Canvas(self, bg=SURFACE, height=round(5*owner._dpi/96), bd=0, highlightthickness=0)
        self.bar.pack(fill="x", pady=(3, 0))
        self.bar.bind("<Configure>", self._draw)

    def set_values(self, value: Any, maximum: Any) -> None:
        fraction = vital_fraction(value, maximum)
        known = all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in (value, maximum))
        text = f"{feature_value(value)} / {feature_value(maximum)}" if known else "未同步"
        self.value.configure(text=text, fg=TEXT if known else MUTED)
        if fraction != self.fraction:
            self.fraction = fraction
            self._draw()

    def _draw(self, _event: Any = None) -> None:
        self.bar.delete("all")
        height = max(2, self.bar.winfo_height())
        left, right = height/2, max(height/2, self.bar.winfo_width()-height/2)
        self.bar.create_line(left, height/2, right, height/2, width=height, fill=BORDER, capstyle="round")
        if self.fraction is not None and self.fraction > 0:
            self.bar.create_line(left, height/2, left+(right-left)*self.fraction, height/2, width=height, fill=self.color, capstyle="round")


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
        self._member_full_name = "等待队伍数据"
        self._selected_detail = "点选物品查看详情"
        self.active_view = "status"
        self._inventory_roots: list[str] = []
        self._view_scrolls: dict[str, float] = {}
        self._layout_job: str | None = None

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
        window = self.window
        self.window = None
        if window is not None:
            if self._layout_job is not None:
                window.after_cancel(self._layout_job)
                self._layout_job = None
            window.destroy()
        self._fonts.clear()
        self.visibility_changed(False)

    def _font(self, size: int, weight: str = "normal") -> tuple[str, int, str]:
        return "Microsoft YaHei UI", -round(size*self._dpi/72), weight

    def _label(self, parent: tk.Misc, text: str, *, size: int = 12, bold: bool = False, muted: bool = False) -> tk.Label:
        label = tk.Label(parent, text=text, bg=parent.cget("bg"), fg=MUTED if muted else TEXT, anchor="w", justify="left", font=self._font(size, "bold" if bold else "normal"))
        self._fonts.append((label, size, "bold" if bold else "normal"))
        label.bind("<Configure>", lambda event: event.widget.configure(wraplength=max(40, event.width-4)))
        return label

    def _button(self, parent: tk.Misc, text: str, command: Callable[[], None], *, accent: bool = False) -> tk.Button:
        button = tk.Button(parent, text=text, command=command, relief="flat", bd=0, highlightthickness=0,
                           bg=ACCENT if accent else SIDEBAR, fg=ACCENT_TEXT if accent else TEXT,
                           activebackground=ACCENT_HOVER if accent else SELECTION, activeforeground=TEXT,
                           font=self._font(10, "bold" if accent else "normal"), padx=round(6*self._dpi/96), pady=round(3*self._dpi/96), cursor="hand2")
        self._fonts.append((button, 10, "bold" if accent else "normal"))
        return button

    def _build(self, anchor: tk.Misc | None) -> None:
        from .app_shell import RoundedPanel

        self._dpi = window_dpi(anchor or self.owner)
        density = self._dpi/96
        window = tk.Toplevel(self.owner)
        window.withdraw()
        self.window = window
        window.title("LC2 队伍小窗")
        window.configure(bg=BG, highlightthickness=1, highlightbackground=BORDER, highlightcolor=BORDER)
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
        content = tk.Frame(window, bg=BG, padx=round(8*density), pady=round(6*density))
        content.pack(fill="both", expand=True)
        bar = tk.Frame(content, bg=BG)
        bar.pack(fill="x", pady=(0, round(2*density)))
        close = self._button(bar, "×", self.hide)
        close.configure(bg=BG, fg=MUTED)
        close.pack(side="right", padx=(4, 0))
        self.lock_button = self._button(bar, "锁定", self._lock)
        self.lock_button.pack(side="right", padx=(4, 0))
        self.enable_button = self._button(bar, "开启", self._toggle_enabled, accent=True)
        self.enable_button.pack(side="right")
        title = self._label(bar, "队伍状态", size=12, bold=True)
        title.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.status = self._label(content, "未开启", size=10, muted=True)
        self.status.pack(fill="x", pady=(0, round(4*density)))
        self.data_body = tk.Frame(content, bg=BG)
        self.data_body.pack(fill="both", expand=True)
        self.empty_state = tk.Frame(content, bg=BG)
        empty_card = RoundedPanel(self.empty_state, height=None, radius=12, fill=SURFACE, content_padx=12, content_pady=18)
        empty_card.pack(fill="x", pady=round(24*density))
        self.empty_title = self._label(empty_card.content, "队友信息，随时查看", size=12, bold=True)
        self.empty_title.pack(fill="x", pady=(0, 8))
        self.empty_detail = self._label(empty_card.content, "点击上方“开启”，查看队友状态、背包与刻印。", size=11, muted=True)
        self.empty_detail.pack(fill="x")

        identity = RoundedPanel(self.data_body, height=None, radius=12, fill=SURFACE, content_padx=round(4*density), content_pady=round(3*density))
        identity.pack(fill="x", pady=(0, round(4*density)))
        member_row = tk.Frame(identity.content, bg=SURFACE)
        member_row.pack(fill="x", pady=(0, round(3*density)))
        self.previous_member = self._button(member_row, "‹", lambda:self._move_player(-1))
        self.previous_member.pack(side="left")
        self.next_member = self._button(member_row, "›", lambda:self._move_player(1))
        self.next_member.pack(side="right")
        self.member_slot = self._label(member_row, "P—", size=10, bold=True, muted=True)
        self.member_slot.pack(side="left", padx=(6, 3))
        self.members = tk.Label(member_row, text="等待队伍数据", bg=SURFACE, fg=TEXT, anchor="w", font=self._font(11, "bold"))
        self._fonts.append((self.members, 11, "bold"))
        self.members.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.members.bind("<Configure>", self._fit_member_name)
        self.members.bind("<Enter>", lambda _e:self.item_detail.configure(text=self._member_full_name))
        self.members.bind("<Leave>", lambda _e:self.item_detail.configure(text=self._selected_detail))
        tabs = tk.Frame(self.data_body, bg=BG)
        tabs.pack(fill="x", pady=(0, round(8*density)))
        self.view_buttons: dict[str, tk.Button] = {}
        for index, (key, caption) in enumerate((("status", "状态"), ("bag", "背包"), ("inscriptions", "刻印"))):
            tabs.columnconfigure(index, weight=1, uniform="tabs")
            button = self._button(tabs, caption, lambda view=key:self._set_view(view))
            button.grid(row=0, column=index, sticky="ew", padx=(0, round(3*density) if index<2 else 0))
            self.view_buttons[key] = button
        self.view_host = tk.Frame(self.data_body, bg=BG)
        self.view_host.pack(fill="both", expand=True)
        self.status_view = tk.Frame(self.view_host, bg=BG)
        self.status_view.bind("<Configure>", self._queue_status_layout)
        vital_card = RoundedPanel(self.status_view, height=None, radius=12, fill=SURFACE, content_padx=round(6*density), content_pady=round(8*density))
        vital_card.pack(fill="x", pady=(0, round(7*density)))
        meters = tk.Frame(vital_card.content, bg=SURFACE)
        meters.pack(fill="x")
        meters.columnconfigure((0, 1), weight=1, uniform="vitals")
        self.hp_meter = TeamVitalMeter(meters, self, "当前生命", "#B97868")
        self.hp_meter.grid(row=0, column=0, sticky="nsew", padx=(0, round(6*density)))
        self.mp_meter = TeamVitalMeter(meters, self, "当前法力", "#7899A2")
        self.mp_meter.grid(row=0, column=1, sticky="nsew", padx=(round(6*density), 0))
        resource_card = RoundedPanel(self.status_view, height=None, radius=12, fill=SURFACE, content_padx=round(6*density), content_pady=round(5*density))
        resource_card.pack(fill="x")
        self._label(resource_card.content, "随身资源", size=10, muted=True).pack(fill="x", pady=(0, 5))
        self.resources = self._label(resource_card.content, "", size=11)
        self.resources.pack(fill="x")
        self.resources.bind("<Configure>", self._queue_status_layout, add="+")
        self.inventory_view = tk.Frame(self.view_host, bg=BG)
        table = tk.Frame(self.inventory_view, bg=SURFACE)
        self.inventory = ttk.Treeview(table, columns=("detail",), show="tree headings", style="LC2TeamMini.Treeview", selectmode="browse")
        self.inventory.heading("#0", text="背包 / 刻印")
        self.inventory.heading("detail", text="数量 / 效果")
        self.inventory.column("#0", minwidth=80)
        self.inventory.column("detail", minwidth=60)
        self.inventory.bind("<Configure>", self._size_columns)
        self.inventory.bind("<<TreeviewSelect>>", self._select_item)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.inventory.yview, style="LC2TeamMini.Vertical.TScrollbar")
        self.inventory.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.inventory.pack(fill="both", expand=True)
        self.item_detail = self._label(self.data_body, self._selected_detail, size=10, muted=True)
        self.view_host.pack_forget()
        self.item_detail.pack(side="bottom", fill="x", pady=(round(4*density), 0))
        self.view_host.pack(fill="both", expand=True)
        table.pack(fill="both", expand=True)
        self._apply_fonts()
        self._apply_view()
        self._bind_drag_surfaces(content)
        prepare_tk_overlay(window)

    def _queue_status_layout(self, _event: Any = None) -> None:
        if self.window is not None and self._layout_job is None:
            self._layout_job = self.window.after_idle(self._fit_status_content)

    def _fit_status_content(self) -> None:
        try:
            window = self.window
            if window is None or self.active_view != "status" or not self._team:
                return
            # Finish nested rounded-card measurement before reading the
            # parent's requested height. Keep the job marked while flushing
            # geometry so Configure events cannot schedule a recursive fit.
            window.update_idletasks()
            missing = self.status_view.winfo_reqheight() - self.status_view.winfo_height()
            if missing <= 0:
                return
            width, height = window.winfo_width(), window.winfo_height()
            x, y = window.winfo_x(), window.winfo_y()
            work = nearest_monitor_work_area(x, y, width, height,
                                            fallback_width=window.winfo_screenwidth(),
                                            fallback_height=window.winfo_screenheight())
            target = min(window.winfo_reqheight(), work[3] - work[1] - round(16*self._dpi/96))
            if target > height:
                x, y = clamp_window_position(x, y, width, target, work)
                place_tk_window(window, width, target, x, y)
        finally:
            self._layout_job = None

    def _bind_drag_surfaces(self, widget: tk.Misc) -> None:
        if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)):
            widget.bind("<ButtonPress-1>", self._begin_drag, add="+")
            widget.bind("<B1-Motion>", self._drag, add="+")
        for child in widget.winfo_children():
            self._bind_drag_surfaces(child)

    def _set_view(self, view: str) -> None:
        if view not in self.view_buttons or view == self.active_view:
            return
        if self.active_view != "status":
            self._view_scrolls[self.active_view] = self.inventory.yview()[0]
        self.active_view = view
        self._apply_view()

    def _apply_view(self) -> None:
        for key, button in self.view_buttons.items():
            button.configure(bg=SELECTION if key==self.active_view else SIDEBAR, fg=ACCENT_TEXT if key==self.active_view else MUTED)
        self.status_view.pack_forget()
        self.inventory_view.pack_forget()
        for iid in self._inventory_roots:
            self.inventory.detach(iid)
        if self.active_view == "status":
            self.status_view.pack(fill="both", expand=True)
            self._selected_detail = "拖动标题或空白处移动小窗"
            self._queue_status_layout()
        else:
            self.inventory.heading("#0", text="随身物品" if self.active_view=="bag" else "刻印 / 灵魂石")
            self.inventory.heading("detail", text="数量" if self.active_view=="bag" else "效果")
            for iid in self._inventory_roots:
                if (iid=="bag") == (self.active_view=="bag"):
                    self.inventory.move(iid, "", "end")
            self.inventory_view.pack(fill="both", expand=True)
            self.inventory.yview_moveto(self._view_scrolls.get(self.active_view, 0.0))
            self._selected_detail = "点选物品查看详情"
        self.item_detail.configure(text=self._selected_detail)

    def _fit_member_name(self, _event: Any = None) -> None:
        font = tkfont.Font(font=self.members.cget("font"))
        width = max(1, self.members.winfo_width()-4)
        text = self._member_full_name
        if font.measure(text) > width:
            while text and font.measure(text+"…") > width:
                text = text[:-1]
            text += "…"
        if self.members.cget("text") != text:
            self.members.configure(text=text)

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
        style.layout("LC2TeamMini.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("LC2TeamMini.Treeview", font=self._font(11), rowheight=round(25*self._dpi/96), background=SURFACE, fieldbackground=SURFACE, foreground=TEXT, borderwidth=0, indent=round(12*self._dpi/96))
        style.configure("LC2TeamMini.Treeview.Heading", font=self._font(10, "bold"), background=SIDEBAR, foreground=MUTED, relief="flat", padding=(4, 3))
        style.map("LC2TeamMini.Treeview.Heading", background=[("active", SELECTION)])
        style.map("LC2TeamMini.Treeview", background=[("selected", SELECTION)], foreground=[("selected", TEXT)])
        style.configure("LC2TeamMini.Vertical.TScrollbar", background=SIDEBAR, troughcolor=SURFACE, borderwidth=0, arrowsize=round(11*self._dpi/96))
        self.inventory.tag_configure("section", font=self._font(10, "bold"), foreground=MUTED, background=BG)
        self.hp_meter.bar.configure(height=round(5*self._dpi/96))
        self.mp_meter.bar.configure(height=round(5*self._dpi/96))
        self._fit_member_name()

    def _size_columns(self, event: Any) -> None:
        width = max(200, event.width-4)
        self.inventory.column("#0", width=round(width*.66))
        self.inventory.column("detail", width=round(width*.34))

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
        self.enable_button.configure(text="暂停" if enabled else "开启")
        snapshot = self.service.snapshot(self.game_pid()) if enabled else None
        self._team = list(snapshot.team) if snapshot is not None and snapshot.state == "ready" else []
        if self._team:
            detail = "演示数据" if getattr(self.service, "is_demo", False) else "实时同步"
            self.status.configure(text=f"● {detail} · {len(self._team)} 人" + (" · 已锁定" if self._locked else ""), fg=GREEN)
            self.empty_state.pack_forget()
            self.data_body.pack(fill="both", expand=True)
        else:
            self.status.configure(text="● 等待连接" if enabled else "○ 未开启", fg=MUTED)
            self.empty_title.configure(text="等待队伍同步" if enabled else "队友信息，随时查看")
            self.empty_detail.configure(text=snapshot.detail if snapshot is not None else "点击上方“开启”，查看队友状态、背包与刻印。")
            self.data_body.pack_forget()
            self.empty_state.pack(fill="both", expand=True)
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
            self._member_full_name = "等待队伍数据"
            self.members.configure(text="等待队伍数据")
            self.member_slot.configure(text="P—")
            self.hp_meter.set_values(None, None)
            self.mp_meter.set_values(None, None)
            self.resources.configure(text="等待队伍同步数据")
            self.inventory.delete(*self._inventory_roots)
            self._inventory_roots.clear()
            self._selected_detail = "点选物品查看详情"
            self.item_detail.configure(text=self._selected_detail)
            self._inventory_identity = ""
            return
        self._member_full_name = inline_name(player.get("name") or "玩家") + (" · 自己" if player.get("is_local") else "")
        self.member_slot.configure(text=f"P{player['slot']+1}")
        self._fit_member_name()
        self.hp_meter.set_values(player.get("hp"), player.get("max_hp"))
        self.mp_meter.set_values(player.get("mp"), player.get("max_mp"))
        resources = player.get("resources", {})
        text = "资源暂未同步" if all(resources.get(key) is None for key in ("gold", "crystal", "iron", "coins")) else "\n".join("    ".join(f"{label} {feature_value(resources.get(key))}" for key, label in row) for row in ((("gold", "金币"), ("crystal", "魂晶")), (("iron", "魔铁"), ("coins", "硬币"))))
        self.resources.configure(text=text)
        self._queue_status_layout()
        identity = json.dumps([self.selected_slot, player.get("inventory_state"), player.get("items"), player.get("inscriptions")], ensure_ascii=False, sort_keys=True)
        if identity == self._inventory_identity:
            return
        self._inventory_identity = identity
        opened = {item: self.inventory.item(item, "open") for item in self._inventory_roots}
        position = self.inventory.yview()[0]
        self.inventory.delete(*self._inventory_roots)
        self._inventory_roots.clear()
        bag = self.inventory.insert("", "end", iid="bag", text="随身背包", open=opened.get("bag", True), tags=("section",))
        self._inventory_roots.append(bag)
        if player.get("inventory_state") != "ready":
            self.inventory.insert(bag, "end", text="背包暂不可读")
        elif not player.get("items"):
            self.inventory.insert(bag, "end", text="未发现已同步物品")
        for item in player.get("items", []):
            self.inventory.insert(bag, "end", text=f"{ITEM_KIND_LABELS.get(item.get('kind'), '物品')} · {inline_name(item.get('name', '未命名物品'))}", values=(f"× {feature_value(item.get('count'))}",))
        for index, inscription in enumerate(player.get("inscriptions", [])):
            iid = f"inscription-{index}"
            parent = self.inventory.insert("", "end", iid=iid, text=f"刻印 · {inscription.get('name', '')}", open=opened.get(iid, True), tags=("section",))
            self._inventory_roots.append(parent)
            for gem in inscription.get("gems", []):
                self.inventory.insert(parent, "end", text=gem.get("name", "灵魂石"), values=(" / ".join(gem.get(key, "") for key in ("main", "sub") if gem.get(key)),))
        if not player.get("inscriptions"):
            self._inventory_roots.append(self.inventory.insert("", "end", iid="empty-inscriptions", text="没有已同步的刻印", tags=("section",)))
        self._view_scrolls[self.active_view] = position
        self._apply_view()

    def _select_item(self, _event: Any = None) -> None:
        selected = self.inventory.selection()
        if not selected:
            return
        item = self.inventory.item(selected[0])
        self._selected_detail = " · ".join([item["text"], *(str(value) for value in item.get("values", []) if value)])
        self.item_detail.configure(text=self._selected_detail)
