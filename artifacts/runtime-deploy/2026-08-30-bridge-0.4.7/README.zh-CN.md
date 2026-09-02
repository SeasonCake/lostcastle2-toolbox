# LC2 Combat Bridge 0.4.7 测试候选

- 生命周期：`SOURCE/BUILD/STATIC/DEPLOY PASS / REAL GAME NOT RUN`。
- DLL：48,640 B，SHA-256 `A917E813DC66D1A2737138905DC324CDF9939C1A5A119556D3442F3ACBC18CA7`。
- PDB：21,760 B，SHA-256 `D4BC007E54591F7A29EA2F146E44BDD93CC3EE1D7BC10283963AAA1F39445D29`。
- 回滚 0.4.6：47,616 B，SHA-256 `7DFF32538C1D40015912D0D6C07A6EDF11A9D4E1E571EEEAF496ECD1AF5C98B4`。
- 构建：隔离 .NET SDK 6.0.428，Release，`0 warning / 0 error`；当前游戏 interop 只读作为编译引用。
- Python：聚焦 11 项 PASS；全量 167 项 PASS。
- 编译回读：插件版本 `0.4.7`；RoundStart 同一 Harmony 目标同时包含 `Prefix→PrepareRoundTransition` 与 `Postfix→BeginRound`；Harmony 目标类型仍为 14；taken/HP 新诊断字符串均存在。
- 行为变化：RoundStart prefix 在游戏执行回营/轮次内部补满前关闭旧活动地图窗口；HP/MP 的营地补满不再聚合。postfix 继续完成 0.4.6 原初始化，不改变下一地图进入逻辑。
- 诊断变化：既有本地玩家 taken 路径记录 `original/real/hp_before/applied/settlement/mitigated/depth`；既有 HP 观察同时记录正负有效变化、`in_map` 与 `inside_damage`。不新增 Hook、玩家身份字段或道具特判。
- 部署门：`LostCastle2.exe` 与目标测试盒子进程按 exact `ExecutablePath` 连续两次为 0；同名其他路径与未知路径均为 0。
- 游戏目录、候选目录和测试盒子内置 Bridge 三者回读均为上述 DLL 哈希。
- 测试盒子仍沿用目录 `<desktop>/失落城堡2工具箱 1.6.0-Bridge0.4.6测试版`，但内部 manifest 已明确更新为 `LC2CombatBridge 0.4.7-test`、48,640 B 与上述哈希；EXE `--self-test` 退出码 0。
- 下一真实正控：普通新局只受击一次，观察 taken 诊断；随后退出回营，恢复数字不得因自动补满突增。真实游戏、回营和受击字段尚未运行，不得发布。
