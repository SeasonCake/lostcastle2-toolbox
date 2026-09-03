# r14 / Bridge0.4.23 两人+NPC额外official record

> lifecycle: `REAL EDGE CONTROL R-FAIL / EXPECTED SAFETY HOLD / 0.4.24 SOURCE FIXED`

- 作者真实组合为两名玩家（含本机）加一个NPC。party roster为2，cache/active列表各3 records；两名玩家跨两列表identity matches=4，NPC各产生1 unmatched，总unmatched=2；collision/read failure均0。
- 首房结束玩家过程值slot0=9,286、slot1=10,057，active官方列表逐槽完全相同。NPC伤害2,409被Bridge记为unattributed，未归入任一玩家；过程总21,752=9,286+10,057+2,409。
- 0.4.23要求`records.Count == KnownPartyBySlot.Count`，因此对NPC额外record整组不发布，partial的live/last_live保持null。这是安全门按预期hold，不是payload复制回归。
- 0.4.24改为允许额外未匹配record；仍要求每个已知human identity恰好匹配一个历史slot、接受槽集合与期望全集相等、duplicate slot失败、Boss≤damage且逐槽单调。NPC record被忽略，不加入玩家团队官方合计。
- 关闭前最终active缓存：P1=164,336/Boss41,002，本机=675,616/Boss150,361；逐击过程为P1=164,510/Boss41,002、本机=675,709/Boss150,361，分别只高174与93。18:23截图中本机官方卡为675,616/Boss150,361/承伤295，active缓存逐项精确一致；HUD仍显示旧逐击675,709是0.4.23严格NPC门未发布live，不是缓存不准。
- NPC本局累计76,530/Boss15,576，始终unattributed；官方玩家合计839,952，旧HUD含NPC总量916,749。因此r15启用live后玩家份额将按两张玩家官方卡计算，不把NPC计入任何玩家或玩家团队分母。
- 冻结日志135,222 B / `867DF55881BF5560F0714C8916663CC1EC405CB6490D3B8DAD6443CB68A59E2B`；partial events621,438 B / `A6F5635AB48FF5A566C4690FE158889B18168E28030BF667C9F1DDC73F8FF629`；summary / `F889A952CABE9F9F9B5E932458F2B89EBD5F622C14C5719106A460C8FF075783`。
- 关闭后完整日志513,181 B / `0C861FE3289F39D97537F23BA91198E94BF7F23FB5348F4EB013A3D745B16B4C`；自动ZIP241,941 B / `8B4894F6F04C1A6EF4E76AAFAEB6891CCF2D28B165F437FB9F033F58B77ED1CF`；两张本地截图分别`3A126F78…C9FB`与`4CECE021…6BFD`。
- 未签过程PASS；commit/push/Release未运行。
