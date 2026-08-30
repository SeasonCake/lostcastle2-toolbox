# “默认 7 人/可改更多人”MOD 静态分析与待加入合同

- 来源 A：`全部版本通用默认7人可改更多人MOD(1).zip`。
- 来源 B：`全部版本通用默认7人可改更多人MOD BepInEx框架.zip`。
- 两包均为 40,237,762 B / SHA-256 `F2DFFD094662A868388BA9575ED48DEC043F7C2C0126CD88D99454BAD8E1BDB2`，逐字节相同。
- ZIP 完整性 PASS；311 文件、解压 87,563,031 B。
- 生命周期：`STATIC IDENTITY/FUNCTION PASS / CATALOGUED AS MINIMAL DLL / EXECUTION NOT RUN`。

## 最小载荷

真正功能插件只有：

- `LostCastle2MaxPlayers16.dll`：15,872 B / `1247F19FC0C0447B18E38FABC0AE08EF13967282A116D58C2CFF9FBD3A630F25`。
- 内嵌插件：`梦羽的多人联机补丁` 1.3.0，GUID `mod.lostcastle2.maxplayers16`，作者常量与配置署名均为“梦羽”；内嵌发布地址 `https://www.bilibili.com/opus/959071553286307840`。
- 无快捷键、无游戏内设置面板；配置由 BepInEx 首次运行自动生成。

原包还含 `mod.lostcastle2.maxplayers16.cfg` 330 B，但这是已生成的用户配置，不应作为固定载荷覆盖。默认值为 `MaxPlayers = 7`，说明建议 1–16，超过 16 服务器可能拒绝创建。

只纳管 DLL 可从 40,237,762 B 降到 15,872 B，节省 40,221,890 B；载荷约为原 ZIP 的 0.0394%。其余文件是工具箱已受管提供的 BepInEx core、Doorstop、CoreCLR、Unity 6000.3.16 库、配置与 cache，不重复随社区 MOD 打包。

## 静态行为

Mono.Cecil 回读确认：

- Harmony patch 创建房间的 `CreateLobbyRoomRequestDto.MaxPlayers`，写入 `max(1, 配置值)`，默认 7。
- 给自定义房间名加 `[梦羽多人补丁]` 前缀。
- 读取 Relay/JoinResponse 的 RoomData 后，如果 `mMaxPlayerCount > 4`，仅把本地可见值改回 4；日志明确“cloud capacity stays <配置值>”。
- 插件内嵌说明：主机界面仍可能显示上限 4，但实际人数已修改；如果要加入别人的房间，必须卸载本 MOD，否则会显示房间已满。
- 没有修改战斗数值、伤害、掉落或存档的静态证据；核心作用是房间创建/房间数据的人数上限。

## 纳管与未运行边界

- 用户已选定加入；当前 catalog/package 只携带哈希固定的 15,872 B DLL，不携带原包框架或 cfg。
- 作为高影响联机 MOD，详情必须显著提示“偏房主创建房间用途；加入他人房间前卸载”，不能只写“默认7人”。
- Bridge、schema、聚合器与 pipe 的静态/合成合同已扩到 16 人；主窗口超过 4 人显示横向滚动条，HUD 以每列 3 名队友扩展到 15 名队友。此项只证明结构容量，不替代真实 7–16 人建房/客机实测。
- 第三方 DLL 未执行；真实建房、云端容量、7人加入、超过16拒绝、客机兼容和卸载恢复均为 `NOT RUN`。
