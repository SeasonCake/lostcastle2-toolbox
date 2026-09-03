from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from typing import Iterable, Sequence


PROBE_MARKER = "[LC2CB-SETTLEMENT-FINAL-PROBE]"
OFFICIAL_MARKER = "[LC2CB-OFFICIAL]"
EXPECTED_TARGETS = (
    "SyncSettlementData_ClientResult",
    "SyncSettlementData2_Rpc",
    "SyncSettlementData",
)
SURFACE_NAMES = ("active", "cache", "save", "network")
MAX_NETWORK_SAMPLES = 128
MAX_RECORDS_PER_SURFACE = 32

TOP_LEVEL_FIELD_RE = re.compile(r"(?:^|\s)([a-z_]+)=([^\s]+)")
IDENTITY_RE = re.compile(
    r"(?:player-[1-9]\d*|slot-(?:[0-9]|1[0-5])|"
    r"opaque-[0-9a-fA-F]{1,16}|missing|collision|null|read-failure)"
)
NUMBER_RE = re.compile(
    r"(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?"
)
OFFICIAL_SLOT_RE = re.compile(
    r"(?:^|\s)slot=(?P<slot>\d+):"
    r"damage=(?P<damage>\d+|null):boss=(?P<boss>\d+|null)"
)


@dataclass(frozen=True)
class VectorRecord:
    identity: str
    damage: Decimal | None
    boss: Decimal | None


@dataclass(frozen=True)
class SurfaceSnapshot:
    available: bool
    records: int
    read_failures: int
    truncated: bool
    vector_token: str
    values: tuple[VectorRecord, ...]


@dataclass(frozen=True)
class HookClassification:
    line_index: int
    target: str
    installed: bool
    fail_open: bool


@dataclass(frozen=True)
class NetworkRecord:
    line_index: int
    seq: int
    surface: str
    identity: str
    damage: Decimal | None
    boss: Decimal | None
    read_failure: bool
    network_samples: int
    duplicate_calls: int
    suppressed_calls: int


@dataclass(frozen=True)
class SuppressedRecord:
    line_index: int
    seq: int
    maximum: int
    boundaries_preserved: bool


@dataclass(frozen=True)
class Boundary:
    line_index: int
    seq: int
    phase: str
    run: int
    room_epoch: int
    surfaces: dict[str, SurfaceSnapshot]
    network_samples: int
    duplicate_calls: int
    suppressed_calls: int


@dataclass(frozen=True)
class OfficialSummary:
    line_index: int
    members: int
    final_ready: bool
    final_accepted: bool
    final_records: int
    expected_slots: int
    published_slots: int
    identity_matches: int
    identity_unmatched: int
    identity_collisions: int
    invalid_slots: int
    duplicate_slots: int
    slot_basis: str
    slots: dict[int, tuple[Decimal, Decimal]]


@dataclass(frozen=True)
class SettlementFinalProbeVerdict:
    status: str
    passed: bool
    hooks: str
    sequence: str
    payloads: str
    sync_end: str
    official_match: str
    reasons: tuple[str, ...]
    parse_error_count: int
    hook_log_count: int
    installed_targets: tuple[str, ...]
    fail_open_targets: tuple[str, ...]
    sequenced_event_count: int
    network_record_count: int
    suppressed_log_count: int
    boundary_count: int
    complete_sync_end_count: int
    final_run: int | None
    final_room_epoch: int | None
    official_summary_count_after_postfix: int
    official_slot_count: int
    mapped_slot_count: int
    mismatch_slots: tuple[int, ...]


class ProbeParseError(ValueError):
    pass


def _fields(line: str, marker: str) -> dict[str, str]:
    suffix = line.split(marker, 1)[1]
    result: dict[str, str] = {}
    for match in TOP_LEVEL_FIELD_RE.finditer(suffix):
        key, value = match.groups()
        if key in result:
            raise ProbeParseError(f"duplicate field: {key}")
        result[key] = value
    return result


