# 失落城堡 2 工具箱：宏与实时伤害模块计划

记录日期：2026-08-26（Asia/Shanghai）

## 2026-08-27 开源阶段更新

- 项目迁入 `SeasonCake/lostcastle2-toolbox`，MIT 许可证仅覆盖本项目源码，不覆盖游戏文件与资产。
- 新增 `combat_event` v2：把伤害、HP/MP 变化、护盾/诅咒等效果层、触发因果、房间校准与连接状态统一为可回放事件。
- 新增来源注册表与纯聚合器。香蕉、炼金灵药、自愈魂石或未知新道具不再各写一套统计逻辑；新来源默认先显示原始 token，再通过注册表补中文名称。
- 召唤物、投射物和 DOT 使用 `owner_player_id` 归属玩家；击杀/召唤物击杀触发使用 `trigger_event_id` 与 `trigger_kind` 保留因果。
- 法力消耗、法力恢复、恢复禁止、溢出和周期回满使用同一个 `resource_change` 合同；护盾层和免伤类状态使用 `effect_stack` / `damage_resolution`，不与生命恢复混算。
- 正式 HUD 可以先基于回放快照建设，不再把训练木桩作为前置条件。下一阶段先完成桥接 v2 与 HUD 壳，再补法力/护盾运行时 Hook 正控。
- UI 方案已选定为“B 型紧凑 HUD + A 型主窗口详情”：独立 HUD 只负责游戏中快速扫读，完整拆分只在综合主窗口维护；两者消费同一战斗快照。工具启动入口改为综合主窗口，键盘半镂空悬浮窗降为可独立开关的模块。
- 免费开源维护边界：不继承 BidKing 的账号、激活、服务器、云同步、遥测或更新平台；优先标准库、版本化本地 JSON、来源注册表和单一 view-model。

## 当前结论

1. 按键显示器继续保持独立、轻量；宏和伤害统计作为并列模块接入工具箱，不把输入发送或游戏 Hook 混进按键显示逻辑。
2. 视频最初公开的 HUD 不是逐次命中级实时统计。作者在评论回复中明确说明：它同步的是游戏结算数据，房间清空后更新；最终 Boss 房会因直接结算来不及同步，只能参考百分比。后续 2026-08-14 的 `1.6.4` 包已经加入逐击回调和多层回退，但这属于新的、复杂度更高的实现，不能反向证明视频版本或当前游戏版本的准确性。
3. 当前本机游戏已在 2026-08-24 更新到 Steam build `24795992`、Unity `6000.3.16f1`、IL2CPP metadata `39`。作者提供的 2026-08-14 包只做了静态读取，没有加载其中任何第三方 DLL，也不能视为当前版本兼容证据。
4. 当前元数据中能确认存在以下候选语义：
   - `add_OnHitActual` / `add_OnBeHitActual`
   - `Action_OnHit` / `Action_OnAfterHit_Atker` / `Action_OnAfterHit_BeAtker`
   - `Battle_DamageInfoInRoom`
   - `AdventureRecordDamageSettlementCalculator`
   - `_attackerToTalDamage` / `_bossRoomDamageDict`
   - `_finalDamage` / `_finalRealDamage` / `_additionRealDamage`

这些名字证明游戏内部具备命中事件和房间结算数据，但尚不能单凭字符串确定方法签名、调用时机、网络端职责或伤害口径。

## 目标架构

```text
Lost Castle 2
  └─ LC2DamageBridge（BepInEx 6 / IL2CPP，只观察、不改数值）
       ├─ 命中后事件：真实伤害、攻击者、受击者、来源
       ├─ 房间结算：游戏权威房间累计值
       └─ 本机命名管道（版本化 JSON 行）
             ↓
失落城堡2工具箱.exe
  ├─ 按键显示
  ├─ 宏控制
  └─ 伤害 HUD / 房间历史 / 差异诊断
```

游戏内桥接 DLL 只读取已结算事件并向本机工具发送，不直接绘制 UI，不修改伤害、掉落、网络或存档。外部工具负责显示、配置和导出。桥接不可用时，按键显示和宏模块仍应独立工作。

## 伤害记录口径

