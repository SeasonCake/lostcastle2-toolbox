# v1.7.2 单人终局 + MOD 更新 r4 诊断候选回执

> lifecycle: `diagnostic-candidate-built / desktop-copy-frozen / real-game-mod-load-not-run / distribution-not-built`
>
> recorded: `2026-09-03`

## 候选身份

- 项目包：`<repo>/package/失落城堡2工具箱1.7.2-诊断候选-单人终局+MOD更新-r4`。
- 桌面测试副本：`<desktop>/失落城堡2工具箱1.7.2-诊断候选-单人终局+MOD更新-r4`。
- 两份目录均为 1,770 个文件、167,018,274 B；规范化逐文件树摘要均为 `502B453F86FD4F8F012AB436D87E17BA1680B974E0FA37F003302405130998A0`，差异 0。
- EXE：6,508,585 B，SHA-256 `5231F6099D2597ACF08DBB9DCB53D849124C0E1B88C0C64C13C525CBC8046F86`。
- Bridge 1.7.2 Diagnostic：99,328 B，SHA-256 `BC8FFAD827B454D46D0015F237444CED13580B99696B71819E3941F5E71948B2`；PDB/本机路径命中 0。

树摘要算法按相对 POSIX 路径不区分大小写排序，并依次散列 `相对路径\0大小\0文件SHA-256\n` 的 UTF-8 字节。

## MOD 刷新

- 当前社区目录为 60 条、61 个最小功能文件、3,665,869 B；包内 61 个登记文件逐项大小/SHA-256 差异 0。
- 新增雷击与轰雷强化 1.0.1；更新增强计划 5.0.0、怪物宝藏 11.7、召唤行刑者 2.6、雷神之锤召唤愤怒雷精灵 1.5.1、啵啵法杖 1.9.6。
- 60 个 DLL 均可读取 BepInPlugin 元数据，GUID 重复 0。新增/变更 DLL 的程序集引用均属于当前游戏 interop、BepInEx 或标准运行时，未发现额外 MOD DLL 依赖。
- 包形隔离游戏中 60/60 条逐项安装、状态识别与卸载通过；卸载后遗留文件 0。篡改、路径穿越与同名提供冲突负控继续拒绝。
- 来源压缩包中的说明、联系方式、重复 core、Doorstop、cache、interop 与生成配置没有进入社区功能载荷。

## 产品与包形门

- `build.ps1 -BuildProfile Diagnostic` 内置产品门：322 tests PASS；源码 self-test PASS。
- Bridge Release 编译：0 warning / 0 error；诊断档身份检查 PASS。
- 无 BepInEx 隔离游戏：首次初始化 ready、重复初始化 ready、社区 MOD 自动启用 false、冲突 core 写前阻断 true、控制台关闭。
- 包内 EXE `--self-test` exit 0；包内 60/60 MOD 安装/卸载再次通过。
- 包内 `.cfg`、`.log`、`.partial`、PDB、导出目录与运行时诊断 JSON 均为 0。
- 对维护者用户名、工作区绝对路径、联系方式、实测截图名和本次诊断目录标识的全包字节扫描均为 0 命中。

## 边界

- 真实游戏加载这些新增/更新 MOD、功能效果与互相组合尚未执行，因此本回执只签静态身份、依赖面、安装链和包形，不外推实战功能兼容。
- 单人自然结算对 `SOLO-FINAL-01` 修复的真实正控仍未执行。
- Distribution、commit、push、tag、Release 与群分享均未执行。
