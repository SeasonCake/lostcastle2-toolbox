# 0.4.5 无怀表、自愈与复活完整局

- 生命周期：`DAMAGE/TAKEN R-PASS / HP NO ERROR PROVEN / MP R-FAIL`。
- 最终截图：`result-screen.png`，1,327,199 B，SHA-256 `A41B33F50E0CB4E2E5C2923CF2995541DF8B53F75AF2E354B348822F5E834F6E`。
- 最终日志：`LogOutput.finished-copy.log`，321,189 B，SHA-256 `9A1DB9FE7C7A4E5CDA605EA6931296E115D584266068AA3FF1B3B8ACEF30D02B`。图片/日志本体按仓库 ignore 合同保留，本 README 只保存身份与结论。
- 官方结果与 HUD 一致：总伤害 `125,226`、Boss `23,027`、受击承伤 `308`；击杀 80。Bridge failure/resource conversion/stack mismatch 为 0。
- HUD 回复 `398`。作者确认“自愈”刻印低于 35% 时每次正常 `+1`，本局还死亡/复活一次；因此回复高于承伤有明确合法来源，不能判为 HP 多算。官方结果“力竭次数 0”不能否定特殊/自动复活的实际观察。
- HUD 法力消耗/恢复 `960/0`。日志有 20 次官方消耗、原始合计 960；多次消耗前连续基线已恢复到 95.07656、100、91.50036、105、110 等，但 recovery/runtime_gain 均为 0，且没有怀表。确认 0.4.5 的通用零变化观察漏记。
- 0.4.6 离线候选只修 MP 提前返回，并为 HP 增加诊断；未部署、未实测。
