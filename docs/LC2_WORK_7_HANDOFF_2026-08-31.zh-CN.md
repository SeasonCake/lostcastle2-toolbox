# LC2 工作 7 交接（2026-08-31，Asia/Shanghai）

> 历史快照：工作7交接已完成，以下候选、部署和开放门不表示当前状态；当前行为以正式 v1.7 源码与发布说明为准。

## 1. 角色、目标与不可退让约束

- successor角色：接手工具箱1.6.3多人统计根因收敛、新MOD静态接入与最终发布前审计。
- 用户明确要求：不要再反复让作者完整实测；先充分利用冻结日志、截图、游戏interop/元数据、第三方参考DLL与离线回放，把数据值和P位完全对齐。用户明确允许开multi-agent。
- 当前0.4.14 r3已被真实四人局判`R-FAIL`，不得commit/push/Release，不得把自动测试绿外推为多人准确。
- 游戏或任何工具箱进程运行时禁止部署。每次部署前重新执行两次exact name+path进程0检查（间隔约10秒），不要把本文时间点当当前真相。
- 保留已闭合的官方承伤121/实际HP变化119双口径、0.4.8回营补满排除与MP证据；不重跑、不改公式，不做角色/武器/Boss/道具/固定数值特判。
- 第三方二进制、日志、截图、package不进Git；仅README/合同/源码/测试可提交。当前不stage。

## 2. 仓库、Git与公开发布状态

- 仓库：`<repo>`。
- branch：`main`；已发布基线/HEAD/origin/main/tag v1.6.2：`758db3ae731613e2c3e4fcbfb9d7fd0058286f66`。
- v1.6.2 Release已被0.4.12真实多人证伪，下载数仍为0时改成预发布，标题“暂缓下载：v1.6.2 多人伤害少算，等待 1.6.3 复测”；tag/提交/资产保留。
- 当前working tree为v1.6.3/Bridge0.4.14未提交dirty实现与证据文档。successor先重新`git status --short --branch`、`git diff --check`，不得重置/清理。
- 现有全量：188/188 PASS；C# SDK6.0.428、当前interop、Release为0 warning/0 error。这些只证明合同/构建，不证明真实准确。

## 3. 当前部署与本地候选（时间点记录，必须重核）

- 当前游戏目录Bridge：0.4.14，59,392 B / SHA-256 `343B69EF9FBBB982BB323F8EE291DC37B9783109A775A71A102F46706A3C6E24`。
- PDB：24,816 B / `66FD95BC10DDE9FE8B2E97C8AE8F479EFD4917505100049C3ADC25638F4D8F01`。
- 0.4.13 r2 rollback：58,880 B / `A0738C534040B066F2B90B460E00CAA6D764E2E4E5F2C1563D78A0982EA7C96F`，位于`artifacts/runtime-deploy/2026-08-31-bridge-0.4.14-official-slot-map-r3/`。
- 当前项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 当前桌面r3：`<desktop>/失落城堡2工具箱1.6.3-多人官方槽位测试版-r3`。
- 包/桌面：1,761文件、166目录、166,644,611 B、config0、逐文件差异0；EXE6,472,447 B / `18917B4C54216C714925E55058991BC3DA656EA10DB2E29B8CCA68BF073044A1` / 1.6.3。
- runtime manifest：`A1C2391051D62C8C8F30464835BC3FBDC70ECEC95E5396D4095A77FD9C0FBF63`；包内/游戏Bridge同为`343B69EF…3C6E24`。
- 当前用户消息到达时游戏/盒子在运行，已冻结live日志；successor必须重新查进程。不要部署0.4.14之后的任何东西，直到当前进程真正关闭且新实现已审计。

## 4. 第一轮发布后R-FAIL：0.4.12普通怪少算

证据目录：`artifacts/runtime-captures/2026-08-31-multiplayer-undercount-degraded-0.4.12/`。

- 关闭日志12,028,286 B / `9A6097C725AE52F41D82FE74A7C87EC0CC53E769BAFB8F8B260F41F660C0FE12`。
- HUD三人总伤害：7,293,748 / 9,924,156 / 9,597,741；官方：8,475,632 / 10,035,357 / 13,163,701；全队少4,859,045。
- HUD/官方团队Boss：12,173,916 / 12,114,545，只差59,371；非Boss差4,918,416。逐击`min(realDamage,hpBefore)`不能作为最终官方主卡。
- 唯一黄色code是`damage_stack_mismatch`；无queue、snapshot missing、fatal。源码证明它只清parent/depth栈，后续`EmitDamage`仍执行；0.4.13起改为`damage_event_skipped=False`计数诊断，不再标黄。

## 5. 第二轮R-FAIL：0.4.13 r2官方record塌缩slot3

证据目录：`artifacts/runtime-captures/2026-08-31-official-sync-slot-collapse-0.4.13-r2/`。

- live/closed日志6,306,973 B / `D78C2427F5D25FB41D73C2E5B2D5D7EC63B684890D2E638E4DB431B73317E7D2`。
- 54次`LC2CB-OFFICIAL`均slot0–2 null、slot3单值，最终slot3=40,851,600/Boss14,880,152；本机官方仅11,929,682/4,250,377。
- 根因已闭合：0.4.13优先使用`AdventureRecordPlayerData.mID`，该字段不是当前Player网络身份。0.4.14改用record.mIndex主映射、dictionary pair.Key仅作ID兜底。
- 早期本机31,835、P位1,635/10,008/8,780，却显示100%/5%/31%/27%；partial official时team denominator错误退回本机/单一路径。0.4.14改为roster存在时求各P位显示值之和。

