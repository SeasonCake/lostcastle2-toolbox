# v1.7.2 r5 重进与单人结算实测

> lifecycle: `REJOIN-SEED-01 runtime-pass / SOLO-UI-POSTROUND-01 runtime-fail / SOLO-NATURAL-FINAL-01 not-run`
>
> recorded: `2026-09-03`

## 候选

- 桌面候选：`<desktop>/失落城堡2工具箱1.7.2-诊断候选-重进与单人结算-r5`。
- Bridge 1.7.3 Diagnostic：100,352 B，SHA-256 `DF02CD2B434A01B471C840176DE0CDDD0D52FF619562A32765D72147ACDA719D`。
- 日志确认只加载 Combat Bridge，没有社区 MOD，启动/Hook错误为0。

## 阶段 A：退出前

- 作者从新局开始，清理两个战斗区域后只关闭游戏，工具箱保持运行。
- 冻结 partial 为283条事件、178,589 B，未截断；283/283事件可解析、event ID唯一、全部重放且摘要差异0。
- 盒子退出前总伤害22,466；最后完整live为21,859，另有607逐击尾段；Boss与承伤均为0，近期DPS已自然归零。
- 工具箱在新游戏session到来时把本段自动封存为`superseded`恢复ZIP：12,317 B，SHA-256 `33D79158F903856894F089C416D3B0B5BA3AAD9C5F21462AB68D1330D03D92D1`；归档一致性283/283通过。

## 阶段 B：重进种子

- 新游戏进程加载同一Bridge1.7.3后出现：`[LC2CB-LIVE-SEED] kind=process_start_nonzero slots=0:22430:0`。
- 新session第一个完整live事件为sequence27：`live_damage=22,430 / boss=0`；聚合快照立即显示22,430、`live_damage_complete=true`，近期个人/团队DPS均为0。
- 退出前HUD22,466与游戏重新物化的官方live种子22,430相差-36，属于从逐击尾段回到游戏完整累计的向下校正，不是历史丢失。
- 第二个live为22,942，后续正差分512才产生105.785 DPS；再后续live与DPS连续增长，没有把22,430历史累计压入瞬时尖峰。
- 作者同时观察确认历史总量正确恢复且DPS无异常凸起。

判定：`REJOIN-SEED-01 = RUNTIME PASS`。

## 阶段 C：死亡后中途退出

- 作者已耗尽最后一次复活机会，并在最终死亡后、可见失败结算界面出现前直接 Alt+F4；重启后游戏不再提供“继续游戏”，只提供正常读档开始入口，且游戏对局记录中没有该局。作为对照，仍有复活机会时正常 Alt+F4 可以继续该局。
- 21:07:44 手动导出的旧会话 `AC6898B0BD` 完整保留15,130条事件、10,274,064 B，未截断；摘要为总伤害8,567,079、Boss伤害2,309,917、承伤490，最后仍为`live`。
- 事件仅包含5,111条`damage_resolution`、9,123条`resource_change`与896条`status`；没有official/final快照、`session_ended`或结算UI回调。该结果与“进程在结算界面前被强制结束”的路径一致。
- 工具箱随后为同一旧会话生成`recovery`归档；新局使用独立session与partial目录，没有跨局混写。

判定：游戏大概率已先写入终局状态，而进程退出切断了随后的结算UI与对局记录写入；这是根据用户可见行为和诊断事件共同作出的推断。该段验证了此边界下的诊断恢复链，但**不是**自然结算样本；不据此判定`SOLO-FINAL-01`通过或失败。

## 阶段 D：房间回滚后的主动结束

- 作者在一个房间第一次受伤后 Alt+F4；重新进入时游戏把该房间恢复到“未受伤、怪物未清理”的初始状态，随后作者重新游玩该房间并主动结束本局。
- 结算截图官方显示造成伤害1,451,098、Boss伤害240,540、承受伤害387；HUD造成伤害与Boss逐字一致，承伤显示59。
- 用户确认两次房间尝试的受伤值不同：游戏最终统计丢弃第一次被回滚的尝试，只采用第二次；逐击诊断曾观察第一次尝试。因此本次承伤差异的样本集合不同，不判为承伤算法缺陷。
- 游戏interop静态确认最终记录存在`AdventureRecordPlayerData.mTakeDamageValue`，所以官方承伤值可读取；当前r5官方快照只发布造成伤害与Boss伤害，HUD承伤仍来自逐击观察。
- 结算UI的标准prefix/postfix边界已命中，但当时最终save-list仍`save_available=false`，仅active/UI record已有正确1,451,098/240,540；`ui_settlement_info`与`ui_settlement_data`均记录`accepted=false ... in_active_map=false`，没有official、`session_ended`或automatic ZIP。`in_active_map=false`是post-round时序证据，不是代码中的直接拒绝条件。

判定：`DAMAGE/BOSS = RUNTIME PASS`；承伤差异为`ALT+F4 room rollback / non-comparable`；`SOLO-UI-POSTROUND-01 = RUNTIME FAIL`；作者主动结束而非自然胜利/最终死亡，所以`SOLO-NATURAL-FINAL-01 = NOT RUN`。

## 待完成

- 若继续修复，先让单人UI入口在最终save-list尚未生成时直接校验并采用UI传入的官方record；之后再用自然胜利或最终死亡进入结算界面，要求至少一个入口形成标准prefix/postfix、`[LC2CB-LOCAL-FINAL] accepted=true`、完整official、`session_ended`与automatic ZIP。
- 真实多人回归、Distribution、commit、push、tag、Release与群分享均未执行。
