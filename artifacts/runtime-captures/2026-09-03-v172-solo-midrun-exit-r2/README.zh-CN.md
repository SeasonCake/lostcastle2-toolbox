# v1.7.2 r2 单人中途退出实测

> lifecycle: `local-runtime-evidence / mid-run-exit / diagnostic-frozen / not-a-release-asset`

## 场景与结论

- 作者使用 `<desktop>/失落城堡2工具箱1.7.2-诊断候选-r2` 进行单人实测，在第3阶段中途退出冒险，随后关闭游戏和工具箱。
- 活动监测期间游戏、工具箱与 diagnostic Bridge 身份始终匹配；归档从约198 KiB持续增长到约3.3 MiB，未出现事件跳过、queue overflow、session/schema failure。
- 退出到营地触发了房末/回营生命周期，但没有收到 `session_ended`。归档摘要仍为 `live`、官方Damage/Boss均不完整；因此本局只能作为中途退出样本，不能签自然结算或官方值。
- 进程关闭边界出现一次 `transport reset: IOException`。它发生在回营之后，活动监测阶段为0；没有伴随致命session失败。本记录只把它归为关闭边界信号，不外推为所有退出路径都正常。

## 冻结证据

- 运行中通过盒子“导出诊断”生成一致的manual ZIP：4,915事件、3,336,701 B原始事件、未截断；ZIP 185,860 B，SHA-256 `A6419084759C3417BD529F534AA0C5BA4AE650274C70F4F07C8B6F10BB882AC8`。
- 游戏和工具箱连续确认为0后，只读复制最终partial到任务自有目录并从副本执行恢复；原partial未删除。最终recovered ZIP为4,935事件、ZIP 186,110 B，SHA-256 `8A0374BE95BDE6BEFF809730E07AE74AB22F147A2F59E92800901B2610BE052F`，一致性检查通过。
- 最终事件类型：`damage_resolution=1,908`、`resource_change=2,547`、`status=480`；状态含`session_started=1`、`room_started=27`、`party_updated=233`、`live=219`、`session_ended=0`。
- 冻结BepInEx日志为1,121,539 B，SHA-256 `A60E0223DB85317802A11ECABA1E63C1D5B420659E4051808CA6ACB9FE113339`；skip=0、fatal=0、退出后transport reset=1。原始日志与ZIP均由 `.gitignore` 排除，不进入公共提交。

## DPS 回放

- 最终4,935个事件全部由当前聚合器重放，ingest error=0；归档摘要的总伤害、Boss、个人伤害、承伤、回复、法力和最终sequence逐字段差异=0。
- 4,893个事件点具有完整live口径；team/personal均有4,461个正DPS采样，最大值均为10,007.4；负值、NaN或无穷DPS为0。
- 上述结果证明本次事件链可重放，未出现负DPS、非有限值或摘要双计；由于本局没有官方终局和独立逐秒官方DPS，它不证明绝对DPS与游戏结算完全一致。

## 开放项

- `MIDRUN-END-01`：中途退出回营没有发出`session_ended`，automatic ZIP未生成；本次由manual export与离线副本恢复保住证据。是否调整Bridge退出边界或归档关闭策略，需作为独立修复阶段处理。
- 下一局明确session开始后的状态清理尚未用本候选实测；自然SyncEnd、重连与官方终局仍为`NOT RUN`。
