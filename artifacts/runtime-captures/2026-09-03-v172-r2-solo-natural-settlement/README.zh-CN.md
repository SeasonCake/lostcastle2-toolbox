# v1.7.2 r2 单人自然结算：数值精确、终局事件缺失

> lifecycle: `real-solo-settlement / live-values-exact / final-event-fail / diagnostic-frozen / not-public-raw`

## 作者确认的时序

- 作者明确看到本局结算界面，之后退出并在营地“冒险记录”中回看；营地截图不是结算触发时刻，只是对已产生官方记录的回看。
- 因此，盒子没有收到official或`session_ended`不是“还需等待/退出结算页”，而是已确认的终局事件缺失。
- 本局为单人、营地等级70、17:16开始、战斗时长5:31、晶山结束。作者说明实战中死亡2次；游戏记录卡显示“力竭次数1”，两者可能是玩家叙述与游戏统计字段口径不同，本轮不改写该字段含义。

## 官方截图与盒子对账

| 字段 | 游戏冒险记录 | 盒子最终live | 差异 |
| --- | ---: | ---: | ---: |
| 造成伤害 | 860,235 | 860,235 | 0 |
| 对首领伤害 | 139,339 | 139,339 | 0 |
| 结算承伤 | 409 | 409 | 0 |

- 盒子另记录实际HP掉血652.0188、有效回复642.0511；它们是连续HP浮点口径，不应与游戏逐击结算承伤409互相替代。
- 两次死亡没有造成玩家身份替换：归档全程只有1个本机匿名player、slot始终0、live累计回退0次。

## 冻结诊断

- 作者点击“导出诊断”生成manual ZIP：7,584事件、4,967,756 B事件数据、未截断；ZIP 253,271 B，SHA-256 `4DDBD85AC6112C70DEC0B34561B7277E760F37D65E52D8FB084C163A4FD2996D`，一致性检查通过。
- 冻结日志1,272,130 B，SHA-256 `55214D6FA999BDD350B926EF34D6F7CF1101F302394FF4E2C61DE679E729128D`；skip=0、fatal=0、transport reset=0。
- 最终摘要仍为`live`；live Damage/Boss完整，official Damage/Boss均false，`session_ended=0`。automatic ZIP没有生成。
- 当前聚合器重放7,584/7,584事件，ingest error=0、摘要字段差异0、游戏官方截图三字段差异0；7,569个事件点具有完整live值，team/personal各7,069个正DPS采样，最大均11,492.5，负值/NaN/无穷为0。
- 上述结果签署本局最终累计值与死亡过程稳定；游戏没有提供逐秒官方DPS，因此不把最大DPS或每秒轨迹冒充官方校准。

## 终局链诊断

- Bridge启动时三个可选network settlement探针均安装成功，但本局`kind=record`与`kind=boundary`都为0；固定`StageNetworkCtrl.SyncAdventureRecordDataEnd`前后缀没有进入可观测路径。
- 对照既有两人自然结算样本，同一网络SyncEnd会明确产生prefix/postfix boundary、`final_accepted=true`与逐P official；本次差异与单人路径一致。
- 当前游戏元数据确认：`StageNetworkCtrl.SyncAdventureRecordDataEnd()`是无参网络方法；另有`StatisticsMgr.OnGameSettlementSyncEnd(1参数)`、`OnGameSettlementSyncStart(1参数)`、`SetAdventureRecordSaveData(1参数)`与`SaveAdventureRecordData()`等本地结算入口。
- 排名第一的解释是单人结算不走network SyncEnd；仍保留一个待证伪分支：该方法可能在`OnGameRoundEndPreLoadCamp`清除`_inActiveMap`之后才调用，现有guard静默返回。下一候选应在本地settlement sync-end与现有network hook入口先记录命中，再决定统一final发布点。

## 隐私与开放项

- 两张作者截图及目标窗口截图含游戏昵称，只保存在本地ignored artifact，不进入GitHub/群分享。一次screen-capture因游戏被遮挡误抓到无关聊天界面，已立即删除且不可恢复，未纳入任何证据。
- `SOLO-FINAL-01`：官方结算界面存在且三项数值精确，但Bridge未发布official/session-ended。修复、构建、部署与再次实测尚未执行。
