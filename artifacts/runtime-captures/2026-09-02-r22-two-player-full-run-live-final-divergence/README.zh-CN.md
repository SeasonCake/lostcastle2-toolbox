# r22 双人完整局过程值与最终官方值分岔

> lifecycle: REAL FULL RUN / FINAL OFFICIAL PASS / PROCESS ESTIMATE MISMATCH CONFIRMED / SPECIFIC GAMEPLAY RULE UNKNOWN

## 冻结证据

- Bridge0.4.27、r22双人完整局，session `52147703a7b0443fb70245f9e6be328b`。
- `LogOutput.log`：5,391,195 B / `9B31399656CB238054EFF1A93A4C448A6363DFBC840F4B3F84DBC43BFD965A00`。
- `toolbox-partial/events.jsonl`：23,325,436 B / `E952091FFFC2DE122200264C9DD7282C9790D70AE341132DEC4053949C47B7B4`；33,031行、parse error0。
- `toolbox-partial/summary.json`：12,129 B / `BF9DBAF889D04EA45F643147512A6BCCF9A192FEFA5C58841A840BB3FC0E9BEF`。
- 官方结算截图：2,519,016 B / `011A6793C88750B30DEE8018DDB5327836F2049BB92BFF794E2A02355A35F2DB`。

## 决定性结果

- P1/本机：最终房入口9,524,622/Boss3,404,627；最后raw live 11,057,093/4,326,570；SyncEnd final 10,440,726/4,129,298；final-live为-616,367/-197,272。
- P2：最终房入口6,619,905/Boss2,338,796；最后raw live 8,520,510/2,949,130；SyncEnd final 8,829,890/2,974,693；final-live为+309,380/+25,563。
- 全队：最后raw live 19,577,603/7,275,700；final 19,270,616/7,103,991；final-live为-306,987/-171,709。
- final前2,873个raw sample逐槽combined回退0；890个live party snapshot逐槽回退0；52/52房间边界combined精确守恒。
- 唯一权威回退/重分配发生在SyncEnd：游戏清空cache并把active直接替换成截图中的最终值。本机下降、P2上升、团队总量同时下降，排除单纯cache重复或比例误差。
- HUD未重复叠加：P1最后显示值正好等于raw 11,057,093；P2在最后live 8,520,510后又发生110,363逐击，锚点过程值为8,630,873。
- 偏差无需假设早期累计错误即可完全由最终Boss房解释；但没有最终房入口的另一个final口径checkpoint，不能断言历史房间在游戏内部从未被最终规则重算。

## 根因层级

- 已确认：Bridge忠实读取游戏Statistics active+cache；Python只在新live快照后增加一次未锚定逐击，没有跨快照重复累计。
- 已确认：游戏-owned过程列表与SyncEnd最终存档记录口径不同，最终会剔除部分团队伤害并在P位之间重分配。
- 未确认：具体由最终Boss多实体/阶段、召唤/共享投掷物归属、服务端校正或其他玩法规则中的哪一项触发。
- 现有替代面不能解决：Settlement dict全程0 records；singleton非逐P且SyncEnd后仍未收敛final；save list只在SyncEnd后已有可靠合同。

## 产品边界与下一探针

- 最终SyncEnd继续作为权威值并允许向上/向下覆盖。
- 过程值目前只能诚实标为“实时估算/结算可能校正”；不能用max、固定比例或本局差值外推下一局。
- 若继续追求更早权威值，最小只读探针应在`SyncAdventureRecordDataEnd` prefix/postfix及`SyncSettlementData_ClientResult`/`SyncSettlementData2_Rpc`附近匿名记录incoming record、save list、`_multiRoundDataDic`与active/cache时序，不发布到HUD。

## Not run

- 未实现新探针或UI文案修正，未构建/打包/部署，未commit、push或Release。

## 关闭后归档观察

- 2026-09-02 11:39 exact游戏/工具箱进程0、unknown path0。
- 关闭后日志：5,549,299 B / `0CC4F42DD70A113D98076411C879140E685BC2F80A7364D2437CEBF7464C796E`。
- 工具箱生成`2026-09-02_113803_恢复_55BCED8198.zip`：1,194,633 B / `52CD03C5397A685BD5C39229B81F049DAA6F26CB08E5F48C5C97235B9258CAC4`。
- ZIP manifest记录33,405 events、23,434,037 B、未截断，events属于本次长局；但ZIP内summary却是随后新建的单人零伤害session `c0b279f7314f43dda329bb3676180f25`，而非事件所属session。因此该恢复ZIP存在events/summary跨session不一致，不能用其summary作本局最终证据。
- 本目录在新session出现前冻结的events/summary与官方截图仍保持同一原session，可继续作为本局诊断证据。
