# Bridge 0.4.16退局session修复 r5部署回执

- 生命周期：`SOURCE/PACKAGE/DEPLOY PASS / FINAL MULTIPLAYER NOT RUN / NO COMMIT, PUSH OR RELEASE`。
- 候选/随包/游戏目录 DLL：68,096 B / `CE9A7F10525DBC1AEE375CB3C261B759EA8B1EA1E86067A8312D35ECF04E5900`。
- PDB：26,944 B / `61DA9F2B11C4CD401DD8E1473B668825635093473DB70ACAAA859C8DE953C46C`。
- exact rollback 0.4.15 DLL：68,096 B / `82FC261AF70B3A0B4FAF552FD140D835994A33E97E5632EEB94EF956CE3EC36D`。
- rollback PDB：26,884 B / `EB45F14D0B04EAC604D2DFFF514FC4A6BD5B5555DE45FF6FBFF275CDBB128FB9`。
- 部署前结构化进程查询：2026-08-31T20:54:48.0795510+08:00与20:54:58.6155986+08:00均为0；游戏目录回读与候选一致。
- 真实0.4.15短房registered-owner：208/208 unique hit、四slot、forwarded 2/1/77/10、冲突0，子门PASS。
- 真实0.4.15整体失败原因：退局`round_start is_camp=True`之后、camp preload之前旧地图重开单人phantom session。0.4.16在closing-active-map窗口拒绝重入，并不发布瞬时duplicate-slot roster。
- 提前退出后仅剩单卡的7,453可能是团队/当前缓存折叠，个人口径UNKNOWN；不得与本机逐击2,508做个人A/B。
- 离线门：200项PASS；SDK6.0.428 + 当前interop Release 0 warning/0 error；16个Harmony target；真实0.4.15日志只因`phantom_session_after_round_start`被checker拒绝。
- 下一门：仅一次最终完整多人结算，验证exact SyncEnd后的完整四P `mIndex/Damage/BossDamage`。不再重复短房。
