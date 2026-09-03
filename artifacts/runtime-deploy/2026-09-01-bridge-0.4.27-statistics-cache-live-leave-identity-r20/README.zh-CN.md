# Bridge 0.4.27 Statistics cache-list实时过程与离队身份修复 r20

> lifecycle: `SOURCE/BUILD/DEPLOY/REAL-SHORT/FRESH-AUDIT PASS / NATURAL OBSERVATION / RELEASE HOLD`

- r19真实四人短局已冻结：Statistics active同房恒定、cache-list按玩家实时增长；479样本身份完整，队友-only房本机为0；最后`active+cache`精确等于OWNER总量。dict始终0 records。
- 0.4.27将两张Statistics列表分别按历史human平台身份HMAC完整唯一映射，允许额外NPC record但拒绝human缺失/重复、负数、Boss>总伤害；发布live=`active+cache`。新session仍要求零基线，过程合计仍须逐槽单调，final exact SyncEnd可独立向下覆盖。
- 离队身份修复：同session优先按平台身份HMAC复用旧匿名token；平台身份暂缺时只有旧opaque token仍能证明同一对象才复用，否则整组拒绝。live按历史身份取值，事件slot使用当前Player.Index。本例期望`player-4/slot0/live3338`，不得创建player-5或拿旧P1=45888。
- 在既有`SettlementDataMgr.OnChangeRoomEnd` Hook target增加Prefix：强制发布房末party snapshot并记录room_exit探针；仍为16个Hook target。
- candidate DLL：90,624 B / `28F5960B4A684CAC3150AC688827142646605796BBDC998A9378D77F1301A2CF`。
- candidate PDB：33,396 B / `D75B986EAE2AC62C5BB346A68F9AC93936EDB4F274A49E862D8DB8C520F482D0`。
- exact rollback0.4.26 DLL：89,088 B / `0F4729E27E6618D83E6B6435C08E35ED448D3C24D8DA7A0EBFCFC47C2B7343E4`；PDB：32,640 B / `94B94088B63FC7FDB7CDE1DC6C67DEE175C85E9EA7503AAE25E2DB45C3A928D4`。
- 构建前pytest255 passed +41 subtests；build内255；SDK6.0.428 Release0 warning/0 error；Mono.Cecil回读0.4.27、16 targets、active/cache-list getter与RoomEndLocation Prefix/Postfix。真实checker加入后外部pytest257+41，产品二进制未变化。
- r19原始错误事件继续在正控中复现45,888；期望稳定token/current-slot事件内存回放得到total/personal均3,338，证明Python/UI无需修改。
- 部署前22:49:03与22:50:12两次结构化查询均exact game/toolbox0、unknown path0；部署后22:50:37仍为0。installed DLL/PDB与candidate逐项一致。
- r20真实短测：raw damage realtime、2/2 rollover及离队identity均PASS；Boss/NPC/final NOT_RUN。证据见`artifacts/runtime-captures/2026-09-01-r20-statistics-cache-live-and-leave-identity-pass/`。
- fresh different-owner审计独立确认source/candidate无漂移、candidate/package/installed/desktop核心身份一致、r19 known-red与r20 known-good均可重放；focused 62+15、full 257+41、diff-check均PASS。结论仅到自然使用观察。
- 未commit、push或Release。
