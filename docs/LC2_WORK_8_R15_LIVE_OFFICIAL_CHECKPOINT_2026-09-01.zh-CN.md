# LC2 工作8 r15 live官方过程主口径 checkpoint（2026-09-01）

> lifecycle: `superseded / r15-live-pipe-subgate-pass / r15-product-realtime-r-fail / r16-candidate-built`
>
> role: 工作8为唯一调查/source owner；different-owner审计已派只读，尚未回执。

## 当前结论

- r11完整局继续是过程`known-red`：per-hit observed对final官方逐槽显著不一致，旧owner/final两门PASS不能签过程正确。
- r11全事件重放证伪owner-only、单一逐击公式与回旋镖/共享actor主因。P1绝大多数伤害依赖real=0 fallback，本机P4无fallback仍高算；团队/Boss差额方向也不守恒。
- 参考DLL与r12真实探针确认`StatisticsMgr.mAdventureRecordDataList`可提供按玩家累积的live官方缓存；用`PlatformUniqueID`本机HMAC可完整匿名映射，不依赖mIndex/ordinal。
- r14两人+NPC完整局中，结束前active缓存本机675,616/Boss150,361，与截图官方卡精确一致；per-hit HUD为675,709，高93。P1 active164,336、per-hit164,510，高174。NPC76,530/Boss15,576独立unattributed，不属于玩家官方卡。
- r15四人真实smoke已证明四槽live字段通过C#→pipe→schema→Python→archive全链，但随后同房持续输出时raw live不刷新并压住observed增量，产品实时语义R-FAIL。r16改为房间官方锚点+房内逐击增量。

## 0.4.24合同

1. 新session先取得全部历史human槽的完整零基线；未取得时只用旧逐击。
2. active records可包含额外未匹配NPC，但每个known human identity必须恰好匹配一个历史slot；missing/duplicate/collision整组拒绝。
3. live逐槽必须非负、Boss≤总伤害且单调；异常时整组不发布，Python清空当前live并回退observed。
4. `live_damage/live_boss_damage`是可替换当前快照；`official_damage/official_boss_damage`只供exact SyncEnd后的sticky final，可向下覆盖live。
5. archive保留`last_live_*`。checker在完整last_live存在时以`process_basis=live_official_cache`比较final，否则旧证据仍用`per_hit_observed`。
6. 逐击事件、来源分解、NPC unattributed、0.4.20 session恢复与0.4.19 final冻结均保留；无新增Hook、角色/武器/地图/Boss/道具特判。

## 身份与门

- Git：`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66=origin/main`；工作树仍是工作6/7/8连续共享未提交范围，禁止reset/clean/整体stage。
- source/candidate/package/desktop/installed Bridge0.4.24 DLL：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`。
- candidate/installed PDB：29,760 B / `8BC5DCA2E9C5DA0147DAEB04105963F378B30FE38A9797D8BDCCA3A345B0FCCC`；0.4.23 exact rollback在r15 deploy artifact。
- desktop r15：`<desktop>/失落城堡2工具箱1.6.3-live官方缓存NPC兼容版-r15`；1,761文件、166目录、166,678,069 B、config0，与项目包逐文件差异0；EXE6,485,801 B / `8EFF5DCFE590EBCCE21E89D5B67BFAAD38CB55C509614BDE58AD469F4DF2CDB2`。
- Python聚焦89；全量234 passed +37 subtests；build内unittest234；SDK6.0.428/current interop Release0 warning/0 error；16 Harmony patch。
- 包/桌面self-test exit0；包形runtime fresh ready并安装exact0.4.24，冲突负控写入前阻断；r11 checker保持exit1。

## 证据链

- r11 known-red：`artifacts/runtime-captures/2026-09-01-r11-process-owner-mismatch-final-correct/`。
- r12 active缓存探针：`artifacts/runtime-captures/2026-09-01-r12-live-official-cache-short-probe/`。
- r13 payload遗漏positive control：`artifacts/runtime-captures/2026-09-01-r13-live-payload-copy-omission/`。
- r14 NPC/官方卡：`artifacts/runtime-captures/2026-09-01-r14-npc-extra-official-record/`。
- r15四人pipe PASS：`artifacts/runtime-captures/2026-09-01-r15-four-player-live-pipe-pass/`。
- package/deploy：`artifacts/package-verification/2026-09-01-toolbox-1.6.3-npc-extra-record-r15/`与`artifacts/runtime-deploy/2026-09-01-bridge-0.4.24-npc-extra-record-r15/`。

## 仍开放 / Not run

- 0.4.24的自然完整多人结算`last_live_*` vs final逐槽门尚未运行；当前不要求作者再打长局，以后自然结算自动判定。
- r11目标人口smoke已由r15四人短测覆盖live pipe，但不等于长局final convergence。
- same-process两局reset的独立作者原始短receipt仍pending；已有r11 session-start证明本次主线非跨局续接。
- different-owner审计等待回执；owned-path inventory/fresh-clone/index审查未完成。
- commit、push、新Release、公开分发均未授权且未运行。
