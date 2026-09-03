# 工具箱1.6.3 / Bridge0.4.19 final首次接受冻结 r8候选

- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 桌面：`<desktop>\失落城堡2工具箱1.6.3-官方结算冻结版-r8`。
- 两侧均为1,761文件、166目录、166,658,093 B、config0；逐文件SHA-256差异0。
- EXE：6,472,569 B / `469C69D891C76AC1E139201A6A6008FD3979FAB681234D8478A07B17A571F23C` / 1.6.3。
- runtime manifest：`C08977B9476E5A88C8BF7462BEA31B7D783278466D3C0443F9CD4D5E6A972C07`。
- Bridge：72,704 B / `03BD7A7057C4408A475626E57AA2B4F99594E769AB6FC069CF9AE0366646C06D`。
- BepInEx archive：40,402,401 B / `0B617BC439F53E39680444F1EFD84C2B31A96D144D3267EE06EBEA05B59738A8`。
- 全量pytest `208 passed + 37 subtests`；build内unittest 208项；SDK6.0.428 + 当前interop Release 0 warning/0 error；源码/包self-test、首次/重复运行时安装和冲突core写前负控PASS。
- 冻结r7完整结算为positive control：首次4槽accepted后第二次rejected，checker明确报`final_acceptance_regressed`；r8源码冻结首次slot→原会话匿名token及官方Damage/Boss，下一局reset。
- UI代码未变化，因此不重复视觉调参；真实r8自然结算`NOT RUN`，不要求野队团灭或专门长局。
- 生命周期：`IMPLEMENTATION/PACKAGE/DEPLOY PASS / PASSIVE NATURAL FINAL CONFIRMATION NOT RUN / NO COMMIT, PUSH OR RELEASE`。
