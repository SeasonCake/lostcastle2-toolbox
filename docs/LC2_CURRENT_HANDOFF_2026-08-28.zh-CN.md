# LC2 当前检查点（2026-08-28 17:02，Asia/Shanghai）

## 角色、目标与阶段

- 当前角色：LC2 工具箱本地源码、Bridge 候选和实机验证的协调实现者。
- 当前目标：桌面 `1.5.6` 已完成精确打包与验收，交作者做正常启动和后续自然游戏实测；低层回蓝兜底只在以后自然出现缺 callback 样本时被动验证。
- 当前阶段已完成：1.5.5 历史桌面交付、0.3.9 核心伤害/非战斗房实测、0.4.0 位置时序实测、0.4.1 部署与官方回蓝分支实测、HUD/宽敞默认源码验收，以及 1.5.6 最终桌面包交付。
- 当前授权边界：整理现有 LC2 改动并创建一个本地 checkpoint commit；未授权推送、公开发布、删除回滚证据或增加宽泛 Harmony Hook。

## 仓库与运行身份

| 项目 | 当前值 |
| --- | --- |
| 仓库 | `C:\xiangmuyunxing\biancheng\2026\lostcastle2-keyview` |
| 分支 / HEAD | `main` / `d6ce78e05a7d6bb5de33ccdeb11e831c0f6f8ab0` |
| 工作树 | 共享脏树；当前修改均未暂存、未提交，需继续保留其他任务内容 |
| 游戏进程 | `0`（2026-08-28 17:02 exact name + executable path 复核） |
| 工具箱 | 源码进程为 0；桌面 `1.5.6` PID `5996`，主窗与默认 HUD 均可见 |
| 游戏目录 Bridge | `0.4.1` runtime 候选；加载/pipe 与官方回蓝分支已实测 PASS，当前游戏已关闭 |
| 运行 DLL SHA-256 | `D499BA6BA2B21851F7C325F37503CEE418A66E4AA91A8D2A7C200FCC076B3744` |
| `Plugin.cs` SHA-256 | `34995B87138F6CC0ED5C096459FEF7DAC1D6EF2B80CD557802A364F6CDD9AE6B` |
| Harmony Patch 数 | `14`；0.3.4 的 `ResetDataBy` 探针已删除 |

本文所有 `artifacts/runtime-deploy/...` 定位都指向本机被 `.gitignore` 排除的二进制/回滚证据，fresh clone 不包含，故只作本机恢复定位，不声称是仓库链接。

0.4.1 候选、PDB 和 0.4.0 exact rollback 位于本机 `artifacts/runtime-deploy/2026-08-28-bridge-0.4.1/`。当前游戏目录已逐字节核验为 0.4.1。

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

- UI 待办（作者 2026-08-28 新增，当前仅记录、未开始）：按键显示窗口右上角增加“纯净模式”快速切换按钮，避免只能依赖可能与浏览器/其他软件冲突的 `F11`；保留 `F11` 是否继续作为备用快捷键，实施时再结合现有控制区宽度确认。
- UI 待办（作者 2026-08-28 新增，当前仅记录、未开始）：LC 战斗状态 HUD 首次打开的默认位置改为屏幕左上角，不再默认位于屏幕中间偏下；必须只改变无已保存位置时的默认值，已有用户保存位置不得被覆盖。
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
