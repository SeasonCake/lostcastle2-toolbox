# LC2 Combat Bridge 0.4.5 部署摘要

- 部署前 installed 0.4.4：`46,592` B，SHA-256 `CF2237678432A6131A06B4974FA44B677B4FFED9537FFF6F02A5096AA5CE3966`。
- 候选/部署后 installed 0.4.5：`47,104` B，SHA-256 `A6484B75E3369B1B0AA774F4A7DCB53E0107CE381F104D33A9388FC5EF25A801`。
- 部署前后均以 exact `LostCastle2.exe` + exact `ExecutablePath` 和 exact 工具箱进程名连续两次确认 0；未知路径计数为 0。
- 本机忽略文件 `LC2CombatBridge.0.4.4.rollback.dll` 与 `LC2CombatBridge.0.4.5.candidate.dll` 分别保存精确回滚和候选；fresh clone 不包含这些二进制。
- 部署后读回游戏目录 DLL 大小与 SHA-256 均与候选一致。普通太刀连续回蓝正控见同日 runtime capture 摘要。
