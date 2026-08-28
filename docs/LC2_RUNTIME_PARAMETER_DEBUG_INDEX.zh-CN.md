# LC2 运行时参数、代码映射与调试索引

本文把当前已经解析、实现或实测过的战斗参数统一到同一条链路：

`游戏字段/事件 -> 桥接读取与转换 -> v2 协议 -> Python 聚合 -> HUD/详情页`

目标是让维护者先按症状、字段名或数值口径检索，再决定需要读哪段源码或补哪种实机样本。本文不是整款游戏全部数据的宣称；未进入现有 interop、桥接、协议、探针或实测记录的装备、怪物、技能和道具参数不在本次范围内。

## 1. 记录身份与状态标签

| 项目 | 当前记录 |
| --- | --- |
| 记录日期 | 2026-08-28（Asia/Shanghai） |
| Steam app / build | `2445690` / `24795992`；已从本机 manifest 复核 |
| Unity / IL2CPP metadata | `6000.3.16f1` / `39` |
| `GameAssembly.dll` | `747E8BECB7B97B014D7F282C1EB60A7A4754A8A1DF01CEB943C03967F6E6F1C5` |
| `global-metadata.dat` | `D42663B5ED61E9D5D30FCEF878969507C4B04951595DD61D63B5E0BD7017984A` |
| `LC2.Core.dll` interop | `0267065BFB4CF8E4B7BD369C2240212901294C85B931DD6259FFAF02E5AFEFAF` |
| BepInEx | `6.0.0-be.785`，commit `6abdba47eeebe08552282e7a58ef0f4a9ab60b62` |
| 当前项目源码 | Bridge `0.4.1`；房间位置在 `OnChangeRoomEnd` 读取且跨图实测通过；法力按原始 float 累计、官方恢复分支 `114/114` 无双计；非战斗房 dealt 不聚合；仍为 14 个 Hook |
| 当前游戏目录 | Bridge `0.4.1`，SHA-256 `D499BA6BA2B21851F7C325F37503CEE418A66E4AA91A8D2A7C200FCC076B3744`；0.4.0 exact rollback 已保留。显示模式保持“窗口化全屏”（两份 `GameSettings.mFullScreenMode=2`） |
| 桌面端 | `1.5.6` 已打包并复制到桌面；EXE SHA-256 `85F37430FB6863FB3076A05FDFE4F01B7730B7440BCE8006D29FA395C06CFD59`；默认宽敞 `1280×900、115%` 且 HUD 默认开启，聚合保留结算到下一次新 session |

证据标签：

| 标签 | 含义 |
| --- | --- |
| `R-PASS` | 在上述游戏构建上有真实运行样本，且正控/负控闭合 |
| `R-FAIL` | 真实运行已复现漏记、重复、崩溃或口径错误 |
| `S` | 当前 interop 或源码静态确认，尚未完成对应实机语义正控 |
| `T` | 协议、重放聚合或 UI 模型测试确认；不能替代游戏运行验证 |
| `H` | 有证据支持的假设，仍需能证伪的样本 |
| `U` | 未覆盖或证据不足 |

动态身份必须在游戏更新、interop 重生成、Bridge DLL 替换后重新核对。历史 PASS 只适用于其记录的构建、样本和代码路径。

## 2. 症状速查表

