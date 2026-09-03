# Bridge 0.4.15 final-sync / owner-probe r4 部署回执

- 生命周期：`SOURCE/PACKAGE/DEPLOY PASS / REAL SHORT-ROOM NOT RUN / NO COMMIT, PUSH OR RELEASE`。
- 候选/随包/游戏目录 DLL：68,096 B / `82FC261AF70B3A0B4FAF552FD140D835994A33E97E5632EEB94EF956CE3EC36D`。
- PDB：26,884 B / `EB45F14D0B04EAC604D2DFFF514FC4A6BD5B5555DE45FF6FBFF275CDBB128FB9`。
- exact rollback 0.4.14 DLL：59,392 B / `343B69EF9FBBB982BB323F8EE291DC37B9783109A775A71A102F46706A3C6E24`。
- rollback PDB：24,816 B / `66FD95BC10DDE9FE8B2E97C8AE8F479EFD4917505100049C3ADC25638F4D8F01`。
- 部署前结构化进程查询：2026-08-31T18:24:09.0679450+08:00 与 18:24:19.5848080+08:00 均为0；查询覆盖 exact `LostCastle2.exe` 与所有1.6.3工具箱路径。
- 游戏目录部署后逐文件回读与候选一致。
- 离线门：198项PASS；SDK6.0.428 + 当前interop Release 0 warning/0 error；16个Harmony target；old r3 checker positive control按预期FAIL。
- 0.4.15只在exact SyncEnd且最终slot集合与历史roster完整一致时发布official；registered-player attacker目前只做coverage/conflict诊断，不改变主计数。
- 下一门：一到两个房间短正控。至少两个远端slot产生registered hit，其中一个覆盖投射/召唤转发；registered/Settlement unique hit完整重合且slot conflict为0。失败立即停止，不请求完整长局。
