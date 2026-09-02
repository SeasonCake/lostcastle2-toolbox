# LC2 工作 6 交接

> 历史快照：工作6交接已完成，以下运行身份和开放门不表示当前状态；当前行为以正式 v1.7 源码与发布说明为准。

> 冻结时间：2026-08-30 16:02:51 +08:00。此文件是 successor 的当前短入口；历史细节按链接查阅，不重放长聊天。开始工作前重新读取最近 `AGENTS.md`、`git status`、进程与实时日志，本文中的运行状态是时间点证据，不是永久真相。

## 1. 角色、目标与当前阶段

- 角色：接替“LC2 工作 5”完成失落城堡 2 工具箱下一候选收口。
- 用户最终目标仍是：修完并实测 Bridge、加入新增 MOD、完成 UI/排序与说明、冻结新包，随后只派一个不同 owner 综合审计；通过后再整体 commit、push、压缩包与 GitHub Release。用户尚未把任何版本分享给群友。
- 当前立即阶段不是打包/推送，而是解决 `0.4.7` 结算补满误计并完成最短实机回归；不要把仍在移动的 dirty tree 交给并发 auditor。
- 用户最后追加两个 MOD，要求按实际用途排序：`LC2PurpleDamage暴击字体红色改紫色.dll` 与 `LC2HexAugment.dll`。它们尚未进入 catalog。

## 2. 仓库与发布基线

- 项目：`<repo>`。
- 分支：`main`；HEAD `3d6767794be7b88da3e08e7ef62b444b1658a5ee`；`origin/main` 同步；HEAD tag `v1.6.0`；remote `https://github.com/SeasonCake/lostcastle2-toolbox.git`。
- v1.6.0 是已冻结 Git/Release 基线，但用户尚未向群友分发。当前全部工作是其后的未提交候选，不能回写为“v1.6.0 已含”。
- 冻结时 tracked 修改 15 个：README EN/ZH、notice、两个社区 MOD JSON、build、三个 docs、Bridge source/README、三个 tests、`toolbox/app_shell.py`。
- 未跟踪证据/候选根包含：
  - `artifacts/runtime-captures/2026-08-30-cursed-watch-mp-gap-0.4.5/`
  - `artifacts/runtime-captures/2026-08-30-hp-official-vs-actual-0.4.6/`
  - `artifacts/runtime-captures/2026-08-30-hp-result-jump-0.4.7/`
  - `artifacts/runtime-captures/2026-08-30-mana-capacity-closure-0.4.6/`
  - `artifacts/runtime-captures/2026-08-30-no-watch-selfheal-finished-0.4.5/`
  - `artifacts/runtime-deploy/2026-08-30-bridge-0.4.6/`
  - `artifacts/runtime-deploy/2026-08-30-bridge-0.4.7/`
- 不得 `git add -A`；提交前按 owned paths 显式 stage，并复查共享树。

## 3. 当前运行与部署身份（冻结时）

- 冻结时游戏正在运行，exact path `<game>/LostCastle2.exe`。
- 冻结时测试盒子正在运行，exact path `<desktop>/失落城堡2工具箱 1.6.0-Bridge0.4.6测试版/失落城堡2工具箱.exe`。
- 目录名虽仍写 0.4.6，但内部 manifest 是 `LC2CombatBridge 0.4.7-test`。
- 游戏目录和测试盒子内置 Bridge 均为 48,640 B / SHA-256 `A917E813DC66D1A2737138905DC324CDF9939C1A5A119556D3442F3ACBC18CA7`。
- 0.4.6 回滚：47,616 B / `7DFF32538C1D40015912D0D6C07A6EDF11A9D4E1E571EEEAF496ECD1AF5C98B4`，在 `artifacts/runtime-deploy/2026-08-30-bridge-0.4.7/`。
- 冻结时进程非零：successor 不得部署、替换或运行盒子 self-test；等用户明确关闭后重新做 exact name + `ExecutablePath` 连续双零门。

## 4. Bridge 0.4.6/0.4.7 已闭合与未闭合

### 已闭合

- 0.4.6 修复通用 MP fallback 的零请求/零净变化提前返回；不增加 Hook。普通回蓝、被诅咒怀表、魔晶石容量 `+80+9` 与分解负控已闭合。
- 0.4.7 在同一 RoundStart target 增加 Prefix，受击路径增加 `[LC2CB-TAKEN] original/real/hp_before/applied/settlement`，HP 日志增加负向、`in_map` 与 `inside_damage`。Harmony target 仍 14。
- 0.4.7：聚焦 11 项 PASS；Python 全量 167 项 PASS；隔离 SDK 6.0.428 Release 构建 0 warning/0 error；Mono.Cecil 回读版本/Prefix/Postfix/诊断/14 target PASS；测试盒 self-test exit 0。

### 0.4.7 本局决定性证据

- 冻结记录：`artifacts/runtime-captures/2026-08-30-hp-result-jump-0.4.7/README.zh-CN.md`。
- 三次受击：
  - official raw `36.1267204 / 46.9647331 / 36.1267204`；逐击 ceil `37+47+37=121`。
  - real/applied `37.9330559 + 46.4950867 + 34.6816521 = 119.1097946`。
  - 局内有效正向 HP 也精确为 `119.1097946`，UI 显示119。