主口径必须使用伤害已经解析后的实际值，而不是攻击面板预测值：

- `applied_damage`：目标实际扣除的生命值，主统计使用。
- `raw_damage`：结算前原始值，仅诊断使用；无法可靠取得时为空。
- `owner_player_id`：召唤物、投射物、DOT 必须回溯到玩家所有者。
- `source_entity_id`：保留具体召唤物或伤害实体，支持后续组件拆分。
- `room_id` + `sequence`：用于房间切换和网络重复事件去重。
- `is_boss`：基于目标身份，而不是根据房间名称猜测。
- 房间清空时用游戏自身 `Battle_DamageInfoInRoom` 类数据做 checkpoint；事件累计和权威 checkpoint 都保留，出现差值时显示“待校准”，不静默覆盖。

### 必须验证的伤害类型

1. 普通近战、远程与暴击。
2. 召唤物直接伤害与召唤物 DOT。
3. 玩家施加的中毒、灼烧、持续区域伤害。
4. 过量伤害：分别记录原始值与实际扣血值。
5. Boss 最后一击和直接进入结算的场景。
6. 主机、普通客户端、加入中途与玩家离开。
7. 同一命中在本地预测、ServerRpc、ClientRpc 路径上的去重。

## 伤害模块实施阶段

### D0：当前版本身份冻结（已完成）

- Steam app `2445690`，build `24795992`。
- Unity `6000.3.16f1`，metadata `39`。
- `GameAssembly.dll` SHA-256：`747E8BECB7B97B014D7F282C1EB60A7A4754A8A1DF01CEB943C03967F6E6F1C5`。
- `global-metadata.dat` SHA-256：`D42663B5ED61E9D5D30FCEF878969507C4B04951595DD61D63B5E0BD7017984A`。

### D1：隔离生成当前 interop（已完成）

- 经作者明确授权，在真实游戏目录安装官方 BepInEx 6 IL2CPP bleeding-edge `6.0.0-be.785`。
- 首次启动只生成 interop；共 `203` 个文件、`168,796,588` 字节，零个空文件。
- 原始 `LostCastle2.exe`、`GameAssembly.dll`、`global-metadata.dat` 哈希未变。

### D2：只记录候选 Hook（玩家造成伤害口径已闭合，归属继续采样）

- 临时探针当前已升级到 `LC2DamageProbe 0.12.0`，保留 0.11.0 的 11 个观察目标，只修正玩家根实体过滤；当前部署 DLL SHA-256 为 `22BDF20B51BFB777D5A63FFF14502F0E8ED65C815568FE014E2088A6D9C8FA6B`。
- 0.5.0、0.6.0 与 0.8.0 的伤害观察面均已 runtime PASS；0.8.0 的 `main_attrs/attrs` 与 `defender_is_boss/elite` 已通过长局正控。0.9.0–0.11.0 的 HP 观察均被同一过滤错误影响。0.12.0 修正后，香蕉 `ExhaustProps#Banana_0`、炼金灵药截图区间的 `EatFood`、`FullFoodEnergyOrRecoverHp` 高层入口，以及魂石 `Gem#A_015_2` 均已获得有效/溢出/零恢复正控；hero/base 嵌套以 parent/depth 去重。最终低血片段还证明魂石、`red_blood=true` 恢复和清场恢复会同时存在，必须按来源分列。各版均不写 HUD、不聚合、不修改返回值。
- 双样本以有召唤物官方 `7985` 和无召唤物官方 `7811` 精确闭合造成伤害，正式候选公式细化为 `sum(ceil(max(0, min(mRealHPDamage, hp_before))))`。命中前 HP 用于截断过量伤害，但不能再直接以单精度 HP 写回后的文本差替代伤害字段。
- 承伤口径已在 0.6.0 多层减伤样本闭合：7 个玩家受击的减伤前 `mOriFinalDamage` 逐击向上取整合计 `258`，与官方精确一致；减伤后 `final/applied` 候选只有 `158`。官方承伤与实际掉血必须分列，减伤效果不会降低结算卡承伤数字。
- 不写 HUD、不聚合、不修改返回值。

