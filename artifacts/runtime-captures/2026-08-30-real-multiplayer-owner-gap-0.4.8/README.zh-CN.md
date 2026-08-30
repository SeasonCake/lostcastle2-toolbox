# Bridge 0.4.8 首次真实多人伤害归属反例

- 记录时间：2026-08-30。
- 人口：3 人联机；作者是 1P/房主，其中一名队友携带召唤物。
- 生命周期：`MULTIPLAYER PERSONAL TOTAL R-FAIL / OWNER ATTRIBUTION R-FAIL / 0.4.9 CANDIDATE NOT RUN`。
- Bridge：0.4.8，49,152 B / `7740BA3E30CD8C8B73F8BFDF221C3384CB2D64F940699A6974556E989896CE55`。
- 冻结日志：920,380 B / `29CB5319D323248FD4A92FAA4B57750F386CC0CA79171B0B880E77DD9B6E94E6`。
- 结算/HUD 图：1,324,326 B / `4D0633570980B5C7587C49119C18EC95043A38DDDDB96A7286ED2E2E17ED970E`。
- 主窗口拆分图：205,837 B / `41FF8D212F522F8D5AC9CC6E4717F23DC349DFF7FBEA446AE63A6C45E281628D`。

## 决定性数值

游戏个人结算为总伤害 `576,627`、Boss `171,274`；工具箱顶部为总伤害 `819,706`、Boss `245,900`，分别多 `243,079 / 74,626`。

工具箱队伍拆分为：

- 自己：`235,775 / Boss 65,315`；
- 队友 1：`130,746 / Boss 28,705`；
- 队友 3：`5,726 / Boss 19`；
- 未归属：`447,459`。

四项精确相加为 `819,706`，证明旧顶部就是队伍全量而不是个人量。个人官方与“自己”的差额为 `340,852`；若先用这部分解释未归属中的本地派生攻击，未归属仍剩 `106,607`，它是远端玩家/召唤物未归属的强候选，但 0.4.8 没有逐击 owner 诊断，不能进一步把这 `106,607` 唯一分给某一名队友或召唤物。

## 代码链根因

1. Python 聚合器对所有 `dealt` 事件无条件增加 `total_damage`，HUD/主卡又直接显示该字段；客户端观察到的队友事件因此进入了个人主卡。
2. 0.4.8 的 owner 解析仅为 `TryCreature(attacker)?.OwnerPlayerIncludeMaster`。历史单机证据已证明大量技能/投射派生实体 `OwnerPlayer=null`、但 `OwnerEntity` 指向玩家；该已闭合路径没有进入 Bridge，多数本机事件也会落入未归属。
3. 旧 `PlayerToken` 动态优先取 `ID / ClientID / TransportID / slot`。真实联网过程中这些字段可由 0 变为有效值，导致同一个 native Player 取得新 token；截图中队友编号从 1 跳到 3 与失活旧 token 参与编号一致。

## 0.4.9 / 工具箱 1.6.2 候选

- 顶部/HUD 改为个人伤害、个人 Boss、个人近 10 秒 DPS；队伍合计和未归属只在队伍面板单列，多人来源表改为个人来源。
- owner 解析有界遍历 `mAtkerInHierarchy`、`OwnerEntityInHierarchy`、`OwnerEntity`、`StandMaster` 与 `Creature.Master`，并用 PlayerList 根实体匹配兜底；不按角色、召唤物、武器或道具特判。
- token 改用 session 内 native Player pointer 作为仅内部映射键；桌面仍只收到 `player-N`。本机标记使用 `LocalPlayer.Pointer == player.Pointer`，不依赖槽位 0 或房主身份。
- 新增 owner 汇总诊断，分别记录 local/remote/unattributed 的事件、伤害与 Boss 量，供一次后续实战直接裁决。
- 自动/包形/像素候选已通过；真实房主复测和非房主客机仍为 `NOT RUN`，不得从本样本外推 PASS。
