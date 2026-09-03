from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Iterable, Mapping


SUMMARY_MARKER = "[LC2CB-OWNER-CHECK]"
OFFICIAL_MARKER = "[LC2CB-OFFICIAL]"
FIELD_PATTERN = re.compile(r"(?P<key>[a-z_]+)=(?P<value>[^\s]+)")
SLOT_PATTERN = re.compile(
    r"slot=(?P<slot>\d+):events=(?P<events>\d+):"
    r"unique=(?P<unique>\d+):matched=(?P<matched>\d+):"
    r"forwarded=(?P<forwarded>\d+):owner_match=(?P<owner_match>\d+):"
    r"conflict=(?P<conflict>\d+):unresolved=(?P<unresolved>\d+)"
)
OFFICIAL_SLOT_PATTERN = re.compile(
    r"slot=(?P<slot>\d+):damage=(?P<damage>null|\d+):boss=(?P<boss>null|\d+)"
)
ROOM_LOCATION_PATTERN = re.compile(
    r"stage=(?P<stage>-?\d+)\s+scenario=(?P<scenario>[^\s]+)\s+"
    r"room_index=(?P<room>-?\d+)\s+map=(?P<map>.*)$"
)


@dataclass
class SlotProbe:
    events: int = 0
    unique: int = 0
    matched: int = 0
    forwarded: int = 0
    owner_match: int = 0
    conflict: int = 0
    unresolved: int = 0

    def add(self, other: SlotProbe) -> None:
        for field in self.__dataclass_fields__:
            setattr(self, field, getattr(self, field) + getattr(other, field))


@dataclass(frozen=True)
class ProbeVerdict:
    passed: bool
    reasons: tuple[str, ...]
    summary_count: int
    local_slots: tuple[int, ...]
    settlement_unique: int
    registered_unique: int
    matched_unique: int
    duplicate_callback_conflicts: int
    slots: dict[int, SlotProbe]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["slots"] = {
            str(slot): asdict(values) for slot, values in sorted(self.slots.items())
        }
        return payload


@dataclass(frozen=True)
class FinalOfficialVerdict:
    passed: bool
    reasons: tuple[str, ...]
    summary_count: int
    final_records: int
    expected_slots: int
    identity_matches: int
    identity_unmatched: int
    identity_collisions: int
    index_mismatches: int
    published_slots: int
    roster_collapsed_to_single: bool
    slots: dict[int, tuple[int, int]]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["slots"] = {
            str(slot): {"damage": values[0], "boss": values[1]}
            for slot, values in sorted(self.slots.items())
        }
        return payload


@dataclass(frozen=True)
class FinalObservedSlot:
    observed_damage: int
    official_damage: int
    damage_delta: int
    observed_boss: int
    official_boss: int
    boss_delta: int


@dataclass(frozen=True)
class FinalObservedVerdict:
    passed: bool
    reasons: tuple[str, ...]
    summary_session_id: str | None
    process_basis: str
    slot_count: int
    mismatch_slots: tuple[int, ...]
    observed_team_damage: int
    official_team_damage: int
    team_damage_delta: int
    observed_team_boss: int
    official_team_boss: int
    team_boss_delta: int
    slots: dict[int, FinalObservedSlot]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["slots"] = {
            str(slot): asdict(values) for slot, values in sorted(self.slots.items())
        }
        return payload


def _integer(fields: dict[str, str], name: str) -> int:
    try:
        return max(0, int(fields.get(name, "0")))
    except ValueError:
        return 0


def has_phantom_exit_session(lines: Iterable[str]) -> bool:
    saw_active_room = False
    closed_by_preload = False
    closing_to_camp = False
    for line in lines:
        if "[LC2CB-ROOM]" not in line:
            continue
        if "callback=round_start" in line and "is_camp=True" in line:
            closing_to_camp = saw_active_room and not closed_by_preload
            continue
        if "callback=round_end_preload_camp" in line:
            closing_to_camp = False
            closed_by_preload = True
            continue
        if "callback=change_room_end" in line and "valid=True" in line and "is_camp=False" in line:
            if closing_to_camp:
                return True
            saw_active_room = True
            closed_by_preload = False
    return False


