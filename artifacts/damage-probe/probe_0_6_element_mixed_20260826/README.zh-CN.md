# LC2DamageProbe 0.6.0：法杖投射、元素附魔、毒 DOT 与爆炸混合样本

记录日期：2026-08-26（Asia/Shanghai）

## 作者给出的两局条件

两局在同一次游戏进程中连续完成：

1. 第一局使用电系法杖并携带宝藏“不融冰”。加点描述说明魔法弹属性取决于当前拥有的元素加成宝藏数量、默认火属性；作者在实战画面中观察到最终表现为冰伤。最初忘记截图，随后从对局记录找回：官方结算为造成伤害 `7703`、承受伤害 `37`、对首领伤害 `0`、击杀魔物 `8`。
2. 第二局使用毒法杖并携带毒桶；作者观察到毒伤与火伤并存。官方结算为造成伤害 `7599`、承受伤害 `37`、对首领伤害 `0`、击杀魔物 `8`。

## 冻结证据

- 最终日志：`probe_0.6.0_element_mixed_20260826-232746_final.log`
  - 大小：`276,635` 字节。
  - SHA-256：`BCE83D9CAF50FE9AE1E445B956F29BDC4742E5D1383585ADEAD6EB6A9BC403B3`。
- “不融冰”截图：`codex-clipboard-6b979ea3-4b24-45c5-ab2b-492abc0f1957.png`
  - SHA-256：`84FB73D647254A9E4E0CBAA437C832AA370B43C5A8174BFE7E40FE3B01A6D5F7`。
- 电系法杖截图：`codex-clipboard-3404688f-aeb0-4ee7-ab68-356097968904.png`
  - SHA-256：`DE361F4FCC11B3475256E85376FD58731923989BFD05B10D9C295887387875CB`。
- 元素附魔规则截图：`codex-clipboard-c1de162c-287a-4559-ad34-f7bf800d5227.png`
  - SHA-256：`692538DE6658D1CA9134109C09BB150703ECB5A674999F32AF930248E61A9430`。
- 冰属性状态截图：`codex-clipboard-bc95267b-ed1c-464e-b916-936a8becc42b.png`
  - SHA-256：`87B51B6E7DD56B3115BE4AA6C45B7D422E4DE706B205A959C74951A7690FC953`。
- 第二局结算截图：`codex-clipboard-1f8beb12-efd9-4bc2-b010-00e7aa6b615b.png`
  - SHA-256：`EDCC8B160F53A52DB362BD2351749060377DFD410D696DC9CD4D0D5C4D42560B`。
- 第一局补回的对局记录截图：`codex-clipboard-5b87eef3-9a82-46e2-928e-3660ba9068ad.png`
  - 大小：`703,197` 字节。
  - SHA-256：`39CC80E7F7F9DD1B6D330158D96C6EA61BDBCAF6BEA046BAD8E14644839D0CD7`。
- 探针：`LC2DamageProbe 0.6.0`，SHA-256 `58B26D29CE0FC28AFEDFCC774386B30DDA1D034D8C48D79E36B17E761D694516`。
- 冻结时游戏和工具均已退出，日志为 final；7 个观察目标加载成功，没有 probe error、HP 栈错误、Harmony 异常或 BepInEx 错误。

## 两局切分

- 第一局本地玩家根实体为 `1000003`，归属事件位于日志第 34–288 行。
- 第二局开始时玩家根实体切换为 `1000033`，归属事件位于第 291–664 行。
- 第 290 行 `round_start` 与玩家根切换重合，可作两局边界；第 666 行仍属于第二局内部边界。

## 第一局：冰附伤嵌套事件精确闭合

- 126 个唯一 `official_attacker` 事件，其中 119 个 `depth=0`、7 个 `depth=1`；全部都能按 hit ID 与自己的 HP 快照关联。
- 法杖白弹 `Staff_BulletWhite`：111 个顶层事件，逐击候选 `5160`。
- 宝藏/投掷路径 `Un_Common_CantGrabRidingEnemies`：8 个顶层事件，逐击候选 `1485`。
- 7 个嵌套附伤事件：`NotExactlyAttack`，每个都有独立官方攻击事件与独立实际伤害，逐击候选合计 `1058`。
- 合计：`5160 + 1485 + 1058 = 7703`，与官方造成伤害精确一致；8 个致死事件与官方击杀 `8` 一致。
- 第一局唯一玩家受击的 `ori_final` 逐击候选为 `37`，也与官方承伤 `37` 一致。
- 0.6.0 没有记录 `AttrType`，因此日志只能证明法杖弹与宝藏派生路径存在，不能独立确认画面表现的冰属性，也不能从法杖图标反推最终附魔属性。

这组证据修正了此前过严的深度门：只要 hit ID 唯一、来源已归属且存在 `official_attacker` 事件，`depth>0` 的元素附伤也属于官方总量。`depth` 用于保留父子关系并防止直接用外层 HP 总差重复累计，不能单独作为排除资格。

## 第二局：毒 DOT、毒桶、爆炸与法杖弹精确闭合

第二局有 182 个可计算的顶层官方攻击事件，8 个致死命中与官方击杀 `8` 一致。按来源聚合：

| 来源 | 事件数 | 逐击候选 |
| --- | ---: | ---: |
| `Staff_BulletWhite` | 70 | 2940 |
| `Staff_BulletBlack` | 10 | 726 |
| `Un_Common_PoisonDamage` | 28 | 363 |
| `Un_Common_CommonPoisonSpring` | 1 | 76 |
| `Un_Common_ExplosionDamage` | 7 | 1428 |
| 其余已归属的 `None` 来源 | 66 | 2066 |
| 合计 | **182** | **7599** |

按归属路径聚合：玩家本体 `363`，`OwnerEntity=玩家` 的法杖/桶/爆炸子实体 `6536`，`OwnerPlayer/Master=玩家` 的机制派生实体 `700`；三类合计同样为 `7599`。这证明毒 DOT、毒桶/毒泉、爆炸和独立法杖投射实体都能沿现有归属并集进入官方总量。

第二局唯一玩家受击的 `ori_final` 逐击候选为 `37`，也与官方承伤 `37` 一致。

## 元素身份边界

- 日志名称明确确认毒 DOT、毒泉和爆炸来源，但 `Staff_BulletWhite/Black` 与 `ExplosionDamage` 名称不携带火、冰、电等最终 `AttrType`。
- 作者观察到第一局电系法杖最终出现冰伤、第二局毒与火并存；这些第一手画面观察保留为正控线索，不能被当前日志反驳或替代。
- 游戏 interop 枚举确认元素类型为 `Fire/Ice/Poison/Electric/Evil/Blood`，并提供 `CheckDamageMainAttrType` 与 `CheckDamageAttrType`。下一探针只需记录这两个只读判定，不需要新 hook。

## 当前裁决

1. DOT 来源归属：PASS（毒 DOT 28 跳）。
2. 独立法杖投射实体归属：PASS。
3. 毒桶/毒泉与爆炸来源归属：PASS。
4. 第二局混合来源官方造成伤害：PASS，精确闭合 `7599`。
5. 第一局冰附伤混合总量：PASS，精确闭合 `7703`；元素最终 `AttrType` 仍因 0.6.0 未记录而待只读字段正控。
