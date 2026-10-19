# SongLyricEditor

Edit one or more words (or short phrases) in a song while keeping the **same backing track**, **similar timing**, and **similar pitch contour** on the vocal line.

This is the inverse of your old **VoiceSwapApp** (same song, new voice). Here the goal is: **same voice-ish performance and melody slot, new lyrics**.

## What it does today

1. **Import** — Upload MP3/WAV, or paste a YouTube URL (via `yt-dlp`; use only content you have rights to).
2. **Analyze** — Demucs splits **vocals** / **instrumental**; Faster-Whisper transcribes with **word timestamps**.
3. **Edit** — Add replacement rows with the `+` button; each row selects a word index and its replacement.
4. **Render** — Replaces that slice in the vocal stem, then mixes back to a full song.

The `melody_guided` engine is a lightweight fallback: it synthesizes the new text with [Edge TTS](https://github.com/rany2/edge-tts), then **time-stretches** and **pitch-shifts** it to match the original word’s duration and median pitch. It does **not** clone the singer and must not be used when an identical voice is required.

For same-voice singing, use `ace_step`. This app writes one lyric-edit job per replacement and passes the edited vocal through each job. The adapter uses ACE-Step 1.5's `repaint` task on the vocal stem and selected time interval; ordinary TTS cannot provide the original singer's voice.

For **higher quality** (same voice + melody preservation), use an optional backend:

| Backend | Quality | GPU | Notes |
|--------|---------|-----|--------|
| `melody_guided` | Fallback only | Optional | Built-in TTS; different voice, not singing voice cloning |
| `ace_step` | Best (when it works) | 8GB+ VRAM typical | ACE-Step 1.5 repaint adapter for small vocal segments |
| External | Varies | Varies | [SongSuro](https://github.com/NomaDamas/SongSuro), [YingMusic-Singer](https://github.com/GiantAILab/YingMusic-Singer) |

## Requirements

- **Python 3.10+**
- **FFmpeg** on `PATH` (for mixdown and `yt-dlp` audio extract)
- **CUDA** optional (Demucs / Whisper run faster on GPU)

## Setup (Windows)

```powershell
cd $env:USERPROFILE\Documents\SongLyricEditor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

First run will download Whisper and Demucs weights. The default Whisper model is
`large-v3` for the best word coverage. It is a large download and needs substantial
RAM/VRAM. On a slower machine, set
`$env:SONGLYRIC_WHISPER_MODEL = "small"` before starting the app.

## Install ACE-Step 1.5 locally (Windows)

ACE-Step uses its own virtual environment because its dependencies are separate from
SongLyricEditor. These are the commands used to install the local ACE-Step 1.5 checkout:

```powershell
cd C:\Users\Kristijan\Documents\SongLyricEditor

powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

git clone https://github.com/ACE-Step/ACE-Step-1.5.git
cd ACE-Step-1.5
uv sync
```

`uv sync` creates `ACE-Step-1.5\.venv` and installs ACE-Step 1.5 and its dependencies,
including the Windows CUDA-enabled PyTorch packages selected by the project.

After installation, configure the SongLyricEditor process to use this checkout:

```powershell
$env:ACE_STEP_ROOT = "C:\Users\Kristijan\Documents\SongLyricEditor\ACE-Step-1.5"
cd ..
python app.py
```

The complete command sequence from the installation session was:

```powershell
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor> git clone https://github.com/ACE-Step/ACE-Step-1.5.git
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor> cd ACE-Step-1.5
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor\ACE-Step-1.5> uv sync
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor\ACE-Step-1.5> $env:ACE_STEP_ROOT = "C:\Users\Kristijan\Documents\SongLyricEditor\ACE-Step-1.5"
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor\ACE-Step-1.5> cd ..
(.venv) PS C:\Users\Kristijan\Documents\SongLyricEditor> python app.py
```

Keep the same PowerShell window open when starting `app.py`, because
`$env:ACE_STEP_ROOT` only applies to the current process and its child processes.
The first ACE-Step edit downloads model checkpoints automatically. The model is several
GB and requires substantial RAM; GPU acceleration requires a working NVIDIA driver and
`torch.cuda.is_available()` to return `True`.

## Run

```powershell
python app.py
```

Open the URL shown in the terminal (default `http://127.0.0.1:7860`).

If ACE-Step is installed and provides the helper expected by this project, configure it
before starting the app:

```powershell
$env:ACE_STEP_ROOT = "C:\path\to\ACE-Step"
python app.py
```

The app selects ACE-Step only when `ACE_STEP_ROOT`, its `.venv`, and
`scripts\lyric_edit_cli.py` exist. The SongLyricEditor adapter calls ACE-Step 1.5's
real `repaint` inference task for the selected interval. The fallback is not the
original singer's voice.

## Tips for believable edits

- Keep each replacement short; add multiple rows when changing several words.
- Prefer replacements with **similar syllable count** and stress pattern.
- ACE-Step’s docs warn: large lyric rewrites at once often distort vocals — edit **small segments** sequentially.

## Legal

Only process audio you own or are licensed to modify. YouTube download is for convenience; compliance is your responsibility.

## Project layout

```
SongLyricEditor/
  app.py                 # Gradio UI
  lyric_edit/            # Pipeline modules
  outputs/               # Generated files (gitignored)
```
