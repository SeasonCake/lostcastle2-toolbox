# 工具箱 1.6.2 / Bridge 0.4.12 精确包 UI 复核候选

- 生命周期：`VERIFIED / RELEASE PASS`。同一 different-owner 审计席位已关闭 `HUD-SELF-SHARE-BAR-01`，其他 ledger 项未重开。
- 精确 EXE：6,470,904 B / `EBFF95843F05F3164EE1D040301B7711526DE85C6BD7CFBC29526B52723F0025` / 1.6.2。
- 13 个 arm 的 receipt、截图、进程、窗口与 source identity 全部绑定该 EXE；主界面与 MOD arm 像素保持不变。

## HUD-SELF-SHARE-BAR-01 修复

- 已知 red：旧 exact EXE 的四个 HUD A200 arm 中，`self_share` 仅 14 px 高，低于 requested 27 px；文字被裁切，bar 消失。
- 当前修复：HUD 外框保持 P4 `610×554`、P16 `1570×554`，不增加总高度；多人 recent 卡在高 DPI 时从底部现有空白中获得额外高度，完整容纳占比文字和 bar。
- 当前四个 A200 arm 的 `self_share` 均为实际 27 px / requested 27 px；P16-MIN100 为 17/17 px。
- skill receipt checker 对 HUD-P4/P5/P8/P16-A200 与 HUD-P16-MIN100 的 `dps`、`room`、`self_share` 全部 `VERIFIED`。
- 像素审阅：金色个人占比 bar 清晰可见；recent 卡下沿向下利用原底部空白，外框尺寸、房间、DPS、队友卡和五列映射无漂移。

| arm | 窗口 | 截图 SHA-256 |
| --- | ---: | --- |
| HUD-P4-A200 | 610×554 | `67AD3A617575C8C99FE68C05C271B597F87422606E77B6B3E4B20EFF069E61F1` |
| HUD-P5-A200 | 850×554 | `6CCF85CED76CFE0D1DD6BBAF0BFCE59D5285DA66237B602274CCFF4EAC8E3B87` |
| HUD-P8-A200 | 1090×554 | `35BE5CEA1F9045A7185268542D6E77300341D9A66608A0C47D5B13ED7197C0E9` |
| HUD-P16-MIN100 | 1500×474 | `4851DAA555B635AEEBF07C98C7E3E9ECEB9E37FDAB71A4D9A3E14D2EB1A00845` |
| HUD-P16-A200 | 1570×554 | `9DFC57393EF92BACB02A2DAB26FBA91ABBE61DEAD675B5DD4425B8B7668FE24D` |

主界面六臂继续闭合 P4 无 bar、P5/P16 可拖动首尾及 MIN100；MOD 两臂继续闭合默认 7 人用途、1–16 与加入别人房前卸载警告。完整 arm 证据位于本目录各子目录。
