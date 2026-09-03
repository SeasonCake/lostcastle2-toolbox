from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
import json
import math
from pathlib import Path
from typing import Any
import zipfile


def _nonnegative_int(value: object) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _number(value: object) -> float:
    if type(value) not in (int, float):
        return 0.0
    result = float(value)
    return result if math.isfinite(result) and result > 0.0 else 0.0


def _event_locator(event: Mapping[str, object]) -> dict[str, object]:
    return {
        "sequence": event.get("sequence"),
        "monotonic_ms": event.get("monotonic_ms"),
        "room_id": event.get("room_id"),
        "actor_entity_id": event.get("actor_entity_id"),
        "source_token": event.get("source_token"),
        "settlement_damage": event.get("settlement_damage"),
        "is_boss": event.get("is_boss"),
    }


def analyze_damage_events(
    events: Iterable[Mapping[str, object]],
    summary: Mapping[str, object],
) -> dict[str, object]:
    official: dict[str, dict[str, int | None]] = {}
    player_slots: dict[str, int | None] = {}
    breakdown = summary.get("player_breakdown")
    if isinstance(breakdown, Mapping):
        for player_id, raw_values in breakdown.items():
            if not isinstance(player_id, str) or not isinstance(raw_values, Mapping):
                continue
            official[player_id] = {
                "damage": _nonnegative_int(raw_values.get("official_damage")),
                "boss": _nonnegative_int(raw_values.get("official_boss_damage")),
            }
            player_slots[player_id] = _nonnegative_int(raw_values.get("player_slot"))

    players: dict[str, dict[str, Any]] = {}
    room_actors: dict[tuple[str, str], dict[str, Any]] = {}
    event_count = 0
    dealt_aggregate_count = 0

    for event in events:
        event_count += 1
        if (
            event.get("event_type") != "damage_resolution"
            or event.get("damage_direction") != "dealt"
            or event.get("aggregate") is not True
        ):
            continue
        dealt_aggregate_count += 1
        owner = event.get("owner_player_id")
        if not isinstance(owner, str) or not owner:
            owner = "<unattributed>"
        player = players.setdefault(
            owner,
            {
                "events": 0,
                "current": 0,
                "boss_current": 0,
                "ceil_pre": 0,
                "ceil_post": 0,
                "ceil_applied": 0,
                "boss_ceil_pre": 0,
                "boss_ceil_post": 0,
                "boss_ceil_applied": 0,
                "fallback_events": 0,
                "fallback_damage": 0,
                "overkill": 0.0,
                "first_zero_real_fallback": None,
                "first_damage_above_official_final": None,
                "first_boss_above_official_final": None,
                "source_totals": {},
            },
        )
        damage = _nonnegative_int(event.get("settlement_damage")) or 0
        pre = _number(event.get("pre_mitigation_damage"))
        post = _number(event.get("post_mitigation_damage"))
        applied = _number(event.get("applied_hp_damage"))
        is_boss = event.get("is_boss") is True
        player["events"] += 1
        player["current"] += damage
        player["ceil_pre"] += math.ceil(pre)
        player["ceil_post"] += math.ceil(post)
        player["ceil_applied"] += math.ceil(applied)
        player["overkill"] += _number(event.get("overkill_damage"))
        if is_boss:
            player["boss_current"] += damage
            player["boss_ceil_pre"] += math.ceil(pre)
            player["boss_ceil_post"] += math.ceil(post)
            player["boss_ceil_applied"] += math.ceil(applied)
        if post <= 0.0 and pre > 0.0:
            player["fallback_events"] += 1
            player["fallback_damage"] += damage
            if player["first_zero_real_fallback"] is None:
                player["first_zero_real_fallback"] = _event_locator(event)

        source = event.get("source_token")
        if not isinstance(source, str) or not source:
            source = "<none>"
        source_totals = player["source_totals"].setdefault(
            source,
            {"events": 0, "damage": 0, "boss": 0, "fallback_events": 0,
             "fallback_damage": 0},
        )
        source_totals["events"] += 1
        source_totals["damage"] += damage
        if is_boss:
            source_totals["boss"] += damage
        if post <= 0.0 and pre > 0.0:
            source_totals["fallback_events"] += 1
            source_totals["fallback_damage"] += damage

        expected = official.get(owner)
        if expected is not None:
            official_damage = expected["damage"]
            official_boss = expected["boss"]
            if (
                official_damage is not None
                and player["first_damage_above_official_final"] is None
                and player["current"] > official_damage
            ):
                player["first_damage_above_official_final"] = {
                    **_event_locator(event),
                    "cumulative": player["current"],
                    "official_final": official_damage,
                    "excess": player["current"] - official_damage,
                }
            if (
                official_boss is not None
                and player["first_boss_above_official_final"] is None
                and player["boss_current"] > official_boss
            ):
                player["first_boss_above_official_final"] = {
                    **_event_locator(event),
                    "cumulative": player["boss_current"],
                    "official_final": official_boss,
                    "excess": player["boss_current"] - official_boss,
                }

        room = event.get("room_id")
        actor = event.get("actor_entity_id")
        if isinstance(room, str) and room and isinstance(actor, str) and actor:
            actor_bucket = room_actors.setdefault(
                (room, actor),
                {
                    "room_id": room,
                    "actor_entity_id": actor,
                    "owners": set(),
                    "sources": set(),
                    "events": 0,
                    "damage": 0,
                    "boss": 0,
                    "owner_damage": {},
                },
            )
            actor_bucket["owners"].add(owner)
            actor_bucket["sources"].add(source)
            actor_bucket["events"] += 1
            actor_bucket["damage"] += damage
            if is_boss:
                actor_bucket["boss"] += damage
            actor_bucket["owner_damage"][owner] = (
                actor_bucket["owner_damage"].get(owner, 0) + damage
            )

    player_metrics: dict[str, object] = {}
    for player_id, values in sorted(
        players.items(),
        key=lambda item: (
            player_slots.get(item[0]) is None,
            player_slots.get(item[0]) or 0,
            item[0],
        ),
    ):
        expected = official.get(player_id, {})
        official_damage = expected.get("damage")
        official_boss = expected.get("boss")
        result = dict(values)
        result["player_slot"] = player_slots.get(player_id)
        result["official_damage"] = official_damage
        result["official_boss"] = official_boss
        result["damage_delta"] = (
            result["current"] - official_damage
            if official_damage is not None else None
        )
        result["boss_delta"] = (
            result["boss_current"] - official_boss
            if official_boss is not None else None
        )
        result["formula_damage_delta"] = {
            "current": result["damage_delta"],
            "ceil_pre": (
                result["ceil_pre"] - official_damage
                if official_damage is not None else None
            ),
            "ceil_post": (
                result["ceil_post"] - official_damage
                if official_damage is not None else None
            ),
            "ceil_applied": (
                result["ceil_applied"] - official_damage
                if official_damage is not None else None
            ),
        }
        result["formula_boss_delta"] = {
            "current": result["boss_delta"],
            "ceil_pre": (
                result["boss_ceil_pre"] - official_boss
                if official_boss is not None else None
            ),
            "ceil_post": (
                result["boss_ceil_post"] - official_boss
                if official_boss is not None else None
            ),
            "ceil_applied": (
                result["boss_ceil_applied"] - official_boss
                if official_boss is not None else None
            ),
        }
        player_metrics[player_id] = result

    shared_actors = [
        bucket for bucket in room_actors.values() if len(bucket["owners"]) > 1
    ]
    shared_owner_damage: dict[str, int] = {}
    for bucket in shared_actors:
        for owner, damage in bucket["owner_damage"].items():
            shared_owner_damage[owner] = shared_owner_damage.get(owner, 0) + damage
    top_shared_actors = []
    for bucket in sorted(shared_actors, key=lambda item: item["damage"], reverse=True)[:30]:
        top_shared_actors.append(
            {
                "room_id": bucket["room_id"],
                "actor_entity_id": bucket["actor_entity_id"],
                "owners": sorted(bucket["owners"]),
                "sources": sorted(bucket["sources"]),
                "events": bucket["events"],
                "damage": bucket["damage"],
                "boss": bucket["boss"],
                "owner_damage": dict(sorted(bucket["owner_damage"].items())),
            }
        )

    team: dict[str, int] = {}
    for field in (
        "current", "boss_current", "ceil_pre", "ceil_post", "ceil_applied",
        "boss_ceil_pre", "boss_ceil_post", "boss_ceil_applied",
        "fallback_events", "fallback_damage",
    ):
        team[field] = sum(int(values[field]) for values in players.values())
    team["official_damage"] = sum(
        value["damage"] or 0 for value in official.values()
    )
    team["official_boss"] = sum(value["boss"] or 0 for value in official.values())
    team["damage_delta"] = team["current"] - team["official_damage"]
    team["boss_delta"] = team["boss_current"] - team["official_boss"]

    return {
        "summary_session_id": summary.get("session_id"),
        "official_damage_complete": summary.get("official_damage_complete") is True,
        "official_boss_damage_complete": (
            summary.get("official_boss_damage_complete") is True
        ),
        "event_count": event_count,
        "dealt_aggregate_count": dealt_aggregate_count,
        "players": player_metrics,
        "team": team,
        "shared_room_actor": {
            "count": len(shared_actors),
            "damage": sum(bucket["damage"] for bucket in shared_actors),
            "boss": sum(bucket["boss"] for bucket in shared_actors),
            "owner_damage": dict(sorted(shared_owner_damage.items())),
            "top": top_shared_actors,
        },
    }


def analyze_archive(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        summary = json.loads(archive.read("summary.json"))
        with archive.open("events.jsonl") as raw_events:
            events = (json.loads(line) for line in raw_events)
            result = analyze_damage_events(events, summary)
    result["archive"] = {
        "path": str(path),
        "session_key": manifest.get("session_key"),
        "manifest_event_count": manifest.get("event_count"),
        "events_truncated": manifest.get("events_truncated"),
        "events_sha256": manifest.get("events_sha256"),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="重放LC2匿名事件流并量化过程值与最终官方值的分岔。",
    )
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = analyze_archive(args.archive)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
