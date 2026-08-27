# Lost Castle 2 Toolbox

[简体中文](README.zh-CN.md)

An unofficial, open-source Windows toolbox for *Lost Castle 2*.

The repository currently contains:

- a customizable keyboard/mouse input overlay;
- opt-in, foreground-only input macros with a global emergency stop;
- a read-only combat research probe;
- versioned contracts and a replayable aggregator for damage, healing, mana, effects, and shields;
- a managed entry point for attributed third-party tools.

The application now starts in a calculator-style main toolbox window. It manages the keyboard overlay, macros, and a compact combat HUD; full combat details live in the main window. The v2 event contract keeps game observation, aggregation, and presentation separate so new items normally require a source-registry entry instead of new UI logic.

## Project status

| Area | Status |
| --- | --- |
| Key overlay | Available |
| Foreground-only macros | Available, disabled by default |
| Damage and HP semantics | Runtime-validated on the recorded game build |
| Combat event v2 and replay aggregation | Implemented and tested |
| Mana and shield observation bridge | Contract-ready; runtime hooks pending |
| Main toolbox and external combat HUD | Local transport and bridge candidate implemented; game runtime test pending |
| MOD management | One attributed external trainer registered; user-supplied exact file required |

Research results are scoped to the game build recorded in the Chinese plan. A game update can invalidate hook compatibility and must be revalidated.

## Development

Requirements: Windows, Python 3.13, and the packages in `requirements-dev.txt`.

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
py -3 keyview.py --demo-large-values --show-page combat --window-size 780x560 --tk-scaling 1.5
py -3 keyview.py --demo-large-values --show-page combat --show-combat-hud --demo-scenario CastleBridge --demo-room-index 100
```

Build the Windows package:

```powershell
.\build.ps1
```

The temporary BepInEx probe has separate instructions in [`game_plugins/LC2DamageProbe/README.zh-CN.md`](game_plugins/LC2DamageProbe/README.zh-CN.md). It is research instrumentation, not the final HUD bridge.

The MOD page includes Soul Stone Trainer 1.2 by community author **恨你不见**, with configure, launch, and local-copy removal controls. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Safety and scope

- The overlay reads Windows key state and does not inject into the game.
- Macros send only user-configured input while `LostCastle2.exe` is foreground, and stop on focus loss or `Ctrl + Shift + F12`.
- The research probe observes resolved combat state. It does not modify damage, drops, saves, or network state.
- Third-party tools do not inherit that read-only guarantee; the toolbox only verifies, copies, and explicitly launches the pinned file.
- Game binaries, generated interop assemblies, logs, screenshots, local configuration, and packaged builds are intentionally excluded from Git.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).

## License and disclaimer

Project source code is available under the [MIT License](LICENSE). Game code, assets, names, trademarks, and third-party tools are not covered by this license.

This is an unofficial fan project and is not affiliated with or endorsed by Hunter Studio, Another Indie, or the game's publishers. Users must provide their own legitimate game installation.
