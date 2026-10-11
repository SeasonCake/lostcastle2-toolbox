from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .game_features import GameFeatureError, feature_value


ITEM_KIND_LABELS = {"Weapon": "武器", "Armor": "护甲", "PassiveProps": "宝藏", "ActiveProps": "道具", "AlchemyMix": "炼金"}
GEM_KIND_LABELS = {"Triangle": "三角", "Square": "方形", "Circle": "圆形"}


def inline_name(value: str) -> str:
    return " / ".join(part.strip() for part in value.splitlines() if part.strip())


class FeaturePages:
    """Toolbox-owned views; all data/actions go through the optional feature service."""

    def __init__(self, shell: Any, theme: dict[str, str], panel_factory: Any) -> None:
        self.shell = shell
        self.service = shell.game_features
        self.theme = theme
        self.panel_factory = panel_factory
        self.buttons: dict[str, tk.Button] = {}
        self.status: dict[str, tk.Label] = {}
        self.selected_slot: int | None = None
        self._roster: list[dict[str, Any]] = []
        self._team_identity = ""
        self._roster_identity = ""
        self._inventory_identity = ""
        self._catalog_identity = ""
        self._loadout: dict[str, Any] = {}
        self._equipment_rows: list[dict[str, Any]] = []
        self._gem_rows: list[dict[str, Any]] = []
        self._result_identity = ""
        self._build_team()
        self._build_enhancement()
        self._build_loadout()

    def _label(self, parent: tk.Misc, text: str = "", *, muted: bool = False, size: int = 12, bold: bool = False) -> tk.Label:
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=self.theme["muted" if muted else "text"], anchor="w", justify="left", font=("Microsoft YaHei UI", size, "bold" if bold else "normal"))

    def _panel(self, parent: tk.Misc) -> Any:
        return self.panel_factory(parent, height=None, content_padx=14, content_pady=10)

    def _heading(self, page: tk.Frame, title: str, subtitle: str, key: str) -> None:
        self.shell._page_heading(page, title, subtitle)
        bar = self._panel(page)
        bar.pack(fill="x", pady=(0, 12))
        self.buttons[key] = self.shell._button(bar.content, "启用功能", lambda: self._toggle(key), accent=True, width=13)
        self.buttons[key].pack(side="right", padx=(12, 0))
        self.status[key] = self._label(bar.content, "默认关闭 · 按需开启", bold=True)
        self.status[key].pack(side="left", fill="x", expand=True)

    def _build_team(self) -> None:
        page = self.shell._new_page("team")
        self._heading(page, "队伍状态", "一起看清队友状态、背包和当前刻印。", "team_enabled")
        body = tk.Frame(page, bg=self.theme["bg"])
        self.team_body = body
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=205)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        left = self._panel(body)
        self.team_roster_panel = left
        left.configure(width=205)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._label(left.content, "队伍成员", bold=True).pack(fill="x", pady=(0, 6))
        self.roster = tk.Listbox(left.content, width=16, bg=self.theme["surface"], fg=self.theme["text"], selectbackground=self.theme.get("selection", "#E8D7CA"), selectforeground=self.theme["text"], exportselection=False, relief="flat", highlightthickness=0, font=("Microsoft YaHei UI", 10), activestyle="none")
        self.roster.pack(fill="both", expand=True)
        self.roster.bind("<<ListboxSelect>>", self._select_player)
        right = self._panel(body)
        self.team_details_panel = right
        right.grid(row=0, column=1, sticky="nsew")
        self._team_stacked = False
        self._team_layout_scale = 1.0
        body.bind("<Configure>", lambda _e: self._layout_team())
        self.player_title = self._label(right.content, "开启后选择一位队友", size=14, bold=True)
        self.player_title.pack(fill="x", pady=(0, 6))
        self.player_vitals = self._label(right.content, "生命 —    法力 —", size=11)
        self.player_vitals.pack(fill="x", pady=(0, 8))
        self.player_resources = self._label(right.content, "金币 —    魂晶 —    魔铁锭 —    虚灵硬币 —", muted=True)
        self.player_resources.pack(fill="x", pady=(0, 10))
        for label in (self.player_title, self.player_vitals, self.player_resources):
            label.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(120, e.width)))
        self.inventory = ttk.Treeview(right.content, columns=("detail",), show="tree headings", style="Toolbox.Treeview", selectmode="browse", height=7)
        self.inventory.heading("#0", text="背包 / 刻印")
        self.inventory.heading("detail", text="数量 / 效果")
        self.inventory.column("#0", width=230, minwidth=145)
        self.inventory.column("detail", width=250, minwidth=145)
        self.inventory.bind("<Configure>", self._size_inventory_columns)
        scroll = ttk.Scrollbar(right.content, orient="vertical", command=self.inventory.yview)
        self.inventory.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.inventory.pack(fill="both", expand=True)
        note = self._label(page, "队友信息以游戏当前同步数据为准；未同步的资源会明确提示。", muted=True, size=8)
        note.pack(fill="x", pady=(10, 4))
        note.bind("<Configure>", lambda e: note.configure(wraplength=max(120, e.width)))
        self._label(page, "工具箱功能设计与优化：加菲_barista", muted=True, size=8).pack(fill="x")

    def _build_enhancement(self) -> None:
        page = self.shell._new_page("enhancement")
        self.shell._page_heading(page, "LC 增强计划", "按自己的玩法开启战斗、掉落与便利调节。")
        panel = self._panel(page)
        panel.pack(fill="x", pady=(0, 12))
        self.enhancement_title = self._label(panel.content, "LC2 增强计划", size=14, bold=True)
        self.enhancement_title.pack(fill="x")
        self.enhancement_author = self._label(panel.content, "", muted=True, size=8)
        self.enhancement_author.pack(fill="x", pady=(4, 12))
        self.enhancement_summary = self._label(panel.content, "")
        self.enhancement_summary.pack(fill="x", pady=(0, 10))
        self.enhancement_usage = self._label(panel.content, "", muted=True, size=8)
        self.enhancement_usage.pack(fill="x", pady=(0, 12))
        for label in (self.enhancement_summary, self.enhancement_usage):
            label.bind("<Configure>", lambda e: e.widget.configure(wraplength=max(120, e.width)))
        actions = tk.Frame(panel.content, bg=self.theme["surface"])
        actions.pack(fill="x")
        self.enhancement_install = self.shell._button(actions, "启用 / 安装", lambda: self.shell._configure_mod("enhancement-plan"), accent=True, width=13)
        self.enhancement_install.pack(side="left")
        self.enhancement_open = self.shell._button(actions, "打开游戏面板", lambda: self.shell._launch_selected_mod("enhancement-plan"), width=13)
        self.enhancement_open.pack(side="left", padx=8)
        self.enhancement_remove = self.shell._button(actions, "关闭 / 卸载", lambda: self.shell._remove_mod("enhancement-plan"), width=12)
        self.enhancement_remove.pack(side="left")
        self.enhancement_state = self._label(page, "默认关闭；安装后需重启游戏。", muted=True)
        self.enhancement_state.pack(fill="x", pady=(3, 8))
        self._label(page, "增强计划保留原作者；工具箱统一管理安装、更新和打开面板。", muted=True, size=8).pack(fill="x")

    def _build_loadout(self) -> None:
        page = self.shell._new_page("loadout")
        self._heading(page, "配装助手", "在营地整理装备、附魔和已有灵魂石。", "loadout_enabled")
        self.current_equipment = self._label(page, "当前装备：等待游戏连接", muted=True)
        self.current_equipment.pack(fill="x", pady=(0, 10))
        self.tabs = ttk.Notebook(page)
        self.tabs.pack(fill="both", expand=True)
        equipment = tk.Frame(self.tabs, bg=self.theme["surface"], padx=14, pady=12)
        enchantment = tk.Frame(self.tabs, bg=self.theme["surface"], padx=14, pady=12)
        gems = tk.Frame(self.tabs, bg=self.theme["surface"], padx=14, pady=12)
        self.tabs.add(equipment, text="  装备自选  ")
        self.tabs.add(enchantment, text="  武器附魔  ")
        self.tabs.add(gems, text="  刻印与灵魂石  ")

        searchrow = tk.Frame(equipment, bg=self.theme["surface"])
        searchrow.pack(fill="x", pady=(0, 8))
        self.equipment_kind = tk.StringVar(value="全部装备")
        selector = ttk.Combobox(searchrow, textvariable=self.equipment_kind, values=("全部装备", "武器", "护甲"), state="readonly", width=10)
        selector.pack(side="left", padx=(0, 8))
        selector.bind("<<ComboboxSelected>>", lambda _e: self._filter_equipment())
        self.equipment_query = tk.StringVar(value="")
        self._label(searchrow, "搜索").pack(side="left", padx=(0, 6))
        entry = tk.Entry(searchrow, textvariable=self.equipment_query, bg=self.theme["surface"], fg=self.theme["text"], relief="solid", bd=1, font=("Microsoft YaHei UI", 9))
        entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.equipment_query.trace_add("write", lambda *_: self._filter_equipment())
        self.equipment_list = tk.Listbox(equipment, bg=self.theme["surface"], fg=self.theme["text"], selectbackground=self.theme.get("selection", "#E8D7CA"), selectforeground=self.theme["text"], exportselection=False, font=("Microsoft YaHei UI", 10), relief="flat", highlightthickness=1, highlightbackground=self.theme["border"], activestyle="none")
        self.equipment_list.pack(fill="both", expand=True, pady=(0, 10))
        self.equipment_apply = self.shell._button(equipment, "获得所选装备", lambda: self._request_equipment(), accent=True, width=16)
        self.equipment_apply.pack(anchor="e")

        self._label(enchantment, "替换当前武器的附魔", size=12, bold=True).pack(fill="x", pady=(0, 8))
        self._label(enchantment, "从当前游戏提供的附魔中选择，应用前会再次确认。", muted=True).pack(fill="x", pady=(0, 16))
        self.enchantment = ttk.Combobox(enchantment, state="readonly", font=("Microsoft YaHei UI", 10))
        self.enchantment.pack(fill="x", pady=(0, 16))
        self.enchantment_apply = self.shell._button(enchantment, "应用所选附魔", lambda: self._request_enchantment(), accent=True, width=16)
        self.enchantment_apply.pack(anchor="e")

        self._label(gems, "把已有灵魂石装入已解锁的刻印槽", size=12, bold=True).pack(fill="x", pady=(0, 12))
        self.inscription = self._combo_row(gems, "刻印")
        self.inscription.bind("<<ComboboxSelected>>", lambda _e: self._update_slots())
        self.gem_slot = self._combo_row(gems, "刻印槽")
        self.gem_slot.bind("<<ComboboxSelected>>", lambda _e: self._filter_gems())
        self._label(gems, "搜索已有灵魂石", muted=True).pack(fill="x", pady=(4, 4))
        self.gem_query = tk.StringVar(value="")
        gem_search = tk.Entry(gems, textvariable=self.gem_query, bg=self.theme["surface"], fg=self.theme["text"], relief="solid", bd=1, font=("Microsoft YaHei UI", 12))
        gem_search.pack(fill="x", pady=(0, 8), ipady=3)
        self.gem = self._combo_row(gems, "灵魂石")
        self.gem.bind("<<ComboboxSelected>>", lambda _e: self._show_gem_description())
        self.gem_description = self._label(gems, "请选择已有灵魂石查看属性。", muted=True)
        self.gem_description.pack(fill="x", pady=(0, 8))
        self.gem_description.bind("<Configure>", lambda e: self.gem_description.configure(wraplength=max(120, e.width)))
        self.gem_query.trace_add("write", lambda *_: self._filter_gems())
        self.gem_apply = self.shell._button(gems, "装备灵魂石", lambda: self._request_gem(), accent=True, width=16)
        self.gem_apply.pack(anchor="e", pady=(8, 0))
        self.loadout_feedback = self._label(page, "启用后进入营地，目录会自动出现。", muted=True)
        self.loadout_feedback.pack(fill="x", pady=(10, 4))
        self.loadout_feedback.bind("<Configure>", lambda e: self.loadout_feedback.configure(wraplength=max(120, e.width)))
        self._label(page, "工具箱功能设计与优化：加菲_barista", muted=True, size=8).pack(fill="x")

    def _combo_row(self, parent: tk.Frame, label: str) -> ttk.Combobox:
        self._label(parent, label, muted=True).pack(fill="x", pady=(4, 4))
        combo = ttk.Combobox(parent, state="readonly", font=("Microsoft YaHei UI", 9))
        combo.pack(fill="x", pady=(0, 8))
        return combo

    def set_ui_scale(self, scale: float) -> None:
        self._team_layout_scale = scale
        self._layout_team(force=True)

    def _layout_team(self, *, force: bool = False) -> None:
        scale = self._team_layout_scale
        stacked = self.team_body.winfo_width() < round(780 * scale)
        if not force and stacked == self._team_stacked:
            return
        self._team_stacked = stacked
        self.team_roster_panel.configure(width=round(225*scale))
        self.team_body.columnconfigure(0, weight=1 if stacked else 0, minsize=0 if stacked else round(225*scale))
        self.team_body.columnconfigure(1, weight=0 if stacked else 1)
        self.team_body.rowconfigure(0, weight=0 if stacked else 1)
        self.team_body.rowconfigure(1, weight=1 if stacked else 0)
        self.roster.configure(height=3 if stacked else 10)
        self.team_roster_panel.grid_configure(row=0, column=0, padx=0 if stacked else (0, round(10*scale)), pady=(0, round(10*scale)) if stacked else 0)
        self.team_details_panel.grid_configure(row=1 if stacked else 0, column=0 if stacked else 1)

    def _size_inventory_columns(self, event: Any) -> None:
        width = max(200, event.width - 4)
        first = round(width * 0.53)
        self.inventory.column("#0", width=first, minwidth=100)
        self.inventory.column("detail", width=width-first, minwidth=100)

    def qa_widgets(self) -> dict[str, tk.Misc]:
        return {
            **{f"feature_{key}_status": widget for key, widget in self.status.items()},
            **{f"feature_{key}_toggle": widget for key, widget in self.buttons.items()},
            "team_name": self.player_title, "team_vitals": self.player_vitals,
            "team_resources": self.player_resources, "team_roster": self.roster,
            "team_inventory": self.inventory, "loadout_current": self.current_equipment,
            "loadout_feedback": self.loadout_feedback, "loadout_equipment_action": self.equipment_apply,
            "loadout_enchantment_action": self.enchantment_apply, "loadout_gem_action": self.gem_apply,
            "loadout_gem_description": self.gem_description,
            "enhancement_title": self.enhancement_title, "enhancement_author": self.enhancement_author,
            "enhancement_install": self.enhancement_install, "enhancement_open": self.enhancement_open,
            "enhancement_remove": self.enhancement_remove,
        }

    def _toggle(self, key: str) -> None:
        if self.service is None:
            return
        enabled = self.service.settings()[key]
        if not enabled and not getattr(self.service, "is_demo", False) and not self.shell.ensure_game_runtime():
            return
        try:
            self.service.set_enabled(key, not enabled)
        except GameFeatureError as error:
            messagebox.showerror("无法切换功能", str(error), parent=self.shell.root)
        self._team_identity = ""
        self._catalog_identity = ""
        self.refresh()

    def _select_player(self, _event: Any = None) -> None:
        selected = self.roster.curselection()
        if selected and selected[0] < len(self._roster):
            self.selected_slot = self._roster[selected[0]]["slot"]
        self._show_player()

    def _show_player(self) -> None:
        player = next((p for p in self._roster if p["slot"] == self.selected_slot), None)
        if player is None:
            self.player_title.configure(text="开启后选择一位队友")
            self.player_vitals.configure(text="生命 —    法力 —")
            self.player_resources.configure(text="金币 —    魂晶 —    魔铁锭 —    虚灵硬币 —")
            for item in self.inventory.get_children(""):
                self.inventory.delete(item)
            self._inventory_identity = ""
            return
        labels = ["自己"] if player.get("is_local") else []
        if player.get("is_host"):
            labels.append("房主")
        self.player_title.configure(text=f"{player['name'] or '玩家'}" + (f" · {' / '.join(labels)}" if labels else ""))
        self.player_vitals.configure(text=f"生命 {feature_value(player.get('hp'))} / {feature_value(player.get('max_hp'))}    法力 {feature_value(player.get('mp'))} / {feature_value(player.get('max_mp'))}")
        r = player.get("resources", {})
        self.player_resources.configure(text="    ".join(f"{label} {feature_value(r.get(key))}" for key, label in (("gold", "金币"), ("crystal", "魂晶"), ("iron", "魔铁锭"), ("coins", "虚灵硬币"))))
        identity = json.dumps([self.selected_slot, player.get("inventory_state"), player.get("items"), player.get("inscriptions")], ensure_ascii=False, sort_keys=True)
        if identity == self._inventory_identity:
            return
        self._inventory_identity = identity
        previous_open = {item: bool(self.inventory.item(item, "open")) for item in self.inventory.get_children("")}
        scroll_position = self.inventory.yview()[0]
        for item in self.inventory.get_children(""):
            self.inventory.delete(item)
        bag = self.inventory.insert("", "end", iid="bag", text="背包", open=previous_open.get("bag", True))
        if player.get("inventory_state") != "ready":
            self.inventory.insert(bag, "end", text="背包暂不可读")
        elif not player.get("items"):
            self.inventory.insert(bag, "end", text="未发现已同步物品")
        for item in player.get("items", []):
            if not isinstance(item, dict):
                continue
            self.inventory.insert(bag, "end", text=f"{ITEM_KIND_LABELS.get(item.get('kind'), '物品')} · {item.get('name', '未命名物品')}", values=(f"× {feature_value(item.get('count'))}",))
        for index, inscription in enumerate(player.get("inscriptions", [])):
            if not isinstance(inscription, dict):
                continue
            iid = f"inscription-{index}"
            node = self.inventory.insert("", "end", iid=iid, text=f"刻印 · {inscription.get('name', '')}", open=previous_open.get(iid, True))
            for gem in inscription.get("gems", []):
                if isinstance(gem, dict):
                    self.inventory.insert(node, "end", text=gem.get("name", "灵魂石"), values=(" / ".join(s for s in (gem.get("main", ""), gem.get("sub", "")) if s),))
        self.inventory.yview_moveto(scroll_position)

    def _filter_equipment(self) -> None:
        selected = self.equipment_list.curselection()
        previous = self._equipment_rows[selected[0]].get("id") if selected and selected[0] < len(self._equipment_rows) else None
        query = self.equipment_query.get().strip().casefold()
        kind = self.equipment_kind.get()
        self._equipment_rows = [row for row in self._loadout.get("equipment", []) if (kind == "全部装备" or ITEM_KIND_LABELS.get(row.get("kind")) == kind) and (not query or query in f"{row.get('name', '')}\n{row.get('id', '')}".casefold())]
        self.equipment_list.delete(0, "end")
        for i, row in enumerate(self._equipment_rows):
            self.equipment_list.insert("end", f"{row.get('name', '')}  ·  {ITEM_KIND_LABELS.get(row.get('kind'), '')}")
            if row.get("id") == previous:
                self.equipment_list.selection_set(i)

    @staticmethod
    def _set_choices(combo: ttk.Combobox, labels: list[str]) -> None:
        previous = combo.get()
        combo.configure(values=labels)
        if previous in labels:
            combo.set(previous)
        elif labels:
            combo.current(0)
        else:
            combo.set("")

    def _update_slots(self) -> None:
        idx = self.inscription.current()
        rows = self._loadout.get("inscriptions", [])
        if 0 <= idx < len(rows):
            self._set_choices(self.gem_slot, [f"槽位 {s['slot'] + 1} · {GEM_KIND_LABELS.get(s.get('kind'), s.get('kind', ''))} · {inline_name(s.get('name', ''))}" for s in rows[idx].get("slots", [])])
        else:
            self._set_choices(self.gem_slot, [])
        self._filter_gems()

    def _filter_gems(self) -> None:
        previous_index = self.gem.current()
        previous_id = self._gem_rows[previous_index]["id"] if 0 <= previous_index < len(self._gem_rows) else None
        inscriptions = self._loadout.get("inscriptions", [])
        i, s = self.inscription.current(), self.gem_slot.current()
        kind = inscriptions[i]["slots"][s].get("kind") if 0 <= i < len(inscriptions) and 0 <= s < len(inscriptions[i].get("slots", [])) else None
        query = self.gem_query.get().strip().casefold()
        self._gem_rows = [row for row in self._loadout.get("gems", []) if (kind is None or row.get("kind") == kind) and (not query or query in " ".join(row.get(key, "") for key in ("name", "main", "sub")).casefold())]
        labels = [f"{inline_name(row.get('name', ''))} · {GEM_KIND_LABELS.get(row.get('kind'), row.get('kind', ''))}" for row in self._gem_rows]
        self._set_choices(self.gem, labels)
        for index, row in enumerate(self._gem_rows):
            if row["id"] == previous_id:
                self.gem.current(index)
                break
        self._show_gem_description()

    def _show_gem_description(self) -> None:
        index = self.gem.current()
        if 0 <= index < len(self._gem_rows):
            row = self._gem_rows[index]
            self.gem_description.configure(text=f"主属性：{inline_name(row.get('main', '')) or '无'}\n副属性：{inline_name(row.get('sub', '')) or '无'}")
        else:
            self.gem_description.configure(text="当前筛选没有可用灵魂石。")

    def _request(self, action: str, **selection: Any) -> None:
        if self.service is None:
            return
        game_pid = self.service.demo_pid if getattr(self.service, "is_demo", False) else self.shell.keyboard.game_process_id
        if game_pid is None:
            return
        if not messagebox.askyesno("确认配装", "将对当前本地角色应用所选配装。仅在营地执行。\n\n是否继续？", parent=self.shell.root):
            return
        try:
            self.service.request(action, game_pid, **selection)
        except GameFeatureError as error:
            self.loadout_feedback.configure(text=str(error), fg=self.theme["red"])
        else:
            self.loadout_feedback.configure(text="正在应用，请稍候…", fg=self.theme["muted"])
            self._result_identity = ""

    def _request_equipment(self) -> None:
        selected = self.equipment_list.curselection()
        if selected and selected[0] < len(self._equipment_rows):
            self._request("equipment", item_id=self._equipment_rows[selected[0]]["id"])
        else:
            self.loadout_feedback.configure(text="请先选择一件装备。")

    def _request_enchantment(self) -> None:
        idx = self.enchantment.current()
        rows = self._loadout.get("enchantments", [])
        if 0 <= idx < len(rows):
            self._request("enchantment", enchantment_id=rows[idx]["id"])

    def _request_gem(self) -> None:
        i, s, g = self.inscription.current(), self.gem_slot.current(), self.gem.current()
        inscriptions = self._loadout.get("inscriptions", [])
        gems = self._gem_rows
        if 0 <= i < len(inscriptions) and 0 <= s < len(inscriptions[i].get("slots", [])) and 0 <= g < len(gems):
            self._request("gem", inscription_id=inscriptions[i]["id"], slot=inscriptions[i]["slots"][s]["slot"], gem_id=gems[g]["id"])

    def refresh(self) -> None:
        page = getattr(self.shell, "current_page", "home")
        if page == "enhancement":
            descriptor = self.shell.mod_manager.descriptor("enhancement-plan")
            status = self.shell.mod_manager.status("enhancement-plan")
            self.enhancement_title.configure(text=f"{descriptor.display.name}  v{descriptor.display.version}")
            self.enhancement_author.configure(text=f"原作者：{descriptor.display.author}")
            self.enhancement_summary.configure(text=descriptor.display.summary)
            self.enhancement_usage.configure(text=descriptor.display.usage_hint)
            self.enhancement_state.configure(text="已启用 · 安装/升级后需重启游戏" if status.installed else "默认关闭 · 按需安装后启用")
            self.enhancement_install.configure(text="更新 / 重装" if status.present else "启用 / 安装", state="disabled" if self.shell._mod_busy else "normal")
            self.enhancement_open.configure(state="normal" if status.installed and not self.shell._mod_busy else "disabled")
            self.enhancement_remove.configure(state="normal" if status.present and not self.shell._mod_busy else "disabled")
            return
        if self.service is None or page not in {"team", "loadout"}:
            return
        settings = self.service.settings()
        snapshot = self.service.snapshot(self.shell.keyboard.game_process_id)
        key = "team_enabled" if page == "team" else "loadout_enabled"
        enabled = settings[key]
        self.buttons[key].configure(text="关闭功能" if enabled else "启用功能")
        self.status[key].configure(text=snapshot.detail if enabled else "已关闭 · 开启后在这里使用", fg=self.theme["text"])
        if page == "team":
            team = list(snapshot.team) if enabled and snapshot.state == "ready" else []
            identity = json.dumps(team, ensure_ascii=False, sort_keys=True)
            if identity != self._team_identity:
                self._team_identity = identity
                old_selected = self.selected_slot
                self._roster = team
                roster_identity = json.dumps([(p["slot"], p["name"], p.get("is_local")) for p in team], ensure_ascii=False)
                if roster_identity != self._roster_identity:
                    self._roster_identity = roster_identity
                    self.roster.delete(0, "end")
                    for i, player in enumerate(team):
                        self.roster.insert("end", ("自己 · " if player.get("is_local") else "") + player["name"])
                        if player["slot"] == old_selected:
                            self.roster.selection_set(i)
                    if team and not self.roster.curselection():
                        self.roster.selection_set(0)
                self._select_player()
            return
        usable = enabled and snapshot.state == "ready" and snapshot.loadout is not None
        local = next((player for player in snapshot.team if player.get("is_local")), None)
        if enabled and local is not None and isinstance(local.get("equipment"), dict):
            equipment = local["equipment"]
            self.current_equipment.configure(text=f"当前武器：{equipment.get('weapon') or '未装备'}    护甲：{equipment.get('armor') or '未装备'}")
        else:
            self.current_equipment.configure(text="当前装备：等待游戏连接" if enabled else "配装助手已关闭")
        state = "normal" if usable and snapshot.loadout.get("in_camp") is True else "disabled"
        for button in (self.equipment_apply, self.enchantment_apply, self.gem_apply):
            button.configure(state=state)
        rows = snapshot.loadout if usable else {}
        identity = json.dumps(rows, ensure_ascii=False, sort_keys=True)
        if identity != self._catalog_identity:
            self._catalog_identity = identity
            self._loadout = rows
            self._filter_equipment()
            self._set_choices(self.enchantment, [r.get("name", "") for r in rows.get("enchantments", [])])
            self._set_choices(self.inscription, [r.get("name", "") for r in rows.get("inscriptions", [])])
            self._update_slots()
        game_pid = self.service.demo_pid if getattr(self.service, "is_demo", False) else self.shell.keyboard.game_process_id
        if game_pid is not None:
            result = self.service.result(game_pid)
            if result and result["request_id"] != self._result_identity:
                self._result_identity = result["request_id"]
                self.loadout_feedback.configure(text=result.get("message", ""), fg=self.theme["green"] if result["state"] == "complete" else self.theme["red"])

