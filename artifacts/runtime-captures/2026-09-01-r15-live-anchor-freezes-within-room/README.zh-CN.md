# r15 live官方值只在房间边界刷新导致房内冻结

> lifecycle: `REAL FOUR-PLAYER REALTIME R-FAIL / ROOT CAUSE CONFIRMED / R16 SOURCE FIXED`

- r15四人局已证明live字段穿过pipe，但作者明确观察：同一房间内即使队友持续输出，自己与队友行都不增加；进入下个房间才整体刷新。
- 冻结room6 partial中`live_damage_complete=true`，但四槽display/live分别79,390/67,356/37,799/15,128，observed已到98,236/75,161/44,086/18,987；team显示199,673，observed合计236,470，房内增量36,797被完整live快照压住。
- 根因：`mAdventureRecordDataList`是房间边界官方缓存，不是逐击实时流；Python在live complete时直接显示raw live，忽略后续observed增量。
- r16采用无倍率加法：每次live更新记录`live official anchor`与当时`observed anchor`；房内显示`live + max(0, observed - observed_anchor)`，新房`room_started`先为所有live槽重锚，随后新live快照再校正。相同live的同房roster刷新不得清空增量。
- archive新增保留`last_live_observed_*_anchor`；final checker重建实际过程显示后与官方比较，不再只比raw last_live。
- 冻结日志196,481 B / `E58FC2E3E14DC0AC9F69D449BA4F2999CFDE5C9BAC12F3160E7C93365E645E6F`；events1,983,729 B / `77D1255B33C984A217D44418E942A94BE77D9F61E4396C7F2886B672751F84E7`；summary / `A060CF9C54B96723FD6A15EDB874E20C3730B4D02A051C7B64CAED81CA9E9FA5`。
- r15产品实时语义R-FAIL；其四槽pipe实现子门PASS不能外推。commit/push/Release未运行。
