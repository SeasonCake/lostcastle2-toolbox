# Bridge 0.4.25 房内官方缓存只读探针 r18 部署回执

> lifecycle: `SUPERSEDED / PRE-READ-THROTTLE MISSING / FORCE-CAP BUG / REAL NOT RUN / ROLLED BACK`

- 21:49阶段复审确认：普通命中在限频前已完成全部重读取；普通样本达到4,096后也会阻断force边界；checker还把未实测的dict/cache与rollover关系提前写成硬FAIL。这三项使r18不能提供可信短房判定。
- 作者已被通知不要启动；桌面目录改名为`<desktop>\已撤回-失落城堡2工具箱1.6.3-房内官方缓存探针版-r18`。
- 21:49:14与21:49:48结构化进程查询均为0、unknown path0；随后installed已回滚0.4.24 exact，21:50:08部署后仍为0。

- 0.4.25只新增诊断：在既有`SettlementDataMgr.OnDamageAndBossDamage` postfix及房间/结算边界，同一主线程样本读取`mCacheRoundDataDict`、Statistics cache list和active list；不新增Harmony Hook，不写pipe、不改变`live_*`或HUD。
- 字典key只按非零Player ID/ClientID/TransportID唯一匹配，或由同key network record的平台身份HMAC辅助；不使用昵称、ordinal、固定slot0或`record.mID`。额外NPC计unmatched；缺失、碰撞、重复、非有限/负值及Boss>总伤害均单列。
- candidate DLL：87,040 B / `2C0936C35833A486DEA19ABA8118ECFF79F5295D3383A86C4C4DE16D3433852F`。
- candidate PDB：32,260 B / `36B6F1134062E380750C47E30BD5DAEAA91CFCBEC85FF5C3722006B990344188`。
- exact rollback 0.4.24 DLL：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`；PDB：29,760 B / `8BC5DCA2E9C5DA0147DAEB04105963F378B30FE38A9797D8BDCCA3A345B0FCCC`。
- 部署前结构化进程查询：21:39:44与21:44:32均exact game/toolbox 0、unknown path 0；部署后21:44:56仍为0。
- 本段原始部署当时candidate readback一致，但现已撤回，不得作为current installed身份或真实候选。
- Python完整门：245 passed + 41 subtests；隔离SDK6.0.428 Release：0 warning / 0 error；Mono.Cecil回读0.4.25、16个Harmony patch及三数据面getter。
- 下一真实门只需至少两名human的一到两个短房：同房先由队友造成伤害，再由本机造成伤害，随后过一个房间边界。checker要求同room_epoch至少两个human槽增长、dict/cache-list交叉一致，并验证active只吸收一份delta、不掉数或双加。
- 普通房Boss全0仅记`Boss NOT_RUN`；真实探针通过前不能升级主口径或签过程/Release PASS。
- 未commit、push或Release。