| 症状 | 第一检查点 | 常见根因/反例 | 当前状态与下一步 |
| --- | --- | --- | --- |
| 启动长白屏 | `GameSettings.mFullScreenMode`、窗口首次呈现、显示模式应用时机 | 作者往返复现：最大化窗口出现长白屏，“窗口化全屏”肉眼不再出现；当前实存值 `2`。被动截图只在进程约 `7.14–7.48 s` 捕获到极短白色初始化表面 | `R/T/P0`。显示模式是决定性变量；当前保持“窗口化全屏”，不得再把三臂旧样本概括为所有模式都会长白屏 |
| 启动耗时 | BepInEx/Il2CppInterop 启动阶段；再比较 `Plugin.Load()`、`Harmony.PatchAll` 增量 | 本机暖启动 B 组主菜单中位上界比 A 组约慢 `6.25 s`，C 组未慢于 B 组；作者确认总启动时长可接受 | `R/T/P2`。仅保留性能基线，不作为当前修复目标；详见[三臂实测结果](LC2_STARTUP_PERFORMANCE_2026-08-27.zh-CN.md) |
| Bridge 加载即报 Harmony 参数错误 | Patch 方法参数名和目标签名 | Probe 0.2.0 首个候选把 `hitInfo` 写成 `hit`，主菜单加载失败 | `R-FAIL` 历史正控；任何新 patch 先做精确签名静态门 |
| 法力消耗显示约一半 | `OnUseMana.useMana`、前后 `CurMP`、武器输入语义 | 长杖面板 `24` 是长按持续消耗参考；短按只触发最低段，实扣 `120→108`。另一武器面板 `48`，实扣 `120→72` | `R-PASS` 当前两武器样本；按真实结算累计，不把持续技能面板值强制当作单次成本 |
| 法力恢复始终为 0、异常偏高或与消耗差少量整数 | `OnRecoverMana`、最近真实 MP、有效 session、整局起止 MP | 回调值 `120/125` 是恢复后目标值；续局可能缺 room-start；官方 callback 也可能缺席 | `R-PASS`：0.3.6 `256/256`，0.4.1 官方分支 `114/114` 且 `runtime_gain=0`；低层缺 callback 兜底只待自然正控 |
| 结算后立刻清零 | `StageMgr.OnGameRoundStart` 与 `SettlementDataMgr.OnChangeRoomStart` 的顺序 | 回营也可能触发 round-start，不能把它直接当作新地图 | `R-PASS` 回营保留/再次进入黑森林清零；完整打完结算的 `session_ended` 正控仍未执行 |
| 结算 30 秒后清零 | `DEFAULT_ENDED_RETENTION_MS` | 旧默认 `30000` 会抹掉结果；结算动画本身可能提前消耗时间 | `T`。当前默认 `None`，保留到下一个 session |
| 总伤害偏高 | `mRealHPDamage`、命中前 HP、过量伤害 | 直接汇总 `mRealHPDamage` 会包含过量部分；A 组高 `19.56%` | `R-PASS`。使用逐击 `ceil(min(real, hp_before))` |
| 总伤害偏低 | 玩家归属、召唤物、投射物、DOT、嵌套独立附伤 | 漏掉召唤物、技能派生实体、DOT；把所有 `depth>0` 都排除也会漏冰附伤 | `R-PASS` 多类来源；联机权威路径仍 `U` |
| 总伤害重复 | 多个官方/记录 path 或覆盖方法嵌套 | `official_defender` 与 `monster_record` 可观察同一事件；Hero/Base HP 回调一外一内 | `R-PASS`。伤害资格以唯一官方事件为门；HP 只聚合 `depth=0` |
| 商店人偶使总伤害偏高 | `StageMgr.IsNonBattleRoom()`、事件 `aggregate` | 商店人偶会触发官方 attacker 回调，且内部 `IsBoss=true`，但游戏最终结算排除；0.3.8 的 `_Shop_` 文件名判断实机未命中 | `R-FAIL` 两局：差额 `12254`、`5600` 都与错误 Boss 值相同。0.3.9 改用游戏公开的非战斗房语义，待实机正负控 |
| Boss 伤害不等于结算 | `MonsterRuntimeData.IsBoss` + `StageMgr.IsNonBattleRoom()` | 普通 Boss 必须用 `IsBoss`；但非战斗房木桩也是 `IsBoss=true`，必须先按房间业务语义排除聚合 | 旧 Boss 长局 `R-PASS 24271`；商店两次 `R-FAIL`；0.3.9 待实机 |
| 承伤与恢复不相等 | HP damage 与所有正向 HP delta 是独立累计 | 清场、道具、被动和容量变化都可使恢复大于承伤，不存在守恒要求 | 本局官方/工具箱承伤均 `140`，恢复 `142`；`+2` 来源尚无逐事件 receipt，不判为计算错误 |
| 自伤/诅咒掉血没有进入统计 | 玩家 HP 前后值、`ChangeCurrentHp`/`SetCurHP`、是否位于 `DamageProcess` | 0.3.8 只覆盖正向恢复；敌人伤害和直接负向 HP 不能混入同一指标 | `R-FAIL/S`：折断的妖刀样本复现。0.3.9 仅在官方 DamageProcess 外发负向资源事件，单列“自伤/其他”，待妖刀正控与敌人受击负控 |
| 官方承伤与实际掉血不同 | `mOriFinalDamage` 对比 `mRealHPDamage`/HP 差 | 游戏承伤卡使用减伤前值；实际掉血是减伤后值 | `R-PASS`。UI 必须分列“官方承伤 / 实际战斗掉血” |
| 治疗一直为 0 | 玩家根过滤、`HeroRuntimeData.ChangeCurrentHp` | 只 patch 基类会漏派生覆盖；`Creature.TryCast<Player>()` 是不成立的类型关系 | `R-PASS` 修正：比较玩家根实体 ID；仍需死亡/复活正控 |
| 一次治疗被记两次 | `operation_id`、`parent_operation_id`、`depth` | `HeroRuntimeData.ChangeCurrentHp` 会嵌套进入基类方法 | `R-PASS`。外层 `depth=0` 聚合，内层仅诊断 |
| 满血使用道具仍增加治疗 | `requested_delta` 对比 `effective_delta`、`overflow` | 请求量不等于有效量；满血时有效治疗为 0 | `R-PASS` 香蕉正控 |
| 魂石恢复数字与截图不符 | 来源分流和 35% 阈值 | 同时存在魂石、红血恢复、清场恢复；中途截图不能代表单一来源总量 | `R-PASS`，必须按 token 分列 |
| 击杀数少于结算 | 官方击杀事件 | `mDead`/致死伤害事件不能覆盖所有结算击杀 | `R-FAIL`：长局 `88` 对官方 `89`；禁止从伤害事件反推完整击杀 |
| 地图名、阶段或区域错或晚一房间 | `CurStageLevel`、`CurScenario`、`CurRoomIndex`、`mapFileName`、房间回调时序 | `room_id` 不是显示名称；未知 enum 不能套用邻近地图名；在 `OnChangeRoomStart` 读取会取得切换前状态 | `R-PASS`：0.4.0 改在 `OnChangeRoomEnd` 读取，废村入口与 `DarkForest 8 -> SaltpetreDesert 0 -> 1 -> 2` 已实机通过 |
| 来源显示“未知” | `assets/combat_sources.json` | 游戏更新的新 token，或 Bridge 自己发出的 token 未登记 | 当前已知缺口：`enemy.damage`；`set_cur_hp` 已登记为“直接生命变化” |
| 护盾、自伤、诅咒长期为 0 | Bridge 是否真正发出 `effect_stack/resource_change` | 协议和聚合字段存在不代表游戏入口已接通 | `U`。当前属于协议/测试预留，不能标成已完成功能 |
| 重连后统计被清空或错 session | `session_id`、`sequence`、显式 `session_started` | 断线重连被误当新局；异 session 事件无显式边界 | `T/S`。结束态重连保持 `session_ended`；仍需实机断线正控 |

## 3. 用户指标端到端主表

