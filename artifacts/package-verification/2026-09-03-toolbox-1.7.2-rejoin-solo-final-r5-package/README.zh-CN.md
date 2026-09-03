# v1.7.2 重进与单人结算 r5 诊断候选回执

> lifecycle: `diagnostic-candidate-built / desktop-copy-frozen / bridge-deployed / runtime-not-run / distribution-not-built`
>
> recorded: `2026-09-03`

## 修复范围

- `REJOIN-SEED-01`：插件进程第一次激活的 session 可接收完整、唯一身份映射的非零 live 向量，恢复正在进行的对局总量；首样本只建立 DPS 基线，不制造历史累计尖峰。后续同进程新局仍要求零基线，避免上一局残留冒充新局数据。
- `SOLO-FINAL-01`：保留多人 network SyncEnd owner；单人新增 `GameSettlementUI.SetSettlementData`、`UpdateSettlementInfo` 与 `GameOverEnd_Offline` 三个实际 UI 阶段的幂等入口。只有 Bridge session 活动、历史 party 恰为 1 人且既有最终身份完整性门接受全部记录时，才发布 official 并结束 session；失败撤回 final-ready 并恢复 live。
- Bridge 插件版本提升为 1.7.3；应用版本仍为 1.7.2 诊断候选。社区 MOD 刷新内容与 r4 相同。

## 构建与验证

- 聚焦聚合/Bridge/结算 checker/构建合同：127 tests PASS；标准产品门：324 tests PASS。
- Bridge 两档 Release 均为 100,352 B、0 warning / 0 error、PDB/本机路径 0：
  - Diagnostic SHA-256 `DF02CD2B434A01B471C840176DE0CDDD0D52FF619562A32765D72147ACDA719D`；
  - Distribution SHA-256 `81252C4B45C317B76271D8D80BAE4B089D46BCCF3A52075DD48F9ADE85DB82E4`。
- 无 BepInEx 隔离游戏首次初始化、重复初始化、控制台关闭、社区 MOD 不自动启用与冲突 core 写前阻断均通过。
- 包内 EXE `--self-test` exit 0；60/60 社区 MOD 的包形安装、状态识别、卸载通过，卸载后遗留文件 0。

## 候选身份

- 项目包：`<repo>/package/失落城堡2工具箱1.7.2-诊断候选-重进与单人结算-r5`。
- 桌面副本：`<desktop>/失落城堡2工具箱1.7.2-诊断候选-重进与单人结算-r5`。
- 两份目录均为 1,770 个文件、167,019,441 B，规范化逐文件树摘要均为 `122531FCB0FA6B593E45C74834464E8EE581E98ADD23558A4382A2769E8DCA42`。
- EXE：6,508,585 B，SHA-256 `9C14CC7241D684FBA3C7F3B1BB849EE83947A2BE6E0267B79A97A4806E83DB87`。
- 社区目录：60 条、61 个功能文件、3,665,869 B，包内登记数量与载荷数量一致。
- 包内 `.cfg`、日志、partial、PDB、导出目录与测试数据均为 0；维护者用户名、工作区绝对路径、联系方式、r4 实测目录与截图名的字节扫描均为 0 命中。

树摘要按相对 POSIX 路径不区分大小写排序，依次散列 `相对路径\0大小\0文件SHA-256\n` 的 UTF-8 字节。

## 边界

- 合成正控证明非零 live 首样本立即恢复 `3,662,617 / 684,177` 且 DPS 为 0，下一增量才计速；这不是实际游戏复测。
- 三个单人 UI Hook 已由当前 interop 元数据和真编译证明存在且可引用，但实际哪一个首先命中、最终记录当时是否完整仍需真实单人结算正控。
- Distribution 包、commit、push、tag、Release 与群分享均未执行。
