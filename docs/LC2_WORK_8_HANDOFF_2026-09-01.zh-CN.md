# LC2 工作7→工作8 完整交接（2026-09-01）

> 历史快照：记录 2026-09-01 的工作7→工作8交接，已被正式 v1.7 源码、架构和发布说明取代，不表示当前发布状态。
>
> lifecycle at recording: `current / work7-archived / work8-cold-start-pass`
>
> lineage: 工作7 → 工作8（本地任务标识已从公开档案移除）
>
> role: 工作8是唯一LC2产品调查/source owner；不是formal auditor，不替代作者实机输入。

## 1. 作者最新目标与停止点

作者因工作7持续响应很慢，明确要求建立LC2工作8 successor。最新真实观察：

- r11完整多人局结算后，HUD最终四项看起来与官方卡对应；
- 但结算前本机约`1100万 / 41%`，其它人也有一千多万，作者判断过程不正确；
- 开局早期本机占比也明显偏高；
- 作者要求确认过程是否有记录并继续闭合。

工作7已收到停止指令并于本交接前变为`idle`；工作8完成冷启动身份确认后，工作7已更名
`已退役｜LC2 工作7 (2)`并真实archive。不要恢复或再向工作7派产品任务，不要让两个窗口并发写同一树。

工作8冷启动回执：已确认本交接目标、r11过程R-FAIL/final官方PASS分层和首个离线known-red/known-good
探针；当前为唯一active owner。

## 2. 冷启动唯一读取顺序

工作8只需完整读取：

1. workspace `<workspace>/AGENTS.md`；
2. repo `<repo>/AGENTS.md`；
3. 本handoff；
4. `artifacts/runtime-captures/2026-09-01-r11-process-owner-mismatch-final-correct/README.zh-CN.md`；
5. `docs/LC2_WORK_7_R11_NEXT_RUN_RESET_CHECKPOINT_2026-09-01.zh-CN.md`；
6. 实时`git status`、candidate/installed/process identity。

不要重放工作7全部图片聊天、r3–r10完整历史或旧编年式current handoff。需要实现细节时再读上述README
链接的冻结ZIP/日志与相关source/tests。

## 3. 实时Git与候选身份

记录时点：

- repo：`<repo>`；
- branch：`main`；HEAD=`origin/main=v1.6.2=758db3ae731613e2c3e4fcbfb9d7fd0058286f66`；
- 工作树：工作6/7连续未提交范围，记录前约`28 tracked +47 untracked roots`；本handoff/evidence root会
  再增加untracked入口。禁止reset/clean、`git add -A`、整体stage或吸收不明路径；
- Toolbox：`1.6.3 r11`；
- Bridge source/package/desktop/installed：`0.4.20`；
- installed DLL：73,216 B / `17DF64A11C2BD35D46C3AF252420B0AE5E056FC508D9032C62EDDF28C12CC51C`；
- installed PDB：28,288 B / `5127A5D6BE04E47CBFBBD095F464FDB4EED49964F452CFB9128027F2C202C34C`；
- desktop：`<desktop>/失落城堡2工具箱1.6.3-新局归零自动归档版-r11`；
- EXE：6,485,067 B / `44E40FAC1A64542AF3EECBB39C43A436D20960481004158F56D6FF6FF678D92F`；
- 0.4.19 rollback：`artifacts/runtime-deploy/2026-09-01-bridge-0.4.20-next-run-closing-release-r11/`；
- 本交接冻结时游戏/工具箱相关进程=0。

尚未commit、push或新建Release。`v1.6.2`继续不是可推荐稳定多人版本。

## 4. r11已闭合与必须保持

### 已闭合工程门

- r11修复上一局closing gate不解除导致下一局继续累计；
- Bridge0.4.20已双零部署；
- pytest225项+37 subtests、build内225项；C# 0 warning/0 error；
- package self-test/runtime正负控；项目包与桌面1,761文件逐项一致；
- r10孤立`session_ended`归档风暴修复继续保留；
- r8首次完整final冻结/原session token保留逻辑继续保留。

### 必须保持

- final官方权威只在exact `SyncAdventureRecordDataEnd`后消费完整save list；
- first complete accepted final必须sticky，后续roster降级不能撤销；
- party snapshot中本局local=`player-4 / P4`；不回退到`mIndex`单独判slot；
- 匿名归档不采集昵称、平台ID、聊天或网络地址；
- 手动导出不重置聚合，不删除旧档；
- 不改现有UI布局/字段顺序。当前截图问题是数据语义，不是视觉布局。

## 5. 最新完整局的决定性证据

evidence root：

`artifacts/runtime-captures/2026-09-01-r11-process-owner-mismatch-final-correct/`

### 5.1 过程记录完整

