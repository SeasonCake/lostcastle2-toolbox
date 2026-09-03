# r23 四人高延迟撤退样本

> lifecycle: `R-PASS realtime/owner/archive; SyncEnd NOT_RUN`

## 样本范围

- 2026-09-02，作者为四人房主并开启亚服/VPN，队友延迟明显；进入第 1 阶段后正常推进多个房间，随后由作者主动退出对局并看到撤退结算。
- 精确桌面候选：1.6.3，EXE `0CEF5EA44A623129ACAA75281B972DD2E9AEFFA084C28F9F86194F9138B80584`。
- 已安装 Bridge：0.4.28，`5482997836C1AA594C14C1E10D7858572655B2CB1EE57F9A1F18A57CC9BDA9D1`；三个可选 settlement target 均 `installed=true`。
- 作者随后点击“手动导出”并关闭游戏与工具箱；16:04:07 结构化进程查询为 0、unknown path 0，日志连续 2 秒大小/mtime 不变。

本样本证明高延迟与撤退路径下的局中实时、owner 链和手动归档；它没有触发 `SyncAdventureRecordDataEnd`，因此不能替代完整自然结算局。

## 决定性结果

### Statistics `active + cache` 实时过程

`tools/check_lc2_statistics_cache_probe.py` 严格四槽门 exit `0`：

- `raw_damage_realtime=PASS`
- 498 / 498 个有效样本，解析错误 0
- 7 个战斗房间，四个人类槽位 `0,1,2,3` 均发生变化
- 存在远端单独增长房间，也存在本机造成伤害房间
- 6 / 6 次房间 rollover 精确守恒
- `boss_realtime=NOT_RUN`：本次提前撤退前没有可判定 Boss 样本
- `pipe_e2e=NOT_RUN`：该 checker 只消费 Bridge 日志，不以此冒充桌面端最终验证

### 多人 owner / forwarded 链

`tools/check_lc2_multiplayer_probe.py --minimum-remote-slots 3 --allow-no-forwarded-remote-hit` exit `0`：

- settlement / registered / matched unique：`1845 / 1845 / 1845`
- 四槽事件：`206 / 1034 / 97 / 508`
- 四槽 owner match 与各槽 unique 完全一致
- duplicate callback conflict、owner conflict、unresolved 均为 0

### 归档

- 手动 ZIP：`2026-09-02_160258_手动_733B4DDD23.zip`
- 冻结副本：`post-exit/manual-archive.zip`
- 119,087 B / SHA-256 `B01481472DA18034B6A08ED8AE283E8573A9284A93FF1EBBF189E67F266FA348`
- `check_combat_archive_consistency`：PASS
- reason=`manual`，session key=`733B4DDD23`，2,688 个唯一事件，summary/events session 完全相同，成员、事件数、字节数与 digest 均通过

### SyncEnd / 最终官方值

`tools/check_lc2_settlement_final_probe.py --json` exit `2`，正确分类为 `NOT_RUN`：

- 三个 hook 安装门 PASS
- boundary / network record / complete SyncEnd 均为 0
- 唯一原因：`complete_sync_end_missing`
- 撤退过程中 party 可见成员由 4→3→1 折叠，但所有 `[LC2CB-OFFICIAL]` 均为 `final_ready=false`；未把过程值冒充官方结算
- 未生成自动 ZIP；作者手动导出后才得到上述同 session 合法归档

## 冻结证据

- 最终 `LogOutput.log`：708,418 B / `6D7D551FFCE78BEA3478B33232AA1EE4B61AC59E28A227D5D67E33C440501425`
- 手动 ZIP：119,087 B / `B01481472DA18034B6A08ED8AE283E8573A9284A93FF1EBBF189E67F266FA348`
- 退出 checkpoint partial 仍保留于冻结副本，供恢复路径对照；原工具箱下的 partial 未由本任务删除。
- fatal、queue overflow、schema error、非零 stack mismatch/read failure/identity collision/duplicate callback conflict：0。

## 结论与未运行

- 这次是有效的四人高延迟实时/owner/rollover/手动归档正控。
- 完整自然 SyncEnd、逐槽最终官方匹配、自动 final ZIP、完整局桌面 UI 运行链仍 `NOT_RUN`，发布门不因此放宽。
- 未提交、推送、打 tag、创建 GitHub Release 或发送 QQ 公告。
