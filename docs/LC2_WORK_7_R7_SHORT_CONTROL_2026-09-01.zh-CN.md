# LC2 工作7 r7短房正控入口（2026-09-01 Asia/Shanghai）

> 本入口已由`docs/LC2_WORK_7_R8_PASSIVE_FINAL_CHECKPOINT_2026-09-01.zh-CN.md`接续；以下保留为r7历史测试说明。

## 当前身份

- Git：`main`，HEAD/origin/main=`758db3ae731613e2c3e4fcbfb9d7fd0058286f66`；工作树为工作6/7连续未提交实现与证据。不得reset/clean、commit、push或Release。
- Bridge源码/候选/包/桌面/游戏目录：0.4.18，71,680 B / `1D8272C3B22993D45B822ED5291FA704A4FDB78287E1E83A26412761A83CFDDF`。
- 游戏PDB：27,764 B / `8595D66EC950C8A1C64A322A6720F72C8F58751EC105FC316ED4C8096D1A7AE5`。
- rollback 0.4.17：`artifacts/runtime-deploy/2026-09-01-bridge-0.4.18-final-identity-map-r7/`。
- 桌面盒子：`<desktop>/失落城堡2工具箱1.6.3-官方身份映射短测版-r7`；1,761文件、166目录、166,657,072 B、config0，与项目包逐文件差异0。

## 为什么是0.4.18

- 冻结0.4.17特别卡四人长局：registered/Settlement owner链39,997/39,997且冲突0；zero-real fallback未命中本机slot；但final save list四条record的`mIndex`全0，旧安全门拒绝发布。因此客户端逐击估算不能作为最终多人准确值。
- 原生`StatisticsMgr.SyncMultiplyRoundData`从record读取`mID/mPlatformUniqueID`并传给`SetAdventureRecordPlayerData`；参考伤害DLL只使用mIndex/ordinal，也不能处理全零反例。
- 0.4.18只用随机进程密钥HMAC final record与历史roster的PlatformUniqueID并要求一一唯一匹配。原始身份和指纹都不记录、不发送；mID、昵称、ordinal和固定人数不参与。缺失/碰撞/额外record/重复slot/数量不等时整组拒绝。

## 已过离线门

- pytest：`206 passed + 37 subtests`；build内unittest 206项。
- SDK6.0.428 + 当前interop Release：0 warning / 0 error；16个Harmony target。
- 包self-test exit0；首次/重复运行时安装PASS；不同core写前阻断PASS。
- final checker known-good：四record全零mIndex、四身份唯一匹配PASS。
- positive control：冻结0.4.17长局owner子门PASS、final官方门按预期FAIL。
- 部署前2026-09-01T00:38:43与00:38:54双零；部署后仍零。

## 下一次只做短房

1. 只启动桌面r7盒子；进入至少3人房（本机+至少2个远端P）。
2. 只打一到两个房间；让两个远端P各产生伤害，本机最好各做一次普通/召唤与变身伤害。不需要打完整局。
3. 不要由本机单独退出多人；这会折叠成继续单人冒险的团队摘要，不能校准逐P。应让多人局本身在一到两个房间内快速失败/全队团灭，等真正的四人结算卡出现，再关闭游戏和盒子。
4. 冻结新日志后运行：`py -3 tools/check_lc2_multiplayer_probe.py <LogOutput.log> --require-final-official`。owner和final官方两门必须同时PASS；任一失败立即停止，不请求完整长局。
5. 短房PASS后，才允许作者再做一次唯一最终结算；失败则只回到离线证据，不增加武器/技能/角色/Boss/数值特判。

三个新MOD仍只读预备，不进入r7，不阻塞多人主线。exact package/UI最终冻结、different-owner综合审计、commit/push/Release均未执行。
