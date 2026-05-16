# video-transcript — 视频逐字稿提取 Skill

把 B 站 / 抖音 / 小红书 / YouTube 视频自动转成逐字稿。
全程在你电脑后台跑，**不弹窗、不要登录视频网站**。

默认使用 **本地 SenseVoice/FunASR** 转写,不需要豆包 API Key,也不会把视频发给云端 ASR。原来的豆包视频理解仍保留为可选引擎:`--engine doubao`。

这个版本整合了原 `douyin-transcript` 的抖音下载兜底:抖音视频会按 `Content-Length` 做 Range 分片下载,并用视频时长校验下载结果,避免半截 mp4 进入后续转写。

---

## ⚡ 一键安装（macOS 推荐）

复制下面这一行，粘贴到终端回车，全程跟着提示按回车就行：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/voyagerwang/douyin-transcript-skill/main/bootstrap.sh)
```

引导脚本会自动：
1. 把 skill 文件拉到 `~/.claude/skills/video-transcript/`（优先 `npx skills add`，回退 git，再回退 tarball）
2. 检查/安装 ffmpeg（必要时连 Homebrew 一起装）
3. 装 `yt-dlp` + `playwright` + Chromium 浏览器引擎（~300MB）
4. 检查本地 SenseVoice/FunASR 环境
5. 跑 `--doctor` 自检

完成后在 Claude Code 里就能用 `/video-transcript <视频链接>`。

### 标准两步安装

```bash
# 1. 拉 skill 文件
npx skills add voyagerwang/douyin-transcript-skill -a claude-code -g -y

# 2. 装系统依赖
bash ~/.claude/skills/video-transcript/install.sh
```

### 老手手动 4 步

```bash
brew install ffmpeg
pip3 install --break-system-packages -r ~/.claude/skills/video-transcript/requirements.txt
python3 -m playwright install chromium
export SENSEVOICE_PYTHON="/path/to/your/funasr/python"
```

---

## 本地 SenseVoice 配置

如果当前 `python3` 没有安装 `funasr` 和 `torch`,可以复用已有环境:

```bash
export SENSEVOICE_PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
export SENSEVOICE_REPO="/path/to/SenseVoice"   # 可选,本地 model.py 所在仓库
export SENSEVOICE_DEVICE="cpu"                 # 可选: cpu / mps / cuda:0
export SENSEVOICE_MODEL="iic/SenseVoiceSmall"  # 可选
export VIDEO_TRANSCRIPT_OUTPUT_DIR="/path/to/Inbox"
export VIDEO_TRANSCRIPT_IMAGES_DIR="/path/to/Inbox/images"
```

检查:

```bash
python3 ~/.claude/skills/video-transcript/scripts/transcript.py --doctor
```

---

## 🚀 用法

### 在 Claude Code 里
```
/video-transcript <视频 URL>
```

支持：
- B 站：`https://www.bilibili.com/video/BVxxx`
- 抖音：`https://www.douyin.com/video/xxx` 或 `https://v.douyin.com/xxx`
- 小红书：`https://www.xiaohongshu.com/discovery/item/xxx` 或短链 `xhslink.com/xxx`
- YouTube：`https://youtube.com/watch?v=xxx`
- 本地文件：`/path/to/video.mp4`

### 终端直接跑
```bash
python3 ~/.claude/skills/video-transcript/scripts/transcript.py "<URL>"
```

默认等价于:

```bash
python3 ~/.claude/skills/video-transcript/scripts/transcript.py "<URL>" --engine local
```

如需使用原豆包视频理解:

```bash
python3 ~/.claude/skills/video-transcript/scripts/transcript.py "<URL>" --engine doubao
```

### 实际体验
跑命令时会看到：
```
[Step 0/3] 探测视频元信息...
═══════════════════════════════════════════════════════
  📊 视频探测
───────────────────────────────────────────────────────
  平台:      B 站
  标题:      在浙江和安徽之间，一座10万人的城市消失了
  时长:      17分12秒
  分段:      3 段(每段 ≤ 6 分钟)
  预估耗时:  3分20秒 ~ 5分25秒
═══════════════════════════════════════════════════════
```
然后自动跑 下载 → 校验完整性 → 切片 → 抽音频 → 本地 SenseVoice 转录 → 合并，全程无人值守。

---

## 📝 输出

逐字稿默认**两个去处**：
1. **stdout**：完整 Markdown 直接打印（适合 Claude Code 直接展示，或 `| pbcopy`）
2. **落盘**：`VIDEO_TRANSCRIPT_OUTPUT_DIR/<标题>_transcript.md`；未配置时为 `~/.claude/skills/video-transcript/outputs/`

图片、封面或后续衍生图片统一放到 `VIDEO_TRANSCRIPT_IMAGES_DIR`；未配置时为输出目录下的 `images/`。

