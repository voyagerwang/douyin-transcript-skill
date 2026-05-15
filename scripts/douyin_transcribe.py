#!/usr/bin/env python3
"""Download a Douyin video temporarily and transcribe it with local SenseVoice."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)
FFMPEG_BIN = "ffmpeg"

def run(cmd: list[str], *, timeout: int | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed: {joined}\n{result.stderr.strip()}")
    return result


def run_bytes(cmd: list[str], *, timeout: int | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        joined = " ".join(cmd)
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"Command failed: {joined}\n{stderr.strip()}")
    return result


def decode_html(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    if "\ufffd" not in text:
        return text
    try:
        gb_text = data.decode("gb18030")
    except UnicodeDecodeError:
        return text
    return gb_text if gb_text.count("\ufffd") < text.count("\ufffd") else text


def curl_text(url: str, *, timeout: int = 45) -> str:
    result = run_bytes(
        [
            "curl",
            "-L",
            "--max-time",
            str(timeout),
            "-sS",
            "-A",
            MOBILE_UA,
            url,
        ],
        timeout=timeout + 5,
    )
    return decode_html(result.stdout)


def extract_first_url(text: str) -> str:
    urls = re.findall(r"https?://[^\s]+", text)
    if not urls:
        raise ValueError("No URL found in the provided share text.")
    return urls[0].rstrip("，。；,;")


def require_executable(name: str) -> None:
    if not shutil.which(name):
        raise RuntimeError(missing_executable_message(name))


def missing_executable_message(name: str) -> str:
    install_hint = ""
    if name == "ffmpeg":
        if sys.platform.startswith("win"):
            install_hint = "Install it with: winget install ffmpeg"
        elif sys.platform == "darwin":
            install_hint = "Install it with: brew install ffmpeg"
        elif sys.platform.startswith("linux"):
            install_hint = "Install it with: sudo apt install ffmpeg"

    message = f"Missing required executable: {name}. Install it and ensure it is available on PATH."
    if install_hint:
        message = f"{message}\n{install_hint}"
    return message


def find_ffmpeg() -> str:
    explicit = os.getenv("FFMPEG_BINARY") or os.getenv("IMAGEIO_FFMPEG_EXE")
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())

    found = shutil.which("ffmpeg")
    if found:
        candidates.append(Path(found))

    if sys.platform == "win32":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        program_files = [os.getenv("ProgramFiles", ""), os.getenv("ProgramFiles(x86)", "")]
        search_roots = [Path(path) for path in [local_app_data, *program_files] if path]
        for root in search_roots:
            candidates.extend(root.glob("JianyingPro/Apps/*/ffmpeg.exe"))
        for root in program_files:
            if root:
                candidates.extend(Path(root).glob("Kingsoft/WOA/resources/ffmpeg/ffmpeg.exe"))

    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            probe = subprocess.run(
                [str(candidate), "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0:
            return str(candidate)

    raise RuntimeError(f"{missing_executable_message('ffmpeg')}\nYou can also set FFMPEG_BINARY to an explicit executable path.")


def parse_router_data(html: str) -> dict[str, Any]:
    match = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", html, re.S)
    if not match:
        raise ValueError("Could not find window._ROUTER_DATA in Douyin share page.")
    return json.loads(match.group(1).strip())


def parse_video_info(share_text: str) -> dict[str, Any]:
    html = curl_text(extract_first_url(share_text))
    data = parse_router_data(html)
    loader_data = data["loaderData"]
    page_key = "video_(id)/page" if "video_(id)/page" in loader_data else "note_(id)/page"
    item = loader_data[page_key]["videoInfoRes"]["item_list"][0]

    video_id = item.get("aweme_id") or item.get("awemeId") or ""
    if not video_id:
        video_id = item["video"]["play_addr"]["uri"]
    title = re.sub(r'[\\/:*?"<>|]', "_", (item.get("desc") or f"douyin_{video_id}").strip())
    download_url = item["video"]["play_addr"]["url_list"][0].replace("playwm", "play")
    return {
        "video_id": video_id,
        "title": title,
        "download_url": download_url,
        "duration_ms": item.get("video", {}).get("duration"),
    }


def http_request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, timeout: int = 60):
    request = urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": MOBILE_UA,
            "Referer": "https://www.douyin.com/",
            **(headers or {}),
        },
    )
    return urllib.request.urlopen(request, timeout=timeout)


def get_download_info(download_url: str) -> tuple[str, int | None, bool]:
    try:
        with http_request(download_url, method="HEAD", timeout=45) as response:
            length = response.headers.get("Content-Length")
            accept_ranges = response.headers.get("Accept-Ranges", "").lower()
            return response.geturl(), int(length) if length else None, "bytes" in accept_ranges
    except (urllib.error.URLError, TimeoutError, ValueError):
        with http_request(download_url, method="GET", headers={"Range": "bytes=0-0"}, timeout=45) as response:
            content_range = response.headers.get("Content-Range", "")
            match = re.search(r"/(\d+)$", content_range)
            length = int(match.group(1)) if match else None
            return response.geturl(), length, response.status == 206


def download_byte_range(url: str, start: int, end: int, *, attempts: int = 8) -> bytes:
    expected = end - start + 1
    headers = {"Range": f"bytes={start}-{end}"}
    for attempt in range(attempts):
        try:
            with http_request(url, headers=headers, timeout=90) as response:
                data = response.read()
                if response.status != 206:
                    raise RuntimeError(f"Range request returned HTTP {response.status}")
                if len(data) != expected:
                    raise RuntimeError(f"Range request returned {len(data)} bytes, expected {expected}")
                return data
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(min(10, 1 + attempt))
    raise RuntimeError("unreachable")


def download_stream(url: str, output_path: Path, expected_size: int | None) -> None:
    with http_request(url, timeout=300) as response, output_path.open("wb") as file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            file.write(chunk)

    if expected_size is not None and output_path.stat().st_size != expected_size:
        raise RuntimeError(
            f"Downloaded incomplete video: {output_path.stat().st_size} bytes, expected {expected_size} bytes."
        )


def download_video(download_url: str, output_path: Path) -> None:
    final_url, expected_size, supports_ranges = get_download_info(download_url)
    if not expected_size or not supports_ranges:
        download_stream(final_url, output_path, expected_size)
        return

    chunk_size = int(os.getenv("DOUYIN_DOWNLOAD_CHUNK_BYTES", str(1024 * 1024)))
    with output_path.open("wb") as file:
        offset = 0
        while offset < expected_size:
            end = min(offset + chunk_size - 1, expected_size - 1)
            file.write(download_byte_range(final_url, offset, end))
            offset = end + 1

    actual_size = output_path.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError(f"Downloaded incomplete video: {actual_size} bytes, expected {expected_size} bytes.")


def extract_audio(video_path: Path, audio_path: Path) -> None:
    run(
        [
            FFMPEG_BIN,
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(audio_path),
        ],
        timeout=600,
    )


def transcribe_audio(audio_path: Path, *, language: str, device: str | None, sensevoice_repo: Path | None) -> str:
    from funasr import AutoModel
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    import torch

    if not device:
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda:0"
        else:
            device = "cpu"

    model_name = os.getenv("SENSEVOICE_MODEL", "iic/SenseVoiceSmall")
    model_kwargs: dict[str, Any] = {
        "model": model_name,
        "trust_remote_code": True,
        "vad_model": os.getenv("SENSEVOICE_VAD_MODEL", "fsmn-vad"),
        "vad_kwargs": {"max_single_segment_time": 30000},
        "device": device,
        "disable_update": True,
    }
    if sensevoice_repo and (sensevoice_repo / "model.py").exists():
        model_kwargs["remote_code"] = str(sensevoice_repo / "model.py")

    model = AutoModel(**model_kwargs)
    result = model.generate(
        input=str(audio_path),
        cache={},
        language=language,
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
        ban_emo_unk=False,
    )

    chunks: list[str] = []
    for item in result:
        if isinstance(item, list):
            chunks.extend(str(piece.get("text", "")) for piece in item)
        else:
            chunks.append(str(item.get("text", "")))

    text = "".join(rich_transcription_postprocess(chunk) for chunk in chunks)
    return text.replace("🎼", "").strip()


def default_output_root() -> Path:
    return Path.home() / "Downloads" / "douyin-transcripts"


def ensure_asr_python() -> None:
    if importlib.util.find_spec("funasr") and importlib.util.find_spec("torch"):
        return

    candidate = os.getenv("SENSEVOICE_PYTHON", "")
    if candidate:
        path = Path(candidate).expanduser()
        if path.exists() and path.resolve() != Path(sys.executable).resolve():
            probe = subprocess.run(
                [
                    str(path),
                    "-c",
                    "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('funasr') and importlib.util.find_spec('torch') else 1)",
                ]
            )
            if probe.returncode == 0:
                os.execv(str(path), [str(path), *sys.argv])

    raise RuntimeError(
        "No Python environment with funasr and torch found. "
        "Install dependencies in the current Python or set SENSEVOICE_PYTHON to a Python executable that has them."
    )


def main() -> int:
    require_executable("curl")
    global FFMPEG_BIN
    FFMPEG_BIN = find_ffmpeg()
    ensure_asr_python()

    parser = argparse.ArgumentParser(description="Transcribe a Douyin share link with local SenseVoice.")
    parser.add_argument("--share-text", required=True, help="Douyin share text or URL.")
    parser.add_argument("--output-root", default=str(default_output_root()), help="Directory for transcript artifacts.")
    parser.add_argument("--language", default="zh", help='SenseVoice language, e.g. "zh" or "auto".')
    parser.add_argument("--device", default=os.getenv("SENSEVOICE_DEVICE", ""), help="Device override: mps, cuda:0, cpu.")
    parser.add_argument(
        "--sensevoice-repo",
        default=os.getenv("SENSEVOICE_REPO", ""),
        help="Optional local SenseVoice repo containing model.py for remote_code.",
    )
    parser.add_argument("--keep-media", action="store_true", help="Keep downloaded video and extracted audio.")
    args = parser.parse_args()

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    work_dir = Path(tempfile.mkdtemp(prefix="douyin-media-"))
    video_path = work_dir / "video.mp4"
    audio_path = work_dir / "audio.wav"

    try:
        info = parse_video_info(args.share_text)
        transcript_dir = output_root / info["video_id"]
        transcript_dir.mkdir(parents=True, exist_ok=True)

        info_path = transcript_dir / "metadata.json"
        raw_path = transcript_dir / "transcript.raw.md"

        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        download_video(info["download_url"], video_path)
        extract_audio(video_path, audio_path)
        transcript = transcribe_audio(
            audio_path,
            language=args.language,
            device=args.device or None,
            sensevoice_repo=Path(args.sensevoice_repo).expanduser() if args.sensevoice_repo else None,
        )
        raw_path.write_text(f"# {info['title']}\n\n{transcript}\n", encoding="utf-8")

        print(json.dumps({"metadata": str(info_path), "raw_transcript": str(raw_path)}, ensure_ascii=False, indent=2))
        return 0
    finally:
        if not args.keep_media:
            for path in (video_path, audio_path):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            try:
                work_dir.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