def _official_fields(line: str) -> dict[str, str]:
    suffix = line.split(OFFICIAL_MARKER, 1)[1]
    result: dict[str, str] = {}
    for match in TOP_LEVEL_FIELD_RE.finditer(suffix):
        key, value = match.groups()
        if key == "slot":
            continue
        if key in result:
            raise ProbeParseError(f"duplicate field: {key}")
        result[key] = value
    return result


def _required(fields: dict[str, str], names: Sequence[str]) -> None:
    missing = [name for name in names if name not in fields]
    if missing:
        raise ProbeParseError("missing fields: " + ",".join(missing))


def _integer(fields: dict[str, str], name: str, *, minimum: int = 0) -> int:
    raw = fields[name]
    if not re.fullmatch(r"-?\d+", raw):
        raise ProbeParseError(f"invalid integer: {name}")
    value = int(raw)
    if value < minimum:
        raise ProbeParseError(f"out-of-range integer: {name}")
    return value


def _boolean(fields: dict[str, str], name: str) -> bool:
    raw = fields[name]
    if raw not in {"true", "false"}:
        raise ProbeParseError(f"invalid boolean: {name}")
    return raw == "true"


def _number(raw: str) -> Decimal:
    if not NUMBER_RE.fullmatch(raw):
        raise ProbeParseError("invalid damage number")
    try:
        value = Decimal(raw)
    except InvalidOperation as exception:
        raise ProbeParseError("invalid damage number") from exception
    if not value.is_finite() or value < 0:
        raise ProbeParseError("invalid damage number")
    return value


def _identity(raw: str) -> str:
    if not IDENTITY_RE.fullmatch(raw):
        raise ProbeParseError("invalid anonymous identity")
    return raw.lower() if raw.startswith("opaque-") else raw


def _vector(raw: str) -> tuple[VectorRecord, ...]:
    if raw in {"none", "empty", "unavailable"}:
        return ()
    values: list[VectorRecord] = []
    for item in raw.split(","):
        if item in {"null", "read-failure"}:
            values.append(VectorRecord(item, None, None))
            continue
        parts = item.split(":")
        if len(parts) != 3:
            raise ProbeParseError("invalid surface vector")
        identity = _identity(parts[0])
        damage = _number(parts[1])
        boss = _number(parts[2])
        if boss > damage:
            raise ProbeParseError("boss damage exceeds damage")
        values.append(VectorRecord(identity, damage, boss))
    return tuple(values)


def _surface(fields: dict[str, str], name: str) -> SurfaceSnapshot:
    required = (
        f"{name}_available",
        f"{name}_records",
        f"{name}_read_failures",
        f"{name}_truncated",
        name,
    )
    _required(fields, required)
    vector_token = fields[name]
    return SurfaceSnapshot(
        available=_boolean(fields, f"{name}_available"),
        records=_integer(fields, f"{name}_records"),
        read_failures=_integer(fields, f"{name}_read_failures"),
        truncated=_boolean(fields, f"{name}_truncated"),
        vector_token=vector_token,
        values=_vector(vector_token),
    )


def _parse_hook(line: str, line_index: int) -> HookClassification:
    fields = _fields(line, PROBE_MARKER)
    _required(fields, ("target", "installed", "fail_open"))
    return HookClassification(
        line_index=line_index,
        target=fields["target"],
        installed=_boolean(fields, "installed"),
        fail_open=_boolean(fields, "fail_open"),
    )


def _parse_network_record(line: str, line_index: int) -> NetworkRecord:
    fields = _fields(line, PROBE_MARKER)
    _required(
        fields,
        (
            "seq",
            "phase",
            "surface",
            "identity",
            "damage",
            "boss",
            "read_failure",
            "network_samples",
            "duplicate_calls",
            "suppressed_calls",
        ),
    )
    if fields["phase"] != "prefix":
        raise ProbeParseError("network record phase must be prefix")
    identity = _identity(fields["identity"])
    read_failure = _boolean(fields, "read_failure")
    if fields["damage"] in {"null", "read-failure"}:
        damage = None
    else:
        damage = _number(fields["damage"])
    if fields["boss"] in {"null", "read-failure"}:
        boss = None
    else:
        boss = _number(fields["boss"])
    if (damage is None) != (boss is None):
        raise ProbeParseError("partial network damage vector")
    if damage is not None and boss is not None and boss > damage:
        raise ProbeParseError("network boss damage exceeds damage")
    return NetworkRecord(
        line_index=line_index,
        seq=_integer(fields, "seq", minimum=1),
        surface=fields["surface"],
        identity=identity,
        damage=damage,
        boss=boss,
        read_failure=read_failure,
        network_samples=_integer(fields, "network_samples"),
        duplicate_calls=_integer(fields, "duplicate_calls"),
        suppressed_calls=_integer(fields, "suppressed_calls"),
    )


