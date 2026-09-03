# Bridge 0.4.17零real通用fallback r6部署回执

- 生命周期：`SOURCE/PACKAGE/DEPLOY PASS / REAL FALLBACK AND FINAL MULTIPLAYER NOT RUN / NO COMMIT, PUSH OR RELEASE`。
- 候选/随包/游戏目录 DLL：69,632 B / `EA17B678BDFBCD17066507204D7F9B730A7D56D8AD09E894CFAE810564EDA00B`。
- PDB：27,232 B / `6446E59CD1A082A458089B77676E11C326FB404E263CF227A4251A9B056642EF`。
- exact rollback 0.4.16 DLL：68,096 B / `CE9A7F10525DBC1AEE375CB3C261B759EA8B1EA1E86067A8312D35ECF04E5900`。
- 部署前结构化进程查询：2026-08-31T21:33:02.1599375+08:00与21:33:12.9395608+08:00均为0；游戏目录回读与候选一致。
- 真实0.4.16变身样本：第一战斗房P3有39个callback仅累计27；全局持续2点耗蓝385次/782。registered/Settlement 659/659命中重合，P位冲突0，确认问题是数值阶段而非owner串位。
- 参考DLL优先正`mRealHPDamage`，非正时回退`mFinalDamage`。0.4.17保持普通real>0的既有`min(real,hp_before)`，仅在`real=0/final>0`时回退final，并按slot记录fallback次数/总值。
- 离线门：201项PASS；SDK6.0.428 + 当前interop Release 0 warning/0 error；16个Harmony target；package self-test/runtime正负控PASS。
- 下一门：使用r6时验证P3 `final_fallback_slots`真实增加；唯一最终多人结算验证exact SyncEnd四P官方值。不增加任何武器/技能特判。
