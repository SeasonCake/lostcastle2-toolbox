# Lost Castle 2 Toolbox

[简体中文](README.zh-CN.md)

An unofficial, open-source Windows toolbox for *Lost Castle 2*.

The repository currently contains:

- a customizable keyboard/mouse input overlay;
- opt-in, foreground-only input macros with a global emergency stop;
- a read-only combat bridge;
- versioned contracts and a replayable aggregator for damage, healing, mana, effects, and shields;
- in-memory current-match statistics that reset at explicit session boundaries without writing per-match archives by default;
- a managed entry point for attributed third-party tools.

The application now starts in a calculator-style main toolbox window. It manages the keyboard overlay, macros, and a compact combat HUD; full combat details live in the main window. The v2 event contract keeps game observation, aggregation, and presentation separate so new items normally require a source-registry entry instead of new UI logic.

On a clean game installation, the first toolbox game launch offers an explicit one-click setup for the pinned BepInEx runtime and the read-only combat Bridge. No community MOD is enabled automatically, the BepInEx console is disabled by default, and a different existing BepInEx core is never overwritten silently.

## Project status

| Area | Status |
| --- | --- |
| Key overlay | Available |
| Foreground-only macros | Available, disabled by default |
| Damage and HP semantics | Runtime-validated on the recorded game build |
| Combat event v2 and replay aggregation | Implemented and tested |
| Mana and shield observation bridge | Mana spend/recovery runtime-validated; shield samples still pending |
| Main toolbox and external combat HUD | Bridge 1.7 labels the compact HUD **realtime** while the detailed page explains **realtime estimate / settlement may correct**. Complete SyncEnd values are the **official settlement** and may correct upward or downward |
| MOD management | v1.7 manages two existing tools plus 56 curated community MODs. All plugins share one pinned BepInEx runtime and ship only 57 minimal functional payload files |

Research results are scoped to the game build recorded in the Chinese plan. A game update can invalidate hook compatibility and must be revalidated.

## Combat data contract

- During a match, the compact HUD labels per-player damage and Boss damage **realtime**. The detailed page says **realtime estimate** and explains that settlement may correct it. The values use verified in-game process data, but are not promised to equal the later result screen.
- Only a complete per-player SyncEnd snapshot is labelled **official settlement**. It replaces the estimate as-is and may move a player's value up or down. Per-hit observation remains useful for recent DPS, source details, damage taken, and resource changes.
- The release keeps current-match state in memory and resets it at explicit session boundaries. It does not write per-event journals, match ZIP files, or acceptance-probe data by default.

## Development

Requirements: Windows, Python 3.13, and the packages in `requirements-dev.txt`.

A fresh clone contains the source, contracts, and pinned 7-Zip components, but intentionally omits the Git-ignored community MOD payloads and LC2 runtime binaries. Before running the full `unittest` suite, `keyview.py --self-test`, or packaging, provision the exact local inputs recorded by `THIRD_PARTY_NOTICES.md`, `assets/community_mod_sources.json`, and the runtime manifest. Without those inputs, run only focused tests that do not require payloads; a missing-payload failure is not a source regression.

```powershell
py -3 -m pip install -r requirements-dev.txt
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 keyview.py --self-test
```

Run the toolbox from source:

```powershell
py -3 keyview.py
```

Code-driven UI review can open a page or overlay without moving the mouse:

```powershell
py -3 keyview.py --demo --show-page combat --show-combat-hud
py -3 keyview.py --demo-large-values --show-page combat --window-size 1000x720 --tk-scaling 1.5
py -3 keyview.py --demo-large-values --show-page combat --show-combat-hud --demo-scenario CastleBridge --demo-room-index 100
```

Build the Windows package:

```powershell
.\build.ps1
```

The pinned 7-Zip runtime and its license are included so source-mode archive inspection works after cloning. Other third-party executables, DLLs, archives, and the generated `third_party/community_mods` payload are intentionally excluded from Git. Before packaging, provision the exact local files recorded in `THIRD_PARTY_NOTICES.md` and `assets/community_mod_catalog.json`; `build.ps1` verifies their counts, sizes, and SHA-256 identities and stops if an input is missing or different.

The temporary BepInEx probe has separate instructions in [`game_plugins/LC2DamageProbe/README.zh-CN.md`](game_plugins/LC2DamageProbe/README.zh-CN.md). It is research instrumentation, not the final HUD bridge.

The v1.7 MOD page includes Soul Stone Trainer 1.2 by community author **恨你不见**, Gold Editor 1.0 by **刺心**, and 56 curated community MOD entries. The latest local intake adds Monster Treasure 11, Nightfall Bow Boost 1.1.0, and Reinforcement Transmitter: Lost Swordsman Shadow 1.0.0, while updating Reaper Summon from the Summon Master 2.1 source package. The other five entries moved to that source package are byte-identical to their existing payloads. Max Players 1.3.0 still ships only its 15,872-byte plugin instead of the source package's duplicated BepInEx stack; it is intended primarily for hosts and must be removed before joining another host's room. All entries share the pinned runtime and total 57 hash-bound functional files (3,522,509 bytes); generated config, cache, interop, Doorstop, and duplicate core files are excluded. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

The bottom-left footer links to GitHub and the maintainer's [Bilibili space](https://space.bilibili.com/88048665?), followed by a `投喂` entry that shows the WeChat code by default and opens the local WeChat, Alipay, and explanation folder for friends who enjoy *Lost Castle 2* and want to support the maintainer or nudge an update.

## Safety and scope

- The overlay reads Windows key state and does not inject into the game.
- Macros send only user-configured input while `LostCastle2.exe` is foreground, and stop on focus loss or `Ctrl + Shift + F12`.
- The research probe observes resolved combat state. It does not modify damage, drops, saves, or network state.
- Third-party tools do not inherit that read-only guarantee; the toolbox verifies pinned files and performs only the registered managed copy, install, uninstall, or explicit launch action.
- Game binaries, generated interop assemblies, logs, screenshots, local configuration, and packaged builds are intentionally excluded from Git.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).

## License and disclaimer

Project source code is available under the [MIT License](LICENSE). Game code, assets, names, trademarks, and third-party tools are not covered by this license.

This is an unofficial fan project and is not affiliated with or endorsed by Hunter Studio, Another Indie, or the game's publishers. Users must provide their own legitimate game installation.
