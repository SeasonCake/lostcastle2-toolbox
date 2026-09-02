# LC2 工作7 r9自动归档/手动导出入口（2026-09-01 Asia/Shanghai）

> r9真实启动产生孤立结束回执归档风暴并令事件泵error；本入口已由`docs/LC2_WORK_7_R10_ARCHIVE_BOUNDARY_CHECKPOINT_2026-09-01.zh-CN.md`接续。

## 当前身份

- Git：`main`，HEAD/origin/main=`758db3ae731613e2c3e4fcbfb9d7fd0058286f66`；工作树仍为工作6/7连续未提交实现与证据。不得reset/clean、commit、push或Release。
- 游戏Bridge保持0.4.19：72,704 B / `03BD7A7057C4408A475626E57AA2B4F99594E769AB6FC069CF9AE0366646C06D`；本次仅改盒子，不重复部署游戏DLL。
- 桌面盒子：`<desktop>/失落城堡2工具箱1.6.3-自动归档手动导出版-r9`；1,761文件、166目录、166,670,895 B、config0，与项目包逐文件差异0。
- EXE：6,484,432 B / `AC96FB7D990A05984B121234A8DAD657BBDDC410CCA63BCAB5AAEE0AAF175D5B`。

## 自动归档合同

- 输出：盒子旁`exports\对局归档\*.zip`，固定包含`manifest.json / summary.json / events.jsonl`。
- 正常`session_ended`自动封存；活动局写task-owned partial，盒子关闭时checkpoint，下次启动把旧partial恢复成ZIP。
- 事件按已验证主线程批次写入；同一drain遇到session end会先封旧局再接新局。单局raw events上限64 MiB，超过时manifest标记truncated，summary仍保留。
- 归档只含匿名协议token和CombatSnapshot，不读取BepInEx日志、昵称、平台ID、聊天或网络地址；不自动删除旧档。

## 手动导出/UI合同

- 主窗口顶栏顺序：`手动导出 → v1.6.3 → 启动游戏`。
- 对局中点击：后台线程ZIP当前完整partial，实时采集继续；可重复点击且不覆盖。
- 结算后点击：返回最近的完整自动归档；无会话时生成当前摘要ZIP。
- 写入失败：按钮显示`导出异常`并弹出错误，实时聚合不进入error；忙碌显示`导出中…`且防重复点击。

## 已过门

- pytest `219 passed + 37 subtests`；build内unittest 219项；包self-test/runtime正负控PASS。
- package命名管道E2E：start/end两事件生成automatic ZIP、ended summary、partial0、privacy匿名。
- 源码最小/高DPI与精确包三臂UI：按钮宽度等于requested，无重叠/截断；`UI-A01/A02/A03` CLOSED。
- 正式交付前只读验收：精确r9 EXE在MIN-100、STD-125、LARGE-150、DEGRADED-175、EMPTY-200、ARCHIVE-ERROR-150六臂均绑定PID/HWND与全窗口截图；Tk checker与像素审查最终`VERIFIED`。证据：`artifacts/ui-acceptance/2026-09-01-toolbox-auto-archive-r9-formal-acceptance-r3/`。
- 真实游戏自动归档与r8 final冻结继续采用被动自然结算确认；不要求野队团灭，不安排专门长局。

当前仍未执行different-owner最终综合审计、commit、push或Release；v1.6.2继续暂缓下载。三个新MOD仍只读预备，不进入r9。
