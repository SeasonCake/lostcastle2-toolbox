# r23 Mini HUD 估算绿色差量验收

> verdict: `VERIFIED`

## 冻结身份与范围

- 作者指定变化：Mini HUD 普通“估算”由黄色改为绿色，避免被理解为警告。
- 保持不变：主窗口普通“实时估算”仍为琥珀色；Mini 的“有事件跳过”等真实降级仍为琥珀色；完整官方值仍为绿色并用“官方”文字区分。
- 精确 EXE：6,501,036 B / `4C6C81B6C38EBDBEB0CA298950040D30499E183399B6B678C1C89286CE9EA544`。
- `toolbox/app_shell.py`：`D636DBDFD8CB9F6A120CD943CDC4D775FA5D7EC309C2D485CD4CE4C26E84A399`。
- Bridge 未变：0.4.28 / `5482997836C1AA594C14C1E10D7858572655B2CB1EE57F9A1F18A57CC9BDA9D1`。
- 继承的完整布局合同：前一精确候选 `formal-readonly-r4` 已完成主窗口/HUD 100%–175%、空/降级/官方/error、4/16 人与滚动恢复的正式 `VERIFIED`；本轮源码差量只改变 compact estimate 的颜色选择。

## 差量矩阵

- Mini 普通估算：Tk 1.00 / 1.25 / 1.50 / 1.75，四人千万级值。
- Mini 降级：Tk 1.50，“估算 · 跳过”。
- Mini 官方：Tk 1.50，两人完整逐槽官方值。
- 主窗口：Tk 1.50 普通实时估算像素对照，确认仍为琥珀色。

`tk-check-hud-delta.json` 对六个绑定 PID/EXE/命令行/HWND/PNG/source 的 receipt 判定 `VERIFIED`，SHA-256 `2F485AE79B16DB5C16F41B014584328D1990F36C81D36E6E7C68B8B873D26DC7`。

## VisualIssueLedger

- `R23-UI-01..06`：保持 CLOSED，完整合同见 `formal-readonly-r4`。
- `R23-UI-07` CLOSED：Mini 普通“估算”使用绿色；此前黄色截图为 known-red，对应 `formal-readonly-r4/HUD-LARGE-P4-A150`。
- `R23-UI-07-N1` CLOSED：降级 Mini 仍为琥珀色，不把真实“跳过”状态伪装成正常。
- `R23-UI-07-N2` CLOSED：Mini 官方仍为绿色，但标签为“官方”，与绿色“估算”可由明确文字区分。
- `R23-UI-07-N3` CLOSED：主窗口实时估算仍为琥珀色，没有把完整页面的数据口径提示一并改掉。

## 像素证据

- 正常 Mini Tk1.50：`F94EBAE4…AC4EA1`，绿色“估算”。
- 降级 Mini Tk1.50：`28F5F523…1D2013`，琥珀色“估算 · 跳过”。
- 官方 Mini Tk1.50：`E315D02D…4E818F`，绿色“官方”。
- 主窗口 Tk1.50：`F5EBCD5F…1EE837F`，琥珀色“实时估算 · … · 结算可能校正”。

## 验收边界

本结论只证明精确 4C6C81… 候选的颜色与相关 Mini 几何/像素差量；战斗数值真实 SyncEnd、合规 public-core、独立发布审计与 GitHub/QQ readback 仍由主发布门判定。