def _parse_suppressed(line: str, line_index: int) -> SuppressedRecord:
    fields = _fields(line, PROBE_MARKER)
    _required(
        fields,
        ("seq", "max_network_samples", "sync_end_boundaries_preserved"),
    )
    return SuppressedRecord(
        line_index=line_index,
        seq=_integer(fields, "seq", minimum=1),
        maximum=_integer(fields, "max_network_samples"),
        boundaries_preserved=_boolean(fields, "sync_end_boundaries_preserved"),
    )


def _parse_boundary(line: str, line_index: int) -> Boundary:
    fields = _fields(line, PROBE_MARKER)
    _required(
        fields,
        (
            "seq",
            "phase",
            "run",
            "room_epoch",
            "network_samples",
            "duplicate_calls",
            "suppressed_calls",
        ),
    )
    if fields["phase"] not in {"prefix", "postfix"}:
        raise ProbeParseError("invalid boundary phase")
    return Boundary(
        line_index=line_index,
        seq=_integer(fields, "seq", minimum=1),
        phase=fields["phase"],
        run=_integer(fields, "run", minimum=1),
        room_epoch=_integer(fields, "room_epoch", minimum=1),
        surfaces={name: _surface(fields, name) for name in SURFACE_NAMES},
        network_samples=_integer(fields, "network_samples"),
        duplicate_calls=_integer(fields, "duplicate_calls"),
        suppressed_calls=_integer(fields, "suppressed_calls"),
    )


def _parse_official_summary(line: str, line_index: int) -> OfficialSummary:
    fields = _official_fields(line)
    _required(
        fields,
        (
            "members",
            "final_ready",
            "final_accepted",
            "final_records",
            "final_expected_slots",
            "final_published_slots",
            "final_identity_matches",
            "final_identity_unmatched",
            "final_identity_collisions",
            "final_invalid_slots",
            "final_duplicate_slots",
            "slot_basis",
        ),
    )
    slots: dict[int, tuple[Decimal, Decimal]] = {}
    for match in OFFICIAL_SLOT_RE.finditer(line):
        slot = int(match.group("slot"))
        raw_damage = match.group("damage")
        raw_boss = match.group("boss")
        if slot in slots:
            raise ProbeParseError("duplicate official slot")
        if raw_damage == "null" or raw_boss == "null":
            continue
        damage = _number(raw_damage)
        boss = _number(raw_boss)
        if boss > damage:
            raise ProbeParseError("official boss damage exceeds damage")
        slots[slot] = (damage, boss)
    return OfficialSummary(
        line_index=line_index,
        members=_integer(fields, "members"),
        final_ready=_boolean(fields, "final_ready"),
        final_accepted=_boolean(fields, "final_accepted"),
        final_records=_integer(fields, "final_records"),
        expected_slots=_integer(fields, "final_expected_slots"),
        published_slots=_integer(fields, "final_published_slots"),
        identity_matches=_integer(fields, "final_identity_matches"),
        identity_unmatched=_integer(fields, "final_identity_unmatched"),
        identity_collisions=_integer(fields, "final_identity_collisions"),
        invalid_slots=_integer(fields, "final_invalid_slots"),
        duplicate_slots=_integer(fields, "final_duplicate_slots"),
        slot_basis=fields["slot_basis"],
        slots=slots,
    )