- 判定：`承伤121 / 回复119` 是官方逐击入整/处理阶段与实际 HP 浮点变化的口径差，不是漏算。不要再为这约2点改聚合公式。
- 结算补满仍 `R-FAIL`：日志第608行 `54.6000023→156`，有效 `101.3999939`，仍 `in_map=True`；第609行才触发 camp RoundStart。故 0.4.7 Prefix 仍太晚。总恢复 `119.1097946+101.3999939=220.5097885`，UI 显示221。

### 下一最窄问题

- 必须排除结算/回营补满，但不能按请求值、满血形态、Boss 名、装备或道具名特判。
- 当前诊断未写 `changeSourceStr/source_token`。优先：
  1. 静态确认导致第608行补满的调用/来源；或
  2. 只在既有 HP hook 日志增加有界来源 token，再做一次最短退出测试；或
  3. 找到补满前已有且稳定的生命周期入口，替换/复用现有 target。没有签名/时序证据前不新增 Hook。
- `RoomBattleData_RoomEnd` 与 `OnGameRoundEnd` 在本局 BepInEx 日志里没有提供补满前边界，不得假设它们已触发。

## 5. 当前 MOD/UI 候选

- 已在 dirty source 候选加入：
  - `纵冰之杖加强 1.16.0`，IcePillarCrash DLL 47,104 B / `F4C53E57…D6253D`，上传者署名“大萝卜鸡”。
  - `我不是药神（测试版）1.0.0`，DLL 84,480 B / `B4D6DF01…AC8B37`，上传者署名“木亦”；F1 与三个现有 MOD 冲突，说明已提示不要同时启用。
- 社区 catalog 当前 dirty 候选：51 条目、52 载荷、3,361,741 B；`build.ps1` 期望载荷52；MOD manager 聚焦20项 PASS。
- `LC2 增强计划` 优先级已从180提到110，排在玩家实时属性之后；内建灵魂石/金币仍在社区 MOD 前。
- MOD 表作者列标题/内容已居中；app shell 聚焦28项此前 PASS，尚未启动 actual UI 验收。
- 待加入的新 DLL 位于 `<local-mod-library>`：
  - `LC2PurpleDamage暴击字体红色改紫色.dll`：13,824 B / SHA-256 `5863D6A9346304C418C731F73AF0E0413AAAE1FEBD569065697B9CBDC035EECB`；截图上传者“兔子王お”。预期纯视觉，通常排功能 MOD 后，仍需静态确认版本/作者/载荷/冲突。
  - `LC2HexAugment.dll`：40,960 B / SHA-256 `50CEB677DE7AB88D8E4E4FD8059CEA5FBC440D709DAA7E4A215B059938E04ECC`；截图上传者“笑”。需要优先确认具体功能、面板按键及与现有 F1/Hex 类 MOD 冲突，再决定实战排序。
- 第三方 DLL 不进入 Git；只进入本地打包 payload，Git 只记录 catalog/source identity/notice。不要执行新 DLL 来猜功能，先静态检查。

## 6. 产品与发布边界

- 用户已批准后续：完成测试后做新包、整体 commit/push、压缩包和 Release；但当前 Bridge 有确认 R-FAIL，不得提前执行这些外部阶段。
- 最终包名称需简短明确包含“实时数值监测、一键 MOD 安装”等核心用途。
- 盒子对全新环境必须能安装运行 BepInEx/Bridge/HUD，启动游戏不得弹调试控制台；这些已有测试合同，但 exact 1.6.x 冻结包仍需 fresh/package 验收。
- 多人真实联机、第三方 MOD 实际游戏逻辑目前仍是 `NOT RUN`，不能写成 PASS。
- exact source/package/EXE/UI receipts/owned inventory 冻结后，只派一个 different-owner 综合审计席位；范围沿用阶段观察：Git/fresh clone、source/package/desktop/ZIP/EXE/Bridge/MOD identity、UI DPI/最小窗/四按钮、第三方二进制边界。不要重复 0.4.5 单人闭合样本，不新增保护工程或无关发布门。

## 7. Successor 开始顺序

1. 读取本交接、最近 AGENTS、0.4.7 capture README；重新执行 `git status`、进程/路径和部署哈希检查。
2. 当前游戏/盒子若仍运行，只读分析日志和两个新 DLL；不要写游戏/测试盒目录。
3. 先收敛结算补满边界，做源码/测试/build；用户关闭后双零部署。下一实测只需一次有缺血的短局退出，不必再打完整 Boss 长局。
4. 静态分析并加入两个新 MOD，更新 catalog/sources/notices/inventory/README/build count/tests，按实战价值和冲突风险排序。
5. Bridge 真实 PASS 后冻结 exact package/UI，执行一次不同 owner 综合审计；再根据审计结论打包、显式 stage/commit/push/Release。
6. 不重做已经闭合的 MP、三击官方/实际伤害公式、0.4.5/0.4.6 长局；证据冲突时先对齐版本、session、字段口径和调用时序。
