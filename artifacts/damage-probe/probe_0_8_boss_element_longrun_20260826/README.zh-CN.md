# LC2DamageProbe 0.8.0：随机元素、Boss、诅咒与死亡长局

记录时间：2026-08-26 至 2026-08-27（Asia/Shanghai）

## 作者给出的真实条件与官方结果

- 营地出发前先攻击训练木桩，使用了技能、技能派生物和元素伤害。
- 正式对局中包含蓄雷戒指、魔导师之靴、多个符文/法弹效果；玩家受到过冰属性伤害。
- 诅咒房出现持续数个房间的短期诅咒：使用闪避会受到百分比伤害。
- 本局死亡一次并继续。
- 官方结算：造成伤害 `103848`、承受伤害 `358`、对首领伤害 `24271`、击杀魔物 `89`。

## 冻结证据

- 最终日志：`probe_0.8.0_boss_element_20260826-235646_final.log`
  - 大小：`1,534,423` 字节。
  - SHA-256：`38CE0D199B8DE5FE6C6D83588303C880A3B6433CB96BA09F1678DADFF6FE9441`。
- 营地木桩截图：`codex-clipboard-e3c76908-9d49-46e4-9a42-cc2ceff0faa8.png`
  - SHA-256：`7F4A8AB9360225C457DFF9236FF27973EF674E39CE43DDADC8EEF2BAECFC638C`。
- 蓄雷戒指截图：`codex-clipboard-8f4dc79d-9b9c-4e2b-aef5-bab52d12ce6c.png`
  - SHA-256：`F7FAD6E7CD240937329635AC8BA06EDDCDC79C69579084D733E0D8DAD4DC90AB`。
- 魔导师之靴截图：`codex-clipboard-4be75eb1-bbc2-43c2-be10-e3cc7a080fdb.png`
  - SHA-256：`6E0CA1E72AD296719C6354EC74FCC62C7EDD48CACED14F476CBE6269D3A4C2D8`。
- 结算截图：`codex-clipboard-06ce3b10-6e3d-447e-97b4-be62e8ab530a.png`
  - SHA-256：`5816D5EC0FA40A11BE4126770B7D0FBC26FEA73374D132E94F46376C149731AD`。
- 探针：`LC2DamageProbe 0.8.0`，SHA-256 `9F05C42F08AF4100877FB3186E1E67FD67B5636CD28D4333E213A58F9F4E8841`。
- 冻结时游戏已退出；工具箱仍运行但不会修改 BepInEx 日志。7 个观察目标加载成功，没有 probe error、HP 栈错误、元素读取错误、事件上限或 BepInEx/Harmony 错误。

## 营地木桩负控

- 营地阶段记录 83 个 `hp_snapshot`，其中 65 个有非零 `applied`，单次约 `4.15–495.03`。
- 4 个木桩目标的 HP 前后始终不变；营地阶段没有任何 `official_attacker`。
- 因此木桩可用于确认技能和伤害计算被执行，但必须从正式结算总量排除。只有 HP 快照、没有唯一官方攻击事件的数据不得进入 HUD 总伤害。

## 总伤害与元素分布

正式对局有 1,588 个已归属的唯一 `official_attacker` 事件，没有未归属事件。对每击使用已闭合公式后：

```text
sum(ceil(max(0, min(mRealHPDamage, hp_before)))) = 103848
```

与官方造成伤害精确一致。按 `main_attrs` 聚合：

| 主元素 | 事件数 | 伤害候选 |
| --- | ---: | ---: |
| Electric | 1444 | 97104 |
| None | 52 | 4917 |
| Poison | 89 | 1679 |
| Fire | 3 | 148 |
| 合计 | **1588** | **103848** |

主要来源包括：`Staff_BulletWhite=88487`、`Rune_Blue_Lighting=8617`、`Rune_Blue_RuneBullet=4917`、`Un_Common_PoisonDamage=1679`、`Staff_BulletBlack=148`。0.8.0 元素判定没有 `error`；本局确认电、毒、火与无元素事件可同时分流。

## Boss 伤害

- `defender_is_boss=true`：374 个事件，逐击候选 `24271`，与官方“对首领伤害”精确一致。
- Boss 段主元素：Electric `21615`、None `1562`、Poison `1094`；本局 Fire 事件没有命中 Boss。
- `IsElite=true` 与 Boss 标记不能互换：精英候选为 `20543`，不会得到官方 Boss 数字。正式 Boss 门必须使用 `IsBoss`。
- Boss 抗性和减免已经反映在每击最终 `mRealHPDamage` 中；HUD 统计实际结算伤害，不回填减免前理论伤害。

## 承伤与冰属性受击

- 8 个玩家 `official_defender` 事件的减伤前 `ori_final` 逐击向上取整合计 `358`，与官方承伤精确一致。
- 其中一击明确为 `main_attrs=Ice, attrs=Ice`，证实玩家受到冰属性伤害的第一手观察。
- 减伤后 `final` 逐击候选为 `332`；再次确认官方承伤统计减伤前原始值，而不是实际掉血。

## 击杀、死亡与诅咒边界

- 伤害事件的 `lethal=true` 合计 `88`，官方击杀为 `89`，仍差 1。击杀不能完全从伤害事件反推；若 HUD 需要击杀，应观察官方 `OnKillMonster_Hero`，不能用致死命中数冒充。
- 作者确认本局死亡一次；玩家根实体始终为同一个 `1000003`。最后一次 HP 快照到 `0` 时 `mDead=false`，说明不能只凭 HP=0 或伤害结构推断死亡/复活分段。
- 短期闪避百分比诅咒没有形成独立 `official_defender`；当前伤害探针无法确认它是直接 HP 变化、最大 HP 变化还是另一条状态路径。

## 有效治疗量边界

现有伤害快照之间可观察到 5 个正向 HP 间隙，合计约 `138.725`。这只是下限：

- 治疗后若没有下一次受击，尾段治疗不可见；
- 无法可靠区分治疗、复活、最大生命变化和直接 HP 设置；
- 无法判断请求治疗量中有多少因满血溢出而无效。

游戏 interop 已确认统一增量入口：

```text
CreatureRuntimeData.ChangeCurrentHp(
    float deltaValue,
    DoInjuryType doInjuryType,
    bool showFloating,
    bool isRedBlood,
    string changeSourceStr)
```

并可从 `OwnerCreature` 过滤到玩家。后续只需对该入口做 prefix/postfix，只读记录请求量、前后 HP 与 MaxHP；`max(0, hp_after-hp_before)` 即为该次有效治疗，满血溢出自然排除。死亡/复活需另以生命周期事件分段，不能记作治疗。

## 当前裁决

1. 0.8.0 自然启动、元素字段、Boss/精英字段：PASS。
2. 总伤害：PASS，精确闭合 `103848`。
3. Boss 伤害：PASS，精确闭合 `24271`。
4. 官方承伤：PASS，精确闭合 `358`；冰属性受击正控 PASS。
5. 营地木桩排除：PASS。
6. 击杀：伤害事件少 1，需官方击杀事件。
7. 有效治疗、诅咒直接 HP 变化、死亡/复活生命周期：现有观察面不足，需最窄只读入口补充。