| 用户指标 | 游戏源字段/事件 | Bridge 计算与单位 | v2 字段 | 聚合字段 | UI | 证据/风险 |
| --- | --- | --- | --- | --- | --- | --- |
| 本局总伤害 | `OnAfterHit_All_Damage_Atker` + `mRealHPDamage` + 命中前 `CurHP` | `applied=min(max(0, real), hp_before)`；逐击 `ceil(applied)` | `damage_direction=dealt`, `settlement_damage` | `total_damage += settlement_damage` | HUD“伤害”、主窗口“总伤害” | `R-PASS` 多样本 |
| 最近 10 秒 DPS | 同上 | 只使用可聚合的 `settlement_damage` 和事件 `monotonic_ms` | 同上 | 窗口内伤害和 / `10s` | HUD“近 10 秒平均秒伤”，保留一位小数 | `T/R`；作者选择保留 DPS，不改成十秒总伤害 |
| Boss 伤害 | defender `MonsterRuntimeData.IsBoss` | `IsBoss=true` 的造成伤害逐击值 | `is_boss=true` | `boss_damage` | HUD/主窗口 Boss | `R-PASS 24271` |
| Boss 占比 | 无新增游戏字段 | `clamp(boss_damage / total_damage, 0, 1)` | 无 | UI 派生 | HUD 比例条 | `T` |
| 官方承伤 | 玩家根 defender 的 `OnAfterHit_All_Damage_BeAtker` + `mOriFinalDamage` | 先排除召唤物/非玩家 defender，再逐击 `ceil(max(0, original))` | `damage_direction=taken`, `target_kind=player`, `settlement_damage` | `taken_settlement_damage` | “承伤/官方承伤” | `R-PASS` 0.3.7：召唤物先、玩家后，仅保留玩家 `35`；召唤物造成伤害仍正常 |
| 实际战斗掉血 | `mRealHPDamage` + 命中前 HP | `min(real, hp_before)` | `applied_hp_damage` | `hp_damage_taken` | 主窗口详情 | `R-PASS`，不得与官方承伤合并 |
| 减伤量 | 原始伤害与结算后伤害 | `max(0, original-real)` | `mitigated_damage` | `mitigated_damage` | 主窗口详情 | `R-PASS` 总量语义；具体乘加顺序 `U` |
| 过量伤害 | 结算后伤害与实际可扣 HP | `max(0, real-applied)` | `overkill_damage` | `overkill_damage` | 当前未单独突出 | `R-PASS` |
| 有效治疗 | 玩家 HP 前后值 | 仅 `depth=0` 且 `requested>0`；`effective=after-before>0` | `resource=hp`, `effective_delta` | `effective_healing` | HUD“回复”、详情“有效回复” | `R-PASS` 香蕉/灵药/魂石 |
| 其他掉血/自伤 | 玩家根 HP/RedHp 前后值；来源可能是物品自伤、诅咒或直接 HP 修改 | 0.3.9 仅观察 `effective<0 && !InsideDamageResolution`，尚未覆盖伤势生命并与官方 hit 做完整关联 | 内部候选 `resource=hp`, `resource_operation=loss` | `hp_loss_other`（内部） | 当前不进入 HUD、主卡、来源表或汇总 | 两种诅咒截图均不足以形成 receipt；冻结为 `INCONCLUSIVE/U`，不得作为完成指标打包 |
| 治疗溢出 | 请求恢复量、实际恢复、MaxHP | 到达容量时 `max(0, requested-effective)` | `overflow` | `resource_overflow` | 主窗口“治疗溢出” | `R-PASS` 香蕉/灵药；该总量也会累加其他资源溢出 |
| 被阻止的资源变化 | 请求非零、有效为零、非满容量 | `blocked=true` | `blocked` | `resource_blocked_attempts` | 当前未突出 | `T/S`；诅咒正控仍 `U` |
| 法力消耗 | `OnUseMana.useMana` | `ToCurMPInt(useMana)`，符号转负；底层 MP 前后值仅 `aggregate=false` 旁证 | `resource=mp`, `effective_delta=-spent` | `mp_spent` | HUD/详情“法力消耗” | `R-PASS`：长杖短按 `12`，普通技能 `48`；同次双路径没有重复计数 |
| 法力恢复 | `OnRecoverMana.recoverMana` + 最近运行时 MP | 回调后读取当前 MP，`effective=max(0,current-last_observed)`；回调原值仅证明目标 | `resource=mp`, `effective_delta` + before/after/max | `mp_gained` | HUD/详情“恢复” | `R-PASS` 0.3.6：四次 `54/98/100/4`，before/after 与作者观察闭合 |
| 法力净值 | 无新游戏字段 | `mp_gained - mp_spent` | 无 | `mp_net` | 当前主要供快照/诊断 | `T` |
| 护盾吸收 | 预期 damage outcome | `damage_outcome=absorbed` | `damage_outcome` | `shield_absorbs` | 当前未突出 | 协议/聚合 `T`，Bridge 实机入口 `U` |
| 护盾层消耗 | 预期 shield `effect_stack` | `effect_kind=shield_charge`, `stack_delta<0`, hit_received | `effect_stack` | `shield_layers_consumed` | 当前未突出 | `T` fixture，仅 P4-019 注册表存在 |
| 房间 checkpoint | `RoomBattleDataDto` 三类 float | 不覆盖事件累计，只并列保存 | `checkpoint_totals` | `checkpoint_totals` | 当前无完整差异 UI | `S/T`；仅房间快照，不等同整局总量 |
| 地图/阶段/区域 | `StageMgr` 四字段 | `OnChangeRoomEnd` 后独立保留；`room_id=L{stage}:{scenario}:{index}` | location 字段 | snapshot location | HUD“地图 · 区域”，详情附阶段 | 0.3.9 start 时序 `R-FAIL`；0.4.0 end 时序跨地图 `R-PASS`；游戏更新后重验 |
| 连接/会话状态 | Bridge 生命周期、pipe heartbeat | 显式 session/room 边界 | `status` | `connection_state` | 正常/连接/断开/过期/错误 | `R-PASS` 启动、连接和连续两次黑森林新 session；断线重连仍待独立正控 |

## 4. 关键 interop 符号快照

以下签名来自当前 `LC2.Core.dll` interop。字段存在只证明可见性，不自动证明调用时机或业务语义。

### 4.1 伤害与目标

| 类型/成员 | 原始类型 | 当前解释/用途 | 已知边界 |
| --- | --- | --- | --- |
| `DisposeHitInfo.ID` | `Int32` | 同一次 hit 的快照关联键 | 不是跨局稳定 ID；Bridge 缓存上限 8192 |
| `DisposeHitInfo.mAtker` | `Entity` | 攻击实体/来源归属入口 | 子实体、召唤物、NPC 需追 owner/master |
| `DisposeHitInfo.mBeAtker` | `Entity` | 受击者/目标身份 | Boss 门读取目标 runtime |
| `DisposeHitInfo.mDamageInfo` | `DamageInfo` | 原始伤害与暴击 | 可能为空，Bridge 回退到 real damage |
| `DamageInfo.mOriFinalDamage` | `Single` | 减伤前最终伤害；官方承伤主口径 | 不能代表实际掉血 |
| `DamageInfo.mBeCrit` | `Boolean` | 暴击诊断字段 | 当前 UI 不单独统计 |
| `DisposeDamageInfo.mRealHPDamage` | `Single` | 伤害解析后的 HP 伤害候选 | 可包含超过剩余 HP 的过量部分 |
| `DisposeDamageInfo.mDead` | `Boolean` | 本击致死标志 | 不能反推完整官方击杀 |
| `MonsterRuntimeData.IsBoss` | `Boolean` | Boss 目标唯一门 | 不可用 `IsElite` 替代 |
| `MonsterRuntimeData.IsElite` | `Boolean` | 精英诊断 | 精英伤害不等于 Boss 伤害 |
| `AttrType` | enum | 当前读取 `Fire/Ice/Poison/Electric/Evil/Blood` | Bridge 只做“是否含元素”粗分；主元素/多元素详情未进 UI |

### 4.2 HP

