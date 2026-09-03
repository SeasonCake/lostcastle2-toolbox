from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class LeaveTeamIdentityVerdict:
    passed: bool
    reasons: tuple[str, ...]
    session_id: str | None
    previous_party_size: int
    previous_local_id: str | None
    previous_local_slot: int | None
    previous_local_live: int | None
    singleton_local_id: str | None
    singleton_local_slot: int | None
    singleton_local_live: int | None
    inherited_departed_player_id: str | None


def _party_members(event: Mapping[str, object]) -> list[Mapping[str, object]] | None:
    if (
        event.get("event_type") != "status"
        or event.get("status") != "party_updated"
    ):
        return None
    members = event.get("party_members")
    if not isinstance(members, list) or not all(
        isinstance(member, Mapping) for member in members
    ):
        return None
    return list(members)


def _local_member(
    members: list[Mapping[str, object]],
) -> Mapping[str, object] | None:
    locals_ = [member for member in members if member.get("is_local") is True]
    return locals_[0] if len(locals_) == 1 else None


def _strict_optional_int(value: object) -> int | None:
    return value if type(value) is int else None


def evaluate_leave_team_identity(lines: Iterable[str]) -> LeaveTeamIdentityVerdict:
    events: list[Mapping[str, object]] = []
    parse_error = False
    for line in lines:
        try:
            value = json.loads(line)
        except (TypeError, ValueError):
            parse_error = True
            continue
        if isinstance(value, Mapping):
            events.append(value)

    reasons: set[str] = set()
    if parse_error:
        reasons.add("event_parse_error")
    previous_event: Mapping[str, object] | None = None
    previous_members: list[Mapping[str, object]] | None = None
    singleton_event: Mapping[str, object] | None = None
    singleton_members: list[Mapping[str, object]] | None = None
    for event in events:
        members = _party_members(event)
        if members is None:
            continue
        if len(members) > 1:
            previous_event = event
            previous_members = members
            continue
        if len(members) == 1 and previous_members is not None:
            singleton_event = event
            singleton_members = members
            break
    if previous_members is None or previous_event is None:
        reasons.add("multiplayer_snapshot_missing")
    if singleton_members is None or singleton_event is None:
        reasons.add("singleton_after_leave_missing")

    previous_local = (
        _local_member(previous_members) if previous_members is not None else None
    )
    singleton_local = (
        _local_member(singleton_members) if singleton_members is not None else None
    )
    if previous_members is not None and previous_local is None:
        reasons.add("previous_local_identity_invalid")
    if singleton_members is not None and singleton_local is None:
        reasons.add("singleton_local_identity_invalid")

    session_id = (
        str(previous_event.get("session_id"))
        if previous_event is not None and previous_event.get("session_id") is not None
        else None
    )
    singleton_session = (
        str(singleton_event.get("session_id"))
        if singleton_event is not None and singleton_event.get("session_id") is not None
        else None
    )
    if session_id is not None and singleton_session != session_id:
        reasons.add("session_changed_before_singleton")

    previous_id = (
        str(previous_local.get("player_id"))
        if previous_local is not None and previous_local.get("player_id") is not None
        else None
    )
    singleton_id = (
        str(singleton_local.get("player_id"))
        if singleton_local is not None and singleton_local.get("player_id") is not None
        else None
    )
    previous_live = (
        _strict_optional_int(previous_local.get("live_damage"))
        if previous_local is not None
        else None
    )
    singleton_live = (
        _strict_optional_int(singleton_local.get("live_damage"))
        if singleton_local is not None
        else None
    )
    if previous_id is not None and singleton_id != previous_id:
        reasons.add("local_player_id_changed")
    if previous_live is None or singleton_live is None:
        reasons.add("local_live_damage_missing")
    elif singleton_live != previous_live:
        reasons.add("local_live_damage_changed_on_leave")

    inherited_id: str | None = None
    if previous_members is not None and singleton_live is not None:
        for member in previous_members:
            if member is previous_local:
                continue
            if _strict_optional_int(member.get("live_damage")) == singleton_live:
                inherited_id = str(member.get("player_id"))
                break
    if inherited_id is not None:
        reasons.add("singleton_inherited_departed_live")

    return LeaveTeamIdentityVerdict(
        passed=not reasons,
        reasons=tuple(sorted(reasons)),
        session_id=session_id,
        previous_party_size=0 if previous_members is None else len(previous_members),
        previous_local_id=previous_id,
        previous_local_slot=(
            _strict_optional_int(previous_local.get("player_slot"))
            if previous_local is not None
            else None
        ),
        previous_local_live=previous_live,
        singleton_local_id=singleton_id,
        singleton_local_slot=(
            _strict_optional_int(singleton_local.get("player_slot"))
            if singleton_local is not None
            else None
        ),
        singleton_local_live=singleton_live,
        inherited_departed_player_id=inherited_id,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check same-session LC2 leave-team local identity continuity."
    )
    parser.add_argument("events", type=Path)
    args = parser.parse_args()
    verdict = evaluate_leave_team_identity(
        args.events.read_text(encoding="utf-8", errors="replace").splitlines()
    )
    print(json.dumps(asdict(verdict), ensure_ascii=False, indent=2))
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
