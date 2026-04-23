"""Command-line entry point for the YouTube audio downloader."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .downloader import DEFAULT_OUT_DIR, DownloaderError, download_audio


# Matches a YouTube watch / youtu.be / playlist URL anywhere in a line.
_URL_RE = re.compile(
    r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com/\S+|youtu\.be/\S+)",
    re.IGNORECASE,
)


def parse_batch_file(path: Path) -> list[str]:
    """Extract YouTube URLs from a free-form text file.

    - One URL per line; the rest of the line (title, dash, etc.) is ignored.
    - Blank lines, lines starting with `#`, and lines without a URL are skipped.
    - Order is preserved; duplicates are kept.
    """
    if not path.exists():
        raise DownloaderError(f"Batch file not found: {path}")
    urls: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _URL_RE.search(line)
        if m:
            urls.append(m.group(0).rstrip(".,);]"))
    return urls


def parse_song_file(path: Path) -> list[str]:
    """Read song-name lines for `--search`.

    Each non-blank, non-`#` line is treated as a search query. Free-form OK
    (e.g. "Dynamite - BTS", "BTS Dynamite", "TOMBOY (G)I-DLE").
    Lines that already contain a YouTube URL are skipped (assumed resolved).
    """
    if not path.exists():
        raise DownloaderError(f"Song list file not found: {path}")
    queries: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if _URL_RE.search(line):
            continue
        queries.append(line)
    return queries


def resolve_songs(queries: list[str]) -> list[tuple[str, str | None, str | None]]:
    """For each query, ask yt-dlp's search for the top result.

    Returns list of (query, video_id, yt_title). video_id is None on failure.
    """
    from yt_dlp import YoutubeDL

    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "default_search": "ytsearch1",
    }
    out: list[tuple[str, str | None, str | None]] = []
    with YoutubeDL(opts) as ydl:
        for q in queries:
            try:
                info = ydl.extract_info(f"{q} official", download=False)
                entry = info["entries"][0] if "entries" in info else info
                out.append((q, entry["id"], entry.get("title")))
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL  {q}: {e}", file=sys.stderr)
                out.append((q, None, None))
    return out


HELP_EPILOG = f"""\
EXAMPLES
  Download with all defaults (192kbps M4A into {DEFAULT_OUT_DIR}):
      ydl "https://www.youtube.com/watch?v=VIDEO_ID"

  No URL given -> reads URL from clipboard:
      ydl

  High quality MP3:
      ydl "https://youtu.be/VIDEO_ID" --quality 320 --format mp3

  Save somewhere else:
      ydl "https://youtu.be/VIDEO_ID" --out "D:/music"

  Best available quality (no re-encoding loss):
      ydl "https://youtu.be/VIDEO_ID" --quality highest

  Download a whole playlist (each track as a separate file in a sub-folder):
      ydl "https://www.youtube.com/playlist?list=PLxxxxx" --playlist

  Batch download: read URLs from a text file (one per line, free-form OK):
      ydl --batch my_songs.txt
      ydl --batch my_songs.txt --quality 192

  Resolve a list of song NAMES to YouTube URLs (no download). Writes
  '<input>.urls.txt' next to the input and prints a YouTube playlist URL
  that opens all matches in your browser:
      ydl --search names.txt
      # then either:
      ydl --batch names.urls.txt          # download all as audio, or
      # open the printed watch_videos URL and click Save -> Create playlist

