"""Core YouTube audio/video download logic.

Wraps yt-dlp's Python API. Designed to be reusable from CLI, future GUI,
or AI-processing pipelines.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Callable, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


DEFAULT_OUT_DIR = r"C:/Users/Yoon/Music/0_temp"


class DownloaderError(Exception):
    """User-facing error from the downloader."""


def _default_progress(d: dict) -> None:
    status = d.get("status")
    if status == "downloading":
        pct = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("_eta_str", "").strip()
        sys.stdout.write(f"\r  downloading {pct}  {speed}  ETA {eta}   ")
        sys.stdout.flush()
    elif status == "finished":
        sys.stdout.write("\r  download complete, post-processing...           \n")
        sys.stdout.flush()


def _ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise DownloaderError(
            "ffmpeg not found on PATH. Install it (e.g. `winget install Gyan.FFmpeg`) "
            "and restart your terminal."
        )


def download_audio(
    url: str,
    quality: str = "128",
    fmt: str = "m4a",
    out_dir: str | Path = DEFAULT_OUT_DIR,
    progress_hook: Optional[Callable[[dict], None]] = None,
) -> Path:
    """Download a single YouTube URL as an audio file.

    Args:
        url: YouTube video URL.
        quality: Bitrate in kbps as string ("64", "128", "256", "320") or "highest".
        fmt: Output container/codec ("m4a", "mp3", "ogg").
        out_dir: Directory to save the file in.
        progress_hook: Optional yt-dlp progress hook callable.

    Returns:
        Path to the downloaded audio file.

    Raises:
        DownloaderError: If ffmpeg is missing or the download fails.
    """
    _ensure_ffmpeg()

    out_path = Path(out_dir).expanduser()
    out_path.mkdir(parents=True, exist_ok=True)

    preferred_quality = "0" if quality == "highest" else str(quality)

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(out_path / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "restrictfilenames": False,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt,
                "preferredquality": preferred_quality,
            }
        ],
        "progress_hooks": [progress_hook or _default_progress],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as e:
        raise DownloaderError(f"Download failed: {e}") from e

    # After post-processing, the final extension matches `fmt`.
    title = info.get("title", "audio")
    # Mirror yt-dlp's sanitization for the filename we report back.
    final = out_path / f"{ydl.prepare_filename(info, outtmpl='%(title)s')}.{fmt}"
    if not final.exists():
        # Fallback: search by title stem.
        matches = list(out_path.glob(f"*.{fmt}"))
        if matches:
            final = max(matches, key=lambda p: p.stat().st_mtime)
        else:
            raise DownloaderError(
                f"Download finished but output file not found in {out_path}"
            )
    return final
