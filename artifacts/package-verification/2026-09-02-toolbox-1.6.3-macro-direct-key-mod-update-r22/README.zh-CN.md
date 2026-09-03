# 工具箱1.6.3 宏直接录入与MOD增量更新 r22

> lifecycle: `SOURCE/TEST/BUILD/PACKAGE/DESKTOP/FORMAL-UI PASS / RELEASE HOLD`

- 桌面：`<desktop>\失落城堡2工具箱1.6.3-宏录入与MOD更新修正版-r22`。
- 项目包与桌面不可变基线均为1,764文件、169目录、166,836,963 B、config0；逐文件长度/SHA-256差异0。
- 正式验收后桌面仍为1,764文件、166,836,963 B、config0，原1,764文件与项目包差异0；仅正常启动多出一个空目录`exports/对局归档`，所以当前桌面目录数为170。
- EXE：6,495,545 B / `5A98BB3683525CAE73007F4F026CB71F94277C676F67775AB254EE2DD2209BDB` / 1.6.3。
- community catalog：86,103 B / `876DB83926817600D71A131956726EEAB95855982F2F04543A2752A6B24F3275`；56条、57文件、3,522,509 B。
- Bridge仍为0.4.27：90,624 B / `28F5960B4A684CAC3150AC688827142646605796BBDC998A9378D77F1301A2CF`；runtime manifest / `41C3D6EDC24EEBB347C1A7572A34DBB924911371598B67DF2462B6E94572172C`。
- 源身份：macro_ui / `C96F79E2B9C5B4D2A9C6A027E966E774CF9869D2EC1CECE777B009E4A598F4CD`；macro_config / `BBFC4A59C91B2990F4B46CC552519EB57816F56D29D43D4B95C03175AF681B4A`；mod_inspector / `BCBB98B85101C77FB378782AF7B700F4DBD6EA973E7ADF5833D78FD937F8D473`。
- build内完整门267 tests PASS；源码、项目包及桌面self-test exit0；`git diff --check` exit0。
- package形真实导入正控：怪物宝藏RAR得到version11/author懒虫桑；Nightfall DLL得到version1.1.0/社区未署名；两次均完成56条社区MOD隔离安装/卸载、未知兄弟文件保留与用户注册往返。
- r21在发现通用导入元数据误判后已停止使用并可恢复地改名为`已撤回-...-r21`；没有删除。
- formal Windows/Tk UI acceptance最终`VERIFIED`；证据见`artifacts/ui-acceptance/2026-09-02-toolbox-r22-macro-mod-formal-readonly/`。
- 第三方MOD未被实际加载，游戏目录未写入；commit、push、Release未运行。
