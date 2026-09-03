# Bridge0.4.24 NPC额外official record兼容 r15部署回执

> lifecycle: `BRIDGE DEPLOY PASS / LIVE PIPE SUBGATE PASS / R15 TOOLBOX REALTIME R-FAIL / BRIDGE RETAINED FOR R16`

- candidate/package/desktop/installed DLL：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`。
- candidate/installed PDB：29,760 B / `8BC5DCA2E9C5DA0147DAEB04105963F378B30FE38A9797D8BDCCA3A345B0FCCC`。
- exact rollback0.4.23 DLL：78,336 B / `9BDB748BB77C30D8579851009DD0D4D847B902F49B76A1BF70F4E59081698C9C`；PDB / `2067A1E6B87F8D65CA999BCB74FA5FD59E5EC1EED1C35E00B15E322A5DD80F08`。
- 部署前18:26:05与18:26:16两次结构化查询均0、unknown path0；部署后18:26:52仍0。
- source/full/build/package/desktop/self-test/runtime正负控均PASS。
- 下一恢复条件：使用r15进入多人战斗房打几下；无论是否有NPC，partial应对所有human槽写`live_*`与`last_live_*`并令`live_damage_complete=true`。无需清房或结算。
- r15真实四人smoke证明Bridge四槽live字段穿过pipe且无降级；随后确认工具箱直接显示房间边界raw live会冻结房内增量。Bridge0.4.24保留，r16只修Python聚合为anchor+delta。
- 未commit/push/Release，未签长局最终过程准确PASS。
