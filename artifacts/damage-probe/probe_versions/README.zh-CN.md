# LC2DamageProbe 版本记录

## 0.1.0

- SHA-256：`C3D8AAA93B8C8BAF7F3377F01E603BE2CC21CF09D1E6DDA1F65003C540DB0944`
- 大小：`13,312` 字节。
- 生命周期：A/B 组采样探针，historical；冻结副本 `LC2DamageProbe-0.1.0-C3D8AAA93B8C.dll`。
- 主菜单加载 6 个观察目标 PASS；A/B 两组战斗日志无 probe error。

## 0.2.0

- 当前部署 SHA-256：`D207292FDD42BA7EE8EF4C1B14EC3799A9E52F17B2CF474A5F75DD74A8D7D7C0`
- 大小：`16,896` 字节。
- 新增 `Creature.BeHitActual` 命中前/后 HP 观察，以及 OwnerPlayer/Master/召唤标记。
- 首次候选 `5F0513CCCCB3C483383D05C00F6BA9F42C8B483CCFFE4105122DCC793CC74220` 因 Harmony 参数名 `hit` 与游戏方法的 `hitInfo` 不一致，主菜单加载 FAIL，禁止作为可用探针。
- 修正参数绑定后，7 个观察目标主菜单加载 PASS，焦点日志零错误。
- A2 战斗样本证明 OwnerPlayer/召唤标记正控可用、命中后 HP 可用，但命中前 HP 因调用时序不可用；该版本自此 historical。

## 0.3.0

- SHA-256：`771968CCE7AAE6C10A9802E2B51258150BE3E2E3DAB46B19B007DCC657C7E0AD`
- 大小：`17,408` 字节。
- 将 HP 观察点从 `Creature.BeHitActual` 下移到 `BeHitExecutor_Creature.DamageProcess`，新增按 hit ID 关联的 `hp_snapshot`。
- 7 个观察目标主菜单加载 PASS，A3 样本以逐击实际扣血向上取整精确闭合玩家官方造成伤害。
- C 样本发现派生伤害可嵌套进入 `DamageProcess`；该版本没有直接记录父子关系，逐条累计会重复。自此 historical，冻结副本 `LC2DamageProbe-0.3.0-771968CCE7AA.dll`。

## 0.4.0

- SHA-256：`64545184D108B3BA6C1760402D4A8D24CCD405857A78BF3FE045742E0F3537ED`
- 大小：`18,432` 字节。
- HP 快照新增 `parent_hit_id` 与 `depth`，用于区分顶层实际扣血区间与嵌套派生伤害；总量只直接累计 `depth=0`，内层保留作来源拆分。
- 7 个观察目标主菜单加载 PASS，B2 召唤物战斗正控确认 OwnerPlayer/Master 归属组合；三位小数日志在逐击整数边界留下 `1` 点量化差。
- 冻结副本：`LC2DamageProbe-0.4.0-64545184D108.dll`。
- 生命周期：historical。

## 0.5.0

- 当前部署 SHA-256：`57A83C4EC587D407CB1AA1A552C1207D702A5FF8E3ECEAC5F5E4DDFC8881B792`
- 大小：`18,944` 字节。
- 浮点日志改为 round-trip 格式，保留精确 float 文本，消除 0.4.0 三位小数输出在逐击 `ceil` 整数边界造成的量化误差。
- 本机缺少 .NET SDK，标准 `dotnet build` 未开始；改用 Visual Studio 2022 Roslyn `4.7.0`、.NET 6.0.36 运行时托管程序集及同一游戏引用直接编译，编译零警告、零错误。
- 已在游戏未运行时部署并冻结为 `LC2DamageProbe-0.5.0-57A83C4EC587.dll`；自然启动时 7 个观察目标加载 PASS，焦点日志零错误。
- 双样本战斗验证同时闭合有召唤物 `7985` 与无召唤物 `7811` 的官方造成伤害。round-trip 证据把正式候选公式细化为 `sum(ceil(max(0, min(mRealHPDamage, hp_before))))`；详见 `probe_0_5_roundtrip_dual_sample_20260826/README.zh-CN.md`。
- 生命周期：当前观察探针，runtime PASS；承伤公式仍未闭合。

## 0.6.0

