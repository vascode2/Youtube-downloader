# AGENTS.md

Python CLI + desktop GUI wrapping `yt-dlp` + `ffmpeg` to download YouTube audio. Defaults to 192 kbps M4A. See [README.md](README.md) for user-facing usage and [CLAUDE.md](CLAUDE.md) for design decisions / gotchas.

## Architecture

- [src/downloader.py](src/downloader.py) — pure core. `download_audio(url, quality, fmt, out_dir, progress_hook)` calls `yt_dlp.YoutubeDL` programmatically. **No CLI/UI concerns here** — reused by both the CLI and the GUI.
- [src/cli.py](src/cli.py) — `argparse` wrapper only. Run via `python -m src.cli`.
- [src/gui.py](src/gui.py) — PySide6 desktop GUI. `Worker` runs on a `QThread`; progress is piped via Qt signals. Launch via `ydlg.bat` (no console window) or `python -m src.gui`.
- ffmpeg is an **external dependency** (not bundled). `_ensure_ffmpeg()` checks `shutil.which("ffmpeg")` and raises `DownloaderError` with install hint.

## Conventions

- Keep `downloader.py` framework-agnostic. Anything that prints or parses argv belongs in `cli.py`; anything that talks to a UI belongs in `gui.py`.
- Surface user-actionable errors as `DownloaderError`. Let unexpected errors bubble up.
- Default output path lives in `DEFAULT_OUT_DIR` constant (`C:/Users/Yoon/Music/0_temp`) — change in one place.
- Use `yt-dlp`, never `pytube` (pytube breaks whenever YouTube changes).

## Build / run / test

```powershell
pip install -r requirements.txt
python -m src.cli "<youtube-url>"                                  # default: 192k m4a
python -m src.cli "<url>" --quality 320 --format mp3 --out "D:/x"  # overrides
python -m src.cli --batch songs.txt                                # many URLs from file
.\Install.bat                                                      # one-time: register `ydl` PowerShell function
ydl                                                                # quick mode: URL from clipboard
ydl "<url>"                                                        # quick mode: explicit URL
ydl --help                                                         # full help with examples
.\ydlg.bat                                                         # launch desktop GUI (no console window)
python -m src.gui                                                  # alternative GUI launch (console stays open)
```

`ydl` is registered as a **PowerShell function** in the user's `$PROFILE` (via `Install.bat` → `Install.ps1`), which calls `_ydl.ps1`. The function approach (vs a `.bat` in PATH) keeps the call in-process and avoids PowerShell 5.1's bug where `&` in quoted args leaks to cmd.exe. `ydl.bat` is kept as a fallback for cmd.exe / File Explorer shortcuts. The `.ps1` is named `_ydl.ps1` (underscore prefix) so PowerShell does NOT resolve the bare name `ydl` to it directly — only the function (or the `.bat`) matches.

No automated tests yet. Smoke-test with the 19-second public-domain video `https://www.youtube.com/watch?v=jNQXAC9IVRw` ("Me at the zoo") into `./test_out` (gitignored).

## Roadmap (do not implement unprompted)

Video downloads, device presets (`--for ios|android|...`), AI post-processing (Demucs / UVR for vocal removal etc.). All should reuse `download_audio()` (or its sibling `download_video()` once added) — do not duplicate yt-dlp option-building.
