失落城堡2工具箱 public-core · 官方运行环境来源与许可

public-core 不携带旧版从真实游戏目录准备的 307 文件 runtime 快照，也不携带其中的 Unity base libraries。它只携带 BepInEx 官方 build #785 的原始 Windows x64 IL2CPP ZIP（字节不重打包）以及本项目 MIT 许可的 LC2 Combat Bridge。

固定官方输入：

- BepInEx Unity IL2CPP win-x64 6.0.0-be.785+6abdba4
- 官方下载：
  https://builds.bepinex.dev/projects/bepinex_be/785/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.785%2B6abdba4.zip
- 原始 ZIP：34,335,572 B
- SHA-256：2A7CBF74D26ABE4765C3E662DB1721B923BAC39849EBFEF2CA5DC7DE7E2D9B7F
- 对应 BepInEx 源码：
  https://github.com/BepInEx/BepInEx/tree/6abdba47eeebe08552282e7a58ef0f4a9ab60b62
- BepInEx / UnityDoorstop：LGPL-2.1；完整文本见本目录对应 LICENSE 文件。
- UnityDoorstop 4.5.0 源码：
  https://github.com/NeighTools/UnityDoorstop/tree/v4.5.0
- Dobby 1.0.5：Apache-2.0；源码与许可：
  https://github.com/BepInEx/Dobby/tree/v1.0.5
- BepInEx 官方构建使用 .NET runtime 6.0.7；构建来源：
  https://github.com/BepInEx/dotnet-runtime/releases/tag/6.0.7
  https://github.com/BepInEx/dotnet-runtime/tree/e10df43
  .NET runtime 为 MIT，完整 LICENSE、PATENTS 与 THIRD-PARTY-NOTICES 均随本目录提供。

首次运行游戏时，官方 BepInEx 会在用户自己的游戏目录中下载/生成与当前 Unity 版本对应的 base libraries 和 interop。public-core 不把这些本机生成文件打进发行包，也不会上传它们。

工具箱只在用户明确确认、游戏完全关闭时初始化运行环境；不同身份的现有 BepInEx 核心会写前阻断。LC2 Combat Bridge 单独按版本和 SHA-256 安装到其独占插件目录。
