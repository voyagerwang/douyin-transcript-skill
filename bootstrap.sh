#!/usr/bin/env bash
# One-line installer for video-transcript.

set -e

REPO="voyagerwang/douyin-transcript-skill"
TARGET="$HOME/.claude/skills/video-transcript"

say() { printf "▸ %s\n" "$1"; }
ok() { printf "  ✓ %s\n" "$1"; }
warn() { printf "  ⚠ %s\n" "$1"; }

register_codex() {
  local codex_home="${CODEX_HOME:-$HOME/.codex}"
  if [ ! -d "$codex_home" ]; then
    return 0
  fi
  mkdir -p "$codex_home/skills" "$codex_home/prompts"
  ln -sfn "$TARGET" "$codex_home/skills/video-transcript"
  ln -sfn "$TARGET" "$codex_home/skills/douyin-transcript"
  cat > "$codex_home/prompts/video-transcript.md" <<'PROMPT_EOF'
You are a local video transcript extractor. The user provides a video URL
(B站 / 抖音 / 小红书 / YouTube) or a local file path as $ARGUMENTS.

Run this command, streaming both stderr and stdout:

    python3 ~/.claude/skills/video-transcript/scripts/transcript.py "$ARGUMENTS"

As soon as the script prints the 📊 评估表, tell the user the title, duration,
segment count, and estimated time. When it finishes, display the transcript.
PROMPT_EOF
  ok "Registered Codex skills and /video-transcript prompt"
}

if [ -e "$TARGET" ]; then
  warn "$TARGET already exists; replacing it"
  rm -rf "$TARGET"
fi

mkdir -p "$(dirname "$TARGET")"
tmp="$(mktemp -d)"

say "Downloading $REPO"
if command -v git >/dev/null 2>&1; then
  git clone --depth=1 "https://github.com/$REPO.git" "$tmp/repo"
  rm -rf "$tmp/repo/.git"
  mv "$tmp/repo" "$TARGET"
else
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.tar.gz" | tar xz -C "$tmp"
  mv "$tmp"/* "$TARGET"
fi

rm -rf "$tmp"
ok "Installed to $TARGET"

register_codex

say "Installing dependencies"
bash "$TARGET/install.sh"
