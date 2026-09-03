# 工具箱1.6.3 / Bridge0.4.20下一局重置 r11候选

- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 桌面：`<desktop>\失落城堡2工具箱1.6.3-新局归零自动归档版-r11`。
- 两侧均为1,761文件、166目录、166,672,031 B、config0；逐文件SHA-256差异0。
- EXE：6,485,067 B / `44E40FAC1A64542AF3EECBB39C43A436D20960481004158F56D6FF6FF678D92F` / 1.6.3。
- runtime manifest：`040ED9565C9DEF6983620B7239C50024D64F2C6A18CD282923F03FDFFFE2DB01`。
- Bridge：73,216 B / `17DF64A11C2BD35D46C3AF252420B0AE5E056FC508D9032C62EDDF28C12CC51C`；PDB28,288 B / `5127A5D6…2C34C`。
- pytest `225 passed + 37 subtests`；build内unittest225项；SDK6.0.428/current interop Release0 warning/0 error；包self-test/runtime正负控PASS。
- closing规则：保存旧活动房`stage/scenario/index/map`指纹；新房不同立即建立新session；同房重入以首条真实伤害/法力消耗解锁；同指纹迟到回调仍拦截。
- 冻结r10日志checker positive control报`next_run_blocked_by_closing_gate`；单个旧房迟到→合法新房known-good不报。
- 自动归档沿用r10已闭合的孤立结束风暴修复；手动导出未改变session生命周期。
- 生命周期：`SOURCE/PACKAGE/DEPLOY PASS / REAL TWO-RUN SHORT SMOKE NEXT / NO COMMIT, PUSH OR RELEASE`。