| 类型/成员 | 原始类型/签名 | 当前解释/用途 | 证据/边界 |
| --- | --- | --- | --- |
| `CreatureRuntimeData.CurHP` | `ObscuredFloat` | 前后 HP 快照 | `R-PASS` |
| `CreatureRuntimeData.CurHP_Int` | `ObscuredInt` | 游戏整数显示值候选 | 当前 Bridge 未使用 |
| `CreatureRuntimeData.MaxHP` | `ObscuredFloat` | 容量与溢出判断 | `R-PASS` |
| `CreatureRuntimeData.MaxHP_Int` | `ObscuredInt` | 游戏整数最大 HP | 当前 Bridge 未使用 |
| `ChangeCurrentHp(float, DoInjuryType, bool, bool, string)` | virtual-like method | 通用 HP 变化入口 | 只 patch 基类会漏 Hero 覆盖 |
| `HeroRuntimeData.ChangeCurrentHp(...)` | override | 玩家真实常用写入入口 | 香蕉/灵药/魂石 `R-PASS` |
| `SetCurHP(float value)` | method | 直接设置 HP 候选 | 0.12 样本未走此路径；保留诊断 |
| `FullFoodEnergyOrRecoverHp(Creature,float)` | returns `Boolean` | 饱食/进食高层入口 | 有效与满血 `false` 正控 |
| `OwnerPlayerIncludeMaster.OwnerCreature.EntityID` | entity relation | 玩家根实体判定 | 正确替代不成立的 `Creature -> Player` 强转 |

### 4.3 MP

| 类型/成员 | 原始类型/签名 | 当前解释/用途 | 证据/边界 |
| --- | --- | --- | --- |
| `CreatureRuntimeData.CurMP` | `ObscuredFloat` | 内部 MP 浮点 | 0.3.0 直接累计可能产生半值 |
| `CreatureRuntimeData.CurMP_Int` | `ObscuredInt` | 游戏显示 MP | `R-PASS`：`120→108`、`120→72` 与 HUD 对齐 |
| `CreatureRuntimeData.MaxMP` / `MaxMP_Int` | float/int pair | 内部/显示容量 | `S` |
| `ToCurMPInt(float curMp)` | returns `Int32` | 游戏提供的内部->显示转换 | 0.3.2 实机值与 MP 条前后差闭合；面板 `24` 的差异来自长按技能语义，不是统一换算倍率 |
| `RegenerationMp` | `ObscuredFloat` | 自动回蓝参数候选 | private getter；当前 Bridge 不直接读取 |
| `MpCostRate` | `Single` | 法力成本倍率候选 | 炼金 5% 减耗可能在此或上游体现，未闭合 |
| `ChangeCurrentMp(float,bool,string)` | method | 底层 MP 变化 | 仅发 `aggregate=false` 诊断镜像；已证实可为官方事件提供 `before/after` 旁证且不会双算 |
| `UpdateMp(float deltaTime)` | method | 自动更新入口候选 | 0.3.0 观察未得到恢复正控 |
| `GetSkillCostMP(float basicCostMP)` | returns `Int32` | 技能最终显示成本候选 | 适合对照基础 25、减耗后 24；未接入 Bridge |
| `GetActivePropsCostMP(float basicCostMP)` | returns `Int32` | 主动道具 MP 成本候选 | 未接入 Bridge |
| `OnUseMana.creatureID/useMana` | `Int32` / `Single` | 官方耗蓝事件身份与数值 | `R-PASS` 单机当前武器样本；48 与底层前后差闭合 |
| `OnRecoverMana.creatureID/recoverMana` | `Int32` / `Single` | 官方回蓝事件身份与数值 | `R-PASS` 回调触发；既包含真实 `+6` tick，也包含进图初始化 `+120`，必须带生命周期门 |
| `Player.RegisterCreatureEventCallback<T>` | typed callback + priority | 注册 `OnRecoverMana` 回调 | 0.3.2 运行确认持续触发，无 transport fault |

### 4.4 地图、结算与会话

| 类型/成员 | 类型/范围 | 当前用途 | 边界 |
| --- | --- | --- | --- |
| `StageMgr.IsInCamp` | `Boolean` | 排除营地 room-start | 事件时序必须与 room identity 合并判断 |
| `CurStageLevel` | `StageLevel` -> `0..6` | 主进度阶段 | UI 仅 `>0` 时显示阶段 |
| `CurScenario` | `Scenario` enum | 地图路线 token | 未知 token 保留原值 |
| `CurRoomIndex` | `Int32` | 区域编号 | 当前合同允许 `0..10,99,100,101` |
| `CurRoomInfo.mapFileName` | string | 精确房间 asset 诊断 | 不作为用户地图名 |
| `StageMgr.OnGameRoundStart()` | lifecycle | 只标记“等待新地图” | 回营也可能触发，不能直接清零 |
| `SettlementDataMgr.OnChangeRoomStart(data)` | lifecycle | 首个非营地 room-start 才开新 session；其后换房只更新位置 | `R-PASS` 两次 `DarkForest / room 0 / Map_DF_Entrance_c001` 新会话边界 |
| `SettlementDataMgr.OnGameRoundEnd()` | lifecycle | 发送 `session_ended` | 结算保留，不立即清指标 |
| `RoomBattleData.normalAttackDamage` | `Single` | 房间普通伤害 checkpoint | 房间值，不是整局总量 |
| `RoomBattleData.skillAttackDamage` | `Single` | 房间技能伤害 checkpoint | 同上 |
| `RoomBattleData.throwAttackDamage` | `Single` | 房间投掷伤害 checkpoint | 同上 |

## 5. 公式、取整与去重规则

| 名称 | 当前公式/规则 | 为什么这样做 | 证据 |
| --- | --- | --- | --- |
| 玩家造成伤害 | `sum(ceil(max(0, min(mRealHPDamage, hp_before))))` | 去除过量伤害，逐击向上取整 | 多组 `R-PASS` |
| 官方承伤 | `sum(ceil(max(0, mOriFinalDamage)))` | 结算卡使用减伤前值 | `R-PASS` |
| 实际掉血 | `min(max(0, mRealHPDamage), hp_before)` | 不超过目标剩余 HP | `R-PASS` |
| 减伤 | `max(0, original-real)` | 保留原始与实际差 | `R-PASS` 总量 |
| 过量 | `max(0, real-applied)` | 分离致死一击多余部分 | `R-PASS` |
| 有效治疗 | `max(0, hp_after-hp_before)` | 不把请求量或溢出算作治疗 | `R-PASS` |
| 治疗溢出 | 满容量时 `max(0, requested-effective)` | 区分部分溢出和满血零恢复 | `R-PASS` |
| HP 嵌套去重 | 同一 operation 只聚合 `depth=0` | Hero 覆盖会嵌套调用基类 | `R-PASS` |
| 伤害嵌套 | 不能统一排除 `depth>0` | 部分元素附伤拥有独立官方事件 | `R-PASS` |
| 跨 path 去重 | 只允许 Bridge 裁决的 `aggregate=true` 进入总量 | 同一受击可被多个 path 观察 | `R-PASS/T` |
| MP 显示单位 | `ToCurMPInt(event_value)`；最终以实际前后 MP 差交叉验证 | 对齐真实扣除，不把长按技能面板参考值当固定单次成本 | `R-PASS`：短按 `12`、另一武器 `48` |
| MP 官方/底层去重 | 官方 `OnUseMana aggregate=true`；`ChangeCurrentMp aggregate=false` | 同次施法两条路径只计官方值，底层保留前后值诊断 | `R-PASS`：所有配对事件均未双计 |
| MP 恢复差值 | `max(0, current-last_observed)`；每次运行时变化后刷新 cache | 同时排除已满初始化并精确计算系统回满 | `R-PASS` 0.3.6：`66→120`,`22→120`,`20→120`,`116→120` |
| 最近 DPS | 10 秒内 `settlement_damage` 和 / 10 | 与总伤害同口径 | `T` |
| Boss 占比 | `clamp(boss/total,0,1)` | 防空值和不一致数据 | `T` |
| checkpoint | 保存但不覆盖事件累计 | 差异应显式诊断 | `S/T` |

