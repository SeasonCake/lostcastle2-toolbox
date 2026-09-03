# 自动归档+手动导出源码UI候选

可见合同：主窗口右上角稳定显示“手动导出 → v1.6.3 → 启动游戏”，手动导出使用现有次级按钮样式和固定宽度；不改HUD、导航或主内容层级。

VisualIssueLedger：

- `UI-A01` 手动导出必须紧邻版本号且不抢主操作层级：CLOSED。MIN-A100与WIDE-A200均为手动导出在版本号左侧、启动游戏右侧。
- `UI-A02` 最小窗口/高DPI不能出现标题或操作重叠、截断、挤出：CLOSED。应用实际最小臂802×756，按钮76/76 px；高DPI臂1223×896，按钮130/130 px。
- `UI-A03` 默认/忙碌/失败标签必须保持同一固定按钮宽度：CLOSED（默认两臂截图；忙碌`导出中…`和失败`导出异常`由行为/源码合同覆盖，四字标签不改变width）。

证据：

- MIN-A100截图：802×756 / `BCD4AED635F2E503E73FFAFA874A0622DDFFFF618DB8841458F2F896412EBE15`；receipt `DDEE2994…6A7E6`。
- WIDE-A200截图：1223×896 / `372D2718C29CA63E6F1A83520ED0C1A4435ACE0265E7C104D66FF071331C4F0E`；receipt `9B2691ED…AE70C`。
- 两臂均绑定隔离config/archive目录；未启动游戏，未写真实包配置。

判定：`SOURCE VISUAL CANDIDATE VERIFIED`。
