# 工具箱1.6.3 / Bridge0.4.22 live官方缓存过程版 r13候选

> lifecycle: `SOURCE/PACKAGE/DEPLOY PASS / REAL 0.4.22 SHORT SMOKE R-FAIL / SUPERSEDED BY 0.4.23`

- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 桌面：`<desktop>\失落城堡2工具箱1.6.3-live官方缓存过程版-r13`。
- 两侧均为1,761文件、166目录、166,677,557 B、config0；逐文件SHA-256差异0。
- EXE：6,485,801 B / `586CEEE834AF88D0426C83BA66101112EEB2950844BFAA18B82FA98E56BAADD8` / 1.6.3。
- runtime manifest：58,172 B / `C18D10EA8EAF1D86EA62F298DFB8509CD04117AA76425CC13E2DC21E3A8C57CC`。
- Bridge0.4.22：77,824 B / `FAB3E539150196C27B06788BC30A6D89565F1B1B72264EA9A09644F2B071EC04`；PDB29,752 B / `55DA51167D5E696AA63F1A7A63DEDADA61E281DA6B3EC90F67A22A3DCAB65397`。
- Python全量`234 passed + 37 subtests`；build内unittest234项；隔离SDK6.0.428/current interop Release 0 warning/0 error；16个Harmony patch不变。
- 包和桌面self-test均exit0；包形隔离运行时正控达到`ready`并安装exact 0.4.22，冲突core负控在写入前阻断。
- r11完整局继续由新checker判`process_basis=per_hit_observed / exit1`；r12三人两房证明active缓存三槽零基线、身份6/6、跨房单调且与过程值逐槽闭合。
- 0.4.22仅在完整零基线、record数等于历史party槽、匿名身份一一匹配、Boss≤总伤害、逐槽单调时发布live整组；失败则不发布，Python立即回退逐击。
- `live_*`为可替换当前快照；final `official_*`保持exact SyncEnd sticky并允许向下覆盖。归档保留`last_live_*`，结算checker优先用它评价产品过程值。
- 真实r13短smoke：0.4.22正确加载、四槽零基线和身份8/8均PASS，但partial中live始终null。根因是pipe有界party副本遗漏两个live字段；见`artifacts/runtime-captures/2026-09-01-r13-live-payload-copy-omission/`。该候选不得继续使用，0.4.23只补字段复制。
- 未commit/push/Release；different-owner审计未运行。
