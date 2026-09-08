# 视频制作工具调查与选型

> 2026-09-05前期记录，现已作为历史制作资料保留；最终成片、发布状态及署名以[视频首页](README.zh-CN.md)和实际产品目录为准。

调查日期：2026-09-05。以下是公开资料核验与工程判断，不等同于本机安装或实片测试。Stars 来自当次 GitHub API 快照，只表达关注规模，不表达质量排名。网页摘要与当前仓库不一致时优先当前官方说明；失效查询没有用于填充其他项目的统计。

## 推荐的最小组合

| 工作 | 优先方案 | 本片用途与接入条件 |
| --- | --- | --- |
| 专属片头、片尾、标题动画 | Remotion 官方 Agent Skills + 本地 Remotion | 猫爪/数据线动画、中文标题、真实 HUD 局部放大；需 Node 与渲染依赖 |
| 原片剪接、代理、混音、导出 | FFmpeg/ffprobe | 处理 40 分钟素材与 3 分钟成片；先补齐所需编解码器/字幕支持 |
| 中文脚本与封标审校 | 花叔 huashu-skills 中的视频大纲、口语审校、视频检查 | 作为内容工作参考；不承担视频解码、选段或渲染 |
| 转写、字幕时间 | faster-whisper 或经验证的已有 Whisper 环境 | 优先本地；无口播的战斗高光不能靠转写找，仍要看画面 |
| 中文旁白 | MiniMax 语音 API/MCP，ElevenLabs TTS 作备选 | 按最终稿生成温和中文声音；均需可用服务账户/额度，音色需试听 |

这些是本片制作选择。MCP 是能力接口，Skill 是工作指引，FFmpeg/Remotion 才执行处理；数量多不构成选型优势。

## 候选项目与取舍

