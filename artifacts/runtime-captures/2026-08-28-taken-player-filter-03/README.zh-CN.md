# 0.3.7 玩家承伤过滤实机回归

记录时间：2026-08-28（Asia/Shanghai）

## 结论

- 运行日志确认加载 `LC2 Combat Bridge 0.3.7`；运行 DLL SHA-256 为 `589D8A63DD518A57188CCB7CC61C3CBAF14F80238E0AD5FF3345FB563ECB074F`。
- 作者按“召唤物先受伤、玩家后受伤”执行。receipt 只保留一条玩家 taken：sequence `53`、`target_kind=player`、`settlement_damage=35`、`applied_hp_damage=35.18484878540039`。
- 没有任何非玩家 taken；召唤物造成伤害仍为 `6629`，说明过滤没有破坏 summon dealt 路径。
- 总伤害 `10502 = 6629（召唤物）+3488（玩家普通）+385（玩家元素）`，来源精确闭合。
- 冻结前连接为 `live`；接受事件 `376`，`0` duplicate、`0` collector fault、`0` Bridge status error。

本轮满足 0.3.7 聚焦回归门。0.3.6 的召唤物 defender 混入玩家承伤问题已闭合，不再增加 Hook 或探针。
