from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import stat
import tempfile
import time
from typing import Any, Callable
import uuid


FEATURE_DIRECTORY = Path("BepInEx/config/LC2Toolbox")
FEATURE_PLUGIN = Path("BepInEx/plugins/LC2ToolboxFeatures/LC2ToolboxFeatures.dll")
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024
SNAPSHOT_TTL_MS = 5000


class GameFeatureError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeatureSnapshot:
    state: str
    detail: str
    team: tuple[dict[str, Any], ...] = ()
    loadout: dict[str, Any] | None = None
    captured_at: int | None = None


def feature_value(value: Any) -> str:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return "未同步"
    return f"{value:,.0f}"


def _text(value: Any, limit: int = 160, *, required: bool = False) -> bool:
    return isinstance(value, str) and len(value) <= limit and (bool(value) or not required)


def _rows(value: Any, limit: int) -> bool:
    return isinstance(value, list) and len(value) <= limit and all(isinstance(row, dict) for row in value)


def _valid_loadout(loadout: dict[str, Any]) -> bool:
    if type(loadout.get("in_camp")) is not bool:
        return False
    for section, limit in (("equipment", 2400), ("inscriptions", 128), ("gems", 2000), ("enchantments", 256)):
        rows = loadout.get(section)
        if not _rows(rows, limit):
            return False
        seen = set()
        for row in rows:
            identity = row.get("id")
            valid_id = _text(identity, 80, required=True) if section in {"equipment", "inscriptions"} else type(identity) is int and -(2**31) <= identity < 2**31
            if not valid_id or identity in seen or not _text(row.get("name")):
                return False
            seen.add(identity)
            if section == "equipment" and row.get("kind") not in {"Weapon", "Armor"}:
                return False
            if section == "enchantments" and identity < 0:
                return False
            if section == "gems" and any(not _text(row.get(key, "")) for key in ("main", "sub", "kind")):
                return False
            if section == "inscriptions":
                slots = row.get("slots")
                if not _rows(slots, 32):
                    return False
                indexes = set()
                for slot in slots:
                    index = slot.get("slot")
                    if type(index) is not int or not 0 <= index < 32 or index in indexes or any(not _text(slot.get(key, "")) for key in ("name", "kind")):
                        return False
                    indexes.add(index)
    return True


def parse_feature_snapshot(raw: object, game_pid: int, now_ms: int) -> FeatureSnapshot:
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        return FeatureSnapshot("invalid", "状态数据暂不可读")
    if type(raw.get("game_pid")) is not int or raw["game_pid"] != game_pid:
        return FeatureSnapshot("waiting", "等待本次游戏连接")
    captured_at = raw.get("captured_at")
    if type(captured_at) is not int or not 0 <= now_ms - captured_at <= SNAPSHOT_TTL_MS:
        return FeatureSnapshot("stale", "数据暂未更新，请在游戏中检查连接")
    if raw.get("state") == "disabled":
        return FeatureSnapshot("disabled", "功能已关闭")
    if raw.get("state") != "ready":
        return FeatureSnapshot("waiting", "进入游戏并等待角色就绪")
    team = raw.get("team")
    if not isinstance(team, list) or len(team) > 16:
        return FeatureSnapshot("invalid", "队伍数据暂不可读")
    slots: set[int] = set()
    cleaned = []
    for player in team:
        if not isinstance(player, dict) or type(player.get("slot")) is not int or not 0 <= player["slot"] < 16 or player["slot"] in slots:
            return FeatureSnapshot("invalid", "队伍身份尚未就绪")
        if not isinstance(player.get("name"), str) or len(player["name"]) > 64:
            return FeatureSnapshot("invalid", "队伍数据暂不可读")
        slots.add(player["slot"])
        row = dict(player)
        if not isinstance(row.get("resources"), dict):
            row["resources"] = {}
        if row.get("resources_state") != "ready":
            row["resources"] = {key: None for key in ("gold", "crystal", "iron", "coins")}
        for section in ("items", "inscriptions"):
            if not _rows(row.get(section), 256):
                return FeatureSnapshot("invalid", "背包数据暂不可读")
        for item in row["items"]:
            if not _text(item.get("name")) or not _text(item.get("kind")):
                return FeatureSnapshot("invalid", "背包数据暂不可读")
        for inscription in row["inscriptions"]:
            gems = inscription.get("gems")
            if not _text(inscription.get("name")) or not _rows(gems, 32) or any(any(not _text(gem.get(key, "")) for key in ("name", "main", "sub")) for gem in gems):
                return FeatureSnapshot("invalid", "刻印数据暂不可读")
        cleaned.append(row)
    loadout = raw.get("loadout")
    if loadout is not None:
        if not isinstance(loadout, dict):
            return FeatureSnapshot("invalid", "配装数据暂不可读")
        if not _valid_loadout(loadout):
            return FeatureSnapshot("invalid", "配装目录暂不可读")
    return FeatureSnapshot("ready", "已连接游戏 · 自动刷新", tuple(sorted(cleaned, key=lambda p: p["slot"])), loadout, captured_at)


