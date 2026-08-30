# LC2 当前检查点（2026-08-30，Asia/Shanghai）

## 角色、目标与阶段

- 当前角色：LC2 工具箱下一候选 Bridge/MOD/UI 收口负责人。
- 当前目标：修复回营补满误计，保持官方承伤121/实际HP变化119双口径；静态纳管新增 MOD，实机通过后冻结 exact package/UI，执行单席 different-owner 综合审计，再打包、显式提交、push 与 Release。
- 当前阶段：`BRIDGE 0.4.8 R-PASS / MOD 52+53 PASS / EXACT PACKAGE+UI FROZEN / UNIQUE DIFFERENT-OWNER AUDIT NEXT`。
- 当前授权边界：用户已要求完整收尾后显式提交、push 与 Release。Bridge 0.4.8 已实机通过；第三方 MOD 仍只做静态读取和隔离安装回归，不执行其游戏逻辑。真实 2P–4P 不可由合成验证冒充，Release 必须标注 `NOT RUN`。

## 仓库与运行身份

| 项目 | 当前值 |
| --- | --- |
| 仓库 | `C:\xiangmuyunxing\biancheng\2026\lostcastle2-keyview` |
| 产品 source / remote | `3d6767794be7b88da3e08e7ef62b444b1658a5ee` 与 `origin/main` 对齐并标记 `v1.6.0`；Release 为 `https://github.com/SeasonCake/lostcastle2-toolbox/releases/tag/v1.6.0` |
| 工作树 | 26 个 tracked 文件修改及 13 个未跟踪记录入口，均归属本轮 Bridge 0.4.6–0.4.8、社区 MOD、多人/UI/打包测试与文档；日志、截图、DLL/PDB 和 package 按 ignore 合同留在本机，尚未 stage/commit/push |
| 游戏/盒子进程 | 2026-08-30 16:59 再核：exact `LostCastle2.exe` 与 `失落城堡2工具箱.exe` 均为 0；四个精确包 UI 验收进程也已自行退出 |
| 精确工具箱候选 | `package/失落城堡2工具箱1.6.1-实时数值监测+一键MOD安装`；1,760 文件、`166,606,890` B、0 配置文件；EXE `6,463,717` B / `46525496A85F75C066AB3829D3CE7A2E38FA2962C9A8F034EC137E3902246C8D` / 版本 1.6.1 |
| 分享 ZIP | 尚未生成；唯一 different-owner 审计 PASS 后才从上方 exact package 创建并做 7-Zip、UTF-8 顶层、唯一 EXE、config0 与哈希回读 |
| 游戏目录 Bridge | 已精确部署并回读 `0.4.8`；0.4.7 exact rollback 已冻结 |
| 运行 DLL SHA-256 | `7740BA3E30CD8C8B73F8BFDF221C3384CB2D64F940699A6974556E989896CE55` |
| `Plugin.cs` SHA-256 | `C0EF0AB6BEAF5F991A58F6BC512F747678308F371D907A750C025177DB117261` |
| Harmony Patch 数 | 0.4.8 为 `15`，新增 `PlayerManager.OnGameRoundEndPreLoadCamp` |

本文所有 `artifacts/runtime-deploy/...` 定位都指向本机被 `.gitignore` 排除的二进制/回滚证据，fresh clone 不包含，故只作本机恢复定位，不声称是仓库链接。

0.4.8 候选、0.4.7 exact rollback 与部署回执位于本机 `artifacts/runtime-deploy/2026-08-30-bridge-0.4.8/`；当前游戏目录 DLL 已回读为 49,152 B / `7740BA3E…6CE55`。

0.3.6 候选、PDB、回滚和完整运行 receipt 位于本机 `artifacts/runtime-deploy/2026-08-28-bridge-0.3.6/`。

## 已确认结果

### MP 与续局

- 长杖耗蓝不是固定 24：短按起步 `12`，长按期间逐 tick `2`，总量随按住时长变化。
- `OnRecoverMana.recoverMana` 是恢复后目标 MP，不是增量；恢复量使用 `current - last_observed`。
- 继续已有房间未重放 room-start 时，0.3.6 会在首个地图内官方耗蓝前懒建立当前非营地 session。
- 0.3.6 实机四次恢复：`66→120=54`、`22→120=98`、`20→120=100`、`116→120=4`。
- 同一快照 `mp_spent=256`、`mp_gained=256`、`mp_net=0`；328 事件，0 duplicate、0 fault。
- MP 探针迭代已停止；不得继续增加推测性 Hook。

### 混合伤害与短退出生命周期

- 官方截图：伤害 `6341`、承伤 `35`、Boss `0`、击杀 `8`。
- Bridge 总伤害 `6341`、Boss `0`，与官方精确一致。
- 详情来源：召唤物 `4101`（57 条）、玩家普通/地图投掷物合并 `1635`（57 条）、玩家元素 `605`（3 条）。三项精确合计 `6341`。
- 回营期间旧 `6341/70` 保留；进入下一张黑森林战斗区后，伤害、承伤、MP、治疗和旧来源清零。
- 生命周期 receipt 共 577 事件，0 duplicate、0 fault。
- 手动短局退出没有触发 `session_ended`；只证明“回营保留→下一图清零”，不能冒充完整通关结算。

### 盒子 UI

- 全局页脚新增 `作者：加菲_barista` 和 `GitHub 仓库`，目标为 `https://github.com/SeasonCake/lostcastle2-toolbox`。
- 修正最小窗口高度，避免设置页“打开 HUD”被页脚遮挡。
- Tk scaling 1.5 / 2.0 实际 PrintWindow 截图通过；GitHub 按钮宽度大于文字宽度，无重叠或截断。
- 版本已顺延为 `1.5.4`；原生构建内全量 `90 passed`，源码/源包/桌面包 self-test 均 PASS。
- UI 几何和打包 EXE 的 100%/125%/150%/175%/200% 五档矩阵均通过，最终 verdict 为 `VERIFIED`。
- 源包与桌面包 `1688` 文件逐文件哈希一致；桌面路径为 `C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.4`。
- EXE SHA-256：`A3FA9BAB74D0CE11D1A16FB63D2D335E597EF88A41A33EE82EAEF46763F44420`。

## 承伤 70 vs 35：已闭合

### 已有证据

- Bridge 收到两条独立 taken 事件，约相隔 4 秒；每条 `settlement_damage=35`，实际掉血约 `34.84` / `34.14`。
- 玩家官方结算卡仅显示承伤 `35`。
- 本局使用幽影提灯召唤物；作者补充社区认知是该召唤物攻击会按玩家攻击计入。
- 0.3.6 源码 `EmitDamage("taken", ...)` 没有检查 defender 是否玩家根实体。
- 两条事件不是传输重复：不同 sequence、都产生实际 HP 变化，capture 为 0 duplicate/fault。

### 当前裁决

- 2026-08-28 目标正控已确认：同一 taken 回调内，召唤物目标为 `target-3 / target_kind=normal`，玩家为 `target-9 / target_kind=player`。
- 正数 taken 总计 `290`：召唤物 `246`，玩家 `44`；257 个接受事件，0 duplicate、0 transport/validator fault。
- 0.3.7 在 snapshot 缺失判断前只允许玩家根 defender 进入 taken；召唤物造成伤害路径不变，Hook 仍为 14。
- 决定性事件之后 Bridge 从 sequence 179 起进入 error；旧 allowlist 未保存 detail。下一轮已补 detail，必须同时确认错误不再出现或取得具体 fault。

### 0.3.7 回归结果

- BepInEx 明确加载 `LC2 Combat Bridge 0.3.7`，collector 连接 live。
- 作者再次按“召唤物先受伤、玩家后受伤”执行；taken 只剩玩家一条 `35`。
- 召唤物造成伤害仍为 `6629`；玩家普通 `3488`、玩家元素 `385`，精确合计总伤害 `10502`。
- 冻结时 376 个接受事件，0 duplicate、0 collector fault、0 Bridge status error。
- 结论：过滤正负控通过，保留 0.3.7；不再扩新 Hook 或承伤探针。

### 当前交付与实测

桌面 `1.5.5` 已并列交付，旧 `1.5.4` 保留。下一步只需作者使用桌面 `1.5.5` 正常打一局，确认非战斗房人偶不增加总伤害/Boss/平均秒伤、真实怪物正常增加，并在结算页核对总伤害、Boss 和“受击承伤”。自伤仍为内部诊断，不作为本轮用户验收项。提交、推送和公开发布仍未执行。

