# Bridge0.4.23 live payload复制修正 r14部署回执

> lifecycle: `DEPLOY PASS / REAL SHORT SMOKE R-FAIL / SUPERSEDED BY 0.4.24`

- candidate/package/desktop/installed DLL：78,336 B / `9BDB748BB77C30D8579851009DD0D4D847B902F49B76A1BF70F4E59081698C9C`。
- candidate/installed PDB：29,752 B / `2067A1E6B87F8D65CA999BCB74FA5FD59E5EC1EED1C35E00B15E322A5DD80F08`。
- exact rollback0.4.22 DLL：77,824 B / `FAB3E539150196C27B06788BC30A6D89565F1B1B72264EA9A09644F2B071EC04`；PDB / `55DA51167D5E696AA63F1A7A63DEDADA61E281DA6B3EC90F67A22A3DCAB65397`。
- 部署前18:02:28与18:02:39两次结构化查询均0、unknown path0；部署后18:03:13仍为0。
- 离线、构建、package/desktop self-test和包形runtime正负控均PASS。
- 下一恢复条件：用桌面r14正常启动四人或三人局，进入战斗房打几下；partial必须出现`live_damage_complete=true`、每槽`live_*`与`last_live_*`非null。无需清房或最终结算。
- 真实两人+NPC smoke中NPC产生额外official record，旧严格record-count门拒绝live整组；payload复制本身已越过。0.4.24只放宽额外unmatched record，不放宽human identity完整唯一门。
- 未commit/push/Release，未签发最终过程准确PASS。
