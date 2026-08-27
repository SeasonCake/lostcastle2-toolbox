"""Independent feature modules for the Lost Castle 2 toolbox."""

from .combat_aggregator import (
    CombatAggregator,
    CombatEventError,
    CombatSnapshot,
    ScenarioInfo,
    ScenarioRegistry,
    SequenceError,
    SessionMismatchError,
    SourceInfo,
    SourceRegistry,
)
from .app_shell import (
    MacroRow,
    ToolboxShell,
    format_location_label,
    format_metric,
    format_room_area,
    format_stage_location,
    macro_rows,
    metric_font_size,
    seed_demo_combat,
)
from .macro_engine import MacroController, MacroState
from .macro_model import MacroProfile, MacroProfileError, parse_macro_profile

__all__ = [
    "CombatAggregator",
    "CombatEventError",
    "CombatSnapshot",
    "MacroRow",
    "MacroController",
    "MacroProfile",
    "MacroProfileError",
    "MacroState",
    "ScenarioInfo",
    "ScenarioRegistry",
    "SequenceError",
    "SessionMismatchError",
    "SourceInfo",
    "SourceRegistry",
    "ToolboxShell",
    "format_location_label",
    "format_metric",
    "format_room_area",
    "format_stage_location",
    "macro_rows",
    "metric_font_size",
    "seed_demo_combat",
    "parse_macro_profile",
]
