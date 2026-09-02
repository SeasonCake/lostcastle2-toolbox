# 工具箱 1.6.2 多人个人/队伍拆分 UI 候选

- 精确包：`package/失落城堡2工具箱1.6.2-实时数值监测+一键MOD安装`。
- 包：1,760 文件、166,612,000 B、config0。
- EXE：6,466,270 B / `BCCDDE6C1B917FD92DB261707491D4F5C32592285028F32777E234C28CD65E27`，版本 1.6.2。
- 运行时清单：58,171 B / `EE38C5D3EDF0CE7549463DF9A166C53A262D17ACCE9B4CBBFCF56D7BE41D1B0D`。
- Bridge 0.4.9：51,712 B / `18228F2E5EB91B22AFD6AE6F8F97B968F4734B99794E4BD45FEC8BFFB76E8161`。
- 生命周期：`IMPLEMENTATION UI CANDIDATE VERIFIED / REAL MULTIPLAYER NOT RUN`。

## 冻结臂

| 臂 | 身份 | 画面判定 |
| --- | --- | --- |
| `CLIENT-SLOT2-A150-main` | receipt-bound / 1022×816；receipt `4C75A543…E6EFB`；PNG `B4726D12…6B41C` | 四人、远端槽位0、本机槽位2；本机仍排第一并标“自己”。主卡个人 `480/Boss 0`；队伍单列合计 `34,328`；标题为“个人来源明细” |
| `CLIENT-SLOT2-A200-hud` | receipt-bound / 610×554；receipt `075A9DE5…897DF`；PNG `DFAA83D9…81C07` | HUD 明确“个人伤害 480/Boss 0/DPS 48”，三名远端卡完整，未出现编号跳跃或裁切 |

两臂回执绑定的 EXE、catalog、runtime manifest 与上方冻结身份一致；回执图当前哈希也与 `screenshot.sha256` 一致。QA 配置通过 `KEYVIEW_CONFIG_DIR` 写入各臂隔离目录，精确包保持 config0。

## VisualIssueLedger

| 编号 | 状态 | 证据 |
| --- | --- | --- |
| `MULTI-TOTAL-01` | CANDIDATE CLOSED | 个人主卡/HUD 不再使用队伍 `total_damage`；队伍合计只在队伍面板展示 |
| `OWNER-CHAIN-01` | STATIC/T CLOSED | Bridge 使用通用 owner 层级；真实 0.4.9 仍待运行 |
| `PLAYER-TOKEN-01` | STATIC/T CLOSED | session 内 native Player identity；桌面只见匿名 token |
| `NONHOST-LOCAL-01` | T/UI CLOSED | 本机槽位2、远端房主槽位0时，本机仍为“自己” |
| `TEAMMATE-NUMBER-01` | T/UI CLOSED | 失活 token 不参与活动队友编号；HUD 连续显示队友1–3 |

此处只能判 UI/模型候选；不能证明真实客机 callback 可见性、远端召唤物 owner 链或重连对象生命周期。
