"""Command-line entry point for the YouTube audio downloader."""

from __future__ import annotations

import argparse
import sys

from .downloader import DEFAULT_OUT_DIR, DownloaderError, download_audio


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ydl",
        description="Download YouTube audio (v1: audio-only, defaults to 128kbps M4A).",
    )
    p.add_argument("url", help="YouTube video URL")
    p.add_argument(
        "--quality",
        default="128",
        choices=["64", "128", "256", "320", "highest"],
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"Downloading: {args.url}")
    print(f"  -> {args.fmt} @ {args.quality}kbps into {args.out}")
    try:
        path = download_audio(
            url=args.url,
            quality=args.quality,
            fmt=args.fmt,
            out_dir=args.out,
        )
    except DownloaderError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    print(f"Saved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