## 2026-08-28 新增：MOD 管理与商店人偶

- 金币编辑器 1.0 已按 DLL 内嵌署名登记作者“刺心”；支持直接选择 DLL 或原始 `F5金币编辑器.7z`，精确校验后安装到游戏独占插件目录并精确卸载。
- 用真实金币压缩包在模拟游戏目录完成安装/状态/卸载端到端正控；未把金币 DLL 写入真实游戏，也未随工具箱打包。
- MOD 管理页已从单卡改为多卡；1000x720、Tk scaling 1.5 的实际 PrintWindow 截图无截断、重叠或越界。
- 本地 MOD 总库清点为 58 个压缩包、4 个裸 DLL、2 个外置 EXE、2 个 TXT；46 个压缩包属于单 DLL，9 个是多文件插件，2 个是整包框架。详见 [`LC2_MOD_LIBRARY_INVENTORY_2026-08-28.zh-CN.md`](LC2_MOD_LIBRARY_INVENTORY_2026-08-28.zh-CN.md)。
- 全刻印全共鸣 1.4.0 作者为空容，属于 BepInEx/Harmony DLL，与外置灵魂石修改器不是同一种实现；它与金币编辑器都占用 F5，当前只记录、未加入可安装列表。
- 最近伤害保留平均 DPS 语义，小数保留一位；标题改为“近 10 秒平均秒伤”。
- 新结算样本：工具箱/游戏总伤害 `79751/67497`，Boss `32489/20235`，两项同多 `12254`；商店人偶在真实 Boss 前已经产生 Boss 数值。0.3.8 在已有 room map 上把 `_Shop_` dealt 事件改为 `aggregate=false`，事件本身仍保留，Hook 仍为 14。
- 0.3.8 已编译、95 个 Python 测试通过并在游戏进程为 0 时精确部署；0.3.7 rollback 位于本机 `artifacts/runtime-deploy/2026-08-28-bridge-0.3.8/`。实机正负控尚未执行。
- 0.3.8 启动门已通过：BepInEx 明确加载 `LC2 Combat Bridge 0.3.8`，本地 pipe live。
- 0.3.8 自伤缺口样本：折断的妖刀诅咒会把当前生命值 15% 转为伤势生命并被描述为一次受击；截图时玩家 `167/190`，HUD 承伤仍为 `0`，恢复 `+6` 正常。当时源码在 `requested<=0` 或 `effective<0` 时丢弃 HP 观察；诅咒房是否复用同一路径仍未确认。
- 同局最终再次证伪 0.3.8：工具箱/游戏总伤害 `45310/39710`，工具箱/游戏 Boss `5600/0`，差额精确等于错误 Boss；双方官方承伤均 `35`。桌面 1.5.4 不是原因。
- 0.3.9 已删除 `_Shop_` 文件名推断，改用 interop 静态确认的公开 `StageMgr.IsNonBattleRoom()`；非战斗房 dealt 保留事件但不聚合。
- 0.3.9 对 HP 变化记录 `InsideDamageResolution`：官方 DamageProcess 内的负 delta 仍由官方承伤表示；外部直接负 delta 发为 `resource_operation=loss` 并进入 `hp_loss_other`。无新增 Hook。
- 主窗口/HUD 将主值命名为用户可理解的“受击承伤”，恢复继续独立显示；内部仍保持结算口径与实际掉血分列。探索性的自伤 HUD/表格/汇总字段已撤回，未完成 receipt 闭合前不作为产品指标。
- 0.3.9 已编译，最终 Python 全套 `96 passed`，并在游戏进程为 0 时部署；0.3.8 exact rollback 位于本机 `artifacts/runtime-deploy/2026-08-28-bridge-0.3.9/`。
- 0.3.9 实机房间过滤已闭合：BepInEx 加载/pipe live；作者确认人偶不再误计，最终工具箱与游戏均为总伤害 `59627`、官方承伤 `84`、Boss `20054`。
- 作者又使用“灭世之槊”（持有时每秒燃烧生命上限 15%）。旧桌面 1.5.4 紧凑 HUD 只显示官方承伤，来源表也没有自伤列或唯一自伤 token；截图不能裁决内部 `hp_loss_other`。不再要求作者从旧 UI 反复查找。
- 可维护的后续方案只接受统一关联：玩家 HP/RedHp 变化绑定 hit/operation；同 hit 有官方 `OnTakeDamage` 归官方承伤，无官方事件才归自伤/诅咒。若伤势生命绕过普通 HP 入口，最多新增一个统一 `HeroRuntimeData.RedHp` 入口，不允许逐道具 Hook。
- 当前决定：自伤功能冻结为内部诊断/未支持，不进入当前工具箱包；总伤害、Boss、受击承伤和恢复按已闭合口径继续推进。

## 2026-08-28 最终桌面候选 1.5.5