首个真实样本已完成 B 组（单人 + 噩梦娃娃），详见 [`artifacts/damage-probe/B_nightmare_doll_20260826/README.zh-CN.md`](../artifacts/damage-probe/B_nightmare_doll_20260826/README.zh-CN.md)。该样本确认逐击可见，但同时否定了“跨 path 直接求和”和“所有召唤物都能沿 `OwnerEntityInHierarchy` 回溯玩家”两条假设；用户可见总伤害仍需 A 组闭合。

A 组（单人、无召唤物，含投掷/爆炸桶/回血）也已完成，详见 [`artifacts/damage-probe/A_no_summon_throw_barrel_heal_20260826/README.zh-CN.md`](../artifacts/damage-probe/A_no_summon_throw_barrel_heal_20260826/README.zh-CN.md)。A 的逐击诊断和仍比结算高 `19.56%`，所以 B 的差值不是召唤物独有；过量伤害成为首要假设，但需要命中前 HP 才能证实。

A2 组（单人、仅普通攻击，含死亡复活）详见 [`artifacts/damage-probe/A2_basic_only_death_revive_20260826/README.zh-CN.md`](../artifacts/damage-probe/A2_basic_only_death_revive_20260826/README.zh-CN.md)。逐击诊断和与官方差值缩小到约 `2.40%`；0.2.0 证明后置 HP、OwnerPlayer 与召唤标记可用，但命中前 HP 时序不可用。探针随后升级为 0.3.0，把 HP 观察点下移到 `DamageProcess`。

A3 组（单人、普通攻击，0.3.0 HP 快照校准）详见 [`artifacts/damage-probe/A3_basic_hp_snapshot_20260826/README.zh-CN.md`](../artifacts/damage-probe/A3_basic_hp_snapshot_20260826/README.zh-CN.md)。175/175 个 hit 的前/后 HP 完整；该样本的 HP 差逐击向上取整与官方 `7293` 一致，首次闭合过量伤害与逐击取整。0.5.0 后续证据表明，更稳健的正式候选应使用 `min(mRealHPDamage, hp_before)` 后逐击向上取整；两种公式在 A3 样本上等价。承伤仍未闭合。

C 组（本地玩家 + NPC「霞」）详见 [`artifacts/damage-probe/C_player_npc_xia_20260826/README.zh-CN.md`](../artifacts/damage-probe/C_player_npc_xia_20260826/README.zh-CN.md)。本地玩家 54 个命中的实际扣血逐击向上取整为 `3914`，再次与官方造成伤害精确一致；NPC 及其技能实体归属到独立 NPC 根实体，不计入玩家卡片，且游戏结算页没有 NPC 独立卡片。C 同时发现冰属性派生伤害的 `DamageProcess` 嵌套，促成 0.4.0 父子命中字段；NPC 候选伤害只能作为工具侧校准值，不能冒充官方值。

B2 组（单人 + 噩梦娃娃，0.4.0 归属正控）详见 [`artifacts/damage-probe/B2_nightmare_doll_precision_20260826/README.zh-CN.md`](../artifacts/damage-probe/B2_nightmare_doll_precision_20260826/README.zh-CN.md)。召唤物实体以 `OwnerPlayer` 与 `Master` 双路径稳定回溯到本地玩家，归属判定 PASS；玩家直伤与召唤物顶层 HP 区间的逐击取整候选为 `5978`，官方为 `5979`。残差仅 `1`，且可由 0.4.0 的三位小数日志量化解释，促成 0.5.0 round-trip 浮点输出；B2 无需重跑。

0.5.0 双样本（先误带噩梦娃娃、后做无召唤负控）详见 [`artifacts/damage-probe/probe_0_5_roundtrip_dual_sample_20260826/README.zh-CN.md`](../artifacts/damage-probe/probe_0_5_roundtrip_dual_sample_20260826/README.zh-CN.md)。玩家直伤 `6806` 加娃娃 `1179` 精确得到官方 `7985`；无召唤样本 116 个顶层命中精确得到官方 `7811`。该样本完成 0.5.0 runtime 与 round-trip 正控，也确认娃娃承伤不能沿主人计入玩家承伤。第二局官方承伤 `151` 与当前 4 个玩家 HP 命中的逐击候选 `147` 仍差 `4`，承伤路径继续保持未闭合。

