# 工具箱1.6.3 / Bridge0.4.24 NPC额外record兼容版 r15

> lifecycle: `SOURCE/PACKAGE/DEPLOY PASS / LIVE PIPE SUBGATE PASS / PRODUCT REALTIME R-FAIL / SUPERSEDED BY R16`

- 项目包与桌面`<desktop>\失落城堡2工具箱1.6.3-live官方缓存NPC兼容版-r15`均为1,761文件、166目录、166,678,069 B、config0；逐文件SHA-256差异0。
- EXE：6,485,801 B / `8EFF5DCFE590EBCCE21E89D5B67BFAAD38CB55C509614BDE58AD469F4DF2CDB2` / 1.6.3。
- runtime manifest：58,172 B / `00F5676AF227C9D247801769B1ABA4AA58AB767C406BE2C9A292761E2E5C35AC`。
- Bridge0.4.24：78,336 B / `AED7435360BEEE7FB2B8851EF546987CD69C9C2ACD275F799B47C6457021115A`；PDB29,760 B / `8BC5DCA2E9C5DA0147DAEB04105963F378B30FE38A9797D8BDCCA3A345B0FCCC`。
- 0.4.24只允许额外未匹配官方record；每个历史human slot仍必须按匿名平台身份完整唯一匹配，duplicate/missing/下降/Boss>总伤害均整组拒绝。
- r14真实两人+NPC结束前active：P1 164,336/Boss41,002，本机675,616/Boss150,361；截图官方本机卡675,616/150,361完全一致。逐击HUD分别高174与93，证明live active更接近权威。NPC过程76,530/Boss15,576保持unattributed，不进入玩家官方合计。
- 聚焦89项、Python全量234+37、build内234、C#0 warning/0 error；16 Hook不变。包/桌面self-test0；包形runtime fresh ready、冲突写前阻断。
- 旧r11继续known-red；r13 payload遗漏与r14 NPC严格hold均为positive control，不得标最终过程PASS。
- r15真实四人smoke先证明live pipe子门PASS；随后同房队友持续输出时raw live不变，四槽display冻结并落后observed，产品实时语义R-FAIL。证据见`artifacts/runtime-captures/2026-09-01-r15-live-anchor-freezes-within-room/`；r16改用official anchor+房内observed增量。
- 未commit/push/Release；自然最终结算与different-owner审计未运行。
