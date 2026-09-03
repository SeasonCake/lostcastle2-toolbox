# Bridge 0.4.26 限频房内缓存只读探针 r19

> lifecycle: `SOURCE/BUILD/DEPLOY PASS / REAL NOT RUN / PROCESS ACCURACY HOLD`

- 0.4.25/r18在真实运行前因pre-read限频缺失、force边界受普通cap影响、checker预设未证关系而撤回；installed已恢复0.4.24 exact。
- 0.4.26将200ms单调时钟门放在任何PlayerList、dict、network、Statistics cache/active读取之前；每房首个attacker callback与所有force边界旁路。
- 普通样本额度与总样本序列分离；达到4,096仅抑制普通命中，room_exit/preload/round_end/final_sync仍无条件留样，并在样本中标记`ordinary_suppressed`及`throttled_calls`。
- unmatched/collision/duplicate/read-failure使用每进程密钥加run epoch的16位HMAC opaque token，只供本地诊断关联；不输出raw key、昵称、平台ID或pointer。mapping basis继续单列。
- checker只将同房human增长、唯一映射、有限/非负/Boss≤总伤害、无碰撞/重复/读取失败作为raw门；dict对cache-list/active及转场`active+dict`只分类为关系证据，不因差异预判FAIL。
- candidate DLL：89,088 B / `0F4729E27E6618D83E6B6435C08E35ED448D3C24D8DA7A0EBFCFC47C2B7343E4`。
- candidate PDB：32,640 B / `94B94088B63FC7FDB7CDE1DC6C67DEE175C85E9EA7503AAE25E2DB45C3A928D4`。
- rollback0.4.24 DLL：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`；PDB：29,760 B / `8BC5DCA2E9C5DA0147DAEB04105963F378B30FE38A9797D8BDCCA3A345B0FCCC`。
- 外部pytest247 passed +41 subtests；build内unittest247；SDK6.0.428 Release 0 warning / 0 error；Mono.Cecil回读0.4.26、16 Harmony patch、TickCount门位于首个游戏数据读取之前。
- 部署前21:59:53与22:01:06两次结构化查询均exact game/toolbox 0、unknown path0；部署后22:01:33仍为0。installed DLL/PDB回读与candidate逐项一致。
- 真实r19、formal audit、commit、push、Release均未运行。