格式示例：
```markdown
# 视频标题

> 时长 5:32 | 来源: <URL>

## 1. 引入话题 [00:00 - 00:42]
大家好，今天我们要聊的是...

## 2. 核心观点 [00:42 - 02:15]
那么我的看法是这样的，首先...
```

特性：
- **本地转写**：默认使用 SenseVoice/FunASR,不调用云 ASR
- **段落级时间戳**：`[MM:SS - MM:SS]` 方便定位
- **长视频自动分段**：超 8 分钟切成 6 分钟/段独立转录
- **可选云引擎**：显式 `--engine doubao` 时才走豆包视频理解

---

## 🛠 命令行选项

| 参数 | 说明 |
|---|---|
| `input` | 视频 URL 或本地文件路径（必需，`--doctor` 时不需要） |
| `--title` | 视频标题（默认用探测到的标题） |
| `--target-size` | 压缩目标大小 MB，默认 30 |
| `--no-save` | 不写 .md 文件（默认会保存） |
| `--output-dir` | 改输出目录 |
| `--images-dir` | 改图片/封面等资产输出目录 |
| `--engine` | `local` 或 `doubao`,默认 `local` |
| `--language` | 本地 SenseVoice 语言,默认 `zh`,可设 `auto` |
| `--doctor` | 体检模式：检查所有依赖+配置 |

---

## 🩺 故障排查

```bash
python3 ~/.claude/skills/video-transcript/scripts/transcript.py --doctor
```

会逐项检查：ffmpeg / ffprobe / Python / yt-dlp / playwright / chromium / 本地 SenseVoice/FunASR。豆包 API Key 只有 `--engine doubao` 需要。

### 常见问题

| 现象 | 处理 |
|---|---|
| `local SenseVoice/FunASR 未配置` | 设置 `SENSEVOICE_PYTHON` 指向已有 funasr/torch 环境 |
| `[ERROR] 没找到豆包 API Key` | 仅 `--engine doubao` 需要;检查 `.env` |
| API 报 "模型未授权" / 401 | 火山方舟控制台 → 模型广场 → 给 Doubao-Seed-2.0-pro 点"开通" |
| 抖音/小红书抓不到视频 | 平台前端可能改版，参考 `FALLBACK.md` 手动方案 |
| B 站 yt-dlp 报 412 | 正常，已自动 fallback 到 headless 浏览器，不用管 |
| 长视频被概括而不是逐字 | 已自动分段处理；如仍概括请提 issue 附上 URL |
| `playwright` 报 chromium 找不到 | `python3 -m playwright install chromium` |
| Chromium 下载失败 | 国内网络问题；可设代理或重试 |

---

## 🏗 架构

```
~/.claude/skills/video-transcript/
├── SKILL.md                      ← Claude Code 入口文档
├── README.md                     ← (本文件)
├── FALLBACK.md                   ← 抓取失效时的人工兜底
├── install.sh                    ← 一键安装向导
├── bootstrap.sh                  ← 一行命令入口(三档兜底拉 skill + 跑 install.sh)
├── requirements.txt              ← Python 依赖列表
├── .env                          ← 用户私有配置(API Key)，.gitignore
├── .gitignore
├── outputs/                      ← 逐字稿落盘目录
└── scripts/
    ├── transcript.py             ← 主流程(--doctor 体检 / probe / 切片 / 合并)
    └── platform_extractor.py     ← 抖音/小红书/B 站 headless 直链抓取
```

流程：
```
探测元信息(headless,拿 title+duration+直链 URL)
  ↓
打印评估表(平台/标题/时长/分段/预估耗时)
  ↓
下载(复用探测拿到的直链,不重启浏览器)
  ↓
长视频(>8min)切片 → 每段独立压缩(目标 30MB,智能选分辨率)
  ↓
逐段抽音频,调用本地 SenseVoice/FunASR
  ↓
合并各段 + 时间戳偏移修正
  ↓
stdout + 落盘 outputs/
```

---

## 📦 手动安装（不想用 install.sh）

```bash
# 0. 把 skill 拷贝到 ~/.claude/skills/video-transcript/

# 1. ffmpeg
brew install ffmpeg

# 2. Python 包
pip install --break-system-packages -r ~/.claude/skills/video-transcript/requirements.txt

# 3. Chromium
python3 -m playwright install chromium

# 4. 配置本地 SenseVoice 环境
export SENSEVOICE_PYTHON="/path/to/python-with-funasr-and-torch"

# 5. 体检
python3 ~/.claude/skills/video-transcript/scripts/transcript.py --doctor
```

---

## 🔒 隐私

- 默认本地转写,不会上传视频到云端 ASR
- 临时视频和音频只在本机处理
- 只有显式 `--engine doubao` 时才会把压缩后视频发给豆包 API

---

## 🤝 反馈

平台前端改版导致抓取失效是常态。遇到失败：
1. 跑 `--doctor`
2. 看 `FALLBACK.md` 手动绕开
3. 提 issue 附上 URL + 报错日志
