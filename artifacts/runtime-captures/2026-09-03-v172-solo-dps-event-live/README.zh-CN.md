# v1.7.2 早期实测取证说明

> lifecycle: `local-runtime-evidence / sanitized-summary / not-a-release-asset`

## 样本边界

- 目录名在房间人数确认前创建，其中 `solo` 不是证据。作者随后确认本局为四人房，两名路人中途逐渐退出，作者打到城堡后离开。
- 盒子最终只把仍活动的两名玩家纳入可见团队分母；这是该次截图能直接支持的行为。
- `LogOutput.live.log` 只有一次 `damage_snapshot_missing`，没有 queue overflow、schema/session failure 或 transport reset。低频日志不能还原被跳过的具体命中，也不能量化 DPS 差额。

## 文件身份与使用

| 文件 | 字节 | SHA-256 | 说明 |
| --- | ---: | --- | --- |
| `toolbox-main-by-title.png` | 95,606 | `D8152A4F1BEE1624D9565C063D3B77F98A1DA3434F35B66F651667A44E19F7A5` | 按窗口标题重新抓取的主界面，可作为候选短测分享图 |
| `combat-hud-by-title.png` | 28,989 | `3F39E8B56D9DD22E4071C01B04C8D02D79380FAA080E02D13C46FD428ED8533A` | 按窗口标题抓取的 Mini HUD，可作为候选短测分享图 |
| `LogOutput.live.log` | 1,231 | `3B04DF855571AF2E6A7E0268FD67C8510631B7A7D906DC953FA10FD706528A5F` | 本地低频诊断，不作为公开分享文件 |

首次按 PID 抓取时，`toolbox-main.png` 实际重复捕获了 HUD；它和 `combat-hud.png`、`combat-hud-by-title.png` 字节相同。该两张重复图保留为抓图工具反例，不得冒充主界面证据。

公开分享前只从两张按标题抓取的 PNG 中人工选择；不要上传日志、配置、原始诊断归档或整个目录。