def has_next_run_blocked_by_closing_gate(lines: Iterable[str]) -> bool:
    closing = False
    blocked_locations: set[tuple[str, str, str, str]] = set()
    for line in lines:
        if "[LC2CB-ROOM]" not in line:
            continue
        if "callback=round_end_preload_camp" in line:
            closing = True
            blocked_locations.clear()
            continue
        if not closing or "callback=change_room_end" not in line:
            continue
        if "valid=True" in line and "is_camp=False" in line:
            closing = False
            blocked_locations.clear()
            continue
        if "valid=False" not in line or "is_camp=False" not in line:
            continue
        match = ROOM_LOCATION_PATTERN.search(line)
        if match is None:
            continue
        blocked_locations.add(
            (
                match.group("stage"),
                match.group("scenario"),
                match.group("room"),
                match.group("map"),
            )
        )
        if len(blocked_locations) >= 2:
            return True
    return False


def evaluate_short_probe(
    lines: Iterable[str],
    *,
    minimum_remote_slots: int = 2,
    require_forwarded_remote_slot: bool = True,
) -> ProbeVerdict:
    lines = tuple(lines)
    summary_count = 0
    local_slots: set[int] = set()
    settlement_unique = 0
    registered_unique = 0
    matched_unique = 0
    duplicate_callback_conflicts = 0
    slots: dict[int, SlotProbe] = {}

    for line in lines:
        if SUMMARY_MARKER not in line:
            continue
        summary_count += 1
        fields = {
            match.group("key"): match.group("value")
            for match in FIELD_PATTERN.finditer(line)
        }
        local_value = fields.get("local_slot")
        if local_value and local_value != "null":
            try:
                local_slots.add(int(local_value))
            except ValueError:
                pass
        settlement_unique += _integer(fields, "settlement_unique")
        registered_unique += _integer(fields, "registered_unique")
        matched_unique += _integer(fields, "matched_unique")
        duplicate_callback_conflicts += _integer(
            fields,
            "duplicate_callback_conflicts",
        )
        for match in SLOT_PATTERN.finditer(line):
            slot = int(match.group("slot"))
            values = SlotProbe(
                **{
                    field: int(match.group(field))
                    for field in SlotProbe.__dataclass_fields__
                }
            )
            slots.setdefault(slot, SlotProbe()).add(values)

    reasons: list[str] = []
    if has_phantom_exit_session(lines):
        reasons.append("phantom_session_after_round_start")
    if has_next_run_blocked_by_closing_gate(lines):
        reasons.append("next_run_blocked_by_closing_gate")
    if summary_count == 0:
        reasons.append("owner_check_missing")
    if settlement_unique <= 0:
        reasons.append("settlement_hits_missing")
    if registered_unique <= 0:
        reasons.append("registered_hits_missing")
    if matched_unique <= 0:
        reasons.append("registered_settlement_overlap_missing")
    if registered_unique > 0 and matched_unique != registered_unique:
        reasons.append("registered_settlement_overlap_incomplete")
    if duplicate_callback_conflicts > 0:
        reasons.append("duplicate_callback_slot_conflict")

    remote_slots = {
        slot: values
        for slot, values in slots.items()
        if slot not in local_slots and values.events > 0
    }
    if len(remote_slots) < max(1, minimum_remote_slots):
        reasons.append("remote_slot_coverage_insufficient")
    for values in slots.values():
        if values.conflict > 0:
            reasons.append("registered_owner_slot_conflict")
            break
    if require_forwarded_remote_slot and not any(
        values.forwarded > 0 for values in remote_slots.values()
    ):
        reasons.append("remote_forwarded_hit_missing")

    return ProbeVerdict(
        passed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        summary_count=summary_count,
        local_slots=tuple(sorted(local_slots)),
        settlement_unique=settlement_unique,
        registered_unique=registered_unique,
        matched_unique=matched_unique,
        duplicate_callback_conflicts=duplicate_callback_conflicts,
        slots=slots,
    )


