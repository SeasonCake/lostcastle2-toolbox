# LC2 Combat Bridge

这是工具箱战斗统计的只读 BepInEx 6 IL2CPP 本地桥接插件。

- 只观察已验证的官方造成/承受伤害、有效 HP 恢复、房间生命周期和结算 checkpoint。
- 不修改游戏参数、返回值、存档、网络状态或战斗逻辑。
- 事件仅通过本机命名管道 `LostCastle2Toolbox.Combat.v2` 发送，不写战斗事件文件。
- 不采集昵称、Steam ID、平台账号、网络地址或聊天内容；实体编号仅作为本轮进程内的临时命中关联值。
- 队列、单行和事件字段均有上限。丢失快照、转换失败或队列溢出会将本轮标为错误，不继续显示伪实时统计。
- 当前 `0.3.0` 候选覆盖已有样本闭合的伤害和 HP 恢复；技能法力消耗改用官方 `OnUseMana` 事件，自动回蓝观察 `UpdateMp` 的有效增量，开局和换房位置跟随实际关卡生命周期。法力修复仍需真实游戏复测，护盾及多人主客机权威性仍待独立取样。

构建需要 .NET 6 SDK、BepInEx 6 和当前游戏生成的 interop 程序集：

```powershell
dotnet build .\LC2CombatBridge.csproj -c Release -p:GameDir="<游戏目录>"
```

本地测试前，将生成的 `LC2CombatBridge.dll` 放入 `<游戏目录>\BepInEx\plugins\LC2CombatBridge\`。部署、游戏实测和发布是独立阶段；仅构建源码不会修改游戏目录。
