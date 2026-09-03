from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

try:
    from tools.check_lc2_settlement_cache_probe import (
        MARKER,
        ProbeSample,
        _parse_sample,
        _valid_vector,
    )
except ModuleNotFoundError:
    from check_lc2_settlement_cache_probe import (  # type: ignore[no-redef]
        MARKER,
        ProbeSample,
        _parse_sample,
        _valid_vector,
    )


EXACT_TOLERANCE = 0.001


@dataclass(frozen=True)
class StatisticsCacheProbeVerdict:
    passed: bool
    raw_damage_realtime: str
    rollover: str
    boss_realtime: str
    pipe_e2e: str
    reasons: tuple[str, ...]
    sample_count: int
    valid_sample_count: int
    parse_error_count: int
    run: int | None
    local_slot: int | None
    combat_room_count: int
    changing_human_slots: tuple[int, ...]
    remote_only_rooms: tuple[int, ...]
    local_damage_rooms: tuple[int, ...]
    rollover_transitions: int
    exact_rollover_transitions: int


def _vectors_close_exact(
    left: dict[int, tuple[float, float]],
    right: dict[int, tuple[float, float]],
) -> bool:
    return left.keys() == right.keys() and all(
        abs(left[slot][0] - right[slot][0]) <= EXACT_TOLERANCE
        and abs(left[slot][1] - right[slot][1]) <= EXACT_TOLERANCE
        for slot in left
    )


def _statistics_mapping_valid(
    sample: ProbeSample,
    minimum_human_slots: int,
) -> bool:
    expected_matches = sample.humans * 2
    return (
        sample.humans >= minimum_human_slots
        and sample.local_slot is not None
        and sample.cache_list_available
        and sample.active_available
        and sample.cache_list_records >= sample.humans
        and sample.active_records >= sample.humans
        and sample.stat_identity_matches >= expected_matches
        and sample.stat_identity_collisions == 0
        and sample.stat_read_failures == 0
        and len(sample.cache_list_slots) == sample.humans
        and len(sample.active_slots) == sample.humans
        and sample.cache_list_slots.keys() == sample.active_slots.keys()
        and sample.local_slot in sample.cache_list_slots
        and _valid_vector(sample.cache_list_slots)
        and _valid_vector(sample.active_slots)
    )


def _combined(sample: ProbeSample) -> dict[int, tuple[float, float]]:
    if sample.active_slots.keys() != sample.cache_list_slots.keys():
        return {}
    return {
        slot: (
            sample.active_slots[slot][0] + sample.cache_list_slots[slot][0],
            sample.active_slots[slot][1] + sample.cache_list_slots[slot][1],
        )
        for slot in sample.active_slots
    }


def _is_zero(values: dict[int, tuple[float, float]]) -> bool:
    return all(damage == 0 and boss == 0 for damage, boss in values.values())


