# LC2 工作 7 多人准确性证据链（2026-08-31）

> 历史快照：保留多人故障与修复证据链；各 PASS/FAIL/NOT RUN 只适用于文中版本和样本，不表示当前发布状态。

## 生命周期与裁决

- 记录时间：2026-08-31（Asia/Shanghai）。
- 基线：`main` / `758db3ae731613e2c3e4fcbfb9d7fd0058286f66` / tag `v1.6.2`；本文涉及实现仍未提交。
- 真实结论：Bridge 0.4.14 r3 仍为 `R-FAIL`；自动测试不能替代真实多人。
- 0.4.15短房registered-owner子门已真实通过；整体因退局phantom session失败。当前源码为0.4.16退局修复候选；最终四P校准、包/UI、发布仍未通过。
- 禁止把本文解释为 commit、push、Release 或恢复 latest 的授权/结果。

## 决定性静态身份

- `LC2.Core.dll`：`0267065BFB4CF8E4B7BD369C2240212901294C85B931DD6259FFAF02E5AFEFAF`。
- `GameAssembly.dll`：`747E8BECB7B97B014D7F282C1EB60A7A4754A8A1DF01CEB943C03967F6E6F1C5`。
- 参考伤害统计 DLL：`915764422A72CE28D268BC19CDF794E781132F3A732EFE4004780EB5A3875A11`。
- r3 冻结日志：`67218B63E68B9FF654824E20DA4E6B0356BEA99A0560EF6D7778001013DBBD62`；54/54 摘要均为 `network_records=0 fallback_records=1`。

## 可证伪数据链

`game source -> P slot -> session -> protocol -> aggregator -> UI`

1. **game source**
   - 房内稳定的远端逐P官方累计源尚未证明存在。
   - `_multiRoundDataDic` 是最终结算临时收件箱，不是可靠轮询源；最终流程消费后会清空，因此 r3 的全零不能证明最终记录从未存在。
   - 单 `SettlementDataMgr.mCacheRoundData` 已被真实局证明是团队/当前缓存，不得冒充某P official。
   - 最终可靠门是 `StageNetworkCtrl.SyncAdventureRecordDataEnd` 返回后，再读取 `StatisticsMgr.mCurAdventureRecordSaveData.mAdventureRecordPlayerDataList`。
   - GameAssembly `0x5812402/0x581240C` 与 `0x58125BC/0x58125C3` 把 Damage/BossDamage 写到 record `+0x12C/+0x130`；随后 `SyncMultiplyRoundData` 物化记录并清空多轮字典。
2. **P slot**
   - `AdventureRecordPlayerData.mIndex == Player.Index`，0基；UI 显示为 `P(mIndex+1)`。
   - `mID`、dictionary key、PlayerList ordinal、1/0基猜测不得代替 slot。
   - 实时逐击当前 owner 链可返回“错误但非空”的 Player。15份冻结probe共3382条 official attacker：`event_creature == attacker OwnerEntityInHierarchy` 为3382/3382，且2114/3382不等于raw attacker。
   - 0.4.15短房已证明最多16人设计下的4个实际roster Player callback覆盖：208/208与Settlement命中重合，四slot forwarded为2/1/77/10且冲突为0。callback仍只输出coverage/conflict诊断，不改变主计数。
3. **session**
   - 新 run 的 `BeginGameSession` 清 player token、party fingerprint 与聚合状态。0.4.15退局时出现`round_start is_camp=True`后旧地图重开单人session；0.4.16在closing-active-map窗口拒绝该重入。
   - Python 收到异 GUID 的显式 `session_started` 会清旧值；冻结证据没有 pipe GUID/party payload 收据，因此 P4 跨局同值仍是告警，不是已闭合的 Python 污染根因。
   - 同 run pipe 重连不再生成新 GUID；同 session 的 resume 保留累计，并标记 `degraded:transport_reconnected`，明确期间可能存在传输缺口。
