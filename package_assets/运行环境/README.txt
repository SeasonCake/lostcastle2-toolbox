失落城堡 2 工具箱 · HUD / MOD 运行环境

盒子在首次启动游戏或首次安装 DLL MOD 时，会先询问是否一键初始化。

初始化只会安装：
- 已验证的 BepInEx 6.0.0-be.785 运行时；
- LC2 Combat Bridge 0.4.3（战斗 HUD 的只读数据桥）。

不会自动安装或启用随包社区 MOD，也不会安装伤害探针、多人上限或其他调试插件。
BepInEx 控制台默认关闭；必要日志仍写入游戏目录的 BepInEx\LogOutput.log。
检测到不同版本的现有 BepInEx 核心时，盒子会停止，不会盲目覆盖。

BepInEx 项目： https://github.com/BepInEx/BepInEx
本包对应源码提交： 6abdba47eeebe08552282e7a58ef0f4a9ab60b62
许可证见同目录 BepInEx-LICENSE.txt。
