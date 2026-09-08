# 视频制作环境与小样

> 2026-09-05前期记录，现已作为历史制作资料保留；最终成片、发布状态及署名以[视频首页](README.zh-CN.md)和实际产品目录为准。

记录日期：2026-09-05。范围：本地前期准备与合成样例，实际 40 分钟游戏素材尚未提供。

## 安装位置

视频工作目录为仓库内 `artifacts/video-production/lc2-v176`，原片之外的代理、模型、合成和输出都放在这里。该目录受现有 Git 忽略规则保护，不进入盒子发布包。

| 组成 | 已配置状态 |
| --- | --- |
| Python | 独立 `.venv`，Python 3.13 x64；依赖版本保存在 `requirements.lock.txt`，`pip check` 通过 |
| FFmpeg | imageio-ffmpeg 0.6.0 提供项目内 FFmpeg 7.1；libx264、libass/subtitles、loudnorm、sidechaincompress 均可用，编码与字幕已实测 |
| 语音 | edge-tts 7.2.8；用户已选 A：zh-CN-YunyangNeural，正式旁白按句优化停顿；faster-whisper 1.2.1 已可导入 |
| 动画 | Remotion/CLI 4.0.520、React 19.2.3，保存在 `motion`；npm 依赖写入 package-lock.json |
| 渲染浏览器 | 使用本机已有 Chrome；中文使用本机 Microsoft YaHei，未把字体文件打包公开 |
| 官方技能 | remotion-best-practices、create、render、markup、captions、docs；按官方仓库提交 54e9b19a612897171e0b3b242e01c2badba4a272 安装 |

技能进入用户技能目录，后续对话可发现；其余依赖安装在本次视频工作目录。没有修改共享 Python、Node 或 PATH，没有注册新的远程 MCP，没有使用付费生成接口。

## 已执行验证

- `smoke_env.py`：3 秒 H.264/AAC 编码，1280×720、30 fps、yuv420p；中文 ASS 渲染可见且无缺字。编码、混音、字幕的最小组合通过。
- `smoke_env.py --tts`：在线列举音色后选 zh-CN-YunxiNeural，语速 -8%，生成 11.544 秒 MP3。只发送自写试音文本，不发送原片。
- `npx tsc --noEmit`：片头工程类型检查通过。
- `remotion still` + `remotion render`：5 秒、150 帧猫爪动画导出通过，使用本机 Chrome、渲染并发 2。
- FFmpeg 添加原创轻合成音效并规范输出为 1920×1080、30 fps、H.264 yuv420p / AAC；成片 5 秒，全片解码无错误。静帧已检查中文排版和主体边界。
- Remotion Studio：本机预览服务成功启动，页面返回 HTTP 200，约 315 ms 完成构建。测试后已停止本次进程，保留 MP4 文件预览，不持续占用后台渲染资源。

本地识别实际结果由 `samples/transcription-smoke.json` 记录：faster-whisper tiny、CPU int8、2 线程成功识别 11.544 秒样片，产生 5 段及词时间戳。第一次模型下载在 180 秒超时，保留部分下载；第二次续传并完成测试耗时 55.08 秒。模型已本地缓存，版本 d90ca5fe260221311c53c58e660288d3deb8d356。tiny 把“加菲”等词识别错了，因此这只证明管线可工作；实际字幕需原稿校正，正式原声转写再用样片评估是否需要更大模型。

## 看小样

当前修订优先看 [第二版记录](REVISION_02.zh-CN.md)：`samples/cat-terminal-intro-v2-glitch.mp4`，以及 `samples/voice-v2-A-listen.mp3`、`samples/voice-v2-B-listen.mp3`。下面保留第一版的历史位置。

当前用户确认与生产选择以 `production-choices.json` 为准：LC2 专用 Glitch 片头 + A 男声；停顿裁剪参考为 `samples/voice-v3-A-pause-trim.mp3`。通用片头未开始。

- 片头：`samples/cat-terminal-intro-preview.mp4`
- 片头静帧：`samples/intro-frame.png`
- 中文音色试听：`samples/voice-preview.mp3`
- 字幕/编码测试片：`samples/encoding-subtitle-smoke.mp4`

片头标有“方向小样”，用于先看猫元素、颜色和节奏。音乐为脚本合成的轻量试作，正式片头/片尾与 BGM 仍可按录屏调整。旁白仅完成生成与媒体格式检查，最终音色听感、作者名发音和全长混音还要试听。

## 以后如何继续

在视频目录下，可用 `.venv/Scripts/python.exe smoke_env.py` 再做短测试。动画在 `motion` 下用 `npx remotion studio --no-open` 打开 Studio，合成 ID 为 `CatTerminalIntro`；渲染命令需指定本机 Chrome 路径，避免另下浏览器。实际调用记录与环境路径在 `environment-receipt.json`，技能来源在 `skill-install-receipt.json`。

收到录屏后，先测试 10—15 秒实际素材，确认浮层被录入、音轨可分离、变帧率/色彩处理正确，再索引整片。默认一次只跑一条长转码/模型下载/渲染任务。

目前没有必须由维护者完成的登录或权限操作。如果最后决定使用 MiniMax/ElevenLabs 专业配音，再选择服务并由维护者登录或在本地配置凭据；不需要在聊天里粘贴密钥。
