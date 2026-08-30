# 0.4.8 回营补满排除实机闭合

- 记录时间：2026-08-30 16:31 +08:00。
- 生命周期：`IN-MAP HEALING R-PASS / OFFICIAL TAKEN R-PASS / SETTLEMENT REFILL EXCLUSION R-PASS`。
- Bridge：0.4.8，49,152 B / SHA-256 `7740BA3E30CD8C8B73F8BFDF221C3384CB2D64F940699A6974556E989896CE55`。
- 冻结日志 `LogOutput.live-copy.log`：79,094 B / SHA-256 `8D99B8B57CF986DA5961EF79D32754491C181480042D73D205B5AE9D23D66B88`。
- `author-room1-healing-43.png`：1,349,721 B / `025B43FB760D480315A07097979B354DC8910CB900BD19B2CBEA0F195058A78D`。
- `author-room2-before-return-healing-59.png`：476,517 B / `7E22A9025A96E2E8D8CEA4751F61F994D08CDE63FB524AADDC77CB2EB87F31E5`。
- `author-settlement-healing-69.png`：593,585 B / `8A894963812C36CF7E20D983CFB47729552D3F0E8471562E9784DBAEE1D55960`。
- 图片/日志本体按仓库 ignore 合同保留，本 README 冻结身份、计算和判定。

## 局内正控

- 48 个 `in_map=True` 正向 HP 事件合计 `68.90609741210938`，UI/结算边界显示 `69`。
- 来源拆分：`Gem#A_015_2` 31 次 / `30.8654880524`；无 token 的周期恢复 13 次 / `14.3649940491`；香蕉 3 次 / `21.2999954224`；`Battle#Battle_ClearStageStatus_1` 1 次 / `2.3756198883`。
- 作者截图依次显示第一房回复 `43`、第二房返回前回复 `59`、结算回复 `69`，证明战斗中真实恢复持续计入且保持实时。

## 官方承伤正控

- 两次受击的官方 `settlement_display` 均为 `46`，合计 `92`；游戏结算与 HUD 也均为 `92`。
- 两击 `original_raw` 合计 `90.3167953491`，逐击向上取整为 `46+46=92`；实际 `applied_raw` 合计 `86.2525405884`。这再次确认官方承伤与实际 HP 变化是独立口径，不合并。

## 回营补满排除

- 日志第 253 行先触发 `[LC2CB-ROOM] callback=round_end_preload_camp`，当时仍为黑森林第 2 区。
- 第 254 行游戏在回城途中执行 HP `31.8978786469→123.0346679688`，有效补血 `91.1367874146`；该事件明确为 `in_map=False / inside_damage=False`。
- 第 255 行随后才触发 `round_start is_camp=True`。因此 0.4.8 的预加载边界早于补满，RoundStart 仅作为末端兜底。
- 回营补满是日志中唯一有效的 `in_map=False` 正向事件，没有进入局内 `68.9060974` 或 UI `69`。作者也确认回城过程中游戏仍会回血，但工具箱没有异常突增。

## 判定

- `SETTLEMENT REFILL EXCLUSION R-PASS`。0.4.7 的确认反例 `101.3999939` 已由 0.4.8 的通用生命周期边界关闭。
- 修复不依赖请求值、满血形态、Boss、装备、刻印或道具名；保留局内真实恢复、官方承伤及实际 HP 变化的既有口径。
- 不重跑已闭合的 MP、0.4.5 长局或 0.4.7 121/119 样本。多人真实联机与第三方 MOD 游戏逻辑仍为 `NOT RUN`。
