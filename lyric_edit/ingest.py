"""Load audio from upload or URL."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

from lyric_edit.config import OUTPUT_DIR


def _session_dir() -> Path:
    path = OUTPUT_DIR / uuid.uuid4().hex[:12]
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(upload_path: str | Path, session: Path | None = None) -> tuple[Path, Path]:
    """Copy uploaded file into session folder; return (session_dir, song_path)."""
    session = session or _session_dir()
    src = Path(upload_path)
    dest = session / f"source{src.suffix.lower() or '.wav'}"
    dest.write_bytes(src.read_bytes())
    return session, dest


def download_from_url(url: str, session: Path | None = None) -> tuple[Path, Path]:
    """Download best audio via yt-dlp as WAV in session folder."""
    if not url.strip():
        raise ValueError("URL is empty.")

    session = session or _session_dir()
    out_template = str(session / "source.%(ext)s")

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-x",
        "--audio-format",
        "wav",
        "--audio-quality",
        "0",
        "-o",
        out_template,
        url.strip(),
    ]
    subprocess.run(cmd, check=True)

    candidates = sorted(session.glob("source.*"))
    if not candidates:
        raise FileNotFoundError("yt-dlp did not produce an audio file.")

    return session, candidates[0]
