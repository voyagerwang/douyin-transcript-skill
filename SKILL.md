---
name: video-transcript
description: |
  视频逐字稿提取专家(默认本地 SenseVoice/FunASR,可选豆包视频理解模型)。支持 B 站 / 抖音 / 小红书 / YouTube 链接或本地视频。全程在用户电脑后台运行(headless),不弹窗、不要求登录视频网站。默认下载到本地后用本地算力转写;长视频自动分段处理。
  触发场景:
  - 用户说"出逐字稿"、"提取逐字稿"、"转文字"、"视频转文字"
  - 用户说"听写视频"、"提取视频文案"、"视频字幕"
  - 用户使用 /video-transcript 命令
  - 用户贴一个视频链接(B站 / 抖音 / 小红书 / YouTube),意图是要文字版
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# 视频逐字稿提取专家

> 输入视频链接或本地路径 → 自动探测 → 后台下载 → 切片 → 本地 SenseVoice 转录 → Markdown 逐字稿(stdout + 落盘)

默认引擎是 `local`,即本地 SenseVoice/FunASR。只有用户明确要求云端视频理解或传 `--engine doubao` 时,才使用豆包 API。

## 阶段 0 · 定位 skill 根目录(第一件事)

被触发时你必须先定位自己,跑这段:

```bash
VT_HOME="$(
  for d in "$HOME/.claude/skills/video-transcript" \
           "$(pwd)/.claude/skills/video-transcript" \
           "$(pwd)/skills/video-transcript" \
           "$HOME/.claude/plugins/video-transcript/video-transcript"; do
    [ -f "$d/SKILL.md" ] && echo "$d" && break
  done
)"
export VT_HOME
echo "VT_HOME=$VT_HOME"
```

如果输出为空,说明 skill 安装位置非标准。让用户给出路径,然后手工 `export VT_HOME=<路径>`。
之后**所有命令**都通过 `"$VT_HOME/scripts/transcript.py"`,不要用相对路径或绝对路径硬编码。

## 阶段 1 · 依赖体检(首次/可疑时)

第一次跑或者遇到报错时,先做体检:

```bash
python3 "$VT_HOME/scripts/transcript.py" --doctor
```

如果有 ✗ 项,告诉用户:
- 缺 ffmpeg / playwright / chromium / funasr / torch 等 → 跑安装向导或配置 `SENSEVOICE_PYTHON`:
  ```bash
  bash "$VT_HOME/install.sh"
  ```
- 体检全 ✓ 才进入阶段 2。

## 阶段 2 · 触发方式与执行

用户给视频链接(URL 或本地路径)就直接跑:

```bash
python3 "$VT_HOME/scripts/transcript.py" "<URL或本地路径>"
```

支持的输入:
- B 站:`https://www.bilibili.com/video/BVxxx` 或 `b23.tv/xxx` 短链
- 抖音:`https://www.douyin.com/video/xxx`、`v.douyin.com/xxx`、`douyin.com/jingxuan?modal_id=xxx`
- 小红书:`xiaohongshu.com/discovery/item/xxx`、`xiaohongshu.com/explore/xxx`、`xhslink.com/xxx`
- YouTube:`youtube.com/watch?v=xxx`、`youtu.be/xxx`
- 本地视频文件路径

脚本自动:
0. **探测** — 启动 headless 浏览器,拿标题、时长、视频/音频直链;打印 📊 评估表 + 预估耗时
1. **下载** — 复用探测拿到的直链(不重启浏览器);B 站走 dash 流(分别下载 video/audio + ffmpeg 合并);其他平台直接 mp4
2. **长视频切片** — 总时长 > 8min 自动切成 6min/段,避免被模型概括成摘要
3. **压缩** — ffmpeg,目标 30MB;按时长自动选分辨率,一次到位
4. **本地转录** — ffmpeg 抽音频,用本地 SenseVoice/FunASR 转写
5. **合并** — 长视频合并各段输出,保留段落级时间范围

抖音下载路径必须保留完整性校验:脚本会优先按服务器 `Content-Length` 做 Range 分片下载,并用页面时长/ffprobe 时长校验是否下载到半截文件。若时长明显短于预期,不要进入转写和清理,先重跑。

### ⚠️ 你(agent)必须做的两件事

**(1) 评估表复述 — 给用户等待预期**

脚本启动后,stderr 第一段就会打印 📊 视频探测评估表。**你必须立刻把它复述给用户**,告诉他:
- 视频标题、时长、分段数
- **预估耗时**(给用户一个等待预期,这点最重要)

不要等转录跑完才说,**先复述评估表 → 再继续等待转录**。如果用户看不到时长和耗时预估,会以为程序卡死。

