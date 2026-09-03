# Bridge 0.4.19 final首次接受冻结 r8部署回执

- 生命周期：`SOURCE/PACKAGE/DEPLOY PASS / PASSIVE NATURAL FINAL CONFIRMATION NOT RUN / NO COMMIT, PUSH OR RELEASE`。
- 候选/随包/桌面/游戏目录 DLL：72,704 B / `03BD7A7057C4408A475626E57AA2B4F99594E769AB6FC069CF9AE0366646C06D`。
- 游戏目录 PDB：28,144 B / `56C2F2856F7ECBA63BE2F364F24BA101F4516DC9A28565D78DD6BC453257D93F`。
- exact rollback 0.4.18 DLL：71,680 B / `1D8272C3B22993D45B822ED5291FA704A4FDB78287E1E83A26412761A83CFDDF`；PDB：27,764 B / `8595D66EC950C8A1C64A322A6720F72C8F58751EC105FC316ED4C8096D1A7AE5`。
- 部署前结构化进程查询：2026-09-01T02:17:10.3478158+08:00 与 02:17:21.0847257+08:00 均为0；部署后02:17:21.7191100+08:00仍为0。
- r7真实证据：首次final四槽与官方四卡逐项一致，包括断线P3；紧接三人roster刷新撤销结果。r8冻结首次完整accepted的官方值和原会话匿名token，后续刷新直接复用，不再读终局新Player对象。
- r7局内唯一degraded为墓园第4区一次`damage_snapshot_missing`；该问题未在r8中猜测、静默清除或混入final修复。
- 离线门：pytest `208 passed + 37 subtests`；build内unittest 208项；SDK6.0.428 + 当前interop Release 0 warning/0 error；16个Harmony target；package self-test/runtime正负控PASS。
- 下一门改为被动：作者以后正常游玩自然结算时只需留一张四卡+HUD截图；不要求野队配合团灭，不安排专门长局。
