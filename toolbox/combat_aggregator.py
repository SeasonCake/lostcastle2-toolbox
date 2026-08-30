from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping


SCHEMA_VERSION = 2
DEFAULT_DPS_WINDOW_MS = 10_000
DEFAULT_ENDED_RETENTION_MS: int | None = None
VALID_ROOM_INDICES = frozenset((*range(0, 11), 99, 100, 101))
VALID_TRANSPORT_STATES = frozenset({"connecting", "disconnected", "stale", "error"})


def monotonic_milliseconds() -> int:
    return max(0, round(time.monotonic() * 1_000))


class CombatEventError(ValueError):
    """Raised when an event violates the runtime aggregation contract."""


class SessionMismatchError(CombatEventError):
    """Raised when data from another session arrives without a start boundary."""


class SequenceError(CombatEventError):
    """Raised when sequence or monotonic time moves backwards."""


@dataclass(frozen=True)
class SourceInfo:
    token: str
    label: str
    category: str
    resource: str = "unknown"
    effect_kind: str = "unknown"
    known: bool = False


class SourceRegistry:
    def __init__(self, entries: Mapping[str, SourceInfo] | None = None) -> None:
        self._entries = dict(entries or {})

    @classmethod
    def from_file(cls, path: Path) -> SourceRegistry:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise CombatEventError("Unsupported combat source registry version.")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, dict):
            raise CombatEventError("Combat source registry entries must be an object.")
        entries: dict[str, SourceInfo] = {}
        for token, raw in raw_entries.items():
            if not isinstance(token, str) or not token or not isinstance(raw, dict):
                raise CombatEventError("Invalid combat source registry entry.")
            label = raw.get("label")
            category = raw.get("category")
            if not isinstance(label, str) or not label or not isinstance(category, str) or not category:
                raise CombatEventError(f"Invalid combat source metadata for {token!r}.")
            entries[token] = SourceInfo(
                token=token,
                label=label,
                category=category,
                resource=str(raw.get("resource", "unknown")),
                effect_kind=str(raw.get("effect_kind", "unknown")),
                known=True,
            )
        return cls(entries)

    def resolve(self, token: str | None) -> SourceInfo:
        key = token if token not in {None, "", "null"} else "<none>"
        known = self._entries.get(key)
        if known is not None:
            return known
        if key == "<none>":
            return SourceInfo(key, "未提供来源", "unknown")
        return SourceInfo(key, f"未知来源 · {key}", "unknown")


@dataclass(frozen=True)
class ScenarioInfo:
    scenario_id: str
    label_zh_cn: str
    label_en: str
    enum_value: int | None = None
    stage_level: int | None = None
    known: bool = False


