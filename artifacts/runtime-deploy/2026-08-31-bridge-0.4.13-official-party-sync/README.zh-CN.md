# Bridge 0.4.13 官方逐玩家累计部署回执（已被r2取代）

- 候选/随包/游戏目录 DLL：58,880 B / `9FF0B4FFFA3E2B3E02327B5A3B90B810B2906884ADD0E5AF8936858D79BFD64D`。
- PDB：24,720 B / `595E450E2BEB46E93F752B6DC8CD2593702EE5C5D7729D9C12F7A5475D7C6616`。
- exact rollback 0.4.12：52,736 B / `3229359A7D901CEBCD523109261A034704CA06B0E3EAD0829ADC5B19ED976D8D`。
- 隔离 SDK 6.0.428、当前游戏 interop、Release：0 warning / 0 error；15 Harmony Hook不变。
- 部署前两次exact进程检查（相隔10秒）均为0；部署后游戏目录回读与候选一致。
- 协议在`party_updated`成员上新增可选`official_damage/official_boss_damage`；不发送昵称或原始ID。Bridge内部只用ID/ClientID/TransportID与Index把游戏记录映射到匿名slot。
- `damage_stack_mismatch`改为`damage_event_skipped=False`计数诊断，不再产生黄色degraded；真实snapshot/conversion/checkpoint失败和致命queue边界保持。
- 生命周期：`SUPERSEDED BEFORE REAL RUN`；索引基准锁定与同slot token去重进入r2，本DLL未运行真实游戏。
