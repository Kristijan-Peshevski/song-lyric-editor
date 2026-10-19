"""Orchestrate word replacements and full-song export."""

from __future__ import annotations

from pathlib import Path

from lyric_edit.backends import BACKENDS
from lyric_edit.merge import mix_vocals_instrumental
from lyric_edit.transcribe import WordSpan


def apply_word_replacements(
    *,
    vocals_path: Path,
    instrumental_path: Path,
    words: list[WordSpan],
    replacements: list[tuple[int, str]],
    work_dir: Path,
    backend_name: str = "melody_guided",
) -> tuple[Path, Path]:
    """
    Replace several words in the vocal stem and mix with instrumental.
    Returns (edited_vocals_wav, final_mp3).
    """
    backend = BACKENDS.get(backend_name)
    if backend is None:
        raise ValueError(f"Unknown backend: {backend_name}")

    if not replacements:
        raise ValueError("Add at least one word replacement.")

    seen_indexes: set[int] = set()
    edited_vocals = vocals_path
    for word_index, new_text in replacements:
        if word_index < 0 or word_index >= len(words):
            raise IndexError(
                f"word_index {word_index} out of range (0..{len(words) - 1})"
            )
        if word_index in seen_indexes:
            raise ValueError(f"Word index {word_index} is listed more than once.")
        if not new_text.strip():
            raise ValueError(f"Replacement for word index {word_index} is empty.")
        seen_indexes.add(word_index)
        edited_vocals = backend.replace_word(
            edited_vocals, words[word_index], new_text, work_dir
        )

    final_mp3 = work_dir / "edited_song.mp3"
    mix_vocals_instrumental(instrumental_path, edited_vocals, final_mp3)
    return edited_vocals, final_mp3


def apply_word_replacement(
    *,
    vocals_path: Path,
    instrumental_path: Path,
    words: list[WordSpan],
    word_index: int,
    new_text: str,
    work_dir: Path,
    backend_name: str = "melody_guided",
) -> tuple[Path, Path]:
    """Backward-compatible wrapper for a single replacement."""
    return apply_word_replacements(
        vocals_path=vocals_path,
        instrumental_path=instrumental_path,
        words=words,
        replacements=[(word_index, new_text)],
        work_dir=work_dir,
        backend_name=backend_name,
    )
