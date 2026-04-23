# YouTube Downloader (v1)

Minimal Python CLI to download YouTube audio. v1 scope: audio-only, defaults to **128 kbps M4A** saved to `C:/Users/Yoon/Music/0_temp`.

## Prerequisites

- Python 3.9+
- `ffmpeg` on PATH. On Windows: `winget install Gyan.FFmpeg` (then restart your terminal).

## Install

```powershell
pip install -r requirements.txt
```

## Usage

```powershell
# Default: 128k m4a into C:/Users/Yoon/Music/0_temp
python -m src.cli "https://www.youtube.com/watch?v=VIDEO_ID"

# Override quality / format / output folder
python -m src.cli "https://www.youtube.com/watch?v=VIDEO_ID" --quality 320 --format mp3 --out "D:/music"
```

### Quick mode (recommended) — `ydl`

**One-time install** (registers `ydl` as a PowerShell function in your `$PROFILE`):

```powershell
.\Install.bat
```

Then open a **new** PowerShell window and use it from anywhere:

```powershell
ydl --help                                       # show full help with examples
ydl "https://www.youtube.com/watch?v=VIDEO_ID"   # explicit URL
ydl                                              # downloads URL from clipboard
ydl --quality 320 --format mp3                   # clipboard URL + overrides
```

**Fastest workflow**: copy the YouTube URL in your browser → run `ydl` → done.

**Why a function and not just a `.bat`?** PowerShell 5.1 mangles `&` in quoted args when launching `.bat` files — a YouTube URL with `&list=...` would leak to cmd.exe and produce errors. The function call stays in-process and handles it cleanly.

The installer also sets your user-scope execution policy to `RemoteSigned` (Microsoft's recommended setting; allows local scripts, requires signed scripts from internet). If you'd rather keep the policy stricter, you can still invoke `ydl.bat` directly — it works for URLs without `&`.

### Options

| Flag | Choices | Default |
|------|---------|---------|
| `--quality` | `64`, `128`, `192`, `256`, `320`, `highest` | `128` |
| `--format` | `m4a`, `mp3`, `ogg` | `m4a` |
| `--out` | any folder path | `C:/Users/Yoon/Music/0_temp` |
| `--playlist` | (flag, no value) | off — downloads only the single `?v=` video |

### Playlist downloads

If the URL contains `&list=...` (or is a `playlist?list=...` URL), pass `--playlist` to download every video as its own audio file. Files land in a sub-folder named after the playlist, prefixed with track number:

```powershell
ydl "https://www.youtube.com/playlist?list=PLxxxxxxx" --playlist
# -> C:/Users/Yoon/Music/0_temp/<Playlist Title>/001 - <Track 1>.m4a
#    C:/Users/Yoon/Music/0_temp/<Playlist Title>/002 - <Track 2>.m4a
#    ...
```

Without `--playlist`, even a URL like `?v=ID&list=...` only downloads the single `?v=` video (this is the safer default — one click != accidentally downloading a 200-track playlist).

## Project layout

```
src/
  downloader.py   # core download_audio() — reusable from GUI / web / AI pipelines
  cli.py          # argparse wrapper
requirements.txt
```

## Roadmap / TODO

Features (implement on demand — use the `/add-feature` prompt to keep changes consistent):

- [ ] **Video downloads** — `--video` flag, mp4 container, `bestvideo+bestaudio` format
- [ ] **Quality presets** — `highest | 320 | 256 | 128 | 64` for both audio and video
- [ ] **Device presets** — `--for ios|android|windows|mac|linux|m4a|mp3|ogg` mapping to `(fmt, quality)` pairs
- [ ] **Playlist / channel batch** — ~~drop `noplaylist=True`, add `--playlist` flag~~ ✅ done
- [ ] **Desktop GUI** — PySide6 window (paste link, dropdowns, progress bar) reusing `download_audio()` on a `QThread`
- [ ] **AI post-processing** — vocal removal, voice extraction, denoise, instrument isolation, loudness balance, audio upscale (Demucs + Resemble Enhance + pyloudnorm). See [.copilot/skills/ai-postprocess/SKILL.md](.copilot/skills/ai-postprocess/SKILL.md) for the build plan.
- [ ] **Pip-install global command** — `pip install -e .` exposing a `ydl` console script

Agent / workflow customization (inspired by [roboco.io: Everything Claude Code distilled](https://roboco.io/posts/everything-claude-code-distilled/)):

- [x] **Agent instructions** — [AGENTS.md](AGENTS.md) (architecture) + [CLAUDE.md](CLAUDE.md) (gotchas, decisions)
- [x] **Slash command** — [`.github/prompts/add-feature.prompt.md`](.github/prompts/add-feature.prompt.md) for safe feature additions
- [x] **Skill** — [`.copilot/skills/ai-postprocess/SKILL.md`](.copilot/skills/ai-postprocess/SKILL.md) for the AI processing roadmap item
- [ ] **Subagents** — defer until the codebase grows (current scope too small to benefit from a `code-reviewer` / `tdd-guide` split)
- [ ] **Hooks** — defer until there's a real footgun to guard (e.g., pre-commit hook to block accidental `test_out/` commits — currently handled by `.gitignore`)
- [ ] **Tests** — add `pytest` smoke test that mocks yt-dlp; only after a second feature lands
