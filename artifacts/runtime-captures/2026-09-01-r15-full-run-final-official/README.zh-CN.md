# r15四人完整长局：final官方PASS、实时过程仍R-FAIL

> lifecycle: `FINAL OFFICIAL PASS / R15 REALTIME R-FAIL / ANCHOR+DELTA FINAL CONVERGENCE R-FAIL / NEXT REALTIME OFFICIAL-DICT PROBE`
>
> session: `F000947F23` / `d9f74dc4846e4871add1ce08cf42e64e`

## 最终四槽

| slot | observed total / Boss | final official total / Boss | observed delta / Boss delta |
| --- | ---: | ---: | ---: |
| P1 / slot0 | 4,567,404 / 2,038,713 | 4,722,964 / 1,926,621 | -155,560 / +112,092 |
| P2 / slot1 | 16,528,974 / 7,707,748 | 16,352,764 / 6,533,391 | +176,210 / +1,174,357 |
| 本机P3 / slot2 | 17,773,501 / 8,759,248 | 14,657,910 / 5,725,414 | +3,115,591 / +3,033,834 |
| P4 / slot3 | 2,714,016 / 1,366,040 | 3,135,844 / 1,443,729 | -421,828 / -77,689 |
| team | 41,583,895 / 19,871,749 | 38,869,482 / 15,629,155 | **+2,714,413 / +4,242,594** |

- exact SyncEnd后连续两次final摘要：4 records、4 identity matches、0 unmatched/collision、4 published、accepted=true；final官方门PASS。
- SyncEnd时active列表也变为4,722,964/16,352,764/14,657,910/3,135,844及对应Boss，与final逐槽完全一致；说明游戏官方缓存最终权威正确。

## 过程模型结论

- r15直接显示raw live，房内冻结，产品实时语义R-FAIL。
- 用最后房间官方锚点与owner日志的observed team基线精确重建r16/r17 anchor+delta：过程team约41,341,011，对final高2,471,529（约6.36%）；Boss约19,647,750，对final高4,018,595（约25.7%）。
- 相比纯逐击，锚点分别修正242,884总伤害与223,999 Boss，但最终房预测命中仍显著高于主机最终认可；anchor+delta不能签长局过程准确PASS。
- 主城剧情房证明active可能跨多个room保持不变、随后延迟更新；因此不能在每次room_started清delta，只能在live快照实际变化时全槽重锚。
- 下一最窄数据面是参考DLL已使用的`SettlementDataMgr.mCacheRoundDataDict`逐玩家`DamageCollector`；需先只读诊断其房内实时更新、human/NPC身份和final收敛，不能引入倍率或角色/道具特判。

## 异常与归档边界

- 全局仅1次`damage_snapshot_missing`，后续未重复；无queue overflow、stack mismatch、slot conflict、schema/pipe fatal。该单击可能在房内临时漏计，并由后续官方锚点校正。
- partial共97,296 events，但67,108,683 B达到64 MiB上限，`events_truncated=true`；events文件止于sequence92,034，约5,261条尾部事件未落盘。summary与LogOutput保留final，但无法从r15 archive精确重建最终前逐槽anchor observed基线。
- 后续默认事件上限应提高到128 MiB；archive仍保留截断正控，且需在final报告明确记录存储成本。

## 冻结文件

- `LogOutput.log`：14,366,432 B / `EF07F3BBCEBAE007526C583D7E4CEFC86EFB6B151AB3BC64A0FEE49D65FD7CD2`。
- `partial-final/events.jsonl`：67,108,683 B / `D523F10D98EE9A6B8A158087123B323C287EC27EC906A6077EEC04ED9A73A326`。
- `partial-final/summary.json`：13,305 B / `9FC3A9AB2C6BDE0C354BF80685A2A3853C398A9F60B6DACBDEBCD7B7D47822A2`。

## Not run

- 新版official-dict实时探针、r17实机、完整未截断重放、fresh-clone、commit/push/Release均未运行。
- final official PASS不等于r15/r16/r17实时过程PASS或Release PASS。
