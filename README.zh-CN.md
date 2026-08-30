# 失落城堡 2 工具箱

[English](README.md)

一个非官方、开源的 Windows《失落城堡 2》辅助工具箱。

当前仓库包含：

- 可自定义的键盘/鼠标按键悬浮窗；
- 默认关闭、仅在游戏前台运行并带紧急停止的按键宏；
- 只读战斗语义研究探针；
- 面向伤害、治疗、法力、状态效果和护盾的版本化事件合同与可回放聚合器；
- 带作者与用途说明的第三方 MOD/修改器受管入口。

应用现在从计算器风格的综合主窗口启动，由它打开和管理按键显示、按键宏与战斗统计。游戏中使用紧凑战斗 HUD，完整拆分只放在主窗口；键盘模块继续保留柔雾半镂空外观。v2 事件层把“游戏观察、数据聚合、UI 展示”分开：以后发现新的回血道具、魂石、召唤物击杀触发或法力效果，通常只需补充来源注册表和样本，不需要为每件道具写一套 UI 代码。

这是面向免费开源维护的小工具。主窗口与战斗 HUD 读取同一份战斗快照，避免重复计算和双份状态机。

## 当前进度

| 模块 | 状态 |
| --- | --- |
| 按键悬浮窗 | 可用 |
| 前台限定宏 | 可用，默认全部停用 |
| 造成伤害、承伤与生命恢复口径 | 已在记录的游戏版本完成运行时验证 |
| 战斗事件 v2 与回放聚合 | 已实现并有行为测试 |
| 法力与护盾观察桥 | 法力消耗/恢复已完成运行时验证；护盾仍待独立样本 |
| 综合主窗口与外部战斗 HUD | Bridge 0.4.8 已完成回蓝、官方/实际 HP 双口径与回营补满排除实测；匿名多人归属仍待联机实测 |
| MOD 管理 | v1.6.1 纳管 2 个原有工具与 52 个社区 MOD；支持本地自动识别、面板一键打开与添加 |

研究结论只适用于计划文档记录的游戏构建。游戏更新后，Hook 兼容性与数据口径都需要重新验证。

## 使用工具箱和按键悬浮窗

- 启动 `keyview.py`，或使用自行构建的 `失落城堡2工具箱.exe`，首先进入综合主窗口。
- 从“按键显示”页面打开悬浮窗或设置；默认显示键盘，支持最多 20 个键，也可切换为手柄布局。
- `F8` 显示/隐藏，`F9` 开关鼠标穿透，`F11` 开关纯净模式。
- 点击“启动游戏”会优先从 Steam 安装信息定位游戏；找不到时可手动选择 `LostCastle2.exe`。
- 全新游戏环境首次启动时会明确询问是否一键初始化 HUD / MOD 运行环境；盒子只安装固定身份的 BepInEx 与只读战斗 Bridge，不会默认启用任何社区 MOD，BepInEx 控制台默认关闭。
- “设置”页可调整主窗口尺寸与字体档位，并分别调整按键悬浮窗和战斗 HUD 缩放。
- 主窗口首次启动默认使用宽敞档 `1280×900、115%`，战斗 HUD 默认同时打开；已保存的标准、紧凑或自定义尺寸保持不变。
- 设置保存在程序目录的 `config/settings.json`；该目录不会提交到 Git。

## 按键宏

- 从右键菜单或显示设置打开“宏设置”。
- 支持按一次、按住循环、开关循环；示例方案默认全部停用。
- 宏只在 `LostCastle2.exe` 为前台时发送输入；切出游戏、游戏退出、修改配置或退出工具会停止并释放按键。
- `Ctrl + Shift + F12` 紧急停止全部宏。

## MOD 管理

