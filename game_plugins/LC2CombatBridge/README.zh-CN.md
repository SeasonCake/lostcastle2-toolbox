# LC2 Combat Bridge

这是工具箱战斗统计的只读 BepInEx 6 IL2CPP 本地桥接插件。

- 只观察已验证的官方造成/承受伤害、有效 HP 恢复、房间生命周期和结算 checkpoint。
- 不修改游戏参数、返回值、存档、网络状态或战斗逻辑。
- 事件仅通过本机命名管道 `LostCastle2Toolbox.Combat.v2` 发送，不写战斗事件文件。
- 不采集昵称、Steam ID、平台账号、网络地址或聊天内容；实体编号仅作为本轮进程内的临时命中关联值。
- 队列、单行和事件字段均有上限。单个快照、转换或checkpoint失败会把本轮标为可恢复的“有事件跳过”并继续；详细页只在当前区与下一区显示，Mini HUD 不显示。只有队列溢出仍fail closed。伤害嵌套栈错序只影响parent/depth诊断，不丢伤害事件，改为计数日志且不再把HUD标黄。
- 已安装/已发布的 `0.4.5` 保留由实战闭合的伤害、承伤、HP 恢复、房间位置与 14 个既有 Hook。玩家承伤与 HP/MP 资源观察只接收本地玩家根实体，队友只参与匿名伤害归属；20%/40%/65% 官方生命锁定产生的非受击负 HP 变化使用既有 `resource_operation=loss`，不进入“受击承伤”或“回复”。65% 锁血已完成 `49/140` 实机正控。法力按原始浮点变化累计并只在 UI 边界取整；恢复同时采用根操作对账和连续观测基线，并扣除同操作官方已覆盖量，覆盖官方恢复、闪避回蓝、同操作先扣后回以及两次技能之间的自然回蓝。普通太刀实测已得到法力消耗/恢复 `762/763`，HUD 保持实时。
- 已实测的 `0.4.6` 不增加 Hook 或道具特判。它修正零请求/零净变化的 MP 观察把已经识别的 fallback 恢复提前丢弃的问题；普通回蓝、怀表回满、魔晶石容量增加与分解负控已闭合。HP 仍按实际正向变化累计。
- `0.4.7` 实战确认 RoundStart prefix 仍晚于回营补满；官方承伤 `121` 与实际 HP 变化/恢复 `119` 已闭合为逐击入整与真实浮点变化的双口径，不改聚合公式。
- `0.4.8` 增加第 15 个、语义明确的 `PlayerManager.OnGameRoundEndPreLoadCamp` Hook，在游戏的 `GameRoundEndBackPreLoadCamp` 生命周期进入时关闭旧活动地图窗口；既有 RoundStart prefix 仅保留为末端兜底。HP 诊断同时记录有界 `changeSourceStr`，不按请求值、满血形态、Boss、宝藏或道具特判。缺血短局实测中，局内有效回复 `68.9060974` 显示 `69`，回城补满 `91.1367874` 明确为 `in_map=False` 且未进入统计，判 `R-PASS`。
- `0.4.9` 来自首次三人联机反例：0.4.8 的顶部把队伍 `819,706` 显示成个人总伤害，而游戏个人结算为 `576,627`；同时只有 `235,775` 归到自己、`447,459` 未归属。0.4.9 以通用有界关系遍历 `mAtkerInHierarchy / OwnerEntityInHierarchy / OwnerEntity / StandMaster / Creature.Master`，补回技能、投射物、召唤物和根玩家关系，并按 local/remote/unattributed 输出汇总诊断；不按角色、武器、召唤物名或数值特判。
- `0.4.9` 两个真实长局都在中途进入红色“异常”并冻结，其中第二局四人从头到尾无人离开，排除了离队必要性。0.4.10 将单个 snapshot/conversion/stack/checkpoint 问题改为显式 recoverable：日志写出 code、HUD 显示“实时 · 有事件跳过”，其余事件继续累计；每种 code 每局只通知一次。真正的 queue overflow 仍 fail closed，并明确记录致命原因，禁止靠扩大队列掩盖。
- 0.4.10 后续完整四人局在进入 CrystalMountain 第 1 区时先记录 `damage_snapshot_overflow`，紧接 `damage_snapshot_missing`；旧实现达到 8,192 时整表 `Clear()`，因此一次溢出会连锁丢失尚未消费的命中。0.4.11 改为字典索引配最旧未消费 FIFO，只逐个淘汰最老快照，并在消费、新局和卸载时同步移除。
- 0.4.12 收窄归属关系：优先官方 `mAtkerInHierarchy`，再用瞬时 `mAtker`；只接受 Player/native、OwnerEntity hierarchy 与 `Creature.Master`，不再用 StandMaster 或 EntityID 根做推测。`change_room_end` 每房记录 owner 汇总，避免多人路径只在 session start 留一份诊断。roster、pipe、schema、聚合与 UI 上限统一为 16；合成 16 人高负载、非 1P 本机和五列 HUD 已通过，真实 7–16 人与远端召唤物仍未运行。
- 0.4.12完整三人局确认逐击重建不能作为最终权威：HUD全队26,815,645对官方31,674,690，普通怪部分少4,918,416；团队Boss总量仅差59,371但玩家间错分。唯一黄色code为`damage_stack_mismatch`且无queue/snapshot致命错误，该code实际不跳过EmitDamage。
- 0.4.13从`StageNetworkCtrl._multiRoundDataDic`的逐玩家`mDamageValue/mBossDamageValue`同步官方累计，并以`SettlementDataMgr.mCacheRoundDataDict`的`mAtkDmg/mAtkDmg_Boss`作fallback；使用Player ID/ClientID/TransportID与Index映射匿名slot。主卡、队伍合计、占比和Boss采用不回退的官方累计，逐击仍提供DPS/来源与诊断。回营预加载前强制发送最后一次官方快照。
- 后续 r2 真实四人复测中，全部官方record被错误映到本机slot3；54次日志均为slot0–2 null、slot3单值，最终本机40,851,600而官方本机11,929,682。根因是把record.mID误当Player网络身份。0.4.14改为mIndex主映射、dictionary pair.Key仅作ID兜底；部分官方覆盖时团队分母改为各P位显示值之和，并用`自己 · Pn/Pn/Pn（离队）`对应游戏P位。日志新增匿名index映射摘要。
- 0.4.14真实四人局再次`R-FAIL`：54次均`network_records=0/fallback_records=1`，singleton cache被错误当作slot0 official，远端P仍无官方值；P4旧观察值跨局重复。游戏native证明确切最终门为`StageNetworkCtrl.SyncAdventureRecordDataEnd`返回后，`mCurAdventureRecordSaveData`中的`mIndex`直接等于0基`Player.Index`。
- 0.4.15短房诊断候选删除network/settlement轮询值的发布，只在exact SyncEnd后、最终record slot集合与本局历史roster完全一致时发布逐P官方Damage/BossDamage，否则整组拒绝。inactive不再进入可见团队分母，duplicate slot被拒绝，同run pipe重连保留session并显式标degraded。按roster Player注册的attacker callback当前只输出覆盖/冲突诊断，不改变主计数；必须先通过两个远端slot和投射/召唤转发的自动短房正控。
- 0.4.15短房registered-owner子门208/208命中重合，四个slot均覆盖且forwarded为2/1/77/10、冲突为0；但退局时旧地图在camp preload前被误判为新局，生成单人phantom session并令桌面异常。0.4.16加入closing-active-map门，且瞬时duplicate slot不再发布到桌面。退出后只剩单卡的7,453口径可能是团队/当前缓存折叠，不能当原多人slot个人official。
- 0.4.16变身样本中，P3第一战斗房39个callback只累计27；全局持续2点耗蓝385次/782，证明变身伤害不是无事件而是数值阶段为0/近0。参考DLL优先正`mRealHPDamage`、否则回退`mFinalDamage`。0.4.17保留普通real>0命中的现有HP封顶公式，仅对`real=0/final>0`做通用fallback，并按slot记录次数/总值；不含任何武器/技能特判。
- 0.4.17特别卡的真实四人长局中，registered/Settlement owner链39,997/39,997完整匹配且冲突为0，但本机逐击HUD仍明显高于官方卡；zero-real fallback未命中本机slot。exact SyncEnd虽拿到4条官方record，四条`mIndex`却全为0，安全门因此拒绝发布。这证明卡顿下客户端逐击只能作实时估算，最终必须由服务端/主机认可的官方record覆盖，也证明`mIndex`不能作为该客户端final save路径的唯一槽位事实。
- 0.4.18仅改变final record映射：按游戏原生`AdventureRecordPlayerData.mPlatformUniqueID`与roster `Player.PlatformUniqueID`做会话内HMAC后唯一匹配；不落盘、不输出原始值或指纹，不使用已证伪的`mID`网络匹配，也不按昵称、列表ordinal或固定4人猜槽。身份缺失/碰撞、额外record、重复slot或record/roster数量不一致都会整组拒绝。当前为离线候选，真实短房`NOT RUN`。
- 0.4.18真实四人最终结算首次`final_accepted=true`，四槽Damage/Boss逐项与四张官方卡完全一致，包括中途断线的P3；但紧接的三人roster刷新改写KnownParty身份并再次映射，变为2匹配/2未匹配/1碰撞，撤销已接受结果。结算HUD因此仍显示逐击估算。0.4.19在首次完整接受时冻结slot→原会话匿名token与官方Damage/Boss；之后不再读取终局场景新Player对象或重算身份，直到下一局统一reset。
- 同一 r7 真实四人长局唯一可恢复告警为墓园第4区一次`damage_snapshot_missing`，发生在P3断线之后；无owner冲突、queue overflow、stack mismatch或致命session失败。该告警确实跳过一条实时事件并让HUD保持“异常/有事件跳过”，暂不在0.4.19中猜测或静默清除；最终官方Damage/Boss冻结与它分开处理。
- 后续 r10 两局真实短测证明0.4.16 closing门在中途退局、缺少`OnGameRoundEnd`时永久保留：第二局入口和战斗房均valid=false，原session从9,906继续到16,519。0.4.20记录旧活动房完整指纹；新房变化立即解锁，同房重入则由第一条真实伤害/法力消耗解锁；同指纹且无战斗证据的旧房迟到回调仍被拒绝。
- 0.4.21为过程准确性诊断候选：只在既有房间边界读取`StatisticsMgr._adventureRecordCacheDataList`与`mAdventureRecordDataList`，用当前party的`PlatformUniqueID`本机HMAC匹配匿名slot，并记录可用性、匹配/冲突/失败及逐slot候选总量。候选值不写入pipe、不覆盖HUD；先用一到两个多人房间证明缓存的重置、累计与身份语义，再决定是否作为过程主口径。
- 在 r12 三人两房真实探针基础上，0.4.22仅采用`mAdventureRecordDataList`作为live过程主口径：新session必须先得到完整三槽零基线，之后要求record数与历史party槽全集一致、平台身份一一匹配、Boss不大于总伤害且逐槽单调；任一门失败即整组不发布并回退逐击。pipe新增可替换的`live_damage/live_boss_damage`，与exact SyncEnd后的sticky `official_*`分离，因此final可向下纠正；归档保留`last_live_*`供结算checker比较。
- 后续 r13 真实烟测发现`PartyMemberSnapshot.ToPayload`已有live字段，但`PublishPartyUpdated`制作有界副本时只复制final字段，导致pipe只发布初始roster、partial中live始终null；VPN卡顿不是原因。0.4.23只补复制`LiveDamage/LiveBossDamage`，不改缓存、身份、单调门、逐击或final逻辑。
- r14 两人+NPC真实样本证明payload复制已进入下一门，但active/cache各有3 records、party只有2名玩家；两个human identity完整匹配，NPC各1条unmatched。旧`records.Count == party.Count`安全门按预期拒绝整组。0.4.24允许额外未匹配record，但仍要求每个历史玩家slot恰有一个身份匹配且禁止重复slot；NPC的2,409伤害保持unattributed，不并入任一玩家live总量。
- r15 四人真实长局证明`mAdventureRecordDataList`只在房间边界吸收当前房增量，同房内直接显示会冻结；延迟锚点加逐击增量仍比最终官方总伤害高6.36%、Boss高25.71%，不能签过程准确。0.4.25只新增匿名只读诊断：在既有官方攻击postfix和房间/结算边界原子读取`mCacheRoundDataDict`、Statistics房间cache list与active累计，按非零Player ID/ClientID/TransportID唯一映射并记录raw float、NPC unmatched、碰撞/重复/读取失败。singleton仅单列观察；探针不写pipe、不覆盖`live_*`或HUD。先用一到两个短房证明同房双玩家增长及换房守恒，再决定是否采用。
- 0.4.25在真实运行前被阶段复审撤回：去重发生在完整重读取之后，普通样本cap会同时吞掉force边界，checker还提前假定dict必须等于cache-list及`active+dict`必须转场守恒。installed已回滚0.4.24。0.4.26把200ms单调时钟限频放在任何PlayerList/dict/network/cache读取之前，首个攻击与所有force边界旁路；普通额度不再影响边界，并记录suppressed/throttled计数。dict/cache与rollover只做关系分类，真实样本冻结前不因差异判FAIL；unmatched/collision使用每进程加盐HMAC opaque token辅助本地复核，不输出raw key、身份或pointer。
- r19 四真人短局得到479个完整样本：`mCacheRoundDataDict`始终0 records；Statistics active在同房恒定，cache-list进房归零并按玩家实时单调增长。队友-only房本机slot3始终0，本机攻击房分别增加1,139/2,199；最后`active+cache=[45,888,35,652,41,555,3,338]`，精确等于OWNER远端123,095加本机3,338。Boss全0、NPC未覆盖；严格checker因此只签普通伤害raw realtime，rollover因旧版本没有真正room_exit force样本保持NOT_RUN。
- 同局先离队再退出时，官方卡仍为本机3,338，但HUD跳45,888。冻结事件证明45,888精确来自旧P1，不是三队友求和：同session内LocalPlayer native token和Index从P4变P1，Bridge先按旧slot0取live，再创建`player-5`并覆盖身份，导致collision。0.4.27采用`active + cache-list`发布过程值；同session按平台HMAC或仍有效的旧token复用`player_id`，live按历史身份取值而可见`player_slot`采用当前Index，所以期望离队事件为`player-4/slot0/live=3338`。身份缺失/碰撞整组拒绝；现有OnChangeRoomEnd target同时增加Prefix房末强制样本，不新增Hook。
- Bridge 1.7.0 是 v1.7.1 已发布并冻结的隐私重编译版本。工具箱1.7.2 r2/r3依次提升到1.7.1/1.7.2并引入互斥诊断档与Statistics本地终局候选。r4真实单人结算证明`StatisticsMgr.OnGameSettlementSyncEnd`仍不执行，同时确认进程重启续玩时首个完整live向量非零会被旧基线门永久拒绝。r5 Bridge 1.7.3只允许“本游戏进程的首个session”接收完整非零live种子，后续同进程新局仍要求零基线；桌面把首样本仅作DPS基线。单人终局改由`GameSettlementUI.SetSettlementData`/`UpdateSettlementInfo`及offline-end兜底触发。真实主动结束样本证明UI入口会执行，但当时最终save-list尚未物化，r5没有读取UI正在显示的record，因而没有official或`session_ended`。
- Bridge 1.7.4只在最终record读取`AdventureRecordPlayerData.mTakeDamageValue`并发布`official_taken_damage`；历史证据没有证明active+cache承伤可安全逐房相加，所以局中承伤继续使用已验证的玩家根逐击口径。`UpdateSettlementInfo`显式record以及同一调用链的`GameSettlementUI._selfPlayerData`必须通过单人本机身份、slot、非负值和Boss≤Damage门，才被冻结为Damage/Boss/Taken三项最终值；较早的`GameOverEnd_Offline`只记录入口，不读取可能为空或陈旧的record。可信单人结算UI即使record仍不可用，也保留最后live值并发送`session_ended`，不得遗留phantom session或冒充官方。`CombatDiagnostics=true`打开既有逐击、cache与终局采样日志，`false`只保留低频支持信号；两档数值路径相同，均不修改游戏对象，档位标记不一致时拒绝启动。
- 多人只向桌面发送会话内匿名`player-N`、槽位、本机标记和通过完整门的官方数值，不发送昵称、Steam ID、平台账号或原始身份。本机严格比较`LocalPlayer`对象，不假设1P/房主或slot0。真实0.4.17变身fallback与最终SyncEnd仍未运行。

构建需要 .NET 6 SDK、BepInEx 6 和当前游戏生成的 interop 程序集：

```powershell
dotnet build .\LC2CombatBridge.csproj -c Release -p:GameDir="<游戏目录>"
```

Release 配置固定 `DebugType=None`、`DebugSymbols=false` 与确定性构建，正式 DLL 不携带 PDB/CodeView 本机路径；如需源码级调试，请使用非 Release 配置并只保留在本地。

本地测试前，将生成的 `LC2CombatBridge.dll` 放入 `<游戏目录>\BepInEx\plugins\LC2CombatBridge\`。部署、游戏实测和发布是独立阶段；仅构建源码不会修改游戏目录。
