# CLAUDE.md — Things to Remember

Working notes for the AI agent. Things that bit us, decisions we made, and stuff that's easy to forget. See [AGENTS.md](AGENTS.md) for the architecture overview.

## Environment gotchas (Windows)

- **ffmpeg PATH does not refresh in the same PowerShell session after `winget install Gyan.FFmpeg`.** Open a new terminal, or invoke the shim at `$env:LOCALAPPDATA\Microsoft\WinGet\Links\ffmpeg.exe` directly.
- The first `winget install` attempt for `Gyan.FFmpeg` silently exited without installing. Re-running with `--verbose` succeeded. If install seems to "do nothing", retry with `--verbose` before assuming it worked.
- Python interpreter on this machine: `C:/Users/Yoon/AppData/Local/Microsoft/WindowsApps/python3.12.exe` (Windows Store Python 3.12). System install — no venv yet. The path is hardcoded in `ydl.ps1` — update there if Python moves.
- Workspace path has a space (`g:\My Drive\...`). Always quote paths in PowerShell.
- **Direct `.ps1` execution is blocked** by default execution policy. Always go through `ydl.bat` (which passes `-ExecutionPolicy Bypass`). Don't tell users to run `.\_ydl.ps1` — they'll hit `UnauthorizedAccess`.
- **PowerShell prefers `.ps1` over `.bat`** when both share a stem in PATH. That's why the script is named `_ydl.ps1` (underscore prefix) and only the `.bat` is named `ydl` — so `ydl` from PowerShell resolves to the bypass-wrapper, not the blocked script.
- **PowerShell range gotcha**: `$args[1..0]` does NOT return empty when `$args.Count -eq 1`; it returns `@($args[1], $args[0])` (ranges are bidirectional). Always guard with `if ($args.Count -gt 1)` before slicing.

## Design decisions (do not relitigate without asking)

- **CLI first, GUI later.** User explicitly chose Python CLI over browser extension / GUI / mobile. Browser extensions can't download YouTube directly (CORS + DRM); they'd need a local helper anyway.
- **M4A default, not MP3.** YouTube serves AAC natively → M4A = no transcoding loss + better quality at 128k + native iOS/Mac support. MP3 is offered as an option for compatibility.
- **128 kbps default** — matches user's primary use case (the screenshot showed 128k M4A for iOS).
- **`yt-dlp`, never `pytube`.** pytube breaks frequently when YouTube changes its page format.
- **No playlist support in v1** (per user). `noplaylist=True` is set explicitly.
- **ffmpeg as external dep** — documented in README, not bundled. Bundling adds ~70MB and licensing complexity.

## Code conventions

- `downloader.py` stays UI-free. If you need to print or parse argv there, you're doing it wrong — push it to `cli.py`.
- All user-actionable failures → `DownloaderError`. Let programmer errors bubble.
- The progress hook prints with `\r` to stdout; it's overwritten by the post-processing line. If adding a GUI, pass a custom `progress_hook` rather than reading stdout.
- yt-dlp's post-processing renames the file *after* `extract_info` returns. We reconstruct the final path via `prepare_filename` + the `fmt` extension, with a glob-based fallback. Don't trust `info["filepath"]` — it's the pre-processed file.

## Future expansion notes

- **Adding video**: add `download_video(url, quality, container, out_dir)` in `downloader.py` with `format='bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'` and `merge_output_format='mp4'`. Add `--video` flag in `cli.py` that dispatches to it. Don't merge audio+video into one mega-function.
- **Device presets** (`--for ios|android|mp3|ogg|windows|mac|linux`): just a mapping table from preset → `(fmt, quality)`. Apply before calling `download_audio`. Keep the core function preset-unaware.
- **GUI** (PySide6 recommended): `gui.py` imports `download_audio`, runs it on a `QThread`, pipes progress hook into a signal. Do not subprocess the CLI.
- **AI processing** (vocal removal etc. — see screenshots in original request): chain after download. Likely tools: Demucs (vocal isolation), UVR-MDX-Net. These are heavy ML deps — make optional via `requirements-ai.txt`, don't pollute the base install.

## Verified test command

```powershell
python -m src.cli "https://www.youtube.com/watch?v=jNQXAC9IVRw" --out "./test_out"
```
Should produce `Me at the zoo.m4a` (~310 KB) in `./test_out/`. Used as smoke test.

## Agent customizations (chat-only, not runtime code)

- [.github/prompts/add-feature.prompt.md](.github/prompts/add-feature.prompt.md) — slash prompt: load this whenever the user asks to add a feature. Forces reading AGENTS/CLAUDE first and respects the architecture invariants.
- [.copilot/skills/ai-postprocess/SKILL.md](.copilot/skills/ai-postprocess/SKILL.md) — auto-loaded skill for any AI-audio-processing request (vocal removal, denoise, etc.). Encodes tool choices (Demucs, Resemble Enhance) and pipeline pattern.

If you're tempted to add more agents/hooks/skills: don't, unless the codebase has actually grown. The article we drew from explicitly warns "필요한 설정만 활성화" (only activate what you need) — over-customization eats context budget.
