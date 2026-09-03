# 短测与验收摘要

本页只公开足以理解工程结论的短摘要，不包含原始日志、截图、ZIP、本机路径、进程/窗口句柄、会话标识、玩家昵称或平台账号。

## 启动性能

- 三臂：原版、BepInEx-only、BepInEx + Bridge。
- 暖启动主菜单中位上界约为 16.46 秒、22.71 秒、20.97 秒；Bridge 相对 BepInEx-only 未形成可辨认附加回归。
- Chainloader 中位差约 22 毫秒，低于本次轮询与批写粒度，不能宣传为性能优势。
- 退出残留在原版和 BepInEx 组都出现过，不能归因给 Bridge。

## 多人身份与官方结算

| 批次 | 结果 | 决定性证据 |
| --- | --- | --- |
| r2 | FAIL | 54/54 官方摘要都把 record 塌缩到本机槽位；确认 `mID` 不是可用玩家网络身份 |
| r3 | FAIL | `mIndex` 与临时官方容器的生命周期不足以支持持续房内显示；自动测试不能替代真实多人 |
| r4/r5 | PARTIAL PASS | registered owner 208/208 与 Settlement 对齐，槽位冲突为 0；退出后 phantom session 仍失败 |
| r7 | PASS | 四条最终 record 经匿名身份一一匹配，断线玩家保留；首次完整 final 冻结后不被 roster 收缩覆盖 |
| r9/r10 | FAIL | 旧结束事件曾生成 74 个小 ZIP，证明重复结束信号和当前全局摘要不能直接组成归档 |
| r11 | PASS | 新 session 明确清空上一局聚合、身份和冻结状态，跨局累计门闭合 |
| r19/r20 | PASS（限定口径） | 479 个完整样本证明 Statistics cache-list 房内逐槽单调；`active + cache` 在已测房间切换中守恒 |

## r23 正式候选实测

- 四人高延迟撤退：realtime、owner 与 rollover 通过；本样本没有自然 SyncEnd，因此 SyncEnd 为 `NOT RUN`。
- 双人自然完整局：SyncEnd、逐玩家 official、Boss 与身份映射通过；一名玩家从过程 750,867 向上校正为 825,048，另一名从 1,168,246 向下校正为 1,002,936。
- 该双人局同时出现游戏侧符文异常，未确认与工具箱有关；因此只用于统计链证据，不冒充“玩法完全无异常”样本。
- 由这些结果形成 UI 合同：Mini HUD 为“实时”，发生跳过时为“实时 · 跳过”，完整 SyncEnd 后为“官方”；详细界面解释“实时估算/结算可能校正”。

## v1.7 离线、包形与 UI 门

- 正常测试：305 tests、92 subtests 通过；源码与包 self-test 均 exit 0。
- Bridge 1.7.0：Release 构建 0 warning / 0 error；正式版关闭高频探针，保留低频启动、连接和错误信号。
- 无 BepInEx 隔离夹具：首次自动配置成功，307 个 runtime 条目与独立 Bridge 均零缺失/零不匹配；第二次执行字节一致。
- 正式包：1,765 个文件、168 个目录、166,841,561 字节；config 为 0，测试导出目录不存在，包与干净桌面候选逐文件一致。
- Windows/Tk：Mini HUD 100%/125%/150%/175%、降级、官方状态与详细主窗口均通过进程/窗口绑定的可见验收；未发现裁切、重叠或旧“手动导出”控件。

## v1.7.1 MOD、隐私与分享门

