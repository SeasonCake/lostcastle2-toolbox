# 受管 MOD 单一运行时与最小载荷审计

- 生命周期：`STATIC/PACKAGE SHAPE VERIFIED / THIRD-PARTY GAMEPLAY NOT RUN`。
- 范围：当前 53 个社区条目、43 个唯一来源、54 个最终载荷文件。
- 最终社区载荷：3,391,437 B；精确包内逐文件哈希由 `assets/community_mod_catalog.json` 固定。
- 18 个条目使用显式成员选择；其余由同一静态识别器选取最小可安装载荷。
- 生成目录与精确包社区目录均未发现 `winhttp.dll`、`doorstop_config.ini`、`coreclr.dll`、`.cfg`、cache、interop、dotnet 或 BepInEx 框架路径。

统一合同：工具箱只维护一套固定 BepInEx 6 IL2CPP/Unity 运行时。社区 MOD 只携带自己的 DLL 与必要资源；生成配置由插件首次运行创建，不从来源包覆盖。检测到整套框架/游戏覆盖文件时，普通 MOD 自动添加继续 fail closed，不为省体积放宽安全门。

## 十 MiB 以上本地来源

| 来源 | 大小 | 当前处理 |
| --- | ---: | --- |
| `LostCastle2SoulStoneTrainer v1.1.exe` | 242,314,025 B | 旧版且更大，不纳入 |
| `LostCastle2SoulStoneTrainer v1.2.exe` | 72,428,059 B | 独立 EXE，不是 BepInEx；按原身份单独随包，不能按插件 DLL 裁剪 |
| 两个默认 7 人整包 | 各 40,237,762 B | 两包逐字节相同；只纳入 15,872 B `LostCastle2MaxPlayers16.dll`，排除重复框架、cache 与生成 cfg |
| `LC2增强计划 V4.7.7z` | 34,438,982 B | 旧版完整安装包，不纳入；当前使用 4.8 来源并只选 328,192 B 功能 DLL |
| `LC2增强计划v3.3.0及完整安装教程.zip` | 34,432,718 B | 旧版，不纳入 |
| `模组前置BepInEx-...zip` | 34,335,572 B | 纯前置参考，不作为 MOD；工具箱固定运行时替代 |
| `失落城堡mod前置.zip` | 34,325,481 B | 整包前置，不作为 MOD |

精确包只保留一份 `bepinex-runtime.zip`（40,402,401 B）和一份 `LC2CombatBridge.dll`（52,736 B）；社区 MOD 不再各带运行时。受管载荷中最大的是 `item-ban-freenix` 的独立功能 DLL 1,715,712 B，不是框架重复。

准备回执为 `artifacts/community-mod-preparation-2026-08-30.json`，记录每个条目的来源大小、选择模式、载荷文件数与字节数。真实第三方游戏行为、组合兼容与 7–16 人云端建房仍不由本体积审计外推为 PASS。