0.6.0 特殊攻击 + 多层减伤样本详见 [`artifacts/damage-probe/probe_0_6_reduction_take_damage_20260826/README.zh-CN.md`](../artifacts/damage-probe/probe_0_6_reduction_take_damage_20260826/README.zh-CN.md)。本局不是纯普通攻击：玩家本体 `6439` 加 `OwnerEntity=玩家` 的技能派生实体 `2399` 精确得到官方造成伤害 `8838`，10 个致死命中与击杀 `10` 一致；7 个 `ori_final` 逐击向上取整精确得到官方承伤 `258`。该样本闭合了特殊攻击子实体归属与减伤前官方承伤口径，但没有裁决百分比、固定与防御减伤之间的唯一乘加顺序。

0.6.0 元素混合双样本详见 [`artifacts/damage-probe/probe_0_6_element_mixed_20260826/README.zh-CN.md`](../artifacts/damage-probe/probe_0_6_element_mixed_20260826/README.zh-CN.md)。第一局电系法杖 + “不融冰”由作者观察到冰伤，补回的对局记录为 `7703/37/8`；119 个顶层事件 `6645` 加 7 个拥有独立官方事件的嵌套附伤 `1058`，精确闭合 `7703`。第二局毒法杖 + 毒桶同时出现毒与火，毒 DOT、毒泉、爆炸及法杖投射等 182 个事件精确闭合官方 `7599`，8 个致死命中与击杀一致。0.6.0 未输出最终 `AttrType`，因此来源与总量 PASS，具体元素身份仍需只读字段正控。

0.8.0 Boss + 随机元素长局详见 [`artifacts/damage-probe/probe_0_8_boss_element_longrun_20260826/README.zh-CN.md`](../artifacts/damage-probe/probe_0_8_boss_element_longrun_20260826/README.zh-CN.md)。1,588 个官方攻击事件精确闭合总伤害 `103848`；374 个 `IsBoss=true` 事件精确闭合 Boss 伤害 `24271`；8 个 `ori_final` 精确闭合官方承伤 `358`，其中冰属性受击正控成立。营地木桩只有 HP 快照、没有官方攻击事件，明确排除。击杀的伤害致死事件为 88、官方为 89，不能从伤害事件完全反推；有效治疗、短期诅咒直接 HP 变化与死亡/复活仍需最窄生命周期观察。

0.9.0 香蕉恢复负控详见 [`artifacts/damage-probe/probe_0_9_banana_heal_missed_20260827/README.zh-CN.md`](../artifacts/damage-probe/probe_0_9_banana_heal_missed_20260827/README.zh-CN.md)。作者连续吃 10 根香蕉：第 9 根部分有效并溢出，第 10 根满血触发但有效恢复为 0；0.9.0 虽成功挂载 `ChangeCurrentHp` 且无异常，却产生 0 条 HP 变化事件，证明该单一入口不能覆盖香蕉。0.10.0 因此同时观察进食高层入口与实际 HP setter，并用嵌套深度防止重复累计。

0.10.0 玩家 HP 覆盖负控详见 [`artifacts/damage-probe/probe_0_10_player_hp_override_missed_20260827/README.zh-CN.md`](../artifacts/damage-probe/probe_0_10_player_hp_override_missed_20260827/README.zh-CN.md)。本局两个玩家受击事件分别把 HP 从 `140` 降到 `96.647934`、再降到 `75.19769`，但 `hp_change/hp_set/hp_food_recover` 全部为 `0`；这已独立证伪 0.10.0 对玩家 HP 写入的覆盖。interop 显示 `HeroRuntimeData.ChangeCurrentHp` 覆盖基类虚方法，促成 0.11.0 最窄补丁。作者是否在该局使用香蕉尚未明确，因此恢复语义继续保持未裁决。

