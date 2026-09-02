# LC2 工作7重启checkpoint（2026-08-31 23:35 Asia/Shanghai）

> 本checkpoint已完成恢复；当前短入口已接续到`docs/LC2_WORK_7_R7_SHORT_CONTROL_2026-09-01.zh-CN.md`。以下身份保留为重启前历史证据，不再代表当前部署。

## 恢复入口与角色

- 这是LC2工作7唯一当前重启checkpoint。恢复后先读项目/工作区`AGENTS.md`、本文件和当前diff；不要重放图片聊天或67KB旧handoff。
- 目标仍是工具箱1.6.3多人伤害准确、exact package/UI冻结与发布前审计。当前不得commit、push、Release或恢复latest。
- 作者可能立即重启电脑。重启后所有PID/句柄均视为失效，先重新核对Git、进程、游戏DLL、包/桌面和冻结日志身份。

## Git与发布身份

- 仓库：`<repo>`，branch `main`。
- HEAD / local origin/main / remote main：`758db3ae731613e2c3e4fcbfb9d7fd0058286f66`，tag `v1.6.2`。
- 工作树仍为工作6/7连续未提交实现与证据；不要reset/clean，不要吸收无关路径。恢复后重新`git status --short --branch`和`git diff --check`。
- GitHub v1.6.2仍为预发布，标题“暂缓下载：v1.6.2 多人伤害少算，等待 1.6.3 复测”，资产下载数0；无新Release。

## 当前候选/部署身份

- Bridge源码/包/游戏目录：0.4.17，69,632 B / `EA17B678BDFBCD17066507204D7F9B730A7D56D8AD09E894CFAE810564EDA00B`。
- 游戏目录PDB：27,232 B / `6446E59CD1A082A458089B77676E11C326FB404E263CF227A4251A9B056642EF`。
- rollback 0.4.16：`artifacts/runtime-deploy/2026-08-31-bridge-0.4.17-zero-real-final-fallback-r6/`。
- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 桌面r6：`<desktop>/失落城堡2工具箱1.6.3-变身伤害fallback最终结算版-r6`。
- r6 package/desktop：1,761文件、166目录、166,655,009 B、config0、逐文件差异0；EXE `F656BDD695486A85072034329F7423E11ECC4DAF877D0FDA327A5A4A8FD423F4`。
- runtime manifest：`88F2A6D482403CF455D7B39FFE5C6A0CACD75CF62C0EE4903559A91DC8C011B1`。
- 离线门：201项PASS；SDK6.0.428 + 当前interop Release 0 warning/0 error；package self-test/runtime正负控PASS。

## 本次最终多人样本（0.4.17，特别卡）

- 用户一手观察：本局特别卡；自己的HUD从开局就偏离，整体/其他人已明显更接近官方。需考虑客户端卡顿时“本地命中怪物，但主机已判怪物死亡”的幽灵命中。
- checkpoint时游戏/工具箱仍运行：游戏PID10352、r6工具箱PID22756；重启后不得复用。
- 冻结证据：`artifacts/runtime-captures/2026-08-31-final-laggy-mindex-zero-0.4.17/`。
  - live checkpoint日志：5,794,413 B / `8DE308AABBEF8CF2B20F3E3756A2526361CEA2C3B5E5701EB8BA68AA0361C4B4`。
  - 最终四卡+HUD截图：3,985,202 B / `F4C31B221394C66E646BA1B1A06ACE1743352C066DBAF33D4EC573B912B59053`。
- 游戏四张官方卡（截图从左到右，UI把本机放第一，不能直接等同slot顺序）：
  - 加菲beatrix：18,804,040 / Boss 6,883,592。
  - 鲨鱼：3,300,109 / Boss 944,663。
  - V：8,190,592 / Boss 2,933,953。
  - 药：11,651,860 / Boss 4,382,389。
  - 团队官方：41,946,601 / Boss 15,144,597。
- Bridge日志本机slot=3。最终截图HUD个人为30,202,440 / Boss13,229,901；若第一张官方卡确为本机，则高算11,398,400 / Boss6,346,309。
- HUD远端可见值：P2=7,181,504/Boss3,429,666，P3=11,811,670/Boss6,509,588；P1伤害被截图边界裁掉、占比6%、Boss1,051,265。不要伪造缺失P1值。

## 已确认结论

