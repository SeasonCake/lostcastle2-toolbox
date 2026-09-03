# Bridge 0.4.13 官方逐玩家累计 r2 部署回执

- 候选/随包/游戏目录 DLL：58,880 B / `A0738C534040B066F2B90B460E00CAA6D764E2E4E5F2C1563D78A0982EA7C96F`。
- PDB：24,748 B / `485481155AD478D6779181B530BC3B2DDC4189E8D0C450A4D534E786942A3029`。
- exact rollback：pre-r2 DLL 58,880 B / `9FF0B4FFFA3E2B3E02327B5A3B90B810B2906884ADD0E5AF8936858D79BFD64D`；0.4.12另在上一部署目录冻结。
- SDK6.0.428、当前interop、Release：0 warning / 0 error；15 Hook不变。
- 部署前两次exact进程查询（相隔10秒）均0；游戏目录回读与候选一致。
- r2在pre-r2基础上把官方`mIndex`的0/1基准锁定到本局，避免离队后重新推断；同slot多个token只取活动token或最大官方值，避免Player对象重建双算团队总量。
- 真实0.4.13多人：`NOT RUN`。