4. **protocol**
   - 最终 official 仅在 exact SyncEnd 后、record slot 集合与本局历史 roster slot 集合完全一致、无非法/重复 slot 时发布；否则整组拒绝，不允许 partial official 冒充正确。
   - registered callback 当前只写 BepInEx 诊断，不进入 `owner_player_id`。
5. **aggregator**
   - 可见团队分母只使用 active roster；inactive 历史保留在 breakdown，但不再进入可见总量。
   - party snapshot 拒绝 duplicate slot；本机 personal 只使用 active local token。
   - 团队cache伪装slot0的冻结回放会得到错误的 `65,363,930` 且占比仍100%，所以“比例守恒”只能作为必要条件，不能证明源语义正确。
6. **UI**
   - 保留 `自己 · Pn`、`Pn`、`Pn（离队）` 合同。
   - 新实现未增加控件；最终包冻结仍须抽核主界面/HUD，真实多人通过后再做完整Windows UI验收。

## 自动短房 checker

入口：`tools/check_lc2_multiplayer_probe.py`。

默认 PASS 条件：

- 至少两个远端 slot 有 registered-player attacker 事件；
- registered unique hit 与 Settlement official attacker hit 完整重合；
- 至少一个远端 slot 覆盖 sender 不同于 raw attacker 的投射/召唤转发样本；
- owner slot conflict 与 duplicate callback slot conflict 都为0。

known-good、缺第二远端slot、owner冲突、旧r3无诊断四个控制均有自动测试。旧r3日志必须返回 FAIL。短房不通过立即停止，不请求完整长局。

## 离线检查

- `py -3 -m unittest tests.test_combat_aggregator tests.test_multiplayer_probe_checker tests.test_combat_bridge_source -q`：49项 PASS。
- `py -3 -m unittest discover -s tests -p "test_*.py" -v`：201项 PASS。
- 隔离 SDK `6.0.428` + 当前 interop Release：0 warning / 0 error。
- build输出：Bridge `0.4.17`，16个 Harmony target；此处只证明源码/合同/构建。
- 0.4.15短房owner子门`R-PASS`、整体退局生命周期`R-FAIL`；0.4.16真实部署、完整结算、包/UI、commit/push/Release仍未完成。

## 2026-09-01：0.4.17最终长局反例与0.4.18离线候选

- 冻结的特别卡四人长局仍判`R-FAIL`：owner链registered/Settlement为39,997/39,997、四slot冲突/未解析均0，但final save list四条record的`mIndex=0,0,0,0`，旧安全门发布0槽；客户端逐击HUD不能替代官方结算。
- 0.4.17的zero-real fallback不是本机高算来源：本机slot3为0次；只有slot0/1/2共46次、44,803伤害。网络卡顿产生主机不认可的客户端“幽灵命中”仍是解释高算的有证据假设，最终官方record覆盖才是产品闭环。
- 当前interop确认record包含`mPlatformUniqueID`；原生`StatisticsMgr.SyncMultiplyRoundData`从record `+0x58/+0x60`读取`mID/mPlatformUniqueID`并传给`SetAdventureRecordPlayerData`。参考伤害DLL仅使用`mIndex/ordinal`，在本样本下同样不能解决塌槽。
- 0.4.18只在进程内用随机密钥HMAC record与roster的`PlatformUniqueID`并要求一一唯一对应；原始身份与指纹都不记录、不发送。`mID`、昵称、ordinal和固定人数不参与映射。身份缺失/碰撞、额外record、重复slot或record/roster数量不等时整组拒绝。
- 自动判定器新增final官方门：合成的“4条全零mIndex但4个身份唯一匹配”known-good PASS；冻结0.4.17长局positive control按预期FAIL，同时owner子门仍PASS。全量`206 passed + 37 subtests`；SDK6.0.428 + 当前interop Release为0 warning/0 error。r7项目包/桌面逐文件一致、包self-test/runtime正负控PASS，Bridge已在双零门后可回滚部署；真实短房仍`NOT RUN`。

