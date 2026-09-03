# Bridge 0.4.12 三人完整局：普通怪少算与黄色误报

- 生命周期：`REAL MULTIPLAYER R-FAIL / 0.4.13 OFFICIAL SYNC CANDIDATE BUILT`。
- 版本身份：游戏目录 Bridge 0.4.12，52,736 B / `3229359A7D901CEBCD523109261A034704CA06B0E3EAD0829ADC5B19ED976D8D`；作者运行正式 v1.6.2 ZIP `B244610C…772431` 的解压目录。
- 关闭日志：12,028,286 B / `9A6097C725AE52F41D82FE74A7C87EC0CC53E769BAFB8F8B260F41F660C0FE12`。
- 截图：3,631,589 B / `75C508C00E35171BD3DA808EE1411F3E1768291721694BAC44DB2E34BEDD3999`。

| 玩家顺序 | HUD 总伤害 / Boss | 游戏官方总伤害 / Boss | 总伤害差 | Boss差 |
| --- | ---: | ---: | ---: | ---: |
| 本机 | 7,293,748 / 2,465,442 | 8,475,632 / 2,331,390 | -1,181,884 | +134,052 |
| 队友1 | 9,924,156 / 5,062,190 | 10,035,357 / 4,012,909 | -111,201 | +1,049,281 |
| 队友2 | 9,597,741 / 4,646,284 | 13,163,701 / 5,770,246 | -3,565,960 | -1,123,962 |
| 全队 | 26,815,645 / 12,173,916 | 31,674,690 / 12,114,545 | **-4,859,045** | **+59,371** |

全队非Boss部分：HUD 14,641,729，官方19,560,145，差`-4,918,416`；团队Boss只差0.49%。这把缺口几乎全部集中于普通怪，支持逐击`min(realDamage,hpBefore)`在高伤害多人清怪时不等于游戏最终官方累计；同时Boss团队总量近似但玩家间错分，证明owner分配是独立问题。

日志只有一个首次code：`damage_stack_mismatch`；`queue_overflow`、`damage_snapshot_missing`和致命session error均为0。源码路径确认stack mismatch发生在`CaptureHp`之后，只清空parent/depth线程栈，后续官方回调仍独立执行`EmitDamage`，故旧文案“event skipped”是误报，不能解释486万缺口。

当前interop静态反射确认官方权威字段：网络`AdventureRecordPlayerData.mDamageValue/mBossDamageValue/mID/mIndex`；本地fallback `GameRoundData.DamageCollector.mAtkDmg/mAtkDmg_Boss`。0.4.13按匿名slot发送这些不回退累计，逐击只保留DPS、来源和诊断；真实复测尚未运行。