## 6. v2 协议与运行边界

| 项目 | 值/规则 | 失败表现 |
| --- | --- | --- |
| schema | `2`；拒绝额外字段 | `schema_invalid` |
| pipe | `\\.\pipe\LostCastle2Toolbox.Combat.v2` | `pipe_unavailable/pipe_closed` |
| Bridge/客户端队列 | 各 `512` | 清空并进入 `queue_overflow` 错误，不静默丢事件 |
| JSON 单行 | 最大 `64 KiB`，严格 UTF-8，对象，换行结尾 | `line_too_long/invalid_utf8/invalid_json/event_not_object/unterminated_line` |
| 读取块 | `8192` bytes | 可拆行/合行解码 |
| heartbeat | Bridge 每 `2000 ms` | 客户端 `6 s` 无数据标记 `stale` |
| 重连间隔 | `1 s` | 状态先 `connecting`，失败为 `disconnected` |
| session | 新局生成 GUID；异 session 仅接受显式 `session_started` | 否则 `SessionMismatchError` |
| sequence | session 内从 0 单调递增，不得复用/倒退 | `SequenceError` |
| monotonic | session 内不得倒退 | `SequenceError` |
| event id | `${session_id}:${sequence}`，幂等 | 完全重复忽略；同 sequence 不同 ID 报错 |
| `aggregate` | 由 Bridge 决定 | Aggregator 不从 `depth` 猜测 |
| location | stage `0..6`；room index `0..10/99/100/101` | 非法位置拒绝，不做邻近映射 |
| 字符串上限 | event 160；session/room/player/entity 128；hook/token/map 256；detail 512 | schema 拒绝；错误消息不回显敏感原值 |
| HP 快照缓存 | `8192` | 超限前淘汰最旧快照；丢快照使 session fail-closed |
| 结算保留 | 默认 `ended_retention_ms=None` | 只在下一显式 session 清指标 |

## 7. 来源 token 注册表与缺口

| token | 标签 | 分类 | 运行证据/备注 |
| --- | --- | --- | --- |
| `ExhaustProps#Banana_0` | 香蕉 | `consumable.heal` | `R-PASS` |
| `EatFood` | 进食恢复 | `consumable.food` | 灵药逐 tick 也会使用，不能硬编码成单一道具 |
| `full_food_energy_or_recover_hp` | 饱食或进食恢复入口 | `system.food` | 高层入口正控 |
| `Gem#A_015_2` | 自愈 | `passive.periodic_threshold` | 约 +1 tick、35% 阈值 `R-PASS` |
| `Battle#Battle_ClearStageStatus_1` | 清场恢复 | `system.stage` | `R-PASS` |
| `P4-019` | 护盾充能器 | `defensive.shield_charge` | 仅协议/fixture；Bridge 游戏入口未闭合 |
| `combat.player.normal` | 玩家普通伤害 | `damage.player.normal` | Bridge 当前粗分 |
| `combat.player.element` | 玩家元素伤害 | `damage.player.element` | 任一六元素命中即归此类 |
| `combat.summon` | 召唤物伤害 | `damage.summon` | OwnerPlayer/Master 归属已有正控 |
| `resource.self_damage` | 宝藏或技能自伤 | `resource.self_damage` | 官方伤害结算外的直接负向 HP 候选；伤势生命仍未闭合，不作为用户指标 |
| `resource.skill_cost` | 技能法力消耗 | `resource.skill_cost` | `R-PASS` 12/48 与底层 MP 差闭合 |
| `resource.mana_recovery` | 法力恢复 | `resource.mana_recovery` | `R-PASS` 0.3.6；四条均 aggregate、before/after/max 完整 |
| `enemy.damage` | 未登记 | 当前 Bridge 承伤事件 token | 维护缺口：会进入未知来源计数 |
| `set_cur_hp` | 直接生命变化 | `resource.direct_hp_change` | 已登记；该路径当前样本未命中，仍只作内部诊断 |
| 空 token | `未知来源` | `<none>` | 红血恢复正控中出现；需新样本确认是否应命名 |

未知 token 必须保留为 `未知来源 · token`，不得丢弃或猜成邻近道具。

## 8. 地图枚举与路线

| enum | 数值 | 阶段 | 中文 | 当前路线 |
| --- | ---: | ---: | --- | --- |
| `Camp` | 1 | 0 | 营地 | 非战斗地图 |
| `DarkForest` | 2 | 1 | 黑森林 | 是 |
| `RuinedCemetery` | 4 | 2 | 废村 | 第 2 阶段三选一 |
| `SaltpetreDesert` | 8 | 2 | 硝石荒漠 | 第 2 阶段三选一 |
| `MudSwamp` | 16 | 2 | 泥鱼沼泽 | 第 2 阶段三选一 |
| `CrystalMountain` | 32 | 3 | 结晶山 | 第 3 阶段二选一 |
| `MagmaCave` | 64 | — | 地热洞窟 | 仅本地化/枚举，当前包无现行入口 |
| `IceCavern` | 128 | 3 | 冰窖洞窟 | 第 3 阶段二选一 |
| `CastleBridge` | 256 | 4 | 黑城堡大桥 | 第 4 阶段二选一 |
| `MainCastle` | 512 | 5 | 黑城堡 | 是 |
| `MageTower` | 1024 | 6 | 法师塔 | 是 |
| `Sewer` | 2048 | 4 | 城堡地牢 | 第 4 阶段二选一 |
| `Random` | 536870912 | — | 未知地区 | 不断言路线 |
| `TrainingRoom` | 1073741824 | 0 | 训练场 | 非主路线 |

