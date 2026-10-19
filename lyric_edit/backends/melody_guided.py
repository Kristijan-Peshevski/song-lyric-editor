"""Experimental local word replace: TTS + pitch/duration match + crossfade."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from lyric_edit.backends.base import ReplacementBackend
from lyric_edit.config import CROSSFADE_MS
from lyric_edit.transcribe import WordSpan


async def _edge_tts_to_file(text: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice="en-US-AriaNeural")
    await communicate.save(str(out_path))


def _run_edge_tts(text: str, out_path: Path) -> None:
    asyncio.run(_edge_tts_to_file(text, out_path))


def _median_f0(y: np.ndarray, sr: int) -> float | None:
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
    )
    if voiced_flag is not None:
        voiced = f0[np.asarray(voiced_flag, dtype=bool)]
    else:
        voiced = f0.copy()
    voiced = voiced[~np.isnan(voiced)]
    if len(voiced) == 0:
        return None
    return float(np.median(voiced))


def _pitch_shift_to_target(y: np.ndarray, sr: int, target_hz: float | None) -> np.ndarray:
    if target_hz is None:
        return y
    source_hz = _median_f0(y, sr)
    if source_hz is None or source_hz <= 0:
        return y
    semitones = 12.0 * np.log2(target_hz / source_hz)
    semitones = float(np.clip(semitones, -8.0, 8.0))
    if abs(semitones) < 0.05:
        return y
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=semitones)


def _fit_duration(y: np.ndarray, sr: int, target_samples: int) -> np.ndarray:
    if target_samples <= 0:
        return y
    if len(y) == target_samples:
        return y
    rate = len(y) / target_samples
    stretched = librosa.effects.time_stretch(y, rate=rate)
    if len(stretched) > target_samples:
        return stretched[:target_samples]
    if len(stretched) < target_samples:
        pad = target_samples - len(stretched)
        return np.pad(stretched, (0, pad))
    return stretched


def _crossfade_replace(
    vocals: np.ndarray,
    sr: int,
    start_sample: int,
    end_sample: int,
    replacement: np.ndarray,
) -> np.ndarray:
    out = vocals.copy()
    seg_len = end_sample - start_sample
    rep = _fit_duration(replacement, sr, seg_len)

    fade = int(sr * (CROSSFADE_MS / 1000.0))
    fade = min(fade, seg_len // 4, max(1, len(rep) // 4))

    if fade > 1:
        fade_in = np.linspace(0.0, 1.0, fade)
        fade_out = 1.0 - fade_in
        rep[:fade] *= fade_in
        rep[-fade:] *= fade_out
        out[start_sample : start_sample + fade] *= fade_out
        out[end_sample - fade : end_sample] *= fade_in

    out[start_sample:end_sample] = rep
    return out


class MelodyGuidedBackend(ReplacementBackend):
    name = "melody_guided"
    description = "Edge TTS + pitch/duration match (experimental, CPU-friendly)"

    def replace_word(
        self,
        vocals_path: Path,
        word: WordSpan,
        new_text: str,
        work_dir: Path,
    ) -> Path:
        new_text = new_text.strip()
        if not new_text:
            raise ValueError("Replacement text is empty.")

        y, sr = librosa.load(vocals_path, sr=None, mono=True)
        start_s = max(0, int(word.start * sr))
        end_s = min(len(y), int(word.end * sr))
        if end_s <= start_s:
            raise ValueError("Invalid word time range.")

        original_slice = y[start_s:end_s]
        target_f0 = _median_f0(original_slice, sr)

        with tempfile.TemporaryDirectory(dir=work_dir) as tmp:
            tts_mp3 = Path(tmp) / "word.mp3"
            _run_edge_tts(new_text, tts_mp3)
            tts_y, tts_sr = librosa.load(tts_mp3, sr=sr, mono=True)

        tts_y = _pitch_shift_to_target(tts_y, sr, target_f0)
        edited = _crossfade_replace(y, sr, start_s, end_s, tts_y)

        out_path = work_dir / "vocals_edited.wav"
        sf.write(out_path, edited, sr)
        return out_path