## 2026-09-01：r7提前退多人短房（测试路径无效）

- 用户一手确认：本机退出多人后，游戏把当前冒险继续为单人；其后单卡数字是刚才房间四人的折叠团队摘要，不是原四人逐P官方卡。
- 四人实时HUD截图时本机为slot2，个人23,785，远端P1/P2/P4为1,542/6,329/5,572；之后单人卡为21,134/8击杀。两张图处于不同会话语义，禁止相减或据此判个人高算。
- 冻结日志中四人roster随后降为1人，本机slot2随后重建为slot0；`final_ready=true`为0次、final records为0。因此0.4.18身份映射本局`NOT RUN`，不是PASS或FAIL。
- owner子门仍PASS：registered/Settlement 354/354；slot0/1/2/3分别33/125/81/115事件，冲突/未解析/重复均0。变身及技能期间的实时伤害可增加由用户确认；这不等于服务端逐P终值准确。
- 下一短正控必须让多人局本身在一到两个房间内快速失败/全队团灭，不能由本机单独退出。checker新增`multiplayer_roster_collapsed_to_single_without_final_sync`专门拒绝本路径。

## 2026-09-01：r7完整结算、P3断线与final接受回退

- 官方四卡：slot0 902,144/Boss322,493；slot1 372,078/152,264；slot2断线P3 4,605/0；slot3本机5,118,609/2,217,960。
- 0.4.18第一次final摘要为4 records、4 identity matches、0 unmatched/collision、4 published、accepted=true；四项与截图逐项完全一致，证明匿名身份映射算法与断线P保留PASS。
- 下一次强制刷新时当前roster只有3人，终局Player对象/身份状态改写KnownParty；同一4 records变为2 matches、2 unmatched、1 collision、0 published、accepted=false。截图HUD仍为逐击估算（本机5,838,110等），证明首次接受结果没有冻结。
- owner链整局13,752/13,752 matched，slot0/1/2/3分别5,503/1,283/154/6,812，冲突/未解析/重复为0。P3断线不是归属串位。
- “异常”来源独立闭合：墓园第4区仅一次`damage_snapshot_missing`；无queue overflow、stack mismatch、owner conflict或fatal。它发生较早但degraded状态保留到后期Boss，符合作者“很后面才发现”。退出后的transport IOException是盒子关闭管道，不是局内异常。
- 0.4.19只冻结首次完整accepted的slot→原会话匿名token与官方Damage/Boss，下一局reset；不改伤害公式。checker新增`final_acceptance_regressed`，冻结r7日志按预期FAIL。

## 怪物宝藏 v10.5 次级静态结果

- RAR：26,649 B / `E49625AECB22890299B1D6AE8EE71D232ECC2684D25F099689FB1ABD1C7F90DF`；RAR5完整性 PASS，4个根成员，无目录穿越、BepInEx/core/cache/cfg。
- 唯一功能载荷：`怪物宝藏v10.5.dll`，56,320 B / `6A67A0790DA593FB38BAB5C5CA8ECD706356C1FB4A9E0F95E032E120B8BEE37D`。
- 作者：DLL内嵌“懒虫桑”；面板快捷键 IL 为 Alt+F（F=102、RightAlt=307、LeftAlt=308）。
- 依赖均为现行BepInEx/IL2CPP/Harmony与游戏interop（含`Hunter.Common`），无需额外功能文件。
- 版本存在待澄清不一致：RAR/DLL文件名为10.5，BepInPlugin版本为0.1.0，压缩包更新总结仍写10.4。
- 同靶点/语义潜在冲突包括 dynamic-hp、mech-attack-inherit、enhancement-plan 等怪物生命周期补丁，以及其他掉落/伤害改写MOD；第三方真实逻辑 `NOT RUN`。
- 为不阻塞多人主线，尚未写入catalog/package；若后续接入，最小载荷只能是该DLL，并应保留版本不一致与“有bug找作者反馈”的内部记录。
