# 工具箱1.6.3 official anchor + 房内增量实时版 r16

> lifecycle: `SOURCE/PACKAGE PASS / DELAYED-CACHE SEMANTIC R-FAIL / SUPERSEDED BY R17`

- 项目包与桌面`<desktop>\失落城堡2工具箱1.6.3-live官方锚点实时版-r16`均为1,761文件、166目录、166,678,833 B、config0；逐文件SHA-256差异0。
- EXE：6,486,565 B / `1BE5721A336A7EEEEF673B0051CBF343C684C34D8CBE7FE7040F127BFDA62003` / 1.6.3。
- Bridge仍为已部署0.4.24：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`；manifest / `00F5676AF227C9D247801769B1ABA4AA58AB767C406BE2C9A292761E2E5C35AC`。
- r16显示公式无倍率：`live official anchor + max(0, observed - observed_at_anchor)`；同房重复相同live不重锚。原候选在每个`room_started`全槽重锚，长局证明该规则错误：主城剧情战后active跨房不变，到法师塔电梯结束才延迟刷新；无条件换房重锚会丢掉约365.8万真实增量。
- live缺失整组回退observed；final official仍独立sticky并可向下覆盖。archive保留last live与对应observed anchor；checker重建实际过程显示后比较final。
- 正控覆盖：同房逐击实时增加、同live roster refresh不清增量、room边界相同live清旧delta、部分槽live变化全槽重锚、live缺失回退、final向下覆盖、raw last_live偶合final不得掩盖process delta。
- 聚焦aggregator/checker50项；Python全量235 passed +37 subtests；build内unittest235。包/桌面self-test exit0；包形runtime fresh ready、冲突写前阻断。
- r15房内冻结为known-red positive control；当前作者继续用r15完成自然长局，线程heartbeat只读监测，不中途换包或部署。
- r17改为仅当任一live值实际变化时全槽重锚；room变化本身不清delta。r16不得运行或推荐。
- 未commit/push/Release；r17真实运行与official-dict探针待后续。
