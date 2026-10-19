"""Lyrics transcription with word-level timestamps."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from lyric_edit.config import WHISPER_MODEL

_model = None


@dataclass
class WordSpan:
    index: int
    text: str
    start: float
    end: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="auto")
    return _model


def transcribe_words(vocals_path: Path) -> list[WordSpan]:
    """Transcribe vocal track; return flat list of words with times (seconds)."""
    model = _get_model()
    segments, _info = model.transcribe(
        str(vocals_path),
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
        beam_size=5,
    )

    words: list[WordSpan] = []
    idx = 0
    for segment in segments:
        if not segment.words:
            continue
        for w in segment.words:
            text = (w.word or "").strip()
            if not text:
                continue
            words.append(
                WordSpan(
                    index=idx,
                    text=text,
                    start=float(w.start),
                    end=float(w.end),
                )
            )
            idx += 1

    if not words:
        raise RuntimeError(
            "No words detected on the vocal stem. Try a clearer recording or a larger Whisper model in config.py."
        )
    return words


def words_to_table(words: list[WordSpan]) -> str:
    lines = ["| # | Word | Start | End |", "|---|------|-------|-----|"]
    for w in words:
        lines.append(f"| {w.index} | {w.text} | {w.start:.2f}s | {w.end:.2f}s |")
    return "\n".join(lines)


def words_from_dicts(raw: list[dict[str, Any]]) -> list[WordSpan]:
    return [WordSpan(**item) for item in raw]
