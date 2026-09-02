失落城堡 2 工具箱 · HUD / MOD 运行环境

盒子在首次启动游戏或首次安装 DLL MOD 时，会先询问是否一键初始化。

初始化只会安装：
- 已验证的 BepInEx 6.0.0-be.785 运行时；
- LC2 Combat Bridge 1.7.0（Mini HUD局中显示“实时”；详细页说明“实时估算/结算可能校正”；完整SyncEnd逐玩家值显示“官方结算”，可向上或向下校正）。

正式版关闭高频逐事件与终局验收探针日志，不写桌面对局归档；Bridge只通过本机pipe提供当前局数据，不改变显示算法或游戏状态。

不会自动安装或启用随包社区 MOD，也不会安装伤害探针、多人上限或其他调试插件。
BepInEx 控制台默认关闭；低频启动、连接与错误支持信息仍写入游戏目录的 BepInEx\LogOutput.log，该文件在下次启动游戏时重新开始。
检测到不同版本的现有 BepInEx 核心时，盒子会停止，不会盲目覆盖。

BepInEx 项目： https://github.com/BepInEx/BepInEx
本包对应源码提交： 6abdba47eeebe08552282e7a58ef0f4a9ab60b62
许可证见同目录 BepInEx-LICENSE.txt。
