from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from lyric_edit.transcribe import WordSpan


class ReplacementBackend(ABC):
    name: str
    description: str

    @abstractmethod
    def replace_word(
        self,
        vocals_path: Path,
        word: WordSpan,
        new_text: str,
        work_dir: Path,
    ) -> Path:
        """Return path to full-length edited vocal WAV."""