OPTIONS
  url                    The YouTube video URL. Can be a full watch URL,
                         a youtu.be short link, or a URL with extra params
                         (?list=..., &t=...). Quote it to avoid shell issues.
                         Omit when using --batch.
  --quality {{64,128,192,256,320,highest}}
                         Target audio bitrate in kbps. 'highest' keeps the
                         best stream YouTube offers (no re-encoding).
                         Default: 192 (good size/quality balance for music).
  --format  {{m4a,mp3,ogg}}
                         Output container/codec. M4A is recommended (YouTube
                         serves AAC natively, so M4A = no transcoding loss
                         and native iOS/Mac support). Use MP3 for max
                         device compatibility. Default: m4a.
  --out PATH             Folder to save into. Created if missing.
                         Default: {DEFAULT_OUT_DIR}
  --playlist             Download every video in the playlist (when the URL
                         contains &list=...). Files go into a sub-folder
                         named after the playlist, prefixed with track number.
                         Without this flag, only the single ?v= video is
                         downloaded.
  --batch FILE           Read URLs from FILE (one per line). Free-form lines
                         are OK -- anything that contains a YouTube URL is
                         picked up; titles, dashes, blank lines, and lines
                         starting with `#` are ignored. Failures do NOT stop
                         the batch; a summary of failures prints at the end.
  --search FILE          Resolve song NAMES (not URLs) in FILE to YouTube URLs
                         using yt-dlp's search. One song per line, free-form
                         ("Dynamite - BTS", "BTS Dynamite", etc.). Writes the
                         resolved URLs to '<input>.urls.txt' and prints a
                         YouTube playlist URL containing all matches (max 50,
                         YouTube limit). Does NOT download.
  --no-rename            Keep yt-dlp's original filename. By default, files
                         are renamed to '<Artist> - <Title>.<ext>' (e.g.
                         "(여자)아이들((G)I-DLE) - 'Allergy' Official
                         Music Video.m4a" -> "(G)I-DLE - Allergy.m4a").
  --no-tags              Skip embedding metadata (title, artist, album, year)
                         and the YouTube thumbnail as cover art into the file.
  -h, --help             Show this help and exit.

NOTES
  - Requires ffmpeg on PATH (winget install Gyan.FFmpeg).
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ydl",
        description="Download a YouTube video's audio track. Defaults to 192kbps M4A.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "url",
        nargs="?",
        help="YouTube video URL (quote it). Omit when using --batch.",
    )
    p.add_argument(
        "--quality",
        default="192",
        choices=["64", "128", "192", "256", "320", "highest"],
        help="Audio bitrate in kbps (default: 192)",
    )
    p.add_argument(
        "--format",
        dest="fmt",
        default="m4a",
        choices=["m4a", "mp3", "ogg"],
        help="Output audio format (default: m4a)",
    )
    p.add_argument(
        "--out",
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    p.add_argument(
        "--playlist",
        action="store_true",
        help="Download every video in the playlist (URL must contain &list=...)",
    )
    p.add_argument(
        "--batch",
        metavar="FILE",
        help="Read URLs from a text file (one per line; free-form lines OK)",
    )
    p.add_argument(
        "--search",
        metavar="FILE",
        help="Resolve song NAMES (not URLs) in FILE to YouTube URLs (no download)",
    )
    p.add_argument(
        "--no-rename",
        dest="rename",
        action="store_false",
        help="Keep yt-dlp's original filename (skip the 'Artist - Title' cleanup)",
    )
    p.add_argument(
        "--no-tags",
        dest="tags",
        action="store_false",
        help="Skip embedding metadata + cover art into the audio file",
    )
    return p


def _download_one(url: str, args: argparse.Namespace) -> tuple[bool, list, str]:
    """Download a single URL. Returns (ok, paths, error_message)."""
    try:
        paths = download_audio(
            url=url,
            quality=args.quality,
            fmt=args.fmt,
            out_dir=args.out,
            playlist=args.playlist,
            rename=args.rename,
            tags=args.tags,
        )
        return True, paths, ""
    except DownloaderError as e:
        return False, [], str(e)
    except Exception as e:  # noqa: BLE001 -- catch-all for batch resilience
        return False, [], f"{type(e).__name__}: {e}"


def _run_search(in_path: Path) -> int:
    """Resolve song names to YouTube URLs; write `<input>.urls.txt`; print playlist URL."""
    try:
        queries = parse_song_file(in_path)
    except DownloaderError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if not queries:
        print(f"Error: no song names found in {in_path}", file=sys.stderr)
        return 1

    print(f"Resolving {len(queries)} song(s) via YouTube search...")
    results = resolve_songs(queries)

    out_lines: list[str] = [f"# Resolved from {in_path.name}"]
    ids: list[str] = []
    failures: list[str] = []
    for query, vid, yt_title in results:
        if vid:
            url = f"https://www.youtube.com/watch?v={vid}"
            out_lines.append(f"{query} - {url}")
            ids.append(vid)
            print(f"  OK    {query[:40]:40s} -> {(yt_title or '')[:50]}")
        else:
            out_lines.append(f"# FAILED: {query}")
            failures.append(query)

    out_path = in_path.with_suffix(in_path.suffix + ".urls.txt") if in_path.suffix else in_path.with_name(in_path.name + ".urls.txt")
    # Cleaner: 'songs.txt' -> 'songs.urls.txt'
    if in_path.suffix == ".txt":
        out_path = in_path.with_name(in_path.stem + ".urls.txt")
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print(f"\nWrote {len(ids)} URL(s) to {out_path}" + (f"  ({len(failures)} failed)" if failures else ""))
    print(f"Next: ydl --batch \"{out_path}\"")

    if ids:
        # YouTube's anonymous-playlist endpoint accepts up to 50 ids.
        capped = ids[:50]
        playlist_url = "https://www.youtube.com/watch_videos?video_ids=" + ",".join(capped)
        extra = "" if len(ids) <= 50 else f"  (capped to first 50 of {len(ids)})"
        print(f"\nYouTube playlist URL{extra}:")
        print(f"  {playlist_url}")
        print("  Open it, then click Save -> + Create new playlist to save into your account.")

    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.search:
        return _run_search(Path(args.search))

    # Determine the URL list.
    if args.batch:
        try:
            urls = parse_batch_file(Path(args.batch))
        except DownloaderError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        if not urls:
            print(f"Error: no URLs found in {args.batch}", file=sys.stderr)
            return 1
        if args.url:
            urls.insert(0, args.url)  # allow mixing positional + batch
        print(f"Batch mode: {len(urls)} URL(s) from {args.batch}")
        print(f"  -> {args.fmt} @ {args.quality}kbps into {args.out}")
    else:
        if not args.url:
            print("Error: URL is required (or use --batch FILE).", file=sys.stderr)
            return 2
        urls = [args.url]
        mode = "playlist" if args.playlist else "single video"
        print(f"Downloading: {args.url}")
        print(f"  -> {args.fmt} @ {args.quality}kbps ({mode}) into {args.out}")

    # Single-URL fast path keeps the original output format.
    if len(urls) == 1 and not args.batch:
        ok, paths, err = _download_one(urls[0], args)
        if not ok:
            print(f"\nError: {err}", file=sys.stderr)
            return 1
        if len(paths) == 1:
            print(f"Saved: {paths[0]}")
        else:
            print(f"Saved {len(paths)} files:")
            for p in paths:
                print(f"  {p}")
        return 0

    # Batch loop with summary.
    successes: list[tuple[str, list]] = []
    failures: list[tuple[str, str]] = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] {url}")
        ok, paths, err = _download_one(url, args)
        if ok:
            for p in paths:
                print(f"  saved: {p.name}")
            successes.append((url, paths))
        else:
            print(f"  FAILED: {err}", file=sys.stderr)
            failures.append((url, err))

    # Summary.
    print("\n" + "=" * 60)
    print(f"Batch complete: {len(successes)} ok, {len(failures)} failed, {len(urls)} total")
    if failures:
        print("\nFailures:")
        for url, err in failures:
            print(f"  {url}")
            print(f"    -> {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
