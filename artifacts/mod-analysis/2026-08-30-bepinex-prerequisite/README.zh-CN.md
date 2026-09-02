# “模组前置 BepInEx”静态分析

- 用户文件：`模组前置BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785+6abdba4.zip`。
- 实际定位：`<local-mod-library>`；最初提供的候选路径存在转义差异，已在只读清点时纠正。
- 文件：34,335,572 B / SHA-256 `2A7CBF74D26ABE4765C3E662DB1721B923BAC39849EBFEF2CA5DC7DE7E2D9B7F`。
- ZIP 完整性：7-Zip PASS；228 个文件、解压 75,665,788 B。
- 生命周期：`STATIC IDENTITY PASS / NOT A GAMEPLAY MOD / EXECUTION NOT RUN`。

## 它是什么

这是 BepInEx 6 的 Windows x64 Unity IL2CPP 加载器，不是提供玩法功能的 MOD。顶层 `winhttp.dll` 通过 Unity Doorstop 4.5.0 在游戏启动时进入进程；`doorstop_config.ini` 指向 `BepInEx/core/BepInEx.Unity.IL2CPP.dll`，并使用包内 `dotnet/coreclr.dll` 与托管运行库。BepInEx 随后负责生成/加载 IL2CPP interop，并从 `BepInEx/plugins` 发现真正的插件。

该 ZIP 本身没有 `BepInEx/plugins` 文件、没有游戏功能 DLL、没有用户配置文件。单独把它解压到游戏根目录只会安装 MOD 加载基础设施；玩法变化来自之后放入 plugins 的其他 DLL。

## 与工具箱内置运行时的关系

工具箱当前 `bepinex-runtime.zip` 为 40,402,401 B / `0B617BC439F53E39680444F1EFD84C2B31A96D144D3267EE06EBEA05B59738A8`，307 个文件、解压 87,570,584 B。

- 两包共有 227 个文件；大小和 SHA-256 逐文件全部一致，证明 core、Doorstop、CoreCLR 等基础二进制是同一构建。
- 用户 ZIP 仅多一个 `changelog.txt`，首行标明 commit `6abdba4`。
- 工具箱运行时多 80 个文件：一份受管 `BepInEx/config/BepInEx.cfg`，以及与本机《失落城堡 2》Unity `6000.3.16f1` 匹配的 `BepInEx/unity-libs` 基础库/缓存包。
- 工具箱把 Bridge 作为清单中单独固定哈希的插件安装，不把它混入 BepInEx 基础 ZIP；社区 MOD也默认不自动启用。

## 产品结论

- 不应把这个 ZIP登记成普通社区 MOD：它会写游戏根目录、BepInEx core、Doorstop 和 CoreCLR，生命周期与普通 `BepInEx/plugins/<mod>` 完全不同。
- 工具箱现有“首次初始化运行环境”已经覆盖它的用途，而且提供 Unity 库、默认关闭控制台、不同核心写入前阻断、重复安装幂等和精确卸载边界。
- 若游戏目录已有同一 core，重复手工解压通常没有新增功能；若已有不同 core，不应盲目覆盖。压缩包内容未执行，本记录不评价任意第三方插件兼容性。