class GameFeatureService:
    def __init__(self, game_exe_provider: Callable[[], Path | None]) -> None:
        self.game_exe_provider = game_exe_provider
        self.last_request_id: str | None = None
        self.last_request_time = 0
        self._snapshot_identity: tuple[str, int, int, int] | None = None
        self._snapshot_payload: object = None

    def _directory(self) -> Path:
        game = self.game_exe_provider()
        if game is None or game.name.casefold() != "lostcastle2.exe" or not game.is_file():
            raise GameFeatureError("请先在设置中定位 LostCastle2.exe")
        game_root = game.resolve().parent
        target = game_root / FEATURE_DIRECTORY
        for path in (target, *target.parents):
            if path.exists() or path.is_symlink():
                attrs = getattr(path.lstat(), "st_file_attributes", 0)
                if path.is_symlink() or attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise GameFeatureError("功能配置目录是链接，请先恢复普通目录")
            if path == game_root:
                break
        return target

    @staticmethod
    def _read(path: Path, limit: int) -> object:
        if path.is_symlink() or not path.is_file():
            return None
        if path.stat().st_size > limit:
            raise GameFeatureError("功能数据文件过大，暂不可读")
        with path.open("r", encoding="utf-8-sig") as stream:
            return json.load(stream)

    @staticmethod
    def _write(path: Path, data: object) -> None:
        if path.is_symlink():
            raise GameFeatureError("功能配置文件是链接")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".feature-", suffix=".tmp", delete=False) as stream:
                json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
                stream.write("\n")
                temporary = Path(stream.name)
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def settings(self) -> dict[str, bool]:
        defaults = {"team_enabled": False, "loadout_enabled": True}
        try:
            raw = self._read(self._directory() / "settings.json", 16 * 1024)
            if isinstance(raw, dict):
                return {key: raw.get(key, default) is True for key, default in defaults.items()}
        except (GameFeatureError, OSError, ValueError):
            pass
        return defaults

    def set_enabled(self, key: str, enabled: bool) -> None:
        if key not in {"team_enabled", "loadout_enabled"} or type(enabled) is not bool:
            raise GameFeatureError("不支持的功能开关")
        values = self.settings()
        values[key] = enabled
        self._write(self._directory() / "settings.json", {"schema_version": 1, **values})

    def snapshot(self, game_pid: int | None, *, now_ms: int | None = None) -> FeatureSnapshot:
        if game_pid is None:
            return FeatureSnapshot("waiting", "游戏未运行，请从顶部启动游戏")
        try:
            path = self._directory() / "snapshot.json"
            if not path.is_file():
                return FeatureSnapshot("waiting", "等待游戏连接；新安装组件后请重启游戏")
            identity = (str(path), path.stat().st_size, path.stat().st_mtime_ns, game_pid)
            if identity != self._snapshot_identity:
                self._snapshot_payload = self._read(path, MAX_SNAPSHOT_BYTES)
                self._snapshot_identity = identity
            return parse_feature_snapshot(self._snapshot_payload, game_pid, now_ms if now_ms is not None else round(time.time() * 1000))
        except (GameFeatureError, OSError, ValueError):
            return FeatureSnapshot("invalid", "状态数据暂不可读，等待下一次刷新")

    def request(self, action: str, game_pid: int, **selection: Any) -> str:
        if not self.settings()["loadout_enabled"]:
            raise GameFeatureError("请先启用配装助手")
        snapshot = self.snapshot(game_pid)
        if snapshot.state != "ready" or snapshot.loadout is None or snapshot.loadout.get("in_camp") is not True:
            raise GameFeatureError("请在营地、角色就绪后使用配装助手")
        expected = {"equipment": {"item_id"}, "gem": {"inscription_id", "gem_id", "slot"}, "enchantment": {"enchantment_id"}}
        if action not in expected or set(selection) != expected[action]:
            raise GameFeatureError("请选择有效的配装项目")
        rows = snapshot.loadout
        valid = False
        if action == "equipment":
            valid = any(row["id"] == selection["item_id"] for row in rows["equipment"])
        elif action == "enchantment":
            valid = type(selection["enchantment_id"]) is int and any(row["id"] == selection["enchantment_id"] for row in rows["enchantments"])
        elif type(selection["slot"]) is int and type(selection["gem_id"]) is int:
            valid = any(row["id"] == selection["gem_id"] for row in rows["gems"]) and any(row["id"] == selection["inscription_id"] and any(slot["slot"] == selection["slot"] for slot in row["slots"]) for row in rows["inscriptions"])
        if not valid:
            raise GameFeatureError("所选项目已不在当前目录，请刷新后重新选择")
        if self.last_request_id is not None and round(time.time() * 1000) - self.last_request_time < 15000 and self.result(game_pid) is None:
            raise GameFeatureError("上一个配装请求仍在处理，请稍候")
        request_id = uuid.uuid4().hex
        now = round(time.time() * 1000)
        self._write(self._directory() / "request.json", {"schema_version": 1, "request_id": request_id, "created_at": now, "game_pid": game_pid, "action": action, **selection})
        self.last_request_id = request_id
        self.last_request_time = now
        return request_id

    def result(self, game_pid: int) -> dict[str, Any] | None:
        if self.last_request_id is None:
            return None
        try:
            result = self._read(self._directory() / "result.json", 16 * 1024)
            if isinstance(result, dict) and result.get("request_id") == self.last_request_id and result.get("game_pid") == game_pid and result.get("state") in {"complete", "error"} and _text(result.get("message", ""), 240):
                return result
        except (GameFeatureError, OSError, ValueError):
            pass
        if self.last_request_time > 0 and round(time.time() * 1000) - self.last_request_time >= 15000:
            return {"request_id": self.last_request_id, "game_pid": game_pid, "state": "error", "message": "尚未收到游戏确认，请先在游戏中核对结果；工具箱不会自动重复执行。"}
        return None


