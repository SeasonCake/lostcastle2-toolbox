# r23 双人自然 SyncEnd（含游戏侧符文异常）

> lifecycle: `diagnostic-evidence / accuracy-and-archive-contract-pass / clean-release-acceptance-not-run`

## 样本边界

- 2026-09-02，双人自然完整局，Bridge 0.4.28，正常 r23 桌面候选。
- 作者在局后报告自己的游戏符文出现异常；当前没有证据把该现象归因于工具箱或 Bridge。
- 因存在未归因的玩法异常，本局不作为干净的最终发布实战 PASS；保留为准确度、终局诊断和跨 session 归档证据。
- 作者随后建立第二个 session、尚未战斗；本目录的日志快照末尾包含该第二 session 的启动片段，不能把全日志直接当作单 run 输入。

## 冻结身份

- r23 EXE：6,501,036 B / `4C6C81B6C38EBDBEB0CA298950040D30499E183399B6B678C1C89286CE9EA544`。
- Bridge 0.4.28 DLL：98,304 B / `5482997836C1AA594C14C1E10D7858572655B2CB1EE57F9A1F18A57CC9BDA9D1`。
- `LogOutput.with-run2-start.log`：1,838,010 B / `EC73A7E478080975114C2C6C9BCA42282C3B1C71554ECFEAF7946A4AC4958A91`。
- `LogOutput.final.log`：1,883,142 B / `7325908A7667C22E94D6417940704BCEA9A54659FF7AEF41DA0621DADF0ADB58`；游戏与工具箱退出后的稳定完整日志。
- `auto-superseded-final.zip`：226,053 B / `34DD45A982CEAACEEC7F48A7ABE6668A0383E351B9EA41F50A32CE30D0F394B4`。
- `run2-empty-automatic.zip`：14,306 B / `535AB011C103056B14189382C22C3A27C42EB5B132D5D2963013E848F9B10190`。
- session key：`3B4698D42E`；session ID：`476157de55da4edd9a35c5ddaf07009e`。

## 决定性结果

### SyncEnd 与官方 final

`check_lc2_settlement_final_probe.py` 对冻结日志 exit `0`：

- hooks / sequence / payloads / sync_end / official_match 全部 `PASS`；
- parse error 0，3 个可选 target 全部安装，fail-open target 0；
- 7 个有序终局事件、5 个网络 record、2 个边界、1 个完整 SyncEnd；
- final run 1 / room epoch 26；2 个官方槽位、2 个映射槽位、mismatch 0。

官方逐槽结果：

- P1：damage 825,048 / Boss 258,019；过程观察值 750,867 / 224,471，final 向上校正 74,181 / 33,548。
- P2（本机）：damage 1,002,936 / Boss 179,429；过程观察值 1,168,246 / 205,359，final 向下校正 165,310 / 25,930。
- 团队官方 damage 1,827,984 / Boss 437,448。

该结果直接验证 final 可相对过程估算向上或向下覆盖，不能继续要求过程值与 final 完全相等。

### owner 与实时 Statistics

- owner 链本身 PASS：2,724 settlement unique = registered unique = matched unique；duplicate callback conflict 0；两槽 conflict / unresolved 均为 0。
- final official 映射 PASS：2 records / 2 expected slots / 2 identity matches / 2 published slots；identity unmatched/collision 0。
- 第二 session 建立前的 run1 检查：1,211 / 1,211 Statistics 样本，parse error 0；两个人类槽位均变化；25 / 25 rollover 精确；Boss realtime PASS。
- 本局没有“只由远端玩家造成伤害”的房间，因此严格独立样本门报告 `remote_only_room_missing`；前一 r23 四人样本已提供该正控。本项是样本覆盖缺口，不是已观察到的数值错误。

### 归档与 session 隔离

- 第二 session 启动时，上一局自动封存为 reason=`superseded`。
- `check_combat_archive_consistency` exit `0`：5,302 events；manifest / summary / events 均为同一 session `476157de55da4edd9a35c5ddaf07009e`。
- 第二 session 使用独立 session ID `889c8ab555f3460aa2fdb657e31812c3`，未混入上一局 ZIP。
- 第二 session 未战斗并在正常退出时自动生成 reason=`automatic` 的独立 ZIP：350 events、official complete=false；一致性 checker exit `0`，无 partial 残留。

## 四类回执

- **实际结果失败**：作者观察到游戏侧符文异常；根因与工具箱相关性均未确认，因此该局不是干净发布验收样本。
- **当时规则违规**：旧 `check_lc2_multiplayer_probe.py --require-final-official` 仍把过程值与 final 不相等判为失败，违反当前“官方 final 允许双向校正”合同；其 owner 与 final official 子门实际均 PASS。
- **后来新增教训**：一个游戏进程内可包含多个 probe run；冻结日志必须绑定 run，或 checker 必须支持显式 run 选择，不能把第二局启动片段误报为第一局失败。
- **规范落地后回归**：SyncEnd/official mapping、Boss、owner、rollover、同 session 归档与新旧 session 隔离均有正证据。

## Not run

- 无玩法异常的干净自然完整局；
- 本局完整 UI 最终画面截图与 pipe e2e；
- SyncEnd 当下立即生成 reason=`automatic` 的 ZIP（本局在下一 session 建立时以 `superseded` 封存）；
- final source/package/runtime fresh audit、commit、push、Release、readback 与 QQ 发布。
