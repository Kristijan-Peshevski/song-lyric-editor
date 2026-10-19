"""Vocal / instrumental separation with Demucs."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from lyric_edit.config import DEMUCS_MODEL


def separate_stems(
    song_path: Path,
    work_dir: Path,
    *,
    on_status: Callable[[str], None] | None = None,
) -> tuple[Path, Path]:
    """
    Run Demucs two-stems=vocals. Returns (vocals_wav, instrumental_wav).
    Reuses existing stems if already present for this song name.
    """
    song_stem = song_path.stem
    demucs_out = work_dir / DEMUCS_MODEL / song_stem
    vocals = demucs_out / "vocals.wav"
    instrumental = demucs_out / "no_vocals.wav"

    if vocals.is_file() and instrumental.is_file():
        if on_status:
            on_status("Using cached vocal/instrumental stems.")
        return vocals, instrumental

    if on_status:
        on_status(
            "Running Demucs (first run also downloads the model). "
            "On CPU this often takes several minutes — watch this terminal for progress."
        )

    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=vocals",
        "-n",
        DEMUCS_MODEL,
        str(song_path),
        "-o",
        str(work_dir),
    ]
    # Stream progress to the terminal (Demucs uses tqdm).
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Demucs exited with code {result.returncode}. See terminal output above.")

    if not vocals.is_file() or not instrumental.is_file():
        raise RuntimeError("Demucs separation failed — vocal or instrumental stem missing.")

    return vocals, instrumental
