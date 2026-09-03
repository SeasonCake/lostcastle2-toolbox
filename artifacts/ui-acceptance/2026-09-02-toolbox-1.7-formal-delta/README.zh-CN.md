# 失落城堡2工具箱 1.7 正式 UI 差量验收

> verdict: `VERIFIED`

## 冻结身份

- 候选目录：`失落城堡2工具箱1.7`，不含测试 rxx 后缀。
- EXE：6,485,470 B / `BDC3462A223F808708711C956ADFB2C7291FCD3595C2A3E5ECA9F7FE032C89E9`。
- `keyview.py`：`166FB595F61B63F2627C6FF5458D9A2ED4778DA37548E6AD302CAAADAE0ED7B3`。
- `toolbox/app_shell.py`：`99E7A893B795B79E4E0D79A8BEB8BBF75EB24BAF1008E24B443BECBB91DA13C9`。
- runtime manifest：`C8D7AFA258FC17C9D17EFDCBE08AB76ED309094D46A142C461409E6F9C17B21F`。
- Bridge 1.7.0：98,304 B / `3A346E29F8A7737F3C32716990ABBCB0248A0656C2FB8E28FAF888996A4A1C75`。

所有正式 receipt 均绑定精确 PID、EXE、命令行、HWND/窗口标题、候选资产哈希、截图字节/尺寸/哈希和标签几何。本目录是本地验收证据，不进入公开 release stage。

## 冻结可见合同

- `UI-17-01`：主窗口顶部不再出现测试用“手动导出”；只保留 v1.7 与“启动游戏”。
- `UI-17-02`：Mini HUD 普通状态使用绿色“实时”；降级状态使用琥珀色“实时 · 跳过”；完整 final 使用绿色“官方”。
- 详细主界面继续使用“实时估算 · … · 结算可能校正”，不把过程值描述成必然等于 final。
- 继承上一精确候选已验证的主窗口/HUD布局；本轮文案均为等长二字差量，仍重新检查 100%–175% 和千万级四人值。

## 正式矩阵

`check_tk_receipt.py` 对以下冻结 receipt 全部判定 `VERIFIED`，完整截图像素复核无裁切、重叠或错误层级：

- `HUD-LIVE-A100-R2`：绿色“实时”，580×474；
- `HUD-LIVE-A125-R2`：绿色“实时”，580×484；
- `HUD-LIVE-A150`：绿色“实时”，580×494；
- `HUD-LIVE-A175`：绿色“实时”，595×529；
- `HUD-DEGRADED-A150`：琥珀色“实时 · 跳过”，580×494；
- `HUD-OFFICIAL-A150-R3`：绿色“官方”，双人向上/向下 final 正控，580×494；
- `MAIN-LIVE-A150-R2`：v1.7、无导出控件、琥珀色“实时估算/结算可能校正”，802×776。

## VisualIssueLedger

- `UI-17-01` CLOSED：正式 header 未创建或显示导出按钮。
- `UI-17-02` CLOSED：Mini/详细/降级/官方文案与颜色分层符合作者选择。
- `CAPTURE-17-01` CLOSED AS HARNESS：最初 100%/125% 采集在 HUD 建立前按 PID 捕获，`window not found`；改为等待精确标题后通过。
- `CAPTURE-17-02` CLOSED AS HARNESS：`PrintWindow` 在主窗口与首次官方臂造成 receipt 缺失；保留失败 arm，改用 screen pixels 后相同候选通过。失败采集未冒充产品红项或 PASS。

## 边界

本 verdict 证明上述精确 1.7 候选的可见差量、几何和状态文案；不替代纯净依赖安装、真实游戏启动、源代码/包综合审计、第三方外发裁决或 GitHub/QQ群 readback。
