失落城堡 2 工具箱 · HUD / MOD 运行环境

盒子在首次启动游戏或首次安装 DLL MOD 时，会先询问是否一键初始化。

初始化只会安装：
- 已验证的 BepInEx 6.0.0-be.785 运行时；
- LC2 Combat Bridge 1.7.4（只读采集当前局战斗数值；Mini HUD显示“实时”，详细页提示“实时估算/结算可能校正”；结算数据完整时以游戏最终的造成伤害、Boss伤害和承伤校正显示）。

Bridge只通过本机pipe把数值提供给工具箱，不修改游戏对象。正式分享版不保存逐事件对局明细，也不提供对局导出。

不会自动安装或启用随包社区 MOD；需要的 MOD 由你在工具箱列表中自行选择安装。
BepInEx 控制台默认关闭；低频启动、连接与错误支持信息仍写入游戏目录的 BepInEx\LogOutput.log，该文件在下次启动游戏时重新开始。
检测到不同版本的现有 BepInEx 核心时，盒子会停止，不会盲目覆盖。

BepInEx 项目： https://github.com/BepInEx/BepInEx
本包对应源码提交： 6abdba47eeebe08552282e7a58ef0f4a9ab60b62
许可证见同目录 BepInEx-LICENSE.txt。
