# 工具箱1.6.3 延迟live锚点过程版 r17

> lifecycle: `SOURCE/PACKAGE PASS / REAL R17 NOT RUN / PROCESS ACCURACY HOLD`

- 项目包与桌面`<desktop>\失落城堡2工具箱1.6.3-live官方延迟锚点版-r17`均为1,761文件、166目录、166,679,118 B、config0；逐文件SHA-256差异0。
- EXE：6,486,850 B / `FBC0050A0F4CF9313E04D6A660E18670CF173C8E86D5BA795629AF2126A1CD04` / 1.6.3。
- Bridge仍为installed/package0.4.24：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`；manifest / `00F5676AF227C9D247801769B1ABA4AA58AB767C406BE2C9A292761E2E5C35AC`。
- r17无倍率公式：live官方锚点+非负observed增量。只有任一human槽live总/Boss实际变化时，所有human槽同步重锚；单纯room变化或同live roster refresh不清增量。live缺失回退observed，final official独立sticky并可向下覆盖。
- archive保留last live及对应observed anchor；checker重建实际过程显示再比较final，raw last_live偶合final不得假绿。
- 事件默认上限由64 MiB升至128 MiB；r15完整局97,296 events /67,108,683 B触发旧截断，尾部约5,261 events未落盘。截断正控仍保留。
- 聚焦aggregator/checker50项；Python全量236 passed +37 subtests；build内unittest236；包/桌面self-test exit0。
- r15完整局final官方四槽PASS，但r17团队过程重建仍高final约2,471,529（6.36%），Boss高4,018,595（25.7%）。因此r17只解决实时冻结和延迟锚点，不签过程准确PASS。
- 下一数据面：只读验证`SettlementDataMgr.mCacheRoundDataDict`是否提供房内逐玩家官方累计；不得通过倍率或角色/武器/地图特判掩盖差异。
- 未deploy新Bridge（Bridge不变）、未运行r17实机、未commit/push/Release。