def _surface_reasons(
    boundary: Boundary,
    name: str,
    surface: SurfaceSnapshot,
) -> set[str]:
    prefix = f"{boundary.phase}_{name}"
    reasons: set[str] = set()
    if surface.records > MAX_RECORDS_PER_SURFACE:
        reasons.add(f"{prefix}_record_limit_exceeded")
    if surface.truncated:
        reasons.add(f"{prefix}_truncated")
    if surface.read_failures > 0:
        reasons.add(f"{prefix}_read_failure")
    if surface.available:
        if surface.records == 0:
            if surface.vector_token != "empty":
                reasons.add(f"{prefix}_empty_vector_invalid")
        elif surface.vector_token in {"none", "empty", "unavailable"}:
            reasons.add(f"{prefix}_vector_missing")
        elif len(surface.values) != surface.records:
            reasons.add(f"{prefix}_record_count_mismatch")
    else:
        if surface.records != 0:
            reasons.add(f"{prefix}_unavailable_record_count")
        if surface.vector_token not in {"none", "unavailable"}:
            reasons.add(f"{prefix}_unavailable_vector_invalid")
    read_failure_entries = sum(
        value.identity == "read-failure" for value in surface.values
    )
    if read_failure_entries > surface.read_failures:
        reasons.add(f"{prefix}_read_failure_count_mismatch")
    seen_identities: set[str] = set()
    for value in surface.values:
        if value.identity == "collision":
            reasons.add(f"{prefix}_identity_collision")
        if value.identity == "read-failure":
            reasons.add(f"{prefix}_read_failure")
        if value.identity == "null":
            reasons.add(f"{prefix}_null_record")
        if value.damage is None or value.boss is None:
            if value.identity not in {"read-failure", "null"}:
                reasons.add(f"{prefix}_damage_missing")
            continue
        if value.boss > value.damage:
            reasons.add(f"{prefix}_boss_exceeds_damage")
        if value.identity not in {"missing", "null", "read-failure"}:
            if value.identity in seen_identities:
                reasons.add(f"{prefix}_duplicate_identity")
            seen_identities.add(value.identity)
    return reasons


def _official_reasons(summary: OfficialSummary) -> set[str]:
    reasons: set[str] = set()
    if not summary.final_ready:
        reasons.add("final_official_not_ready")
    if not summary.final_accepted:
        reasons.add("final_official_not_accepted")
    if summary.expected_slots <= 0:
        reasons.add("final_official_expected_slots_missing")
    if summary.members != summary.expected_slots:
        reasons.add("final_official_member_count_mismatch")
    if summary.final_records != summary.expected_slots:
        reasons.add("final_official_record_count_mismatch")
    if summary.published_slots != summary.expected_slots:
        reasons.add("final_official_publish_incomplete")
    if summary.identity_matches != summary.expected_slots:
        reasons.add("final_official_identity_match_incomplete")
    if summary.identity_unmatched > 0:
        reasons.add("final_official_identity_unmatched")
    if summary.identity_collisions > 0:
        reasons.add("final_official_identity_collision")
    if summary.invalid_slots > 0:
        reasons.add("final_official_invalid_slot")
    if summary.duplicate_slots > 0:
        reasons.add("final_official_duplicate_slot")
    if summary.slot_basis != "platform_identity_hmac":
        reasons.add("final_official_identity_basis_invalid")
    if len(summary.slots) != summary.expected_slots:
        reasons.add("final_official_slot_values_incomplete")
    return reasons


def _overall_status(statuses: Sequence[str]) -> str:
    if "FAIL" in statuses:
        return "FAIL"
    if statuses and all(status == "PASS" for status in statuses):
        return "PASS"
    return "NOT_RUN"