- 社区 catalog 为 59 条、60 个最小功能文件、3,619,277 B；怪物宝藏升级到 11.6，新增啵啵法杖、磁暴线圈召唤啵啵与雷神之锤召唤愤怒雷精灵。啵啵法杖作者按维护者确认记录为 `啊 这`，海克斯强化药水为繁体 `時間與你`。
- 正常测试增至 306 tests；本轮相关 focused 为 106 tests、17 subtests。隔离包 self-test、59 项安装/卸载、无 BepInEx 首次初始化、重复初始化和冲突核心拒绝写入均通过。
- 隐私正控确认旧 Bridge DLL 的 RSDS/CodeView 记录含编译项目路径；Release 配置禁用调试目录后，两个不同绝对构建根均产生 98,304 B、`7581AF04…E90981` 的相同 DLL。332 个 IL 方法体以及 API、字段、托管字符串/Blob 和资源与旧 Bridge 1.7.0 一致；新 DLL 不含盘符、UNC、项目根或用户名路径。
- 最终包为 1,768 个文件、171 个目录、166,944,053 B；EXE 为 `8D187D40…914067`，config 0，exports 不存在，包内没有本机路径、旧作者误录或测试取证目录。
- Windows/Tk 增量矩阵覆盖 125% 主战斗页、怪物宝藏、啵啵法杖、繁体作者、最长新增 MOD 标题和 150% Mini HUD；全部 receipt/关键标签与整窗像素为 `VERIFIED`。
- 群分享 ZIP 为 1,768 文件、172 目录项、137,244,023 B，非 ASCII 条目全部带 UTF-8 标志，逐文件内容与冻结包一致；SHA-256 为 `1B3F9F12…8F1AAC2`。GitHub 服务器 digest 与 Draft 资产下载回读哈希相同，回读 ZIP 再验完整。

## v1.7.2 DPS 与双构建档维护门

- v1.7.1 单人反馈提示 DPS 偏低；源码正负控制确认旧实现首段固定除以10、总伤害与DPS数据源不一致、空闲墙钟不推进三类缺口。v1.7.2 改为完整live累计正差分优先、逐击尾段/回退、1—10秒实际分母和重连重建。
- 早期四人房中两名路人逐渐退出，最终活动团队分母正确收缩；只有一次`damage_snapshot_missing`低频信号，没有高频事件归档，因此不把具体漏击或漏量写成已确认根因。
- 默认维护包为`Diagnostic`，可暂停/继续并手动导出匿名逐事件，单局上限128 MiB；只有明确发布时才构建不含桌面归档/控件和Bridge高频诊断的`Distribution`。两档profile、manifest与Bridge身份不一致时拒绝启动。
- 两档各运行320项产品测试；无BepInEx首次/重复初始化、冲突核心写前阻断与包self-test通过。诊断/分享EXE分别为`FE42FA22…A09AE3`/`C98B7BE0…28AEE`，Bridge分别为`401D6FD0…E5BD69B`/`5261B844…1390AF`；包内config与测试数据均为0，三份最终候选的本机路径扫描为0命中。
- 同一最终UI轮次覆盖诊断主界面125%最小/常用尺寸、诊断HUD150%、分享主界面125%与分享HUD150%，五臂receipt、geometry与整窗像素均`VERIFIED`。详细页保留当前区/下一区跳过诊断；Mini HUD两档均精确为“实时”，不显示跳过。首轮布局红项与中间无receipt抓图都保留但不参与签字。
- r2单人中途退出样本含4,935条匿名事件，全部可重放、关键摘要差异0、完整live采样4,893、正DPS采样4,461且非法DPS为0。退出回营没有`session_ended`，只由manual export与离线partial副本恢复保全；因此签“中途退出可回放”，不签自然结算或绝对DPS官方一致。
- r2自然单人结算官方伤害860,235、Boss 139,339、承伤409与盒子live逐项差异0；两次死亡叙述下匿名身份/slot仍稳定，7,584条事件全回放、摘要差异0、DPS非法值0。结算界面明确存在，但network SyncEnd与三个探针命中0，official/session-ended缺失，判`VALUES PASS / SOLO FINAL EVENT FAIL`。
- r3接入带active-session门的`StatisticsMgr.OnGameSettlementSyncEnd`，仅在既有final身份门接受完整记录后结束session；失败恢复live。Bridge 1.7.2 diagnostic/distribution分别为`BC8FFAD8…1948B2`/`93480F5E…5A7B6F`，双编译、66项聚焦和321项产品测试通过；诊断包EXE为`D328375E…1B33D43`，包形/隐私/空白运行时门通过，真实结算`NOT RUN`。
- r4刷新为60条/61文件社区清单：新增雷击强化1.0.1并更新增强计划5.0.0、怪物宝藏11.7、行刑者2.6、雷神之锤1.5.1与啵啵法杖1.9.6。60个插件GUID无重复，61个文件身份与包形安装/卸载60/60通过；诊断包1,770文件、167,018,274 B，项目包与桌面树摘要一致，真实MOD加载`NOT RUN`。
- r4跨重启续玩实测确认`REJOIN-SEED-01`：游戏最终live与截图同为10,619,575/Boss3,466,900，盒子因拒绝非零首个live种子退回逐击，只显示6,964,256/Boss3,945,311；承伤前后两段757+805精确等于官方1,562。结算卡与回营边界均存在，但local-final/network探针、official/session-ended全为0，`SOLO-FINAL-01`仍失败。三段224、8,520、16,456事件均完成一致性/重放验证。
- r5 Bridge1.7.3将非零首值授权收窄为进程第一次激活session，并以结算UI数据/显示/offline-end三个入口复用单人final身份门；标准prefix/postfix边界同时保留checker可判定性。两档100,352 B、127项相关与324项产品测试通过；诊断包1,770文件/167,019,441 B，项目包与桌面树摘要一致，隐私/空白运行时/60项MOD包形门通过。1.7.2回滚已冻结、最终1.7.3部署读回一致，真实重进和结算均`NOT RUN`。
- r5重进实测：退出前HUD22,466；重进首个游戏live22,430被非零seed门接受并立即显示，首样本team/personal DPS均0。下一live22,942后才按512增量计速；283条退出前事件与恢复ZIP一致性/重放均通过。作者观察同步确认，`REJOIN-SEED-01`转为`RUNTIME PASS`，单人final仍待本局结算。
- r5后续单人局经一次Alt+F4整房回滚后主动结束：官方造成/Boss 1,451,098/240,540与HUD逐字一致；承伤因两次房间尝试事件集合不同而不可比较，不判Bug。结算UI的prefix/postfix已命中，但最终save-list尚不可用且r5没有采用UI显式record，info/data两个入口均未接受，未产生official/session-ended/automatic ZIP，判`SOLO-UI-POSTROUND-01 RUNTIME FAIL`；自然终局未运行。
- r5节点的Distribution、commit、push、tag、Release和群分享均为`NOT RUN`；`MIDRUN-END-01`、post-round UI record接入、`SOLO-NATURAL-FINAL-01`、新增MOD真实加载与下一局清理当时保持开放。后续本地发布准备见下节。