class DemoGameFeatureService:
    """Explicit development demo; no game files, native calls or saved settings."""
    is_demo = True
    demo_pid = 42

    def __init__(self) -> None:
        self._settings = {"team_enabled": False, "loadout_enabled": True}
        self.last_request_id: str | None = None
        self.last_request_time = 0
        self._result: dict[str, Any] | None = None
        self._weapon = "终极大剑"

    def settings(self) -> dict[str, bool]:
        return dict(self._settings)

    def set_enabled(self, key: str, enabled: bool) -> None:
        if key not in self._settings or type(enabled) is not bool:
            raise GameFeatureError("不支持的功能开关")
        self._settings[key] = enabled

    def snapshot(self, game_pid: int | None, **_kwargs: Any) -> FeatureSnapshot:
        shared_items = [{"kind": "PassiveProps", "name": "孽者之石", "id": "demo-stone", "count": 1}, {"kind": "PassiveProps", "name": "被封印的冰灵", "id": "demo-ice", "count": 2}]
        local = {"slot": 0, "name": "我的角色", "is_local": True, "is_host": True, "hp": 256, "max_hp": 320, "mp": 40, "max_mp": 75, "resources_state": "ready", "resources": {"gold": 0, "crystal": 1250, "iron": 8, "coins": 3}, "inventory_state": "ready", "equipment": {"weapon": self._weapon, "armor": "兽面吞头连环铠"}, "items": shared_items, "inscriptions": [{"id": "demo-inscription", "name": "力量刻印", "gems": [{"name": "三角灵魂石", "main": "攻击力提升", "sub": "生命上限提升", "slot": 0}]}]}
        teammate = {"slot": 1, "name": "队友 · 一位很长名字的冒险者", "is_local": False, "is_host": False, "hp": 95, "max_hp": 200, "mp": 0, "max_mp": 80, "resources_state": "not_synced", "resources": {"gold": None, "crystal": None, "iron": None, "coins": None}, "inventory_state": "ready", "items": shared_items + [{"kind": "AlchemyMix", "name": "已经同步的炼金效果", "count": 1}], "inscriptions": []}
        loadout = {"in_camp": True, "equipment": [{"id": "demo-sword", "name": "终极大剑", "kind": "Weapon"}, {"id": "demo-staff", "name": "冰封魔杖", "kind": "Weapon"}, {"id": "demo-armor", "name": "兽面吞头连环铠", "kind": "Armor"}], "enchantments": [{"id": 0, "name": "攻击力提升"}, {"id": 1, "name": "生命上限提升"}], "inscriptions": [{"id": "demo-inscription", "name": "力量刻印", "weapon_type": "THW", "slots": [{"slot": 0, "kind": "Triangle", "name": "三角灵魂石"}, {"slot": 1, "kind": "Square", "name": "空槽"}]}], "gems": [{"id": 1, "name": "三角灵魂石", "main": "攻击力提升", "sub": "生命上限提升", "kind": "Triangle"}, {"id": 2, "name": "方形灵魂石", "main": "暴击率提升", "sub": "", "kind": "Square"}]}
        team = (local, teammate) if self._settings["team_enabled"] else (local,)
        return FeatureSnapshot("ready", "演示数据 · 不连接或修改游戏", team, loadout if self._settings["loadout_enabled"] else None, round(time.time() * 1000))

    def request(self, action: str, game_pid: int, **selection: Any) -> str:
        if not self._settings["loadout_enabled"]:
            raise GameFeatureError("请先启用配装助手")
        self.last_request_id = uuid.uuid4().hex
        if action == "equipment":
            self._weapon = "冰封魔杖" if selection.get("item_id") == "demo-staff" else "终极大剑"
        self._result = {"request_id": self.last_request_id, "game_pid": self.demo_pid, "state": "complete", "message": "演示操作已完成；实际游戏未被修改。"}
        return self.last_request_id

    def result(self, game_pid: int) -> dict[str, Any] | None:
        return self._result

