# Bridge 0.4.14 官方slot映射 r3 部署回执

- 候选/随包/游戏目录DLL：59,392 B / `343B69EF9FBBB982BB323F8EE291DC37B9783109A775A71A102F46706A3C6E24`。
- PDB：24,816 B / `66FD95BC10DDE9FE8B2E97C8AE8F479EFD4917505100049C3ADC25638F4D8F01`。
- exact rollback 0.4.13 r2：58,880 B / `A0738C534040B066F2B90B460E00CAA6D764E2E4E5F2C1563D78A0982EA7C96F`。
- SDK6.0.428、当前interop、Release：0 warning/0 error；15 Hook不变。
- 部署前两次exact进程查询（相隔10秒）均0；游戏目录回读与候选一致。
- 网络官方记录按`mIndex`主映射；`pair.Key`只作Player ID/ClientID/TransportID兜底。日志增加不含身份的`network_records/fallback_records/index_base/raw_indices`，可直接验证P位分布。
- roster存在时团队分母由各P位显示值求和；部分官方覆盖不再把本机值当团队分母。标签改为`自己 · Pn`、`Pn`、`Pn（离队）`。
- 真实0.4.14多人：`NOT RUN`。
