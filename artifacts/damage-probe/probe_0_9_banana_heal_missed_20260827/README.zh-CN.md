# 0.9.0 香蕉有效恢复漏记样本

## 作者实测

- 玩家生命上限为 `140`。
- 使用“神奇的香蕉藤”连续吃了 `10` 根香蕉。
- 倒数第二根只恢复到满血，剩余恢复量溢出。
- 最后一根在满血时仍触发了恢复操作，但有效恢复量为 `0`。

这组操作同时提供了部分有效恢复与零有效恢复两个边界正控。作者观察是本样本的屏幕语义依据；图片只作装备与上限佐证，不从静态截图反推每根香蕉的精确数值。

## 0.9.0 运行证据

- 日志：`probe_0.9.0_banana_final.log`
- 日志 SHA-256：`CD67B4DDF07C6350DB321DA600BC13A194F8B200DAFCD17C1D03553C4341A93E`
- 日志大小：`45,508` 字节。
- 自然启动加载 `LC2 Damage Probe 0.9.0`，8 个观察目标全部挂载；其中包括 `LC2.CreatureRuntimeData.ChangeCurrentHp`。
- 日志未出现 probe error、Harmony 加载错误或异常。
- `kind=hp_change` 事件数为 `0`。

## 判定

- 0.9.0 加载门：**PASS**。
- 香蕉/进食恢复覆盖：**FAIL**。
- 原因边界：本次香蕉恢复没有经过已观察的 `CreatureRuntimeData.ChangeCurrentHp`；这证明路径选择不完整，但尚不能仅凭该负结果断言游戏内部唯一实现。
- `effective_heal` 公式本身没有获得本样本验证，不能把“零事件”误报成“有效恢复为 0”。

## 下一步

将观察面下沉到 `CreatureRuntimeData.SetCurHP(float)`，并在香蕉的高层入口 `FullFoodEnergyOrRecoverHp(Creature,float)` 同时记录前后 HP。嵌套观察携带 operation、parent 与 depth；聚合只累计最外层有效 HP 上升，避免同一次恢复被高低两层重复计算。

## 附件

- `banana_treasure.png`：SHA-256 `D897F7DCA35B29E5B165D364534005E9B356E82A6BE424260C90CD0CCDA1D847`
- `player_max_hp_140.png`：SHA-256 `B68891E931648B645759195FF4C681645BC735C4B43EAF4F514492A299B07833`