class ScenarioRegistry:
    """Versioned map-name data, kept separate from room/session identity."""

    def __init__(
        self,
        entries: Mapping[str, ScenarioInfo] | None = None,
        active_campaign_routes: Mapping[int, tuple[str, ...]] | None = None,
    ) -> None:
        self._entries = dict(entries or {})
        self._active_campaign_routes = dict(active_campaign_routes or {})

    @classmethod
    def from_file(cls, path: Path) -> ScenarioRegistry:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise CombatEventError("Unsupported game location registry version.")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, dict):
            raise CombatEventError("Game location registry entries must be an object.")
        entries: dict[str, ScenarioInfo] = {}
        for scenario_id, raw in raw_entries.items():
            if not isinstance(scenario_id, str) or not scenario_id or not isinstance(raw, dict):
                raise CombatEventError("Invalid game location registry entry.")
            label_zh_cn = raw.get("label_zh_cn")
            label_en = raw.get("label_en")
            stage_level = raw.get("stage_level")
            enum_value = raw.get("enum_value")
            if not isinstance(label_zh_cn, str) or not label_zh_cn:
                raise CombatEventError(f"Invalid Chinese location label for {scenario_id!r}.")
            if not isinstance(label_en, str) or not label_en:
                raise CombatEventError(f"Invalid English location label for {scenario_id!r}.")
            if stage_level is not None and (
                type(stage_level) is not int or not 0 <= stage_level <= 6
            ):
                raise CombatEventError(f"Invalid stage level for {scenario_id!r}.")
            if enum_value is not None and type(enum_value) is not int:
                raise CombatEventError(f"Invalid scenario enum value for {scenario_id!r}.")
            entries[scenario_id] = ScenarioInfo(
                scenario_id=scenario_id,
                label_zh_cn=label_zh_cn,
                label_en=label_en,
                enum_value=enum_value,
                stage_level=stage_level,
                known=True,
            )
        raw_routes = payload.get("active_campaign_routes")
        if not isinstance(raw_routes, dict):
            raise CombatEventError("Active campaign routes must be an object.")
        active_campaign_routes: dict[int, tuple[str, ...]] = {}
        for raw_stage_level, raw_scenario_ids in raw_routes.items():
            try:
                stage_level = int(raw_stage_level)
            except (TypeError, ValueError) as exception:
                raise CombatEventError("Invalid campaign route stage level.") from exception
            if str(stage_level) != raw_stage_level or not 1 <= stage_level <= 6:
                raise CombatEventError("Invalid campaign route stage level.")
            if (
                not isinstance(raw_scenario_ids, list)
                or not raw_scenario_ids
                or not all(
                    isinstance(scenario_id, str) and scenario_id
                    for scenario_id in raw_scenario_ids
                )
                or len(raw_scenario_ids) != len(set(raw_scenario_ids))
            ):
                raise CombatEventError(
                    f"Invalid campaign route list for stage {stage_level}."
                )
            for scenario_id in raw_scenario_ids:
                scenario = entries.get(scenario_id)
                if scenario is None or scenario.stage_level != stage_level:
                    raise CombatEventError(
                        f"Campaign route {scenario_id!r} does not match stage {stage_level}."
                    )
            active_campaign_routes[stage_level] = tuple(raw_scenario_ids)
        if set(active_campaign_routes) != set(range(1, 7)):
            raise CombatEventError("Campaign routes must define stages 1 through 6.")
        return cls(entries, active_campaign_routes)

    def route_ids_for_stage(self, stage_level: int) -> tuple[str, ...]:
        return self._active_campaign_routes.get(stage_level, ())

    def resolve(self, scenario_id: str | None) -> ScenarioInfo:
        key = scenario_id if scenario_id not in {None, "", "null"} else "<none>"
        known = self._entries.get(key)
        if known is not None:
            return known
        if key == "<none>":
            return ScenarioInfo(key, "未知地图", "Unknown map")
        return ScenarioInfo(key, f"未知地图 · {key}", f"Unknown map · {key}")


@dataclass
class SourceTotals:
    damage_dealt: int = 0
    boss_damage: int = 0
    effective_healing: float = 0.0
    hp_loss_other: float = 0.0
    mp_spent: float = 0.0
    mp_gained: float = 0.0
    blocked_attempts: int = 0
    effect_event_count: int = 0
    trigger_count: int = 0


@dataclass
class PlayerTotals:
    player_slot: int | None = None
    is_local: bool = False
    active: bool = False
    damage_dealt: int = 0
    boss_damage: int = 0


