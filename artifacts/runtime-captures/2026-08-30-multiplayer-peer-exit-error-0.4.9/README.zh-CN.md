# Bridge 0.4.9 队友退出后异常冻结证据

- 记录时间：2026-08-30 20:31 +08:00。
- 用户条件：四人长局中一名队友中途退出；本局完整打完，但游戏结算画面卡住，无法取得官方个人结算数。
- 生命周期：`OWNER/PERSONAL DISPLAY POSITIVE / PEER-EXIT ERROR INCONCLUSIVE / RESTART RECOVERY R-PASS`。
- Bridge：0.4.9，51,712 B / `18228F2E5EB91B22AFD6AE6F8F97B968F4734B99794E4BD45FEC8BFFB76E8161`。
- 冻结 HUD：95,261 B / `BFD53402A30454A680A5ECBBD261BE6D19365855BB4736D281FA0F214C92CDFC`。
- 冻结日志：4,092,372 B / `F20C6298911F46F2A0D51007352B4B9F0FE27FC1E75BAC4B971DB4F6A4C2A6BB`。
- 重启恢复日志：9,264 B / `869725BB91675BB0C9336A00D7B3006225E8C7C9621091C9E379554C84984584`。
- 冻结时进程：桌面 1.6.2 PID 24260；游戏 PID 22700；没有部署或重启。

## 归属正控

异常画面显示：

- 自己：`788,666 / Boss 142,444`；
- 队友 1：`244,744 / Boss 66,436`；
- 队友 2：`451,973 / Boss 98,561`；
- 队友 3：`103,788 / Boss 16,826`。

四人伤害合计 `1,589,171`，Boss 合计 `324,267`；队友占比 `15%+28%+7%=50%`，自己约为其余 50%。画面没有“未归属”提示，个人主卡也不再显示队伍合计。因此 0.4.9 的通用 owner 链与个人/队伍 UI 在异常发生前得到真实多人正控；该样本仍缺官方结算卡，不能裁决个人 `788,666/142,444` 是否与游戏最终卡精确相等。

## 异常边界

- HUD 状态为红色“异常”，并保留退出前的三张队友卡；可能是 fail-closed 后画面冻结，也可能是 roster 离队事件本身触发 fault。
- 日志有 11,072 条 MP 标记、4,762 条 HP 标记、131 条 TAKEN，但 `[LC2CB-OWNER]` 只有 session-start 零值汇总；`RoomBattleData_RoomEnd`/round-end owner 汇总没有出现。
- BepInEx 日志没有 Bridge warning/error；现有 `CombatPipeServer.FailSession` 与队列 overflow 路径不会把 detail code 写入 BepInEx 日志，桌面界面也只显示“异常”。因此本快照不能唯一确定是 `queue_overflow`、schema/sequence、damage conversion、snapshot mismatch 或其他 fault。
- 0.1 级法力恢复观察数量很大，但平均/峰值事件速率未被冻结，不能仅凭总行数就认定队列溢出。队友退出与异常有时间相关性，但尚不等于根因。

## 下一步

作者重新启动同一 1.6.2/0.4.9 后，HUD 恢复正常。恢复日志明确重新加载 Bridge 0.4.9、命名管道 client connected，并进入营地 round-start；没有新的 Bridge error。这排除了安装损坏、永久配置故障和跨进程持续异常，确认旧“异常”是单局/单连接 fail-closed 状态。

仍需在以后自然再次出现时取得精确 fault code；在此之前不改 owner 算法、不扩大队列，也不把队友退出写成已确认根因。下一次多人只需观察离队后 roster 是否收缩、状态是否保持实时；无需为旧局重复找结算卡。
