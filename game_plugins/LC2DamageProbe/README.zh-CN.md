# LC2 Damage Probe

这是只用于确认《失落城堡 2》当前版本伤害语义的临时 BepInEx 6 IL2CPP 探针。

- 只对游戏已有的伤害累计处理器、房间起止方法和 `BeHitExecutor_Creature.DamageProcess` 添加观察 patch。
- 不修改参数、返回值、伤害、存档或网络状态。
- 不记录昵称、平台 ID、Steam ID 或网络账号标识。
- 日志事件最多 5000 条，超过后停止输出。
- `0.2.0` 增加命中后 HP、最大 HP、召唤标记、Master 与 OwnerPlayer 实体 ID。
- `0.3.0` 将 HP 观察点下移到实际扣血的 `DamageProcess`，额外输出可按 hit ID 关联的 `hp_snapshot`，用于取得命中前/后 HP 并证伪过量伤害；仍不记录昵称或平台账号。
- `0.4.0` 为嵌套 `DamageProcess` 增加 `parent_hit_id` 与 `depth`，避免 NPC/技能外层快照再次包含内层子伤害。
- `0.5.0` 将浮点日志从三位小数改为往返精度，避免逐击取整在整数边界因日志量化产生 `1` 点误差。
- `0.6.0` 增加 `mOriFinalDamage` 与 `mFinalDamage_Clamp` 观察字段，用于验证官方承伤是否采用减伤前原始伤害；不增加 hook，不改变游戏状态。
- `0.7.0` 调用游戏已有的只读 `CheckDamageMainAttrType` / `CheckDamageAttrType`，输出 `main_attrs` 与 `attrs`，用于区分火、冰、毒、电等最终元素身份；不增加 hook。
- `0.8.0` 在 0.7.0 上增加目标怪物 `IsBoss` / `IsElite` 只读标记，用于把总伤害与“对首领伤害”按同一事件公式分流；不增加 hook。
- `0.9.0` 只对玩家的 `CreatureRuntimeData.ChangeCurrentHp` 增加前后观察，输出请求变化量、有效 HP 变化、有效治疗、MaxHP 和来源；用于排除溢出治疗并捕获绕过伤害事件的直接 HP 变化。
- `0.10.0` 补充玩家 `SetCurHP` 底层写入与 `FullFoodEnergyOrRecoverHp` 进食入口；三条 HP 路径统一输出 operation、parent 与 depth，聚合时只累计 `depth=0` 的有效 HP 上升，避免高低层嵌套重复。
- `0.11.0` 补充 `HeroRuntimeData.ChangeCurrentHp` 覆盖方法，并在 `hp_change` 中标记 `hero_runtime` / `creature_runtime`；用于修复基类 patch 未覆盖玩家实际 HP 路径的问题，继续沿用 operation/depth 去重。
- `0.12.0` 修正玩家过滤：`Creature` 不能转换成无继承关系的 `Player`，改以 `OwnerPlayerIncludeMaster.OwnerCreature` 与当前实体 ID 同一性确认玩家根实体，同时排除召唤物。
- 观察完成后应从 `BepInEx/plugins` 移除，不作为最终 HUD 组件发布。

构建：

```powershell
$env:LC2_GAME_DIR = "D:\SteamLibrary\steamapps\common\Lost Castle 2"
dotnet build .\LC2DamageProbe.csproj -c Release
```

探针输出使用 `[LC2DAMAGE]` 前缀，写入游戏根目录的 `BepInEx/LogOutput.log`。
