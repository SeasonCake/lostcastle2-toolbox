# 0.4.3 诅咒的魔晶石回蓝漏记

生命周期：`R-FAIL FROZEN / 0.4.4 CANDIDATE DEPLOYED / REAL RETEST PENDING`

原始日志和截图被 `.gitignore` 排除；本 README 只保留可提交的最小证据与本机定位。

## 真实反例

- 道具：`PassiveProps_Curse_BrokenMagicCrown` / “诅咒的魔晶石”。游戏本地化说明：法力值
  上限提升 80%，诅咒状态下所有法力值消耗提升 50%。
- 作者新开一局取得道具后施放两次同一技能；HUD 显示消耗 `38`、恢复 `0`，游戏法力条已经
  回到 `225/225`。
- 冻结日志中两次官方消耗均为 `19`：每次回调读取 `current=206/max=225`，根操作前观察值
  为 `225`；下一次操作开始时又已回到 `225`。该区间没有官方恢复回调，也没有
  `runtime_gain`。
- 结论：恢复发生在同一个底层 `ChangeCurrentMp` 根操作内部。入口前后净变化为 0，旧
  fallback 只接受 `effective>0`，所以真实的“先扣 19、再回 19”被净值抵消。

冻结日志副本：`LogOutput.live-copy.log`，`48,969` B / SHA-256
`7715403058FE84530CF7E56AE15BF8D6AFA6F7A406B40BAB4E70F05CE66729E8`。

## 0.4.4 最窄修正

- 不增加道具 Hook 或新的 Harmony 入口；继续复用现有根操作内官方耗蓝覆盖量。
- 低层候选恢复统一为：
  `max(0, after - before + same_operation_spend - official_recovery_covered)`。
- 关键矩阵已直接反射调用编译 DLL：净零回满 `225→225 + spend19 = gain19`；纯消耗
  `225→206 + spend19 = 0`；部分返还 `225→210 + spend19 = 4`；已有官方恢复覆盖 19 后为
  0；纯低层 `206→225 = 19`。五臂均 PASS。

真实继续游戏复测仍待作者执行；候选通过前不得把 1.5.13 标为发布 PASS。
