# LC2 Combat Bridge 0.4.12 部署回执

- 候选/随包/游戏目录 DLL：52,736 B / SHA-256 `3229359A7D901CEBCD523109261A034704CA06B0E3EAD0829ADC5B19ED976D8D`。
- PDB：23,160 B / `30EB272BD2903DA1701298B27CF7DE505BF3D9995AACDBCA6988843E79705FAA`。
- exact rollback 0.4.10：52,224 B / `B27FC892719F289CAD4AD94B7FFC33C348647310DF73C7B39F3E27A66F7CB0FA`。
- 2026-08-30 23:36:11 与 23:36:21 两次 exact process 查询均为 0 后部署；回读与候选哈希一致。
- 0.4.11 把 8,192 快照上限从整表清空改为“字典 + 最旧未消费 FIFO 淘汰”，消费/新局/卸载同步移除。
- 0.4.12 优先 `mAtkerInHierarchy`，再用瞬时 `mAtker`；仅沿 Player/native、OwnerEntity hierarchy 与 `Creature.Master` 关系归属，不再猜测 StandMaster/EntityID 根。每次 `change_room_end` 记录 owner 汇总；roster/pipe/schema 扩至 16。
- 0.4.10 长局真实日志给出 `damage_snapshot_overflow` 随后 `damage_snapshot_missing`，证明旧整表清空是事件跳过根因；0.4.12 的该路径已有源码回归和构建，真实多人复测未运行。
- 隔离 SDK 6.0.428 Release 构建：0 warning / 0 error；15 个 Harmony target 不变。部署后没有启动游戏或工具箱。
