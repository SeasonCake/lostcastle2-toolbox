# Bridge 0.4.3 锁血兼容候选

生命周期：`LOCAL DEPLOYED CANDIDATE / PACKAGE VERIFIED / REAL 65% HP LOCK PASS`

## 问题与修正

- 1.5.11 的 Bridge 0.4.2 已会把官方伤害结算外的直接负 HP 变化发为
  `resource_operation=loss`，但桌面端事件 schema 未允许 `loss`。选择生命锁定后，第一条
  合法事件因此被校验器拒绝，客户端按既有 fail-closed 合同把本轮标为“异常”。
- 0.4.3 补齐 `loss` 合同，并把承伤、HP/MP 资源观察限定为本地玩家根实体。队友仍只参与
  匿名伤害归属，队友自身锁血或资源变化不进入本地承伤/恢复/法力累计。
- 锁血与真实上限变化保持不同语义：锁 20%/40%/65% 时 `max` 不变，可用当前生命上限分别
  为原上限的 80%/60%/35%；染血的冠军腰带是实际最大生命 100→60。清除诅咒、房间药剂和
  宝物引起的当前值或最大值变化继续走同一个有界资源合同，不按道具增加专用 Hook。
- `loss` 只进入内部 `hp_loss_other`，不进入用户主指标“受击承伤”或“回复”。

## 冻结身份

| 对象 | 大小 | SHA-256 |
| --- | ---: | --- |
| 0.4.2 exact rollback | 46,080 B | `2D87EFA3B1805310595626AFBC27926CEAB389EB74CA8CD84E556ECDB402A57F` |
| 0.4.3 candidate / 当前游戏目录 | 46,592 B | `2837F6C485F691BB743CEAF3EB5EBE2BB5FA1D66A19E1FB2D4B87F029CF562A3` |

本 README 可提交；同目录 DLL 被 `.gitignore` 排除，仅作本机精确回滚/恢复定位。

## 已完成门

- Bridge .NET 6 构建：0 warnings / 0 errors。
- Python 全量：149/149 PASS。
- 20%/40%/65% 锁血合同、真实最大生命降低/恢复、直接 HP 成本、药剂治疗正控均保持连接 live；
  未登记操作 `drain` 为反例并被拒绝。
- 干净运行时 bundle 校验、首次安装/重复安装、不同核心写前阻断均 PASS。
- 桌面 1.5.12 EXE：`4E48267FFDBB5868FFC0890FBC67E7B74CB2B2353EC38A5EB8404FABEB8DAD31`。
- 冻结 EXE 的 100%/200% 战斗页与 200% 四人 HUD 结构/像素验收为 `VERIFIED`。
- 部署前后游戏 exact name + `ExecutablePath` 均连续两次为 0；部署后 DLL 已回读为上述 0.4.3。

## 尚未外推

- 作者已完成真实 65% 锁血正控：游戏 `49/140`，HUD 保持绿色“实时”，本局伤害、承伤、
  回复和法力继续累计；详情见 `artifacts/runtime-captures/2026-08-29-hp-lock-0.4.3/README.zh-CN.md`。
- 20%/40% 仍只有同合同自动测试；冠军腰带、清除诅咒和药剂造成的当前/最大生命变化未逐项实测。
- 2P–4P 主客机及队友独立锁血仍为 `NOT RUN`。静态本地玩家过滤与合同测试不能替代真实联机。
