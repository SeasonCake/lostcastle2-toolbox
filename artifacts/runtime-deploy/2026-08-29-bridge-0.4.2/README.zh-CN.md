# LC2CombatBridge 0.4.2 部署回执

- 候选/随包/安装后 DLL：`46,080` 字节，SHA-256 `2D87EFA3B1805310595626AFBC27926CEAB389EB74CA8CD84E556ECDB402A57F`。
- 回滚 DLL：0.4.1，`41,472` 字节，SHA-256 `D499BA6BA2B21851F7C325F37503CEE418A66E4AA91A8D2A7C200FCC076B3744`。
- 部署前以 exact name `LostCastle2.exe` + exact `ExecutablePath` 连续两次确认进程数为 0；未知状态不写入。
- 部署后游戏目录回读与候选完全一致；BepInEx `[Logging.Console] Enabled=false`、磁盘日志保持开启。
- 0.4.2 修正同一根操作中“先官方耗蓝、后低层观察到恢复”被抵扣的问题，并增加 session-scoped 多人 roster/owner 归属事件。
- 静态、回放和构建门通过；真实闪避回蓝与多人对局仍等待作者实测。
