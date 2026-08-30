# LC2 Combat Bridge

这是工具箱战斗统计的只读 BepInEx 6 IL2CPP 本地桥接插件。

- 只观察已验证的官方造成/承受伤害、有效 HP 恢复、房间生命周期和结算 checkpoint。
- 不修改游戏参数、返回值、存档、网络状态或战斗逻辑。
- 事件仅通过本机命名管道 `LostCastle2Toolbox.Combat.v2` 发送，不写战斗事件文件。
- 不采集昵称、Steam ID、平台账号、网络地址或聊天内容；实体编号仅作为本轮进程内的临时命中关联值。
- 队列、单行和事件字段均有上限。单个快照、转换、stack 或 checkpoint 失败会把本轮标为“实时 · 有事件跳过”并继续；只有队列溢出仍 fail closed，日志明确写出 code。
- 已安装/已发布的 `0.4.5` 保留由实战闭合的伤害、承伤、HP 恢复、房间位置与 14 个既有 Hook。玩家承伤与 HP/MP 资源观察只接收本地玩家根实体，队友只参与匿名伤害归属；20%/40%/65% 官方生命锁定产生的非受击负 HP 变化使用既有 `resource_operation=loss`，不进入“受击承伤”或“回复”。65% 锁血已完成 `49/140` 实机正控。法力按原始浮点变化累计并只在 UI 边界取整；恢复同时采用根操作对账和连续观测基线，并扣除同操作官方已覆盖量，覆盖官方恢复、闪避回蓝、同操作先扣后回以及两次技能之间的自然回蓝。普通太刀实测已得到法力消耗/恢复 `762/763`，HUD 保持实时。
- 已实测的 `0.4.6` 不增加 Hook 或道具特判。它修正零请求/零净变化的 MP 观察把已经识别的 fallback 恢复提前丢弃的问题；普通回蓝、怀表回满、魔晶石容量增加与分解负控已闭合。HP 仍按实际正向变化累计。
- `0.4.7` 实战确认 RoundStart prefix 仍晚于回营补满；官方承伤 `121` 与实际 HP 变化/恢复 `119` 已闭合为逐击入整与真实浮点变化的双口径，不改聚合公式。
- `0.4.8` 增加第 15 个、语义明确的 `PlayerManager.OnGameRoundEndPreLoadCamp` Hook，在游戏的 `GameRoundEndBackPreLoadCamp` 生命周期进入时关闭旧活动地图窗口；既有 RoundStart prefix 仅保留为末端兜底。HP 诊断同时记录有界 `changeSourceStr`，不按请求值、满血形态、Boss、宝藏或道具特判。缺血短局实测中，局内有效回复 `68.9060974` 显示 `69`，回城补满 `91.1367874` 明确为 `in_map=False` 且未进入统计，判 `R-PASS`。
- `0.4.9` 来自首次三人联机反例：0.4.8 的顶部把队伍 `819,706` 显示成个人总伤害，而游戏个人结算为 `576,627`；同时只有 `235,775` 归到自己、`447,459` 未归属。0.4.9 以通用有界关系遍历 `mAtkerInHierarchy / OwnerEntityInHierarchy / OwnerEntity / StandMaster / Creature.Master`，补回技能、投射物、召唤物和根玩家关系，并按 local/remote/unattributed 输出汇总诊断；不按角色、武器、召唤物名或数值特判。
- `0.4.9` 两个真实长局都在中途进入红色“异常”并冻结，其中第二局四人从头到尾无人离开，排除了离队必要性。0.4.10 将单个 snapshot/conversion/stack/checkpoint 问题改为显式 recoverable：日志写出 code、HUD 显示“实时 · 有事件跳过”，其余事件继续累计；每种 code 每局只通知一次。真正的 queue overflow 仍 fail closed，并明确记录致命原因，禁止靠扩大队列掩盖。
- 0.4.10 后续完整四人局在进入 CrystalMountain 第 1 区时先记录 `damage_snapshot_overflow`，紧接 `damage_snapshot_missing`；旧实现达到 8,192 时整表 `Clear()`，因此一次溢出会连锁丢失尚未消费的命中。0.4.11 改为字典索引配最旧未消费 FIFO，只逐个淘汰最老快照，并在消费、新局和卸载时同步移除。
- 0.4.12 收窄归属关系：优先官方 `mAtkerInHierarchy`，再用瞬时 `mAtker`；只接受 Player/native、OwnerEntity hierarchy 与 `Creature.Master`，不再用 StandMaster 或 EntityID 根做推测。`change_room_end` 每房记录 owner 汇总，避免多人路径只在 session start 留一份诊断。roster、pipe、schema、聚合与 UI 上限统一为 16；合成 16 人高负载、非 1P 本机和五列 HUD 已通过，真实 7–16 人与远端召唤物仍未运行。
- 多人只发送会话内匿名 `player-N`、队伍槽位和本机标记，不发送昵称、Steam ID 或平台账号。插件以 native Player 对象作为仅会话内映射键，避免 `ID/ClientID/TransportID` 在联网加载中变化导致 token 漂移；桌面仍只收到 `player-N`。本机身份严格使用 `PlayerManager.LocalPlayer` 的对象同一性，不把槽位 0 或房主当作自己。工具箱 1.6.2 顶部/HUD 显示个人伤害，队伍合计与未归属另列。真实房主样本已出现不同玩家独立列，但客机、离队重连和召唤物归属仍需复测。

构建需要 .NET 6 SDK、BepInEx 6 和当前游戏生成的 interop 程序集：

```powershell
dotnet build .\LC2CombatBridge.csproj -c Release -p:GameDir="<游戏目录>"
```

本地测试前，将生成的 `LC2CombatBridge.dll` 放入 `<游戏目录>\BepInEx\plugins\LC2CombatBridge\`。部署、游戏实测和发布是独立阶段；仅构建源码不会修改游戏目录。