- 归档内的 session key 与 session id 已交叉一致；原始运行标识不进入公开记录；
- 15:30:16开始；16:36:13手动ZIP；
- 64,761 events / 47,405,830 raw event bytes / `events_truncated=false`；
- 游戏LogOutput写到16:35:35；
- 因此无需作者重打完整局，先离线闭合。

### 5.2 早期截图被事件流exact复现

15:33截图：本机89,257/84%，P1=6,434、P2=7,427、P3=3,398。按截图墙钟映射到
`monotonic_ms≈692613`，事件流求和得到完全相同的数值和83.80/6.04/6.97/3.19%。

结论：开局高占比是过程数据真实状态，不是截图/crop/rounding问题。

### 5.3 结算前observed与final official

| player | observed | official | delta |
| --- | ---: | ---: | ---: |
| 本机P4 | 11,610,684 | 9,732,171 | **+1,878,513** |
| P1 | 12,257,746 | 15,548,016 | **-3,290,270** |
| P2 | 2,400,402 | 2,647,181 | -246,779 |
| P3 | 1,770,725 | 1,845,895 | -75,170 |
| team | 28,039,557 | 29,773,263 | **-1,733,706** |

final截图中HUD与官方四卡逐项对应，final authority/freeze可判PASS；过程owner/coverage明确R-FAIL。

### 5.4 当前checker假绿

现有`check_lc2_multiplayer_probe.py --require-final-official`同时给出：

- owner callback门PASS：24,475/24,475 settlement/registered/matched，四slot conflict/unresolved=0；
- final official门PASS：4 records、4 identity matches、4 published slots；
- 但逐slot observed与official显著不一致。

这直接否证“registration callback内部自洽即可证明过程owner正确”。工作8必须先补离线差值门，让本局
known-red；不能沿用旧checker PASS签过程正确。

## 6. 工作8首个问题与探针顺序

当前问题：

`为何过程事件将本机P4高算约1.88M，同时P1少算约3.29M、团队少算约1.73M，而最终官方四槽正确？`

按以下顺序收敛：

1. checker先加入逐slot`observed_damage_dealt/observed_boss_damage` vs final official差值，当前局known-red；
2. 用至少一条此前真实逐击/最终一致样本作known-good，证明checker不会普遍报红；
3. 将P4正delta与P1/团队负delta按`hook_path/source_token/actor_entity_id/source_entity_id/forwarded/
   room/time`分桶，定位首次分岔；
4. 核registration root对远端本体、变身、召唤和代理actor的语义，不以callback自洽替代官方credit；
5. 先离线证明最小根因，再决定是否需要Bridge/source修复；禁止新增宽Hook、角色/武器/地图/Boss/数值特判；
6. source修复后跑focused正反控、全量、C#和package门；只有需要真实runtime时才使用一到两个房间短正控，
   不要求完整长局；
7. 不复用当前known-red checker PASS，不让final官方覆盖掩盖过程失败。

## 7. 角色、阶段与审计

- 工作8是唯一调查/source owner；不要提前派第二产品owner；
- 可在作者已选择的本地终点内连续完成调查、最小source、tests、package、rollback、可逆部署和短smoke；
- 游戏操作属于author input，说明一次精确恢复条件即可；
- exact source/package/runtime冻结后，只派一个different-owner综合审计；
- commit、push、Release、公开分发仍是独立阶段；当前未授权；
- 三个新MOD继续只读预备，不进入该多人正确性主线。

## 8. 仍开放的门

1. r11过程owner/coverage：`R-FAIL / primary blocker`；
2. LC2目标人口真实smoke receipt：`implemented-but-unmeasured / pending`；
3. r11同进程两局reset：本轮新session已建立，但未单独冻结作者原要求的两局短receipt，保持`pending`；
4. unique different-owner final audit：not run；
5. owned-path inventory、index/fresh-clone/package/desktop/archive identity：not run；
6. commit/push/new Release：not run；
7. 三个新MOD真实运行与公开再分发：not run/deferred。

## 9. cleanup-disposition

- `keep-until`：工作8消费本handoff、现有known-red形成可重放checker，并冻结下一source/candidate身份；
- `safe-remove-after`：本文件不授权删除截图、ZIP、日志、partial、r3–r11 artifacts或旧rollback；
- `unique-evidence`：本局首次同时保留早期84%、结算前41%、observed-vs-official逐slot与正确final；
- `generated-large-paths`：新evidence root约13.43MB；其ZIP内部承载47.4MB event stream；
- `recovery-source`：本repo evidence root、桌面r11归档和游戏BepInEx日志。

## 10. Not run

本交接只做只读调查和证据复制；未修改产品source/tests/checker，未构建、部署、启动游戏/工具箱，未
commit/push/Release，未签发多人过程PASS或发布裁决。