def evaluate_final_official_sync(lines: Iterable[str]) -> FinalOfficialVerdict:
    lines = tuple(lines)
    summaries = [
        line
        for line in lines
        if OFFICIAL_MARKER in line and "final_ready=true" in line
    ]
    accepted_summary_seen = any("final_accepted=true" in item for item in summaries)
    acceptance_regressed = bool(
        accepted_summary_seen
        and summaries
        and "final_accepted=true" not in summaries[-1]
    )
    line = summaries[-1] if summaries else ""
    fields = {
        match.group("key"): match.group("value")
        for match in FIELD_PATTERN.finditer(line)
    }
    final_records = _integer(fields, "final_records")
    expected_slots = _integer(fields, "final_expected_slots")
    identity_matches = _integer(fields, "final_identity_matches")
    identity_unmatched = _integer(fields, "final_identity_unmatched")
    identity_collisions = _integer(fields, "final_identity_collisions")
    index_mismatches = _integer(fields, "final_index_mismatches")
    published_slots = _integer(fields, "final_published_slots")
    slots: dict[int, tuple[int, int]] = {}
    for match in OFFICIAL_SLOT_PATTERN.finditer(line):
        if match.group("damage") == "null" or match.group("boss") == "null":
            continue
        slots[int(match.group("slot"))] = (
            int(match.group("damage")),
            int(match.group("boss")),
        )

    maximum_roster = 0
    roster_collapsed_to_single = False
    for candidate in lines:
        if OFFICIAL_MARKER not in candidate:
            continue
        candidate_fields = {
            match.group("key"): match.group("value")
            for match in FIELD_PATTERN.finditer(candidate)
        }
        members = _integer(candidate_fields, "members")
        if members > maximum_roster:
            maximum_roster = members
        elif maximum_roster >= 2 and members == 1:
            roster_collapsed_to_single = True

    reasons: list[str] = []
    if not summaries:
        reasons.append("final_official_summary_missing")
    if acceptance_regressed:
        reasons.append("final_acceptance_regressed")
    if roster_collapsed_to_single and not summaries:
        reasons.append("multiplayer_roster_collapsed_to_single_without_final_sync")
    if fields.get("slot_basis") != "platform_identity_hmac":
        reasons.append("final_identity_basis_missing")
    if expected_slots <= 0:
        reasons.append("final_expected_slots_missing")
    if final_records != expected_slots:
        reasons.append("final_record_count_mismatch")
    if identity_matches != expected_slots:
        reasons.append("final_identity_match_incomplete")
    if identity_unmatched > 0:
        reasons.append("final_identity_unmatched")
    if identity_collisions > 0:
        reasons.append("final_identity_collision")
    if _integer(fields, "final_duplicate_slots") > 0:
        reasons.append("final_duplicate_slot")
    if published_slots != expected_slots:
        reasons.append("final_publish_incomplete")
    if fields.get("final_accepted") != "true":
        reasons.append("final_official_rejected")
    if len(slots) != expected_slots:
        reasons.append("final_slot_totals_incomplete")

    return FinalOfficialVerdict(
        passed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        summary_count=len(summaries),
        final_records=final_records,
        expected_slots=expected_slots,
        identity_matches=identity_matches,
        identity_unmatched=identity_unmatched,
        identity_collisions=identity_collisions,
        index_mismatches=index_mismatches,
        published_slots=published_slots,
        roster_collapsed_to_single=roster_collapsed_to_single,
        slots=slots,
    )


