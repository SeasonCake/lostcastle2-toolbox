from __future__ import annotations

from typing import Any


MOD_CATEGORIES = {
    "all": "全部功能", "combat": "战斗与召唤", "loadout": "装备与刻印",
    "loot": "掉落与资源", "information": "信息与面板", "room": "房间与联机",
    "appearance": "外观与特效", "utility": "其他工具",
}

MOD_CATEGORY_IDS = {
    "loadout": {"soul-stone-trainer", "weapon-picker", "inscription-soulstone-manager", "all-inscriptions", "item-ban-freenix", "multi-resonance", "alchemy-capacity", "fire-dragon-synthesis", "unique-weapon-perks", "build-master"},
    "loot": {"gold-editor-f5", "resource-transfer-f1", "loot-combat-enhancement", "chest-drop-enhancement", "no-soulstone-drops", "entrance-free-refresh", "curse-coin", "monster-treasure"},
    "information": {"player-live-stats", "inventory-source-panel", "unified-tools", "damage-meter", "evil-spirit-stack", "team-stats"},
    "room": {"max-players-16", "multiplayer-room-fix", "room-type-reforger", "room-prefix", "welcome-message", "stage-countdown", "boss-cinematic-free"},
    "appearance": {"hide-weapon-fx", "purple-critical-damage", "armor-transmog", "staff-skin-swap", "nightmare-doll-skin", "hand-color-white", "summon-model-swap"},
    "utility": {"enhancement-plan"},
    "combat": {"player-auto-reborn", "lightning-enhance-plate", "dynamic-hp", "not-drug-god", "hex-augment", "fire-dragon-enhancement", "dual-blades-overhaul", "icebound-wand-tuner", "tornado-greatsword", "master-craftsman-cannon", "dark-matter-black-hole", "goblin-cannon-dark-matter", "thunder-hammer-summon", "coil-summon-bobo", "bobo-staff", "evilstone-power-duration", "ice-system-enhancement", "armor-enhancement", "curse-treasure-enhancement", "desert-marauder-combo", "inspire-duration", "boss-hpbar-steady", "chaos-charge-fix", "golden-rescue", "spark-activator", "npc-recruit-unlimited", "demon-invasion", "brain-core-boost", "golem-shield-boost", "sword-break-block-buff", "ice-pillar-enhancement", "nightfall-bow-boost", "summon-balance", "evil-fire-crusher-summon", "hideyoshi-summon", "reaper-summon", "reinforce-hideyoshi", "client-armor-enhancement", "mech-attack-inherit", "thunder-spirit-summon", "cannon-resonance-alt", "reaper-contract", "burst-bow", "redstone-carver", "kalion-spear", "poison-fog-cap", "shadow-lantern-enhancement", "niya-summon"},
}


def mod_category(mod_id: str) -> str:
    for category, ids in MOD_CATEGORY_IDS.items():
        if mod_id in ids:
            return category
    return "utility"


def filter_mods(entries: Any, query: str, category: str) -> list[Any]:
    folded = query.strip().casefold()
    result = []
    for descriptor in entries:
        if category != "all" and mod_category(descriptor.mod_id) != category:
            continue
        display = descriptor.display
        haystack = "\n".join((display.name, display.author, display.summary, display.usage_hint, MOD_CATEGORIES[mod_category(descriptor.mod_id)])).casefold()
        if not folded or folded in haystack:
            result.append(descriptor)
    return result