- 版本号、EXE 资源和使用说明统一为 `1.5.5`；构建内全量 `97 passed`，源码与桌面包 self-test 均 PASS。
- 桌面目录：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.5`；旧 `1.5.4` 未覆盖。
- 桌面包 `1688` 文件、`118617744` 字节；EXE SHA-256：`0D99BACBB14BBC131DB7395CACDD2A4FCA251F28FFD3F33A2C0D633A82917F56`。
- 金币编辑器二进制未随包分发；用户选择原始压缩包后才会执行本地精确校验和安装。
- package receipt 覆盖 1.0/1.25/1.5/1.75 scaling、640×480 最小窗口、千倍大数、HUD、MOD 和设置页；源码几何 receipt 同步通过。最终 verdict：`VERIFIED`，详见 `artifacts/ui-acceptance/2026-08-28-toolbox-1.5.5-final/VERDICT.zh-CN.md`。

## 其余待办（非明早阻塞项）

- 下一桌面版本集中计划见 [`LC2_NEXT_DESKTOP_VERSION_PLAN_2026-08-28.zh-CN.md`](LC2_NEXT_DESKTOP_VERSION_PLAN_2026-08-28.zh-CN.md)；生命周期为 `PLANNED / NOT STARTED`，当前只完成截图、源码和新武器幻化包的静态调查。
- UI 待办（作者 2026-08-28 新增，当前仅记录、未开始）：按键显示窗口右上角增加“纯净模式”快速切换按钮，避免只能依赖可能与浏览器/其他软件冲突的 `F11`；保留 `F11` 是否继续作为备用快捷键，实施时再结合现有控制区宽度确认。
- UI 待办（作者 2026-08-28 新增，当前仅记录、未开始）：LC 战斗状态 HUD 首次打开的默认位置改为屏幕左上角，不再默认位于屏幕中间偏下。源码调查确认当前没有跨重启保存 HUD 坐标；下版只改变首次创建默认值，不顺带增加坐标持久化，同进程拖动/隐藏恢复/缩放行为保持。
- 未来正常完成整局时，被动确认一次 `session_ended -> 营地保留 -> 新图清零`；无需为此额外打一整局。
- 地图投掷物当前进入玩家普通/元素总量，没有独立详情 token；总量已闭合，分类改善不是当前 P1。
- 击杀数没有权威事件，不能从致死伤害反推或补差。

参数、公式、来源和历史样本总索引：
[`LC2_RUNTIME_PARAMETER_DEBUG_INDEX.zh-CN.md`](LC2_RUNTIME_PARAMETER_DEBUG_INDEX.zh-CN.md)。

## 2026-08-28 长局后续：位置延迟与法力差值

- 作者使用桌面 1.5.5 完成长局；工具箱/结算精确对齐总伤害 `177901`、受击承伤 `347`、Boss `23483`，确认核心伤害口径保持闭合。
- HUD 显示法力消耗 `238`、恢复 `236`。进程退出后没有逐事件 receipt，也没有独立结算法力字段；当前只能确认净值为 `-2`，不能直接判定统计错误。
- 从黑森林 Boss 进入废村入口时位置没有及时刷新；进入废村第 1 区后 HUD 才显示“废村 · 入口”。该一房间延迟与 0.3.9 在 `OnChangeRoomStart` postfix 读取 `StageMgr` 状态一致。
- 0.4.0 将同一个位置 Hook 改到 `OnChangeRoomEnd`，Hook 总数仍为 14；同时在 BepInEx 日志加入 `[LC2CB-ROOM]` 和 `[LC2CB-MP]` 有界诊断。法力公式未先行修改。
- 0.4.0 DLL 已通过 Roslyn 编译和 Python 全量 `99 passed`，并在游戏进程为 0 时部署。候选 SHA-256 `4223288D04EF2DC8E1DAB3325CC582358233E571B0BD304F32F63A3A572900C2`；0.3.9 exact rollback 位于 `artifacts/runtime-deploy/2026-08-28-bridge-0.4.0/`。
- 作者截图中的 HUD 外框约 `370x492`，与 200% 设计尺寸一致；源码 200% 几何 receipt 为 `VERIFIED`，截图内暂未定位到明确被裁控件。若实机再次出现，需要作者指出具体行或边缘，禁止凭不明确截图盲目缩放。
- 作者确认战斗 HUD 是工具箱主要功能；下一桌面包改为启动工具箱时默认打开 HUD，保留 HUD 内“隐藏”操作，并提供仅供启动参数使用的显式 opt-out。当前已交付的桌面 1.5.5 尚未包含该默认行为，待地图/法力裁决后一起重打下一包。

## 2026-08-28 0.4.0 实机裁决与 0.4.1 候选

- 位置时序已经闭合：作者确认跨图后立即显示“废村 · 入口”；同一 0.4.0 日志还记录了 `DarkForest 8 -> SaltpetreDesert 0 -> 1 -> 2`，入口不再晚一房间。`OnChangeRoomEnd` 保留。
- 无禁回状态的长局样本记录官方耗蓝 21 次、原始合计 `504`；18 次恢复原始合计约 `508.67097`，若逐事件换成显示整数则为 `509`。0.4.1 因此统一累计原始 float，只在 HUD 最终显示时取整。
- 新局携带“禁咒羊皮纸”后，截图确认角色多次技能消耗后由房间系统恢复到满蓝，但 HUD 恢复仍为 `0`。该局日志在 `session_start` 后记录 6 次官方消耗、合计 `207`，没有任何有效 `[LC2CB-MP] kind=recovery`；后续消耗前的 `last_observed_raw` 却已回到满值 `130`。这证明实际恢复经过底层 MP 写入，但没有触发官方 `OnRecoverMana`。
- 羊皮纸文案只禁止“通过攻击恢复法力”，不能把房间系统回满解释成不应统计。0.4.1 不新增 Hook：复用现有 `ChangeCurrentMp/UpdateMp` 前后观察，对顶层真实正向 delta 做兜底；同一根操作中若官方回调已经聚合，则按已覆盖量抵扣，避免双计。
- `UI-CLIP-01`：HUD 地区省略已明确复现为布局问题，不是地图映射问题。最近秒伤卡改为两列并为地区预留固定宽度，地区字段永远保留完整场景和区域文字；HUD 启动默认开启的源码改动继续保留。候选实现完成，精确可见性验收等待游戏退出后执行，未验收前不得关闭此项。
- 0.4.1 Release 构建使用隔离 SDK 6.0.428，0 warning / 0 error；Python 全量 `104 passed`（包含低层回蓝事件协议正控与地区完整显示源码回归），工具箱 self-test PASS，Harmony Patch 数仍为 `14`。
- 候选冻结记录时 DLL 为 `41,472` 字节、SHA-256 `D499BA6BA2B21851F7C325F37503CEE418A66E4AA91A8D2A7C200FCC076B3744`；当时因游戏运行尚未部署。现已按下节 16:15 接管记录完成 exact rollback 与部署，桌面包仍未重打。

## 2026-08-28 16:15 工作 5 接管与实测入口

- 已完整读取 `LC2 工作 4`，后续以当前源码、本文件和当前运行身份为权威，不再重复加载旧图片/整段历史。
- 接管时分支/HEAD 仍为 `main` / `d6ce78e05a7d6bb5de33ccdeb11e831c0f6f8ab0`，共享脏树为 18 项 tracked 修改、6 个 untracked 路径；未暂存、未提交，也未把继承改动归到本轮。
- 0.4.1 重新通过隔离 SDK Release 构建（0 warning / 0 error）、Python 全量 `104 passed`、工具箱 self-test 和 `git diff --check`；候选哈希未漂移。
- 游戏退出后先冻结 installed 0.4.0 为 `artifacts/runtime-deploy/2026-08-28-bridge-0.4.1/LC2CombatBridge.0.4.0.rollback.dll`，再部署 exact 0.4.1。游戏目录回读为 `41,472` 字节、SHA-256 `D499BA6BA2B21851F7C325F37503CEE418A66E4AA91A8D2A7C200FCC076B3744`；部署后两次 `LostCastle2.exe + C:\xiangmuyunxing\steamapps\common\Lost Castle 2\LostCastle2.exe` exact 查询均为 0。
- `UI-CLIP-01` 与 `HUD-DEFAULT-01` 的源码候选验收为 `VERIFIED`：H1-H8 覆盖空/正常/千倍值、最长地区、Tk 1.0-2.0 与 HUD 0.85/1.25；真实 D1/D2 证明默认显示 HUD、显式 opt-out 不显示；隐藏后可恢复。详情见 `artifacts/ui-acceptance/2026-08-28-hud-location-default-source/VERDICT.zh-CN.md`。
- 非 DPI-aware 抓图曾产生一次假裁切，已按证据故障保留并排除；有效 D1/D2 使用 `PER_MONITOR_AWARE_V2`，未修改候选源码。
- 下一桌面包仍未重打。当前终点是作者实机验证 0.4.1：自然启动/pipe、禁咒羊皮纸或房间系统回蓝进入底层兜底、正常官方回蓝不双计、游戏内地区文字完整。实机闭合后再统一顺延桌面版本并做 exact package 验收。
- 自伤/伤势生命和逐道具 Hook 继续 deferred；本轮不夹带。
- 16:17 已启动仓库源码候选供作者实测：`C:\Python313\python.exe keyview.py --show-page combat`，PID `9148`。16:17:39 回读主窗口 HWND `3410728` 与 HUD HWND `4720930` 均可见；游戏 exact 进程仍为 0，运行 DLL 仍为 0.4.1 哈希。此为源码候选，不是新的桌面包；实测期间不要再启动桌面 1.5.5 造成双客户端。

## 2026-08-28 16:43 0.4.1 实测与宽敞默认

- 作者重启后继续携带禁咒羊皮纸的存档，截图显示硝石荒漠第 2 区、法力消耗 `114`、恢复 `+114`，并确认表现正常。日志确认 0.4.1 加载且 pipe live；2 次官方耗蓝 raw 合计 `114`，18 次官方恢复 raw 合计 `114`，`runtime_gain=0`。官方回调分支和根操作抵扣没有双计，判 `R-PASS`。
- 这局回蓝实际触发了官方 callback，因此没有覆盖“官方 callback 缺失时由低层正 delta 补记”的兜底正控。该 arm 保持 `NOT RUN`，只在以后自然再次出现时被动裁决，不要求作者强造。
- 作者随后关闭游戏；游戏 exact 进程复核为 0，Bridge 仍是已部署 0.4.1，本轮未替换 DLL。
- 作者选择工具箱默认使用“宽敞”，并要求宽敞预设更大。源码现为：紧凑 `840×650、90%`、标准 `1000×720、100%`、宽敞/默认 `1280×900、115%`。旧默认 `900×650、100%` 与旧宽敞 `1160×840、115%` 自动迁移；标准、紧凑和自定义尺寸保持。
- 尺寸实现通过聚焦 `43 passed`、全量 `107 passed`、self-test 和差异格式检查。只读验收在关闭首轮主页摘要和第二轮 Treeview 大数裁切后，Iteration 3 对主页正常/千倍值、紧凑反例、战斗页 125%/175%、设置页 150%/200% 及三档操作全部 `VERIFIED`。
- 真实迁移：旧本地 `1160×840、115%` 由 PID `8864` 加载为 `1280×900、115%`；主窗口 HWND `1967948` 与默认 HUD HWND `133006` 可见。全窗截图 `1302×956`，SHA-256 `8A833D233585F13E2A7D79986026DFA41106C222C3203D29B61DA6D7D5810B67`。验收见 `artifacts/ui-acceptance/2026-08-28-toolbox-spacious-default-source/VERDICT.zh-CN.md`。
- 当时源码工具箱曾留在设置页供作者查看；随后已按下节完成 1.5.6 打包并关闭源码进程。提交、推送和公开发布仍未执行。

## 2026-08-28 17:02 最终桌面包 1.5.6

- 作者授权进入打包阶段；版本、EXE 资源、包目录与使用说明统一为 `1.5.6`。旧桌面 `1.5.5` 保留，未覆盖。
- 最终桌面目录：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.6`；EXE FileVersion / ProductVersion 均为 `1.5.6`。
- 最终 EXE SHA-256：`85F37430FB6863FB3076A05FDFE4F01B7730B7440BCE8006D29FA395C06CFD59`；包体 `1688` 文件、`118618824` 字节。源包与桌面副本对全部文件逐项核对相对路径、大小和 SHA-256，一致。
- 聚焦测试 `17 passed + 26 passed`，全量 `107 passed`，构建内再次 `107 passed`；源码和桌面包 self-test、py_compile、diff check 均通过。
- Iteration 1 在 Tk 1.25 最小窗口发现来源明细法力列越界，旧候选判红废弃；Iteration 2 只调整来源列请求宽度，最小窗口五列全显，175%/200% 千倍大数保持完整。
- 最终 EXE 12-arm 矩阵覆盖 100%/125%/150%/175%/200%、无设置默认宽敞、HUD 默认开启、显式 opt-out、主页、战斗、MOD、设置和最小窗口；receipt checker 与像素审阅均为 `VERIFIED`。桌面副本另做 exact-path 默认启动 receipt，同样 `VERIFIED`。证据见 `artifacts/ui-acceptance/2026-08-28-toolbox-1.5.6-final/VERDICT.zh-CN.md`。
- Bridge 与游戏目录本轮未改；仍为 0.4.1 exact runtime。官方回蓝 114/114 不双计已闭合；缺官方 callback 时的底层兜底保持 `NOT RUN`、以后自然观察。
- 17:04 从桌面副本无 QA 参数自然启动，PID `5996`，ExecutablePath 精确为桌面 `1.5.6` EXE；主窗 HWND `7276446`、HUD HWND `2492226` 均可见，游戏 exact 进程数为 0。该进程留给作者实测；首次启动产生的本地 config 属于运行状态，不是候选二进制漂移。
- 提交、推送和公开发布未执行；自伤/伤势生命与逐道具 Hook 继续 deferred。

