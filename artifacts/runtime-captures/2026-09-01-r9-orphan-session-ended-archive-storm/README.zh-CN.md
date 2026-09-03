# r9孤立session_ended归档风暴

- 生命周期：`REAL R-FAIL / ARCHIVE STATE MACHINE ROOT CAUSE CONFIRMED`。
- r9精确EXE：`AC96FB7D990A05984B121234A8DAD657BBDDC410CCA63BCAB5AAEE0AAF175D5B`。
- 用户目录真实结果：74个ZIP、89,176 B，时间10:53:38–10:56:04；全部session key=`D28FF91DC8`。
- 每个ZIP都只有1条`session_ended`，序号0..73递增；没有`session_started`、伤害、roster或房间事件。首个ZIP `D6DED821…BDF4`，末个`E7563992…DFD1`。
- 截图：HUD从启动即`异常`且0，游戏续单人卡46,296/13击杀；截图 `EF6383BBF95721C62EE30074FAF57BB96D3C7F083F6D29F94F1577D941C5A188`。HUD没有接收当前局，不能与卡片比较。
- 双根因：归档器在无active partial时仍为孤立结束回执创建并立即封存；聚合器只接受foreign session_started边界，新Bridge未进地图时先发foreign session_ended，导致SessionMismatchError和事件泵error。
- 冻结副本位于`duplicate-zips/`；用户原74个ZIP未删除。
- r10规则：孤立结束回执不建档；已自动封存session迟到事件不重开；foreign started/ended均为显式安全边界，其他foreign事件继续fail closed。
