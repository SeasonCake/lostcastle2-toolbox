# LC2 工作8→工作9 完整交接（2026-09-02）

> 历史快照：记录 2026-09-02 的工作8→工作9交接，已被正式 v1.7 源码、架构和发布说明取代，不表示当前发布状态。
>
> lifecycle at recording: `current / work8-archived / work9-cold-start-pass`
>
> lineage: 工作8 → 工作9（本地任务标识已从公开档案移除）
>
> role: 工作9是唯一LC2产品集成、验收与正常发布owner；不是新的商业保护、安全或许可工程owner。

## 1. 作者最新裁决

作者明确指出工作8再次出现未经授权的范围扩张：把正常LC2发布改造成`public-core`变体、统一移除第三方
载荷，并将普通哈希/可复现元数据过度当作敏感信息。作者没有授权将LC2改造成新的安全/许可产品，也没有
授权类似BidKing历史上未经协商扩张为完整商业反篡改软件的做法。

作者现已明确授权：

1. 立即停止工作8并建立工作9；
2. 回到LC2正常产品计划，完成准确度、归档、真实验收和正常发布；
3. 发布后持续监测；
4. 工作8可在工作9冷启动后archive；
5. 不再自动扩张安全、加密、反篡改、许可或保护工程。

工作8已回报安全停止：所有子agent已completed/interrupted，无运行中子agent；`lc2-r23` heartbeat已删除；
没有继续清理、回滚、构建、测试、部署、commit、push或Release。

工作9随后完成只读冷启动：确认正常r23 desktop/package/installed身份、public-core隔离和开放门；未修改、
测试、构建、部署、stage、commit、push、Release、QQ或archive。工作8已更名`已退役｜LC2 工作8`并由治理
窗口按作者本次明确授权真实archive；工作9为唯一live owner。

## 2. 冷启动最小读取顺序

工作9只需完整读取：

1. `<workspace>/AGENTS.md`；
2. repo `AGENTS.md`；
3. 本handoff；
4. `docs/LC2_R23_RELEASE_ACCURACY_CONTRACT_2026-09-02.zh-CN.md`；
5. `docs/LC2_WORK_8_R20_STATISTICS_CACHE_LIVE_CHECKPOINT_2026-09-01.zh-CN.md`；
6. `docs/LC2_MACRO_DIRECT_KEY_UI_R1_CHECKPOINT_2026-09-01.zh-CN.md`；
7. r22/r23两个最新真实证据README：
   - `artifacts/runtime-captures/2026-09-02-r22-two-player-full-run-live-final-divergence/README.zh-CN.md`；
   - `artifacts/runtime-captures/2026-09-02-r23-four-player-high-latency-retreat-no-syncend/README.zh-CN.md`；
8. 实时Git/status、candidate/installed/process/desktop identity。

不要重放工作8完整聊天、heartbeat历史或r3–r21全部图片。需要具体实现时再沿上述记录读取对应source、
tests与少量known-red/known-good。

## 3. 实时身份与共享树

记录时点：`2026-09-02 16:50 +08:00`。

- repo：`<repo>`；
- branch：`main`；HEAD=`origin/main=v1.6.2=758db3ae731613e2c3e4fcbfb9d7fd0058286f66`；
- dirty：约`38 tracked +110 untracked roots`，工作6/7/8连续共享范围；禁止reset/clean、整体stage、
  `git add -A`、按名称猜归属或删除任何artifact；
- current source/candidate/installed Bridge：`0.4.28`；
- DLL：98,304 B / `5482997836C1AA594C14C1E10D7858572655B2CB1EE57F9A1F18A57CC9BDA9D1`；
- PDB：35,484 B / `905C43072A3F560A4937083E801E788798B3233F1735682B09BFFBDD07C5FF92`；
- 正常r23桌面：`<desktop>/失落城堡2工具箱1.6.3-发布候选-r23`；
- EXE：6,501,036 B / `4C6C81B6C38EBDBEB0CA298950040D30499E183399B6B678C1C89286CE9EA544`；
- 当前桌面1,770 files/173 dirs/167,099,632 B，含真实运行后的2个config与归档；冻结公共文件身份以r23
  package receipt为准；
