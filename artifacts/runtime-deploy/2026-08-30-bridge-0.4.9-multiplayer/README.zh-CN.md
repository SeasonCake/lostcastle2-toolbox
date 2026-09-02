# Bridge 0.4.9 多人归属候选部署

- 部署时间：2026-08-30 18:25 +08:00。
- 生命周期：`SOURCE/BUILD/PACKAGE/DEPLOY PASS / REAL 0.4.9 MULTIPLAYER NOT RUN`。
- 候选 DLL：51,712 B / SHA-256 `18228F2E5EB91B22AFD6AE6F8F97B968F4734B99794E4BD45FEC8BFFB76E8161`。
- 候选 PDB：22,880 B / `05E024633E52AE096C71D5877B02AD925F7373416CA9467F9867DC8471FC5FCD`。
- 回滚 0.4.8 DLL：49,152 B / `7740BA3E30CD8C8B73F8BFDF221C3384CB2D64F940699A6974556E989896CE55`。

## 进程与部署门

- 18:24:51 与 18:25:01 两次 exact name + `ExecutablePath` 观察中，`LostCastle2.exe` 和 `失落城堡2工具箱.exe` 均为 0。
- 部署前游戏目录 Bridge 精确为 0.4.8 `7740BA3E…6CE55`；候选和回滚先复制到独立 artifact，再替换游戏 DLL/PDB。
- 部署后游戏 DLL/PDB 与构建候选逐字节回读一致，进程仍为 0；没有启动游戏。

## 桌面测试盒

- `<desktop>/失落城堡2工具箱1.6.2-多人归属测试版`。
- 1,760 文件、166,612,000 B、config0。
- EXE：6,466,270 B / `BCCDDE6C1B917FD92DB261707491D4F5C32592285028F32777E234C28CD65E27`，版本 1.6.2。
- 内置 Bridge 与游戏目录均为 `18228F2E…E8161`；隐藏 `--self-test` 退出码 0。

## 下一实测

1. 房主路径：任意 2P–4P 一局，结算时个人主卡应与作者自己的游戏卡对齐；队伍合计只在队伍面板出现。
2. 客机路径：作者加入他人房间，确认本机即使不是槽位0仍显示“自己”；远端房主显示为队友。
3. 至少一方带召唤物/派生投射物；结束日志读取 `[LC2CB-OWNER] kind=summary` 的 local/remote/unattributed，不能只凭 UI 看起来接近就判 PASS。
4. 若 `unattributed_damage` 仍非零，保留精确量和日志，不把差额猜给本机或某名队友；用 0.4.9 汇总决定是否需要更细的有界 owner sample。

本部署不授权 commit、push、tag、Release 或覆盖公开 v1.6.1。