## v1.7.4 结算字段与本地发布准备

- 互操作类型确认最终record有`mDamageValue`、`mBossDamageValue`、`mTakeDamageValue`；原生链确认`UpdateSettlementInfo(__0)`是结算UI实际显示所用record，`SetSettlementData._selfPlayerData`为同链后备。`GameOverEnd_Offline` prefix发生过早，只保留观察，不直接final。
- 并行扫描92个历史诊断ZIP：官方伤害+Boss完整2包、`session_ended` 77包、automatic 77包，三者交集0；历史归档也未保存最终承伤字段。因此1.7.4实现有类型/调用链与合成正负控，但真实三字段+结束事件闭环仍明确`NOT RUN`。
- 1.7.4只在本机单人、HMAC身份/槽位一致且三值合法时冻结官方伤害/Boss/承伤；承伤只在final覆盖，不做实时累计。可信UI结束回调即使缺record也结束session并保留live估算，不伪造“官方”。
- 当前源码338项测试通过；双构建档C# Release 0 warning/0 error，Diagnostic初次构建327项产品门通过，新增群友文案门后的最终Distribution原生重构建328项通过；public-core实际构建重新运行338项并self-test exit0。
- Distribution为1,770文件/167,021,045 B，EXE `F881D798…28660`、Bridge `190B8B4A…7DED`，诊断/默认记录关闭、exports不存在、维护者精确个人目录与测试数据扫描0命中；同名桌面目录逐文件一致。UTF-8分享ZIP为137,406,593 B，逐文件内容一致，SHA-256 `8905A9DE…CF7C5`。
- 群分享说明只保留用户操作和不落对局明细的边界，诊断演进留在GitHub文档。public-core为1,712文件/84,931,341 B，EXE `1C6DB28B…364C9`；只带公开catalog、官方固定运行时和Distribution Bridge，不带本地第三方MOD载荷。所有产物仅本地准备，未提交、推送或发布。

## 明确不外推

- 未覆盖未来游戏版本、真实 7—16 人联机或所有社区 MOD 组合。
- 历史探针与归档 PASS/FAIL 不表示这些测试功能仍存在于 v1.7；正式版已移除逐事件 journal、每局 ZIP 和手动导出。
- GitHub 技术批次 `rxx` 是证据索引，不是正式产品版本号。