1. **owner/slot事件链稳定**：本局registered unique=39,997，Settlement unique=39,997，matched=39,997，duplicate callback conflict=0；四slot owner conflict/unresolved均0。网络卡顿没有造成Bridge内部slot冲突或pipe漏事件。
2. **0.4.17 zero-real fallback不是本机偏差来源**：最终fallback仅slot0 `10次/10,841`、slot1 `2次/6,009`、slot2 `34次/21,953`；本机slot3无fallback。因此本机30.2m高算不是新fallback引入。
3. **最终SyncEnd触发但映射失败**：两次final摘要均为`final_ready=true final_records=4 final_raw_indices=0,0,0,0 final_duplicate_slots=1 final_published_slots=0 final_accepted=false`。安全门正确拒绝整组发布；HUD继续显示客户端逐击估算。
4. **mIndex运行时假设被证伪**：尽管native构造路径能写Player.Index，本机最终save list的四条`mIndex`实际全0，不能再把mIndex作为这个最终客户端路径的slot唯一事实。
5. **卡顿可能导致客户端估算高算**（推断，不是已证根因）：本地仍生成damage callback而主机/服务端已判目标死亡时，客户端逐击值可能计入HUD但不进入最终官方record。这能解释本机明显高算，且不会表现为queue/owner conflict。需要最终官方record覆盖，而不是继续调逐击公式。
6. **0.4.16退局closing修复已在上一局真实通过**；本次checker又报`phantom_session_after_round_start`，可能是完成后进入合法新局导致的checker状态机误报，需重审checker，不能直接记回归。

## 仍未闭合

- 最终save list四条record在mIndex全0时如何稳定映射到P1-P4。必须先静态核对参考DLL`ResolveStableSlot/ReadGameSaveBaseline`与真实list/roster顺序；不要直接复制4槽ordinal heuristic。
- 当前日志没有记录final record的ordinal Damage/BossDamage，也没有记录不暴露身份的record↔roster相等关系，因此无法仅靠现日志证明save list顺序。
- 若静态证据不足，下一候选只能增加隐私安全的最终record诊断（ordinal、damage、boss、与当前Player对象身份比较结果），不得再请求完整长局前盲改映射。
- 本次未做exact package/UI最终冻结、different-owner综合审计、commit/push/Release。

## 三个新MOD只读预调查

- 原始目录：`<local-mod-library>`；尚未集成、未执行第三方逻辑。
- `我不是药神F1.zip`：39,855 B / `04F3E04E78B42FB264A90E60D0F670B957FF8C914CA24EA233055C0B2BD3FDD0`。
  - 现有`not-drug-god`的同GUID/同版本1.0.0新构建；最小载荷`LC2NotDrugGod.dll` 88,576 B / `520078096A03DFF18F7572A695ABF7529E93E32B790F531ACA2E7BC103E74A86`。
  - 新增per-player状态/宝箱观察迹象，但说明仍写仅单人、联机待测试；不能静默覆盖现有84,480 B载荷。
- `LC2BossCinematicFree_v1.4.1源码.zip`：46,233 B / `D7F5EA8206612D58135A6B3E448A7E794C6A1D6E1747F3DAE61ADF67AAF9C074`。
  - 最小载荷`LC2BossCinematicFree.dll` 27,136 B / `51E404FA31A3719527F75AC7D98D8640B760A6FAEC65AD9174C11E5481CFFFC6`；v1.4.1，无热键，上传者空容。
  - 与增强计划精确重叠BossEnter Start/End；源码称可共存但仍需组合负控。
- `LC2BossControl源码.zip`：126,243 B / `524EFCAE21FCA7513DA39ADA3FFD46F378FAD9E5A8E1574ECB5871B4449938DF`。
  - 最小载荷`bin/Release/net6.0/LC2BossControl.dll` 52,224 B / `1FD8AF8BD2BD24275AC123F54E6D0BCAE036B14D5517528E7D0823AEB288C71B`；v0.2.2，F6，仅单人，上传者空容。
  - `Boss.OnSpawned`与恶魔入侵/动态血量/增强计划/雷灵召唤等重叠；F6与玩家实时属性、刻印灵魂石管理器冲突。只允许隔离实验，暂不进默认包。
- 三包完整性与路径安全PASS；依赖均由现有BepInEx/core和游戏interop提供；源码包无明确许可证。两个源码csproj带自动部署目标，未来隔离编译必须禁用/覆盖，不能直接默认build。

## 重启后最便宜下一步

1. 重核Git、进程双零、游戏/包Bridge哈希、checkpoint日志/截图哈希。
2. 只读完成final save list映射静态审计：参考DLL`ResolveStableSlot`、`ReadGameSaveBaseline`，游戏record list构造/排序与PlayerList关系。
3. 纠正checker对合法新局的phantom误报条件。
4. 若映射仍缺证据，做最窄final-record诊断源码/测试/构建；不得部署直到新双零，不得要求作者再打完整长局来替代静态证据。
5. 多人准确性闭合前，三个新MOD只保留预备记录，不阻塞主线、不进入当前最终候选。

## 禁止事项

- 不重跑已闭合MP、121/119承伤/HP、0.4.8回营补满。
- 不新增角色/武器/Boss/道具/固定数值特判。
- 不把201项测试、39,997回调或fallback诊断外推为最终多人准确。
- 不commit、push、Release、恢复latest；不让作者重复完整长局；不在游戏/工具箱进程非零时部署或self-test。
