"""Core YouTube audio/video download logic.

Wraps yt-dlp's Python API. Designed to be reusable from CLI, future GUI,
or AI-processing pipelines.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from typing import Callable, Optional

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


DEFAULT_OUT_DIR = r"C:/Users/Yoon/Music/0_temp"

# Characters Windows forbids in filenames.
_FORBIDDEN = '<>:"/\\|?*'


def _safe_filename(name: str) -> str:
    """Replace forbidden Windows filename characters with similar-looking ones."""
    table = str.maketrans({
        "<": "‹", ">": "›", ":": "꞉", '"': "ʺ",
        "/": "⁄", "\\": "⧹", "|": "ǀ", "?": "？", "*": "＊",
    })
    return name.translate(table)


class DownloaderError(Exception):
    """User-facing error from the downloader."""


# Trailing noise patterns commonly stuck on YouTube music video titles.
# Stripped repeatedly until stable so combined suffixes (e.g. "[MV] ... Official Video")
# all come off.
_NOISE_SUFFIX_RE = re.compile(
    r"\s*[\(\[]?\s*"
    r"(?:official\s+)?"
    r"(music\s*video|music\s*audio|lyric\s*video|lyrics?|"
    r"performance\s*video|visualizer|audio|video|m\s*/?\s*v|mv)"
    r"\s*[\)\]]?\s*$",
    re.IGNORECASE,
)
_QUOTE_RE = re.compile(r"^['\"\u2018\u2019\u201c\u201d](.+?)['\"\u2018\u2019\u201c\u201d]$")
_SPLIT_RE = re.compile(r"\s+[-\u2013\u2014]\s+")  # ' - ', ' – ', ' — '


def _latin_count(s: str) -> int:
    return sum(1 for c in s if c.isascii() and c.isalpha())


def _pick_artist_alias(artist: str) -> str:
    """Given a messy artist field with possibly nested parens and mixed scripts,
    pick the variant with the most Latin letters (usually the romanized name).

    Examples:
        '(여자)아이들((G)I-DLE)' -> '(G)I-DLE'
        'BTS (방탄소년단)'        -> 'BTS'
        'Coldplay'                  -> 'Coldplay'
    """
    candidates: list[str] = []
    depth = 0
    start = -1
    for i, c in enumerate(artist):
        if c == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif c == ")" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(artist[start:i].strip())
                start = -1
    # Bare text outside any parens.
    bare = re.sub(r"\([^()]*(?:\([^()]*\)[^()]*)*\)", "", artist).strip()
    if bare:
        candidates.append(bare)
    if not candidates:
        return artist.strip()
    best = max(candidates, key=_latin_count)
    if _latin_count(best) >= 2:
        return best.strip()
    return artist.strip()


def _clean_title(raw: str) -> str:
    """Convert a YouTube video title to '<Artist> - <Title>' best-effort.

    Returns the cleaned form, or the stripped original if it can't be parsed.
    Pure / no I/O / safe to unit-test.
    """
    s = raw.strip()
    # Repeatedly strip trailing noise ("... Official Music Video", "[MV]", etc.)
    for _ in range(4):
        new = _NOISE_SUFFIX_RE.sub("", s).strip().rstrip("-–— ").strip()
        if new == s or not new:
            break
        s = new

    parts = _SPLIT_RE.split(s, maxsplit=1)
    if len(parts) == 2:
        artist_raw, title_raw = parts[0].strip(), parts[1].strip()
    else:
        # Fallback: pattern "Artist 'Title'" with no dash (common on K-pop MVs).
        m = re.match(
            r"^(.+?)\s+['\"\u2018\u201c](.+?)['\"\u2019\u201d]\s*$", s
        )
        if not m:
            return s
        artist_raw, title_raw = m.group(1).strip(), m.group(2).strip()

    # Title: unwrap surrounding quotes if present.
    qm = _QUOTE_RE.match(title_raw)
    if qm:
        title_raw = qm.group(1).strip()

    artist = _pick_artist_alias(artist_raw)
    if not artist or not title_raw:
        return s
    return f"{artist} - {title_raw}"

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
    rename: bool = True,
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
        rename: If True (default), clean the YouTube title into
            '<Artist> - <Title>.<ext>' after download (best-effort heuristic;
            falls back to the original if parsing fails or the target name
            collides). Pass False to keep yt-dlp's filename verbatim.

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
        # `(playlist_title|...)s` is yt-dlp's fallback syntax — used if the
        # playlist title can't be fetched (e.g. private playlist).
        outtmpl = str(
            out_path
            / "%(playlist_title,playlist|_no_playlist)s"
            / "%(playlist_index)03d - %(title)s.%(ext)s"
        )
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

    # Detect: playlist was requested but yt-dlp couldn't enumerate it
    # (private playlist, unlisted with no auth, etc.) and fell back to a single
    # video download. In that case the file landed in `_no_playlist/NA - ....`
    # — move it back up to `out_path` and warn.
    playlist_inaccessible = (
        playlist
        and info is not None
        and "entries" not in info  # not actually treated as a playlist by yt-dlp
    )

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

        if playlist_inaccessible and final.exists():
            # Strip the "NA - " (or "001 - ") index prefix and move out of the
            # `_no_playlist` sub-folder so the result is just `<title>.<ext>`.
            clean_name = entry.get("title", final.stem) + f".{fmt}"
            target = out_path / _safe_filename(clean_name)
            try:
                final.replace(target)
                # Remove the now-empty fallback folder.
                if final.parent.exists() and not any(final.parent.iterdir()):
                    final.parent.rmdir()
                final = target
            except OSError:
                pass  # if move fails, just keep the file where it is

        if final.exists():
            if rename:
                cleaned = _clean_title(entry.get("title", final.stem))
                # Preserve the playlist track-number prefix (e.g. "001 - ").
                idx_match = re.match(r"^(\d{2,4})\s*-\s*", final.stem)
                if idx_match:
                    cleaned = f"{idx_match.group(1)} - {cleaned}"
                target = final.with_name(_safe_filename(cleaned) + final.suffix)
                if target != final and not target.exists():
                    try:
                        final.replace(target)
                        final = target
                    except OSError:
                        pass  # keep yt-dlp name on any rename failure
            results.append(final)

    if not results:
        raise DownloaderError(
            f"Download finished but no output files found in {out_path}"
        )

    if playlist_inaccessible:
        print(
            "\nNote: --playlist was given but the playlist could not be "
            "enumerated (likely private). Downloaded only the single ?v= "
            "video. To fix: set the playlist visibility to Unlisted or Public "
            "on YouTube.",
            file=sys.stderr,
        )

    return results
