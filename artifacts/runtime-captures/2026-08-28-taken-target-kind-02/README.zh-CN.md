# 0.3.6 玩家/召唤物承伤目标正控

记录时间：2026-08-28（Asia/Shanghai）

## 结论

- 根因已确认：官方 defender 回调同时包含玩家根实体和召唤物 defender，0.3.6 未过滤目标，导致召唤物承伤进入玩家“官方承伤/实际掉血”。
- 作者实机顺序为召唤物先受伤、玩家后受伤。receipt 中召唤物对应同一匿名目标 `target-3`，`target_kind=normal`；玩家对应 `target-9`，`target_kind=player`。
- 正数 `taken` 合计为 `290`：召唤物目标贡献 `246`，玩家目标贡献 `44`。这不是传输重复，采集器记录 `257` 个接受事件、`0` duplicate、`0` transport/validator fault。
- 先前混合短局的 Bridge `70` 对官方 `35` 因而不应按二硬除；应在 Bridge 的 taken 分支只保留玩家根 defender。

## 决定性事件

| sequence | target_kind | target_alias | settlement_damage | applied_hp_damage |
| ---: | --- | --- | ---: | ---: |
| 19 | normal | target-3 | 44 | 43.55 |
| 39 | normal | target-3 | 35 | 34.14 |
| 97 | normal | target-3 | 44 | 32.33 |
| 105 | normal | target-3 | 35 | 33.09 |
| 117 | normal | target-3 | 44 | 44.85 |
| 136 | player | target-9 | 44 | 42.24 |
| 137 | normal | target-3 | 44 | 41.80 |

后续 `target-3` 还有多条 `settlement_damage=0`、`applied_hp_damage=6` 的非玩家事件，不进入上述官方承伤正数合计。

## 采集限制

- 采集在决定性事件之后从 sequence 179 起收到 Bridge `status=error`；脱敏 allowlist 当时未保留 `detail`，因此不能从本 receipt 判断错误原因。
- 该状态不否定此前目标身份与承伤合计证据，但必须在 0.3.7 过滤候选实测时确认不再出现。
- 文件中的 `target_alias` 仅为本 session 临时别名，未保存原始实体 ID、账号或平台身份。