- 在 0.5.0 的同一 7-hook 观察面上新增 `ori_final=mOriFinalDamage` 与 `final_clamp=mFinalDamage_Clamp`。
- 目的：验证 `OnTakeDamage` 编译闭包中的整数 `oriFinalDamage` 是否解释官方承伤与实际 HP 扣血之间的差值。
- 不修改参数、返回值、伤害、HP、结算或网络状态；构建、部署与 runtime 状态见后续记录。
- SHA-256：`58B26D29CE0FC28AFEDFCC774386B30DDA1D034D8C48D79E36B17E761D694516`。
- 大小：`18,944` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 静态回读确认插件版本 `0.6.0` 且只新增两个目标 getter 调用。
- 已在游戏未运行时部署并冻结为 `LC2DamageProbe-0.6.0-58B26D29CE0F.dll`；源、冻结副本和游戏目录三方哈希一致。
- 自然启动时 7 个观察目标加载 PASS，焦点日志零错误；`ori_final` 与 `final_clamp` 均成功输出。
- 多层减伤样本中，7 个玩家受击的 `ori_final` 逐击向上取整精确得到官方承伤 `258`，而减伤后的 `final/applied` 候选仅为 `158`。
- 同一样本还以玩家本体 `6439` 加技能派生实体 `2399` 精确闭合官方造成伤害 `8838`；详见 `probe_0_6_reduction_take_damage_20260826/README.zh-CN.md`。
- 生命周期：当前观察探针，runtime PASS；承伤统计字段与技能子实体归属已闭合。

- 后续元素混合双样本又以毒 DOT、毒泉、爆炸及法杖投射实体精确闭合官方造成伤害 `7599`；0.6.0 不含最终 `AttrType`，具体元素身份仍不能从来源名称推断。
- 第一局补回的官方 `7703` 进一步确认：119 个顶层事件 `6645` 加 7 个嵌套独立附伤事件 `1058` 精确闭合；`depth>0` 不能自动排除拥有唯一官方攻击事件的元素附伤。

## 0.7.0

- 在 0.6.0 的同一 7-hook 观察面上调用游戏已有的只读 `CheckDamageMainAttrType` 与 `CheckDamageAttrType`，新增 `main_attrs` / `attrs` 字段。
- 只枚举游戏 interop 已确认的 `Fire/Ice/Poison/Electric/Evil/Blood`；无匹配输出 `None`，读取失败输出 `error`。
- 目的：验证法杖自身属性、宝藏决定的附魔属性、DOT 与爆炸的最终元素身份；不修改参数、返回值、伤害、HP、结算或网络状态。
- SHA-256：`1A077724BB8AC0A18DDF7D8BACB112C8C5B5E930B813B4B148C89E3683654793`。
- 大小：`19,968` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 回读确认插件版本 `0.7.0`、`LogHit` 两次调用 `DamageAttrs`，编译闭包实际调用两个游戏元素检查方法。
- 首次静态门因检查主方法体而没有看到闭包内调用，按预期阻止部署；修正审计定位后重新验证通过。该失败没有改变游戏目录，旧 0.6.0 哈希保持不变直到正式替换。
- 已在游戏未运行时部署并冻结为 `LC2DamageProbe-0.7.0-1A077724BB8A.dll`；源、冻结副本和游戏目录三方哈希一致。
- 生命周期：当前部署候选；尚未自然启动，不能称为 runtime PASS。
- 自然启动时同一 7 个观察目标加载 PASS，元素、Boss 与精英字段均成功输出且零读取错误。
- 长局以 1,588 个官方攻击事件精确闭合总伤害 `103848`；374 个 `IsBoss=true` 事件精确闭合 Boss 伤害 `24271`；8 个 `ori_final` 精确闭合官方承伤 `358`。
- 生命周期：当前观察探针，runtime PASS；总伤害、元素分流、Boss 分流与官方承伤已闭合。

## 0.9.0

