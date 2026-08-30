# LC2 Combat Bridge 0.4.6 离线候选

- 生命周期：`SOURCE/BUILD/DEPLOY PASS / MP REAL PARTIAL PASS`。
- DLL：47,616 B，SHA-256 `7DFF32538C1D40015912D0D6C07A6EDF11A9D4E1E571EEEAF496ECD1AF5C98B4`。
- PDB：21,644 B，SHA-256 `512F3F0BA660682FF348B4DA4645C3192D1A01F080E6C20A4023B8C3AE46751E`。
- 构建：隔离 .NET SDK 6.0.428，Release，`0 warning / 0 error`；当前游戏 interop 只读作为编译引用。
- Hook：14，与 0.4.5 相同；不增加怀表、药剂或装备特判。
- MP 合同：零请求/零净变化且 fallback=96 必须继续发出；全零仍返回；普通消耗继续发出。
- HP：撤回未证实的容量归一化行为，保持 0.4.5 `effective=after-before` 聚合；仅增加 requested/before/after/max 诊断。自愈刻印、同类装备、药剂和复活产生的实际正向 HP 继续正常累计。
- Python 全量 165 项 PASS；`git diff --check` PASS（仅既有行尾转换提示）。
- 候选 DLL/PDB 本体按仓库 ignore 合同仅保存在本机同目录；部署身份与回滚另按下列回执记录。
- 2026-08-30 部署门：`LostCastle2.exe` 与正式 `失落城堡2工具箱.exe` 均按 exact name + `ExecutablePath` 连续两次为 0；同名、未知路径和近似路径均为 0。
- 独立回滚：`LC2CombatBridge.0.4.5.rollback.dll`，47,104 B / SHA-256 `A6484B75E3369B1B0AA774F4A7DCB53E0107CE381F104D33A9388FC5EF25A801`。
- 游戏目录部署后逐字节回读为 47,616 B / SHA-256 `7DFF32538C1D40015912D0D6C07A6EDF11A9D4E1E571EEEAF496ECD1AF5C98B4`。
- 测试盒子：`C:\Users\shenc\Desktop\失落城堡2工具箱 1.6.0-Bridge0.4.6测试版`；由正式目录复制，仅 `_internal/assets/lc2_runtime_manifest.json` 与 `_internal/third_party/lc2_runtime/LC2CombatBridge.dll` 两处不同，EXE `--self-test` 退出码 0。正式盒子目录未修改。
- 实机正控：普通无怀表新局恢复已非零；截图时消耗/总正向变化 `461/550`，其中普通恢复 461、容量变化 80+9，`100+550-461=189` 与游戏法力精确闭合。分解魔晶石后最大法力回到105且无新增 runtime_gain。
