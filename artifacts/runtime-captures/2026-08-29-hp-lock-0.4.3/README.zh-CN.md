# Bridge 0.4.3 生命锁定真实正控

生命周期：`R-PASS / AUTHOR CONFIRMED / LOCAL SCREENSHOT EVIDENCE`

截图和运行日志本身被 `.gitignore` 排除；本 README 只保留可提交的最小结论与本机恢复定位。

## 运行身份

- 工具箱：桌面 `1.5.12-锁血兼容测试版`，EXE SHA-256
  `4E48267FFDBB5868FFC0890FBC67E7B74CB2B2353EC38A5EB8404FABEB8DAD31`。
- Bridge：BepInEx 明确加载 `LC2 Combat Bridge 0.4.3`，候选/包内/游戏目录均为
  `46,592` B / `2837F6C485F691BB743CEAF3EB5EBE2BB5FA1D66A19E1FB2D4B87F029CF562A3`。
- 日志包含 `Combat bridge client connected; local stream active`；本轮 Bridge
  `resource_conversion_failed`、`resource_stack_mismatch` 与显式 Error 匹配均为 0。

## 正控结果

- 作者先在 1.5.11 稳定复现：选择锁定 65% 生命后 HUD 立即变“异常”。
- 使用 1.5.12 / 0.4.3 重新完成一局后，游戏画面为 `49/140`：真实最大生命仍是 140，
  可用当前生命上限是 `140 × 35% = 49`，与“锁定 65%”语义精确一致。
- 同帧 HUD 仍为绿色“实时”，保留黑森林第 8 区结算：总伤害 `63,952`、Boss
  `26,969`、受击承伤 `205`、回复 `191`、法力消耗/恢复 `162/162`。
- 结论：65% 生命锁定不再触发 schema fail-closed；锁血直接负 HP 没有污染受击承伤或
  回复，已有伤害与法力聚合继续运行。

## 本机截图定位

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `game-window.png` | 6,028,396 B | `77DA95C3953CF51E79FF6E493B9129163CD1762798313E0B609EDC76D806D3E7` |
| `hud-screen.png` | 21,219 B | `18BAF27B134DB9922E62CC07BE299212C989A66F18706E954A44D6FEF2DFEA2C` |

`toolbox-main.png` 是同一 HUD 的 PrintWindow 复本，不作为独立证据人口。

## 未外推

- 20%/40% 档位已有同合同自动测试，但本轮没有逐档真实选择。
- 冠军腰带实际 max 下降、洗掉诅咒、药剂/宝物 max-only 变化仍未形成单独真实正控。
- 2P–4P 队友独立锁血与本地资源过滤仍为 `NOT RUN`。
