# YouTube Downloader

**Save any YouTube song to your computer as a clean, tagged music file — in one click.**

Paste a link (or just copy it) and get back an `.m4a` file that:

- Plays anywhere — Windows, iPhone, Mac, your car, foobar2000, iTunes.
- Has the **right song title and artist** in its name (no `(Official Music Video) [4K HD] FULL` mess).
- Shows **cover art** in your music player automatically.
- Sounds great — 192 kbps by default, the same audio YouTube actually serves.

Perfect for building an offline music library, prepping a road-trip playlist, or grabbing a track that isn't on Spotify.

---

## What you can do with it

- 🎵 **Grab one song** — copy the link, run `ydl`, done.
- 📂 **Whole playlist at once** — every track saved as its own file, in a folder named after the playlist.
- 📝 **Download from a list** — give it a text file of song names or links and walk away.
- 🔍 **Don't have links? Just type names** — it searches YouTube for you and downloads the top result for each.
- 🎚️ **Pick your quality** — 64 kbps for podcasts, 320 kbps for audiophile playlists.
- 🖱️ **Prefer clicking to typing?** — there's a desktop app too. Drag a list onto the window.

---

## Setup (do this once)

1. **Install Python 3.9 or newer** — [python.org/downloads](https://www.python.org/downloads/) (during install, tick *"Add Python to PATH"*).
2. **Install ffmpeg** (the audio engine). On Windows, open PowerShell and run:
   ```powershell
   winget install Gyan.FFmpeg
   ```
   Then **close that PowerShell window and open a fresh one** (otherwise it won't see ffmpeg yet).
3. **Install this app**: in PowerShell, navigate to this folder and run:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Set up the `ydl` shortcut** so you can run it from anywhere:
   ```powershell
   .\Install.bat
   ```
   Open a new PowerShell window after this — the shortcut is now ready.

That's it. You only do this once.

---

## How to use it (the easy way)

### The 5-second workflow

1. Find a song on YouTube. Copy the link from the address bar.
2. Open PowerShell. Type:
   ```powershell
   ydl
   ```
3. Done. The song lands in `C:/Users/Yoon/Music/0_temp`, named like `BTS - Dynamite.m4a`, with cover art embedded.

`ydl` reads the link straight from your clipboard — no pasting needed.

### Other ways to call it

```powershell
ydl                                              # use whatever's on your clipboard
ydl "https://www.youtube.com/watch?v=VIDEO_ID"   # paste a specific link
ydl --help                                       # show every option with examples
```

### Want a different folder, format, or quality?

```powershell
ydl --quality 320                  # higher quality
ydl --format mp3                   # save as MP3 instead of M4A
ydl --out "D:/Music/RoadTrip"      # save somewhere else
```

You can mix and match: `ydl --quality 320 --format mp3 --out "D:/Music"`

---

## Downloading a whole playlist

Got a YouTube playlist? Add `--playlist`:

```powershell
ydl "https://www.youtube.com/playlist?list=PLxxxxxxx" --playlist
```

Every track gets saved into its own folder named after the playlist — perfect for keeping albums and sets together.

> Without `--playlist`, links like `?v=ID&list=...` only download the **one** video you clicked on. This is intentional — it stops you from accidentally pulling down a 200-track playlist.

---

## Downloading a list of songs

Have a bunch of songs you want to grab? Put them in a plain text file and let `ydl` work through them.

### If you already have the YouTube links

Make a file called `songs.txt`:

```
# My road-trip playlist
Dynamite (BTS) – https://www.youtube.com/watch?v=gdZLi9oWNZg
Yellow (Coldplay) – https://www.youtube.com/watch?v=yKNxeF4KMsY
I AM (IVE) – https://www.youtube.com/watch?v=6ZUIwj3FgUY
```

Then run:

```powershell
ydl --batch songs.txt
```

The format is forgiving — comments, blank lines, dashes, any text around the link is fine.

### If you only have song names

No links? No problem. Just type the names:

```
Dynamite BTS
Yellow Coldplay
TOMBOY (G)I-DLE
```

Then run:

```powershell
ydl --search names.txt --download
```

It finds each song on YouTube, downloads the top result, and even prints a YouTube playlist link so you can save the same list to your YouTube account in one click.

### Mixing names and links works too

```
OMG (NewJeans) - https://www.youtube.com/watch?v=sVTy_wmn5SU
Ditto (NewJeans) - https://www.youtube.com/watch?v=pSUydWEqKwE
Hype Boy NewJeans
```

`ydl --batch` handles all three lines — the last one gets searched automatically.

**A few nice things about batches:**
- Live progress shows `[3/12]` so you know how far along you are.
- One bad link doesn't stop everything — it skips and keeps going.
- At the end, you get a summary of anything that failed.

---

## Prefer a window with buttons? Try the desktop app

```powershell
.\ydlg.bat
```

Double-click that file (or run it from a terminal) and you get a clean little window:

- **Paste a link** and hit Download.
- **Drag a `.txt` file** onto the window — it figures out whether it's links, song names, or a mix, and just handles it.
- **Tweak settings** with dropdowns (quality, format, output folder).
- **Watch progress** with a real progress bar and a live log.
- **Cancel** anytime if you change your mind.

Same engine as the command-line version, no console window left hanging around.

---

## Smart things it does for you

### Clean filenames

YouTube titles are messy. This app tidies them up automatically:

| What YouTube calls it | What you get |
|---|---|
| `(여자)아이들((G)I-DLE) - 'Allergy' Official Music Video` | `(G)I-DLE - Allergy.m4a` |
| `BTS (방탄소년단) 'Dynamite' Official MV` | `BTS - Dynamite.m4a` |
| `Coldplay - Yellow (Official Video)` | `Coldplay - Yellow.m4a` |

It strips the `[MV]`, `(Audio)`, `4K HD`, `Official Music Video` noise, and when an artist has both a Korean and English name, picks the romanized one so your library stays sortable.

Don't want this? Add `--no-rename`.

### Tags + cover art

Every download comes with proper metadata baked in — title, artist, year, and the YouTube thumbnail as cover art. Your music player picks it all up automatically. No more "Unknown Artist" clutter.

Don't want tags? Add `--no-tags`.

---

## Quick reference

| Flag | What it does | Default |
|------|--------------|---------|
| `--quality` | Audio quality (`64`, `128`, `192`, `256`, `320`, `highest`) | `192` |
| `--format` | File type (`m4a`, `mp3`, `ogg`) | `m4a` |
| `--out` | Where to save | `C:/Users/Yoon/Music/0_temp` |
| `--playlist` | Download every track in a playlist | off |
| `--batch FILE` | Download from a list of links/names | — |
| `--search FILE` | Find songs on YouTube by name | — |
| `--download` | Combine with `--search` to also download them | off |
| `--no-rename` | Keep YouTube's original filename | off |
| `--no-tags` | Skip tags and cover art | off |

---

## Troubleshooting

**`ffmpeg not found`** — close PowerShell and open a fresh window. ffmpeg only shows up in newly-opened terminals after it's installed.

**`ydl: command not found`** — you forgot to run `.\Install.bat`, or you didn't open a new PowerShell window afterwards.

**Download fails with a "file in use" error** — usually antivirus or Windows Search briefly locks the file. The app retries automatically; if it still fails, try a different output folder (somewhere outside `Music/` or `OneDrive/`).

**A song name found the wrong video** — search picks the top YouTube result, which is usually right but not always. For obscure tracks, grab the link manually instead.

---

## What's coming

- **Video downloads** (`.mp4`, with quality presets)
- **Device presets** — `--for iphone`, `--for android`, etc.
- **Vocal removal / instrument isolation** — AI-powered post-processing for karaoke tracks and stems
- **One-click installer** — no PowerShell knowledge needed

---

## For developers

Architecture, design decisions, and contribution notes live in [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md). The core download logic in [src/downloader.py](src/downloader.py) is UI-free and reusable — the CLI ([src/cli.py](src/cli.py)) and GUI ([src/gui.py](src/gui.py)) are thin wrappers around `download_audio()`.
