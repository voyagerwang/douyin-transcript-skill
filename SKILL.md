---
name: douyin-transcript
description: Extract, locally transcribe, optimize, and clean up Douyin/TikTok China share videos. Use when the user provides a Douyin share link or copied share text and asks to extract video text, generate a transcript, use local Whisper/SenseVoice, improve ASR typos, or keep only the optimized transcript while deleting downloaded media.
---

# Douyin Transcript

## Workflow

Use the bundled script for the deterministic media work, then use the current agent or your own editing step for the language-sensitive cleanup.

1. Run `scripts/douyin_transcribe.py` with the user's full share text.
2. Read the generated `transcript.raw.md` and `metadata.json`. Confirm `duration_ms` is present when available and that the ASR log processed the expected duration; if the transcript is suspiciously short, re-run before cleanup.
3. Create `transcript.optimized.md` in the same directory.
4. Optimize only as a transcript correction pass:
   - Fix obvious ASR typos, homophones, names, book titles, and classical/history terms.
   - Add punctuation, paragraphing, and readable line breaks.
   - Preserve the speaker's meaning, sequence, and tone.
   - Do not summarize, add examples, or rewrite into an article unless the user asks.
5. Delete `transcript.raw.md` and `metadata.json` after the optimized file is written and checked, unless the user asks to keep metadata.
6. Confirm only `transcript.optimized.md` remains in the video output directory, unless the user explicitly asked to keep media or metadata.

Default final artifact:

```text
~/Downloads/douyin-transcripts/<video_id>/transcript.optimized.md
```

## Command

From this skill folder:

```bash
python3 scripts/douyin_transcribe.py \
  --share-text "<full Douyin share text>" \
  --output-root "$HOME/Downloads/douyin-transcripts"
```

The script prints JSON containing:

- `metadata`: video title, id, and download URL
- `raw_transcript`: temporary ASR transcript path

The script validates ranged video downloads against the server-reported byte length before extracting audio. It deletes downloaded video and extracted audio by default. Use `--keep-media` only when the user explicitly asks to keep media or when debugging an incomplete transcript. The raw transcript and metadata are temporary handoff files for the agent or cleanup step; remove them after writing `transcript.optimized.md`.

The script configures Python stdio and subprocess decoding as UTF-8, so Windows users do not need to run Python with `-X utf8` manually.

## Local ASR Assumptions

The script uses local SenseVoice through `funasr`.

Defaults:

- SenseVoice model: `iic/SenseVoiceSmall`
- Device: `mps` when available, then `cuda:0`, then `cpu`
- Output root: `~/Downloads/douyin-transcripts`
- Python: use the current interpreter when it has `funasr` and `torch`; set `SENSEVOICE_PYTHON` to another interpreter when needed.
- Optional local repo for `model.py`: set `SENSEVOICE_REPO` if your SenseVoice install needs a local remote-code file.
- On Windows, the script can discover common bundled `ffmpeg.exe` locations such as JianyingPro/CapCut. If needed, set `FFMPEG_BINARY` to an explicit executable path.

Useful overrides:

```bash
SENSEVOICE_MODEL="/path/or/model/name"
SENSEVOICE_REPO="/path/to/SenseVoice"
SENSEVOICE_DEVICE="cpu"
SENSEVOICE_PYTHON="/path/to/python"
```

If `funasr` or `torch` is missing, report the missing dependency and stop. Do not silently fall back to cloud ASR. Use cloud ASR only if the user explicitly asks for it.

If `ffmpeg` is missing, the script reports the dependency and prints an OS-specific install command:

- Windows: `winget install ffmpeg`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## Optimization Rules

Use the video title and surrounding context to correct terms. For Chinese history or classics content, strongly prefer canonical terms when the raw transcript has likely homophones.

Examples:

- `祭篇` / `G片` -> `计篇`
- `五是七计` / `武士七迹` -> `五事七计`
- `道天地降法` -> `道、天、地、将、法`
- `降熟有能` -> `将孰有能`
- `煮熟有道` -> `主孰有道`
- `法令熟刑` -> `法令孰行`
- `赏罚孰名` -> `赏罚孰明`
- `算无一册` -> `算无遗策`

Keep uncertain corrections conservative. If a term is unclear, prefer leaving a plausible transcript over inventing a polished but unsupported phrase.
