# 项目演进档案

本目录把失落城堡2工具箱从早期宏与单人统计，到多人实时数据、自动运行环境、社区 MOD 管理和 v1.7.1 的工程记录串成一条可复用证据链。

这些文档是时间点记录，不自动代表当前代码、发布状态或仍然有效的待办。判断当前行为时，优先读取源码、测试、当前发布说明和最新构建回执。

## 公开与脱敏约定

- 保留版本号、`rxx` 测试批次、失败结论、关键数值、修复思路、正负控制、哈希与验收方法。
- `<repo>`、`<workspace>`、`<game>`、`<desktop>`、`<local-mod-library>` 是本机位置别名；公开记录不保存个人用户名或绝对路径。
- 明确来自程序、源码或随包说明的作者署名可以保留；维护者确认的社区上传别名可作为来源，但不得冒充作者，也不公开联系方式或账号标识。
- 原始日志、截图、ZIP、配置、聊天、平台账号、昵称、网络地址和未经筛选的运行转储不进入本目录。
- `PASS`、`FAIL`、`NOT RUN` 只在原记录限定的版本、样本和检查面内有效。

## 建议阅读顺序

1. [版本时间线](TIMELINE.zh-CN.md)：快速理解每轮为何发生、解决了什么、又暴露了什么。
2. [可复用工程经验](LESSONS.zh-CN.md)：把本项目的调试、测试、UI、打包和隐私做法抽象为其他项目也能采用的方法。
3. [总体架构](../ARCHITECTURE.md)：查看当前模块边界、事件模型、统计口径与第三方载荷原则。
4. [运行时参数与调试索引](../LC2_RUNTIME_PARAMETER_DEBUG_INDEX.zh-CN.md)：按症状、字段、Hook 和版本定位具体实现。
5. [v1.7.1 发布说明](../LC2_1.7.1_RELEASE_NOTES_2026-09-02.zh-CN.md)：查看当前群分享版本的 MOD 增量、验证结果与边界。

## 原始设计与早期验证

- [宏与实时伤害模块计划](../PLAN_macro_damage_2026-08-26.zh-CN.md)
- [启动性能三臂实测](../LC2_STARTUP_PERFORMANCE_2026-08-27.zh-CN.md)
- [本地 MOD 总库清点与接入边界](../LC2_MOD_LIBRARY_INVENTORY_2026-08-28.zh-CN.md)
- [下一桌面版本计划与 UI 问题账本](../LC2_NEXT_DESKTOP_VERSION_PLAN_2026-08-28.zh-CN.md)
- [MOD 署名与多人伤害统计调查](../LC2_MOD_AUTHOR_AND_MULTIPLAYER_DAMAGE_RESEARCH_2026-08-29.zh-CN.md)
- [v1.6 收口计划](../LC2_V1_6_RELEASE_PLAN_2026-08-29.zh-CN.md)
- [v1.6.1 候选判定](../LC2_1.6.1_CANDIDATE_VERDICT_2026-08-30.zh-CN.md)

## 多人准确度与会话生命周期

- [工作6交接：多人归属与 MOD/UI 候选](../LC2_WORK_6_HANDOFF_2026-08-30.zh-CN.md)
- [工作7交接](../LC2_WORK_7_HANDOFF_2026-08-31.zh-CN.md)
- [工作7多人准确性证据链](../LC2_WORK_7_MULTIPLAYER_EVIDENCE_2026-08-31.zh-CN.md)
- [r7 短房正控](../LC2_WORK_7_R7_SHORT_CONTROL_2026-09-01.zh-CN.md)
- [r8 被动自然结算](../LC2_WORK_7_R8_PASSIVE_FINAL_CHECKPOINT_2026-09-01.zh-CN.md)
- [r9 自动归档实验](../LC2_WORK_7_R9_AUTO_ARCHIVE_CHECKPOINT_2026-09-01.zh-CN.md)
- [r10 归档边界](../LC2_WORK_7_R10_ARCHIVE_BOUNDARY_CHECKPOINT_2026-09-01.zh-CN.md)
- [r11 新局归零](../LC2_WORK_7_R11_NEXT_RUN_RESET_CHECKPOINT_2026-09-01.zh-CN.md)
- [工作7重启检查点](../LC2_WORK_7_REBOOT_CHECKPOINT_2026-08-31.zh-CN.md)
- [工作8交接：实时值与官方值分层](../LC2_WORK_8_HANDOFF_2026-09-01.zh-CN.md)
- [r15 live/official 合同](../LC2_WORK_8_R15_LIVE_OFFICIAL_CHECKPOINT_2026-09-01.zh-CN.md)
- [r18 结算缓存探针](../LC2_WORK_8_R18_SETTLEMENT_CACHE_PROBE_CHECKPOINT_2026-09-01.zh-CN.md)
- [r19 限频缓存探针](../LC2_WORK_8_R19_THROTTLED_CACHE_PROBE_CHECKPOINT_2026-09-01.zh-CN.md)
- [r20 Statistics cache-list 实时过程](../LC2_WORK_8_R20_STATISTICS_CACHE_LIVE_CHECKPOINT_2026-09-01.zh-CN.md)

## UI、宏、MOD 与发布收口

- [v1.7.1 社区 MOD 增量收录](../LC2_1.7.1_MOD_INTAKE_2026-09-02.zh-CN.md)
- [v1.7 正式发布说明](../LC2_1.7_RELEASE_NOTES_2026-09-02.zh-CN.md)
- [宏直接录入与可读性验收](../LC2_MACRO_DIRECT_KEY_UI_R1_CHECKPOINT_2026-09-01.zh-CN.md)
- [发布后 MOD 收录队列](../LC2_POST_1.6.3_MOD_INTAKE_BACKLOG_2026-09-02.zh-CN.md)
- [r23 实时准确度与公开发布合同](../LC2_R23_RELEASE_ACCURACY_CONTRACT_2026-09-02.zh-CN.md)
- [工作9交接](../LC2_WORK_9_HANDOFF_2026-09-02.zh-CN.md)
- [r23 正常发布冻结](../LC2_WORK_9_R23_FINAL_FREEZE_2026-09-02.zh-CN.md)
- [累计检查点](../LC2_CURRENT_HANDOFF_2026-08-28.zh-CN.md)

## 公开证据摘要

- [短测与验收摘要](EVIDENCE_SUMMARY.zh-CN.md)

公开摘要只保留版本、样本类别、关键计数、PASS/FAIL/NOT RUN 与结论。大体量、含本机状态或可能包含身份信息的原始证据由维护者本地保管，不作为公开发布物。
