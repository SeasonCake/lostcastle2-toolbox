# 失落城堡2工具箱 1.7.4 结算、承伤与发布准备回执

> lifecycle: `source-and-package-pass / real-1.7.4-final-not-run / local-share-ready / github-release-prepared`
>
> recorded: `2026-09-03 Asia/Shanghai`

## 判定

- 1.7.4 源码、双构建档、public-core、隐私边界、空白运行时安装和本地分享包均通过离线/包形门。
- 1.7.4 的单人结算 UI 显式 record、最终承伤覆盖和 `session_ended` 组合路径已由源码链、互操作类型与合成端到端归档正控闭合；本版本尚未再跑真实游戏终局，因此真实运行状态明确为 `NOT RUN`，不冒充实战 PASS。
- 正式群分享目录与 UTF-8 ZIP 已准备在 `<desktop>`；GitHub public-core 资产已完成本地冻结，外部 commit、push、tag、Release 与上传将在独立发布阶段记录。

## 源码身份

- 工作分支为 `main`，本轮开始时 HEAD 为 `b228472c6027838ea1568e5881f4f965b4937c7a`。
- `<repo>` 是含既有维护改动与历史证据的共享脏工作树；本回执记录的是当前源码与本地产物身份，不宣称干净 checkout，也没有暂存或提交任何路径。

## 字段与结算链

- 互操作程序集确认 `AdventureRecordPlayerData` 有确定字段：`mDamageValue`、`mBossDamageValue`、`mTakeDamageValue`。
- 原生调用链为 `CollectSettlementData -> GameSettlementUI._selfPlayerData -> UpdateSettlementInfo(_selfPlayerData)`；`UpdateSettlementInfo(__0)` 是当前单人结算最强的最终数据源，`SetSettlementData` postfix 的 `_selfPlayerData` 是同一调用链的后备源。
- r5 已命中结算 UI prefix/postfix，但只查询最终 save-list，没有读取 UI 直接传入的 record；当时 active 值完整而 save-list 不可用，所以没有接受 official，也没有产生 `session_ended`。
- 1.7.4 直接校验 UI record：活动会话、已知队伍恰为本机单人、HMAC 身份匹配、record 槽位一致、三项数值非负且 Boss 不大于总伤害。完整时冻结官方伤害/Boss/承伤并结束会话；可信 UI 结束回调若缺官方 record，则保留最后实时估算并只结束会话，不伪造“官方”。
- `GameOverEnd_Offline` prefix 只记录边界，不在过早阶段读取可能为空或陈旧的 `_selfPlayerData`。
- `mTakeDamageValue` 只作为最终结算覆盖，允许向上或向下校正逐击承伤；不新增实时承伤累计，避免房间回滚/重进把旧尝试带入当前官方结果。

## 历史大包检索

- 并行扫描 92 个诊断 ZIP：完整官方伤害+Boss 为 2，含 `session_ended` 为 77，automatic 为 77，三者交集为 0。
- 历史包存在独立的 `session_ended`/automatic 正控，也存在官方伤害/Boss正控，但没有一份真实样本同时闭合官方三字段、`session_ended` 与 automatic ZIP。
- 历史运行日志/归档没有序列化 `mTakeDamageValue` 或 `official_taken_damage`；最终承伤接入有类型与调用链证据，但仍需下一版本/后续实战补真实正控。

## 检查结果

- Bridge/Python 聚焦回归：181 tests PASS。
- 当前源码全量：338 tests PASS；最终 public-core 实际构建也重新运行 338 tests PASS。
- Diagnostic 初次构建运行 327 tests PASS；新增群友文案门后，最终 Distribution 原生重构建运行 328 tests PASS。两档 C# Release 编译均为 0 warning / 0 error。
- 合成端到端正控同时包含三项官方 final、`session_ended` 和单个 automatic ZIP；负控覆盖非法承伤、身份/槽位冲突、Boss 大于总伤害、过早 offline prefix 与缺失 record。
- 60 个社区 MOD 的包形安装/卸载全部通过；无 BepInEx 的首次与重复初始化为 ready，冲突 core 在写盘前拒绝。

## 冻结产物

| 产物 | 文件 / 字节 | EXE SHA-256 | Bridge SHA-256 |
| --- | ---: | --- | --- |
| Diagnostic r6 | 1,770 / 167,021,037 | `BB2FC8505D43025E61A5B6F4CEC253A566941DEF8EF4228F685A687F135E4642` | `8047D2B7DBA8E52E1129FD3C61B1736639556F00ECD9A3C4FF2D2A33467E4CCF` |
| Distribution 群分享 | 1,770 / 167,021,045 | `F881D79879A7A80C3BD198B47E0AA3BAA1372B29E0A4911E83DA9663B4028660` | `190B8B4A8C661C73A32ADF15DF56487E57473E591BFA25520D172A7E188E7DED` |
| public-core | 1,712 / 84,931,341 | `1C6DB28BC8D86A87FE9B2C26DC260128B229B52B03EE3ED7F275DF96899364C9` | `190B8B4A8C661C73A32ADF15DF56487E57473E591BFA25520D172A7E188E7DED` |

- 三包 EXE FileVersion/ProductVersion 均为 1.7.4，包内 profile/manifest/Bridge 身份交叉一致，self-test exit 0。
- Distribution 与 public-core 均为 `distribution`：诊断入口、Bridge 高频诊断和默认逐局记录全部为 false；`exports` 不存在。
- 三包二进制全扫描对维护者精确个人目录、工程根、截图/剪贴板名均为 0 命中；日志、PDB、partial、截图和 runtime-captures 为 0。部分上游依赖/社区 DLL 自带其构建环境的通用用户目录片段，不包含维护者的目录或工程身份。
- public-core 只带官方固定 BepInEx 运行时、1.7.4 Distribution Bridge、7-Zip 运行依赖和公开 catalog；不带本地第三方 MOD 二进制。
- 群分享根说明仅保留启动、HUD含义、重进、MOD安装和“不保存逐事件对局明细”等用户操作；`rxx`、探针、导出按钮与记录上限只留在仓库维护文档。
- `<desktop>/失落城堡2工具箱1.7.4-实时数值监测+一键MOD安装` 与冻结 Distribution 逐文件 SHA-256 一致。
- `<desktop>/失落城堡2工具箱1.7.4-实时数值监测+一键MOD安装.zip`：1,770 文件，未压缩 167,021,045 B，ZIP 137,406,593 B，所有条目位于同名顶层目录且中文名为 UTF-8；逐文件 SHA-256 与同名目录一致，ZIP SHA-256 `8905A9DE49215B65E42F750DE396853C79A067D33696F343410C1140962CF7C5`。
- GitHub public-core 资产 `LostCastle2Toolbox-v1.7.4-public-core-windows-x64.zip`：58,012,289 B，1,712 文件逐文件一致，SHA-256 `B68160E15EB917E14B9C448B2F82C678005D6E493978DCD799A6ECB5A0D2A4C4`；外部上传/下载回读在发布后补记。

## 仍未运行

- 1.7.4 的单人自然胜利、最终死亡、主动结束和 Alt+F4 后终局实测；所以 `official_taken_damage`、真实 `session_ended` 与 automatic ZIP 的同局闭环仍是 `NOT RUN`。
- 1.7.4 真实多人结算、再次跨进程重进、下一局清理，以及新增/更新 MOD 的真实游戏效果和组合兼容。
- commit、push、tag、GitHub Release、远端下载回读与群分享。
