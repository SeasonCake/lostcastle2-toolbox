# Bridge 0.4.10 四人完整局：快照溢出与个人误归属

- 记录时间：2026-08-30 23:21 +08:00。
- 条件：四人完整局；第三个 Boss 后一名队友退出，其余玩家继续到完整结算。
- 生命周期：`DEGRADED CONTINUATION R-PASS / SNAPSHOT CAPACITY R-FAIL / PERSONAL ATTRIBUTION R-FAIL / 0.4.11 NOT RUN`。
- Mini UI 空行图：5,182 B / `22C6FB093A75C35DED33A9DF8117D4BB8BFEAC159977A282F6BF706FFB9B7AF5`。
- 第三个 Boss 后黄色 HUD：41,219 B / `FAF4A79AFAA34015548771BC74EBCAB539B1C89F32B3C3C5206B7F8114B45D44`。
- 四人结算图：3,674,880 B / `6DE7E68F8B5247E8A753EBBFFAE550036A70ECCFEC2A3CD076FD49803F869713`。
- 日志：4,051,372 B / `9BCC168BD8306E535B39D0B39355E0DDC5B0BB4E76FE3EB82696CC9A8DCEAAC8`。
- Bridge：0.4.10 / `B27FC892…7CB0FA`。

## 稳定性正控

HUD 显示黄色“实时 · 有事件跳过”后仍继续更新并完成整局，没有像 0.4.9 那样红色异常后永久冻结。0.4.10 的 recoverable/degraded 生命周期判 `R-PASS`。

作者在 23:02:29、第三个 Boss 后安全区首次记录黄色提示；这是“首次注意到”而不是故障发生时间。日志顺序为：

- 进入结晶山第1区：第7982行；
- `damage_snapshot_overflow` / `damage_snapshot_missing`：第8118–8119行；
- 进入结晶山第2区：第8658行；
- 第三个 Boss（第7区）：第10724行；
- Boss后安全区：第12531行。

因此实际故障发生在进入结晶山第1区不久，明显早于第三个 Boss和23:02:29截图。

## 快照容量根因

0.4.10 仍沿用 0.4.9 的 `HpSnapshots.Count >= 8192 -> HpSnapshots.Clear()`。真实四人高命中局达到上限后整表清空，立即造成后续 `damage_snapshot_missing`；黄色降级虽避免整局停止，但这些事件被跳过并形成少算。

0.4.11 改为：

- `Dictionary + LinkedList` 同步维护活跃快照和插入顺序；
- 官方事件消费快照时同步移除顺序节点；
- 达上限只逐个淘汰最旧未消费项，不再整表清空；
- 每个新 session 显式清空全部索引，避免跨局残留。

## 总量与个人归属

游戏官方四人伤害合计 `4,914,668`，Boss 合计 `1,620,539`。工具箱最终可见三人加已退出队友最后一次观测合计 `4,771,208`，Boss `1,572,139`，分别少 `143,460 / 48,400`；与快照溢出后跳过事件方向一致。

作者个人官方为 `1,464,111 / Boss 532,182`，工具箱为 `1,731,117 / Boss 644,418`，分别多 `267,006 / 112,236`。总量少算却个人多算，证明仍有远端事件误归 LocalPlayer，不能用快照漏算单独解释。

0.4.11 收窄 owner 关系：优先 `DisposeHitInfo.mAtkerInHierarchy`，再回退瞬态 attacker；移除缺少多人证据的 `StandMaster` 路径和可能碰撞的 `EntityID` 根玩家匹配，只接受 native pointer 同一性、OwnerEntity层级和Creature.Master。每次换房输出累计 local/remote/unattributed，便于在下一局中途就对账。

## Mini UI

用户要求多人时在近10秒平均DPS卡底部空行增加“自己队伍占比”与 bar。0.4.11/1.6.2 候选仅在识别到队友时显示，单人布局保持不变；仍需精确包 100%/200% 像素验收。
