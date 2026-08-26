# 0.10.0 玩家 HP 覆盖方法漏记负控

记录日期：2026-08-27（Asia/Shanghai）

## 冻结证据

- 日志：`probe_0.10.0_player_hp_override_negative_final.log`
- 大小：`59,070` 字节，`196` 行。
- SHA-256：`629B7B1897B357BE985E452B29EF4AA10E7C9AA537D8289FF829E71C06A18E19`。
- 自然启动加载 `LC2 Damage Probe 0.10.0`，10 个观察目标全部挂载。
- 游戏已完整退出；日志没有 probe、Harmony 或 HP observation 错误。

## 运行时负控

本局有两个以本地玩家 `1000003` 为受击者的 `official_defender` 事件，并有对应 HP 快照：

1. `140 → 96.647934`，实际扣血 `43.352062`。
2. `96.647934 → 75.19769`，实际扣血 `21.45024`。

但同一日志中：

- `hp_change=0`
- `hp_set=0`
- `hp_food_recover=0`

因此，0.10.0 的三个 HP 观察点没有覆盖这两次已证实的玩家 HP 写入。作者是否在本局使用香蕉尚未获得明确口述确认，所以本记录只裁决“玩家 HP 覆盖失败”，不能把该局单独标成第二个香蕉恢复失败样本。

## 静态追踪与下一候选

当前 `LC2.Core.dll` interop 显示：

- `CreatureRuntimeData.ChangeCurrentHp(...)` 是虚方法并创建新虚槽。
- `HeroRuntimeData.ChangeCurrentHp(...)` 覆盖该方法。
- `MonsterRuntimeData.ChangeCurrentHp(...)` 也有独立覆盖。

0.9.0/0.10.0 只 patch 了 `CreatureRuntimeData.ChangeCurrentHp` 基类方法。结合本局玩家扣血负控，最窄候选是玩家实际走了 `HeroRuntimeData` 覆盖方法，而 Harmony 的基类 patch 没有自动覆盖该实现。

0.11.0 因此只新增 `HeroRuntimeData.ChangeCurrentHp` 前后观察，并保留既有 operation/parent/depth 去重。该静态解释仍需自然启动和一次玩家 HP 变化正控确认。
