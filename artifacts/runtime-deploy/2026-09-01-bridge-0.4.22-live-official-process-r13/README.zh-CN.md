# Bridge0.4.22 live官方缓存过程主口径 r13部署回执

> lifecycle: `DEPLOY PASS / REAL SHORT SMOKE R-FAIL / SUPERSEDED BY 0.4.23`

- candidate/package/desktop/installed DLL：77,824 B / `FAB3E539150196C27B06788BC30A6D89565F1B1B72264EA9A09644F2B071EC04`。
- candidate/installed PDB：29,752 B / `55DA51167D5E696AA63F1A7A63DEDADA61E281DA6B3EC90F67A22A3DCAB65397`。
- exact rollback0.4.21 DLL：75,776 B / `B164F49608DA4C4EEC6DA75CD7A383EA9725217D7FE68ADB358103764F38D56C`；PDB28,944 B / `0B4E3AC68456E77CAC6B3D39592CEA873CBC98342B80D649B44FB17808E3D0DF`。
- 部署前17:46:23与17:46:34两次结构化查询均0、unknown path0；部署后17:47:17仍为0。
- 离线门：Python全量234+37；build内234；C#0 warning/0 error；包/桌面self-test与包形runtime正负控PASS。
- 0.4.22不新增Hook，不删除逐击事件；只把已证明可用的active官方缓存作为完整live快照，并与final官方字段分离。
- 下一恢复条件：使用桌面r13正常启动，三人或四人进入战斗房打几下；HUD/partial应在约1秒内出现完整`live_*`，退出/最终结算仍可由`official_*`向下覆盖。无需完整长局即可做协议smoke；最终收敛PASS仍需以后一次自然结算。
- 真实烟测中缓存/身份门PASS，但live字段未穿过pipe有界副本，partial保持null；0.4.22判R-FAIL，不签过程PASS。0.4.23只修此复制遗漏。
- 未commit/push/Release，未签发多人最终过程准确PASS。
