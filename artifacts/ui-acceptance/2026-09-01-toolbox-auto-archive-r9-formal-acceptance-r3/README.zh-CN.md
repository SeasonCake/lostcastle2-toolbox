# r9自动归档/手动导出正式Windows UI验收

## 冻结合同与身份

- 作者可见要求：盒子主窗口右上角版本号附近新增“手动导出”；保留既有标题、启动游戏、导航、战斗HUD和信息顺序。
- 精确候选：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装/失落城堡2工具箱.exe`，6,484,432 B / `AC96FB7D990A05984B121234A8DAD657BBDDC410CCA63BCAB5AAEE0AAF175D5B`。
- Git身份：`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66`，工作树为工作6/7连续未提交范围；验收未修改候选源码、测试或截图期望。
- 可见顺序固定为：`手动导出（或导出异常） → v1.6.3 → 启动游戏`。
- 已知正常参考：同项目r8精确包主窗口；本候选只在版本区左侧新增一个次级按钮，其余布局/文案/颜色未漂移。
- formal r1/r2保留为捕获编排红项：r1误用PowerShell自动变量，r2的PrintWindow在复杂战斗画布阻塞Tk；二者没有完整收据，不进入候选判定。r3改用工具既有`--screen`全窗口像素捕获，候选未修改。

## 非缩减VisualIssueLedger

- `UI-A01` 手动导出紧邻版本号、启动游戏仍为右侧主操作：CLOSED，六臂一致。
- `UI-A02` 最小尺寸与100/125/150/175/200% DPI无顶栏重叠、截断、越界或标题挤压：CLOSED。
- `UI-A03` normal/degraded/empty/large/archive-error状态不改变按钮宽度与顶栏层级：CLOSED。error臂显示`导出异常`，其actual/requested仍103/103。
- 未报告其他可见缺陷；问题账本未删除或改名。

## 冻结矩阵

| arm | PID / HWND | window | 按钮 | actual/requested | screenshot SHA-256 |
| --- | --- | --- | --- | --- | --- |
| MIN-A100 | 27900 / 2820654 | 802×756 | 手动导出 | 76/76 | `E2FD16E51C15B87AFDD784FEEE713F98B37B3D52D91FFAE652541B822D880C9D` |
| STD-A125 | 9008 / 1311664 | 1022×776 | 手动导出 | 85/85 | `AD2EE20DDD8B827F0EAF0A335CCA0E231FD5ECE7B72B80A5D4FF6949FCB13429` |
| LARGE-A150 | 28504 / 1836436 | 1122×836 | 手动导出 | 103/103 | `DDB0017F86AFB67A213454296284E3AC8AF7356F4C4309012D131A6EA575C8D8` |
| DEGRADED-A175 | 1672 / 1115774 | 1172×876 | 手动导出 | 112/112 | `22C1B798F8E84C88709ACBC378BF53AAC2C1C50DA4C24D7FEDA9DD1222082E57` |
| EMPTY-A200 | 11540 / 1181310 | 1223×896 | 手动导出 | 130/130 | `8B1FC86F263F56C9D2B7E63957243F050046756E520697C0EB069467F64805D6` |
| ARCHIVE-ERROR-A150 | 31792 / 1443198 | 1122×836 | 导出异常 | 103/103 | `8DBD3C1A7CD0D82E99F224DC550D5B1DA0672CB4FF7A6C69E168D87A8E06E425` |

- 六个receipt均绑定上述精确EXE、完整命令行、PID/HWND、窗口标题、截图时间/bytes/hash/dimensions。
- `check_tk_receipt.py --required manual_export --required app_version`：六臂全部`VERIFIED`，输出`tk-check.json` / `DFF3B58859E656FC72CABBF4714AC796AE6A5D19EE47B4FC4EFAD1A4920D0022`。
- 像素复核：标题/按钮/版本基线一致；大数战斗页、degraded橙色状态、empty等待态与红色归档错误态均无额外控件漂移、截断或越界。

## 测试分类与未运行

- 几何/来源：Tk receipt checker六臂VERIFIED。
- 像素/UI合同：六张全窗口截图人工复核VERIFIED。
- 功能：pytest219+37、包形命名管道自动归档E2E、手动导出成功/失败/重复点击测试；功能绿不替代上述UI证据。
- `NOT RUN`：真实游戏自然结算后的r9自动归档、手动按钮由作者实际点击；不要求专门长局或野队团灭。

最终生命周期判定：`VERIFIED`。