## 2026-08-28 18:46 金币编辑器随包与桌面包 1.5.7

- 作者要求金币编辑器像灵魂石修改器一样随包，并要求 MOD 卡片有一键启动入口、明确游戏内使用步骤且不影响其他界面。实现保留灵魂石原流程；金币卡固定为“安装/重新安装 → 启动游戏 → 卸载”。
- 金币编辑器 `LC2GoldFree.dll` 已作为冻结输入随包，大小 `9,216` 字节，SHA-256 `BB6FF96AA4AF9BB3521ED93C3A5582E48D5D9CB8C7BAAF5291FA4C3E57647B56`。目录仍执行精确哈希检查；安装到独占 `BepInEx/plugins/gold-editor-f5/LC2GoldFree.dll`，不批量改写其他插件。
- 卡片说明为：“安装后启动游戏，按 F5 打开窗口；输入数量并保存，返回主菜单再进入游戏生效。”。“启动游戏”复用工具箱已有的启动/聚焦 Lost Castle 2 路径；只有插件状态为精确已安装时才启用，未安装、完整性失败或操作进行中均禁用。
- 版本、EXE 资源、包目录和使用说明统一为 `1.5.7`。聚焦测试 `13 passed + 18 passed + 26 passed`，源码全量 `110 passed`，原生构建内再次 `110 passed`；源码/包/桌面 self-test、py_compile 和 diff check 均通过。
- 包形隔离测试使用临时假游戏目录完成随包来源解析、安装、精确状态识别、卸载和同级插件保留；真实游戏目录未写入。启动按钮回调正控调用一次、未安装反例不调用；真实游戏启动保持 `NOT RUN`。
- 最终桌面目录：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.7`；旧 1.5.6 未覆盖。EXE FileVersion / ProductVersion 均为 `1.5.7`，SHA-256 `4F2CD80C0EEDE3F8905CFFC157BCAAC7BD31EAD43BB73338AA7917666705FB91`。
- 源包与桌面副本均为 `1689` 文件、`107` 目录、`118628736` 字节；逐文件相对路径、大小和 SHA-256 清单零差异。桌面 exact-path self-test 退出码 `0`，截图后工具箱与游戏进程均为 `0`。
- 冻结 EXE UI 矩阵覆盖 MOD 未安装/隔离夹具已安装、Tk 1.0/1.25/1.5/1.75、`640×480` 最小窗口，以及概览、战斗千倍值、设置和 HUD；结构 checker 及像素审阅全部 `VERIFIED`。桌面副本另做 exact-path MOD 页回执，同样 `VERIFIED`。证据见本机 `artifacts/ui-acceptance/2026-08-28-toolbox-1.5.7-gold-bundled/VERDICT.zh-CN.md`。
- 1.5.7 新增差异尚未提交；HEAD 仍为 `359785b93ffdfe39b9a2a67abce5f05c4a41d540`。推送、公开发布、自伤/伤势生命与逐道具 Hook 均未执行。

## 2026-08-28 19:34 社区 MOD 自动添加与桌面包 1.5.8

- 重新静态扫描作者桌面 `LC2_versions/LCMods`：共 67 个候选输入；65 个属于普通插件来源，两个 BepInEx/前置整包按框架边界拒绝。默认目录按功能族只选最新可用版，同时排除旧版、测试版、未完成/半成品和明确有 bug 的包。
- 最终内置 46 个社区 MOD、47 个载荷文件，总载荷 `3,163,085` 字节。多 DLL 整合包拆成独立可管理条目；作者仅在压缩包说明、源码或程序集有可靠证据时填写，否则显示“社区未署名”。
- MOD 页改为搜索列表和固定详情/操作区，保留灵魂石、金币及其他页面行为；每项显示名称/版本、作者、用途、使用方法和状态，并提供安装/重新安装、启动游戏和精确卸载。
- 新增“添加 MOD”：支持 DLL、文件夹、ZIP、7Z、RAR；使用包内固定身份的 7-Zip 静态读取，自动识别必要信息并给出可编辑预览。用户登记到 `config/user_mods`，同载荷重复导入复用已有条目，冲突 DLL 阻止覆盖。
- 包内提供 `MOD自动添加说明.txt` 和 `用户MOD/请把MOD放到这里.txt`，包含 schema 1 的 `lc2-mod.json` 示例、字段规则和可直接交给 AI 的整理提示词。
- 源码全量 `118 passed`；原生构建内再次 `118 passed`；冻结包 self-test 退出码 `0`。46 个默认条目在隔离假游戏目录逐项完成安装、精确状态识别和卸载，且保留无关同级插件；包内 7-Zip 完成 7Z 导入、登记和重载正控。
- 冻结 EXE UI 验收覆盖 MOD 100%/125% 最小窗口/175%、社区条目已安装、150% 归档导入预览，以及概览、战斗千倍值、设置和 HUD；9 份回执路径与哈希唯一一致，最终 `VERIFIED`。证据见本机 `artifacts/ui-acceptance/2026-08-28-toolbox-community-mods/VERDICT.zh-CN.md`。
- 最终桌面目录：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.8`；旧 1.5.7 保留。EXE FileVersion / ProductVersion 均为 `1.5.8`，SHA-256 `43F855FD0BFC516AD99985CE01A9CD1822D7CF1DE0266619C2433D3F0C554E94`。
- 源包与桌面副本均为 `1,742` 文件、`156` 目录、`124,390,970` 字节；全部相对路径、大小和 SHA-256 零差异。桌面 exact-path self-test 退出码 `0`，随后工具箱与游戏进程均为 `0`。
- 未向真实游戏安装/卸载新增社区 MOD，未启动真实游戏，也未执行任何第三方 MOD DLL/EXE。本节与 1.5.8 源码、目录、测试和说明作为一次收口提交；父提交为 `359785b93ffdfe39b9a2a67abce5f05c4a41d540`，提交后推送 `main` 并以远端回读为最终身份。

## 2026-08-28 20:11 产品停工与治理冻结

- 作者已停止 BidKing/LC2 全部产品任务，后续先执行项目治理、SOP、skills、结构/存储与开源准备；
  `LC2_NEXT_DESKTOP_VERSION_PLAN_2026-08-28.zh-CN.md` 只作为 inactive backlog 保留，不启动实现。