例:
> 视频探测完成:
> - 平台:B 站 / 标题:《xxx》
> - 时长 17 分 12 秒,会切成 3 段独立转录
> - **预估耗时 3 分 20 秒 ~ 5 分 25 秒**,正在跑,稍等...

**(2) 转录完成后必须输出完整逐字稿全文**

脚本最后会把完整 Markdown 逐字稿打印到 stdout。**你必须把整篇逐字稿原样展示在对话里**,不要只说"已保存到 xxx.md"——那等于用户什么都没看到。

正确做法:
1. 抓 stdout 里 `# <标题>` 之后的全部 Markdown
2. 完整复述给用户(标题、时长、所有段落)
3. 末尾附一行说明落盘路径,方便用户后续打开 .md 文件

错误做法:
- ❌ "逐字稿已保存到 outputs/xxx.md,请查看文件"
- ❌ 只展示前几段就省略
- ❌ 总结/精简内容(逐字稿要逐字展示)

## 阶段 3 · 输出去处

脚本会**两个去处同时输出**:
1. **stdout 直出**完整 Markdown 全文 — 供 agent 复述给用户(见阶段 2 第 2 条强制要求)
2. **落盘**到 `$VT_HOME/outputs/<标题>_transcript.md` — skill 自管,所有产出归一处

如果用户要“优化后只保留最终稿”,agent 在脚本完成后应读取 Markdown,做错别字/同音词/断句修正,写回同一路径或另存 `*.optimized.md`,并删除临时 raw/中间文件。不要删除用户显式要求保留的媒体或调试文件。

**取消落盘**:`--no-save`
**改保存路径**:`--output-dir <path>`

### 评估表样例

```
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

### 输出格式样例

```markdown
# 视频标题

> 时长 5:32 | 来源: <URL或文件名>

## 1. 引入话题 [00:00 - 00:42]
大家好,今天我们要聊的是...

## 2. 核心观点 [00:42 - 02:15]
那么我的看法是这样的,首先...
```

特性:
- **语义分段**:按主题自动分 3-8 段,每段一个简短小标题
- **段落级时间戳**:每段开头标 `[MM:SS - MM:SS]`,定位方便
- **逐字转录**:保留口语词("呃""那""啊""就是")、网络梗、停顿,不总结、不改写
- **无人声段落**:用 `_(此处无人声,XX秒)_` 标注

## 阶段 4 · 异常处理

| 场景 | 处理 |
|---|---|
| `--doctor` 报缺依赖 | 跑 `bash "$VT_HOME/install.sh"` |
| `local SenseVoice/FunASR 未配置` | 设置 `SENSEVOICE_PYTHON` 指向已有 funasr/torch 环境,或在当前 Python 安装依赖 |
| `没找到豆包 API Key` | 仅 `--engine doubao` 需要;检查 `$VT_HOME/.env` |
| API 401 / "模型未授权" | 火山方舟控制台 → 模型广场 → 给 Doubao-Seed-2.0-pro 点"开通" |
| 抖音图文笔记(note 链接) | 提示用户不支持图文,仅支持视频 |
| 平台前端改版导致抓取失败 | 看 `$VT_HOME/FALLBACK.md` 走人工兜底 |
| 长视频被模型概括而非逐字 | 已自动处理(>8min 切片);仍出现请反馈 |
| 压缩后视频仍 > 50MB | 脚本自动迭代降码率/分辨率(最多 4 轮) |

## 命令行选项

| 参数 | 说明 |
|---|---|
| `input` | 视频 URL 或本地文件路径(必需,`--doctor` 时可省) |
| `--title` | 视频标题(默认用探测到的) |
| `--target-size` | 压缩目标大小 MB,默认 30 |
| `--no-save` | 不落盘 .md(默认会保存到 `$VT_HOME/outputs/`) |
| `--output-dir` | 改保存路径 |
| `--engine` | `local` 或 `doubao`,默认 `local` |
| `--language` | 本地 SenseVoice 语言,默认 `zh`,可设 `auto` |
| `--doctor` | 体检模式:检查依赖+配置 |

## Notes

- 默认使用本地 SenseVoice/FunASR,不上传视频到云端 ASR
- 本地模式时间戳精度为切片级/段落级(不是词级/句级),用于章节定位
- 默认 stdout 直接输出 Markdown 全文(供上层 agent 展示);**同时**落盘
- 预估耗时模型(粗估):headless 启动 + 下载 + 本地 ASR,给 ±20% 范围
- 豆包 API Key 仅 `--engine doubao` 需要,配置存在 `$VT_HOME/.env`(权限 600,gitignore),不会随仓库分发