- 在 0.8.0 上新增一个观察目标：`CreatureRuntimeData.ChangeCurrentHp`。
- 仅当 `OwnerCreature` 可确认为 `Player` 时记录；怪物、召唤物和其他实体不增加 HP 变化日志。
- prefix/postfix 记录请求变化量、前后 HP、前后 MaxHP、`effective_delta`、`effective_heal`、伤害类型、浮字/红血标志与受限长度的来源 token。
- `effective_heal=max(0, hp_after-hp_before)`，因此满血溢出自然为 0；复活仍需独立生命周期事件，不能仅凭 HP 上升记作普通治疗。
- SHA-256：`E5D55507910F4AC3AA21E7E7E08526E8C3F388B744004E6938B7F2D0E2389BC9`。
- 大小：`23,040` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 回读确认版本、`ChangeCurrentHp` patch、玩家 `TryCast` 过滤、前后观察调用及 `effective_heal` 字段均存在。
- 已在游戏未运行时部署并冻结为 `LC2DamageProbe-0.9.0-E5D55507910F.dll`；源、冻结副本和游戏目录三方哈希一致。
- 自然启动时 8 个观察目标加载 PASS，焦点日志无 probe error；但 10 根香蕉样本产生 `0` 条 `hp_change`，进食恢复覆盖 FAIL。详见 `probe_0_9_banana_heal_missed_20260827/README.zh-CN.md`。
- 生命周期：historical；加载 PASS、香蕉语义覆盖 FAIL。

## 0.10.0

- 在 0.9.0 上新增 `CreatureRuntimeData.SetCurHP(float)` 与 `FullFoodEnergyOrRecoverHp(Creature,float)` 两个玩家前后观察目标，总 hook 数为 10。
- 三条 HP 路径统一记录 `operation_id`、`parent_operation_id`、`depth` 与 `outermost`；同一次高层恢复调用若嵌套进入底层 setter，聚合只累计 `depth=0`，避免重复。
- 进食入口记录 `food_energy` 与返回值；setter 记录目标 HP。两者都输出前后 HP/MaxHP、`effective_delta` 与 `effective_heal=max(0,hp_after-hp_before)`。
- SHA-256：`83F0A33D11467E7F17BF12B1849B73162B06A468ED749BBACAF2AA720DD8C7FE`。
- 大小：`26,112` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 回读确认版本 `0.10.0`、10 个 patch 类型及两个新增目标的准确签名，所需 HP/嵌套/来源字段均存在。
- 已在游戏与工具箱均未运行时部署并冻结为 `LC2DamageProbe-0.10.0-83F0A33D1146.dll`；源、冻结副本和游戏目录三方哈希一致。
- 2026-08-27 自然启动时 10 个观察目标全部加载，完整退出后的日志零 probe error；加载门 PASS。日志 SHA-256 为 `C9980807D2C8AE7E3D25C83449B825230182AEC5E7BD451A9D77F3C3DD3AF122`，详见 `probe_0_10_startup_20260827/README.zh-CN.md`。本会话未发生恢复动作，因此进食/底层 HP 写入的语义覆盖仍待正控。
- 后续一局出现两个本地玩家 `official_defender` 与 HP 扣减快照，但 `hp_change/hp_set/hp_food_recover` 仍全部为 `0`；运行时负控证明三条路径未覆盖玩家实际 HP 写入。interop 同时确认 `HeroRuntimeData.ChangeCurrentHp` 覆盖基类虚方法，详见 `probe_0_10_player_hp_override_missed_20260827/README.zh-CN.md`。
- 生命周期：historical；runtime 加载 PASS、玩家 HP 语义覆盖 FAIL。

## 0.11.0

- 在 0.10.0 上新增 `HeroRuntimeData.ChangeCurrentHp(...)` 覆盖方法观察，总 hook 数为 `11`；保留基类 patch 作为其他类型诊断面。
- 基类和玩家覆盖方法统一输出 `kind=hp_change`，新增 `hook=creature_runtime|hero_runtime`；现有 `operation_id`、`parent_operation_id`、`depth` 与 `outermost` 继续用于嵌套去重。
- SHA-256：`96227EC1BA6610473D509C4C3CEF85C3F9A974453761C9AD596107E7C9B14C37`。
- 大小：`26,624` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 回读确认版本 `0.11.0`、11 个 patch 类型，新增目标精确为 `LC2.HeroRuntimeData.ChangeCurrentHp`，并确认两种 hook 来源字符串与共享后置观察调用。
- 已在游戏与工具箱均未运行时部署并冻结为 `LC2DamageProbe-0.11.0-96227EC1BA66.dll`；源、冻结副本和游戏目录三方哈希一致。
- 自然启动时 11 个观察目标全部加载，焦点日志零错误；作者在同一局明确执行香蕉回满、炼金灵药 `110→140` 与魂石自愈到 `49/140`，但 `hp_change/hp_set/hp_food_recover` 仍全部为零。日志以 `41041/229` 精确闭合结算截图，详见 `probe_0_11_multi_heal_missed_20260827/README.zh-CN.md`。
- 源码与 interop 复核确认共同过滤错误：HP 入口把 `Creature` 尝试转换为没有继承关系的 `Player`，因此合法事件在读取 HP 前即被丢弃；本样本不能单独裁决各 hook 是否被调用。
- 生命周期：historical；runtime 加载 PASS、玩家恢复覆盖 FAIL。

