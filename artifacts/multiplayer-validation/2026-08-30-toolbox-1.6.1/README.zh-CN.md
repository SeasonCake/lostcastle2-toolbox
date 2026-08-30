# 工具箱 1.6.1 多人合同与活性验证

- 记录时间：2026-08-30。
- 生命周期：`2P–4P SYNTHETIC/REPLAY PASS / EXACT PACKAGE UI PASS / REAL NETWORK NOT RUN`。
- 目标：在没有真实联机人口的条件下，尽可能证伪多人身份合并、事件静默丢弃、队列卡死、异常后仍假装实时及 UI 行缺失。

## 已通过

- 冻结前复跑：上述两项聚焦测试 `2/2 PASS`，耗时 0.365 秒；全量 `171/171 PASS`，耗时 3.777 秒。命令分别为 `py -3 -m unittest <两个完整测试名> -v` 与 `py -3 -m unittest discover -s tests -p "test_*.py" -q`。
- `test_two_to_four_player_rosters_keep_every_owner_distinct`：分别建立 2/3/4 人匿名 roster，每个人使用不同 opaque owner token；每个人 250 轮伤害后，总伤害、每人伤害、自己/队友标签与未归属值逐项精确断言，`unattributed_damage=0`。
- `test_four_player_batched_event_pump_stays_live_under_load`：四人共 2,000 个伤害事件分 10 批进入有界 inbox/pump；每批均无 fault，最终仍为 `live`，四人累计精确相等且无未归属，测试设有 5 秒活性上限。
- 相邻负控覆盖重复玩家身份、重复事件、同 sequence 不同内容、foreign session、schema 错误、队列 overflow 和 heartbeat stale；异常均显式进入拒绝/错误/陈旧状态，不静默吞掉后继续伪装正常。
- Windows named-pipe roundtrip、主线程 UI mutation、2–4 人演示快照和四行主面板/HUD 均由全量测试或精确包 UI 回执覆盖。
- 精确包四人 UI：主面板 `COMBAT-A150-party4-r11` 与 HUD `HUD-A200-party4-r11`，共同绑定 EXE SHA-256 `46525496…46C8D`。

## 能证明与不能证明

这些验证证明当前协议、解析、队列、聚合和 UI 对 2–4 个不同 owner 的确定性处理不会在已覆盖输入上合并、卡死或静默漏算；异常输入会显式 fail closed。它不能证明游戏 Bridge 在真实 Steam 联机中一定能取得所有远端 owner，也不能替代主客机、加入/离开、网络重传或召唤物归属的实机人口。

因此 v1.6.1 可以发布为“2–4 人合同/回放/UI 已验证”，但 Release 必须继续标注“真实 2P–4P `NOT RUN`，欢迎反馈”，不得写成“联机实测通过”。
