# YouTube Downloader (v1)

Minimal Python CLI to download YouTube audio. v1 scope: audio-only, defaults to **192 kbps M4A** saved to `C:/Users/Yoon/Music/0_temp`.

## Prerequisites

- Python 3.9+
- `ffmpeg` on PATH. On Windows: `winget install Gyan.FFmpeg` (then restart your terminal).

## Install

```powershell
pip install -r requirements.txt
```

## Usage

```powershell
# Default: 192k m4a into C:/Users/Yoon/Music/0_temp
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
| `--quality` | `64`, `128`, `192`, `256`, `320`, `highest` | `192` |
| `--format` | `m4a`, `mp3`, `ogg` | `m4a` |
| `--out` | any folder path | `C:/Users/Yoon/Music/0_temp` |
| `--playlist` | (flag, no value) | off — downloads only the single `?v=` video |
| `--batch FILE` | path to text file | off |
| `--search FILE` | path to text file (song names) | off |
| `--download` | (flag, no value) | off — with `--search`, also downloads every resolved URL |
| `--no-rename` | (flag, no value) | off — default cleans titles to `<Artist> - <Title>` |
| `--no-tags` | (flag, no value) | off — default embeds Title/Artist/Year + cover art |

### Playlist downloads

If the URL contains `&list=...` (or is a `playlist?list=...` URL), pass `--playlist` to download every video as its own audio file. Files land in a sub-folder named after the playlist:

```powershell
ydl "https://www.youtube.com/playlist?list=PLxxxxxxx" --playlist
# -> C:/Users/Yoon/Music/0_temp/<Playlist Title>/<Artist> - <Track 1>.m4a
#    C:/Users/Yoon/Music/0_temp/<Playlist Title>/<Artist> - <Track 2>.m4a
#    ...
```

Without `--playlist`, even a URL like `?v=ID&list=...` only downloads the single `?v=` video (this is the safer default — one click != accidentally downloading a 200-track playlist).

### Auto-rename to `<Artist> - <Title>`

By default, downloaded files are renamed from YouTube's verbose titles to a clean `<Artist> - <Title>.<ext>` form. Examples:

| YouTube title | Saved as |
|---|---|
| `(여자)아이들((G)I-DLE) - 'Allergy' Official Music Video` | `(G)I-DLE - Allergy.m4a` |
| `BTS (방탄소년단) 'Dynamite' Official MV` | `BTS - Dynamite.m4a` |
| `Coldplay - Yellow (Official Video)` | `Coldplay - Yellow.m4a` |

The heuristic strips trailing noise (`Official Music Video`, `[MV]`, `(Audio)`, ...), unwraps quoted titles, and — when the artist is in mixed scripts — prefers the romanized variant inside parens. If the title doesn't fit a known pattern, the original name is kept.

Pass `--no-rename` to skip cleanup and keep yt-dlp's filename verbatim.

### Embedded metadata + cover art (tags)

By default, downloaded files get the following tags written (visible in Windows Explorer's *Details* tab, iTunes, foobar2000, etc.):

- **Title** — the parsed song title (e.g. `TOMBOY`)
- **Artist** — the parsed artist (e.g. `(G)I-DLE`)
- **Year** — from YouTube's upload date
- **Track #** — when downloading via `--playlist`
- **Cover art** — the YouTube thumbnail

Uses [mutagen](https://mutagen.readthedocs.io/) to write only the fields that matter, so the file isn't polluted with the full video description (lyrics, promo links). Pass `--no-tags` to skip tagging entirely.

### Batch downloads (many URLs from a file)

For large lists, put URLs in a text file and pass `--batch`:

```powershell
ydl --batch songs.txt                  # default 192k m4a
ydl --batch songs.txt --quality 192    # any other flag applies to all
```

**File format** — one URL per line, free-form lines OK. Anything containing a YouTube URL is picked up; titles, dashes, blank lines, and lines starting with `#` are ignored. Your own list works as-is:

```
# K-Pop Collection
Dynamite (BTS) – https://www.youtube.com/watch?v=gdZLi9oWNZg
My Universe (Coldplay x BTS) – https://www.youtube.com/watch?v=bO9O2L2wW3Y
I AM (IVE) – https://www.youtube.com/watch?v=6ZUIwj3FgUY
...
```

**Behavior:**
- Downloads each URL in sequence with `[i/N]` progress
- A failure on one URL does NOT stop the batch
- Summary at the end lists every failed URL with its error message
- Exit code: `0` if all succeeded, `1` if any failed

### Resolve song names to URLs (and make a YouTube playlist)

If you only have a list of **song names** (no URLs yet), use `--search`:

```powershell
ydl --search names.txt
```

For each line in `names.txt`, this asks YouTube's search for the top result. Lines are free-form (`"Dynamite - BTS"`, `"BTS Dynamite"`, `"TOMBOY (G)I-DLE"`). Output:

1. **`names.urls.txt`** — a batch file you can immediately download:
   ```powershell
   ydl --batch names.urls.txt
   ```
   The file's first lines are comments showing where it came from and the
   YouTube playlist URL — so the file is self-contained.
2. **A YouTube playlist URL** printed to the terminal — open it in your browser; YouTube will start playing the first video and show a *Save* button. Click *Save* → *+ Create new playlist* to save the list into your account.

**One-shot end-to-end** — pass `--download` to do everything in a single command (resolve names → write `.urls.txt` with playlist URL inside → download every track as audio):

```powershell
ydl --search names.txt --download                     # full pipeline, defaults
ydl --search names.txt --download --quality 320       # any download flag works
ydl --search names.txt --download --out "D:/music"
```

```
Resolving 3 song(s) via YouTube search...
  OK    Dynamite - BTS    -> BTS (방탄소년단) 'Dynamite' Official MV
  ...
Wrote 3 URL(s) to names.urls.txt
YouTube playlist URL:
  https://www.youtube.com/watch_videos?video_ids=gdZLi9oWNZg,Jh4QFaPmdss,yKNxeF4KMsY
```

**Notes:**
- YouTube's `watch_videos` endpoint accepts at most **50 IDs** per playlist URL; longer lists are truncated (the `.urls.txt` keeps everything).
- Best-effort search; spot-check the picks before saving the playlist (an obscure song name may match a cover or live clip)

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
- [ ] **Playlist / channel batch** — ~~drop `noplaylist=True`, add `--playlist` flag~~ ✅ done (also `--batch FILE` for ad-hoc URL lists)
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
