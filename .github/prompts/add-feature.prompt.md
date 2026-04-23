---
mode: agent
description: Add a new feature to the YouTube downloader while staying consistent with v1 architecture
---

# Add Feature

You are extending the YouTube downloader CLI. Before writing any code, do all of the following in order:

1. **Read the source of truth.** Open and read these files end-to-end:
   - [AGENTS.md](../../AGENTS.md) — architecture & conventions
   - [CLAUDE.md](../../CLAUDE.md) — design decisions and "Future expansion notes" section
   - [src/downloader.py](../../src/downloader.py) — current core
   - [src/cli.py](../../src/cli.py) — current CLI surface

2. **Locate the matching roadmap entry.** The feature being requested almost certainly maps to an item in CLAUDE.md → "Future expansion notes" (video downloads, device presets, GUI, AI processing, playlist support). Follow the implementation hint there. If the requested feature is NOT in that list, stop and ask the user whether to add it to the roadmap first.

3. **Respect these invariants** (violating any of them = wrong approach):
   - `src/downloader.py` stays UI-free — no `print`, no `argparse`, no `input`
   - User-actionable errors → raise `DownloaderError`. Programmer errors bubble.
   - Reuse `download_audio()` (and future `download_video()`); do NOT re-build yt-dlp option dicts in a second place
   - `DEFAULT_OUT_DIR` constant is the single source of truth for the default path
   - Use `yt-dlp` programmatic API (`YoutubeDL`), never subprocess it, never `pytube`
   - ffmpeg stays an external dependency — extend `_ensure_ffmpeg()` if a new tool is needed; do not bundle binaries

4. **Implement.** Make the smallest change that delivers the feature. Add one CLI flag, one function, one mapping table — not a new abstraction layer.

5. **Smoke-test.** Run the verified command from CLAUDE.md ("Verified test command" section) plus one new command exercising the new feature. Confirm files land in `./test_out` (gitignored) and play.

6. **Update docs minimally.**
   - README: add the new flag/usage to the options table or examples
   - CLAUDE.md: if you discovered a new gotcha, add it under "Environment gotchas" or "Code conventions"
   - AGENTS.md: only update if the architecture changed (e.g., new module added)
   - Do NOT create new markdown files unless explicitly asked

7. **Commit.** One commit, conventional-commit style: `feat: <feature>` or `fix: <thing>`.

If at any step you find yourself duplicating yt-dlp option-building, adding UI code to `downloader.py`, or creating a helper module for a one-time operation — stop and reconsider. The codebase is intentionally tiny.
