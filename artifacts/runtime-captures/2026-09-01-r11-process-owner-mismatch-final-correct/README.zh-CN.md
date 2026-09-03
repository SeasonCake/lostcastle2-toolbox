# r11 多人局过程 owner 错配、最终官方覆盖正确证据

> lifecycle: `current / known-red / work8-input / local-restricted-evidence`
>
> recorded_at: `2026-09-01 Asia/Shanghai`
>
> candidate: Toolbox `1.6.3 r11` / Bridge `0.4.20`
>
> session: `8301C84C4D` / `0c734120817a4499baf742f13048fb92`

## 1. 作者观察

- 结算前，本机一度显示约 `1100万 / 41%`，其他玩家也有一千多万，作者判断过程明显不对；
- 更早的15:33截图显示本机 `89,257 / 84%`，作者也认为不可信；
- 结算后HUD突然切换，最终四项与游戏官方四卡逐项对应。

这不是UI裁切或截图缩放问题。HUD如实显示了当时聚合状态；问题位于过程事件的owner/coverage或聚合语义。

## 2. 冻结文件

| file | bytes | SHA-256 | 用途 |
| --- | ---: | --- | --- |
| `early-hud-153345.png` | 79,626 | `B7818EF1304C8282DFB72849469B35009EE0F700FF81DF13CD71BE669E559E5B` | 15:33过程HUD |
| `final-official-hud-163551.png` | 4,116,221 | `3DD0F3C368B1F52495E4D3AEA5410F4C5837A67C4CF924B6AB4D614447ED1F9B` | 16:35官方结算+HUD |
| `r11-manual-session-8301C84C4D.zip` | 2,460,639 | `4F07BD4A62C8D96884C8E731C23F16A2140A215E485C5548AA4C71BDC2F7E77C` | 64,761事件、summary、manifest |
| `LogOutput.log` | 6,759,181 | `4F03F0BEBEDDF4DE34228449C0417C9D7F84E0B1CD1F3D9EDAA71CD18DA1B7BF` | Bridge owner/final诊断 |
| `partial-meta.json` | 285 | `85C731313CE1DC33E7E33D560FE224F5BF92982E9157153A5F3B2F0D74EC1594` | session/event身份 |
| `summary.json` | 14,394 | `CAB05E10B09920FB829B286CDE852D175864935D6149F7C173E6D02F9452C1DD` | observed与official并列结果 |

原始截图和桌面归档均保留，复制后未删除或改写。截图含游戏内昵称，只供本地诊断，不进入公开仓/Release。

## 3. 15:33截图可由事件流精确重放

- partial开始：`2026-09-01T15:30:16.703689+08:00`，Bridge `monotonic_ms=483985`；
- 截图：`2026-09-01T15:33:45.3312003+08:00`；按墙钟差映射目标 `monotonic_ms≈692613`；
- 目标前最后伤害事件 `monotonic_ms=672929`；
- 对`aggregate=true / damage_direction=dealt`的`settlement_damage`按`owner_player_id`求和：

| owner | damage | share | 截图 |
| --- | ---: | ---: | --- |
| `player-4`（本机P4） | 89,257 | 83.80% | 89,257 / 84% |
| `player-1` | 6,434 | 6.04% | P1 6,434 / 6% |
| `player-2` | 7,427 | 6.97% | P2 7,427 / 7% |
| `player-3` | 3,398 | 3.19% | P3 3,398 / 3% |
| total | 106,516 | 100% | exact |

因此早期高占比不是UI舍入、旧截图或肉眼误判；它是匿名事件流的真实过程状态。

## 4. 结算前observed与官方final差异

`summary.json`同时保留过程`observed_*`和最终`official_*`：

| player | observed | official | delta |
| --- | ---: | ---: | ---: |
| 本机 `player-4 / P4` | 11,610,684 | 9,732,171 | **+1,878,513** |
| `player-1 / P1` | 12,257,746 | 15,548,016 | **-3,290,270** |
| `player-2 / P2` | 2,400,402 | 2,647,181 | -246,779 |
| `player-3 / P3` | 1,770,725 | 1,845,895 | -75,170 |
| total | 28,039,557 | 29,773,263 | **-1,733,706** |

这同时证明：

1. 本机过程值确实高算；
2. P1过程值显著少算；
3. 团队过程总值仍少算，不能只用“从P1错分给本机”解释全部差值；
4. final官方覆盖正确，但不能把过程owner/coverage写成PASS。

Boss过程差值也非纯转移：本机`+1,790,731`、P1`-748,261`、P2`+132,234`、P3`+286,363`。

## 5. 现有checker的假绿形状

对同一`LogOutput.log`执行：

```powershell
py -3 tools/check_lc2_multiplayer_probe.py <LogOutput.log> `
  --minimum-remote-slots 1 --allow-no-forwarded-remote-hit --require-final-official
```

结果中：

- owner门：`24475 settlement_unique = 24475 registered_unique = 24475 matched_unique`，四slot
  `owner_match`全量、conflict/unresolved=0，判PASS；
- final门：4条记录、4个identity match、4个published slot，判PASS；
- 但summary的observed-vs-official逐slot明显不一致。

这否证“registration callback内部自洽 + final映射PASS即可证明过程owner正确”。当前checker必须增加
逐slot observed-vs-official final差值门，并用本局作为known-red；否则仍会假绿。

## 6. 当前判断与下一探针

### Confirmed

- r11成功建立独立新session并完整记录64,761事件，`events_truncated=false`；
- 早期84%、结算前约41%均来自过程聚合，不是UI外观问题；
- final官方四槽覆盖和HUD最终呈现正确；
- 过程同时存在本机高算、远端少算、团队总少算。

### Ranked hypotheses

1. `registration callback owner`对某些远端本体/变身/召唤或代理actor只保证回调一致，不等于官方最终
   credit语义；部分P1伤害被记到本机；
2. 远端forwarded/registered覆盖仍不完整，解释P1和团队总少算；
3. final官方覆盖不是根因，只是在`SyncAdventureRecordDataEnd`后纠正过程结果。

### Cheapest next checks

1. 先在离线checker加入observed-vs-official逐slot差异，本局必须known-red，既有真实known-good不得误杀；
2. 对`player-4 +1,878,513`和`player-1 -3,290,270`按`hook_path/source_token/actor_entity_id/
   source_entity_id/forwarded/room/time`分桶，找到首次分岔；
3. 检查变身、召唤与远端代理actor的registration root，不新增宽Hook或角色/武器/地图特判；
4. 使用现有ZIP/日志离线闭合后，只需一到两个房间短正控，不要求作者再打一场完整长局。

## 7. Not run

- 未修改source/tests/checker；
- 未构建、部署、启动游戏或工具箱；
- 未commit/push/Release；
- 未签发r11多人过程PASS或最终release verdict。
