"""Command-line entry point for the YouTube audio downloader."""

from __future__ import annotations

import argparse
import sys

from .downloader import DEFAULT_OUT_DIR, DownloaderError, download_audio


HELP_EPILOG = f"""\
EXAMPLES
  Download with all defaults (128kbps M4A into {DEFAULT_OUT_DIR}):
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

OPTIONS
  url                    The YouTube video URL. Can be a full watch URL,
                         a youtu.be short link, or a URL with extra params
                         (?list=..., &t=...). Quote it to avoid shell issues.
  --quality {{64,128,192,256,320,highest}}
                         Target audio bitrate in kbps. 'highest' keeps the
                         best stream YouTube offers (no re-encoding).
                         Default: 128 (good size/quality balance for music).
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
  -h, --help             Show this help and exit.

NOTES
  - Requires ffmpeg on PATH (winget install Gyan.FFmpeg).
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ydl",
        description="Download a YouTube video's audio track. Defaults to 128kbps M4A.",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("url", help="YouTube video URL (quote it)")
    p.add_argument(
        "--quality",
        default="128",
        choices=["64", "128", "192", "256", "320", "highest"],
        help="Audio bitrate in kbps (default: 128)",
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"Downloading: {args.url}")
    mode = "playlist" if args.playlist else "single video"
    print(f"  -> {args.fmt} @ {args.quality}kbps ({mode}) into {args.out}")
    try:
        paths = download_audio(
            url=args.url,
            quality=args.quality,
            fmt=args.fmt,
            out_dir=args.out,
            playlist=args.playlist,
        )
    except DownloaderError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    if len(paths) == 1:
        print(f"Saved: {paths[0]}")
    else:
        print(f"Saved {len(paths)} files:")
        for p in paths:
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
