# Bridge 0.4.15 registered-owner短房 / 退局session失败

- 日志：87,141 B / `B23D293A32A492C38BA21A723C71003E05BDCE6C0699DA38BABE7C36F20DAEC1`。
- 召唤武器截图：`935CC404B9CD3448F4345C3A03B8EC4CC2719865EA447300C3866117D7330698`。
- 提前退出后的单卡结算截图：`ABDF43F0E317A203A98C855DA1E6B9FBCA1DF36C6B44367F46DD2B106B11EA6A`。
- registered-owner子门：208/208 unique hit与Settlement命中重合；P1/P2/P3/P4各59/11/78/60，forwarded分别2/1/77/10；owner conflict、unresolved和duplicate callback conflict均0。该子门`R-PASS`。
- 单卡7,453不能解释为原多人slot的个人官方值。作者说明退出多人后冒险继续且只剩一张卡，它可能是该房间团队/当前缓存折叠值；与本机逐击2,508不做个人A/B，口径记`UNKNOWN`。
- 整体`R-FAIL`：`round_start is_camp=True`后、真正`round_end_preload_camp`前，旧战斗地图又触发`change_room_end valid=True`，Bridge错误创建仅1人的新session，桌面立即显示异常。
- checker整体结果：`phantom_session_after_round_start`；除此之外owner coverage全部通过。
- 修复方向：退局closing窗口内拒绝旧地图重新激活session；Bridge不发布瞬时duplicate-slot roster。不得要求作者重跑短房。
