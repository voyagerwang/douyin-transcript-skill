# Douyin Transcript

Codex skill and local CLI helper for extracting Douyin video transcripts with local SenseVoice/FunASR.

The workflow is local-first:

1. Parse a Douyin copied share text or short link.
2. Temporarily download the video.
3. Extract 16 kHz mono audio with FFmpeg.
4. Transcribe with local SenseVoice through FunASR.
5. Let Codex produce an optimized transcript.
6. Delete temporary video/audio and raw handoff files, leaving only the optimized Markdown transcript.

## Requirements

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

## Codex Skill Usage

Install by copying or symlinking this folder to your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/douyin-transcript ~/.codex/skills/douyin-transcript
```

Then ask Codex with a Douyin share text:

```text
用 douyin-transcript 提取这个抖音视频：<copied share text>
```

## OpenClaw / Agents Usage

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

The skill tells Codex to keep only:

```text
~/Downloads/douyin-transcripts/<video_id>/transcript.optimized.md
```

## CLI Usage

The bundled script handles media parsing, download, audio extraction, local ASR, and cleanup:

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

When used outside Codex, you can edit `transcript.raw.md` manually or run your own cleanup step. The full skill workflow expects Codex to create `transcript.optimized.md`, then delete `metadata.json` and `transcript.raw.md`.

Use `--keep-media` only when you explicitly want to keep downloaded video and extracted audio for debugging.

## Privacy

This project is designed for local transcription. It does not call cloud ASR APIs. It does download the Douyin video to a temporary local directory during processing and deletes that media by default.

Only process content you have the right to download and transcribe.
