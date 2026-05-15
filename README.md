# Douyin Transcript

Douyin Transcript is a local-first tool and reusable agent skill for extracting Douyin video transcripts with SenseVoice/FunASR.

抖音转写工具：基于本地 SenseVoice/FunASR 提取抖音视频文稿。它既可以作为命令行工具单独使用，也可以接入 Codex、OpenClaw 或其它支持本地 skill/agent 工作流的工具；并不限制只能在 Codex 中使用。

The workflow is local-first:

1. Parse a Douyin copied share text or short link.
2. Temporarily download the video.
3. Extract 16 kHz mono audio with FFmpeg.
4. Transcribe with local SenseVoice through FunASR.
5. Optionally let an agent or your own editing step produce an optimized transcript.
6. Delete temporary video/audio and raw handoff files when you only want the final Markdown transcript.

本地流程：

1. 解析抖音复制口令或短链接。
2. 临时下载视频。
3. 使用 FFmpeg 抽取 16 kHz 单声道音频。
4. 使用本地 SenseVoice/FunASR 转写。
5. 可选：交给 Codex、OpenClaw 或其它 Agent 做错别字修正、断句和排版。
6. 默认删除临时视频和音频；如果按 skill 工作流使用，最终只保留优化后的 Markdown 文稿。

## Requirements / 环境要求

- Python 3.10+
- `curl`
- `ffmpeg`
- Python packages in `requirements.txt`

Install FFmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

If FFmpeg is missing, the script stops immediately and prints the matching install command:

- Windows: `winget install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

Windows users do not need to run Python with `-X utf8`; the script configures UTF-8 stdio and subprocess decoding internally.

Windows 用户不需要手动加 `-X utf8`，脚本内部已经处理了 UTF-8 输出和子进程解码。

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

If your local SenseVoice/FunASR installation lives in a different Python environment, set:

```bash
export SENSEVOICE_PYTHON="/path/to/python"
```

Optional environment variables:

```bash
export SENSEVOICE_MODEL="iic/SenseVoiceSmall"
export SENSEVOICE_DEVICE="cpu"        # or mps / cuda:0
export SENSEVOICE_REPO="/path/to/SenseVoice"  # optional repo containing model.py
```

## Codex Skill Usage / Codex Skill 用法

Install by copying or symlinking this folder to your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/douyin-transcript ~/.codex/skills/douyin-transcript
```

Then ask Codex with a Douyin share text:

```text
用 douyin-transcript 提取这个抖音视频：<copied share text>
```

## OpenClaw / Agents Usage / OpenClaw 与其它 Agent 用法

Install by copying or symlinking this folder to your agents skills directory:

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/douyin-transcript ~/.agents/skills/douyin-transcript
```

OpenClaw-compatible launch metadata is available at:

```text
agents/openclaw.yaml
```

Then ask OpenClaw with a Douyin share text:

```text
Use douyin-transcript to extract and optimize this Douyin video: <copied share text>
```

The skill workflow tells the agent to keep only:

如果按 skill 工作流使用，Agent 会在完成优化后只保留：

```text
~/Downloads/douyin-transcripts/<video_id>/transcript.optimized.md
```

## CLI Usage / 命令行用法

The bundled script handles media parsing, download, audio extraction, local ASR, and cleanup:

脚本可以脱离任何 Agent 独立运行，负责解析、下载、抽音频、本地 ASR 和清理：

```bash
python3 scripts/douyin_transcribe.py \
  --share-text "复制打开抖音 ... https://v.douyin.com/xxxx/" \
  --output-root "$HOME/Downloads/douyin-transcripts"
```

It prints JSON with temporary handoff files:

```json
{
  "metadata": ".../metadata.json",
  "raw_transcript": ".../transcript.raw.md"
}
```

When used outside an agent, you can edit `transcript.raw.md` manually or run your own cleanup step. The full skill workflow expects the agent to create `transcript.optimized.md`, then delete `metadata.json` and `transcript.raw.md`.

不接 Agent 时，你可以直接编辑 `transcript.raw.md`，或者接入自己的文本优化流程。接 Agent 时，完整 workflow 会让 Agent 生成 `transcript.optimized.md`，然后删除 `metadata.json` 和 `transcript.raw.md`。

Use `--keep-media` only when you explicitly want to keep downloaded video and extracted audio for debugging.

只有在调试下载或转写问题时才建议使用 `--keep-media` 保留视频和音频。

## Privacy / 隐私说明

This project is designed for local transcription. It does not call cloud ASR APIs. It does download the Douyin video to a temporary local directory during processing and deletes that media by default.

本项目默认使用本地转写，不调用云端 ASR API。处理过程中会把抖音视频临时下载到本地目录，并默认在转写后删除临时媒体文件。

Only process content you have the right to download and transcribe.

请只处理你有权下载和转写的内容。
