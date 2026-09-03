# r13 / Bridge0.4.22 live字段未穿过pipe有界副本

> lifecycle: `REAL SHORT SMOKE R-FAIL / ROOT CAUSE CONFIRMED / 0.4.23 SOURCE FIXED`

- 作者在VPN卡顿的四人局进入首战斗房并实打；0.4.22 exact DLL正确加载，四槽active/cache列表存在，各4 records，身份匹配8/8，unmatched/collision/read failure全0，零基线成立。
- r13 partial过程累计到60,369，但`live_damage_complete=false`，四槽`live_*`与`last_live_*`始终null；events中只有初始不含live字段的`party_updated`。
- 根因：`PartyMemberSnapshot.ToPayload`和fingerprint已包含live字段，但`CombatPipeServer.PublishPartyUpdated`构造bounded副本时遗漏`LiveDamage/LiveBossDamage`，导致后续fingerprint永远不变、pipe不再发布party更新。
- VPN卡顿不是该失败原因；未见queue overflow、snapshot missing、stack mismatch、slot conflict或fatal。
- 0.4.23只在bounded副本补复制两个非负live字段，不改缓存读取、身份映射、baseline、单调、observed fallback或final权威。
- 冻结日志115,790 B / `B3270855294EA9A577FC0A2E855F9F01CDEE68F8F77F49D2BF3B58E75A56A79D`；自动ZIP33,989 B / `DCA8B9C99F18C83183B36E414560449A28C98DDB95AD8794E7C760822392AE53`。
- 未签发0.4.22过程PASS；commit/push/Release未运行。
