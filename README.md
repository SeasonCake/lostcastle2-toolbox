# Lost Castle 2 Toolbox

[简体中文](README.zh-CN.md)

An unofficial, open-source Windows toolbox for *Lost Castle 2*.

The repository currently contains:

- a customizable keyboard/mouse input overlay;
- opt-in, foreground-only input macros with a global emergency stop;
- a read-only combat bridge;
- versioned contracts and a replayable aggregator for damage, healing, mana, effects, and shields;
- separate maintenance and distribution profiles: the diagnostic candidate can pause/export anonymous per-event evidence, while the distribution build keeps only in-memory current-match state and resets it at explicit session boundaries;
- a managed entry point for attributed third-party tools.
- dedicated team status, loadout, and LC Enhancement Plan pages; loadout changes require manual confirmation in camp.

The application now starts in a calculator-style main toolbox window. It manages the keyboard overlay, macros, and a compact combat HUD; full combat details live in the main window. The v2 event contract keeps game observation, aggregation, and presentation separate so new items normally require a source-registry entry instead of new UI logic.

On a clean game installation, the first toolbox game launch offers an explicit one-click setup for the pinned BepInEx runtime and the read-only combat Bridge. No community MOD is enabled automatically, the BepInEx console is disabled by default, and a different existing BepInEx core is never overwritten silently.

## Download