def _strict_nonnegative_integer(value: object) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def evaluate_final_observed_match(
    summary: Mapping[str, object] | None,
) -> FinalObservedVerdict:
    reasons: list[str] = []
    slots: dict[int, FinalObservedSlot] = {}
    session_id: str | None = None
    process_basis = "per_hit_observed"

    if summary is None:
        reasons.append("final_observed_summary_missing")
    else:
        raw_session_id = summary.get("session_id")
        if isinstance(raw_session_id, str) and raw_session_id:
            session_id = raw_session_id
        if summary.get("official_damage_complete") is not True:
            reasons.append("final_observed_official_damage_incomplete")
        if summary.get("official_boss_damage_complete") is not True:
            reasons.append("final_observed_official_boss_incomplete")

        breakdown = summary.get("player_breakdown")
        if not isinstance(breakdown, Mapping) or not breakdown:
            reasons.append("final_observed_player_breakdown_missing")
        else:
            use_live_cache = all(
                isinstance(raw_values, Mapping)
                and _strict_nonnegative_integer(
                    raw_values.get("last_live_damage")
                ) is not None
                and _strict_nonnegative_integer(
                    raw_values.get("last_live_boss_damage")
                ) is not None
                and _strict_nonnegative_integer(
                    raw_values.get("last_live_observed_damage_anchor")
                ) is not None
                and _strict_nonnegative_integer(
                    raw_values.get("last_live_observed_boss_anchor")
                ) is not None
                for raw_values in breakdown.values()
            )
            if use_live_cache:
                process_basis = "live_official_anchor_plus_observed_delta"
            for player_id, raw_values in breakdown.items():
                if not isinstance(raw_values, Mapping):
                    reasons.append("final_observed_player_entry_invalid")
                    continue
                slot = _strict_nonnegative_integer(raw_values.get("player_slot"))
                observed_damage = _strict_nonnegative_integer(
                    raw_values.get("observed_damage_dealt")
                )
                official_damage = _strict_nonnegative_integer(
                    raw_values.get("official_damage")
                )
                observed_boss = _strict_nonnegative_integer(
                    raw_values.get("observed_boss_damage")
                )
                official_boss = _strict_nonnegative_integer(
                    raw_values.get("official_boss_damage")
                )
                if (
                    slot is None
                    or observed_damage is None
                    or official_damage is None
                    or observed_boss is None
                    or official_boss is None
                ):
                    reasons.append("final_observed_slot_totals_invalid")
                    continue
                if slot in slots:
                    reasons.append("final_observed_duplicate_slot")
                    continue
                if use_live_cache:
                    live_damage = _strict_nonnegative_integer(
                        raw_values.get("last_live_damage")
                    )
                    live_boss = _strict_nonnegative_integer(
                        raw_values.get("last_live_boss_damage")
                    )
                    damage_anchor = _strict_nonnegative_integer(
                        raw_values.get("last_live_observed_damage_anchor")
                    )
                    boss_anchor = _strict_nonnegative_integer(
                        raw_values.get("last_live_observed_boss_anchor")
                    )
                    assert live_damage is not None
                    assert live_boss is not None
                    assert damage_anchor is not None
                    assert boss_anchor is not None
                    observed_damage = live_damage + max(
                        0,
                        observed_damage - damage_anchor,
                    )
                    observed_boss = live_boss + max(
                        0,
                        observed_boss - boss_anchor,
                    )
                slots[slot] = FinalObservedSlot(
                    observed_damage=observed_damage,
                    official_damage=official_damage,
                    damage_delta=observed_damage - official_damage,
                    observed_boss=observed_boss,
                    official_boss=official_boss,
                    boss_delta=observed_boss - official_boss,
                )

    mismatch_slots = tuple(
        slot
        for slot, values in sorted(slots.items())
        if values.damage_delta != 0 or values.boss_delta != 0
    )
    if any(values.damage_delta != 0 for values in slots.values()):
        reasons.append("final_observed_damage_mismatch")
    if any(values.boss_delta != 0 for values in slots.values()):
        reasons.append("final_observed_boss_mismatch")

    observed_team_damage = sum(value.observed_damage for value in slots.values())
    official_team_damage = sum(value.official_damage for value in slots.values())
    observed_team_boss = sum(value.observed_boss for value in slots.values())
    official_team_boss = sum(value.official_boss for value in slots.values())

    return FinalObservedVerdict(
        passed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        summary_session_id=session_id,
        process_basis=process_basis,
        slot_count=len(slots),
        mismatch_slots=mismatch_slots,
        observed_team_damage=observed_team_damage,
        official_team_damage=official_team_damage,
        team_damage_delta=observed_team_damage - official_team_damage,
        observed_team_boss=observed_team_boss,
        official_team_boss=official_team_boss,
        team_boss_delta=observed_team_boss - official_team_boss,
        slots=slots,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="判定 LC2 多人 registered-player attacker 短房正控。",
    )
    parser.add_argument("log", type=Path)
    parser.add_argument("--minimum-remote-slots", type=int, default=2)
    parser.add_argument(
        "--allow-no-forwarded-remote-hit",
        action="store_true",
        help="仅用于本体直击房；默认至少一个远端slot必须覆盖投射/召唤转发。",
    )
    parser.add_argument(
        "--require-final-official",
        action="store_true",
        help=(
            "同时要求退出后的最终官方record按匿名身份完整映射，并要求过程逐slot"
            "累计与最终官方值一致。"
        ),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        help="对比过程值的summary.json；默认使用日志同目录的summary.json。",
    )
    args = parser.parse_args()
    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    verdict = evaluate_short_probe(
        lines,
        minimum_remote_slots=args.minimum_remote_slots,
        require_forwarded_remote_slot=not args.allow_no_forwarded_remote_hit,
    )
    payload: dict[str, object] = verdict.to_dict()
    passed = verdict.passed
    if args.require_final_official:
        final_verdict = evaluate_final_official_sync(lines)
        summary_path = args.summary or args.log.with_name("summary.json")
        summary: Mapping[str, object] | None = None
        if summary_path.is_file():
            try:
                loaded = json.loads(summary_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                loaded = None
            if isinstance(loaded, Mapping):
                summary = loaded
        observed_verdict = evaluate_final_observed_match(summary)
        payload = {
            "owner": payload,
            "final_official": final_verdict.to_dict(),
            "final_observed": observed_verdict.to_dict(),
        }
        passed = passed and final_verdict.passed and observed_verdict.passed
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
