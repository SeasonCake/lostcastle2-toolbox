# Bridge 0.4.16变身技能伤害少算样本

- 日志：119,888 B / `D185FA306D528F67B1B5AAF3CCAB33EE50F99864811B43C093C2565067E5F2EE`。
- 本机为P3。第一战斗房HUD/日志：P3=27；P1/P2/P4=23,045/1,673/7,319，远端合计32,037完全闭合。
- 退出前HUD/日志：P3=4,794；P1/P2/P4=46,996/11,124/18,935，远端合计77,055完全闭合；占比和100%。
- registered/Settlement共659/659 unique hit重合；P1/P2/P3/P4各203/99/180/177，owner conflict、unresolved与duplicate均0。没有P3伤害串到队友的证据。
- 变身技能表现为持续2点耗蓝；全局385次耗蓝、合计782。第一战斗房变身期间P3有39个damage callback却仅累计27，变身伤害数值明显少算；不是整个变身阶段无事件。
- 退出后单卡25,209未经过final SyncEnd，可能是P3个人值，也可能是退出后团队/当前缓存折叠，口径UNKNOWN。若为个人值则与HUD差20,415，但不据此单独定根因。
- 参考DLL `ExtractActualDamage`：优先正数`mRealHPDamage`；非正时回退`mFinalDamage`。0.4.16只用real并取`min(real,hp_before)`，导致real=0的变身命中累计为0/近0。
- 0.4.17通用修复：正数real仍保持已闭合的HP封顶公式；仅`real=0/final>0`回退final，并按slot记录fallback次数/总值。无角色、武器、变身、召唤物或固定数值特判。
- 0.4.16退局closing门真实生效：回营后的`change_room_end`为`valid=False/is_camp=True`，未再创建phantom session。
