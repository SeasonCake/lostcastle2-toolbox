# 工具箱1.6.3 自动归档+手动导出 r9候选

- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 桌面：`<desktop>\失落城堡2工具箱1.6.3-自动归档手动导出版-r9`。
- 两侧均为1,761文件、166目录、166,670,895 B、config0；逐文件SHA-256差异0。
- EXE：6,484,432 B / `AC96FB7D990A05984B121234A8DAD657BBDDC410CCA63BCAB5AAEE0AAF175D5B` / 1.6.3。
- runtime manifest：`C08977B9476E5A88C8BF7462BEA31B7D783278466D3C0443F9CD4D5E6A972C07`。
- Bridge仍为0.4.19：72,704 B / `03BD7A7057C4408A475626E57AA2B4F99594E769AB6FC069CF9AE0366646C06D`；游戏目录已是同一身份，无重复部署。
- BepInEx archive：40,402,401 B / `0B617BC439F53E39680444F1EFD84C2B31A96D144D3267EE06EBEA05B59738A8`。
- 全量pytest `219 passed + 37 subtests`；build内unittest 219项；包self-test、运行时首次/重复安装、冲突core写前负控PASS。
- 精确打包EXE命名管道端到端正控：`session_started→session_ended`自动生成ZIP `55EB1E76…19E74`；manifest reason=automatic、2 events、truncated=false、privacy=anonymous_protocol_tokens_only、summary=ended、partial=0。
- 自动归档：活动局append-only events + 原子summary/meta partial；正常结束封存ZIP；下次启动恢复旧partial；64 MiB事件上限只截断raw events并在manifest标记，不丢summary；不自动删除旧档。
- 手动导出：对局中异步导出当前完整副本且采集继续；结算后返回最近完整自动归档；无局时导出当前摘要。失败只影响归档并把按钮标为“导出异常”，不破坏实时聚合。
- 正式Windows/Tk只读验收：精确EXE六状态/DPI臂、Tk receipt checker与像素审查最终`VERIFIED`；`UI-A01/A02/A03`全部CLOSED。
- 生命周期：`IMPLEMENTATION/PACKAGE/UI/ARCHIVE E2E PASS / REAL GAME AUTO ARCHIVE PASSIVE NEXT / NO COMMIT, PUSH OR RELEASE`。
