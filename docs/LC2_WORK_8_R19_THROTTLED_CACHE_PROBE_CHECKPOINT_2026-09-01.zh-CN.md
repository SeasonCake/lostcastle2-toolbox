# LC2 工作8 r19 限频缓存探针 checkpoint（2026-09-01）

> 历史快照：r19 探针已完成并在正式 v1.7 中关闭；下列 `current/release-hold` 是当时状态，不表示当前发布门。

> lifecycle: `current / r19-deployed / ready-for-short-real-probe / real-not-run`

## 更正与当前决策

- r18在实测前撤回，原因是pre-read限频缺失、普通样本cap吞force边界、checker预设未证dict/cache及rollover关系。作者已被通知不运行，桌面目录已改名，installed在双零门后恢复0.4.24 exact。
- r19/Bridge0.4.26只修诊断证据质量，不改变HUD或过程计算。真实短房冻结前不把dict解释为delta或cumulative，也不要求其必须等于Statistics cache-list。

## 0.4.26合同

1. 非force attacker sample在所有游戏对象读取前执行200ms `Environment.TickCount64`门；每房首个attacker sample旁路。
2. force边界永不受普通4,096样本额度影响；日志显式提供ordinary samples/suppressed和throttled calls。
3. 同一采样仍连续读取dict、cache-list、active三张raw向量；无max/单调化/提前取整。
4. unique nonzero network key映射、human完整性、NPC unmatched、碰撞/重复/invalid/read failures合同保持。
5. unresolved记录只输出run-scoped HMAC opaque token、status和mapping basis；不输出raw key、昵称、平台ID或pointer。
6. checker raw门只验证当前已证安全条件；`dict_relation`分类`DELTA_MATCHES_CACHE_LIST/CUMULATIVE_MATCHES_ACTIVE/UNKNOWN/MIXED`，rollover只标`OBSERVED`及关系，不先判公式正确。

## 身份与门

- Git仍为`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66=origin/main`，共享工作树未stage；禁止reset/clean/整体stage。
- candidate/package/desktop Bridge0.4.26 DLL：89,088 B / `0F4729E27E6618D83E6B6435C08E35ED448D3C24D8DA7A0EBFCFC47C2B7343E4`；PDB：32,640 B / `94B94088B63FC7FDB7CDE1DC6C67DEE175C85E9EA7503AAE25E2DB45C3A928D4`。
- r19桌面：`<desktop>/失落城堡2工具箱1.6.3-限频房内缓存探针版-r19`；1,761文件、166目录、166,689,868 B、config0，与项目包逐项一致；EXE / `64A3E51F333B454F85C16121648838D1DCF49CF37689CD53C3BC1B446E5091CC`。
- pytest247 passed +41 subtests；build内247；SDK6.0.428/current interop0 warning/0 error；16 Harmony patch；包/桌面self-test exit0。
- 0.4.24 rollback与0.4.26 candidate已冻结；21:59:53与22:01:06两次部署前结构化进程查询均为0、unknown path0；部署后22:01:33仍为0，installed DLL/PDB与candidate exact。

## 下一步

只需至少两名human的一到两个短房，阶段间等待超过250ms：队友有效伤害、本机有效伤害、一个房间边界。冻结真实日志后才收紧关系合同，并只派一个fresh different-owner综合审计。

## Not run

真实短房、Boss语义、pipe/HUD采用、fresh audit、commit、push、Release均未运行。
