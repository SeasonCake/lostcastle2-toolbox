# LC2 工作8 r20 Statistics cache-list实时过程 checkpoint（2026-09-01）

> 历史快照：r20 记录已被后续 r23/v1.7 收口接续；下列 `current/release-hold` 是当时状态，不表示当前发布门。

> lifecycle: `current / r20-real-short-pass / fresh-audit-pass / natural-observation / release-hold`

## r19真实结论

- r19四真人479个有效样本：active/cache-list各4 records、identity matches8、unmatched/collision/readfail均0；dict479次均0 records。
- active同房恒定，cache-list进房归零并逐槽单调增长；remote-only房本机0，本机攻击房增加1,139/2,199。
- 最后`active+cache=[45,888,35,652,41,555,3,338]`，team126,433，精确等于OWNER remote123,095+local3,338。raw damage realtime PASS；Boss、NPC、pipe、严格room-exit rollover均NOT_RUN。
- 先离队再退出后，游戏官方卡仍3,338，HUD却45,888。45,888精确为旧P1，不是三队友求和。错误协议事件为同session新`player-5/slot0/live45888`；正确期望是稳定`player-4/current slot0/live3338`。

## 0.4.27合同

1. live同时要求active与cache-list覆盖全部历史human身份且各身份唯一；NPC可额外unmatched。
2. 每槽live=active+cache；非负、Boss≤总伤害、完整零基线、组合值单调。不满足时整组不发布，旧逐击fallback保持。
3. final exact SyncEnd sticky独立，仍可向下覆盖live。
4. 同session平台HMAC匹配旧身份时复用player token；身份暂缺只允许同旧opaque token连续，否则hold。live按历史身份查值，协议slot使用当前Index。
5. KnownParty历史身份不因本机Index从3变0而覆盖旧slot0或制造双槽碰撞；真正新session仍统一清空。
6. 既有OnChangeRoomEnd target新增Prefix房末force，不新增target；下一短局必须得到room_exit样本并验证rollover。

## 身份与门

- Git仍为`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66=origin/main`；共享未提交工作6/7/8范围未stage，禁止reset/clean/整体stage。
- candidate/package/desktop Bridge0.4.27 DLL90,624 B / `28F5960B4A684CAC3150AC688827142646605796BBDC998A9378D77F1301A2CF`；PDB33,396 B / `D75B986EAE2AC62C5BB346A68F9AC93936EDB4F274A49E862D8DB8C520F482D0`。
- r20桌面`<desktop>/失落城堡2工具箱1.6.3-房内实时官方过程修正版-r20`的不可变基线为1,761文件、166目录、166,691,409 B、config0，与项目包逐项一致；本次真实运行后新增2个config与3个partial运行态文件，原1,761个公共文件仍逐项一致。EXE / `009F8A055CB4751DE33455BFF52EF39349AC054D56010D106F72D42B512DC626`。
- 构建前pytest255 passed +41 subtests；build内255；SDK6.0.428/current interop0 warning/0 error；16 Harmony targets；包/桌面self-test exit0。真实checker加入后外部pytest257+41，产品二进制未变。
- 0.4.26 exact rollback与0.4.27 candidate已冻结；部署前22:49:03与22:50:12两次进程0/unknown0；部署后22:50:37仍为0，installed回读exact。

## 下一步与Not run

- 最短真实门已完成：本机13,827；room_exit/entry四槽2/2逐项一致；离队后同`player-3`从slot2变slot0且live仍13,827，用户确认无异常增加。
- 唯一fresh different-owner审计独立复核SOURCE/PACKAGE/REAL短门并PASS：focused 62 passed +15 subtests，full 257 passed +41 subtests，`git diff --check` exit0；r19离队known-red仍exit1，r20离队known-good exit0。结论仅允许进入自然使用观察，不是Release PASS。
- Boss、NPC、完整final SyncEnd、普通样本4,096耗尽、自然完整长局、离队后结算、commit、push、Release均未运行。
