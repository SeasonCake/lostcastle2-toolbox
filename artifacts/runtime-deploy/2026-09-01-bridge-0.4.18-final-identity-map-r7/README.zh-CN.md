# Bridge 0.4.18 final匿名身份映射 r7部署回执

- 生命周期：`SOURCE/PACKAGE/DEPLOY PASS / REAL SHORT CONTROL NOT RUN / NO COMMIT, PUSH OR RELEASE`。
- 候选/随包/桌面/游戏目录 DLL：71,680 B / `1D8272C3B22993D45B822ED5291FA704A4FDB78287E1E83A26412761A83CFDDF`。
- 游戏目录 PDB：27,764 B / `8595D66EC950C8A1C64A322A6720F72C8F58751EC105FC316ED4C8096D1A7AE5`。
- exact rollback 0.4.17 DLL：69,632 B / `EA17B678BDFBCD17066507204D7F9B730A7D56D8AD09E894CFAE810564EDA00B`；PDB：27,232 B / `6446E59CD1A082A458089B77676E11C326FB404E263CF227A4251A9B056642EF`。
- 部署前结构化进程查询：2026-09-01T00:38:43.9834535+08:00 与 00:38:54.5329650+08:00 均为0；部署后 00:38:55.1036349+08:00仍为0。
- 静态门：原生`SyncMultiplyRoundData`从final record读取`mID/mPlatformUniqueID`并交给`SetAdventureRecordPlayerData`；参考DLL只用mIndex/ordinal，不能处理真实四条mIndex全0反例。
- 0.4.18只用随机进程密钥HMAC record/roster的PlatformUniqueID后做唯一匹配；原始身份与指纹均不记录、不发送。缺失、碰撞、额外record、重复slot或数量不一致时整组拒绝。
- 离线门：pytest `206 passed + 37 subtests`；build内unittest 206项；SDK6.0.428 + 当前interop Release 0 warning/0 error；16个Harmony target；package self-test/runtime正负控PASS。
- 下一门：一个房间短局，至少两名远端P产生命中，最好包含一次变身/召唤；不要本机单独退出，应让多人局本身快速失败/全队团灭后取得真正四人结算。checker需同时PASS owner子门与final官方身份门；失败立即停止，不请求完整长局。