- v1.6.1 收录“灵魂石修改器 1.2”（作者：恨你不见）、“金币编辑器 1.0”（作者：刺心）与 52 个社区 MOD；实战/资源工具优先，外观类靠后。“纵冰之杖加强 1.16.0”“我不是药神 1.0.0 测试版”和纯视觉“暴击字体改紫色 1.0.0”已进入本版。新收到的海克斯 DLL 与既有 2.7.6 载荷逐字节一致，因此只提升实战排序并补充 F1 冲突说明，不重复收录。
- 灵魂石修改器支持配置、启动和删除盒子副本；金币编辑器随包提供登记 DLL，可一键安装到独占 BepInEx 插件目录，并只卸载自身文件。
- 金币编辑器安装完成后可从 MOD 卡片直接启动游戏；进入游戏后可点击“打开 MOD 面板”或按 `F5`，输入数量并保存，返回主菜单再进入游戏生效。作者与文件信息见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
- 社区目录剔除了旧版重复、测试、未完成、半成品和明确有 bug 的来源；每个条目显示作者、功能和使用方法，作者证据不足时明确标为“社区未署名”。
- 明确带设置/操作界面的 MOD 会登记独立 `panel_hotkey`：未安装时提示先安装，游戏未运行时启动游戏，本次游戏启动后才安装时提示重启，已加载时切回游戏并代按面板键；丢钱等直接执行功能的快捷键不会被误判为面板。
- 用户可把 DLL、ZIP、7Z、RAR 或文件夹放入工具箱旁的“用户MOD”，点击“添加 MOD”静态识别并编辑预览；完整清单、可选 `interaction.panel_hotkey` 与 AI 提示词见包内 `MOD自动添加说明.txt`。
- 普通插件安装到各自独占目录；卸载只移除登记文件，同名 DLL 冲突会阻止重复安装。BepInEx 前置整包和游戏文件覆盖不会按普通 MOD 自动添加。
- 首次安装 DLL MOD 时会复用同一初始化入口；若已有不同身份的 BepInEx 核心，盒子停止并保留原文件，不盲目覆盖。
- 主窗口左下角依次提供 GitHub、[bilibili](https://space.bilibili.com/88048665?) 和“投喂”；“投喂”可悬停查看默认微信赞助码，点击打开微信、支付宝与完整说明。工具箱源于玩家对《失落城堡2》的热爱，想支持加菲或催催更新时可以自愿投喂猫罐头。

## 开发与测试

战斗参数、游戏字段、转换公式、协议/聚合/UI 映射、实测数值基线和已知 Bug 统一维护在 [`docs/LC2_RUNTIME_PARAMETER_DEBUG_INDEX.zh-CN.md`](docs/LC2_RUNTIME_PARAMETER_DEBUG_INDEX.zh-CN.md)。

需要 Windows、Python 3.13，以及 `requirements-dev.txt` 中的依赖：

注意：fresh clone 包含源码、合同与固定 7-Zip 组件，但不包含被 Git 排除的社区 MOD 载荷和 LC2 运行时二进制。运行下面的全量 `unittest`、`keyview.py --self-test` 或打包前，必须先按 `THIRD_PARTY_NOTICES.md`、`assets/community_mod_sources.json` 和运行时清单准备精确本地输入；未准备时只能运行不依赖这些载荷的聚焦测试，不能把缺载荷失败解释为源码回归。

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
py -3 keyview.py --demo-large-values --show-page combat --window-size 1000x720 --tk-scaling 1.5
py -3 keyview.py --demo-large-values --show-page combat --show-combat-hud --demo-scenario CastleBridge --demo-room-index 100
```

构建 Windows 目录包：

```powershell
.\build.ps1
```

仓库包含固定版本的 7-Zip 运行组件及其许可证，clone 后可直接使用源码模式的压缩包识别。其他第三方 EXE、DLL、压缩包及生成的 `third_party/community_mods` 载荷不会提交到 Git。打包前需在本机准备 `THIRD_PARTY_NOTICES.md` 和 `assets/community_mod_catalog.json` 登记的精确输入；`build.ps1` 会核对数量、大小和 SHA-256，缺失或不一致时直接停止。

实时桥接见 [`game_plugins/LC2CombatBridge/README.zh-CN.md`](game_plugins/LC2CombatBridge/README.zh-CN.md)；临时研究探针见 [`game_plugins/LC2DamageProbe/README.zh-CN.md`](game_plugins/LC2DamageProbe/README.zh-CN.md)。Bridge 0.4.5 已闭合普通太刀自然回蓝，0.4.6 闭合零变化 fallback 与容量变化，0.4.7 确认官方承伤121/实际 HP 变化119为双口径，0.4.8 使用游戏自身回营预加载边界排除结算补满。最新短局中局内回复 `68.906097→69`，回城补满 `91.136787` 明确为 `in_map=False`；2P–4P 仍需真实联机实测。

## 数据与安全边界

- 按键悬浮窗只查询 Windows 按键状态，不向游戏注入代码。
- 宏只发送用户显式配置的输入，不应包含无人值守玩法或规避游戏限制的功能。
- 研究探针只观察已经结算的战斗状态，不修改伤害、掉落、存档或网络状态。
- 第三方工具不继承上述只读保证；盒子只对登记版本做固定哈希校验，并执行对应的受管复制、安装、卸载或显式启动。
- 仓库不会提交游戏 DLL、生成的 interop、日志、截图、本机配置或打包产物。

架构见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，协作规则见 [`CONTRIBUTING.md`](CONTRIBUTING.md)，安全问题见 [`SECURITY.md`](SECURITY.md)。

## 许可与声明

本项目源码使用 [MIT License](LICENSE)。游戏代码、美术资源、名称、商标和第三方工具不在本许可范围内。

本项目是非官方玩家项目，与 Hunter Studio、Another Indie 或游戏发行方无从属或背书关系。使用者需自行拥有合法游戏副本。
