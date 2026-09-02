# LC2 工作7 r8被动自然结算入口（2026-09-01 Asia/Shanghai）

> 本入口已由`docs/LC2_WORK_7_R9_AUTO_ARCHIVE_CHECKPOINT_2026-09-01.zh-CN.md`接续；以下保留为r8历史状态。

## 当前身份

- Git：`main`，HEAD/origin/main=`758db3ae731613e2c3e4fcbfb9d7fd0058286f66`；工作树仍为工作6/7连续未提交实现与证据。不得reset/clean、commit、push或Release。
- Bridge源码/候选/包/桌面/游戏目录：0.4.19，72,704 B / `03BD7A7057C4408A475626E57AA2B4F99594E769AB6FC069CF9AE0366646C06D`。
- 游戏PDB：28,144 B / `56C2F2856F7ECBA63BE2F364F24BA101F4516DC9A28565D78DD6BC453257D93F`。
- rollback 0.4.18：`artifacts/runtime-deploy/2026-09-01-bridge-0.4.19-final-acceptance-freeze-r8/`。
- 桌面盒子：`<desktop>/失落城堡2工具箱1.6.3-官方结算冻结版-r8`；1,761文件、166目录、166,658,093 B、config0，与项目包逐文件差异0。

## r7已闭合证据

- 真实四人最终记录首次完整接受，四槽Damage/Boss与官方四卡逐项一致，包括中途断线P3：匿名身份映射PASS。
- 第二次三人roster刷新改写终局身份并撤销accepted：final stickiness R-FAIL。
- owner整局13,752/13,752 matched，四slot冲突/未解析/重复0。
- 局内“异常”来自墓园第4区唯一一次`damage_snapshot_missing`；无queue overflow、stack mismatch、owner conflict或fatal。该项仍独立开放，r8未掩盖。

## r8窄修复与门

- 首次完整`final_accepted=true`时冻结slot→原会话匿名token与官方Damage/Boss；后续final/roster刷新只复用冻结值，下一局统一reset。
- 不改伤害、fallback、owner、协议或UI，不新增角色/武器/Boss/道具/数值特判。
- pytest `208 passed + 37 subtests`；build内unittest 208项；SDK6.0.428 + 当前interop Release 0 warning/0 error；包self-test/runtime正负控PASS。
- 冻结r7日志positive control必须报`final_acceptance_regressed`；合成稳定accepted known-good PASS。

## 下一步改为被动确认

- 不要求野队团灭，不安排专门完整长局。作者以后按正常玩法自然出现多人最终结算时，使用r8并保留一张“四卡+HUD”截图即可。
- 预期：final摘要连续保持4 matches、4 published、accepted=true；HUD四项与官方四卡逐项相同，即使有人中途断线。
- 被动确认前：exact release、different-owner综合审计、commit/push/Release仍不执行；v1.6.2继续暂缓下载。

三个新MOD仍只读预备，不进入r8，不阻塞多人主线。