- 产品 source `ba2a34253c8e429064c724478df898a56cf602b2` 与 `origin/main` exact 对齐；产品代码无未提交
  修改。冻结时只有本检查点修改与下一版本计划两项记录差异。
- 本观察席独立重跑 Python 全套：`118 passed`；`py -3 keyview.py --self-test` PASS；
  `git diff --check` PASS。游戏与工具箱 exact 进程数均为 0。
- 冻结源包仍为 `1,742` 文件、`124,390,970` 字节；桌面目录在首次正常运行后多出
  `config/settings.json`（551 bytes）和 `config/macros.json`（1,903 bytes），其余路径/大小无差异。
  这是明确的运行状态，不是 1.5.8 候选字节漂移。
- 1.5.8 的 source/package/UI acceptance 可保留为 scoped PASS；真实社区 MOD 安装/启动、第三方
  DLL/EXE 执行与公共再分发仍为 `not-run / separate-stage`，不得由隔离假游戏目录测试外推。
- LC2 工作1–4 已由作者归档；归档任务仍可按 task ID 读取，不影响本仓库、工作5记录或后续复盘。
  动态项目真相只取本 Git、当前检查点和真实产物，不要求取消归档或重放旧图片上下文。

## 2026-08-29 本地桌面包 1.5.9

- HUD 首次创建位置从屏幕下方居中改为左上安全边距；最终打包 EXE 的默认 HUD 矩形为 `[16,16,386,508]`。显式 `--hide-combat-hud-on-start` 反例只出现主窗口，拖动/隐藏/缩放合同未改。
- MOD Treeview 改为按实际宽度分配名称、版本、作者、状态四列；工具栏按钮先保留宽度，搜索框使用剩余空间。设置页控制组同样先保留右侧宽度，DPI 安全最小窗为 150% `780×700`、200% `900×840`。候选截图无版本/作者挤压、“添加 MOD”裁字或“恢复拖动”裁字。
- QQ 上传列表仅在缺少更强作者证据时补暂定署名；程序、源码或 README 中已有的作者未被覆盖。社区目录由 46 增至 47 个条目、48 个载荷文件、总载荷 `3,175,885` 字节。
- 武器皮肤替换以同插件身份的 1.5 原位替换 1.2；载荷 `LC2.StaffSkinSwap.dll` 为 `20,992` 字节 / `5827C562C7E614B366EC7D2C4907AA72729D611CEFC5012598DBADC57FA614C0`。新增“隐藏震击环绕球”1.0，载荷 `11,776` 字节 / `7A0C082EFE54CFAF7977515A09668EFB01E3CE9C25E22845249FDF1C1291D3E5`。战利品 V2.4.0 因同身份、低于现有 2.5.3 且标注有 bug 未加入。
- 页脚新增“投喂”按钮与 hover；默认展示微信二维码，点击打开随包 `赞助与投喂` 目录。文案只表达因热爱《失落城堡2》、愿意支持加菲或催更时投喂猫罐头；未沿用 BigKing 的原付费语境。目录包含微信 PNG/JPG、支付宝、两张猫图和说明，共 6 个哈希绑定文件。
- 构建门新增原生命令退出码检查，图标生成、测试、self-test 或 PyInstaller 任一失败都会立即终止。最终源码与构建内均为 `122 passed`，源码/包/桌面 self-test 均退出 `0`。包形验证对 47 个默认 MOD 逐项安装、精确状态识别、卸载并保留无关插件；包内 7-Zip 对武器幻化 RAR 完成导入与登记。
- 最终源包：`package/失落城堡2工具箱 1.5.9`；最终桌面：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.9`。两者均为 1,749 个文件、`125,569,376` 字节，逐文件相对路径、大小和 SHA-256 零差异。
- 最终 EXE：`6,207,037` 字节，SHA-256 `8BD31A260C4AB308FFF3EF1E7B179B6A382DEA236D863ADBDF98A645F85D70B9`；FileVersion / ProductVersion 均为 `1.5.9`。冻结 EXE 的主页、MOD 宽敞/200% 最小窗、设置 200%、战斗页、HideWeaponFX、武器皮肤 1.5、微信 hover、默认 HUD 与 opt-out 均 `VERIFIED`；本机回执见 `artifacts/ui-acceptance-1.5.9-final/VERDICT.zh-CN.md`。
- 未向真实游戏安装、卸载或执行任何新增第三方 MOD，未启动真实游戏；游戏与桌面候选 exact name + ExecutablePath 连续两次均为 `0`。真实游戏兼容性等待作者后续实测。
- 本轮尚未 commit、push、创建 GitHub Release 或公开发布；当前 HEAD 仍为 `364bab6ae142d5bf30571ec8ef7b5f3e1678dc41`（ahead 2）。

## 2026-08-29 1.5.10 工作中检查点

- 作者实测数个一键安装 MOD 可用；金币编辑器实际可用但其 Unity 初始窗口 `(20,20,300,160)` 曾被 1.5.9 默认 HUD 完整覆盖。当前源码把 HUD 首次 x 从 16 改为 500、y 保持 16，窄屏向右边界钳制；拖动、隐藏、缩放合同不变。
- 静态扫描 19 个带 IMGUI 的随包插件：多个窗口从 x=20–80 起始；新增玩家/队友数值面板主控制窗为 `(30,30,980,650)`，固定数据条位于屏幕下部。x=500 可完整让出金币小窗并减轻其他左上小窗遮挡，不能也不声称完全避开所有大型面板。
- 新增来源 `实时显示数值及查看队友数值.rar` 为 `34,772` 字节 / `782FECB1D0887F8F2823FFDCF0612E970488A7C063E35B69934851852ECDD4F1`；只随包 `实时数据1.3.dll`（`27,136` 字节 / `ADF5C15460741FABA356B9B7ADFEF3FC2762A5B236949F302EBD5E84E3553B17`），说明为 F6 打开、勾选数值、2P–4P 查看队友，暂定上传署名“懒虫桑”。
- 自动识别器只对“同一主体 + 点分版本”的整组 DLL 保留最高版；不同主体的版本化 DLL 反例保持全部。默认社区目录当前为 48 个条目、49 个载荷文件、`3,203,021` 字节。
- 社区目录以可维护 `sort_priority` 调整为实战/资源优先、外观/皮肤靠后；内置灵魂石和金币两个工具仍先于社区目录。页脚顺序为 GitHub → bilibili → 投喂，bilibili 目标为 `https://space.bilibili.com/88048665?`。
- 源码与构建内全量均为 `134 passed`，源码/包/桌面 self-test 均退出 `0`；精确包 UI 与桌面候选已完成，真实游戏仍未执行新增 MOD。未经真实游戏运行的第三方 MOD 不得从静态/隔离安装结果外推为功能 PASS。本阶段不 commit、不 push。

## 2026-08-29 1.5.10 本地候选与全新环境收口

- 最终源包与桌面分别为 `package/失落城堡2工具箱 1.5.10`、`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.10`；两侧都是 1,755 个文件、161 个目录、`166,142,080` 字节，逐文件相对路径/大小/SHA-256 零差异。
- 最终 EXE 为 `6,222,051` 字节 / `64226A7E9831E3EE4127AA254083D7B1680658062C0481E10A34ABF900E809A8`，FileVersion / ProductVersion 均为 1.5.10。
- 全新环境初始化随包提供清洁 BepInEx `6.0.0-be.785` 与 Bridge 0.4.1。运行时 ZIP 为 `40,402,401` 字节 / `0B617BC439F53E39680444F1EFD84C2B31A96D144D3267EE06EBEA05B59738A8`，307 个成员；明确排除来源中的 plugins/cache/interop、多人上限 MOD 和全部研究探针。BepInEx LGPL-2.1 全文与源码提交定位随包。
- 首次点击启动游戏或首次安装 DLL MOD 时出现“首次初始化”，文案明确不自动安装/启用社区 MOD并默认关闭调试控制台。包形空目录安装/重复安装均 `ready`；唯一新增插件为 exact Bridge；不同核心反例在任何写入前阻断。
- 当前测试机在游戏 exact name + ExecutablePath 连续两次为 0 后，将 BepInEx 控制台开关从 true 改为 false并保留备份；当前运行环境状态为 `ready`。真实启动后是否完全不出现控制台仍待作者下一次自然启动观察，不能由静态配置冒充运行时 PASS。
- 精确 EXE 的 10 臂 UI 验收为 `VERIFIED`：HUD `[500,16,870,508]`、opt-out、宽敞主页、200% 1200×840 安全最小窗、MOD 排序/2P 搜索、首次初始化提示、175% 战斗、200% 设置与微信 hover 均通过；见本机 `artifacts/ui-acceptance-1.5.10-final-runtime/VERDICT.zh-CN.md`。
- 独立子 agent 对冻结 EXE `64226A7E...E809A8` 的综合终审 findings 为 none，结论 `PASS TO REAL-GAME TEST`；独立复跑 134/134、清洁运行时、48 个社区 MOD、包↔桌面逐文件和 10 路精确 UI 回执均通过。
- 尚未 commit、push、创建 Release 或公开发布。下一步是作者实战，包括真实首次 interop、真实第三方 MOD/联机功能与启动后无控制台观感。
- 作者实测期间的只读调查已另存为 [`LC2_MOD_AUTHOR_AND_MULTIPLAYER_DAMAGE_RESEARCH_2026-08-29.zh-CN.md`](LC2_MOD_AUTHOR_AND_MULTIPLAYER_DAMAGE_RESEARCH_2026-08-29.zh-CN.md)：记录署名证据分层、游戏内伤害统计后移要求，以及未来自有 HUD 多人归属路线。该记录未修改 1.5.10 代码或包。

