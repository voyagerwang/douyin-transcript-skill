#!/usr/bin/env python3
"""Backward-compatible wrapper for the unified local video transcript tool."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Compatibility wrapper for Douyin transcription.")
    parser.add_argument("--share-text", required=True, help="Douyin share text or URL.")
    parser.add_argument("--output-root", default="", help="Legacy output root; mapped to --output-dir when set.")
    parser.add_argument("--language", default="zh", help="SenseVoice language, e.g. zh or auto.")
    parser.add_argument("--keep-media", action="store_true", help="Accepted for compatibility; media cleanup is internal.")
    parser.add_argument("--engine", choices=["local", "doubao"], default="local")
    args = parser.parse_args()

    script = Path(__file__).with_name("transcript.py")
    cmd = [
        sys.executable,
        str(script),
        args.share_text,
        "--engine",
        args.engine,
        "--language",
        args.language,
    ]
    if args.output_root:
        cmd.extend(["--output-dir", args.output_root])
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
