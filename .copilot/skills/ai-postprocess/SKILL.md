---
name: ai-postprocess
description: Chain AI audio post-processing (vocal removal, voice extraction, noise reduction, instrument isolation, voice change, upscaling) onto downloaded YouTube audio. Load this skill whenever the user asks for "remove vocals", "isolate vocals", "extract instruments", "karaoke version", "clean up audio", "denoise", "remove background music", "voice clone", "upscale audio", or any of the AI processing operations shown in the 4K Video Downloader+ AI panel screenshots.
---

# AI Audio Post-Processing

This skill describes how to extend the YouTube downloader with AI audio processing that runs **after** `download_audio()` finishes. Mirrors the "AI Processing" panel from 4K Video Downloader+ (vocal removal, vocal extraction, voice isolation, echo removal, background music removal, denoise, instrument extraction, loudness balance, audio upscale, voice change, lead vocal extract, back vocal extract).

## Architectural rules (do not violate)

1. **Optional install.** AI deps are heavy (PyTorch, model weights ~hundreds of MB). They MUST live in a separate `requirements-ai.txt` and import lazily. The base CLI must continue to work without them installed.
2. **Pipeline pattern, not monolith.** Each AI operation is its own function in `src/ai/<op>.py` taking `(in_path: Path, out_dir: Path) -> Path`. They never know about yt-dlp.
3. **CLI composes.** Add `--ai <op>[,<op>...]` to `cli.py`. The CLI calls `download_audio(...)` first, then chains the AI ops in order, passing each output to the next input.
4. **Fail soft.** If an AI dep is missing, raise `DownloaderError("Install AI extras: pip install -r requirements-ai.txt")`. Never silently no-op.

## Operation → tool mapping (use these, don't invent alternatives)

| Operation | Tool | Notes |
|---|---|---|
| Remove Vocals (karaoke / instrumental) | **Demucs** (`htdemucs` model) | Output: `no_vocals.wav`. Best quality open-source separator. |
| Extract Vocals | **Demucs** (`htdemucs`) | Output: `vocals.wav`. Same model, different stem. |
| Extract Voice (isolate speech from all bg) | **Demucs** + filter, or **Resemble Enhance** | For speech specifically, Resemble Enhance > Demucs. |
| Remove Echo / Reverb | **Resemble Enhance** (`enhance` mode) | Also handles general voice cleanup. |
| Remove Background Music (keep speech) | **Demucs** (`htdemucs`) take `vocals` stem | Same as extract vocals; the use case differs but the operation is identical. |
| Remove Noise | **Resemble Enhance** or **demucs --two-stems=vocals** | Use `noisereduce` (lightweight) for simple cases; Resemble for ML-based. |
| Extract Instruments (drums/bass/other) | **Demucs** (`htdemucs_ft` 6-stem model) | Returns drums/bass/other/vocals/guitar/piano stems. |
| Balance Loudness | **pyloudnorm** (LUFS normalization to -14 LUFS) | Not ML — simple DSP, do NOT use a model for this. |
| Upscale Audio | **AudioSR** (Haoheliu) | Heavy (~3GB model). Make this an opt-in extra-extra. |
| Change Voice | **so-vits-svc** or **RVC** | Requires a target voice model file. Out of scope for first AI release — defer. |
| Extract Lead Vocal | **Demucs** then duet-aware split | First release: alias to "Extract Vocals". |
| Extract Back Vocal | **Demucs** + harmony separation | Defer — no clean OSS solution. |

**Build order:** Start with Remove Vocals + Extract Vocals (Demucs covers both). Add denoise (Resemble Enhance) second. Defer the rest until requested.

## Implementation skeleton

```
src/
  ai/
    __init__.py        # registry: NAME_TO_FUNC mapping
    demucs_split.py    # remove_vocals(), extract_vocals(), extract_instruments()
    enhance.py         # remove_echo(), remove_noise(), extract_voice()
    loudness.py        # balance_loudness() — pyloudnorm
requirements-ai.txt    # demucs, resemble-enhance, pyloudnorm, torch
```

Lazy import inside each function:
```python
def remove_vocals(in_path, out_dir):
    try:
        import demucs.separate
    except ImportError as e:
        raise DownloaderError("Install AI extras: pip install -r requirements-ai.txt") from e
    ...
```

## CLI integration

```powershell
python -m src.cli "<url>" --ai remove_vocals
python -m src.cli "<url>" --ai remove_noise,balance_loudness  # chain in order
```

Pipeline: `download_audio()` → temp wav → AI op 1 → AI op 2 → final file (named `<title>.<op>.<ext>`).

## Performance / UX gotchas

- **First run downloads model weights** (Demucs ~80MB, Resemble Enhance ~200MB, AudioSR ~3GB). Print a one-time warning so users don't think it hung.
- **GPU vs CPU.** Demucs is ~10x faster on CUDA. Detect `torch.cuda.is_available()` and pass device accordingly. Don't assume GPU.
- **Format conversion.** Demucs/Resemble work on WAV. Convert M4A → WAV (ffmpeg) before processing, then convert back to the user's chosen format. Use a temp dir, clean up.
- **Don't re-encode lossy → lossy unnecessarily.** If user wants vocal-removed M4A from a YouTube M4A, the chain is: m4a → wav → demucs → wav → m4a (one extra encode). Acceptable.

## Things NOT to do

- ❌ Do not bundle model weights in the repo (gitignore them; let the libraries download on first use).
- ❌ Do not import AI libs at module load time anywhere in `src/` outside `src/ai/`. The base CLI must stay fast and dep-light.
- ❌ Do not write your own vocal separator. Demucs is state-of-the-art OSS — use it.
- ❌ Do not expose AI features in `download_audio()` itself. Keep download and post-process as separate phases.

## When done, update

- README: add `## AI processing (optional)` section with install + usage
- CLAUDE.md: under "Future expansion notes", change AI processing from "future" to "implemented (basic)"
- requirements-ai.txt: pin versions
