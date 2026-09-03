from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import re
from typing import Iterable


MARKER = "[LC2CB-SETTLEMENT-CACHE]"
FIELD_RE = re.compile(r"([a-z_]+)=([^\s]+)")
VALUE_TOLERANCE = 1.0


@dataclass(frozen=True)
class ProbeSample:
    run: int
    room_epoch: int
    sample: int
    point: str
    combat: bool
    trigger_slot: int | None
    local_slot: int | None
    humans: int
    dict_available: bool
    dict_records: int
    dict_matched: int
    dict_unmatched: int
    dict_duplicate_slots: int
    dict_collisions: int
    dict_read_failures: int
    dict_invalid: int
    human_mapped: int
    human_complete: bool
    dict_slots: dict[int, tuple[float, float]]
    cache_list_available: bool
    cache_list_records: int
    cache_list_slots: dict[int, tuple[float, float]]
    active_available: bool
    active_records: int
    active_slots: dict[int, tuple[float, float]]
    stat_identity_matches: int
    stat_identity_unmatched: int
    stat_identity_collisions: int
    stat_read_failures: int


@dataclass(frozen=True)
class SettlementCacheProbeVerdict:
    passed: bool
    raw_damage_realtime: str
    rollover: str
    dict_relation: str
    rollover_relation: str
    boss_realtime: str
    pipe_e2e: str
    reasons: tuple[str, ...]
    sample_count: int
    parse_error_count: int
    best_run: int | None
    best_room_epoch: int | None
    changing_human_slots: tuple[int, ...]
    cache_crosscheck_samples: int
    relation_samples: int
    rollover_transitions: int


def _strict_int(fields: dict[str, str], name: str) -> int:
    raw = fields[name]
    if not re.fullmatch(r"-?\d+", raw):
        raise ValueError(f"invalid integer: {name}")
    return int(raw)


def _strict_bool(fields: dict[str, str], name: str) -> bool:
    raw = fields[name]
    if raw not in {"true", "false"}:
        raise ValueError(f"invalid boolean: {name}")
    return raw == "true"


def _optional_slot(fields: dict[str, str], name: str) -> int | None:
    raw = fields[name]
    if raw == "null":
        return None
    if not re.fullmatch(r"\d+", raw):
        raise ValueError(f"invalid slot: {name}")
    value = int(raw)
    if not 0 <= value <= 15:
        raise ValueError(f"out-of-range slot: {name}")
    return value


def _slot_values(raw: str) -> dict[int, tuple[float, float]]:
    if raw == "none":
        return {}
    result: dict[int, tuple[float, float]] = {}
    for entry in raw.split(","):
        parts = entry.split(":")
        if len(parts) != 3 or not re.fullmatch(r"\d+", parts[0]):
            raise ValueError("invalid slot vector")
        slot = int(parts[0])
        if not 0 <= slot <= 15 or slot in result:
            raise ValueError("invalid or duplicate slot vector")
        damage = float(parts[1])
        boss = float(parts[2])
        result[slot] = (damage, boss)
    return result


