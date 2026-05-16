#!/usr/bin/env bash
# video-transcript local install helper

set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say() { printf "▸ %s\n" "$1"; }
ok() { printf "  ✓ %s\n" "$1"; }
warn() { printf "  ⚠ %s\n" "$1"; }

say "Checking ffmpeg"
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  ok "ffmpeg / ffprobe"
else
  warn "ffmpeg is missing"
  case "$(uname -s)" in
    Darwin) echo "Install with: brew install ffmpeg" ;;
    Linux) echo "Install with: sudo apt install ffmpeg" ;;
    *) echo "Install with: winget install ffmpeg" ;;
  esac
fi

say "Installing Python helpers"
python3 -m pip install --break-system-packages --upgrade -r "$SKILL_DIR/requirements.txt"

say "Installing Playwright Chromium"
python3 -m playwright install chromium

if [ -n "${SENSEVOICE_PYTHON:-}" ]; then
  ok "Using SENSEVOICE_PYTHON=$SENSEVOICE_PYTHON"
else
  warn "If current python3 does not have funasr and torch, set SENSEVOICE_PYTHON=/path/to/python"
fi

say "Running doctor"
python3 "$SKILL_DIR/scripts/transcript.py" --doctor