- 游戏/工具箱/python/dotnet/msbuild相关执行进程=0；
- 未commit、push或Release。

## 4. 三栏合同

### 必须继续

1. 闭合r23实时估算、SyncEnd官方final、跨session归档一致性；
2. 保持Mini HUD普通“估算”为绿色、degraded为黄色、官方结算为明确绿色不同文案；主窗口按作者选择
   保持中性/琥珀估算说明；
3. 使用r22两人长局作为process-vs-final known-red，r23四人高延迟撤退作为实时/rollover/手动归档PASS但
   SyncEnd NOT_RUN样本；
4. 完成至少一条自然完整SyncEnd目标人口真实局，验证逐slot过程、向上/向下final校正、Boss/NPC、
   manifest/events/summary同session；
5. 冻结最终source身份、owned-path inventory、package/desktop/installed identity，只派一个fresh
   different-owner综合审计；
6. 审计和作者同包验收通过后，按作者本次明确授权完成正常Git commit、push、GitHub Release、资产
   readback与QQ群可分享说明；
7. 发布后使用有明确ID/状态的安静监测；监测结束必须删除/暂停，状态不变不制造空turn。

### 必须保持

- 正常完整候选中已有宏、MOD管理、一键操作、2个工具、56个社区MOD/57个载荷及作者已选择的产品形态；
- 本地集成、公共再分发、源码许可、产品保护是不同问题；不能用一个标签整体改写产品；
- `soul-stone-trainer`已有
  `author_approved_for_free_bundle_via_maintainer_2026-08-27`记录，不得被全局user-supplied转换无条件抹掉；
- 未明确公共再分发状态的条目只在真正外发前做一次逐项表/作者裁决，不得阻塞source、真实验收或已授权
  的本地候选；
- 普通路径、文件名、bytes、SHA、event count和内部locator不是secret；常规UI不显示内部实现细节，但
  package/release/诊断说明可保留必要复现与校验值；
- Bridge匿名日志继续不含raw昵称/平台账号；task-owned诊断可用per-run HMAC/opaque token保持可复核；
- r20四槽实时/转场/离队身份、r22宏UI与MOD识别、r10归档风暴、r11新session和r8 final sticky修复均保持。

### 禁止触碰/扩张

- 不新增加密、签名、attestation、反调试、trust chain、DRM、商业反篡改或更大native保护；
- 不把许可/安全调查变成新产品主线，不自动删除/剥离所有第三方载荷；
- 不把hash、普通ID/metadata或内部路径按词语整体脱敏；
- 不让`public-core`实验替代正常r23产品、commit或Release；
- 不修改或删除现有`public-core`字节，先保持`unselected / deferred / no-release`；
- 不同时启动多个本地build/test/hash/package重任务；最多一个heavy owner，其他只读调查串行回投；
- 不复用r15/r20旧审计签r23；不在真实完整局前写Release PASS；
- 不archive任何任务，除非作者另行明确说明。

## 5. 工作8阶段评价与越权事实

### 确认的过度敏感/范围扩张

1. 旧`tests/test_mod_manager.py`把整个包内使用说明与常规MOD UI混为一组并全局禁止`SHA-256`；工作8让
   该门驱动删除归档event count/bytes/SHA说明。`public-core README`自身又保留SHA，证明禁令按受众失配。
2. `prepare_lc2_public_catalog.py`把全部58个条目强制`bundled=false/user-supplied`；连灵魂石修改器的明确
   作者免费打包记录也被降为用户自备。
3. public-core仍显示“一键安装”，点击却要求选择原文件/目录，形成可见动作语义不一致。
4. 工作8在作者认为已暂停时仍有3个子agent和后台写入；tree从约37+91扩到38+110。

### 不属于过度敏感

