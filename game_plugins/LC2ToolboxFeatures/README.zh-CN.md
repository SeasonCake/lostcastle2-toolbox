# 队伍状态与配装助手

本项目自有实现，版本 1.9.0，作者加菲_barista，沿用仓库 MIT 许可证。社区测试模块提供了功能方向参考，没有复制或打包其反作弊、播报等实现。LC2 增强计划是独立的第三方条目，继续显示原作者。

安装路径为 `BepInEx/plugins/LC2ToolboxFeatures/LC2ToolboxFeatures.dll`，GUID `cn.zidus.lc2.toolbox.features`。由 BepInEx IL2CPP 加载，使用组件低频读取，不安装战斗 Harmony Hook。队伍状态默认关闭；配装助手默认可查看，修改必须由用户手动确认，并在本地角色和营地就绪时请求。

本机当前状态位于 `BepInEx/config/LC2Toolbox/`：`settings.json`、覆盖刷新的 `snapshot.json`、`request.json`、`result.json`；内部目录加载检查保存在 `catalog-state.json`。队伍昵称和背包属于该功能当前数据，不写入战斗桥接的匿名事件。没有联网上传或对局历史库。

快照绑定游戏 PID、捕获时间和唯一玩家槽位；未同步的队友资源使用空值。工具箱不把未知值呈现为零。目录只显示当前游戏数据，已有灵魂石按解锁的刻印槽形状筛选，保留搜索输入。

请求只接受装备、附魔与已有灵魂石三类操作，绑定本次进程、随机请求 ID 和 15 秒有效期。游戏侧再次检查本地角色、营地、启用状态、所有权与槽位条件；执行后等游戏回读确认，超时不自动重复。角色或功能状态变化时停止待确认请求。

使用本地 .NET 6 SDK 编译；`GameDir` 指向当前实际游戏 BepInEx/interop 目录。编译通过与实际角色行为分别验证，不能用单一成功请求推断所有装备、属性或联机组合。

```powershell
dotnet build game_plugins/LC2ToolboxFeatures/LC2ToolboxFeatures.csproj -c Release "-p:GameDir=C:/path/to/Lost Castle 2"
```