地图证据来源为 `DefaultPackage_2026-08-18-1017` 的 scenario 配置和本地化表。游戏更新后必须重新导出 enum、route 和 label 三者，不能只改中文名。

## 9. 真实样本数值基线

| 样本 | 关键输入/候选 | 官方/画面 | 裁决 |
| --- | --- | --- | --- |
| A 无召唤、投掷/爆炸桶 | `mRealHPDamage` 直和 `41231.479` | 造成伤害 `34486` | 直和高 `19.56%`，过量伤害假设形成 |
| A2 普通攻击+死亡复活 | 诊断和 `11160.532` | `10899` | 差 `2.40%`；命中前 HP 时序失败 |
| A3 HP 快照 | 逐击实际 HP 差 `ceil` = `7293` | `7293` | 造成伤害公式首次精确闭合；承伤 `132` 对 `134` 未闭合 |
| B 噩梦娃娃初样 | 逐击 `12283.004`；房间边界 `8700.789` | `10780` | 跨 path 求和和通用 owner hierarchy 均失败 |
| B2 娃娃归属 | 玩家 `4300` + 娃娃 `1678` = `5978` | `5979` | 归属 PASS；三位小数日志造成 1 点量化边界 |
| Probe 0.5 双样本 | 玩家 `6806` + 娃娃 `1179` | `7985` | round-trip 后精确闭合；无召唤样本也精确 `7811` |
| 0.6 特殊攻击/减伤 | 玩家 `6439` + 子实体 `2399`；承伤原始 `258`，实际候选 `158` | 造成 `8838`，承伤 `258` | 特殊实体归属、官方承伤口径 PASS |
| 0.6 元素双样本 | 冰附伤 `6645+1058`；混合毒/爆炸候选 | `7703` / `7599` | 两局精确闭合；`depth>0` 不可统一排除 |
| 0.8 Boss 长局 | 总 `103848`；Boss `24271`；承伤 `358` | 三项同值 | 总伤害、Boss、元素、承伤 PASS；致死 88 对击杀 89 |
| 0.9 香蕉负控 | 连续 10 根；HP hook 事件 0 | 第 9 根部分有效，第 10 根满血 | 路径覆盖 FAIL；不能解释为治疗 0 |
| 0.10 玩家 HP 负控 | `140→96.647934→75.19769`，三类 HP hook 仍 0 | 明确受击 | 基类/候选 setter 覆盖失败 |
| 0.11 多恢复负控 | 香蕉、灵药 `110→140`、魂石到 `49/140`；HP 事件全 0 | 伤害/承伤仍闭合 `41041/229` | 确认错误是玩家类型过滤，不是错日志 |
| 0.12 六根香蕉 | 请求 `42`；有效 `31.7012024`；溢出 `10.2987976` | `108.2988→140` | 来源、有效量、溢出、嵌套去重 PASS |
| 0.12 炼金灵药 | 11 tick 请求 `77`；有效 `75.687134` | `64.31287→140` | 截图区间精确闭合 |
| 0.12 魂石/红血/清场 | 魂石约 `30` + 红血 `6.629997` + 清场 `0.7804966` | `12.894005→50.304497/142` | 多来源分流与 35% 阈值 PASS |
| 0.3.2 MP/会话聚焦样本 | 长杖面板 `24`、短按实扣 `12`；另一武器面板/实扣均 `48`；同次官方/底层双路径 | `120→108`、`120→72`；恢复 `+6,+6`；两次黑森林入口产生独立 session | 消耗、恢复回调、去重和新图清零 PASS；长杖差异为长按持续消耗机制，不是计算 Bug |
| 0.3.2 初始化回蓝负控 | 新 session/room 后、首次施法前官方回调 `+120` | 角色以满蓝进入黑森林 | `R-FAIL`：初始化被误记为恢复；0.3.3 增加首次耗蓝门 |
| 0.3.3 动态长按样本 | 黑森林安全区短按一次、长按两次 | `12`；`12+28*2=68`；`12+22*2=56` | 面板 `24` 非固定成本；总量由起步 12 与持续 `-2` tick 构成。安全区是视觉地图，但引擎尚未发 `room_started` |
| 0.3.3 战后回满负控 | 进入魔物区后累计耗蓝 `166`，作者肉眼确认打完回满 | 聚合仍 `mp_gained=0`；520 事件、0 duplicate/fault | 初始化过滤 PASS，但战后回满不走已接三条路径；0.3.4 验证 `ResetDataBy` |
| 0.3.4 持续耗蓝/系统回满 | 继续当前进度，长按持续扣蓝；系统在新房间恢复到 `120`，后续上限到 `125` | 回调目标 `120,120,120,125`；此前真实值 `52,22,20,112` | `ResetDataBy` 未命中；有效恢复应为 `68+98+100+13=279`，不是回调直和 `485` |
| 0.3.5 续局生命周期负控 | 继续已有房间，作者观察恢复 3 次（含 `116→120`） | 216 事件、91 条底层耗蓝、0 aggregate spend、0 gain、0 duplicate/fault；session 始终无 room | 差值算法未被执行；缺口是续局未重放 room-start。0.3.6 用首个官方耗蓝懒建立当前非营地 session |
| 0.3.6 续局差值正控 | 继续黑森林第 2 区，长按持续耗蓝，系统恢复 4 次 | session/room 在首个官方耗蓝前建立；恢复 `54+98+100+4=256`，消耗 `256`，净值 `0`；328 事件、0 duplicate/fault | 续局 bootstrap、动态耗蓝、目标值差分和去重全部 PASS；停止 MP 探针迭代 |
| 0.3.6 混合来源短局 | 黑森林入口一战；召唤物、地图投掷物、玩家元素均参与 | 官方伤害 `6341`、承伤 `35`、Boss `0`；Bridge 来源 `4101+1635+605=6341`，承伤两条 `35+35=70` | 总伤害/Boss PASS；投掷物未独立分类；承伤 FAIL，疑似召唤物 defender 未过滤，需保留 `target_kind` 正控 |
| 0.3.6 短退出生命周期 | 结算画面后正常退出到营地，再进黑森林战斗区 | 营地期间保留 `6341/70`；新 session-3 后伤害/承伤/MP/治疗全 0；577 事件、0 duplicate/fault | “回营保留→新图清零” PASS；手动退出未发 `session_ended`，不能替代完整通关结算 |
| 0.3.6 承伤目标正控 | 幽影提灯；作者先让召唤物承伤，再让玩家承伤 | 非玩家 `target-3/normal` 正数承伤 `246`，玩家 `target-9/player` 承伤 `44`；合计 `290`；257 事件、0 duplicate/transport fault | 根因确认：官方 defender 回调包含召唤物，0.3.6 未做玩家根过滤。0.3.7 已加单点过滤；末尾另有无 detail 的 Bridge error，随候选回归复核 |
| 0.3.7 承伤过滤回归 | 幽影提灯；召唤物先受伤、玩家后受伤 | taken 仅一条 `player=35`；召唤物 dealt `6629`；总伤害 `6629+3488+385=10502`；376 事件 | `R-PASS`：0 duplicate、0 collector fault、0 Bridge status error，连接冻结前 live；问题闭合 |
| 0.3.7 商店人偶/完整结算反例 | 黑森林商店人偶后正常打到结算 | 工具箱/游戏总伤害 `79751/67497`，Boss `32489/20235`；两项差额都为 `12254`；承伤两边均 `140`，恢复 `142` | `R-FAIL`：商店人偶事件同时污染总伤害和 Boss；0.3.8 使用已有地图生命周期将 `_Shop_` dealt 标为 `aggregate=false`，未增 Hook，待实机正负控 |
| 0.3.8 自伤物品正控 | 折断的妖刀诅咒：触发怨魂攻击时将当前生命值 15% 转为伤势生命，游戏说明该效果视作受击 | 截图时玩家 `167/190`，HUD 官方承伤 `0`、恢复 `+6`；0.3.8 已加载且 pipe live | `R-FAIL`：恢复链正常，自伤/伤势负向变化未进入统计；源码静态确认 recovery-only 过滤会丢弃负 delta。作者仍在继续本局，暂不改 Hook/部署 |
| 0.3.8 商店二次反例/结算 | 同局在黑森林第 5 区商店攻击人偶后结算 | 工具箱/游戏总伤害 `45310/39710`；工具箱/游戏 Boss `5600/0`；差额精确等于错误 Boss。双方官方承伤均 `35` | `_Shop_` 文件名假设被证伪；桌面 1.5.4 不是原因。0.3.9 改用 `StageMgr.IsNonBattleRoom()`；官方承伤继续保持结算口径，自伤单列 |
| 0.3.9 非战斗房/完整结算回归 | 作者正常打一局，包含非战斗房人偶和真实战斗 | 人偶不再进入伤害；工具箱/游戏结算均为总伤害 `59627`、官方承伤 `84`、Boss `20054` | `R-PASS`：游戏非战斗房语义正负控闭合；停止房间过滤迭代 |
| 0.3.9 第二种诅咒道具 | 灭世之槊：持有时每秒燃烧生命上限 15% 的生命 | 角色出现大幅生命/伤势变化；旧桌面 1.5.4 HUD 官方承伤仍为 `0`，符合结算口径；来源表无自伤列且没有唯一自伤 token | `INCONCLUSIVE`：截图不能证明内部 `hp_loss_other`；停止要求作者反复找界面。仅在能冻结 HP/RedHp + hit receipt 时再开功能 |
| 1.5.5 长局/跨地图反例 | 黑森林完整通关并进入废村；正常战斗与结算 | 工具箱/结算总伤害 `177901/177901`、受击承伤 `347/347`、Boss `23483/23483`；法力 `238/236`；废村入口未刷新，废村第 1 区显示入口 | 核心伤害继续 `R-PASS`；法力差 2 为 `H`；位置时序 `R-FAIL`。0.4.0 改用 room-end 并加诊断，待一次同路线复核 |
| 0.4.0 跨地图位置回归 | 黑森林跨图到废村/硝石荒漠入口 | 作者在入口截图确认位置立即正确；日志顺序包含 `DarkForest 8 -> SaltpetreDesert 0 -> 1 -> 2` | `R-PASS`：room-end 读取修复一房间延迟；停止位置 Hook 迭代 |
| 0.4.0 原始 MP 样本 | 无禁回状态的长局 | 官方耗蓝 21 次、原始合计 `504`；恢复 18 次、原始合计约 `508.67097`，逐事件显示端点合计 `509` | 逐事件取整会积累偏差；0.4.1 改为 raw 累计、UI 边界统一取整 |
| 0.4.0 禁咒羊皮纸漏回蓝 | 新局携带禁咒羊皮纸；多次技能消耗并经历房间系统回满 | 截图满蓝 `130/130`，HUD 恢复 `0`；日志有 6 次耗蓝合计 `207`、无有效官方恢复，后续 `last_observed_raw` 已回到 `130` | `R-FAIL`：羊皮纸禁止攻击回蓝，但房间系统回满真实发生；官方回调缺失。0.4.1 复用低层 MP 观察兜底并按根操作抵扣官方覆盖量，无新增 Hook |
| 0.4.1 羊皮纸续局官方回蓝 | 重启后继续同一羊皮纸局，在硝石荒漠诅咒房消耗并回满 | 2 次官方耗蓝合计 raw `114`；18 次官方恢复合计 raw `114`；HUD `114 / +114`；`runtime_gain=0` | `R-PASS`：0.4.1 加载/pipe 与官方回调分支无漏记、无双计。该局回蓝触发了官方回调，因此低层缺回调兜底仍未形成实机正控 |

