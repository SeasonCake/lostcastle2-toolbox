# 工具箱 1.6.3 房内官方缓存探针版 r18

> lifecycle: `SUPERSEDED / WITHDRAWN / REAL NOT RUN`

- 阶段复审发现pre-read限频缺失、force边界会被普通样本cap阻断、checker预设未证关系三项问题；本包身份虽然自洽，但不再是可运行候选。
- 原桌面目录已改名为`<desktop>\已撤回-失落城堡2工具箱1.6.3-房内官方缓存探针版-r18`；installed已回滚0.4.24 exact。

- 构建时项目包与原桌面均为1,761文件、166目录、166,687,814 B、config 0；逐文件长度/SHA-256差异0。该历史身份不构成运行PASS。
- EXE：6,486,850 B / `23CAC42797C7037060516909A13A1ABE09C4A609E362A19612DA3A20D2BEEEAD` / 1.6.3。
- Bridge0.4.25：87,040 B / `2C0936C35833A486DEA19ABA8118ECFF79F5295D3383A86C4C4DE16D3433852F`；manifest / `4ACB01A79A6D7DED251E5D270C18AC4557967CE926032F8F41ACF0D0B2F0CDEA`。
- package与desktop self-test均exit0；build内245项通过，外部pytest 245 passed +41 subtests；C# 0 warning / 0 error，16 Hook不变。
- r18只记录三数据面匿名诊断，现有HUD仍保持r17延迟锚点行为；本次短测不要凭HUD数值判断探针成败。
- 专用checker拒绝：只有转场才变化、单快照/全零、singleton塌槽、human缺失/重复/碰撞、dict/cache-list不一致、下降、NaN/Infinity/负数/Boss>总伤害、转场掉数或双加，以及仅final正确外推实时。
- 真实r18、Boss语义、pipe采用、过程准确性、commit/push/Release均未运行。
