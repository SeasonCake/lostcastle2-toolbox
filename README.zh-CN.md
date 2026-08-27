# 失落城堡 2 工具箱

[English](README.md)

一个非官方、开源的 Windows《失落城堡 2》辅助工具箱。

当前仓库包含：

- 可自定义的键盘/鼠标按键悬浮窗；
- 默认关闭、仅在游戏前台运行并带紧急停止的按键宏；
- 只读战斗语义研究探针；
- 面向伤害、治疗、法力、状态效果和护盾的版本化事件合同与可回放聚合器；
- 带作者、版本、哈希和风险说明的第三方 MOD/修改器受管入口。

应用现在从计算器风格的综合主窗口启动，由它打开和管理按键显示、按键宏与战斗统计。游戏中使用紧凑战斗 HUD，完整拆分只放在主窗口；键盘模块继续保留柔雾半镂空外观。v2 事件层把“游戏观察、数据聚合、UI 展示”分开：以后发现新的回血道具、魂石、召唤物击杀触发或法力效果，通常只需补充来源注册表和样本，不需要为每件道具写一套 UI 代码。

这是面向免费开源维护的小工具，不按商业平台建设：默认不引入账号、激活、云同步、遥测、远程服务或插件市场。主窗口与战斗 HUD 读取同一份战斗快照，避免重复计算和双份状态机。

## 当前进度

| 模块 | 状态 |
| --- | --- |
| 按键悬浮窗 | 可用 |
| 前台限定宏 | 可用，默认全部停用 |
| 造成伤害、承伤与生命恢复口径 | 已在记录的游戏版本完成运行时验证 |
| 战斗事件 v2 与回放聚合 | 已实现并有行为测试 |
| 法力与护盾观察桥 | 合同已预留；运行时 Hook 待验证 |
| 综合主窗口与外部战斗 HUD | 本地管道与桥接候选已实现；待游戏实测 |
| MOD 管理 | 已登记 1 个第三方独立修改器；用户提供原文件并校验后配置 |

研究结论只适用于计划文档记录的游戏构建。游戏更新后，Hook 兼容性与数据口径都需要重新验证。

## 使用工具箱和按键悬浮窗

- 启动 `keyview.py`，或使用自行构建的 `失落城堡2按键显示器.exe`，首先进入综合主窗口。
- 从“按键显示”页面打开悬浮窗或设置；悬浮窗支持最多 20 个键、配色、缩放和背景透明度。
- `F8` 显示/隐藏，`F9` 开关鼠标穿透，`F11` 开关纯净模式。
- 点击“启动游戏”会优先从 Steam 安装信息定位游戏；找不到时可手动选择 `LostCastle2.exe`。
- 设置保存在程序目录的 `config/settings.json`；该目录不会提交到 Git。

## 按键宏

- 从右键菜单或显示设置打开“宏设置”。
- 支持按一次、按住循环、开关循环；示例方案默认全部停用。
- 宏只在 `LostCastle2.exe` 为前台时发送输入；切出游戏、游戏退出、修改配置或退出工具会停止并释放按键。
- `Ctrl + Shift + F12` 紧急停止全部宏。

## MOD 管理

- “MOD 管理”页当前登记“灵魂石修改器 1.2”，作者为“恨你不见”。作者和固定文件身份见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
- 该文件是未签名、使用 Frida IL2CPP 注入的独立修改器，不是本项目的只读 BepInEx 战斗桥。
- 由于未找到明确的公开再分发授权，仓库和构建包不捆绑其 72 MB 二进制。首次点击“一键配置”时选择作者原文件；只有大小和完整 SHA-256 都匹配才会保存盒子受管副本。
- “删除副本”只删除 `config/managed_mods` 中由盒子创建的精确文件，不会删除下载目录原件或游戏目录文件。
- 启动第三方修改器必须再次确认；其注入、资源替换和成就写入行为不受本项目只读边界保证。

## 开发与测试

需要 Windows、Python 3.13，以及 `requirements-dev.txt` 中的依赖：

```powershell
py -3 -m pip install -r requirements-dev.txt
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 keyview.py --self-test
```

从源码运行：

```powershell
py -3 keyview.py
```

无需移动鼠标即可打开指定页面或 HUD 做界面检查：

```powershell
py -3 keyview.py --demo --show-page combat --show-combat-hud
py -3 keyview.py --demo-large-values --show-page combat --window-size 780x560 --tk-scaling 1.5
py -3 keyview.py --demo-large-values --show-page combat --show-combat-hud --demo-scenario CastleBridge --demo-room-index 100
```

构建 Windows 目录包：

```powershell
.\build.ps1
```

实时桥接候选见 [`game_plugins/LC2CombatBridge/README.zh-CN.md`](game_plugins/LC2CombatBridge/README.zh-CN.md)；临时研究探针见 [`game_plugins/LC2DamageProbe/README.zh-CN.md`](game_plugins/LC2DamageProbe/README.zh-CN.md)。桥接候选尚未部署或完成游戏运行时验证。

## 数据与安全边界

- 按键悬浮窗只查询 Windows 按键状态，不向游戏注入代码。
- 宏只发送用户显式配置的输入，不应包含无人值守玩法或规避游戏限制的功能。
- 研究探针只观察已经结算的战斗状态，不修改伤害、掉落、存档或网络状态。
- 第三方工具不继承上述只读保证；盒子只做固定哈希校验、受管复制和显式启动。
- 仓库不会提交游戏 DLL、生成的 interop、日志、截图、本机配置或打包产物。

架构见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，协作规则见 [`CONTRIBUTING.md`](CONTRIBUTING.md)，安全问题见 [`SECURITY.md`](SECURITY.md)。

## 许可与声明

本项目源码使用 [MIT License](LICENSE)。游戏代码、美术资源、名称、商标和第三方工具不在本许可范围内。

本项目是非官方玩家项目，与 Hunter Studio、Another Indie 或游戏发行方无从属或背书关系。使用者需自行拥有合法游戏副本。
