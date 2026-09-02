# LC2 工作8 r18 房内官方缓存探针 checkpoint（2026-09-01）

> lifecycle: `superseded / r18-withdrawn / installed-0.4.24-restored / r19-calibration-in-progress`

> 21:49复审更正：r18缺少pre-read限频、force边界受普通样本cap影响，且checker预设未证dict/cache及rollover关系。r18未运行，已撤回并回滚installed 0.4.24。下文r18身份仅作历史恢复证据，不再表示ready。

## 当前结论

- r15完整四人局final官方逐槽映射PASS，但per-hit过程团队总伤害高2,714,413，Boss高4,242,594。
- r17延迟live锚点重建仍高final总伤害2,471,529（6.36%）、Boss4,018,595（25.71%），因此r17不签过程准确。
- 冻结r15日志另证明`_adventureRecordCacheDataList`是当前房delta：旧active加该cache在下一房被active逐槽精确吸收。这使`active + 一份房delta`成为下一条可证伪路线，不能把dict与cache-list重复相加。
- 当前interop与参考DLL静态确认`SettlementDataMgr.mCacheRoundDataDict`为`Dictionary<ulong, StatisticsMgr.GameRoundData>`，逐项提供`mDamageCollector.mAtkDmg/mAtkDmg_Boss`；reference的使用只能证明访问路径，不能代替本客户端实时语义实测。

## 0.4.25诊断合同

1. 不新增Hook；在既有官方攻击postfix之后采样，另在room entry/exit、preload、round end、final sync强制采样。
2. 每个样本原子记录dict、Statistics cache list、active list三张匿名slot向量；raw float用Invariant round-trip，不取max、不单调化、不提前取整。
3. dict key只使用非零Player ID/ClientID/TransportID唯一映射，或同key network record的平台身份HMAC辅助；NPC允许unmatched但不进入human slots。
4. 重复slot、跨slot碰撞、读取失败、非有限/负数、Boss>总伤害均保留为失败证据；singleton只单列，不映射本机。
5. 诊断不发布到pipe，不覆盖`live_damage`、final official或HUD。
6. 专用`tools/check_lc2_settlement_cache_probe.py`要求同一combat room内至少两个human槽增长，dict与cache-list交叉一致；可选`--require-rollover`验证转场前后`active + 一份delta`守恒。

## 当前身份与门

- Git：`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66=origin/main`；共享工作树仍有工作6/7/8未提交内容，禁止reset/clean/整体stage。
- candidate/package/desktop/installed Bridge0.4.25 DLL：87,040 B / `2C0936C35833A486DEA19ABA8118ECFF79F5295D3383A86C4C4DE16D3433852F`；PDB：32,260 B / `36B6F1134062E380750C47E30BD5DAEAA91CFCBEC85FF5C3722006B990344188`。
- r18桌面：`<desktop>/失落城堡2工具箱1.6.3-房内官方缓存探针版-r18`；1,761文件、166目录、166,687,814 B、config0，与项目包逐文件差异0；EXE / `23CAC42797C7037060516909A13A1ABE09C4A609E362A19612DA3A20D2BEEEAD`。
- pytest245 passed +41 subtests；build内unittest245；SDK6.0.428/current interop Release0 warning/0 error；16 Harmony patch；包/桌面self-test exit0。
- 0.4.24 exact rollback与0.4.25 candidate冻结于`artifacts/runtime-deploy/2026-09-01-bridge-0.4.25-settlement-cache-probe-r18/`；双零门后已部署，readback exact。

## 原恢复条件（已撤销）

不要运行r18。先完成0.4.26：200ms单调时钟pre-read限频、首击/force旁路、普通额度与force边界分离、受限per-run HMAC opaque token，以及只分类不预判的dict/cache与rollover checker。新候选冻结后再给短房步骤。

## Not run

真实r18短房、Boss实时语义、pipe/HUD采用、最终过程准确PASS、different-owner审计、commit、push、Release均未运行。
