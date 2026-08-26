# LC2DamageProbe 0.5.0 双样本：round-trip 精度与召唤归属

记录日期：2026-08-26（Asia/Shanghai）

## 作者给出的真实条件与官方结果

两局在同一次游戏进程中连续完成：

1. 第一局误带噩梦娃娃，官方结算为造成伤害 `7985`、承受伤害 `0`、对首领伤害 `0`、击杀魔物 `8`。
2. 第二局按要求不带召唤物，官方结算为造成伤害 `7811`、承受伤害 `151`、对首领伤害 `0`、击杀魔物 `8`。

## 冻结证据

- 最终日志：`probe_0.5.0_dual_run_20260826-225757_final.log`
  - 大小：`187,474` 字节。
  - SHA-256：`46F67E1342D0CEF2F26C17D0B33AAD7D218D3DCC9A92369D8E31593A4E50E51A`。
- 第一局结算图：`codex-clipboard-c55f60af-d227-4d58-bf40-43e4dfa67d1a.png`
  - 大小：`610,066` 字节。
  - SHA-256：`5E11EA4DAEC147CC8E20199106C9C3ACD17AAFBC38F07BFABB4D11C33E3FCBC2`。
- 第二局结算图：`codex-clipboard-d7aceb66-9271-4613-b4eb-0a99e89a53bf.png`
  - 大小：`807,463` 字节。
  - SHA-256：`E9725BAF35083A45771F2DA006F5DB75442926BCADBEB9AFD9B1A19265706CC3`。
- 探针：`LC2DamageProbe 0.5.0`，SHA-256 `57A83C4EC587D407CB1AA1A552C1207D702A5FF8E3ECEAC5F5E4DDFC8881B792`。
- 冻结时游戏和工具均已退出，日志为 final；7 个观察目标加载成功，没有 probe error、HP 栈错误、Harmony 异常或 BepInEx 错误。

## 两局切分

- 第一局本地玩家根实体为 `1000003`，其归属事件位于日志第 27–232 行。
- 第二局开始时本地玩家根实体切换为 `1000030`，其归属事件位于第 234–477 行；第二局没有任何 `attacker_is_summon=true` 事件。
- 第 233 行的 `round_start` 同时位于玩家根实体切换处，可作辅助边界；第 478 行仍是第二局内部边界。不能把每个 `round_start` 都误判为新开一局。

## 造成伤害精确闭合

0.5.0 的 round-trip 文本可恢复游戏 `float32`。对每个归属给本地玩家、`depth=0` 的命中，按以下候选计算：

```text
per_hit = ceil(max(0, min(mRealHPDamage, hp_before)))
official_damage = sum(per_hit)
```

第一局：

- 玩家直伤：90 个顶层命中，其中 6 个致死，候选合计 `6806`。
- 噩梦娃娃：11 个顶层命中，其中 2 个致死，候选合计 `1179`。
- 合计：`6806 + 1179 = 7985`，与官方造成伤害精确一致。

第二局：

- 本地玩家：116 个顶层命中，其中 8 个致死；没有召唤物攻击实体。
- 候选合计 `7811`，与官方造成伤害精确一致。

第一局娃娃有三击的 `mRealHPDamage` 分别略高于整数（例如 `126.0000076`），但写回单精度 HP 后的前后差恰好为整数。若用 `ceil(hp_before - hp_after)`，娃娃会少算 3 点；若用 round-trip 的 `mRealHPDamage` 并以命中前 HP 截断过量伤害，则精确得到官方值。这说明此前 A3 的 HP 差公式只是在该样本上等价，正式公式应使用“实际伤害字段、命中前 HP 截断、逐击向上取整”。

## 承伤边界仍未闭合

- 第一局只有噩梦娃娃承受两击，玩家官方承伤为 `0`。这确认承伤不能沿召唤物主人回溯并计入玩家卡片，必须按实际受击对象过滤。
- 第二局观察到 4 个玩家 HP 命中；逐击向上取整合计 `147`，官方承伤为 `151`，仍差 `4`。
- 因此造成伤害公式判定 PASS；承伤口径继续保持未闭合，禁止照搬造成伤害公式。

只读 interop 元数据给出一条强线索：`SettlementDataMgr.OnDamageAndBossDamage` 的编译闭包保存整数 `finalDamage`，而 `SettlementDataMgr.OnTakeDamage` 的相邻编译闭包保存整数 `oriFinalDamage`。这支持“官方承伤使用减伤前 `mOriFinalDamage`，实际 HP 扣血使用减伤后字段”的假设，但当前 0.5.0 日志没有输出原始伤害，尚不能凭字段名直接裁决。探针 0.6.0 只增加 `ori_final` 与 `final_clamp` 两个观察字段来做正控。

## 当前裁决

1. `LC2DamageProbe 0.5.0` 自然启动、7-patch 加载与战斗字段：PASS。
2. round-trip 浮点输出：PASS，消除了 0.4.0 的三位小数信息损失。
3. 玩家直伤与召唤物归属后的官方造成伤害公式：两个新样本均精确闭合。
4. 无召唤物负控：PASS；第二局没有召唤攻击实体。
5. 承伤公式：未闭合，仍需独立调查。

后续 0.6.0 多层减伤样本已确认该分叉：官方承伤逐击使用减伤前 `mOriFinalDamage`，详见 `../probe_0_6_reduction_take_damage_20260826/README.zh-CN.md`。