## 0.12.0

- 保留 0.11.0 的 11 个观察目标，只修正玩家根实体过滤。
- 移除 `Creature.TryCast<Player>()`；改用 `creature.OwnerPlayerIncludeMaster.OwnerCreature.EntityID == creature.EntityID`。该关系沿用已验证的玩家归属链，并以根实体 ID 同一性排除玩家召唤物。
- SHA-256：`22BDF20B51BFB777D5A63FFF14502F0E8ED65C815568FE014E2088A6D9C8FA6B`。
- 大小：`26,624` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 回读确认版本 `0.12.0`、11 个 patch 类型、入口调用新的根实体过滤，过滤体调用 `OwnerPlayerIncludeMaster`、`OwnerCreature` 与两侧 `EntityID`，程序集不再包含 `TryCast<Player>` 调用。
- 已在游戏与工具箱均未运行时部署并冻结为 `LC2DamageProbe-0.12.0-22BDF20B51BF.dll`；源、冻结副本和游戏目录三方哈希一致。
- 自然启动时 11 个观察目标全部加载，焦点日志零错误。香蕉数量截图 `10→4` 与 6 次外层调用一致；每根请求 `7`，外层有效恢复依次为 `7/7/7/7/3.7012024/0`，合计 `31.7012024`，精确闭合 `108.2988→140`。
- 每个 `hero_runtime depth=0` 香蕉事件都有一个 `creature_runtime depth=1` 子事件，parent operation 精确对应；正式聚合只取外层。来源统一为 `ExhaustProps#Banana_0`。详见 `probe_0_12_banana_heal_pass_20260827/README.zh-CN.md`。
- 后续灵药截图区间的 11 个 `EatFood` 外层事件合计有效恢复 `75.687134`，精确闭合 `64.31287→140`；`FullFoodEnergyOrRecoverHp` 同时获得 3 个有效恢复和 1 个满血 `result=false` 正控。
- 魂石来源 `Gem#A_015_2` 在最大 HP 142 的低血片段中产生 30 个有效 tick、合计约 `30`；同片段另有红血恢复约 `6.629997` 与清场恢复 `0.7804966`，三者分列后闭合 `12.894005→50.304497`。最大 HP 140、HP `49.000004` 时另有 13 个魂石请求全部有效恢复 `0`，闭合 35% 阈值。详见 `probe_0_12_alchemy_self_heal_pass_20260827/README.zh-CN.md`。
- 生命周期：当前观察探针；runtime、玩家根过滤、香蕉、炼金灵药、魂石自愈、有效恢复、溢出/阈值截断、满血零恢复、来源分流与嵌套去重均 PASS。死亡/复活及短期诅咒等直接 HP 生命周期仍待独立正控。

## 0.8.0

- 在 0.7.0 的元素字段上增加 `defender_is_boss` 与 `defender_is_elite`。
- 标志直接读取 `Monster.RuntimeData.IsBoss/IsElite`；非 Monster 或读取失败输出 `null`。
- 目的：用一次 Boss 实战同时验证随机元素身份、Boss 目标筛选、抗性/减免后的实际伤害和官方“对首领伤害”；不修改参数、返回值、伤害、HP、结算或网络状态。
- SHA-256：`9F05C42F08AF4100877FB3186E1E67FD67B5636CD28D4333E213A58F9F4E8841`。
- 大小：`20,480` 字节。
- 使用隔离的 .NET SDK `6.0.428` 标准 Release 构建，`0` 警告、`0` 错误；Mono.Cecil 回读确认版本、两个元素检查调用及 `IsBoss/IsElite` getter 均存在。
- 首次部署门因 PowerShell 比较表达式缺少空格而在复制前停止；旧 0.7.0 游戏目录哈希保持不变。修正脚本后完整静态门通过。
- 已在游戏未运行时部署并冻结为 `LC2DamageProbe-0.8.0-9F05C42F08AF.dll`；源、冻结副本和游戏目录三方哈希一致。
- 生命周期：当前部署候选；尚未自然启动，不能称为 runtime PASS。
