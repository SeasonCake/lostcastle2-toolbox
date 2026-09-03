# r19 Statistics cache-list实时PASS / 离队身份重绑R-FAIL

> lifecycle: `RAW DAMAGE REALTIME PASS / SETTLEMENT DICT R-FAIL / ROLLOVER NOT_RUN / BOSS NOT_RUN / LEAVE-TEAM HUD R-FAIL`

## 冻结身份

- Bridge0.4.26/r19；四名真人；本机初始`slot3/P4`。
- `LogOutput.log`：860,697 B / `7D5E87165A330A9AE6739FAD2DC229B1751ED56415BFC903E3B6049C4EC892C7`。
- toolbox partial events：2,553,277 B / `29C4D8C31BCB691352727A008D678BBD71DDD4EA7A862F1A155F0BE47CB06171`；summary / `48F860474C99F1537A9ADCD24CD4E35E0001C28F3B35F62904137EA541398F62`。
- 作者截图：771,336 B / `1209DA2F6174E0681A515FDE1F78B66F72846E939E385A53EE78E04D6C883886`。截图含玩家昵称，仅作本机受限证据，不公开分发。
- 退出后exact game/toolbox进程0；LogOutput冻结时SHA-256如上。

## 房内实时数据面

- 479/479探针样本均active/cache-list可用，各4 records；`matches=8`、unmatched/collision/read failures均0。
- `mCacheRoundDataDict`在479/479均`available=true`但`records=0 / slots=none`，本局判该数据面R-FAIL。
- Statistics active同房恒定；cache-list每房入口归零并按玩家单调增长，没有回退。
- `local_slot=3`全程稳定：作者完全不攻击的epoch2/5/7，本机cache始终0；攻击的epoch4/6分别累计1,139和2,199。
- 最后有效`active+cache=[45,888,35,652,41,555,3,338]`，team126,433；精确等于OWNER远端123,095加本机3,338。
- 200ms限频账精确：2,073 calls = 479 samples +1,594 throttled；472 ordinary +7 room-entry force；五个战斗房首个真实hit均旁路。未触4,096额度。
- 严格命令`py -3 tools/check_lc2_statistics_cache_probe.py .../LogOutput.log --allow-no-rollover`退出0：raw damage realtime PASS；Boss、pipe均NOT_RUN。
- 0.4.26没有产生room_exit/round_end/final_sync探针样本。普通样本距下一room-entry存在尾差91、3、523，均在下一active中补齐；由于缺少真实房末force，rollover严格门保持NOT_RUN，不能签完整过程PASS。

## 作者人工伤害旁证

- epoch4作者报告两次早期飘字约573、564；官方cache最终1,139，人工第二数可能有读数误差，仅作旁证。
- epoch6作者总共普攻两次，第二次带溅射；首个611对应cache首样本612，后续可见约928/567，但最终本机cache稳定2,199。屏幕飘字不是完整官方结算口径，因此不用于公式拟合。

## 离队后R-FAIL

- 离队前最后正确party事件：`player-4 / slot3 / local / live=3338`。
- 作者先离开队伍再退出结算；全程没有新`session_started`，仍是原session。
- 离队后错误事件变为`player-5 / slot0 / local / live=45888`。45,888精确等于旧P1；P2=35,652、P3=41,555、三队友合计123,095，因此不是三队友求和。
- screenshot中游戏官方卡仍为3,338，而HUD显示45,888，证明官方cache未错，Bridge roster/live绑定错。
- 根因：`CapturePartyMembers`先按旧KnownPartyBySlot得到slot0=P1 live45,888，再因LocalPlayer native对象/Index变为slot0创建新token并把旧slot0值挂给本机；随后同一本机平台身份同时留在旧slot3和新slot0，日志出现identity collision1。
- toolbox只是忠实消费错误协议事件；内存正控证明若事件为同session稳定`player-4 / current slot0 / live3338`，Python/UI无需修改即可显示3,338。

## 下一修复合同

- 0.4.27过程候选发布`active + cache-list`；两张表均须覆盖全部历史human身份、唯一、非负、Boss≤总伤害，NPC可额外unmatched。
- 同session优先按平台身份HMAC复用匿名player token；身份暂缺时只有旧opaque token仍可证明同一对象才复用，否则整组拒绝。
- live按历史身份取得，但事件`player_slot`采用当前`Player.Index`；本例期望`player-4 / slot0 / live3338`。不得创建player-5或继承旧P1值。
- 在既有OnChangeRoomEnd Hook增加Prefix房末强制snapshot，不新增Hook target；用下一短局验证tail rollover。

## Not run

Boss、NPC、0.4.27真实运行、离队修复真实复测、final exact SyncEnd、fresh different-owner审计、commit、push、Release均未运行。
