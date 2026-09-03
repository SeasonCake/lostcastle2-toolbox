# r23 发布候选正式 Windows/Tk 验收

> verdict: `VERIFIED`

## 冻结身份

- 桌面候选：`<desktop>\失落城堡2工具箱1.6.3-发布候选-r23`。
- EXE：6,501,024 B / `0CEF5EA44A623129ACAA75281B972DD2E9AEFFA084C28F9F86194F9138B80584`。
- `toolbox/app_shell.py`：`96B365C2EE7723CA7980803113B95BF91820524F47DEC49E38741968850A93D9`。
- Bridge 0.4.28：98,304 B / `5482997836C1AA594C14C1E10D7858572655B2CB1EE57F9A1F18A57CC9BDA9D1`。
- 宏界面源码仍与 r22 正式已验候选逐字节相同：`C96F79E2…98F4CD`。
- 所有 receipt 均绑定候选 PID、完整 EXE 路径、命令行、HWND/标题、源文件哈希与 PNG 字节/尺寸/哈希；每个状态臂使用独立配置、归档和 inbox，未污染桌面候选。

## 冻结矩阵

- 主战斗页：Tk 1.00 / 1.25 / 1.50 / 1.75，最小受支持窗口，4 人千万级值。
- HUD：Tk 1.00 / 1.25 / 1.50 / 1.75，4 人千万级值。
- 状态：空/断开、实时估算、事件跳过、完整官方结算、schema 错误。
- 扩展人数：16 人主页面和 16 人 HUD；主页面滚动至末端。
- 4 人窄窗：默认端与滚动末端各一张完整窗口证据；2 人官方结算负控确认不出现无效横向滚动条。

三组 Tk receipt checker 均为 `VERIFIED`：

- `tk-check-main-populated.json`：`CFB62BD0…D95E72`
- `tk-check-main-empty-error.json`：`D0386760…93F527`
- `tk-check-hud.json`：`48485E13…83D802`

## VisualIssueLedger

- `R23-UI-01` CLOSED：局中主页面显示“实时估算 · … · 结算可能校正”，HUD 显示“估算”。
- `R23-UI-02` CLOSED：完整逐玩家 official 后显示绿色“官方结算”，并原样显示向上/向下校正后的值。
- `R23-UI-03` CLOSED：空、断开、延迟、error 和事件跳过不被估算标签遮蔽。
- `R23-UI-04` CLOSED：旧候选 Tk1.50 的 `combat_totals` 为 `10/26px`；本候选为 `26/26px`，像素无底边裁切。
- `R23-UI-05` CLOSED：旧候选 HUD Tk1.25/Tk1.50 的 `self_share` 为 `19/22px`、`4/23px`；本候选为 `22/22px`、`23/23px`。
- `R23-UI-06` CLOSED：恰好 4 人且卡片放不下时显示横向恢复条，滚动末端完整显示 P4；2–3 人不显示无效滚动条，5–16 人继续可滚动。

## 关键像素证据

- 4 人 Tk1.50 默认：`691A1F0E…F5A5A9`（前一候选 known-red 类别已关闭；本轮同状态 receipt/checker green）。
- 4 人 Tk1.50 滚动末端：`A61FBFB3…35BB5`，P4 完整可见。
- 2 人官方结算：`E2FCCF68…FD1A51`，无无效横向滚动条。
- 4 人 HUD Tk1.50：`6B4738C1…58AE3F`，本机占比和进度条完整。
- 16 人主窗口：`723C0219…2A585`；16 人 HUD 也完成全窗口像素检查。

## 验收范围

本结论只证明上述精确候选的 Windows/Tk 可见合同与几何/像素矩阵；不替代战斗数值的真实多人运行验收、第三方再分发许可审查、源码/包/运行时独立审计或公开发布 readback。
