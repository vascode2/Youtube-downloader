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

### Options

| Flag | Choices | Default |
|------|---------|---------|
| `--quality` | `64`, `128`, `256`, `320`, `highest` | `128` |
| `--format` | `m4a`, `mp3`, `ogg` | `m4a` |
| `--out` | any folder path | `C:/Users/Yoon/Music/0_temp` |

## Project layout

```
src/
  downloader.py   # core download_audio() — reusable from GUI / web / AI pipelines
  cli.py          # argparse wrapper
requirements.txt
```

## Roadmap

- Video downloads (`--video`, mp4)
- Device presets (`--for ios|android|windows|mac|linux`)
- Playlist / channel batch
- Desktop GUI (PySide6) reusing `download_audio()`
- AI post-processing (vocal removal, noise reduction) via Demucs / UVR