## 2026-08-29 1.5.11 冻结候选

- Bridge 已升至 0.4.2：修正闪避回蓝衣服/魂石触发时同根官方耗蓝掩盖低层净恢复的问题；旧日志回放补回 41 段、raw `169.1415`，恢复累计 `2602.2174`。候选/随包/当前游戏目录 DLL 均为 `46,080` 字节 / `2D87EFA3B1805310595626AFBC27926CEAB389EB74CA8CD84E556ECDB402A57F`；真实 0.4.2 对局仍待作者验证。
- 多人合同新增 session-scoped 匿名 roster 与 owner 归属。聚合器保留未归属伤害、不猜补差；HUD 保持左侧单人卡不动，仅在识别到 2–4 人时向右增加最多三个队友卡，每卡显示伤害、队伍占比 bar 和 Boss 伤害；主战斗页也显示队伍 bar。
- HUD 总伤害面板增加结构留白，千万级数字不再被 bar 裁切；小字整体上调。默认位置仍为 `[500,16]`，避免覆盖金币等左上小窗。
- Windows AppUserModelID、EXE 资源和 Tk 默认图标统一为盒子黄色 `K`。页脚保持 GitHub → bilibili → 投喂；MOD 版本/作者列间距、实战优先排序和署名分层均已落地。
- 默认社区目录为 49 个条目、50 个载荷文件、`3,230,669` 字节。新增终始武器 1.5.0 和玩家实时属性/队友面板，游戏内伤害统计升级为 1.6.4 并后移；同功能族只保留最新版本。
- 最终项目包与干净分享目录分别为 `package/失落城堡2工具箱 1.5.11`、`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.11-预备正式版`。两侧均为 1,757 个文件、163 个目录、`166,216,333` 字节，逐文件零差异。已实测的旧桌面 `1.5.11-final` 含作者本机配置，不作为分享源。
- 最终 EXE 为 `6,237,475` 字节 / `3A6B08D97D7172292748BEB37A364A99357789BDDA759D84CA29CEDD14BF6D8C`；固定数值版与字符串版均为 `1.5.11.0 / 1.5.11`。源码全量 `145 passed + 7 subtests`，构建内 `145 passed`；清洁运行时门通过。
- 最终 EXE 额外复核 100% 最小主界面、175% MOD 页和 200% 四人 HUD。四人 HUD 从 `610×516` 增至 `610×554`，三个队友卡的 Boss 行实际高度均为 30、请求高度均为 30，几何 checker 为 `VERIFIED`；干净截图确认数字、bar 和 Boss 行无裁切。证据保存在本机 `artifacts/ui-acceptance/2026-08-29-toolbox-1.5.11-final4/`。
- 当前作者只需后续自然实测真实 2P–4P 和更多第三方 MOD 组合；0.4.2 单人闪避回蓝与小数累计口径已闭合。commit、push 和 GitHub 预发布已获授权，完成后以远端回读为准。

## 2026-08-29 0.4.2 法力差 2 裁决

- 作者完成后续实战，HUD 显示法力消耗 `720`、恢复 `+722`。最终日志逐事件回放为 15 次 `48 = 720`；恢复为 `7×96 + 49.655174255371094 = 721.6551742553711`，在 UI 末端正确显示为 `722`。
- 该局 `runtime_gain=0`，Bridge MP error/stack mismatch 为 0，没有漏记或双计证据。一次部分恢复端点为 `100.3448257446289 -> 150`，且 MP 上限/当前值跨房间变化，因此恢复总量不要求与消耗总量相等。
- 作者接受这是底层小数累计后的整数显示，不要求改算法或重打包。1.5.11 进入预备正式版提交/push 收口；真实多人和第三方 MOD 组合仍不外推为已验证。

## 2026-08-29 预备正式版分享包

