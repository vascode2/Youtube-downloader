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
    playlist: bool = False,
) -> list[Path]:
    """Download a YouTube URL as audio file(s).

    Args:
        url: YouTube video or playlist URL.
        quality: Bitrate in kbps ("64", "128", "192", "256", "320") or "highest".
        fmt: Output container/codec ("m4a", "mp3", "ogg").
        out_dir: Directory to save into.
        progress_hook: Optional yt-dlp progress hook callable.
        playlist: If True, download every video in the playlist as a separate
            file (into `out_dir/<playlist title>/`). If False (default), only
            the single video pointed to by `?v=` is downloaded, even if the URL
            also contains `&list=`.

    Returns:
        List of paths to the downloaded audio file(s). Single-element list
        when `playlist=False`.

    Raises:
        DownloaderError: If ffmpeg is missing or the download fails.
    """
    _ensure_ffmpeg()

    out_path = Path(out_dir).expanduser()
    out_path.mkdir(parents=True, exist_ok=True)

    preferred_quality = "0" if quality == "highest" else str(quality)

    if playlist:
        outtmpl = str(out_path / "%(playlist_title)s" / "%(playlist_index)03d - %(title)s.%(ext)s")
    else:
        outtmpl = str(out_path / "%(title)s.%(ext)s")

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": not playlist,
        "ignoreerrors": playlist,  # don't abort whole playlist on one bad video
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

    # Collect entries (playlist) or wrap single video info as a one-item list.
    entries = info.get("entries") if info and "entries" in info else [info]
    entries = [e for e in entries if e]  # drop None from skipped/private videos

    results: list[Path] = []
    for entry in entries:
        # Reconstruct the post-processed filename (extension changed to `fmt`).
        pre = Path(ydl.prepare_filename(entry))
        final = pre.with_suffix(f".{fmt}")
        if not final.exists():
            # Fallback: most recent file of `fmt` in the parent dir.
            matches = list(final.parent.glob(f"*.{fmt}"))
            if matches:
                final = max(matches, key=lambda p: p.stat().st_mtime)
        if final.exists():
            results.append(final)

    if not results:
        raise DownloaderError(
            f"Download finished but no output files found in {out_path}"
        )
    return results