def evaluate_settlement_final_probe(
    lines: Iterable[str],
) -> SettlementFinalProbeVerdict:
    materialized = list(lines)
    marker_seen = False
    hooks: list[HookClassification] = []
    records: list[NetworkRecord] = []
    suppressed: list[SuppressedRecord] = []
    boundaries: list[Boundary] = []
    parse_errors = 0
    reasons: set[str] = set()

    for line_index, line in enumerate(materialized):
        if PROBE_MARKER not in line:
            continue
        marker_seen = True
        try:
            fields = _fields(line, PROBE_MARKER)
            kind = fields.get("kind")
            if kind == "hook":
                hooks.append(_parse_hook(line, line_index))
            elif kind == "record":
                records.append(_parse_network_record(line, line_index))
            elif kind == "suppressed":
                suppressed.append(_parse_suppressed(line, line_index))
            elif kind == "boundary":
                boundaries.append(_parse_boundary(line, line_index))
            else:
                raise ProbeParseError("unknown probe kind")
        except ProbeParseError:
            parse_errors += 1
            reasons.add("probe_line_parse_error")

    installed_targets: set[str] = set()
    fail_open_targets: set[str] = set()
    hook_by_target: dict[str, set[tuple[bool, bool]]] = {}
    for hook in hooks:
        if hook.target not in EXPECTED_TARGETS:
            reasons.add("hook_target_unknown")
            continue
        hook_by_target.setdefault(hook.target, set()).add(
            (hook.installed, hook.fail_open)
        )
        if hook.installed:
            installed_targets.add(hook.target)
        else:
            fail_open_targets.add(hook.target)
        if not hook.fail_open:
            reasons.add("hook_not_fail_open")
    if not hooks:
        hook_status = "NOT_RUN" if not marker_seen else "FAIL"
        if marker_seen:
            reasons.add("hook_classification_missing")
    else:
        missing_targets = set(EXPECTED_TARGETS) - set(hook_by_target)
        if missing_targets:
            reasons.add("hook_target_classification_incomplete")
        if any(len(classifications) > 1 for classifications in hook_by_target.values()):
            reasons.add("hook_target_conflicting_classification")
        hook_failures = {
            "hook_target_unknown",
            "hook_not_fail_open",
            "hook_target_classification_incomplete",
            "hook_target_conflicting_classification",
        }
        hook_status = "FAIL" if reasons & hook_failures else "PASS"

    sequenced: list[tuple[int, int, str]] = [
        (record.line_index, record.seq, "record") for record in records
    ]
    sequenced.extend(
        (item.line_index, item.seq, "suppressed") for item in suppressed
    )
    sequenced.extend(
        (boundary.line_index, boundary.seq, "boundary")
        for boundary in boundaries
    )
    sequenced.sort()
    if not sequenced:
        sequence_status = "NOT_RUN"
    elif any(
        current[1] <= previous[1]
        for previous, current in zip(sequenced, sequenced[1:])
    ):
        reasons.add("probe_sequence_not_strictly_increasing")
        sequence_status = "FAIL"
    else:
        sequence_status = "PASS"

    payload_reasons: set[str] = set()
    previous_network_samples = -1
    previous_duplicate_calls = -1
    previous_suppressed_calls = -1
    counter_events: list[tuple[int, int, int, int]] = []
    for record in records:
        if record.surface not in EXPECTED_TARGETS:
            payload_reasons.add("network_record_surface_unknown")
        if not 1 <= record.network_samples <= MAX_NETWORK_SAMPLES:
            payload_reasons.add("network_sample_limit_invalid")
        if record.read_failure or record.identity == "read-failure":
            payload_reasons.add("network_record_read_failure")
        if record.identity == "collision":
            payload_reasons.add("network_record_identity_collision")
        if record.identity == "null":
            payload_reasons.add("network_record_null")
        if record.damage is None or record.boss is None:
            payload_reasons.add("network_record_damage_missing")
        elif record.boss > record.damage:
            payload_reasons.add("network_record_boss_exceeds_damage")
        counter_events.append(
            (
                record.line_index,
                record.network_samples,
                record.duplicate_calls,
                record.suppressed_calls,
            )
        )
    for item in suppressed:
        if item.maximum != MAX_NETWORK_SAMPLES:
            payload_reasons.add("suppression_limit_invalid")
        if not item.boundaries_preserved:
            payload_reasons.add("suppression_boundary_preservation_missing")
    for boundary in boundaries:
        if boundary.network_samples > MAX_NETWORK_SAMPLES:
            payload_reasons.add("network_sample_limit_exceeded")
        for name, surface in boundary.surfaces.items():
            payload_reasons.update(_surface_reasons(boundary, name, surface))
        counter_events.append(
            (
                boundary.line_index,
                boundary.network_samples,
                boundary.duplicate_calls,
                boundary.suppressed_calls,
            )
        )
    for _, network_samples, duplicate_calls, suppressed_calls in sorted(counter_events):
        if network_samples < previous_network_samples:
            payload_reasons.add("network_sample_counter_regressed")
        if duplicate_calls < previous_duplicate_calls:
            payload_reasons.add("duplicate_call_counter_regressed")
        if suppressed_calls < previous_suppressed_calls:
            payload_reasons.add("suppressed_call_counter_regressed")
        previous_network_samples = network_samples
        previous_duplicate_calls = duplicate_calls
        previous_suppressed_calls = suppressed_calls
    reasons.update(payload_reasons)
    if not sequenced:
        payload_status = "NOT_RUN"
    elif payload_reasons or parse_errors:
        payload_status = "FAIL"
    else:
        payload_status = "PASS"

    complete_pairs: list[tuple[Boundary, Boundary]] = []
    open_prefix: Boundary | None = None
    pair_failures: set[str] = set()
    unpaired_count = 0
    for boundary in sorted(boundaries, key=lambda item: item.line_index):
        if boundary.phase == "prefix":
            if open_prefix is not None:
                unpaired_count += 1
            open_prefix = boundary
            continue
        if open_prefix is None:
            unpaired_count += 1
            continue
        if (
            boundary.run != open_prefix.run
            or boundary.room_epoch != open_prefix.room_epoch
        ):
            pair_failures.add("sync_end_boundary_identity_mismatch")
            open_prefix = None
            continue
        complete_pairs.append((open_prefix, boundary))
        open_prefix = None
    if open_prefix is not None:
        unpaired_count += 1
    boundary_phases = {boundary.phase for boundary in boundaries}
    if not complete_pairs and boundary_phases == {"prefix", "postfix"}:
        pair_failures.add("sync_end_boundary_order_invalid")
    if complete_pairs and unpaired_count:
        pair_failures.add("sync_end_boundary_unpaired")
    reasons.update(pair_failures)
    if pair_failures or (complete_pairs and payload_status == "FAIL"):
        sync_end_status = "FAIL"
    elif complete_pairs:
        sync_end_status = "PASS"
    else:
        sync_end_status = "NOT_RUN"
        reasons.add("complete_sync_end_missing")

    official_status = "NOT_RUN"
    official_after_count = 0
    official_slot_count = 0
    mapped_slot_count = 0
    mismatch_slots: tuple[int, ...] = ()
    final_run: int | None = None
    final_room_epoch: int | None = None
    if complete_pairs:
        _, final_postfix = complete_pairs[-1]
        final_run = final_postfix.run
        final_room_epoch = final_postfix.room_epoch
        candidates = [
            (index, line)
            for index, line in enumerate(materialized)
            if index > final_postfix.line_index
            and OFFICIAL_MARKER in line
            and "kind=summary" in line
        ]
        official_after_count = len(candidates)
        if not candidates:
            reasons.add("final_official_summary_after_postfix_missing")
        else:
            try:
                summary_index, summary_line = candidates[0]
                summary = _parse_official_summary(summary_line, summary_index)
            except ProbeParseError:
                parse_errors += 1
                reasons.add("final_official_summary_parse_error")
                official_status = "FAIL"
            else:
                official_slot_count = len(summary.slots)
                official_failures = _official_reasons(summary)
                if official_failures:
                    reasons.update(official_failures)
                    official_status = "FAIL"
                else:
                    save = final_postfix.surfaces["save"]
                    mapped: dict[int, tuple[Decimal, Decimal]] = {}
                    mapping_incomplete = False
                    mapping_invalid = False
                    if not save.available or save.records == 0:
                        reasons.add("postfix_save_unavailable")
                        mapping_incomplete = True
                    for value in save.values:
                        match = re.fullmatch(r"slot-(\d+)", value.identity)
                        if match is None:
                            mapping_incomplete = True
                            continue
                        slot = int(match.group(1))
                        if value.damage is None or value.boss is None or slot in mapped:
                            mapping_invalid = True
                            continue
                        mapped[slot] = (value.damage, value.boss)
                    mapped_slot_count = len(mapped)
                    if not set(mapped).issubset(summary.slots):
                        mapping_invalid = True
                    known_mismatches = tuple(
                        slot
                        for slot in sorted(set(mapped) & set(summary.slots))
                        if mapped[slot] != summary.slots[slot]
                    )
                    mismatch_slots = known_mismatches
                    if known_mismatches:
                        reasons.add("postfix_official_slot_value_mismatch")
                        official_status = "FAIL"
                    elif mapping_invalid:
                        reasons.add("postfix_save_slot_mapping_invalid")
                        official_status = "FAIL"
                    elif mapping_incomplete or set(mapped) != set(summary.slots):
                        reasons.add("postfix_save_slot_mapping_not_available")
                        official_status = "NOT_RUN"
                    else:
                        official_status = "PASS"

    if parse_errors:
        payload_status = "FAIL"
    statuses = (
        hook_status,
        sequence_status,
        payload_status,
        sync_end_status,
        official_status,
    )
    status = _overall_status(statuses)
    if not marker_seen:
        reasons.add("settlement_final_probe_missing")
        status = "NOT_RUN"
    elif parse_errors:
        status = "FAIL"
    return SettlementFinalProbeVerdict(
        status=status,
        passed=status == "PASS",
        hooks=hook_status,
        sequence=sequence_status,
        payloads=payload_status,
        sync_end=sync_end_status,
        official_match=official_status,
        reasons=tuple(sorted(reasons)),
        parse_error_count=parse_errors,
        hook_log_count=len(hooks),
        installed_targets=tuple(
            target for target in EXPECTED_TARGETS if target in installed_targets
        ),
        fail_open_targets=tuple(
            target for target in EXPECTED_TARGETS if target in fail_open_targets
        ),
        sequenced_event_count=len(sequenced),
        network_record_count=len(records),
        suppressed_log_count=len(suppressed),
        boundary_count=len(boundaries),
        complete_sync_end_count=len(complete_pairs),
        final_run=final_run,
        final_room_epoch=final_room_epoch,
        official_summary_count_after_postfix=official_after_count,
        official_slot_count=official_slot_count,
        mapped_slot_count=mapped_slot_count,
        mismatch_slots=mismatch_slots,
    )