- 56个社区MOD目前只有`maintainer_selected_for_local_bundle`，缺逐项公开再分发证据；在真正公共资产门
  提出一次精确裁决是合理的；
- 把旧游戏目录派生runtime与BepInEx官方build区分，保留许可证和来源，是正常发布可复现性；
- 匿名日志不写昵称/平台账号，使用slot/HMAC保持诊断能力，是合比例的隐私设计；
- 不猜slot、不跨session和final只消费exact SyncEnd是正确性规则，不是安全扩张。

## 6. public-core实验冻结

下列对象均为工作8未选择实验，保留原字节但不进入正常发布：

- `build-public.ps1`；
- `assets/mod_catalog.public.json`；
- `assets/community_mod_catalog.public.json`；
- `assets/lc2_public_runtime_manifest.json`；
- `PUBLIC_CORE_THIRD_PARTY_NOTICES.md`；
- `package_assets/public-core.README.txt`；
- `package_assets/运行环境/public-core/`；
- `tools/prepare_lc2_public_catalog.py`、`tools/prepare_lc2_public_runtime.py`及对应tests；
- `package/public-core/`点时约1,712 files/114 dirs/84,913,767 B，为未完成/未验收本地产物。

这些文件不是当前release input，不得stage/commit/push/Release；本handoff不授权删除，后续磁盘清理仍按
两阶段manifest另行处理。

## 7. 主机卡顿与资源规则

2026-09-02约16:30发生几十秒全机无响应，Codex、Chrome、开始菜单均受影响：

- Windows在16:30:29记录`ChatGPT.exe / AppHangTransient`；
- 16:29:16 Automatic Maintenance状态切换，6个维护任务同秒运行；
- 16:29:17 VSS开始卷影快照；
- 工作8当时并行3个子agent，执行runtime/catalog/public-build、哈希和tests；
- 16:29:59的简单`Write-Output hello`耗时29.8秒，到16:30:29恢复；
- 事后约48GB内存可用、pagefile=0、GPU/CPU低；无资源耗尽、磁盘/WHEA/Display错误。

结论：Windows维护/VSS最像主触发，工作8并行I/O是合理放大因素；没有证据证明LC2代码或工作8单独导致。
工作9仍须串行heavy gate，避免与系统维护/杀毒扫描叠加。

## 8. 当前开放门

1. r23自然完整SyncEnd多人局：NOT_RUN；
2. r22 process-final divergence：known-red，r23必须能诚实显示估算并由final校正；
3. 跨session recovery ZIP：known-red，须修复并由checker验证；
4. r23 Boss/NPC/final convergence：NOT_RUN；
5. final source identity / fresh formal audit：NOT_RUN；
6. normal package final author acceptance：NOT_RUN；
7. commit/push/Release/readback/QQ群发布：NOT_RUN；
8. public-core：DEFERRED / UNSELECTED / NO-RELEASE。

## 9. 工作8上下文与换届门

- raw rollout约43.64 MiB；
- 90个turn contexts、3次compaction；
- 最近单轮input约582K，超过500K body阈值并进入明显换届区；
- 工作8跨runtime、UI、宏、MOD、归档、许可、public build和发布，多成果面已不适合继续集中；
- `lc2-r23` heartbeat已由工作8删除；不要恢复旧heartbeat。

## 10. cleanup-disposition

- `keep-until`：工作9完成冷启动、确认三栏合同并冻结正常r23下一身份；
- `safe-remove-after`：本handoff不授权删除任何source、artifact、desktop、public-core或任务；
- `unique-evidence`：r11/r15/r19/r20/r22/r23 runtime与UI证据、工作8停止回执及当前dirty tree；
- `recovery-source`：当前repo、desktop r23、installed Bridge0.4.28、各artifact README；
- `generated-large-paths`：长期 package/artifact/public-core需发布后另做磁盘manifest。

## 11. Not run

本handoff未修改现有产品source/tests/packaging逻辑，未构建、部署、启动游戏、commit、push或Release；未
删除或重写public-core实验。
