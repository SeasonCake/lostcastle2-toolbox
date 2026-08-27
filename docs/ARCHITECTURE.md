# Architecture

## Design goal

The combat module must remain maintainable when the game adds or reveals new healing items, mana modifiers, curses, summon ownership rules, kill procs, or defensive effects. Item names therefore do not define aggregation behavior.

```text
Lost Castle 2
  -> read-only bridge (observe resolved events)
  -> versioned JSON-line transport
  -> schema validation and session ordering
  -> CombatAggregator (pure replayable state)
  -> immutable snapshot
  -> external HUD / exports
```

The key overlay and macro modules stay usable when the bridge is absent.

## Product shell and window responsibilities

The application starts in one calculator-style toolbox window instead of starting in the keyboard overlay. That window is the only full application shell and opens or manages independent modules:

- **Combat:** a compact B-style in-game HUD for totals and resource flow; the full A-style breakdown lives only on the combat page in the main window.
- **Keyboard:** the existing semi-hollow soft-mist overlay remains visually independent from the warm calculator shell.
- **Macros:** configuration and status live in the main window; execution remains foreground-only and disabled by default.

The combat HUD and the full combat page consume the same `CombatSnapshot`. They do not calculate totals independently. Closing or hiding an overlay does not destroy the session model, and a module failure must not prevent the main shell or other modules from opening.

This split keeps the in-game surface small while avoiding a second expandable-window state machine. The main window owns navigation, settings, module status and global exit; each overlay owns only its geometry, visibility, topmost/click-through behavior and rendering.

## Open-source maintenance budget

This is a small free/open-source desktop tool, not a hosted commercial platform. The default architecture deliberately excludes accounts, activation, cloud sync, telemetry, a remote service, a plugin marketplace and an in-app updater.

- Prefer the Python standard library and the existing Tk stack.
- Keep configuration in bounded, versioned local JSON files.
- Keep raw game tokens out of layout code; labels belong in the source registry.
- Add generic event behavior only when semantics differ. Another item with the same behavior is data, not code.
- Keep one snapshot/view-model for every presentation of the same combat session.
- Add dependencies only when they remove more maintenance than they introduce.
- Sponsorship or video links, if added later, remain static project links and do not create account or entitlement infrastructure.

## Event model

[`contracts/combat_event.schema.json`](../contracts/combat_event.schema.json) is the current cross-process contract.

| Event | Purpose |
| --- | --- |
| `damage_resolution` | Dealt/taken damage, mitigation, overkill, boss identity, ownership |
| `resource_change` | Effective HP/MP/temp-HP change, attempted change, blocking and overflow |
| `effect_stack` | Shield charges, barriers, curses, buffs and debuffs |
| `trigger` | Kill, summon kill, hit, skill-use, periodic and item-use causality |
| `room_checkpoint` | Authoritative room totals used for reconciliation |
| `status` | Session, room and connection lifecycle |

Three fields prevent common counting errors:

1. `owner_player_id` attributes summons, projectiles and damage-over-time to their owning player.
2. `trigger_event_id` and `trigger_kind` preserve causality without forcing the UI to understand each soul-stone proc.
3. `aggregate` is decided by the bridge after nested-operation deduplication. The aggregator must not guess from `nesting_depth`.

## Location identity

`room_id` is a technical identity for ordering and deduplication. It is never a
user-facing map label. A `room_started` event carries four independent values from
the game's `StageMgr` state:

| Event field | Game source | Meaning |
| --- | --- | --- |
| `stage_level` | `StageMgr.CurStageLevel` | Main progression level, `0..6` |
| `scenario_id` | `StageMgr.CurScenario` | Route/map enum such as `MudSwamp` |
| `room_index` | `StageMgr.CurRoomIndex` | Area index inside that map; `99/100/101` are special |
| `map_file_name` | `StageMgr.CurRoomInfo.mapFileName` | Exact generated room asset for diagnosis |

The compact UI renders `地图名 · 第 N 区` (or a special room label) and the main
page additionally renders `第 N 阶段`. Scenario labels live in
[`assets/game_locations.json`](../assets/game_locations.json),
derived from the game's own `UI_UniformType.json::ScenarioName_*` table. Unknown
scenario enums remain visible as `未知地图 · token`; they must never inherit a nearby
known name. The current mapping is scoped to game package
`DefaultPackage_2026-08-18-1017` and must be rechecked after a game update.

The same package's `ScenarioConfigData.stageLevel` and `nextScenarioFlag` values
define the active campaign route:

| Stage | Active scenarios |
| --- | --- |
| 1 | `DarkForest` / 黑森林 |
| 2 | `RuinedCemetery`, `SaltpetreDesert`, `MudSwamp` / 三选一 |
| 3 | `CrystalMountain`, `IceCavern` / 二选一 |
| 4 | `CastleBridge`, `Sewer` / 二选一 |
| 5 | `MainCastle` / 黑城堡 |
| 6 | `MageTower` / 法师塔 |

`MagmaCave` still exists in the enum and localization table, but the verified
package has no matching scenario config and no active route points to it. It remains
a known label with no asserted stage instead of being presented as a current route.

## Counting rules

- Dealt damage uses the verified settlement value; actual target HP loss and overkill remain separate diagnostics.
- Official damage taken and actual HP loss are separate totals because mitigation can change only the latter.
- Healing uses positive effective HP delta, not requested healing. Overflow is recorded separately.
- Mana spend/gain uses effective MP delta. A curse-blocked recovery is an attempted change with zero effective delta and `blocked=true`.
- An HP decrease already represented by a damage event must not be emitted as a second aggregate resource loss. A mirror observation may be emitted with `aggregate=false`.
- Nested observer callbacks can all be retained for diagnosis, but exactly one event per logical operation is aggregateable.
- Room checkpoints reconcile event totals; they do not silently overwrite them.

## Source registry

[`assets/combat_sources.json`](../assets/combat_sources.json) maps raw source tokens to labels and broad categories. Unknown tokens remain visible as `未知来源 · token` and are counted, so a game update degrades to an actionable label instead of silently losing data.

Adding a new item should normally be:

1. capture a positive and a negative/overflow/blocked sample;
2. confirm the generic event semantics and ownership;
3. add or refine one registry entry;
4. add a replay fixture/test if it introduces a new behavior class.

New aggregator code is justified only for a new behavior class, not for another item name.

The location registry follows the same maintenance rule: a new route normally adds
one data entry. A new location hierarchy or room-index meaning justifies a contract
change.

## Session and replay invariants

- `(session_id, sequence)` is ordered and an `event_id` is idempotent.
- A foreign session is rejected unless it starts with an explicit `session_started` boundary.
- Monotonic time cannot move backwards within a session.
- The aggregator is deterministic and has no Tk or game dependency, allowing the HUD to be developed from fixtures before the final bridge exists.

## Implementation stages

1. **Foundation (complete):** v2 schema, source registry, replay aggregator, tests and public repository hygiene.
2. **Toolbox shell and replay HUD (current):** calculator-style main navigation, compact combat HUD, full combat details and deterministic demo/replay states.
3. **Bridge v2:** convert the proven damage/HP observer into the event envelope and local transport, then expose live/stale/error connection states.
4. **Mana and defenses:** verify MP cost/recovery/blocked paths and shield/effect stacks, then add registry entries.
5. **Calibration:** host/client, game-update compatibility, checkpoint differences and packaging.

A training dummy is not a prerequisite. Focused replay fixtures plus the game's authoritative settlement checkpoints provide the required positive control; a dummy can still be useful for manual UX demonstrations.
