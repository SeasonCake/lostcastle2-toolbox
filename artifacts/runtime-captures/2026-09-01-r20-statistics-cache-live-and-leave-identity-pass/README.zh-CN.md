# r20 Statistics cache-list实时过程与离队身份修复短测

> lifecycle: `RAW DAMAGE REALTIME PASS / ROLLOVER PASS / LEAVE-TEAM IDENTITY PASS / FRESH DIFFERENT-OWNER AUDIT PASS / BOSS-NPC-FINAL NOT_RUN`

## 冻结身份

- Bridge0.4.27/r20；四名真人；本机初始`player-3 / slot2 / P3`。
- `LogOutput.log`：132,553 B / `7DECC85C36D125CBEC1750BD05D170BB5B2D4D1CE6726F169BD5CA04AE3C29C4`。
- partial events：319,551 B / `12D6EE0D384154000ADB1B881B1B4EC9922FEF3D7AA44E0DF134893F4B80AED1`；summary / `E642B0496E2A8E61D9EBBF4678B7A90DAFCA3002EDBF37F4B5B0DEB4CC647D82`。
- 退出后23:01:35 exact game/toolbox进程0、unknown path0。
- 作者确认正常游戏过程中HUD可用；离队前本机13,827，离队到单人后没有异常增加。

## 过程与房间边界

- 0.4.27真实加载；64个探针样本全部可解析，active/cache-list各4 records、身份完整、无collision/read failure。
- 同房四槽均发生增长，本机slot2最终13,827。工具箱partial在房内持续收到完整live字段；观察值只在两次官方snapshot之间作短时增量，下一live会重新锚定。
- 新增OnChangeRoomEnd Prefix实际产生`room_exit`样本；随后`room_entry`的四槽active逐项一致、cache归零。
- `check_lc2_statistics_cache_probe.py ... --allow-no-remote-only-room`退出0：raw damage realtime PASS、rollover PASS，2/2 transition精确；Boss全0为NOT_RUN。
- dict继续0 records，settlement-dict checker按预期exit1，不进入过程主口径。

## 离队身份

- 离队前最后四人快照：本机`player-3 / slot2 / live13827`。
- 同session离队后单人快照：本机仍为`player-3`，当前slot变为0，live仍13,827；没有生成新player token，也没有继承旧slot0伤害。
- 离队后的官方诊断`members=1`但active/cache仍各4 records、identity matches8、unmatched0、collision0，历史身份门未被覆盖。
- `check_lc2_leave_team_identity.py`对r20 events exit0；对r19冻结events exit1（local token及live改变），形成真实known-good/known-red。
- partial summary最终活动本机为`player-3 / 自己·P1 / live=damage=13,827`，旧队友均inactive。Python/UI无需修改。

## 离线门

- 0.4.27构建前完整门255 passed +41 subtests；SDK6.0.428 C#0 warning/0 error；包/桌面self-test0。
- 新增Statistics/离队真实checker正反控后，外部pytest257 passed +41 subtests；产品二进制未再变化。

## Not run

- fresh different-owner审计独立重算64/64探针样本、2/2边界、437/437事件和离队前后身份，并重放r19 known-red/r20 known-good；SOURCE/PACKAGE/REAL短门PASS。
- Boss、NPC、完整最终SyncEnd、普通样本4,096耗尽、自然完整长局、离队后结算、commit、push、Release均未运行。