0.11.0 多恢复负控详见 [`artifacts/damage-probe/probe_0_11_multi_heal_missed_20260827/README.zh-CN.md`](../artifacts/damage-probe/probe_0_11_multi_heal_missed_20260827/README.zh-CN.md)。作者明确执行香蕉回满、炼金灵药 `110→140` 和魂石自愈到 `49/140（35%）`，但三类 HP 日志仍全部为 `0`；同一日志又以 `41041/229` 精确闭合结算截图，排除了错日志和样本不完整。源码复核确认 0.9.0–0.11.0 的玩家过滤把 `Creature` 错转为无继承关系的 `Player`，这是合法事件被统一丢弃的已确认实现错误，促成 0.12.0 过滤修正。

0.12.0 香蕉恢复正控详见 [`artifacts/damage-probe/probe_0_12_banana_heal_pass_20260827/README.zh-CN.md`](../artifacts/damage-probe/probe_0_12_banana_heal_pass_20260827/README.zh-CN.md)。截图香蕉数量 `10→4` 与 6 次外层调用一致；每根请求 `7`，前四根各有效 `7`，第 5 根只有效 `3.7012024`，第 6 根有效 `0`，合计有效恢复 `31.7012024`，精确把 `108.2988` 补到 `140`。每个外层 `hero_runtime` 事件都有一个正确关联的内层 `creature_runtime` 事件，聚合只取 `depth=0`。同一日志还以 `5603/44/8` 精确闭合结算截图。

0.12.0 炼金灵药与魂石自愈正控详见 [`artifacts/damage-probe/probe_0_12_alchemy_self_heal_pass_20260827/README.zh-CN.md`](../artifacts/damage-probe/probe_0_12_alchemy_self_heal_pass_20260827/README.zh-CN.md)。灵药截图区间的 11 个 `EatFood` 外层事件合计有效恢复 `75.687134`，精确闭合 `64.31287→140`；高层 `FullFoodEnergyOrRecoverHp` 另有有效恢复与满血 `result=false` 正控。最终自愈片段实际从 `12.894005` 恢复到 `50.304497`，其中魂石 30 个 tick 合计约 `30`，红血恢复约 `6.629997`，清场恢复 `0.7804966`；`27/142` 只是中间截图。最大 HP 140 时魂石在 `49.000004` 的 13 次请求全部有效恢复 `0`，最大 HP 142 时最后一次从 `49.304497→50.304497` 后停止，闭合 35% 阈值。

### D3：归属与去重

- direct、summon、特殊攻击/技能子实体、毒 DOT、法杖 projectile、毒桶/毒泉和爆炸均已有正控；具体元素 `AttrType` 与 Boss 目标仍需后续样本。
- 事件资格以唯一且已归属的 `official_attacker` 为准；`depth>0` 的独立元素附伤仍计入。`depth` 只用于父子关系与防止基于外层 HP 总差重复累计，不能作为统一排除门。
- 主机与客户端同时记录时，确定唯一权威事件；预测事件只作诊断。
- 用房间 checkpoint 验证累计值，不能只凭结算页总数判定正确。

### D4：外部 HUD

- 默认显示本局总伤害、当前房间、最近 10 秒 DPS、Boss 伤害。
- 支持紧凑、纯净、侧边收起和点击穿透。
- 组件拆分（武器、召唤物、DOT）只在归属证据完整后开放。

## 宏模块合同

宏保持在外部工具进程中，默认通过 Windows `SendInput` 发送，不注入游戏：

- 仅在 `LostCastle2.exe` 为前台窗口时运行。
- 默认无启用中的宏；用户必须显式保存并启用配置。
- 支持 `按一次`、`按住循环`、`开关循环` 三种触发模式。
- 步骤只包含按下、抬起、点击和等待；第一版不录制鼠标轨迹。
- 任一停止路径都会释放工具按下的全部键。
- 游戏失去焦点、游戏退出、配置变化、工具退出或紧急停止时立即中止。
- 全局紧急停止键独立于宏触发键；不得被宏自身发送。
- 限制最短间隔、最大步骤数和单次最长运行时间，禁止无界忙循环。
- 每次运行显示明确状态；纯净模式仍保留一个可选的小型运行指示。

### M1：通用宏内核与编辑器（已完成）

