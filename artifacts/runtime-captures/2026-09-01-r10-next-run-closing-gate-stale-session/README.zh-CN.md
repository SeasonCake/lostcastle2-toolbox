# r10退局后下一局未重置

- 生命周期：`FIRST RUN LIVE PASS / NEXT RUN SESSION RESET R-FAIL / MANUAL EXPORT NOT CAUSAL`。
- r10精确EXE：`1D05A4EAF829A439D854B7DF9AEF9163AE0167343FE2AF35ED16FC85FE1E9637`；游戏Bridge0.4.19。
- 第一局截图：HUD实时9,906与当前单人续局卡9,906一致 / `3D2C3F143E1FF82A5845A80B01DB27A592BB0CD8BDBDDDA82CD5F96F1FEF8D48`。
- 用户在营地点两次手动导出，得到同session key的两个当前partial副本；活动partial继续累计，不终止采集。两个ZIP哈希`827055A5…A189`、`D632E0A9…948F`。
- 第二局入口和战斗房日志均`change_room_end valid=false`；没有新`session_start`。partial summary仍是原session，个人值从9,906继续到16,519。
- 根因：0.4.16的`_closingActiveMapTransition`防迟到旧房回调门只在`EndRound`清除；中途退局路径没有该回调，门永久保留并阻断下一局。
- 日志：66,298 B / `974C26D015D203018241A3D19DCFEDA8699201ADBB9FCB31DFC9A69D225A9B26`；checker明确报`next_run_blocked_by_closing_gate`。
- r11使用旧活动房完整指纹；新房指纹变化立即解锁，同房重入由首条真实伤害/法力消耗解锁，旧房单迟到回调继续拒绝。
