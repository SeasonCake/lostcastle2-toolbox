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
- Redistribution status: local user-supplied only. Neither the DLL nor its archive is included in the toolbox package.

The toolbox accepts only the registered DLL or original archive, verifies the extracted DLL, installs it into a dedicated BepInEx plugin directory, and removes only that catalog-owned file during uninstall.
