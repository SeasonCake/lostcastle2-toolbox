# r5 房间回滚后主动结束结算

> lifecycle: `damage-boss-pass / taken-non-comparable / postround-ui-final-fail / natural-final-not-run`
>
> recorded: `2026-09-03 21:32 +08:00`

## 用户操作与口径

1. 作者第一次进入目标房间并受伤。
2. 作者 Alt+F4；重启后该房间恢复到未受伤、怪物未清理的初始状态。
3. 作者第二次游玩同一房间，两次受伤数值不同，随后主动结束本局。
4. 游戏官方最终统计只包含保留的第二次房间尝试；逐击诊断已经观察过被回滚的第一次尝试。

因此承伤并非同一事件集合，不能用本样本判断逐击承伤算法是否与官方一致。用户确认这是测试操作造成的差异，不作为产品Bug或发布阻断。

## 可见结果

- 截图`settlement-official-vs-hud.png`：游戏官方造成伤害1,451,098、承受伤害387、Boss伤害240,540；HUD为1,451,098、59、240,540。
- 造成伤害与Boss伤害逐字一致。
- interop中`AdventureRecordPlayerData`明确包含`mTakeDamageValue`，说明最终官方承伤存在可读字段；当前r5的`OfficialDamageTotals`与party快照只传递造成伤害和Boss伤害，HUD承伤仍为逐击观察值。

## 重启边界

- 重启前恢复包`pre-restart-recovery-8C56369862.zip`：3,605条事件、2,436,054 B、未截断，摘要总伤害1,403,258、Boss伤害240,540、逐击承伤399。
- 新进程日志先收到`[LC2CB-LIVE-SEED] ... 0:1329687:240540`，证明游戏回滚后的保留累计低于退出前盒子累计。
- 新进程冻结partial共332条事件，332个event ID唯一、JSON解析错误0；摘要总伤害1,451,098、Boss伤害240,540、逐击承伤59。

## 单人结算UI

- 标准结算边界命中：prefix两次、postfix两次；active记录已经是`slot-0:1451098:240540`。
- probe同时显示最终save-list仍`save_available=false`，而active record已经是`slot-0:1451098:240540`。随后两条结果均为拒绝：
  - `[LC2CB-LOCAL-FINAL] kind=ui_settlement_info accepted=false known_players=1 in_active_map=false`
  - `[LC2CB-LOCAL-FINAL] kind=ui_settlement_data accepted=false known_players=1 in_active_map=false`
- 未发布official、未产生`session_ended`，也没有automatic归档。

判定：两个post-round UI入口虽然已拿到实际结算时机，但r5只尝试读取尚未物化的最终save-list，没有使用UI正在显示的record，因此`SOLO-UI-POSTROUND-01 = RUNTIME FAIL`。日志中的`in_active_map=false`是时序旁证，不是finalizer的直接拒绝条件。本局由作者主动结束，不外推为自然胜利或最终死亡入口的测试结果。

## 文件身份

- `settlement-official-vs-hud.png`：1,210,074 B，SHA-256 `B090E1F168C9B8F6BCFDD73EAF415D152FE643E9734C158ED5CE51BDB44827A7`。
- `LogOutput.log`：63,776 B，SHA-256 `9FCB8282BA302B2DDD0C7D004F40DBB8DB74723B0811BFAC35D37B6C85FB04C6`。
- `pre-restart-recovery-8C56369862.zip`：139,429 B，SHA-256 `EAC6423EEFF25DCB80DB64DE5CC3398A1659A89682EA28959347A6296BB6FF81`。
- `post-restart-partial/events.jsonl`：181,772 B，SHA-256 `D3D05BEFFA076CAAA5EFE51BEF118FCBDD0AED41586B69ACD2527AE1F1152BA9`。