## 6. 最新第三轮R-FAIL：0.4.14 r3仍没有远端官方数据

证据目录：`artifacts/runtime-captures/2026-08-31-official-slot-r3-stale-crossrun-0.4.14/`。

- live日志9,738,366 B / `67218B63E68B9FF654824E20DA4E6B0356BEA99A0560EF6D7778001013DBBD62`。
- 截图哈希：早期`C14D4BAD…7422B5`、最终卡+HUD`15F2A8C5…047DF1`、新MOD`176C63C5…75F26`。
- 0.4.14 identity：`343B69EF…3C6E24`，确认作者运行r3桌面目录。
- 最终官方四卡：
  - 本机/P1：10,380,702 / Boss3,449,829
  - P2：1,243,381 / 565,440
  - P3：10,195,871 / 3,946,071
  - P4：2,303,119 / 770,698
  - 团队：24,123,073 / Boss8,732,038
- 最终HUD：本机32,669,460/Boss11,901,301；P2 8,145,972/4,125,150；P3 7,942,224/3,712,816；P4 16,606,274/7,798,165。明显不是官方值，且用户指出部分非本人数据仍归主玩家。
- 决定性日志：54次摘要全部`network_records=0 fallback_records=1 index_base=null raw_indices=`。只有slot0有fallback，最终slot0=32,669,460/Boss11,901,301，恰等于HUD本机主卡；P2–P4始终官方null。
- 结论：`StageNetworkCtrl._multiRoundDataDic`在这条真实路径为空；`SettlementDataMgr.mCacheRoundData`单fallback不是逐玩家本机官方值，而是团队/当前缓存汇总，禁止再作为某个player official。0.4.14的mIndex修复没有机会生效。
- P4 HUD值16,606,274与前一轮0.4.13 r2的P4观察值完全相同，强烈提示跨局旧token/旧观察累计或游戏缓存复用；必须从session_id、Bridge BeginGameSession、Python `_clear_session_metrics`、player token/fingerprint和slot替换全链查清，不能称巧合。

## 7. 必须并行完成的根因工作（用户已授权multi-agent）

建议successor同时派最多3个只读agent，root整合并自行验证：

1. **游戏权威数据面**：完整反编译/解析`失落城堡2伤害统计v1.6.4-逐房强制官方校准修正版.dll`的`ReadGameSaveBaseline`、`ReadNetworkAuthoritativeData`、`ReadSettlementRealtimeFallback`、`PollDamageIfNeeded`及游戏`AdventureRecordData_SaveData.mCurAdventureRecordSaveData`/record player list。回答：live远端是否有官方值；最终结算何时可读四人`mDamageValue/mBossDamageValue`；不要复制第三方UI/持久化代码。
2. **逐击owner与事件面**：对照参考DLL`ResolveSlotForAttackerCreature/OnPerHitDamageEvent/OnPlayerForwardedHitEvent/OnTargetBeHitEvent`，检查我方`mAtkerInHierarchy→OwnerEntity→Master`是否把召唤/投射错误分配；检查官方attacker callback的注册对象/发送者是否比DisposeHitInfo owner更权威。目标是live P位准确，不能依赖最终卡才纠正。
3. **跨局/聚合状态机**：用两轮冻结值构造回放，审计Bridge session生成、party fingerprint、player token reset、Python foreign-session/new-session清理、inactive token与same-slot grouping、official partial denominator。解释P4 16,606,274跨局重复；构造会失败的正/负控后再修。

successor root必须逐条验证agent结论；agent不得同时编辑同一文件。没有闭合上述三面前不要生成r4，更不要请求作者完整实测。

## 8. UI合同（用户已明确）

- “队友1/2/3”已改为真实slot标签：本机`自己 · Pn`，活动`P1–P16`，离队`Pn（离队）`。
- r3合成slot3 UI证据：`artifacts/ui-acceptance/2026-08-31-toolbox-1.6.3-official-slot-r3/`；P4与P1/P2/P3显示和比例合计100%通过。
- 该UI结构保留，但数据值当前R-FAIL。以后若只改数据不加控件，仍需exact包抽核主界面/HUD；最终冻结再执行完整Windows UI验收。

## 9. 新MOD待办

- 文件：`<local-mod-library>/怪物宝藏v10.5（更新详情且看压缩包内txt文件，这波啊，是怪物大加强有bug找作者反馈）.rar`。
- 大小：26,649 B；上传截图显示来自“懒虫桑”。
- 尚未静态解包/读取说明/识别DLL、作者、版本、快捷键、依赖、冲突或真实功能；未执行、未纳入catalog/package。
- 按现行统一规则：先静态检查压缩包完整性和成员，排除BepInEx/core/cache/cfg，只纳入最小功能载荷；明确“有bug找作者反馈”的风险文案。第三方真实逻辑仍NOT RUN。

## 10. 下一步与发布门

1. 新任务先完整读最近AGENTS与本文，再重查Git/进程/部署/log身份。
2. 完成三面并行只读调查，写出一条可证伪的数据链：游戏源→slot→session→协议→聚合→UI。
3. 先用冻结两局和合成跨局做离线回归；新增checker必须有known-good和positive control。
4. 只有离线证据闭合后才构建新Bridge/包；进程双零后部署。先做一到两个房间的短正控，日志自动判定映射是否多slot且比例守恒；短正控不通过就停止，不让作者打完整局。
5. 短正控通过后才请求一次最终完整结算；随后exact package/UI、唯一different-owner综合审计。
6. 审计PASS后才commit、push、创建新Release并恢复latest。v1.6.2保持“暂缓下载”预发布，除非后续发布策略明确变更。
