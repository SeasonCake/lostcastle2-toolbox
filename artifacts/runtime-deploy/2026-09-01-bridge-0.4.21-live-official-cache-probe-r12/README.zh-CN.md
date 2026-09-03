# Bridge 0.4.21 live官方缓存只读探针 r12部署回执

> lifecycle: `DEPLOYED / DIAGNOSTIC-ONLY / REAL SHORT RUN NOT RUN`
>
> recorded_at: `2026-09-01 Asia/Shanghai`

- 目标：验证`StatisticsMgr._adventureRecordCacheDataList`与`mAdventureRecordDataList`在真实多人房间中的可用性、逐slot身份映射、重置和累计语义；候选值只写匿名`[LC2CB-OFFICIAL]`日志，不进入pipe、不覆盖HUD。
- 0.4.21候选/installed DLL：75,776 B / `B164F49608DA4C4EEC6DA75CD7A383EA9725217D7FE68ADB358103764F38D56C`。
- 0.4.21候选/installed PDB：28,944 B / `0B4E3AC68456E77CAC6B3D39592CEA873CBC98342B80D649B44FB17808E3D0DF`。
- exact rollback 0.4.20 DLL：73,216 B / `17DF64A11C2BD35D46C3AF252420B0AE5E056FC508D9032C62EDDF28C12CC51C`。
- exact rollback 0.4.20 PDB：28,288 B / `5127A5D6BE04E47CBFBBD095F464FDB4EED49964F452CFB9128027F2C202C34C`。
- 部署前结构化进程查询：17:19:46与17:19:57两次均为0，unknown path为0；部署后17:20:31仍为0。
- 离线门：Python `231 passed + 37 subtests`；隔离SDK6.0.428 Release `0 warning / 0 error`；Mono.Cecil回读版本0.4.21、16个Harmony patch、两组live缓存getter均存在。
- 当前项目包和桌面r11仍内置Bridge0.4.20。短测期间不要使用工具箱内“启动游戏”按钮，否则运行环境检查会把诊断DLL判为需更新；从Steam/游戏程序正常启动游戏，再单独启动r11工具箱即可连接同一pipe。
- 恢复条件：多人一到两个房间，至少出现一次房间边界；冻结`BepInEx\LogOutput.log`后检查`live_cache_*`、`live_active_*`、identity和read failure字段。若两组列表为空、身份不完整、跨局不归零或数值不单调，立即停止，不接入HUD、不要求完整长局。
- 未构建新工具箱包、未替换桌面、未commit/push/Release，未签发过程准确PASS。