- 干净来源目录：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.11-预备正式版`；与项目 `package/失落城堡2工具箱 1.5.11` 的 1,757 个文件逐项零差异，不含作者本机 settings/macros。
- 分享 ZIP：`C:\Users\shenc\Desktop\失落城堡2工具箱1.5.11-实时数值监测+一键MOD安装.zip`，`136,726,230` 字节，SHA-256 `524C3BBA642C308DA03CCF7B9FC9777668C8D37D7F253E397517290E22062982`。
- 7-Zip 完整性测试退出码 0；强制 UTF-8 文件名后，Windows/.NET 回读唯一顶层目录为“失落城堡2工具箱 1.5.11-预备正式版”，且唯一主 EXE 名称正确。首个错误代码页 ZIP 已按精确身份删除，不得分发。
- 发布包采用 PyInstaller EXE/PYZ 封装，不直接散发 `.py`，但没有新增加密、反调试或重保护；这是作者选定的适度封装，便于群友共享和后续维护。

## 2026-08-29 1.5.12 / Bridge 0.4.3 锁血兼容候选

- 作者稳定复现：1.5.11 重启后正常，选择锁定 65% 生命的噩梦/诅咒后立刻变为“异常”。根因已定位为 Bridge 0.4.2 发出合法意图的 `resource_operation=loss`，而 1.5.11 schema 枚举遗漏 `loss`，第一条事件被客户端按合同拒绝；不是锁血数值本身越界，也不是第三方锁血 MOD 冲突。
- 两类生命语义已明确分开：锁 20%/40%/65% 不改变真实 `max`，只把当前可用上限限制为 80%/60%/35%；染血的冠军腰带是实际 `max 100→60`。清除诅咒、房间药剂与宝物引起的当前/最大生命增减使用统一资源变化合同，不增加逐道具 Hook。
- Bridge 0.4.3 将承伤、HP/MP 观察和官方法力路径限定为 `LocalPlayer.OwnerCreature`；队友资源或锁血不会进入本地指标，队友仍只参与匿名伤害归属。直接负 HP 的 `loss` 只进入内部 `hp_loss_other`，不污染“受击承伤”或“回复”。
- 源码全量 `149/149 PASS`；Bridge 构建 `0 warnings / 0 errors`。候选/随包/当前游戏目录 DLL 均为 `46,592` B / `2837F6C4...CF562A3`，0.4.2 exact rollback 已冻结。
- 桌面 `1.5.12-锁血兼容测试版` 与项目包逐文件零差异，均为 1,757 文件、162 目录、`166,217,064` B；EXE 版本 `1.5.12`，SHA-256 `4E48267F...B8DAD31`。运行时首次/重复安装、控制台关闭与不同核心写前阻断均 PASS。
- 主战斗页新增一行低强调说明：“法力按底层小数累计，界面最终取整；与逐次整数相加可能有少量差异。”；紧凑 HUD 不增加说明。冻结 EXE 的 100%/200% 战斗页和 200% 四人 HUD 均经几何 checker 与像素审阅 `VERIFIED`。
- 真实 65% 锁血正控 `R-PASS`：游戏画面 `49/140`，即真实 max 仍为 140、可用 35% 精确为 49；HUD 保持绿色“实时”，结算保留总伤害 `63,952`、Boss `26,969`、受击承伤 `205`、回复 `191`、法力消耗/恢复 `162/162`。BepInEx 明确加载 0.4.3、pipe connected，Bridge error/resource conversion/stack mismatch 匹配均为 0。
- 干净分享 ZIP：`C:\Users\shenc\Desktop\失落城堡2工具箱1.5.12-实时数值监测+一键MOD安装.zip`，`136,662,047` B / SHA-256 `103E8A1363343CF031FC32F4C39C4EC4C4AF3A83B31979340E262E9809EF947F`。7-Zip 完整性 PASS；.NET 回读唯一 UTF-8 顶层目录为 `失落城堡2工具箱 1.5.12`，1,757 个文件、唯一主 EXE、0 个 config 文件。
- `NOT RUN`：20%/40% 档位逐档真实选择、洗掉生命锁定、冠军腰带/药剂的当前与最大生命变化、2P–4P 队友独立锁血；自动合同正控不能替代这些人口。

## 2026-08-29 1.5.13 / Bridge 0.4.4 魔晶石回蓝候选

- 新反例：作者新开一局取得“诅咒的魔晶石”（法力上限 +80%、消耗 +50%），两次技能后游戏已回到 `225/225`，HUD 却为消耗 `38`、恢复 `0`。
- 冻结日志精确记录前两次官方消耗各 `19`，每次回调处为 `206/225`，下一次根操作前又是 `225`；期间没有官方恢复 callback 或现有 `runtime_gain`。根因是恢复在同一底层 `ChangeCurrentMp` 根操作内发生，入口/出口净变化为 0，旧 fallback 的 `effective>0` 条件把“先扣19、再回19”抵消掉。
- 0.4.4 不增加 Hook；统一 fallback 为 `max(0, after-before+same_operation_spend-official_recovery_covered)`。编译 DLL 直接反射五臂：净零回满 19、纯消耗 0、部分返还 4、官方已覆盖 0、纯低层恢复 19，全部 PASS。
- 0.4.4 为 `46,592` B / `CF223767...CE3966`；0.4.3 exact rollback 已冻结并在游戏进程连续两次为 0 时部署。源码/构建内均为 149/149 PASS。
- 桌面 `C:\Users\shenc\Desktop\失落城堡2工具箱 1.5.13-魔晶石回蓝测试版` 与项目包逐文件零差异；EXE 版本 1.5.13。100% 主战斗页和 200% 四人 HUD 均 `VERIFIED`。
- GitHub `v1.5.12` 预发布在下载数仍为 0 时已将标题与首行改为“暂缓下载：魔晶石恢复漏记”；不删除、不移动 tag。1.5.13 真实复测通过后才进入新的 commit/push/Release。

## 2026-08-29 Bridge 0.4.5 / 工具箱 1.6.0 收口

- 0.4.4 的第二个真实反例来自普通太刀、无加蓝宝藏的新局：游戏为 `105/105`，HUD 消耗已到 `144`、恢复仍为 `0`。冻结日志显示第一次 `48` 消耗后当前 `57`，下一次消耗前连续观测已到 `95.513`；恢复发生在两次技能之间，根操作入口/出口仍为净负，故 0.4.4 的 root-local 公式不足。
- 0.4.5 不增加 Hook：官方耗蓝回调把权威扣蓝后值写回连续基线；根操作结束时同时计算 rooted recovery 与 sequential recovery，并扣除官方已覆盖量。编译反射六臂包含太刀 `38.513`、`24.35785675`、魔晶石净零 `19`、纯消耗 `0`、官方已覆盖 `0`、纯 runtime gain `19`，全部 PASS。
- 0.4.5 DLL 为 `47,104` B / `A6484B75...25A801`；部署前后游戏与工具箱 exact name + path 连续两次为 0。作者完成普通太刀实测，截图为总伤害 `69,634`、Boss `26,990`、承伤/回复 `155/200`、法力消耗/恢复 `762/763`，并说明伤害差异来自中途继续对局。关闭日志 `208,919` B / `76C3F50C...59F0E62` 明确包含 `84` 与 `43.3125` 等有效回蓝，判 `R-PASS`。
- 1.6.0 将“玩家实时属性与队友面板”从 1.3 升到 2.0（作者懒虫桑，DLL `26,624` B / `ED2183DD...10194`），操作改为点击玩家名字并修复房主偶发缺失。新下载的诅咒银币独立包内仍声明 v1.5.0，且早于当前整合包同版本构建，按“同功能族只保留最新”继续使用现有 `16,896` B / `0ECEF204...72AAC`，文案明确每局首个诅咒房保底与配置开关，不新增重复条目。
- 新增显式 `panel_hotkey`：只为打开设置/UI 的 MOD 提供“打开 MOD 面板”；未安装、游戏未运行、安装晚于当前游戏启动、正常已加载分别进入提示安装、启动游戏、提示重启、聚焦游戏并代按快捷键。直接丢钱等动作键不登记。用户 `lc2-mod.json` 可选 `interaction.panel_hotkey`，已有格式说明和导入→登记→隔离安装→卸载回归。
- 任务栏图标新增原生 `20/40/96` 像素层，与既有 `16/24/32/48/64/128/256` 合并，避免 Windows DPI 临时缩放。最终 exact H2/H3/H4 五臂覆盖 MIN100、125%、150%、175%、200% 与四按钮状态，几何和像素均 `VERIFIED`。
- 唯一 different-owner 初审曾判 `RELEASE HOLD`：重复 modifier 可登记但运行拒绝、manifest 绕过 64 文件/128 MiB 门、Bridge notice 旧版本、3 个 README EOF、fresh-clone 前置条件和 inventory 旧版本。随后已共用运行时快捷键解析器、把载荷门移到共同出口、增加三类负控并修正文档；重建后全量 `164 PASS`，package runtime/MOD 与原始 2.0 RAR 导入 PASS，同一审计席位窄复核最终为 `VERIFIED / RELEASE PASS`。

## 2026-08-30 v1.6.0 发布与发布后第 50 个 MOD

- 同一独立审计席位最终签发 `VERIFIED / RELEASE PASS`；提交 `3d67677` 已推送，tag `v1.6.0` 与 `origin/main` 指向同一提交。正式 Release 资产 136,933,435 B，远端 digest 与本地 ZIP SHA-256 `3352565A…90E0` 一致。
- `失落城堡2伤害统计v1.6.4-逐房强制官方校准修正版.dll` 是纯 DLL，59,392 B / `91576442…A11`。项目只静态参考其多人身份、官方锚点、逐 hit 兜底与重连分段，不复制其累计、倍率、状态文件或游戏内 UI；自有 HUD 单人口径仍来自官方事件、结算和作者多轮实战校准，真实 2P–4P 仍未校准。
- 新来源 `纵冰之杖加强，大幅增加冰锥数量.zip` 为 20,355 B / `9E3BF2D0…D79C`；唯一载荷 `IcePillarCrash.dll` 为 47,104 B / `F4C53E57…D6253D`，内嵌插件版本 1.16.0。静态字符串明确冰锥 6→12、冷却 3→1 秒，无设置面板或快捷键；DLL 未见作者署名，按 QQ 上传截图暂显示“大萝卜鸡”。
- 本地源码目录现为 52 条目、53 载荷、3,375,565 B；“我不是药神（测试版）1.0.0”与“暴击字体改紫色 1.0.0”进入下一包候选。新收到的 `LC2HexAugment.dll` 与既有 2.7.6 载荷均为 40,960 B / `50CEB677…E04ECC`，不重复收录，只提升实战排序并补齐它与三项现有 MOD 共用 F1 的说明；紫色暴击 DLL 为 13,824 B / `5863D6A9…35EECB`，无快捷键、纯视觉。第三方 DLL 均未执行，真实游戏效果 `NOT RUN`。已发布 v1.6.0 仍保持 49 条目，不回写。
- “LC2 增强计划”因群友使用较多，社区排序从优先级 180 提升到 110，位于玩家实时属性之后、一键丢钱之前；原有灵魂石/金币工具位置不变。
- 下一版 MOD 表格将“作者”表头与每行作者值统一居中；版本、状态、列宽、详情卡及动作不变。该调整只进入发布后源码候选，不修改 v1.6.0 资产。

## 2026-08-30 Bridge 0.4.6 通用回蓝/HP 诊断候选

- 作者实机取得“被诅咒的怀表”后，游戏周期回满但 HUD 在消耗 `336` 时恢复仍为 `0`。冻结 0.4.5 日志 164,635 B / `961FE437…FEF7`：耗蓝序列明确从 `current=4` 的基线跳到下一次 `last_observed=100`，中间没有 recovery/runtime_gain。
- 作者随后无怀表新开一局，HUD 消耗 `144`、恢复 `0` 时游戏为 `88/110`。新快照 313,008 B / `A8BCD946…40AB6`：第二次耗蓝前基线已经从 57 恢复到 `81.35785675`，后续多次耗蓝前回到 110，recovery/runtime_gain 仍为 0；确认是通用零变化观察缺陷，不是怀表分支。
- 根因已由源码证伪：零变化观察已经计算 fallback，却被只看 `requested/effective` 的提前返回丢弃并更新满蓝基线。0.4.6 最窄候选让 fallback 非零时继续发事件，不增加 Hook 或怀表特判。
- HP 误计假设已撤回：作者确认“自愈”刻印在低于 35% 时逐次正常 `+1`，完整局还死亡/复活一次；官方/工具箱承伤均 `308`、回复 `398`，回复不与承伤守恒。最大生命变化只是一度相关线索，不足以授权改变 HP 算法。
- 0.4.6 保持 0.4.5 的 HP `effective=after-before` 聚合，仅增加 `[LC2CB-HP]` requested/before/after/max 日志。同类装备、刻印、药剂与复活的真实正向 HP 继续累计。
- 收窄后的 0.4.6 Release 构建为 47,616 B / `7DFF3253…C98B4`，隔离 SDK 6.0.428 为 `0 warning / 0 error`，Hook 数仍为 14。MP 合同覆盖 fallback 非零零变化、全零和普通消耗；Python 全量 165 项 PASS。
- 0.4.6 已在双零进程门后部署并回读，0.4.5 回滚为 47,104 B / `A6484B75…25A801`。另建桌面 `失落城堡2工具箱 1.6.0-Bridge0.4.6测试版`，相对正式盒子只改运行时清单与内置 Bridge 两文件，self-test 退出码 0。下一实机以普通无怀表新局的法力恢复非零/不双计为主；HP 只采诊断，不作为修复宣称。
- 实机已得到普通回蓝与容量变化正控：截图 HUD `461/550`、游戏 `189/189`；日志精确拆分普通恢复461与容量正向变化80+9，`100+550-461=189`。分解魔晶石后最大法力回到105且没有新增 runtime_gain。该部分判 `R-PASS`，本局仍在继续。
- 同局 Boss 房出现官方/HUD承伤 `33`、局内恢复 `39`。0.4.6 HP 日志将 19 个正向事件精确闭合为 `38.5444756`，所以恢复显示本身正确且不是小数约分造成差额；最后已观测 `56.7000046` 到后续恢复起点 `18.1555290` 也相差同值。由于当前 BepInEx 日志没有逐 hit 的 `ori/real/applied`，也不记录 DamageProcess 内负向 HP，约 `5.54` 的具体来源仍不可唯一归因，禁止先称官方 Bug。
- 回营后恢复从 `39` 跳到 `141` 已单独闭合：游戏先执行 `55.3000031→158`（有效 `102.6999969`），下一行才触发 `round_start is_camp=True`。这是 0.4.6 会话边界过滤 `R-FAIL`，与 Boss 房承伤差额独立；下一候选只按生命周期排除营地补满，不得吞战斗内回复/复活。
- 对应冻结记录：`artifacts/runtime-captures/2026-08-30-hp-official-vs-actual-0.4.6/README.zh-CN.md`。
- 0.4.7 最窄候选已构建并部署到游戏目录及同一桌面测试盒子：48,640 B / `A917E813…18CA7`，0.4.6 独立回滚为 47,616 B / `7DFF3253…C98B4`。RoundStart 同一目标用 prefix 在游戏内部回营补满前关闭活动窗口，postfix 保持原初始化；taken 记录 `original/real/hp_before/applied/settlement`，HP 记录非零负向及 `in_map/inside_damage`。Hook 目标仍14，聚焦11、全量167、Release构建与盒子self-test均 PASS；真实回营/单击 `NOT RUN`。
- 测试盒子目录名暂保持 `失落城堡2工具箱 1.6.0-Bridge0.4.6测试版`，内部 manifest 已明确为 `LC2CombatBridge 0.4.7-test` 且内置 DLL 与游戏目录/候选哈希一致，避免另建相似目录。部署回执见 `artifacts/runtime-deploy/2026-08-30-bridge-0.4.7/README.zh-CN.md`。

## 2026-08-30 Bridge 0.4.7 实战反例与 0.4.8 最窄候选

- 0.4.7 三次受击的官方逐击向上取整为 `37+47+37=121`；处理后实际 HP 变化与局内有效回复均精确为 `119.1097946`，UI 显示 `119`。该双口径已闭合，不再调整承伤或恢复聚合公式。
- 回营补满仍发生在 RoundStart prefix 之前：日志先记录 `54.6000023→156`、有效 `101.3999939`、`in_map=True`，下一行才是 `round_start is_camp=True`。0.4.7 判 `SETTLEMENT REFILL R-FAIL`。
- IL2CPP 当前元数据确认独立 `StageFlowEvent.GameRoundEndBackPreLoadCamp` 与无参 `PlayerManager.OnGameRoundEndPreLoadCamp()` 回调。0.4.8 在该回调 prefix 关闭旧活动窗口，保留 RoundStart 末端兜底；既有 HP Hook 同时记录有界 `changeSourceStr`，不按满血数值、Boss、装备或道具特判。
- 0.4.8 聚焦 12 项 PASS；隔离 SDK 6.0.428 Release 构建 0 warning/0 error；Mono.Cecil 回读版本/15 target/预加载 prefix/source token PASS。候选 49,152 B / `7740BA3E…6CE55`。游戏与测试盒仍运行，未部署、未执行测试盒 self-test；下一实测只需一次缺血短局退出。
- 社区目录现为 52 条目、53 载荷、3,375,565 B。新紫色暴击 1.0.0 为纯视觉、无快捷键；新收到的海克斯 2.7.6 DLL 与既有载荷逐字节相同，不重复收录，只提升排序并明确它与三项现有 MOD 共用 F1。MOD manager 20 项 PASS；第三方真实游戏逻辑 `NOT RUN`。
- 0.4.8 缺血短局已闭合：局内 48 个正向 HP 事件合计 `68.9060974`，HUD/结算显示 `69`；两次官方承伤 `46+46=92` 与游戏一致。日志顺序为 `round_end_preload_camp`→回城补血 `91.1367874/in_map=False`→`round_start is_camp=True`，补满未进入统计。判 `SETTLEMENT REFILL EXCLUSION R-PASS`，回执位于 `artifacts/runtime-captures/2026-08-30-settlement-refill-excluded-0.4.8/README.zh-CN.md`。

## 2026-08-30 工具箱 1.6.1 精确候选冻结

- exact package 为 `package/失落城堡2工具箱1.6.1-实时数值监测+一键MOD安装`：1,760 文件、`166,606,890` B、config0；EXE 6,463,717 B / `46525496…46C8D`，固定/字符串版本均为 1.6.1。
- 随包 Bridge 为 0.4.8 / 49,152 B / `7740BA3E…6CE55`；社区目录为 52 条目、53 载荷，海克斯 `50CEB677…E04ECC` 只收一份，紫色暴击 `5863D6A9…35EECB` 位于视觉类排序。
- 最终构建内全量 171 项与 source self-test PASS；精确包清洁运行时首次/重复安装、console false、不同核心写前阻断 PASS；52 项逐个安装/卸载、无关插件保留与原始 RAR 导入登记 PASS。
- 多人新增 2/3/4 人各 250 轮 distinct owner 精确累计，以及四人 2,000 事件分 10 批活性测试；重复身份/事件、foreign session、schema error、queue overflow、stale heartbeat 均显式拒绝或报错，不静默漏算。真实 2P–4P 主客机仍为 `NOT RUN`。
- r11 精确包 UI 回执覆盖 100% 最小海克斯、200% 紫色、150% 四人主面板、200% 四人 HUD；四臂均绑定 EXE `46525496…46C8D` 并按时退出。正式像素证据使用回执哈希一致的 `window-internal.png`，不使用被其他前景程序遮挡的环境实屏。
- 实现 owner 判定为 `IMPLEMENTATION GREEN / AUDIT PENDING`。下一步只派一个 different-owner 对冻结源码、精确包、Bridge 实战、多人与 UI 做综合只读审计；审计 PASS 后才创建 ZIP、提交、push 与 v1.6.1 Release。
