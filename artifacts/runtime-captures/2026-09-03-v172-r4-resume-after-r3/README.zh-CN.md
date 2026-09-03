# v1.7.2 r4 单人跨重启续玩与自然结算证据

> lifecycle: `captured / REJOIN-SEED-01 confirmed-fail / SOLO-FINAL-01 confirmed-fail / fix-not-started`
>
> recorded: `2026-09-03`

## 样本边界

- 作者先以 r3 开始单人对局，在第一阶段中途退出；随后启动 r4 续接同一游戏进度。
- r4 继续至最终城堡阶段后，作者再次明确退出游戏并重新进入，以验证游戏进程重启后的续玩行为；工具箱进程未退出。
- 第二次重进后完成法师塔最终 Boss，并出现明确游戏结算卡。该样本不是从零开始的完整 r4 对局，因此只用于跨重启连续性和单人结算触发，不外推干净完整局的全部过程统计。
- BepInEx 日志确认本局只加载 `LC2 Combat Bridge 1.7.2`，没有加载社区 MOD。

## 三段证据

### A：r3 起始段

- 冻结 partial：224 条事件、132,313 B，未截断，事件 ID 224/224 唯一且只有一个 session。
- `events.jsonl` SHA-256：`CCFD83086233F2567588DC54FA103B1E84B6C53666E8B6854A499B4BD8771271`。
- 224/224 条事件重放成功，数值摘要差异 0；仅 `connection_state` 因退出后的断线状态没有对应事件而为 `summary=disconnected / replay=live`。
- 退出时个人总伤害 17,217、Boss 0、受击承伤 0。

### B：首次以 r4 续接，第二次退出前

- 工具箱在第二次重进时把旧 partial 自动封存为 `superseded` 恢复 ZIP；ZIP 300,547 B，SHA-256 `04A87C4536D4532D82BA66B5EB5B072A2F3947EACCD10AF30D9F34322543B2F5`。
- 8,520/8,520 条事件通过归档一致性检查并全部重放，摘要关键字段差异 0，未截断。
- 退出前盒子摘要：总伤害 4,002,225、Boss 684,177、受击承伤 757。

### C：第二次重进至自然结算

- 手动诊断 ZIP：463,923 B，SHA-256 `EE5FBB81D4C3BF85A9BFEEB5C9D846F33D36C855BF7DA8FA744045FF343B3890`。
- 16,456/16,456 条事件通过归档一致性检查并全部重放；10,578,669 原始事件字节，未截断，摘要关键字段差异 0。
- 最终 BepInEx 日志：1,964,195 B，SHA-256 `24C2F810182E56AC792CECE99DBD0C44BDFFB19527EC46F390A9F9B3A5FF062C`。
- 用户结算截图：1,400,079 B，SHA-256 `593A7A0BF4E1480DCB7604598839A74AAA1BAA919DCC098109FBF7F02AF1B9DF`。截图含游戏昵称，只作本地私有证据，不进入公开文档或发布包。

## 结算差值

| 字段 | 游戏官方结算 | 盒子最终 HUD | HUD - 官方 | 解释 |
| --- | ---: | ---: | ---: | --- |
| 总伤害 | 10,619,575 | 6,964,256 | -3,655,319 | 少 34.4206%；主要缺失第二次重进时未注入的历史累计 |
| Boss 伤害 | 3,466,900 | 3,945,311 | +478,411 | 缺历史 Boss 基线与逐击 fallback 高算同时存在，净值表现为高 13.7994% |
| 承伤 | 1,562 | 805 | -757 | 第二次退出前盒子恰好已累计 757；`757 + 805 = 1,562`，确认重进后承伤从零重新累计 |

游戏日志中的 Statistics live active 首次值为 `3,662,617 / 684,177`，最终值为 `10,619,575 / 3,466,900`，后者与截图官方总伤害/Boss 逐字一致。重进后官方增量应为：

- 总伤害：`10,619,575 - 3,662,617 = 6,956,958`；盒子逐击 fallback 为 6,964,256，高 7,298。
- Boss：`3,466,900 - 684,177 = 2,782,723`；盒子逐击 fallback 为 3,945,311，高 1,162,588。

因此不能把当前 HUD 的净差简单解释成“只漏了旧值”：重启还使盒子失去完整 live 校正，退回逐击口径，Boss 高算同时重新出现。

## 已确认根因与触发链

- Bridge 能按匿名身份从游戏 Statistics 读到完整非零累计，日志持续显示 `live_identity_matches=2`、碰撞/未匹配/读取失败均为 0。
- 但当前 `CaptureLiveOfficialDamageTotals()` 要求每个新 Bridge session 的首个完整 live 向量必须全零；第二次重进的首值非零，所以 `_liveOfficialBaselineReady` 永远不置位，完整 live 不进入 `PartyMemberSnapshot`。
- C 段只有 1 个 `party_updated` 事件，其中带 `live_damage` 的事件为 0；最终摘要同时为 `live_damage_complete=false / live_boss_damage_complete=false`。桌面只能从重进后的逐击重新累计。
- 聚合器已经把首个 live 样本作为 DPS 基线而不制造差分尖峰，因此修复方向应是允许“明确新 Bridge session + 完整唯一身份映射”的首个非零 live 向量作为总量种子，同时继续由桌面首样本抑制 DPS 尖峰，而不是丢弃该向量。

判定：`REJOIN-SEED-01 = CONFIRMED FAIL`。

## 单人终局触发

- 日志明确出现一次 `round_end_preload_camp`，随后进入 camp；与作者看到结算卡一致。
- 三个 network settlement 探针均安装成功，但 `kind=record`、`kind=boundary`、`final_accepted=true`、`session_ended` 均为 0。
- r3 新增的 `[LC2CB-LOCAL-FINAL]` 也为 0，证明 `StatisticsMgr.OnGameSettlementSyncEnd` 不是本局实际执行的单人结算入口，或当前 Harmony 目标没有覆盖实际重载/调用路径。
- 没有自动归档，只能由作者点击手动导出保全 C 段。

判定：`SOLO-FINAL-01 = STILL FAIL`。

## 后续边界

- 本记录只确认缺陷和最窄修复方向；源码修改、r5 构建、部署与复测尚未开始。
- r5 至少需要两个独立正控：中途退出重进后首个非零 live 种子恢复完整总量且 DPS 不尖峰；单人自然结算实际入口命中并发布完整 official/session-ended。
- commit、push、tag、Distribution、Release 与群分享均未执行。
