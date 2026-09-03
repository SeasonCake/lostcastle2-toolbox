# r15 / Bridge0.4.24 四人live字段pipe烟测

> lifecycle: `LIVE PIPE IMPLEMENTATION SUBGATE PASS / PRODUCT REALTIME R-FAIL / SUPERSEDED BY R16`
>
> session: `F000947F23` / `d9f74dc4846e4871add1ce08cf42e64e`

- exact installed Bridge0.4.24：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`；r15桌面EXE为`8EFF5DCF…2CDB2`。
- 四名真实玩家，本机slot2；session入口cache/active各4 records，identity matches8/8，unmatched/collision/read failure全0，四槽零基线成立。
- 首个冻结过程快照：slot0=4,546、slot1=4,958、本机slot2=32,498、slot3=2,121，team=44,123。Bridge active日志、partial各槽`damage_dealt`、`live_damage`、`last_live_damage`逐项完全相同。
- `live_damage_complete=true`、`live_boss_damage_complete=true`；final official尚未发生。partial connection live、diagnostic warning null、unattributed=0。
- 未见queue overflow、damage snapshot missing、stack mismatch、slot conflict、fatal或pipe/schema错误。
- 该短测只证明0.4.23 bounded-copy修复与0.4.24 human/NPC匹配门穿过真实C#→pipe→schema→Python→archive全链。后续同局证明raw live只在房间边界更新并压住房内observed增量，产品实时语义R-FAIL；见`../2026-09-01-r15-live-anchor-freezes-within-room/`。
- 冻结日志115,900 B / `830C170BA784C2FACD1013F9F428A083B2B3E4818C66A7C331A67F8B489BF96B`；events509,512 B / `72D82E9BFD908E91D249AFD10398179CA6CFEBBB1A20A3346CB8938FD274509C`；summary / `3FA799DA68F779753358581DB34B00746F8D3A352D2DD020AB13CBFCBA017771`。
- 未commit/push/Release；最终自然结算与different-owner审计另行记录。
