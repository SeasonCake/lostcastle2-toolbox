# r7 P3断线：final首次接受后被撤销

- 生命周期：`OWNER PASS / FINAL IDENTITY MAPPING PASS / FINAL STICKINESS R-FAIL`。
- Bridge：0.4.18 / `1D8272C3B22993D45B822ED5291FA704A4FDB78287E1E83A26412761A83CFDDF`。
- 日志：1,682,348 B / `87C7DE20109BA982CE9F97C474E806EF5FFF93260C42B9649812A11DB881045A`。
- 四卡+HUD截图：3,310,694 B / `B286349F25BF99ABAA3F8D3E24FAFB6D2575B500BD7EC2841E1ACD956DE7E820`。
- P3在黑森林第5区前后断线，roster由4降为3。最终官方四卡仍包含P3：slot0 902,144/322,493；slot1 372,078/152,264；slot2 4,605/0；slot3本机5,118,609/2,217,960。
- 第一次final：4 matches、0 unmatched/collision、4 published、accepted=true，逐项精确匹配截图；第二次final：2 matches、2 unmatched、1 collision、0 published、accepted=false。HUD停留在逐击值，首次接受未冻结。
- owner：13,752/13,752 matched；四slot冲突/未解析/重复均0。
- 局内唯一Bridge可恢复告警：墓园第4区一次`damage_snapshot_missing`，会跳过一条实时事件并保持degraded；无queue overflow、stack mismatch、owner conflict或fatal。最终关闭后的`transport reset: IOException`不是局内故障。
- 0.4.19候选只冻结首次完整final官方槽位与原会话匿名token；checker的`final_acceptance_regressed`以本日志为positive control。
