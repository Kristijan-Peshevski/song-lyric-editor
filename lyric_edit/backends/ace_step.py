"""Optional ACE-Step integration (manual install)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from lyric_edit.backends.base import ReplacementBackend
from lyric_edit.transcribe import WordSpan


def resolve_ace_step_root() -> Path | None:
    """Use the environment override or the checkout beside this project."""
    configured = os.environ.get("ACE_STEP_ROOT")
    candidates = [Path(configured)] if configured else []
    candidates.append(Path(__file__).resolve().parents[2] / "ACE-Step-1.5")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


class AceStepBackend(ReplacementBackend):
    name = "ace_step"
    description = "ACE-Step repaint lyric edit — requires local ACE-Step 1.5"

    def replace_word(
        self,
        vocals_path: Path,
        word: WordSpan,
        new_text: str,
        work_dir: Path,
    ) -> Path:
        ace_path = resolve_ace_step_root()
        if ace_path is None:
            raise RuntimeError(
                "ACE-Step was selected, but no installation was found. Expected "
                "ACE-Step-1.5 beside SongLyricEditor or ACE_STEP_ROOT pointing to it."
            )

        job = {
            "input_audio": str(vocals_path.resolve()),
            "start_sec": word.start,
            "end_sec": word.end,
            "old_text": word.text,
            "new_text": new_text.strip(),
            "mode": "repaint",
        }
        job_path = work_dir / "ace_step_job.json"
        job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")

        helper = ace_path / "scripts" / "lyric_edit_cli.py"
        if helper.is_file():
            ace_python = ace_path / ".venv" / "Scripts" / "python.exe"
            if not ace_python.is_file():
                ace_python = ace_path / ".venv" / "bin" / "python"
            if not ace_python.is_file():
                raise RuntimeError(
                    f"ACE-Step environment not found under {ace_path / '.venv'}. "
                    "Run `uv sync` from the ACE-Step directory."
                )
            subprocess.run(
                [str(ace_python), str(helper), str(job_path), str(work_dir)],
                check=True,
                cwd=ace_path,
            )
            candidate = work_dir / "vocals_edited.wav"
            if candidate.is_file():
                return candidate

        raise RuntimeError(
            f"ACE-Step job file written to {job_path}. "
            "No helper script found at scripts/lyric_edit_cli.py — open ACE-Step UI, "
            "load the vocal stem, repaint this segment, export WAV, "
            f"and save as {work_dir / 'vocals_edited.wav'}."
        )