def evaluate_statistics_cache_probe(
    lines: Iterable[str],
    *,
    minimum_human_slots: int = 2,
    minimum_changing_human_slots: int = 2,
    require_remote_only_room: bool = True,
    require_local_damage_room: bool = True,
    require_rollover: bool = True,
) -> StatisticsCacheProbeVerdict:
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
        reasons.add("ordinary_sample_cap_reached")
    if any(sample.stat_identity_collisions for sample in samples):
        reasons.add("statistics_identity_collision")
    if any(sample.stat_read_failures for sample in samples):
        reasons.add("statistics_read_failure")
    if any(
        not _valid_vector(vector)
        for sample in samples
        for vector in (sample.cache_list_slots, sample.active_slots)
    ):
        reasons.add("invalid_statistics_damage_value")

    valid_samples = [
        sample
        for sample in samples
        if _statistics_mapping_valid(sample, minimum_human_slots)
    ]
    if samples and not valid_samples:
        reasons.add("statistics_complete_human_mapping_missing")

    run_values = {sample.run for sample in valid_samples}
    local_slots = {sample.local_slot for sample in valid_samples}
    if len(run_values) > 1:
        reasons.add("multiple_probe_runs")
    if len(local_slots) > 1:
        reasons.add("local_slot_changed_during_probe")
    run = next(iter(run_values)) if len(run_values) == 1 else None
    local_slot = next(iter(local_slots)) if len(local_slots) == 1 else None

    by_room: dict[tuple[int, int], list[ProbeSample]] = {}
    for sample in valid_samples:
        by_room.setdefault((sample.run, sample.room_epoch), []).append(sample)
    for room_samples in by_room.values():
        room_samples.sort(key=lambda sample: sample.sample)

    changing_slots: set[int] = set()
    boss_changing_slots: set[int] = set()
    remote_only_rooms: set[int] = set()
    local_damage_rooms: set[int] = set()
    combat_room_count = 0
    combined_regression = False
    for (_run, room_epoch), room_samples in by_room.items():
        if any(sample.combat for sample in room_samples):
            combat_room_count += 1
        room_changed: set[int] = set()
        previous_combined: dict[int, tuple[float, float]] | None = None
        realtime_samples = [
            sample
            for sample in room_samples
            if sample.point in {"room_entry", "attacker_post"}
        ]
        for sample in realtime_samples:
            combined = _combined(sample)
            if previous_combined is not None and previous_combined.keys() == combined.keys():
                for slot in combined:
                    old_damage, old_boss = previous_combined[slot]
                    damage, boss = combined[slot]
                    if (
                        damage + EXACT_TOLERANCE < old_damage
                        or boss + EXACT_TOLERANCE < old_boss
                    ):
                        combined_regression = True
                    if damage > old_damage + EXACT_TOLERANCE:
                        room_changed.add(slot)
                        changing_slots.add(slot)
                    if boss > old_boss + EXACT_TOLERANCE:
                        boss_changing_slots.add(slot)
            previous_combined = combined

        if local_slot is not None:
            remote_changes = room_changed - {local_slot}
            if remote_changes and local_slot not in room_changed:
                remote_only_rooms.add(room_epoch)
            if local_slot in room_changed:
                local_damage_rooms.add(room_epoch)

    if combined_regression:
        reasons.add("same_room_combined_regression")
    by_run_entries: dict[int, list[ProbeSample]] = {}
    for sample in valid_samples:
        if sample.point == "room_entry":
            by_run_entries.setdefault(sample.run, []).append(sample)
    if any(
        entries
        and not _is_zero(_combined(min(entries, key=lambda item: item.sample)))
        for entries in by_run_entries.values()
    ):
        reasons.add("initial_room_entry_combined_not_zero")
    if len(changing_slots) < minimum_changing_human_slots:
        reasons.add("same_room_multi_human_change_missing")
    if require_remote_only_room and not remote_only_rooms:
        reasons.add("remote_only_room_missing")
    if require_local_damage_room and not local_damage_rooms:
        reasons.add("local_damage_room_missing")

    rollover_transitions = 0
    exact_rollovers = 0
    by_run: dict[int, list[int]] = {}
    for sample_run, room_epoch in by_room:
        by_run.setdefault(sample_run, []).append(room_epoch)
    for sample_run, room_epochs in by_run.items():
        ordered_epochs = sorted(set(room_epochs))
        for old_epoch, new_epoch in zip(ordered_epochs, ordered_epochs[1:]):
            if new_epoch != old_epoch + 1:
                continue
            old_samples = by_room[(sample_run, old_epoch)]
            new_samples = by_room[(sample_run, new_epoch)]
            old_boundaries = [
                sample for sample in old_samples if sample.point == "room_exit"
            ]
            new_boundaries = [
                sample for sample in new_samples if sample.point == "room_entry"
            ]
            if not old_boundaries or not new_boundaries:
                continue
            old_sample = old_boundaries[-1]
            old_combined = _combined(old_sample)
            new_combined = _combined(new_boundaries[0])
            if not old_combined or not new_combined:
                continue
            rollover_transitions += 1
            if _vectors_close_exact(old_combined, new_combined):
                exact_rollovers += 1
    if rollover_transitions == 0:
        rollover_status = "NOT_RUN"
    elif exact_rollovers == rollover_transitions:
        rollover_status = "PASS"
    else:
        rollover_status = "FAIL"
        reasons.add("active_plus_cache_rollover_mismatch")
    if require_rollover and rollover_status != "PASS":
        reasons.add("rollover_pass_required")

    raw_blockers = {
        "probe_sample_missing",
        "probe_sample_parse_error",
        "ordinary_sample_cap_reached",
        "statistics_identity_collision",
        "statistics_read_failure",
        "invalid_statistics_damage_value",
        "statistics_complete_human_mapping_missing",
        "multiple_probe_runs",
        "local_slot_changed_during_probe",
        "same_room_combined_regression",
        "initial_room_entry_combined_not_zero",
        "same_room_multi_human_change_missing",
        "remote_only_room_missing",
        "local_damage_room_missing",
    }
    raw_status = "FAIL" if reasons & raw_blockers else "PASS"
    boss_status = (
        "PASS"
        if len(boss_changing_slots) >= minimum_changing_human_slots
        else "NOT_RUN"
    )
    passed = raw_status == "PASS" and (
        not require_rollover or rollover_status == "PASS"
    )
    return StatisticsCacheProbeVerdict(
        passed=passed,
        raw_damage_realtime=raw_status,
        rollover=rollover_status,
        boss_realtime=boss_status,
        pipe_e2e="NOT_RUN",
        reasons=tuple(sorted(reasons)),
        sample_count=len(samples),
        valid_sample_count=len(valid_samples),
        parse_error_count=parse_errors,
        run=run,
        local_slot=local_slot,
        combat_room_count=combat_room_count,
        changing_human_slots=tuple(sorted(changing_slots)),
        remote_only_rooms=tuple(sorted(remote_only_rooms)),
        local_damage_rooms=tuple(sorted(local_damage_rooms)),
        rollover_transitions=rollover_transitions,
        exact_rollover_transitions=exact_rollovers,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check LC2 Statistics cache-list in-room realtime semantics."
    )
    parser.add_argument("log", type=Path)
    parser.add_argument("--minimum-human-slots", type=int, default=2)
    parser.add_argument("--minimum-changing-human-slots", type=int, default=2)
    parser.add_argument("--allow-no-remote-only-room", action="store_true")
    parser.add_argument("--allow-no-local-damage-room", action="store_true")
    parser.add_argument("--allow-no-rollover", action="store_true")
    args = parser.parse_args()
    verdict = evaluate_statistics_cache_probe(
        args.log.read_text(encoding="utf-8", errors="replace").splitlines(),
        minimum_human_slots=args.minimum_human_slots,
        minimum_changing_human_slots=args.minimum_changing_human_slots,
        require_remote_only_room=not args.allow_no_remote_only_room,
        require_local_damage_room=not args.allow_no_local_damage_room,
        require_rollover=not args.allow_no_rollover,
    )
    print(json.dumps(asdict(verdict), ensure_ascii=False, indent=2))
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