详细证据见 [`artifacts/damage-probe`](../artifacts/damage-probe/) 各冻结样本 README；表中一个样本只能证明对应人口、路线、版本和动作，不能外推所有玩法。

## 10. 当前 Bug、缺口与优先级

| 优先级 | 项目 | 已知事实 | 尚缺证据/动作 |
| --- | --- | --- | --- |
| P0 | 最大化窗口启动长白屏 | 作者完成“最大化窗口 -> 窗口化全屏 -> 切回”往返复现；长白屏随显示模式变化。当前“窗口化全屏”实存值为 `2`，肉眼白屏消失 | 保留当前模式；后续启动验收必须冻结显示模式，白屏与总耗时分别判定 |
| P0 | 0.3.1 诊断版启动回归 | 新增多组 Harmony 入口后白屏/卡死/闪退；回滚 0.3.0 后可进入 | 若要定位唯一入口，只能在隔离候选逐个二分；不得在用户主游戏目录盲试 |
| P1 | MP 原始累计与回调缺口 | 0.4.0 证明恢复含小数；0.4.1 羊皮纸续局已确认官方回调 raw `114` 与 HUD `+114` 一致、`runtime_gain=0`，官方分支无双计 | 缺回调时的低层正 delta 兜底仍缺实机正控；只在后续自然再次出现“回满但无官方 callback”时被动裁决，不要求作者强造 |
| 已闭合 | `OnRecoverMana` 有效量语义 | 回调字段是恢复后目标值，不是增量；有效量为最近真实 MP 到回调后 MP 的 raw 差 | 0.4.1 只在最终 UI 取整；官方缺席时由现有低层观察补记 |
| 已闭合 | 安全区/跨地图位置晚一房间 | 0.3.9 在 room-start 读取会晚一房间 | 0.4.0 room-end 实机确认废村入口及 `DarkForest 8 -> SaltpetreDesert 0 -> 1 -> 2` 顺序正确 |
| 已闭合 | 承伤混入召唤物 | 0.3.6 目标正控确认非玩家 `246` 与玩家 `44` 同进 taken | 0.3.7 只保留玩家 `35`，召唤物 dealt `6629` 不受影响；0 duplicate/fault/status error。停止探针迭代 |
| P1 | 完整通关 `session_ended` | 短局手动退出只证明营地保留和新图清零，没有发 `session_ended` | 将来正常完成整局时被动采集一次；不要求为此额外重打一整局 |
| P1 | 完整结算生命周期 | 回营保留、再次进图清零已实机通过 | 仍需真正完成一局，确认 `session_ended -> 营地保留 -> 新图清零` 全链路 |
| P2 | 炼金减耗 | 当前 12/48 普通样本闭合；长杖 24/12 已确认为长按语义 | 炼金 5% 减耗下对照面板、官方事件和 MP 前后值 |
| P2 | 自伤/其他 HP 损失 | Bridge 对官方伤害结算外的直接负 HP 发内部候选事件；伤势生命路径和统一 hit 关联未闭合，UI 不展示 | 找到可冻结的 HP/RedHp + hit receipt 后再开产品指标，避免与受击双计 |
| P2 | 护盾/诅咒/effect stack | schema、registry、aggregator fixture 存在 | 游戏 Hook 未闭合；不能在功能说明中宣称完成 |
| P2 | 未登记 token | `enemy.damage` | 明确 UI 是否需要显示后再补 registry 与测试；`set_cur_hp` 已登记 |
| P2 | checkpoint 差异 UI | checkpoint 已传输和保存 | 尚无明确的事件累计 vs checkpoint 差异呈现 |
| P2 | BepInEx 启动耗时 | 暖启动三臂显示 B 相对 A 约 `+6.25 s`，C 未慢于 B；作者确认总体等待可接受 | 仅做回归基线；除非后续明显恶化，不改启用策略 |
| P2 | 击杀 | 致死伤害少于官方击杀 | 接官方击杀事件；不可推算补 1 |
| P2 | 死亡/复活与短期诅咒 | 现有 HP 观察不足 | 独立生命周期正负控 |
| P3 | 多人权威性 | 单机/本地玩家样本为主 | 主机、客户端、中途加入、玩家离开、预测/RPC 去重 |
| P3 | 游戏更新兼容 | 所有映射绑定 build 24795992 | 更新后重算 hashes、interop、patch 签名、路线和正控 |