@dataclass(frozen=True)
class CombatSnapshot:
    session_id: str | None
    connection_state: str
    diagnostic_warning: str | None
    current_room_id: str | None
    current_stage_level: int | None
    current_scenario_id: str | None
    current_scenario_label: str | None
    current_room_index: int | None
    current_map_file_name: str | None
    last_sequence: int | None
    last_monotonic_ms: int | None
    total_damage: int
    recent_dps: float
    boss_damage: int
    personal_damage: int
    personal_recent_dps: float
    personal_boss_damage: int
    taken_settlement_damage: int
    hp_damage_taken: float
    mitigated_damage: float
    overkill_damage: float
    effective_healing: float
    hp_loss_other: float
    mp_spent: float
    mp_gained: float
    mp_net: float
    resource_blocked_attempts: int
    resource_overflow: float
    shield_absorbs: int
    shield_layers_consumed: float
    effect_stacks: dict[str, float]
    checkpoint_totals: dict[str, float]
    unknown_sources: dict[str, int]
    source_breakdown: dict[str, dict[str, Any]]
    personal_source_breakdown: dict[str, dict[str, Any]]
    detected_player_count: int
    player_breakdown: dict[str, dict[str, Any]]
    unattributed_damage: int
    unattributed_boss_damage: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CombatAggregator:
    registry: SourceRegistry = field(default_factory=SourceRegistry)
    scenario_registry: ScenarioRegistry = field(default_factory=ScenarioRegistry)
    dps_window_ms: int = DEFAULT_DPS_WINDOW_MS
    ended_retention_ms: int | None = DEFAULT_ENDED_RETENTION_MS
    clock_ms: Callable[[], int] = field(
        default=monotonic_milliseconds,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.dps_window_ms <= 0:
            raise ValueError("dps_window_ms must be positive")
        if self.ended_retention_ms is not None and self.ended_retention_ms < 0:
            raise ValueError("ended_retention_ms must not be negative")
        self.reset()

    def reset(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self.connection_state = "disconnected"
        self.last_sequence: int | None = None
        self.last_monotonic_ms: int | None = None
        self._seen_event_ids: set[str] = set()
        self._seen_sequences: dict[int, str] = {}
        self._ended_at_clock_ms: int | None = None
        self._ended_metrics_cleared = False
        self._clear_session_metrics()

    def _clear_session_metrics(self) -> None:
        self.current_room_id: str | None = None
        self.diagnostic_warning: str | None = None
        self.current_stage_level: int | None = None
        self.current_scenario_id: str | None = None
        self.current_scenario_label: str | None = None
        self.current_room_index: int | None = None
        self.current_map_file_name: str | None = None
        self._recent_damage: deque[tuple[int, int, str | None]] = deque()
        self._source_totals: defaultdict[str, SourceTotals] = defaultdict(SourceTotals)
        self._player_totals: defaultdict[str, PlayerTotals] = defaultdict(PlayerTotals)
        self._player_source_totals: defaultdict[
            str, defaultdict[str, SourceTotals]
        ] = defaultdict(lambda: defaultdict(SourceTotals))
        self._party_roster_seen = False
        self._unknown_sources: Counter[str] = Counter()
        self.effect_stacks: dict[str, float] = {}
        self.checkpoint_totals: dict[str, float] = {}
        self.total_damage = 0
        self.boss_damage = 0
        self.unattributed_damage = 0
        self.unattributed_boss_damage = 0
        self.taken_settlement_damage = 0
        self.hp_damage_taken = 0.0
        self.mitigated_damage = 0.0
        self.overkill_damage = 0.0
        self.effective_healing = 0.0
        self.hp_loss_other = 0.0
        self.mp_spent = 0.0
        self.mp_gained = 0.0
        self.resource_blocked_attempts = 0
        self.resource_overflow = 0.0
        self.shield_absorbs = 0
        self.shield_layers_consumed = 0.0

    def ingest(self, event: Mapping[str, Any]) -> bool:
        self._validate_common(event)
        event_id = str(event["event_id"])
        if event_id in self._seen_event_ids:
            return False

        event_session = str(event["session_id"])
        is_session_start = (
            event["event_type"] == "status" and event.get("status") == "session_started"
        )
        if self.session_id is None:
            self.session_id = event_session
        elif event_session != self.session_id:
            if not is_session_start:
                raise SessionMismatchError(
                    f"Expected session {self.session_id!r}, got {event_session!r}."
                )
            self.reset(event_session)
        elif is_session_start and self.last_sequence is not None:
            raise SessionMismatchError("A live session cannot start twice with a new event id.")

        sequence = int(event["sequence"])
        previous_event_id = self._seen_sequences.get(sequence)
        if previous_event_id is not None:
            if previous_event_id == event_id:
                return False
            raise SequenceError(f"Sequence {sequence} was reused by another event.")
        if self.last_sequence is not None and sequence <= self.last_sequence:
            raise SequenceError(
                f"Sequence moved backwards: {sequence} <= {self.last_sequence}."
            )

        monotonic_ms = int(event["monotonic_ms"])
        if self.last_monotonic_ms is not None and monotonic_ms < self.last_monotonic_ms:
            raise SequenceError(
                f"Monotonic time moved backwards: {monotonic_ms} < {self.last_monotonic_ms}."
            )

        self._seen_event_ids.add(event_id)
        self._seen_sequences[sequence] = event_id
        self.last_sequence = sequence
        self.last_monotonic_ms = monotonic_ms

        event_type = str(event["event_type"])
        if event_type == "status":
            self._ingest_status(event)
        elif bool(event["aggregate"]):
            if event_type == "damage_resolution":
                self._ingest_damage(event)
            elif event_type == "resource_change":
                self._ingest_resource(event)
            elif event_type == "effect_stack":
                self._ingest_effect(event)
            elif event_type == "trigger":
                self._ingest_trigger(event)
            elif event_type == "room_checkpoint":
                self._ingest_checkpoint(event)
        return True

    def apply_transport_state(self, state: str) -> None:
        """Apply a local transport observation without forging a game event."""
        if state not in VALID_TRANSPORT_STATES:
            raise CombatEventError(f"Unsupported transport state: {state!r}")
        self.connection_state = state

    def snapshot(self, monotonic_ms: int | None = None) -> CombatSnapshot:
        self._expire_ended_metrics()
        now = self.last_monotonic_ms if monotonic_ms is None else monotonic_ms
        if now is None:
            now = 0
        self._prune_recent_damage(now)
        local_player_ids = {
            player_id
            for player_id, totals in self._player_totals.items()
            if totals.is_local
        }
        has_remote_player_history = any(
            not totals.is_local for totals in self._player_totals.values()
        )
        use_personal_scope = bool(local_player_ids) and has_remote_player_history
        recent_damage = sum(value for _, value, _owner in self._recent_damage)
        recent_dps = recent_damage / (self.dps_window_ms / 1000.0)
        personal_damage = (
            sum(self._player_totals[player_id].damage_dealt for player_id in local_player_ids)
            if use_personal_scope
            else self.total_damage
        )
        personal_boss_damage = (
            sum(self._player_totals[player_id].boss_damage for player_id in local_player_ids)
            if use_personal_scope
            else self.boss_damage
        )
        personal_recent_damage = (
            sum(
                value
                for _, value, owner_player_id in self._recent_damage
                if owner_player_id in local_player_ids
            )
            if use_personal_scope
            else recent_damage
        )
        personal_recent_dps = personal_recent_damage / (self.dps_window_ms / 1000.0)

        breakdown: dict[str, dict[str, Any]] = {}
        for token, totals in sorted(self._source_totals.items()):
            info = self.registry.resolve(None if token == "<none>" else token)
            breakdown[token] = {
                "label": info.label,
                "category": info.category,
                "known": info.known,
                **asdict(totals),
            }

        personal_breakdown: dict[str, dict[str, Any]] = {}
        for token, totals in sorted(self._source_totals.items()):
            info = self.registry.resolve(None if token == "<none>" else token)
            personal_damage_for_source = (
                sum(
                    self._player_source_totals[player_id][token].damage_dealt
                    for player_id in local_player_ids
                )
                if use_personal_scope
                else totals.damage_dealt
            )
            personal_boss_for_source = (
                sum(
                    self._player_source_totals[player_id][token].boss_damage
                    for player_id in local_player_ids
                )
                if use_personal_scope
                else totals.boss_damage
            )
            values = {
                **asdict(totals),
                "damage_dealt": personal_damage_for_source,
                "boss_damage": personal_boss_for_source,
            }
            if not any(float(value) for value in values.values()):
                continue
            personal_breakdown[token] = {
                "label": info.label,
                "category": info.category,
                "known": info.known,
                **values,
            }

        player_breakdown: dict[str, dict[str, Any]] = {}
        ordered_players = sorted(
            self._player_totals.items(),
            key=lambda item: (
                not item[1].is_local,
                item[1].player_slot is None,
                item[1].player_slot if item[1].player_slot is not None else 99,
                item[0],
            ),
        )
        teammate_number = 0
        for player_id, totals in ordered_players:
            if totals.is_local:
                label = "自己"
            elif totals.active:
                teammate_number += 1
                label = f"队友 {teammate_number}"
            else:
                label = "离队成员"
            player_breakdown[player_id] = {
                "label": label,
                "player_slot": totals.player_slot,
                "is_local": totals.is_local,
                "active": totals.active,
                "damage_dealt": totals.damage_dealt,
                "boss_damage": totals.boss_damage,
                "damage_share": (
                    totals.damage_dealt / self.total_damage
                    if self.total_damage > 0
                    else 0.0
                ),
            }
        detected_player_count = (
            sum(1 for totals in self._player_totals.values() if totals.active)
            if self._party_roster_seen
            else len(self._player_totals)
        )

        return CombatSnapshot(
            session_id=self.session_id,
            connection_state=self.connection_state,
            diagnostic_warning=self.diagnostic_warning,
            current_room_id=self.current_room_id,
            current_stage_level=self.current_stage_level,
            current_scenario_id=self.current_scenario_id,
            current_scenario_label=self.current_scenario_label,
            current_room_index=self.current_room_index,
            current_map_file_name=self.current_map_file_name,
            last_sequence=self.last_sequence,
            last_monotonic_ms=self.last_monotonic_ms,
            total_damage=self.total_damage,
            recent_dps=recent_dps,
            boss_damage=self.boss_damage,
            personal_damage=personal_damage,
            personal_recent_dps=personal_recent_dps,
            personal_boss_damage=personal_boss_damage,
            taken_settlement_damage=self.taken_settlement_damage,
            hp_damage_taken=self.hp_damage_taken,
            mitigated_damage=self.mitigated_damage,
            overkill_damage=self.overkill_damage,
            effective_healing=self.effective_healing,
            hp_loss_other=self.hp_loss_other,
            mp_spent=self.mp_spent,
            mp_gained=self.mp_gained,
            mp_net=self.mp_gained - self.mp_spent,
            resource_blocked_attempts=self.resource_blocked_attempts,
            resource_overflow=self.resource_overflow,
            shield_absorbs=self.shield_absorbs,
            shield_layers_consumed=self.shield_layers_consumed,
            effect_stacks=dict(sorted(self.effect_stacks.items())),
            checkpoint_totals=dict(sorted(self.checkpoint_totals.items())),
            unknown_sources=dict(sorted(self._unknown_sources.items())),
            source_breakdown=breakdown,
            personal_source_breakdown=personal_breakdown,
            detected_player_count=detected_player_count,
            player_breakdown=player_breakdown,
            unattributed_damage=self.unattributed_damage,
            unattributed_boss_damage=self.unattributed_boss_damage,
        )

    def _validate_common(self, event: Mapping[str, Any]) -> None:
        required = {
            "schema_version",
            "event_id",
            "event_type",
            "session_id",
            "sequence",
            "monotonic_ms",
            "room_id",
            "aggregate",
            "hook_path",
        }
        missing = required.difference(event)
        if missing:
            raise CombatEventError(f"Missing required event fields: {sorted(missing)}")
        if event["schema_version"] != SCHEMA_VERSION:
            raise CombatEventError(f"Unsupported combat event version: {event['schema_version']!r}")
        if not isinstance(event["sequence"], int) or event["sequence"] < 0:
            raise CombatEventError("sequence must be a non-negative integer")
        if not isinstance(event["monotonic_ms"], int) or event["monotonic_ms"] < 0:
            raise CombatEventError("monotonic_ms must be a non-negative integer")
        if not isinstance(event["aggregate"], bool):
            raise CombatEventError("aggregate must be boolean")
        if event["event_type"] == "status" and event.get("status") == "room_started":
            self._validate_room_started(event)
        if event["event_type"] == "status" and event.get("status") == "party_updated":
            self._validate_party_updated(event)

    @staticmethod
    def _validate_room_started(event: Mapping[str, Any]) -> None:
        room_id = event.get("room_id")
        stage_level = event.get("stage_level")
        room_index = event.get("room_index")
        scenario_id = event.get("scenario_id")
        map_file_name = event.get("map_file_name")
        if not isinstance(room_id, str) or not room_id:
            raise CombatEventError("room_started requires a non-empty room_id.")
        if type(stage_level) is not int or not 0 <= stage_level <= 6:
            raise CombatEventError("room_started has an invalid stage_level.")
        if type(room_index) is not int or room_index not in VALID_ROOM_INDICES:
            raise CombatEventError("room_started has an invalid room_index.")
        if not isinstance(scenario_id, str) or not scenario_id:
            raise CombatEventError("room_started requires a scenario_id.")
        if not isinstance(map_file_name, str) or not map_file_name:
            raise CombatEventError("room_started requires a map_file_name.")

    @staticmethod
    def _validate_party_updated(event: Mapping[str, Any]) -> None:
        members = event.get("party_members")
        if not isinstance(members, list) or not 1 <= len(members) <= 16:
            raise CombatEventError("party_updated requires 1 to 16 party members.")
        player_ids: set[str] = set()
        for member in members:
            if not isinstance(member, Mapping):
                raise CombatEventError("party member must be an object.")
            player_id = member.get("player_id")
            player_slot = member.get("player_slot")
            is_local = member.get("is_local")
            if not isinstance(player_id, str) or not player_id or len(player_id) > 128:
                raise CombatEventError("party member has an invalid player_id.")
            if player_id in player_ids:
                raise CombatEventError("party_updated contains a duplicate player_id.")
            if player_slot is not None and (
                type(player_slot) is not int or not 0 <= player_slot <= 15
            ):
                raise CombatEventError("party member has an invalid player_slot.")
            if not isinstance(is_local, bool):
                raise CombatEventError("party member has an invalid is_local flag.")
            player_ids.add(player_id)

    def _source_key(self, event: Mapping[str, Any]) -> str:
        token = event.get("source_token")
        key = str(token) if token not in {None, "", "null"} else "<none>"
        if not self.registry.resolve(None if key == "<none>" else key).known:
            self._unknown_sources[key] += 1
        return key

    def _ingest_damage(self, event: Mapping[str, Any]) -> None:
        direction = event.get("damage_direction")
        settlement = int(event.get("settlement_damage") or 0)
        applied = float(event.get("applied_hp_damage") or 0.0)
        mitigated = float(event.get("mitigated_damage") or 0.0)
        overkill = float(event.get("overkill_damage") or 0.0)
        source = self._source_key(event)
        totals = self._source_totals[source]

        if direction == "dealt":
            self.total_damage += settlement
            totals.damage_dealt += settlement
            owner_player_id = event.get("owner_player_id")
            if isinstance(owner_player_id, str) and owner_player_id:
                player_totals = self._player_totals[owner_player_id]
                player_totals.damage_dealt += settlement
                player_source_totals = self._player_source_totals[owner_player_id][source]
                player_source_totals.damage_dealt += settlement
            else:
                player_totals = None
                self.unattributed_damage += settlement
            if event.get("is_boss") is True:
                self.boss_damage += settlement
                totals.boss_damage += settlement
                if player_totals is not None:
                    player_totals.boss_damage += settlement
                    player_source_totals.boss_damage += settlement
                else:
                    self.unattributed_boss_damage += settlement
            self._recent_damage.append(
                (
                    int(event["monotonic_ms"]),
                    settlement,
                    owner_player_id
                    if isinstance(owner_player_id, str) and owner_player_id
                    else None,
                )
            )
        elif direction == "taken":
            self.taken_settlement_damage += settlement
            self.hp_damage_taken += applied
            self.mitigated_damage += mitigated
            self.overkill_damage += overkill
            if event.get("damage_outcome") == "absorbed":
                self.shield_absorbs += 1

    def _ingest_resource(self, event: Mapping[str, Any]) -> None:
        resource = event.get("resource")
        delta = float(event.get("effective_delta") or 0.0)
        source = self._source_key(event)
        totals = self._source_totals[source]

        if resource == "hp":
            if delta > 0:
                self.effective_healing += delta
                totals.effective_healing += delta
            elif delta < 0:
                loss = -delta
                self.hp_loss_other += loss
                totals.hp_loss_other += loss
        elif resource == "mp":
            if delta > 0:
                self.mp_gained += delta
                totals.mp_gained += delta
            elif delta < 0:
                spent = -delta
                self.mp_spent += spent
                totals.mp_spent += spent

        if event.get("blocked") is True:
            self.resource_blocked_attempts += 1
            totals.blocked_attempts += 1
        self.resource_overflow += float(event.get("overflow") or 0.0)

    def _ingest_effect(self, event: Mapping[str, Any]) -> None:
        effect_token = str(event.get("effect_token") or event.get("source_token") or "unknown")
        after = float(event.get("stacks_after") or 0.0)
        delta = float(event.get("stack_delta") or 0.0)
        self.effect_stacks[effect_token] = after
        source = self._source_key(
            {"source_token": event.get("source_token") or effect_token}
        )
        self._source_totals[source].effect_event_count += 1
        if (
            event.get("effect_kind") == "shield_charge"
            and delta < 0
            and event.get("trigger_kind") == "hit_received"
        ):
            self.shield_layers_consumed += -delta

    def _ingest_trigger(self, event: Mapping[str, Any]) -> None:
        source = self._source_key(event)
        self._source_totals[source].trigger_count += 1

    def _ingest_checkpoint(self, event: Mapping[str, Any]) -> None:
        values = event.get("checkpoint_totals") or {}
        self.checkpoint_totals = {str(key): float(value) for key, value in values.items()}

    def _ingest_status(self, event: Mapping[str, Any]) -> None:
        status = str(event.get("status"))
        if status in {
            "session_started",
            "live",
            "room_started",
            "room_ended",
            "party_updated",
        }:
            self.connection_state = "live"
            self._ended_at_clock_ms = None
            self._ended_metrics_cleared = False
        elif status == "session_ended":
            self.connection_state = "ended"
            if self._ended_at_clock_ms is None:
                self._ended_at_clock_ms = self.clock_ms()
        elif status in {"connecting", "disconnected", "stale", "error"}:
            self.connection_state = status
        detail = event.get("detail")
        if status == "session_started":
            self.diagnostic_warning = None
        elif (
            status == "live"
            and isinstance(detail, str)
            and detail.startswith("degraded:")
        ):
            self.diagnostic_warning = detail
        if status == "room_started":
            self.current_room_id = str(event["room_id"])
            self.current_stage_level = int(event["stage_level"])
            self.current_room_index = int(event["room_index"])
            self.current_scenario_id = str(event["scenario_id"])
            scenario = self.scenario_registry.resolve(self.current_scenario_id)
            self.current_scenario_label = scenario.label_zh_cn
            self.current_map_file_name = str(event["map_file_name"])
        elif status == "party_updated":
            self._party_roster_seen = True
            for totals in self._player_totals.values():
                totals.active = False
            for member in event["party_members"]:
                player_id = str(member["player_id"])
                totals = self._player_totals[player_id]
                totals.player_slot = member.get("player_slot")
                totals.is_local = bool(member["is_local"])
                totals.active = True

    def _expire_ended_metrics(self) -> None:
        if (
            self.ended_retention_ms is None
            or self.connection_state != "ended"
            or self._ended_at_clock_ms is None
            or self._ended_metrics_cleared
        ):
            return
        if self.clock_ms() - self._ended_at_clock_ms < self.ended_retention_ms:
            return
        self._clear_session_metrics()
        self._ended_metrics_cleared = True

    def _prune_recent_damage(self, now_ms: int) -> None:
        cutoff = now_ms - self.dps_window_ms
        while self._recent_damage and self._recent_damage[0][0] < cutoff:
            self._recent_damage.popleft()
