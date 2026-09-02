# LC2 工作7 r10归档边界入口（2026-09-01 Asia/Shanghai）

> r10归档边界PASS，但真实第二局被旧closing门阻断；当前由`docs/LC2_WORK_7_R11_NEXT_RUN_RESET_CHECKPOINT_2026-09-01.zh-CN.md`接续。

## 当前身份

- Git：`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66`，工作树仍为工作6/7连续未提交范围；不得reset/clean、commit、push或Release。
- 游戏Bridge保持0.4.19 / `03BD7A7057C4408A475626E57AA2B4F99594E769AB6FC069CF9AE0366646C06D`，本次不改游戏DLL。
- 桌面r10：`<desktop>/失落城堡2工具箱1.6.3-自动归档修正版-r10`。
- r10 EXE：6,485,067 B / `1D05A4EAF829A439D854B7DF9AEF9163AE0167343FE2AF35ED16FC85FE1E9637`；1,761文件、166目录、166,671,530 B、config0，与项目包逐文件差异0。

## r9真实R-FAIL

- r9在旧ended Bridge重连期间把74条孤立session_ended各自封存为ZIP；74档总计89,176 B、同session key、每档1事件。
- 新游戏Bridge未进地图先发foreign session_ended，聚合器因只允许foreign session_started切换而SessionMismatchError；HUD从启动即异常且0，当前局未建partial。
- 用户截图中的单人续局卡46,296/13击杀不能与0 HUD比较。冻结证据：`artifacts/runtime-captures/2026-09-01-r9-orphan-session-ended-archive-storm/`。
- 用户原74个ZIP保持未删除；冻结副本已保存。

## r10规则与门

- 无active partial的孤立session_ended直接忽略；已自动finalized session的迟到事件不重开。
- recovered partial不算最终封存；盒子重启后同session仍可继续采集新段。
- foreign session_started或session_ended均为显式边界并reset；其他foreign事件继续fail closed。
- pytest223+37；build内unittest223；包self-test/runtime正负控PASS。
- 精确包74条旧结束回执+新局start/end E2E：仅1个新局ZIP、2 events、ended summary、partial0；HUD不为异常。

## 作者下一步

- 改用r10，只需启动盒子和游戏；确认HUD不再“上来就异常”，归档目录不再每2秒新增ZIP。
- 有实时数据后点一次手动导出，继续打几下确认采集不中断。无需完整长局、团灭或队友配合。
- r9原74个重复ZIP可以删除，但当前任务未代作者删除。

真实r10短冒烟前不做different-owner最终审计、commit/push/Release；三个新MOD仍只读预备。