## 11. 启动性能的可证伪测试合同

2026-08-27 已按本合同完成三轮拉丁方测试和一次 C 组视觉补测。完整逐次数据、限制、退出观察与恢复哈希见[三臂实测结果](LC2_STARTUP_PERFORMANCE_2026-08-27.zh-CN.md)。日志本身只说明 BepInEx、Il2CppInterop、Bridge 0.3.0 和 Chainloader 最终完成；`Class::Init signatures have been exhausted` 是警告，不足以单独认定根因。

本次和以后复测都使用同一机器、同一分辨率、同一 Steam 状态，并按三臂比较：

| Arm | 组成 | 回答的问题 |
| --- | --- | --- |
| A | 原版游戏，不加载 BepInEx | 游戏自身启动基线 |
| B | BepInEx 保留，Bridge 禁用 | BepInEx/Il2CppInterop 本体成本 |
| C | BepInEx + Bridge 0.3.0 | Bridge `PatchAll` 和插件初始化的增量成本 |

本次有效结果：A/B/C 主菜单时间中位上界约为 `16.46 / 22.71 / 20.97 s`；B/C Chainloader 中位数约为 `7.764 / 7.786 s`。因此 Bridge 0.3.0 未显示 B 组之上的启动成本，BepInEx/Il2CppInterop 才是数秒级增量的主要候选。原版首轮也曾达到约 `23.24 s`，所以这些数字只描述本机本次暖缓存序列，不外推为普遍常数。

以后复测仍须每臂至少 3 次，记录实际进程创建、首个非空白帧/主菜单、`SceneMgr Set IsLoadingScene: False`、无响应与退出延迟，并使用中位数和最慢一次。若 C 明显慢于 B，再检查 Harmony 安装和插件同步初始化；若 B 持续明显慢于 A，则应重新设计 BepInEx 启用方式。

这项 A/B/C 会更改游戏加载状态，属于独立 runtime 测试阶段；执行前必须冻结三个精确文件清单和回滚路径。2026-08-27 测试结束已恢复 C 状态，进程为 0，loader、Bridge 0.3.0 与游戏 EXE 哈希均与测试前一致。

## 12. 后续维护步骤

1. 先按“症状速查表”定位一条链路，禁止同时改多个 Hook 猜根因。
2. 复核游戏 build、`GameAssembly.dll`、metadata、interop 和实际部署 Bridge 哈希。
3. 从本表找到原始类型、单位、转换、协议、聚合和 UI；确认差异发生在哪一层。
4. 最小样本必须包含一个正例和一个负例/满值/阻止/溢出例。
5. 新字段先更新 schema/registry/replay，再接 Bridge；新 Hook 先做准确签名和启动门。
6. 运行样本记录版本、动作、画面值、日志 identity 和公式；不要只记录“看起来好了”。
7. 更新本表的证据标签和样本行；历史 FAIL 保留，避免重复走弯路。

主要维护入口：

- Bridge：[`game_plugins/LC2CombatBridge/Plugin.cs`](../game_plugins/LC2CombatBridge/Plugin.cs)
- Pipe/session：[`game_plugins/LC2CombatBridge/CombatPipeServer.cs`](../game_plugins/LC2CombatBridge/CombatPipeServer.cs)
- 协议：[`contracts/combat_event.schema.json`](../contracts/combat_event.schema.json)
- 聚合：[`toolbox/combat_aggregator.py`](../toolbox/combat_aggregator.py)
- 传输：[`toolbox/combat_transport.py`](../toolbox/combat_transport.py)
- UI：[`toolbox/app_shell.py`](../toolbox/app_shell.py)
- 来源注册：[`assets/combat_sources.json`](../assets/combat_sources.json)
- 地图注册：[`assets/game_locations.json`](../assets/game_locations.json)
- 历史探针版本：[`artifacts/damage-probe/probe_versions/README.zh-CN.md`](../artifacts/damage-probe/probe_versions/README.zh-CN.md)
