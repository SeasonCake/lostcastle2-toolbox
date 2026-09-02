# Bridge 0.4.8 候选与 0.4.7 回滚

- 冻结时间：2026-08-30 16:24 +08:00；部署完成时间：16:25 +08:00。
- 生命周期：`SOURCE/BUILD PASS / DEPLOY PASS / TEST-BOX SELF-TEST PASS / REAL SHORT EXIT NOT RUN`。
- 候选 `LC2CombatBridge.dll`：49,152 B，SHA-256 `7740BA3E30CD8C8B73F8BFDF221C3384CB2D64F940699A6974556E989896CE55`。
- 调试符号 `LC2CombatBridge.pdb`：21,864 B，SHA-256 `68D325D1033E53B813F9620CA430D3D28EA3EB9163625B0C8510B6D8B461963D`。
- 回滚 `LC2CombatBridge.0.4.7.rollback.dll`：48,640 B，SHA-256 `A917E813DC66D1A2737138905DC324CDF9939C1A5A119556D3442F3ACBC18CA7`。

## 候选内容与静态门

- 0.4.7 已闭合官方承伤 `121` 与实际 HP 变化/局内回复 `119.1097946` 的双口径；0.4.8 不修改该聚合公式。
- 新增第 15 个 Harmony target：`PlayerManager.OnGameRoundEndPreLoadCamp()` prefix。在游戏自身 `GameRoundEndBackPreLoadCamp` 生命周期进入时关闭旧活动地图窗口；既有 RoundStart prefix 仅作末端兜底。
- HP 诊断新增 128 字符有界 `changeSourceStr` token；没有按请求值、满血形态、Boss、装备或道具名特判。
- `py -3 -m unittest tests.test_combat_bridge_source -v`：12 项 PASS。
- `py -3 -m unittest discover -s tests -p "test_*.py" -q`：168 项 PASS。
- 隔离 SDK 6.0.428 Release 构建：0 warning / 0 error。
- Mono.Cecil 回读：插件版本 0.4.8、15 target、预加载 prefix、RoundStart prefix/postfix 与 HP source 诊断均存在。

## 部署回执

- 候选冻结时游戏与测试盒仍在运行，故未部署。作者关闭后，两次按 exact name + `ExecutablePath` 独立观察均为 0；同名未知路径和近似路径也为 0。
- 部署前游戏目录与测试盒内置 Bridge 均回读为 0.4.7：48,640 B / `A917E813…18CA7`。
- 游戏目录 DLL/PDB、测试盒内置 DLL 已显式替换；游戏 DLL、测试盒 DLL 与冻结候选三者逐字节回读均为 49,152 B / `7740BA3E…6CE55`，游戏 PDB 为 21,864 B / `68D325D1…1963D`。
- 测试盒 manifest 已更新为 `LC2CombatBridge 0.4.8-test`，桥接大小与哈希同上；`失落城堡2工具箱.exe --self-test` 使用隐藏等待进程执行，退出码 0。
- 16:25:41 部署后再次观察，游戏与测试盒进程均为 0。
- 下一实测只需一次缺血短局退出：确认 `round_end_preload_camp` 先于补满，补满事件 `in_map=False` 且 HUD 回复不增加；同时保留一次局内正向恢复作为负控。
