# LC2 工作9 r23 正常发布冻结（2026-09-02）

> 历史快照：记录 r23 冻结时状态；归档/探针和当时开放门已被正式 v1.7 决策取代，不表示当前发布状态。

> lifecycle: `normal-candidate-frozen / runtime-matrix-complete / fresh-audit-pending / release-hold`

## 范围

- 正常产品版本：`1.6.3`；Bridge：`0.4.28`。
- Git 基线：`main@758db3ae731613e2c3e4fcbfb9d7fd0058286f66 = origin/main = v1.6.2`。
- 共享工作树仍包含工作6/7/8/9的连续未提交正常产品改动；禁止 reset/clean、整体 stage 或 `git add -A`。
- 工作9已把 r5 验收后混入正常 tracked 文件的 public-core 适配精确回正：`toolbox/app_shell.py` 恢复 r5 已验 SHA-256 `D636DBDFD8CB9F6A120CD943CDC4D775FA5D7EC309C2D485CD4CE4C26E84A399`；`toolbox/runtime_setup.py` 恢复与已验 EXE 相同的 Git 基线语义；对应测试只保留正常 Bridge 0.4.28 身份更新。

正常发布范围包括当前 tracked 产品/测试/文档改动，以及下列新增正常源码与记录：

- `toolbox/combat_archive.py`；
- `tools/analyze_lc2_damage_divergence.py`；
- `tools/check_lc2_leave_team_identity.py`；
- `tools/check_lc2_multiplayer_probe.py`；
- `tools/check_lc2_settlement_cache_probe.py`；
- `tools/check_lc2_settlement_final_probe.py`；
- `tools/check_lc2_statistics_cache_probe.py`；
- `tools/qa_combat_archive_pipe_server.py`、`tools/qa_macro_ui.py`；
- 对应非 public-core 新测试；
- 工作7/8/9 checkpoint、r23合同、r22宏UI checkpoint、1.6.3发布说明草案；
- 各正常 package/runtime/UI 证据目录中的 README。

## public-core 隔离

以下对象保持原字节，但均为 `UNSELECTED / DEFERRED / NO-RELEASE`，不进入正常 stage、commit、push、Release或群分享：

- `build-public.ps1`；
- `assets/mod_catalog.public.json`、`assets/community_mod_catalog.public.json`、`assets/lc2_public_runtime_manifest.json`；
- `PUBLIC_CORE_THIRD_PARTY_NOTICES.md`；
- `package_assets/public-core.README.txt`、`package_assets/运行环境/public-core/`；
- `tools/prepare_lc2_public_catalog.py`、`tools/prepare_lc2_public_runtime.py`；
- `tests/test_prepare_lc2_public_catalog.py`、`tests/test_prepare_lc2_public_runtime.py`、`tests/test_public_build.py`；
- ignored local product `package/public-core/`。

正常执行路径已搜索，不引用上述 public build/catalog/runtime 输入；文档中的 public-core 字样只用于记录隔离边界。

## 离线门

- `py -3 -m pytest -q tests/test_combat_archive.py`：22 passed。
- r22 exact 跨 session ZIP：正确拒绝为 `archive_summary_session_mismatch`；r23手动 known-good：PASS。
- `py -3 -m pytest -q tests/test_app_shell.py tests/test_runtime_setup.py`：43 passed + 8 subtests。
- 正常全量（显式忽略3份 public-core tests）：304 passed + 92 subtests。
- 全目录含隔离测试：314 passed + 98 subtests；该结果不冒充正常 release suite。
- `py -3 keyview.py --self-test`：exit 0，version 1.6.3，runtime bundle verified。
- `git diff --check`：exit 0。

## 包与桌面身份

- 项目包：`package/失落城堡2工具箱1.6.3-实时数值监测+一键MOD安装`。
- 正常桌面：`<desktop>/失落城堡2工具箱1.6.3-发布候选-r23`。
- 项目包：1,766 files / 169 dirs / 166,858,329 B；desktop 对每个包内相对路径的 size/SHA-256 差异为0。
- EXE：6,501,036 B / `4C6C81B6C38EBDBEB0CA298950040D30499E183399B6B678C1C89286CE9EA544`。
- package / desktop / installed Bridge DLL：98,304 B / `5482997836C1AA594C14C1E10D7858572655B2CB1EE57F9A1F18A57CC9BDA9D1`。
- installed PDB：35,484 B / `905C43072A3F560A4937083E801E788798B3233F1735682B09BFFBDD07C5FF92`。
- 实测结束后游戏、工具箱、Python、dotnet、MSBuild相关执行进程为0；日志连续2秒稳定，无 partial 残留。

## 真实矩阵

1. r23四人高延迟撤退样本：严格 Statistics realtime/rollover与owner链PASS，remote-only正控存在；手动归档同session PASS；SyncEnd NOT_RUN。
2. r23双人自然完整局：SyncEnd hooks/sequence/payloads/official mapping全PASS；Boss PASS；P1 final向上、P2 final向下；owner与逐槽final映射PASS；完整局在下一session建立时以同session `superseded` ZIP封存。
3. 第二个未战斗session正常退出时生成独立 reason=`automatic` ZIP；两个ZIP均一致性PASS，无跨session摘要。

双人自然局存在作者观察到的游戏侧符文异常，未确认与工具箱相关，因此它不单独作为“玩法完全无异常”样本；但准确度、final、Boss、owner和归档数据面均有直接正证据。组合矩阵不外推所有MOD组合或7–16人联机。

## 发布前剩余门

1. 唯一 fresh different-owner source/package/runtime/UI综合审计；
2. 第三方外发裁决已于 2026-09-02 完成：当前登记的社区载荷按正常完整包分发，并继续保留逐项作者、来源与哈希记录；
3. 审计PASS后精确stage正常路径、commit、push、GitHub Release资产上传/readback、QQ群说明；
4. 发布后建立有ID/状态的安静监测。

## Not run

- fresh audit、commit、push、tag、GitHub Release、资产readback、QQ群发送与发布后监测均未运行；
- public-core未构建、未stage、未发布，也未删除。