def _parse_sample(line: str) -> ProbeSample | None:
    if MARKER not in line:
        return None
    fields = dict(FIELD_RE.findall(line.split(MARKER, 1)[1]))
    if fields.get("kind") != "sample":
        return None
    required = {
        "run",
        "room_epoch",
        "sample",
        "point",
        "combat",
        "trigger_slot",
        "local_slot",
        "humans",
        "dict_available",
        "dict_records",
        "dict_matched",
        "dict_unmatched",
        "dict_duplicate_slots",
        "dict_collisions",
        "dict_read_failures",
        "dict_invalid",
        "human_mapped",
        "human_complete",
        "dict_slots",
        "cache_list_available",
        "cache_list_records",
        "cache_list_slots",
        "active_available",
        "active_records",
        "active_slots",
        "stat_identity_matches",
        "stat_identity_unmatched",
        "stat_identity_collisions",
        "stat_read_failures",
    }
    if not required.issubset(fields):
        raise ValueError("probe sample fields missing")
    return ProbeSample(
        run=_strict_int(fields, "run"),
        room_epoch=_strict_int(fields, "room_epoch"),
        sample=_strict_int(fields, "sample"),
        point=fields["point"],
        combat=_strict_bool(fields, "combat"),
        trigger_slot=_optional_slot(fields, "trigger_slot"),
        local_slot=_optional_slot(fields, "local_slot"),
        humans=_strict_int(fields, "humans"),
        dict_available=_strict_bool(fields, "dict_available"),
        dict_records=_strict_int(fields, "dict_records"),
        dict_matched=_strict_int(fields, "dict_matched"),
        dict_unmatched=_strict_int(fields, "dict_unmatched"),
        dict_duplicate_slots=_strict_int(fields, "dict_duplicate_slots"),
        dict_collisions=_strict_int(fields, "dict_collisions"),
        dict_read_failures=_strict_int(fields, "dict_read_failures"),
        dict_invalid=_strict_int(fields, "dict_invalid"),
        human_mapped=_strict_int(fields, "human_mapped"),
        human_complete=_strict_bool(fields, "human_complete"),
        dict_slots=_slot_values(fields["dict_slots"]),
        cache_list_available=_strict_bool(fields, "cache_list_available"),
        cache_list_records=_strict_int(fields, "cache_list_records"),
        cache_list_slots=_slot_values(fields["cache_list_slots"]),
        active_available=_strict_bool(fields, "active_available"),
        active_records=_strict_int(fields, "active_records"),
        active_slots=_slot_values(fields["active_slots"]),
        stat_identity_matches=_strict_int(fields, "stat_identity_matches"),
        stat_identity_unmatched=_strict_int(fields, "stat_identity_unmatched"),
        stat_identity_collisions=_strict_int(fields, "stat_identity_collisions"),
        stat_read_failures=_strict_int(fields, "stat_read_failures"),
    )


def _valid_vector(values: dict[int, tuple[float, float]]) -> bool:
    return all(
        math.isfinite(damage)
        and math.isfinite(boss)
        and damage >= 0
        and boss >= 0
        and boss <= damage
        for damage, boss in values.values()
    )


def _vectors_close(
    left: dict[int, tuple[float, float]],
    right: dict[int, tuple[float, float]],
) -> bool:
    return left.keys() == right.keys() and all(
        abs(left[slot][0] - right[slot][0]) <= VALUE_TOLERANCE
        and abs(left[slot][1] - right[slot][1]) <= VALUE_TOLERANCE
        for slot in left
    )


def _combined(sample: ProbeSample) -> dict[int, tuple[float, float]]:
    if sample.active_slots.keys() != sample.dict_slots.keys():
        return {}
    return {
        slot: (
            sample.active_slots[slot][0] + sample.dict_slots[slot][0],
            sample.active_slots[slot][1] + sample.dict_slots[slot][1],
        )
        for slot in sample.dict_slots
    }


def _vector_has_nonzero(values: dict[int, tuple[float, float]]) -> bool:
    return any(damage > VALUE_TOLERANCE or boss > VALUE_TOLERANCE for damage, boss in values.values())


def _dict_relation(sample: ProbeSample) -> str | None:
    if not sample.dict_slots or not _vector_has_nonzero(sample.dict_slots):
        return None
    matches_cache = bool(sample.cache_list_slots) and _vectors_close(
        sample.dict_slots, sample.cache_list_slots
    )
    matches_active = bool(sample.active_slots) and _vectors_close(
        sample.dict_slots, sample.active_slots
    )
    if matches_cache and matches_active:
        return "AMBIGUOUS_MATCHES_BOTH"
    if matches_cache:
        return "DELTA_MATCHES_CACHE_LIST"
    if matches_active:
        return "CUMULATIVE_MATCHES_ACTIVE"
    return "UNKNOWN_DIFFERENT"


