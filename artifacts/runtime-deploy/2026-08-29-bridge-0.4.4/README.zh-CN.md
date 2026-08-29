# Bridge 0.4.4 魔晶石同操作回蓝候选

生命周期：`LOCAL DEPLOYED CANDIDATE / PACKAGE VERIFIED / REAL RETEST PENDING`

| 对象 | 大小 | SHA-256 |
| --- | ---: | --- |
| 0.4.3 exact rollback | 46,592 B | `2837F6C485F691BB743CEAF3EB5EBE2BB5FA1D66A19E1FB2D4B87F029CF562A3` |
| 0.4.4 candidate / 当前游戏目录 | 46,592 B | `CF2237678432A6131A06B4974FA44B677B4FFED9537FFF6F02A5096AA5CE3966` |

- 部署前后 `LostCastle2.exe` 均以 exact name + `ExecutablePath` 连续两次确认 0；未知字段为 0。
- .NET 6 构建为 0 warnings / 0 errors；Python 全量 149/149 PASS。
- 0.4.4 只改变既有低层 MP 根操作的恢复对账，不增加 Harmony Hook；现有 14 个 Hook 保持。
- 包内运行时首次/重复安装、控制台关闭、社区 MOD 不自动启用和不同核心写前阻断均 PASS。
- 桌面 1.5.13 EXE：`6,237,686` B / SHA-256
  `8DFD18F26FEAA8FD2A694701E0BAEDB6C87EFFE6794C5E0BF39D76EC7CD59138`；项目包与桌面包
  都是 1,757 文件 / `166,217,064` B，逐文件零差异、0 config 文件。
- 冻结 EXE 的 100% 主战斗页和 200% 四人 HUD 几何/像素验收均 `VERIFIED`。

同目录二进制被 `.gitignore` 排除；本 README 可提交并提供本机精确回滚定位。