def _human_summary(verdict: SettlementFinalProbeVerdict) -> str:
    reasons = ", ".join(verdict.reasons) if verdict.reasons else "none"
    return "\n".join(
        (
            f"LC2 settlement final probe: {verdict.status}",
            (
                f"hooks={verdict.hooks} sequence={verdict.sequence} "
                f"payloads={verdict.payloads} sync_end={verdict.sync_end} "
                f"official_match={verdict.official_match}"
            ),
            (
                f"hooks_logged={verdict.hook_log_count} "
                f"records={verdict.network_record_count} "
                f"boundaries={verdict.boundary_count} "
                f"complete_sync_end={verdict.complete_sync_end_count}"
            ),
            (
                f"official_slots={verdict.official_slot_count} "
                f"mapped_slots={verdict.mapped_slot_count}"
            ),
            f"reasons={reasons}",
        )
    )


def _missing_input(reason: str) -> SettlementFinalProbeVerdict:
    verdict = evaluate_settlement_final_probe(())
    return replace(
        verdict,
        reasons=(reason,),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check LC2 settlement-final diagnostic logs.",
    )
    parser.add_argument("log", type=Path, nargs="?")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.log is None:
        verdict = _missing_input("input_missing")
    else:
        try:
            lines = args.log.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            verdict = _missing_input("input_unreadable")
        else:
            verdict = evaluate_settlement_final_probe(lines)

    if args.as_json:
        print(json.dumps(asdict(verdict), ensure_ascii=False, indent=2))
    else:
        print(_human_summary(verdict))
    if verdict.status == "PASS":
        return 0
    if verdict.status == "NOT_RUN":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