def _mapping_valid(sample: ProbeSample, minimum_human_slots: int) -> bool:
    return (
        sample.combat
        and sample.humans >= minimum_human_slots
        and sample.dict_available
        and sample.dict_duplicate_slots == 0
        and sample.dict_collisions == 0
        and sample.dict_read_failures == 0
        and sample.dict_invalid == 0
        and sample.human_complete
        and sample.human_mapped == sample.humans
        and len(sample.dict_slots) == sample.humans
        and _valid_vector(sample.dict_slots)
        and _valid_vector(sample.cache_list_slots)
        and _valid_vector(sample.active_slots)
    )


def evaluate_settlement_cache_probe(
    lines: Iterable[str],
    *,
    minimum_human_slots: int = 2,
    minimum_changing_human_slots: int = 2,
    require_rollover_observation: bool = False,
) -> SettlementCacheProbeVerdict:
    material = list(lines)
    samples: list[ProbeSample] = []
    parse_errors = 0
    for line in material:
        try:
            sample = _parse_sample(line)
        except (KeyError, TypeError, ValueError):
            parse_errors += 1
            continue
        if sample is not None:
            samples.append(sample)
    suppressed = any(
        MARKER in line and "kind=suppressed" in line for line in material
    )

    reasons: set[str] = set()
    if not samples:
        reasons.add("probe_sample_missing")
    if parse_errors:
        reasons.add("probe_sample_parse_error")
    if suppressed:
        reasons.add("probe_sample_cap_reached")

    valid_samples = [
        sample
        for sample in samples
        if _mapping_valid(sample, minimum_human_slots)
    ]
    if samples and not valid_samples:
        reasons.add("complete_human_mapping_missing")
    if any(sample.dict_duplicate_slots for sample in samples):
        reasons.add("dict_duplicate_slot")
    if any(sample.dict_collisions for sample in samples):
        reasons.add("dict_identity_collision")
    if any(sample.dict_read_failures for sample in samples):
        reasons.add("dict_read_failure")
    if any(sample.dict_invalid for sample in samples) or any(
        not _valid_vector(vector)
        for sample in samples
        for vector in (
            sample.dict_slots,
            sample.cache_list_slots,
            sample.active_slots,
        )
    ):
        reasons.add("invalid_damage_value")

    by_room: dict[tuple[int, int], list[ProbeSample]] = {}
    for sample in valid_samples:
        by_room.setdefault((sample.run, sample.room_epoch), []).append(sample)
    for room_samples in by_room.values():
        room_samples.sort(key=lambda sample: sample.sample)

    best_key: tuple[int, int] | None = None
    best_changed: set[int] = set()
    regression = False
    crosscheck_count = 0
    relation_values: set[str] = set()
    boss_changed: set[int] = set()
    for key, room_samples in by_room.items():
        changed: set[int] = set()
        previous: ProbeSample | None = None
        for sample in room_samples:
            if sample.cache_list_slots:
                if _vectors_close(sample.dict_slots, sample.cache_list_slots):
                    crosscheck_count += 1
            relation = _dict_relation(sample)
            if relation is not None:
                relation_values.add(relation)
            if previous is not None and previous.dict_slots.keys() == sample.dict_slots.keys():
                for slot in sample.dict_slots:
                    old_damage, old_boss = previous.dict_slots[slot]
                    damage, boss = sample.dict_slots[slot]
                    if damage + VALUE_TOLERANCE < old_damage or boss + VALUE_TOLERANCE < old_boss:
                        regression = True
                    if damage > old_damage + VALUE_TOLERANCE:
                        changed.add(slot)
                    if boss > old_boss + VALUE_TOLERANCE:
                        boss_changed.add(slot)
            previous = sample
        if len(changed) > len(best_changed):
            best_key = key
            best_changed = changed

    if regression:
        reasons.add("same_room_value_regression")
    if len(best_changed) < minimum_changing_human_slots:
        reasons.add("same_room_multi_human_change_missing")

    if not relation_values:
        dict_relation = "UNAVAILABLE_OR_ZERO"
    elif len(relation_values) == 1:
        dict_relation = next(iter(relation_values))
    else:
        dict_relation = "MIXED"

    rollover_status = "NOT_RUN"
    rollover_relation = "UNAVAILABLE"
    rollover_transitions = 0
    rollover_equal = 0
    by_run: dict[int, list[int]] = {}
    for run, room_epoch in by_room:
        by_run.setdefault(run, []).append(room_epoch)
    for run, room_epochs in by_run.items():
        ordered_epochs = sorted(set(room_epochs))
        for old_epoch, new_epoch in zip(ordered_epochs, ordered_epochs[1:]):
            if new_epoch != old_epoch + 1:
                continue
            old_candidates = [
                sample
                for sample in by_room[(run, old_epoch)]
                if sample.point == "room_exit"
            ]
            new_candidates = [
                sample
                for sample in by_room[(run, new_epoch)]
                if sample.point == "room_entry"
            ]
            if not old_candidates or not new_candidates:
                continue
            old_combined = _combined(old_candidates[-1])
            new_combined = _combined(new_candidates[0])
            if not old_combined or not new_combined:
                continue
            rollover_transitions += 1
            if _vectors_close(old_combined, new_combined):
                rollover_equal += 1
    if rollover_transitions:
        rollover_status = "OBSERVED"
        if rollover_equal == rollover_transitions:
            rollover_relation = "ACTIVE_PLUS_DICT_EQUAL"
        elif rollover_equal == 0:
            rollover_relation = "ACTIVE_PLUS_DICT_DIFFERENT"
        else:
            rollover_relation = "MIXED"
    if require_rollover_observation and rollover_status != "OBSERVED":
        reasons.add("rollover_observation_required")

    raw_blockers = {
        "probe_sample_missing",
        "probe_sample_parse_error",
        "probe_sample_cap_reached",
        "complete_human_mapping_missing",
        "dict_duplicate_slot",
        "dict_identity_collision",
        "dict_read_failure",
        "invalid_damage_value",
        "same_room_value_regression",
        "same_room_multi_human_change_missing",
    }
    raw_status = "FAIL" if reasons & raw_blockers else "PASS"
    boss_status = "PASS" if len(boss_changed) >= minimum_changing_human_slots else "NOT_RUN"
    passed = raw_status == "PASS" and (
        not require_rollover_observation or rollover_status == "OBSERVED"
    )
    return SettlementCacheProbeVerdict(
        passed=passed,
        raw_damage_realtime=raw_status,
        rollover=rollover_status,
        dict_relation=dict_relation,
        rollover_relation=rollover_relation,
        boss_realtime=boss_status,
        pipe_e2e="NOT_RUN",
        reasons=tuple(sorted(reasons)),
        sample_count=len(samples),
        parse_error_count=parse_errors,
        best_run=None if best_key is None else best_key[0],
        best_room_epoch=None if best_key is None else best_key[1],
        changing_human_slots=tuple(sorted(best_changed)),
        cache_crosscheck_samples=crosscheck_count,
        relation_samples=sum(
            1 for sample in valid_samples if _dict_relation(sample) is not None
        ),
        rollover_transitions=rollover_transitions,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check LC2 same-room SettlementDataMgr cache diagnostics."
    )
    parser.add_argument("log", type=Path)
    parser.add_argument("--minimum-human-slots", type=int, default=2)
    parser.add_argument("--minimum-changing-human-slots", type=int, default=2)
    parser.add_argument("--require-rollover-observation", action="store_true")
    args = parser.parse_args()
    lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    verdict = evaluate_settlement_cache_probe(
        lines,
        minimum_human_slots=args.minimum_human_slots,
        minimum_changing_human_slots=args.minimum_changing_human_slots,
        require_rollover_observation=args.require_rollover_observation,
    )
    print(json.dumps(asdict(verdict), ensure_ascii=False, indent=2))
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
