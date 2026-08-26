from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import re
from typing import Iterable


PREFIX = "[LC2DAMAGE]"
FIELD_PATTERN = re.compile(r"([a-z_]+)=([^\s]+)")


@dataclass(frozen=True)
class ProbeSummary:
    probe_lines: int
    hit_events: int
    boundary_events: int
    probe_errors: int
    hp_snapshot_events: int
    hp_snapshot_complete: int
    hp_snapshot_applied_sum: float
    hp_snapshot_hp_delta_sum: float
    hp_snapshot_excess_sum: float
    hp_snapshot_depth_known: int
    hp_snapshot_root_events: int
    hp_snapshot_nested_events: int
    hp_snapshot_root_hp_delta_sum: float
    hp_snapshot_root_settlement_sum: int
    paths: dict[str, int]
    applied_sum_by_path: dict[str, float]
    unique_hit_fingerprints: int
    multi_path_fingerprints: int
    nonpositive_applied_events: int
    missing_owner_events: int

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)


def parse_probe_fields(line: str) -> dict[str, str] | None:
    if PREFIX not in line:
        return None
    return {match.group(1): match.group(2) for match in FIELD_PATTERN.finditer(line)}


def summarize_probe_lines(lines: Iterable[str]) -> ProbeSummary:
    probe_lines = 0
    hit_events = 0
    boundary_events = 0
    probe_errors = 0
    hp_snapshot_events = 0
    hp_snapshot_complete = 0
    hp_snapshot_applied_sum = 0.0
    hp_snapshot_hp_delta_sum = 0.0
    hp_snapshot_excess_sum = 0.0
    hp_snapshot_depth_known = 0
    hp_snapshot_root_events = 0
    hp_snapshot_nested_events = 0
    hp_snapshot_root_hp_delta_sum = 0.0
    hp_snapshot_root_settlement_sum = 0
    paths: Counter[str] = Counter()
    applied_sum_by_path: defaultdict[str, float] = defaultdict(float)
    fingerprints: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    nonpositive = 0
    missing_owner = 0

    for line in lines:
        fields = parse_probe_fields(line)
        if fields is None:
            continue
        probe_lines += 1
        if "probe_error" in line:
            probe_errors += 1
        kind = fields.get("kind")
        if kind == "hp_snapshot":
            hp_snapshot_events += 1
            try:
                before = float(fields.get("hp_before", "nan"))
                after = float(fields.get("hp_after", "nan"))
                applied = float(fields.get("applied", "nan"))
            except ValueError:
                continue
            if before == before and after == after and applied == applied:
                hp_snapshot_complete += 1
                hp_delta = max(0.0, before - after)
                hp_snapshot_applied_sum += applied
                hp_snapshot_hp_delta_sum += hp_delta
                hp_snapshot_excess_sum += max(0.0, applied - hp_delta)
                depth_text = fields.get("depth")
                if depth_text is not None:
                    try:
                        depth = int(depth_text)
                    except ValueError:
                        depth = -1
                    if depth >= 0:
                        hp_snapshot_depth_known += 1
                        if depth == 0:
                            hp_snapshot_root_events += 1
                            hp_snapshot_root_hp_delta_sum += hp_delta
                            hp_snapshot_root_settlement_sum += math.ceil(hp_delta)
                        else:
                            hp_snapshot_nested_events += 1
            continue
        if kind == "boundary":
            boundary_events += 1
            continue
        if kind != "hit":
            continue
        hit_events += 1
        path = fields.get("path", "missing")
        paths[path] += 1
        try:
            applied = float(fields.get("applied", "nan"))
        except ValueError:
            applied = float("nan")
        if applied == applied:
            applied_sum_by_path[path] += applied
            if applied <= 0:
                nonpositive += 1
        if fields.get("attacker_owner_entity") in {None, "null"}:
            missing_owner += 1
        fingerprint = (
            fields.get("hit_id", "null"),
            fields.get("attacker_entity", "null"),
            fields.get("defender_entity", "null"),
            fields.get("applied", "null"),
        )
        fingerprints[fingerprint].add(path)

    return ProbeSummary(
        probe_lines=probe_lines,
        hit_events=hit_events,
        boundary_events=boundary_events,
        probe_errors=probe_errors,
        hp_snapshot_events=hp_snapshot_events,
        hp_snapshot_complete=hp_snapshot_complete,
        hp_snapshot_applied_sum=round(hp_snapshot_applied_sum, 3),
        hp_snapshot_hp_delta_sum=round(hp_snapshot_hp_delta_sum, 3),
        hp_snapshot_excess_sum=round(hp_snapshot_excess_sum, 3),
        hp_snapshot_depth_known=hp_snapshot_depth_known,
        hp_snapshot_root_events=hp_snapshot_root_events,
        hp_snapshot_nested_events=hp_snapshot_nested_events,
        hp_snapshot_root_hp_delta_sum=round(hp_snapshot_root_hp_delta_sum, 3),
        hp_snapshot_root_settlement_sum=hp_snapshot_root_settlement_sum,
        paths=dict(sorted(paths.items())),
        applied_sum_by_path={
            path: round(value, 3) for path, value in sorted(applied_sum_by_path.items())
        },
        unique_hit_fingerprints=len(fingerprints),
        multi_path_fingerprints=sum(1 for seen_paths in fingerprints.values() if len(seen_paths) > 1),
        nonpositive_applied_events=nonpositive,
        missing_owner_events=missing_owner,
    )


def summarize_probe_file(path: Path) -> ProbeSummary:
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        return summarize_probe_lines(stream)
