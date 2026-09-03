# 工具箱1.6.3 孤立结束回执修复 r10候选

- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 桌面：`<desktop>\失落城堡2工具箱1.6.3-自动归档修正版-r10`。
- 两侧均为1,761文件、166目录、166,671,530 B、config0；逐文件SHA-256差异0。
- EXE：6,485,067 B / `1D05A4EAF829A439D854B7DF9AEF9163AE0167343FE2AF35ED16FC85FE1E9637` / 1.6.3。
- runtime manifest：`C08977B9476E5A88C8BF7462BEA31B7D783278466D3C0443F9CD4D5E6A972C07`；Bridge仍为0.4.19 / `03BD7A7057…6C06D`，未重复部署游戏DLL。
- pytest `223 passed + 37 subtests`；build内unittest 223项；包self-test/runtime正负控PASS。
- 单元positive control：74条同session孤立`session_ended`产生0 ZIP/0 partial；自动final后迟到事件不重开；crash恢复档仍允许同session继续采集。
- 聚合边界：foreign started/ended可安全切换session；foreign伤害/资源/普通状态仍拒绝。
- 精确包命名管道E2E：74条旧结束回执+新局start/end只生成1个ZIP、2 events、ended摘要、partial0；ZIP `A1900651…D193A`。HUD未进入异常。
- r10精确包UI smoke：1223×896 / `B177859D…3B15`；PID29352/HWND133050；manual/app-version/combat-status Tk checker `VERIFIED`。
- 生命周期：`IMPLEMENTATION/PACKAGE/STORM E2E PASS / REAL GAME SHORT SMOKE NEXT / NO COMMIT, PUSH OR RELEASE`。
