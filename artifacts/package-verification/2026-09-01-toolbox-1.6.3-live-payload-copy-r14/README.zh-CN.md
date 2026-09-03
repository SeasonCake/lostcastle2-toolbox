# 工具箱1.6.3 / Bridge0.4.23 live payload复制修正版 r14

> lifecycle: `SOURCE/PACKAGE/DEPLOY PASS / REAL SHORT SMOKE R-FAIL / SUPERSEDED BY 0.4.24`

- 项目包与桌面`<desktop>\失落城堡2工具箱1.6.3-live官方缓存过程修正版-r14`均为1,761文件、166目录、166,678,069 B、config0；逐文件SHA-256差异0。
- EXE：6,485,801 B / `12D7AC8686CBFDC5D8139679284A7DEFF025D615182A2E2DE4E007EAE9B3F019` / 1.6.3。
- runtime manifest：58,172 B / `3AEE766AAFC825D95BB0DDB7E78D8DEBF381CE20DF7B5F92312DA40C29CFDFA5`。
- Bridge0.4.23：78,336 B / `9BDB748BB77C30D8579851009DD0D4D847B902F49B76A1BF70F4E59081698C9C`；PDB29,752 B / `2067A1E6B87F8D65CA999BCB74FA5FD59E5EC1EED1C35E00B15E322A5DD80F08`。
- 0.4.23只在`PublishPartyUpdated`有界副本补复制`LiveDamage/LiveBossDamage`；0.4.22缓存读取、零基线、identity、单调、fallback、live/final分层与归档字段不变。
- 聚焦89项、Python全量234+37、build内unittest234、C# Release0 warning/0 error；16个Harmony patch不变。
- 包/桌面self-test exit0；包形runtime fresh ready并安装exact 0.4.23，冲突负控写入前阻断。
- 旧r11仍由checker以`per_hit_observed`判known-red exit1；0.4.22真实payload omission为positive control，不得标PASS。
- 0.4.23真实两人+NPC smoke：payload复制修复已生效，但live整组因active records=3、human party=2被严格record-count门拒绝。两个玩家identity完整、NPC额外record各1 unmatched；见`artifacts/runtime-captures/2026-09-01-r14-npc-extra-official-record/`。0.4.24允许额外未匹配NPC，仍要求所有human slot完整唯一。
- 未commit/push/Release；different-owner审计未运行。
