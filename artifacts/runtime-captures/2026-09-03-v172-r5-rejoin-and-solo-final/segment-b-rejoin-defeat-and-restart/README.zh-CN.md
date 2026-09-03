# r5 重进后死亡并中途退出

> lifecycle: `interrupted-before-visible-settlement / recovery-pass / solo-final-not-tested`
>
> recorded: `2026-09-03 21:07 +08:00`

## 用户可见路径

- 本段承接已通过的非零历史量重进测试。
- 作者已耗尽最后一次复活机会，并在最终死亡后、明确的失败结算界面出现前直接 Alt+F4。
- 再次启动游戏后不再出现“继续游戏”，只剩正常读档开始入口；对局记录中也没有该局。
- 对照行为是：仍有复活机会时正常 Alt+F4，游戏会保留“继续游戏”入口。

这说明游戏将该存档视为已经终止，但没有证据表明自然结算UI路径被执行。较符合现有证据的解释是：游戏已在最后一次死亡后写入终局状态，随后 Alt+F4 切断了结算UI和对局记录写入；该解释目前标记为推断，而非代码级根因结论。

## 冻结证据

- `manual-diagnostic-AC6898B0BD.zip`：541,431 B，SHA-256 `3D92FC6A384EEDA219BE9685A1D4CD1FE6828177D9E0E0778E1BECE2E1EB73A1`。
- `recovery-diagnostic-AC6898B0BD.zip`：541,436 B，SHA-256 `DCDAACCAA1FC6902FC7039499CAB6E5BF2DC70637428D4EBA5A470BCADD02E36`。
- 手动包manifest：15,130条事件、10,274,064 B、`events_truncated=false`，事件SHA-256 `F4D152270CB6267AFDA8F2E5867E6DD5330F3CB2AE6B5A890E6E46A9A25A9251`。
- 最后摘要：session `be4f76f37b50431b981462d23c483168`、房间`L6:MageTower:4`、总伤害8,567,079、Boss伤害2,309,917、承伤490、`live_damage_complete=true`、`official_damage_complete=false`。
- 事件构成：5,111条`damage_resolution`、9,123条`resource_change`、896条`status`；没有official/final快照、`session_ended`或结算UI回调。

## 判定

- `REJOIN-SEED-01`此前的非零恢复与DPS无尖峰结论不变。
- 本段`abrupt-exit recovery = PASS`：手动包与恢复包均完整留存，且下一局建立独立partial。
- `SOLO-FINAL-01 = NOT TESTED`：Alt+F4发生在可见结算界面之前，不能用该段判断结算捕获能力。