Current stable release: [v1.9.0](https://github.com/SeasonCake/lostcastle2-toolbox/releases/tag/v1.9.0). See the [v1.9.0 release notes](docs/LC2_1.9.0_RELEASE_NOTES.zh-CN.md) for changes, verification, and known limits.

Version 1.9.0 catalogs 84 community MODs (12 additions and 8 upgrades), adds team status, loadout and LC Enhancement Plan pages, and provides a translucent team mini window directly from the HUD. It includes a brighter warm theme, display-aware fonts and MOD columns, hover support links, background MOD status scanning, and backed-up updates for an existing BepInEx installation.

Damage taken, healing, and mana counter changes remain deferred. New MOD gameplay, all loadout combinations and all multiplayer configurations have not been fully tested.

First game launch requires online retrieval or generation of Unity compatibility files; the actual public-core first-game launch and network path were not revalidated for this release.

The GitHub Release provides a Windows x64 `public-core` package. It contains the toolbox, the official BepInEx artifact, the project-owned Bridge and team/loadout component, and public MOD catalog metadata, but excludes the third-party Soul Stone Trainer, Gold Editor, and community MOD binary/resource payloads. Users can provide packages they obtained independently and let the toolbox verify them against the catalog. The separately distributed Chinese community bundle is not byte-identical to the GitHub asset.

## Project status

| Area | Status |
| --- | --- |
| Key overlay | Available |
| Foreground-only macros | Available, disabled by default |
| Damage and HP semantics | Runtime-validated on the recorded game build |
| Combat event v2 and replay aggregation | Implemented and tested |
| Mana and shield observation bridge | Mana spend/recovery runtime-validated; shield samples still pending |
| Main toolbox and external combat HUD | Toolbox 1.7.6 / Bridge 1.7.4 labels the compact HUD **realtime** and keeps skip diagnostics off that surface. The detailed page explains **realtime estimate / settlement may correct**. DPS prefers complete live cumulative deltas and falls back to hit events. A process-first mid-run join may restore damage and boss damage from a complete nonzero live vector without creating a DPS spike, while in-run taken damage keeps the validated hit-event path. A one-player settlement UI record may finalize damage, boss damage, and taken damage only after the identity gate accepts it; the trusted UI boundary still ends an estimated session when that record is unavailable |
| MOD management | 1.9.0 catalogs two existing tools plus 84 community MODs. The local community bundle uses 90 functional payload files; GitHub public-core ships metadata only and requires user-supplied original packages. Hash-bound superseded payloads are removed during an upgrade while modified or unknown files are preserved |

Research results are scoped to the game build recorded in the Chinese plan. A game update can invalidate hook compatibility and must be revalidated.

## Combat data contract

- During a match, the compact HUD labels per-player damage and Boss damage **realtime**. The detailed page says **realtime estimate** and explains that settlement may correct it. The values use verified in-game process data, but are not promised to equal the later result screen.
- Only complete per-player records from multiplayer network SyncEnd or the guarded one-player settlement UI are labelled **official settlement**. They replace the estimate as-is and may move a player's value up or down. On the first session in a game process, a complete nonzero live vector may restore a continued run's existing totals, while the first sample only establishes the DPS baseline. Recent DPS starts from later positive deltas, adds only the hit tail after the latest live anchor, and falls back to hit events when live totals are unavailable.
- A recoverable event-skip warning is maintenance information. It appears only on the detailed page for the current and immediately following room, then clears if no new skip occurs; the compact HUD does not show it.
- `Diagnostic` is the default local maintenance profile. Its detailed page can pause/resume recording and export an anonymous per-event archive capped at 128 MiB per match. `Distribution` is built only for an explicitly selected release: it exposes no recorder controls, creates no desktop match archive, and keeps current-match state in memory. Neither profile records player names, platform accounts, or chat.

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

Build the Windows package (diagnostic maintenance is the default; select the distribution profile only for an explicit release):

```powershell
.\build.ps1 -BuildProfile Diagnostic
.\build.ps1 -BuildProfile Distribution
```

To preserve earlier packages and build outputs, pass `-OutputRoot` to either build script with a new directory inside the project, for example `-OutputRoot artifacts/release/v1.7.7-community`. Existing destinations and paths outside the project are rejected. Use PowerShell 7 for this option.

The pinned 7-Zip runtime and its license are included so source-mode archive inspection works after cloning. Other third-party executables, DLLs, archives, and the generated `third_party/community_mods` payload are intentionally excluded from Git. Before packaging, provision the exact local files recorded in `THIRD_PARTY_NOTICES.md` and `assets/community_mod_catalog.json`; `build.ps1` verifies their counts, sizes, and SHA-256 identities and stops if an input is missing or different.

The temporary BepInEx probe has separate instructions in [`game_plugins/LC2DamageProbe/README.zh-CN.md`](game_plugins/LC2DamageProbe/README.zh-CN.md). It is research instrumentation, not the final HUD bridge.

The current 1.9.0 source catalog contains the two original tools and 84 curated community MOD entries: 12 additions and 8 upgrades, with 90 functional payload files totaling 5,162,445 bytes. Functional categories, search and installation filters share a background status scan. Generated config, cache, interop, Doorstop, source-package contact details and duplicate core files are excluded. Original authors and exact identities remain in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the catalogs.

The home page, MOD page and bottom-left `支持我们` entries display the WeChat code on hover; clicking opens the local WeChat, Alipay and explanation folder. The footer also links to GitHub and the maintainer's [Bilibili space](https://space.bilibili.com/88048665?). Support is voluntary.

## Safety and scope

- The overlay reads Windows key state and does not inject into the game.
- Macros send only user-configured input while `LostCastle2.exe` is foreground, and stop on focus loss or `Ctrl + Shift + F12`.
- The research probe observes resolved combat state. It does not modify damage, drops, saves, or network state.
- Third-party tools do not inherit that read-only guarantee; the toolbox verifies pinned files and performs only the registered managed copy, install, uninstall, or explicit launch action.
- Team and loadout snapshots stay local. Confirmed loadout actions alter the current local character in camp; gems use the game's own save path. These actions are separate from the read-only combat bridge.
- Game binaries, generated interop assemblies, logs, screenshots, local configuration, and packaged builds are intentionally excluded from Git.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and [`SECURITY.md`](SECURITY.md).

## License and disclaimer

Project source code is available under the [MIT License](LICENSE). Game code, assets, names, trademarks, and third-party tools are not covered by this license.

This is an unofficial fan project and is not affiliated with or endorsed by Hunter Studio, Another Indie, or the game's publishers. Users must provide their own legitimate game installation.
