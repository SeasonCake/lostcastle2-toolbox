# 工具箱 1.6.2 / Bridge 0.4.12 精确包 UI 验收

- 生命周期：`SUPERSEDED INITIAL CANDIDATE / DIFFERENT-OWNER RELEASE HOLD`。初审发现 A200 多人 HUD 的个人占比 bar 被裁切；不得用于最终放行。
- 精确 EXE：6,470,608 B / SHA-256 `ECC6A51EDA3F929DF610EC09FAA101489B2D6FCD60A27F9C907971AFDFF0647A`；FileVersion/ProductVersion 均为 1.6.2。
- 运行时清单：`232360AFD3C225E213C775BBACAFA51F1311B1F820954F7C96F6FDB60A12E630`；社区目录：`9EEEFD73A2EC5D29AC5FECFC034E3292F29F6071A59A123510D50DC817E255B3`。
- 每个 arm 的 `receipt.json`、`window-internal.png` 与进程命令行绑定到同一 EXE；截图均由对应 PID 的窗口直接捕获。

| arm | 窗口 | 截图 SHA-256 | 结论 |
| --- | ---: | --- | --- |
| MAIN-P4-A200-start | 1223×896 | `E78881A71D29C9D41C9905F432AAAF2A416FBCFC89358D27CEF377ED3C812549` | 4 人保持原四格布局，不显示横向滚动条 |
| MAIN-P5-A200-end | 1223×896 | `9CB156124CB9C5795E8D9963DCAAC33FB032B5AFE3C8AC2D84BEC29001F6734A` | 第 5 人可由滚动条到达 |
| MAIN-P16-A200-start/end | 1223×896 | `331E3D9A…D7500` / `640CEFAB…BD83D` | 首端自己+队友 1–3；末端队友 12–15，详情区不移动 |
| MAIN-P16-MIN100-start/end | 802×776 | `36FF351C…35FDB` / `3CCA3B82…C183D` | 100% 最小窗口可拖到末端，无裁切/重叠 |
| HUD-P4-A200 | 610×554 | `D0A21301…3E60F` | 4 人单列 3 张队友卡 |
| HUD-P5-A200 | 850×554 | `5656F3C0…6769` | 第 4 名队友从第二列顶部开始 |
| HUD-P8-A200 | 1090×554 | `03BDCF81…DA14` | 第 7 名队友从第三列顶部开始 |
| HUD-P16-MIN100/A200 | 1500×474 / 1570×554 | `4851DAA5…00845` / `C448FC8F…B511E` | 五列×三行完整显示 15 名队友；个人占比 bar 可见 |
| MOD-MAXP-MIN100/A200 | 802×776 / 1223×896 | `87FE5FF6…EBC75` / `59F1BC06…B5FB` | 默认 7 人 MOD 的名称、版本、作者、1–16 与客机卸载警告完整可读 |

像素审阅结论：主界面仅在人数超过 4 时出现横向滚动条；滚动不挤压个人来源明细。HUD 按列优先映射队友 1–15，主卡的“自己队伍占比”与房间/DPS 行互不覆盖。两档 MOD 页面均无文字、按钮或滚动区域裁切。