- 已实现 `按一次`、`按住循环`、`开关循环` 三种触发模式，以及按一下、按下、抬起、等待四种步骤。
- 已实现游戏前台门、配置变更停止、最长运行时间、可中断等待、并发按键所有权与 `Ctrl+Shift+F12` 全局紧急释放。
- 三个示例全部默认停用；触发组合冲突或配置损坏时整份配置不运行，损坏文件不会被自动覆盖。
- 宏编辑器把“未保存”与“已生效”分开显示，并在最小窗口尺寸下保留步骤表、保存与停止入口。

后续若要随工具预置某个真正可直接使用的游戏连段，仍需作者确定具体技能、触发键和可接受的时序范围；当前示例只是结构模板，不代表推荐游戏打法。条件式读状态循环不在第一版范围内。

## 2026-08-14 第三方 HUD 静态参考审查

作者提供目录中的 `失落城堡2伤害统计v1.6.4-逐房强制官方校准修正版.dll` 仅通过 Mono.Cecil 读取元数据与 IL 字符串，未执行、未复制到游戏。确认其插件自报 `LC2 Damage HUD 1.6.4`，程序集名为 `LC2DamageMeter`、程序集版本 `1.4.6.15`。它已经不是视频最初的“清房后同步结算”单一路径，而是以下多层结构：

- 逐击来源：攻击者事件、玩家转发事件、目标受击事件，并用 `BuildHitDedupKey` / `AcceptHitOnce` 去重。
- 官方来源：网络权威数据、结算实时回退、房间/最终官方校准。
- 角色分流：日志明确区分 `CLIENT bounded fallback`、`HOST official-only`、`SOLO official-only`。
- 状态续接：存在 resume 主文件与备份、断线冻结、重连跟随官方、slot reset 检测。
- 展示耦合：UI 在游戏进程内绘制，并包含聊天分享路径。

这些机制说明作者已经碰到并处理过不少真实边界，但也暴露出我们必须避免的风险：

1. **同一命中多来源重复计数**：不能把事件名不同视为伤害不同；去重必须保留 hook path、hit identity、房间和序号，并用正反例证伪。
2. **倍率/锚点漂移**：官方累计只做 checkpoint 与差异展示，不用乘法 scale 静默改写逐击历史。
3. **主机/客户端口径分叉**：先找一条官方聚合入口作为主口径，再把逐击作为解释层；不能让 host、solo、client 显示同名但不同语义的数值。
4. **断线与持久化污染**：第一版不跨会话自动合并伤害；session、room、slot 变化一律显式分段，旧状态不得无提示续接。
5. **召唤物和 DOT 归属误判**：必须从 `source_entity_id` 回溯 `owner_player_id`，无法确认时进入“未归属”，不能硬塞给本地玩家。
6. **游戏内 UI/聊天耦合**：桥接层不绘制、不发聊天、不修改游戏对象；外部工具通过版本化本机 IPC 展示，桥接失效时不影响按键显示和宏。

因此，我们只借鉴其“多证据观察”和“官方 checkpoint”思路，不复制其 DLL、状态文件、校准倍率或游戏内 UI。

## 配置与目录

```text
失落城堡2工具箱/
  config/
    settings.json            # 现有按键显示，继续兼容
    macros.json              # 宏配置
    damage.json              # 伤害 HUD 配置
  modules/
    damage-bridge/           # 经验证的桥接 DLL 与身份记录
  exports/
    damage/                  # 用户主动导出的对局统计
```

跨模块只共享窗口风格、主题和进程检测；输入状态、宏执行、伤害事件和聚合状态分开拥有。

## 当前不做

- 不安装或运行作者提供的 2026-08-14 第三方插件 DLL；已执行的只有静态元数据读取。
- 不用 OCR 冒充实时伤害。
- 不把外部内存轮询作为首选方案。
- 不在未确认方法签名前写死 IL2CPP 地址。
- 不把召唤物或 DOT 差异静默归零。
- 不默认启用任何宏，也不绕过游戏平台或反作弊机制。

## 参考证据

- B 站视频与作者评论：<https://www.bilibili.com/video/BV1tfum66E6s/>
- 可复用的 Lost Castle 2 BepInEx / IL2CPP 工程方式：<https://github.com/wtksana/lc2mod>
