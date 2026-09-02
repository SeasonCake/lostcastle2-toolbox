# Third-party notices

Third-party tools listed by Lost Castle 2 Toolbox are not covered by this repository's MIT License.

## 灵魂石修改器 1.2

- Author attribution: **恨你不见**.
- Attribution evidence: the supplied executable's embedded window title says `bilibili：恨你不见`; the project maintainer independently identified the same community nickname.
- Registered file: `LostCastle2SoulStoneTrainer v1.2.exe`, 72,428,059 bytes, SHA-256 `025FB6CD01E79F9F2D8018BA9BF4FF592DE43EF2A7EDFD2E7A22F3C1842DF645`.
- Version evidence: the filename and outer window title say `1.2`, while the embedded core identifies itself as `v5.0`; the fixed SHA-256 above is the authoritative file identity.
- Observed form: unsigned PyInstaller executable using Frida IL2CPP injection, with features that can change game memory, resources, and achievements.
- Embedded notice: free sharing; resale, commercial use, and repackaging for sale are prohibited.
- Redistribution status: the maintainer confirmed the author approved inclusion in the free public package on 2026-08-27. Attribution remains required; resale and commercial use remain prohibited.

The packaged binary is pinned to the exact size and SHA-256 above. The toolbox configures a local copy and requires explicit confirmation before launch.

## 金币编辑器 1.0

- Author attribution: **刺心**.
- Attribution evidence: the plugin's embedded window title and load log identify `v1.0 by 刺心`.
- Registered DLL: `LC2GoldFree.dll`, 9,216 bytes, SHA-256 `BB6FF96AA4AF9BB3521ED93C3A5582E48D5D9CB8C7BAAF5291FA4C3E57647B56`.
- Registered original archive: `F5金币编辑器.7z`, 4,136 bytes, SHA-256 `7DFB39A521C1135584D9D88FC6138CFA0F8AF017F952924C141F189EDA7A294B`.
- Observed form: unsigned BepInEx IL2CPP plugin that reads, changes, and saves in-game gold.
- Packaging status: the maintainer selected the exact registered DLL for inclusion in the local toolbox package on 2026-08-28. This does not claim separate public redistribution permission.

The toolbox verifies the bundled DLL, installs it into a dedicated BepInEx plugin directory, and removes only that catalog-owned file during uninstall. The source archive remains outside the package.

## Curated community MOD bundle

- The v1.7 bundle contains 56 maintainer-selected community MOD entries through 2026-09-01. The latest intake adds Monster Treasure 11, Nightfall Bow Boost 1.1.0, and Reinforcement Transmitter: Lost Swordsman Shadow 1.0.0, and updates Reaper Summon from the Summon Master 2.1 source package. Five other DLLs selected from that package are byte-identical to their existing payloads and are not represented as functional upgrades. Max Players 1.3.0 by 梦羽 remains the exact 15,872-byte `LostCastle2MaxPlayers16.dll`; the source package's duplicated runtime and generated files remain excluded.
- Exact payload paths, sizes, SHA-256 values, displayed authors, versions, purposes, and usage guidance are recorded in `assets/community_mod_catalog.json`; source-package selection and attribution evidence are maintained in `assets/community_mod_sources.json`.
- Strong embedded or source-level author evidence takes priority. Where that is absent, maintainer-supplied QQ upload screenshots may provide a provisional uploader attribution; otherwise the entry displays `社区未署名`. Monster Treasure embeds `作者 懒虫桑`; Nightfall Bow Boost has no embedded author and therefore displays QQ uploader 兔子王お provisionally. The new `LC2.ReinforceHideyoshi` payload identifies its behavior as summoning a Lost Swordsman Shadow from the Reinforcement Transmitter, despite conflicting source-package text, and its usage guidance warns that it observes the same item as the existing Thunder Spirit entry. Older duplicates, test builds, unfinished or half-finished sources, and superseded sources explicitly marked as having a bug are not in the default bundle.
- These MODs are not covered by this repository's MIT License. On 2026-09-02, the project maintainer authorized the current registered community payload set for inclusion and community distribution in the free public toolbox after coordinating with group management, which includes authors of part of the set. Per-entry provenance, author evidence and payload hashes remain recorded in the catalog.

The toolbox installs every entry into an independent BepInEx plugin directory, verifies all registered payload files, prevents simultaneous installation of entries that provide the same DLL name, and removes only registered files during uninstall. The 56 entries contain 57 functional payload files totaling 3,522,509 bytes and share the single pinned runtime below; generated `.cfg`, caches, interop, Doorstop, and duplicate BepInEx core files are excluded.

## 7-Zip command-line components

- 7-Zip Copyright (C) 1999-2025 Igor Pavlov.
- Bundled files: `7z.exe` (575,488 bytes, SHA-256 `4CD7D776C686427226A151789D2D61F0B2ED2C392148CC4E69C0238362FAFECF`) and `7z.dll` (1,906,176 bytes, SHA-256 `5BD20FB38499D95C39594F41D4781B6181B3304B7F1F4D06B0182F514E7EAA74`).
- The complete upstream `License.txt` is included beside those files in the package and governs their use and redistribution.

The toolbox uses these components only to list and read user-selected ZIP, 7Z, and RAR packages during static MOD identification.

## BepInEx 6 IL2CPP runtime

- Project: <https://github.com/BepInEx/BepInEx>.
- Bundled identity: `6.0.0-be.785+6abdba47eeebe08552282e7a58ef0f4a9ab60b62`. Published v1.6.2 paired it with Bridge 0.4.12; v1.7 pairs the same pinned runtime with Bridge 1.7.0.
- Prepared runtime archive: `bepinex-runtime.zip`, 40,402,401 bytes, SHA-256 `0B617BC439F53E39680444F1EFD84C2B31A96D144D3267EE06EBEA05B59738A8`.
- The prepared archive contains 307 runtime/config files and explicitly excludes `BepInEx/plugins`, caches, generated interop, the source package's multiplayer plugin, and every research/debug probe. The toolbox installs only the separately pinned LC2 Combat Bridge into the plugin directory.
- BepInEx is licensed under LGPL-2.1. The complete license is bundled as `运行环境/BepInEx-LICENSE.txt`; the matching source revision is linked in `运行环境/README.txt`.

First-use setup is explicit and writes only to the selected Lost Castle 2 directory while the exact game process is stopped. The BepInEx console is disabled in the managed default configuration; disk logging remains available for diagnostics. Existing differing BepInEx core files fail closed and are not overwritten.
