# LC2 工作7 r11下一局归零入口（2026-09-01 Asia/Shanghai）

> 历史快照：r11 入口已被后续工作接续；保留用于说明新 session 归零合同，不表示当前候选身份。

## 当前身份

- Git：`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66`；工作树为工作6/7连续未提交范围。不得reset/clean、commit、push或Release。
- Bridge源码/包/桌面/游戏目录0.4.20：73,216 B / `17DF64A11C2BD35D46C3AF252420B0AE5E056FC508D9032C62EDDF28C12CC51C`。
- rollback0.4.19：`artifacts/runtime-deploy/2026-09-01-bridge-0.4.20-next-run-closing-release-r11/`。
- 桌面r11：`<desktop>/失落城堡2工具箱1.6.3-新局归零自动归档版-r11`；EXE `44E40FAC…78D92F`；1,761文件、166目录、166,672,031 B、config0，与项目包逐文件差异0。

## r10真实R-FAIL与r11规则

- 第一局9,906正常；中途退局后第二局入口/战斗房均valid=false，没有新session，partial继续到16,519。两次手动导出只复制同partial，不是原因。
- r11在closing时冻结旧活动房`stage/scenario/index/map`指纹；新房指纹不同即解除并`BeginGameSession`。
- 若新局恰好重进同一房间，首条真实伤害或本机官方法力消耗作为强正信号解除；营地和无战斗证据的同房迟到回调仍拒绝。
- checker：冻结r10日志报`next_run_blocked_by_closing_gate`；单个旧房迟到后合法新房known-good不报。

## 门与下一步

- pytest225+37；build unittest225；SDK6.0.428/current interop0 warning/0 error；包self-test/runtime正负控PASS。
- 作者只需短测：第一局打几下并退出/回营，再开第二局；第二局进入新房应立即归零，首击只累计本局。无需完整长局或队友配合。
- r10自动归档风暴修复继续保留；手动导出按当前partial工作。
- 作者已授权：其报告/截图已提交并进入待机后，可由本任务按精确PID/路径正常关闭游戏和盒子，不再重复要求手动关闭；身份不明或正常关闭失败时再询问。

真实两局归零PASS前不做different-owner最终审计、commit/push/Release；三个新MOD仍只读预备。
