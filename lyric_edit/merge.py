"""Mix edited vocals with instrumental and export MP3."""

from __future__ import annotations

import subprocess
from pathlib import Path


def mix_vocals_instrumental(
    instrumental: Path,
    vocals: Path,
    output_mp3: Path,
    vocal_gain_db: float = 0.0,
) -> Path:
    """FFmpeg amix of instrumental + vocals → MP3."""
    if not instrumental.is_file():
        raise FileNotFoundError(f"Instrumental stem not found: {instrumental}")
    if not vocals.is_file():
        raise FileNotFoundError(f"Vocal stem not found: {vocals}")
    output_mp3.parent.mkdir(parents=True, exist_ok=True)

    vol_filter = f"volume={vocal_gain_db}dB" if vocal_gain_db else "anull"
    filter_complex = (
        f"[1:a]{vol_filter}[v];"
        f"[0:a][v]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0[aout]"
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(instrumental),
            "-i",
            str(vocals),
            "-filter_complex",
            filter_complex,
            "-map",
            "[aout]",
            "-shortest",
            "-b:a",
            "320k",
            str(output_mp3),
        ],
        check=True,
        capture_output=True,
    )
    return output_mp3
