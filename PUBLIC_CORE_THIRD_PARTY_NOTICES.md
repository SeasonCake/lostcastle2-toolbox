# public-core third-party notices

This notice applies to the publicly distributable `public-core` asset. Third-party tools and MODs listed in the UI are not covered by the repository's MIT License.

## Explicit public-core exclusions

The public-core asset does **not** contain the Soul Stone Trainer, Gold Editor, or any of the curated community MOD DLL/resource payloads. Their catalog metadata remains available so a user who obtained an original package independently can select an exact matching file or extracted directory; size and SHA-256 validation still fail closed. Catalog presence, author attribution, a community upload, or local testing does not assert redistribution permission.

The local maintainer test package is a separate non-public artifact and must not be uploaded to GitHub or sent to a QQ group.

## 7-Zip command-line components

- 7-Zip Copyright (C) 1999-2025 Igor Pavlov.
- Included files: `7z.exe` (575,488 bytes, SHA-256 `4CD7D776C686427226A151789D2D61F0B2ED2C392148CC4E69C0238362FAFECF`) and `7z.dll` (1,906,176 bytes, SHA-256 `5BD20FB38499D95C39594F41D4781B6181B3304B7F1F4D06B0182F514E7EAA74`).
- The complete upstream `License.txt` is included beside those files and governs their redistribution, including its LGPL, BSD and unRAR terms.
- Upstream source release: <https://github.com/ip7z/7zip/releases/tag/25.01>.

The toolbox uses these components only to inspect user-selected ZIP, 7Z and RAR packages.

## Official BepInEx Unity IL2CPP runtime

- Official artifact: `BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip`.
- Official download: <https://builds.bepinex.dev/projects/bepinex_be/785/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785%2B6abdba4.zip>.
- Identity: 34,335,572 bytes; SHA-256 `2A7CBF74D26ABE4765C3E662DB1721B923BAC39849EBFEF2CA5DC7DE7E2D9B7F`.
- Corresponding BepInEx source: <https://github.com/BepInEx/BepInEx/tree/6abdba47eeebe08552282e7a58ef0f4a9ab60b62>.
- BepInEx is LGPL-2.1. The complete license is included as `运行环境/public-core/BepInEx-LICENSE.txt`.
- The exact build script identifies UnityDoorstop 4.5.0, Dobby 1.0.5 and the BepInEx .NET runtime 6.0.7 as downloaded build inputs.
- UnityDoorstop 4.5.0 is LGPL-2.1; source and exact license are included/linked under `运行环境/public-core`.
- Dobby 1.0.5 is Apache-2.0; source and exact license are included/linked under `运行环境/public-core`.
- The BepInEx .NET runtime 6.0.7 is based on .NET and licensed under MIT. Its exact `LICENSE.TXT`, `PATENTS.TXT` and `THIRD-PARTY-NOTICES.TXT` from source revision `e10df43` are included under `运行环境/public-core`; source/release: <https://github.com/BepInEx/dotnet-runtime/releases/tag/6.0.7>.

The public-core bundle uses the official BepInEx ZIP bytes, not the older 307-file `validated_game_runtime` snapshot. It excludes pre-generated Unity base libraries, generated interop, caches and plugins. BepInEx may download/generate compatible Unity libraries and interop locally on first game launch; those local products are not part of the public asset.

## LC2 Combat Bridge

LC2 Combat Bridge is part of this repository and is distributed under the repository MIT License. It is packaged separately from BepInEx and installed only into its dedicated plugin directory.