| 项目及一手来源 | 当次关注/维护信号 | 适用面 | 本次选择 |
| --- | --- | --- | --- |
| [Remotion](https://github.com/remotion-dev/remotion) / [官方 Skills](https://github.com/remotion-dev/skills) | 引擎 58,351 stars；Skills 4,487；均未归档，推送分别为 09-04/09-01 | 可编程动画、媒体组合、预览、字幕、渲染 | 主选，最契合可复用的赛博猫包装 |
| [花叔 huashu-skills](https://github.com/alchaincyf/huashu-skills) | 1,468 stars，08-31 推送 | 视频大纲、脚本口语化、标题/封面一致性 | 内容参考。对应目录为 huashu-video-outline、huashu-script-polish、huashu-video-check |
| [video-recap-skills](https://github.com/zenstory-ai/video-recap-skills) | 495 stars，09-05 推送；旧 worldwonderer 地址重定向至此 | 长视频理解、剪后配音、中文字幕、FFmpeg 合成、剪映草稿 | 功能最接近整条流水线，作为备选；依赖 MiMo API，素材分析涉及外部请求，尚未接入 |
| [MiniMax-MCP](https://github.com/MiniMax-AI/MiniMax-MCP) / [官方 CLI](https://github.com/MiniMax-AI/cli) | MCP 1,576 stars，08-20 推送 | 中文 TTS、音色预览；CLI 提供语音等能力 | 配音优先候选，待短样片试听与账户条件确认 |
| [ElevenLabs 本地 MCP](https://github.com/elevenlabs/elevenlabs-mcp) | 1,536 stars，已归档 | 旧版综合语音 MCP | 不新装旧仓库；备选用官方 TTS API。新 hosted MCP 需验证具体工具，不能假定与旧版全等 |
| [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft) | 4,290 stars，07-08 推送，未归档 | 生成剪映可编辑草稿，支持轨道、文本等 | 用户想手工微调时有用；需对实际剪映版本做导入/保存/再打开/导出小样测试 |
| [mcp-use/remotion-mcp-app](https://github.com/mcp-use/remotion-mcp-app) | README 有交互播放器与本地服务器演示；未对社交热度排名 | 在兼容客户端内预览 Remotion 画面 | 可选预览接口，不作为本地最终 MP4 渲染能力已经验证的证明 |
| [Vidhanvyrs/remotion-mcp](https://github.com/Vidhanvyrs/remotion-mcp) | 0 stars，05-25 推送，未归档 | 社区执行型 MCP，声明可发起异步渲染 | 尚小，不做主链依赖；直接 CLI 已能覆盖关键工作 |
| [Harper Carroll / reel-studio-skill](https://github.com/harper-carroll/reel-studio-skill) | 4 stars、少量提交；非热门成熟工具 | 人像/播客转竖屏，Higgsfield B-roll、Remotion 字幕 | 借鉴选风格、分镜、预览流程；横屏游戏片不需要全套 AI B-roll |

## 两个已核实的更新陷阱

Remotion 的旧官方文档 MCP 已标为 deprecated，并建议改用 Agent Skills 与 remotion-docs；不再按早期博主演示安装旧 MCP。[官方弃用说明](https://www.remotion.dev/docs/ai/mcp)、[当前 Skills](https://www.remotion.dev/docs/ai/skills)。

ElevenLabs 本地 MCP 仓库已归档，README 指向 OAuth hosted MCP；新文档主要介绍 agent 管理和声音样例。本片的旁白应按官方 TTS 能力接入，不能因为新端点可连接就认为旧工具已完整迁移。[仓库声明](https://github.com/elevenlabs/elevenlabs-mcp)、[Hosted MCP](https://elevenlabs.io/docs/eleven-agents/operate/hosted-mcp)、[中文支持](https://elevenlabs.io/docs/overview/models)。

video-recap README 提到的 Fish Audio 免费窗口截止到 2026-08-31，早于本次调查，因此不按“现在免费”预算。MiniMax 旧搜索摘要列出 music_generation，但当次读取当前 MCP README 已不列此工具；BGM 不依赖这个旧承诺。

## 花叔与国外案例，分别能参考什么

| 平台 | 核验结果 | 能采纳的内容 |
| --- | --- | --- |
| X | 找到[花叔本人关于 Chrome DevTools MCP 的帖子](https://x.com/AlchainHust/status/1971839749724975175)，内容是 B 站/YouTube 评论运营；Remotion 官方发布帖全文本次未能直接读取 | 花叔这个 MCP 案例用于运营，不能当剪辑引擎；Remotion 的能力回到官方文档核实 |
| YouTube | 找到 Sabrina Ramonov、Aidan Stanik 的 Remotion 教程线索；YouTube 视频直开未成功，未完整观看或核实播放量 | [Sabrina 本人配套教程](https://www.sabrina.dev/p/claude-just-changed-content-creation-remotion-video)与[五类视频示例](https://www.sabrina.dev/p/5-insane-claude-code-video-prompts)可核验流程；只参考动画与现有素材包装，不照搬社交自动发布 |
| Instagram | 执行多组站内限定查询，并尝试官方/创作者页面；未取得足以可靠比较的帖子正文、视频与热度指标 | 本轮不声称“已看完 Ins 热门案例”或做榜单，后续若有具体参考链接可补看 |
| GitHub | README、官方 docs 与有限个仓库 API 元数据可查 | 以维护状况、Windows 条件、本地/云处理、可编辑产物与渲染能力决定适配 |

[Marcus Volsted 的本人案例](https://www.marcusvolsted.dk/guides/remotion-video-editing-with-ai)描述了处理 42 分钟原片的 Remotion 工作流，可借鉴素材索引与分段包装；其“20 分钟”是作者自己的案例说法，不作为我们实片工时估计。Harper Carroll 的开源项目适合参考统一风格和字幕构图，但演示对象是竖屏人像。

技术资料仅用于核实能力；网页中的安装指令没有执行，也没有下载博主视频当本片素材。

## 初次环境检查（安装前快照）

轻量探测对象仅为 PATH 命令和 Python 3.13 模块，不递归扫描磁盘或读取账户密钥。

- FFmpeg/ffprobe：可运行，版本 6.1.1。loudnorm、sidechaincompress、drawtext 可用；完整枚举中未找到 subtitles/ass、libx264 或 h264_nvenc，有 h264_mf。只证明工具存在，不等于成片管线已跑通。
- Node：23.11.0；npm 10.2.3。后续 Remotion 项目使用单独依赖目录与锁文件，再验证所选版本的运行要求。
- Python 3.13：PIL、OpenCV 可导入发现；faster_whisper、whisper、edge_tts、moviepy 未找到。另一个环境有 whisper 命令，未运行模型。
- 当前没有已经连好的剪辑/TTS MCP。插件管理技能要求的目录搜索/建议工具在本会话未暴露，因此改用公开官方仓库/文档完成选型，没有将“推荐插件”写成“已连接”。

维护者随后授权自行配置环境。本轮实际安装及验证结果见 [运行环境与小样](ENVIRONMENT.zh-CN.md)。配音小样补选 [edge-tts](https://github.com/rany2/edge-tts)：Python 通过 Edge 在线语音服务生成中文，不需要 API Key；它是社区封装，本次仅作为音色试听/技术验证，不把连通成功当成服务稳定性或正式发布许可已经确认。付费专业 TTS 仍保留为后续可选方案。

## 实片到达后的最低验证

先用 10—15 秒自录素材验证 H.264/AAC 输出、中文字幕、HUD 可见、声音电平与剪接同步；再处理长片。默认一条重 I/O/编码任务，保存代理与时间索引，后续修改复用已有分析。

在 Windows 使用项目内完整 FFmpeg 构建，不改共享 PATH。转写只处理必要音轨，选镜由时间码、画面和实际功能共同决定。云配音默认只发送已定中文稿；若选择云视频理解，先明确其接收的素材片段和服务。

FFmpeg 功能依据：[官方滤镜文档](https://ffmpeg.org/ffmpeg-filters.html)。本地转写依据：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)。云语音依据：[MiniMax 官方 MCP](https://github.com/MiniMax-AI/MiniMax-MCP)、[MiniMax CLI](https://github.com/MiniMax-AI/cli)、[ElevenLabs 模型文档](https://elevenlabs.io/docs/overview/models)。
