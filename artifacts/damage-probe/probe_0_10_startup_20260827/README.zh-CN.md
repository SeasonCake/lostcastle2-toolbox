# 0.10.0 自然启动门

- 会话完成后游戏已完全退出。
- 日志：`probe_0.10.0_startup_final.log`
- SHA-256：`C9980807D2C8AE7E3D25C83449B825230182AEC5E7BD451A9D77F3C3DD3AF122`
- 大小：`2,218` 字节。
- 加载版本：`LC2 Damage Probe 0.10.0`。
- `ChangeCurrentHp`、`SetCurHP`、`FullFoodEnergyOrRecoverHp` 与既有 7 个伤害/边界观察点全部挂载，总数 `10`。
- probe/Harmony/HP observation 错误数：`0`。
- 本会话没有恢复动作：`hp_change=0`、`hp_set=0`、`hp_food_recover=0`。

判定：自然启动与 patch 加载 **PASS**；恢复语义 **NOT RUN**，零事件不能解释为零恢复。
