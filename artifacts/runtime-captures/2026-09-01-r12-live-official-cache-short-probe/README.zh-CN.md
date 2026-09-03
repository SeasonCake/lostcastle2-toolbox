# r12 三人两房 live官方缓存短探针

> lifecycle: `REAL SHORT CACHE PROBE PASS / FINAL CONVERGENCE NOT RUN`
>
> candidate: Bridge `0.4.21` / diagnostic-only / HUD unchanged
>
> session: `6820BAA4D6` / `7f673329f4714c479bf22c32aac60cfa`

## 结果

- 游戏与r11工具箱从17:22起保持同一精确进程；installed 0.4.21 DLL为75,776 B / `B164F49608DA4C4EEC6DA75CD7A383EA9725217D7FE68ADB358103764F38D56C`。
- 三人party本机为slot1。`_adventureRecordCacheDataList`与`mAdventureRecordDataList`均存在、各3条record；每次房间边界均`live_identity_matches=6`、unmatched/collision/read failure全0。
- cache列表在本短测保持三槽全0；active列表为有效累计源：

| 边界 | slot0 | 本机slot1 | slot2 | team |
| --- | ---: | ---: | ---: | ---: |
| 进入首战斗房 | 0 | 0 | 0 | 0 |
| 首房结束 | 605 | 28,485 | 9,152 | 38,242 |
| 次房结束 | 2,882 | 36,525 | 16,448 | 55,855 |

- 两次active缓存逐slot均与Bridge过程owner累计、工具箱partial summary精确一致；三槽跨房单调增长。首房owner摘要为local28,485、remote9,757；次房为local36,525、remote19,330，分别精确闭合active列表。
- 因此确认：active列表可在真实多人过程中按匿名平台身份完整映射，并提供跨房累计值；不需要`mIndex`或ordinal猜槽。

## 边界

- 本短测没有最终官方结算，不能单独证明active缓存会在r11长局的P1少算/P4高算路径上收敛最终record。
- 不能把live值写入现有sticky `official_damage`：r11已证明final可能低于过程值，Python当前`max()`会阻止final向下纠正。
- 下一source必须分离`live_damage/live_boss_damage`与final `official_damage/official_boss_damage`：live仅当前完整快照、可撤销；final仍为exact SyncEnd后的sticky权威覆盖。
- 回旋镖/同房多owner actor继续作为次级归属验收项，本短测未识别具体道具实体。

## 冻结文件

- `LogOutput.before-post-hit-transition.log`：64,908 B / `1EEC80218C3784E50509EA291B4E08D2668B62A266F0199B93504D84FAC27EEB`。
- `LogOutput.after-two-room-transition.log`：125,913 B / `AD85C5630876274B81F4EACBD9F2BBF8380085F602FC2DD72D5EDD66C4249E67`。
- `partial-after-two-room-transition/`保留复制时点的events/summary/meta；它是live partial，不冒充同一原子checkpoint。

## Not run

- 未把live缓存发布到pipe/HUD；未构建新工具箱包或替换桌面。
- 未跑最终结算、r11 known-red同路径重放、different-owner审计、commit/push/Release。
