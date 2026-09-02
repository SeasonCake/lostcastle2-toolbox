# Bridge 0.4.10 可恢复事件候选部署

- 部署时间：2026-08-30 22:09 +08:00。
- 生命周期：`SOURCE/BUILD/PACKAGE/DEPLOY/UI PASS / REAL MULTIPLAYER NOT RUN`。
- 候选 DLL：52,224 B / `B27FC892719F289CAD4AD94B7FFC33C348647310DF73C7B39F3E27A66F7CB0FA`。
- 候选 PDB：23,008 B / `2BC7C28A75F6ABDBB9B73FC58C12854D9D20CB7846E3647DEDB4B7E8C70D564F`。
- 回滚 0.4.9：51,712 B / `18228F2E5EB91B22AFD6AE6F8F97B968F4734B99794E4BD45FEC8BFFB76E8161`。

## 部署门

- 22:09:25 与 22:09:36 两次 exact name + `ExecutablePath` 检查中，游戏和工具箱进程均为 0。
- 先冻结游戏目录 0.4.9 DLL/PDB，再替换 0.4.10；部署后 DLL/PDB 与构建输出逐字节回读一致，进程仍为 0。

## 包与 UI

- 新桌面盒：`<desktop>/失落城堡2工具箱1.6.2-多人稳定性测试版`。
- 1,760 文件、166,613,214 B、config0；EXE 6,466,970 B / `D81E9B1D89711569B8C0448603341E92890854F94DAC4E172EC72797BBC505C8`。
- runtime manifest `F47D6D581FA5FDB8777CF8242DEF8AC8FACD7D44649B587A6CED7A728EC80BF3`；内置 Bridge 与游戏目录均为 `B27FC892…7CB0FA`。
- 全量 178 项、包形运行时/MOD 与桌面 self-test PASS。
- 200% 四人客机槽位2降级 HUD：回执绑定精确进程与窗口，尺寸 610×554；画面 `56515FAF…CFFB5`。状态“实时 · 有事件跳过”实际宽 163、文本测量 157、高 30，无裁切或与隐藏按钮重叠。

## 下一实测

无需再为 0.4.9 盲打完整局。下一次自然多人局只看三点：

1. 不再出现红色“异常”并永久冻结；若单事件失败，应显示黄色“实时 · 有事件跳过”且数字继续增长。
2. BepInEx 日志若出现 `Combat bridge event skipped: <code>`，保存 code；它说明局部丢一事件而非整局停止。
3. 若仍出现红色“异常”，日志现在必须给出致命原因，重点检查 `queue_overflow`，再做针对性修复。

本部署不授权 commit、push、tag 或公开 Release。
