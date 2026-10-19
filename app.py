"""
SongLyricEditor — Gradio UI for word-level lyric edits.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path

# Harmless on Windows when Developer Mode / admin symlinks are unavailable.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
from typing import Any

import gradio as gr

from lyric_edit.backends import BACKENDS
from lyric_edit.config import WHISPER_MODEL
from lyric_edit.ingest import download_from_url, save_upload
from lyric_edit.replace import apply_word_replacements
from lyric_edit.separate import separate_stems
from lyric_edit.transcribe import transcribe_words, words_from_dicts, words_to_table


def _backend_choices() -> list[str]:
    return list(BACKENDS.keys())


def _default_backend() -> str:
    """Prefer ACE-Step only when its local helper is ready to run."""
    ace_root = os.environ.get("ACE_STEP_ROOT")
    if ace_root:
        ace_path = Path(ace_root)
        ace_python = ace_path / ".venv" / "Scripts" / "python.exe"
        if (
            ace_path.is_dir()
            and ace_python.is_file()
            and (ace_path / "scripts" / "lyric_edit_cli.py").is_file()
        ):
            return "ace_step"
    return "melody_guided"


def _ace_step_info() -> str:
    ace_root = os.environ.get("ACE_STEP_ROOT")
    if not ace_root:
        return (
            "Not configured in this process. Set `ACE_STEP_ROOT` before starting "
            "`python app.py`; the project also needs `scripts\\lyric_edit_cli.py`."
        )
    helper = Path(ace_root) / "scripts" / "lyric_edit_cli.py"
    ace_python = Path(ace_root) / ".venv" / "Scripts" / "python.exe"
    if not Path(ace_root).is_dir():
        return f"`ACE_STEP_ROOT` does not exist: `{ace_root}`."
    if not helper.is_file():
        return f"ACE_STEP_ROOT is set, but the required helper is missing: `{helper}`."
    if not ace_python.is_file():
        return f"ACE-Step environment is missing: `{ace_python}`. Run `uv sync` in ACE-Step."
    return "Configured. ACE-Step will edit the selected interval in `repaint` mode."


def _backend_help() -> str:
    lines = ["**Backends**"]
    for key, backend in BACKENDS.items():
        lines.append(f"- `{key}`: {backend.description}")
    return "\n".join(lines)


def import_song(upload, url: str) -> tuple[dict[str, Any], str]:
    try:
        if upload is not None:
            session, song = save_upload(upload)
            msg = f"Loaded upload: `{song.name}`"
        elif url and url.strip():
            session, song = download_from_url(url.strip())
            msg = f"Downloaded: `{song.name}`"
        else:
            return {}, "Provide an audio file or a URL."

        state = {
            "session": str(session),
            "song": str(song),
        }
        return state, msg
    except Exception as exc:
        return {}, f"Import failed: {exc}"


def analyze_song(
    state: dict[str, Any],
    upload,
    url: str,
    progress=gr.Progress(),
) -> tuple[dict[str, Any], str, str]:
    if not state.get("song"):
        progress(0, desc="Importing audio…")
        state, import_msg = import_song(upload, url)
        if not state.get("song"):
            return state, "", import_msg

    try:
        session = Path(state["session"])
        song = Path(state["song"])
        status_lines: list[str] = []

        def note(msg: str) -> None:
            status_lines.append(msg)
            print(f"[analyze] {msg}", flush=True)

        progress(0.05, desc="Separating vocals (Demucs)…")
        vocals, instrumental = separate_stems(song, session, on_status=note)

        progress(0.55, desc="Transcribing lyrics (Whisper)…")
        note("Running Faster-Whisper on vocal stem (first run downloads the model).")
        words = transcribe_words(vocals)
        progress(1.0, desc="Done")

        state = {
            **state,
            "vocals": str(vocals),
            "instrumental": str(instrumental),
            "words": [w.to_dict() for w in words],
        }
        table = words_to_table(words)
        preview = "\n".join(f"{w.index}: {w.text}" for w in words[:80])
        if len(words) > 80:
            preview += f"\n... (+{len(words) - 80} more words)"
        steps = "\n".join(f"- {line}" for line in status_lines)
        return (
            state,
            table,
            f"Found **{len(words)}** words using Whisper `{WHISPER_MODEL}`. "
            "Vocal / instrumental stems ready.\n\n"
            f"{preview}\n\n**Steps:**\n{steps}",
        )
    except Exception as exc:
        tb = traceback.format_exc()
        return state, "", f"Analyze failed: {exc}\n\n```\n{tb}\n```"


def render_edit(
    state: dict[str, Any],
    replacement_rows: list[list[Any]] | None,
    backend: str,
) -> tuple[str, str | None, str | None]:
    if not state.get("words"):
        return "Run **Analyze** first.", None, None

    try:
        words = words_from_dicts(state["words"])
        replacements: list[tuple[int, str]] = []
        for row_number, row in enumerate(replacement_rows or [], start=1):
            if len(row) < 2:
                continue
            index_value, text_value = row[0], row[1]
            if index_value in (None, "") and not str(text_value or "").strip():
                continue
            if index_value in (None, ""):
                raise ValueError(f"Replacement row {row_number} has no word index.")
            replacements.append((int(index_value), str(text_value or "")))
        if not replacements:
            raise ValueError("Add at least one word replacement.")

        session = Path(state["session"])
        edited_vocals, final_mp3 = apply_word_replacements(
            vocals_path=Path(state["vocals"]),
            instrumental_path=Path(state["instrumental"]),
            words=words,
            replacements=replacements,
            work_dir=session,
            backend_name=backend,
        )

        changes = "\n".join(
            f"- **#{index}** `{words[index].text}` → `{text.strip()}` "
            f"({words[index].start:.2f}s–{words[index].end:.2f}s)"
            for index, text in replacements
        )
        summary = (
            f"Replaced {len(replacements)} word(s) using `{backend}`:\n{changes}\n\n"
            f"Edited vocals: `{edited_vocals.name}`\nFull mix: `{final_mp3.name}`"
        )
        state["last_output"] = str(final_mp3)
        return summary, str(final_mp3), str(edited_vocals)
    except Exception as exc:
        tb = traceback.format_exc()
        return f"Edit failed: {exc}\n\n```\n{tb}\n```", None, None


def add_replacement_row(rows: list[list[Any]] | None) -> list[list[Any]]:
    """Append a clearly empty replacement row to the editable grid."""
    current_rows = [list(row[:2]) for row in (rows or [])]
    if not current_rows:
        return [[None, ""]]
    return current_rows + [[None, ""]]


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="SongLyricEditor") as demo:
        gr.Markdown(
            "# SongLyricEditor\n"
            "Change a **word** in a song while keeping the **instrumental** and roughly the "
            "**same vocal timing and pitch slot**. Add as many replacement rows as needed."
        )
        gr.Markdown(_backend_help())

        state = gr.State({})

        with gr.Tab("1. Import"):
            upload = gr.Audio(type="filepath", label="Upload song (MP3/WAV)")
            url = gr.Textbox(label="Or YouTube / audio URL (yt-dlp)", placeholder="https://...")
            import_btn = gr.Button("Import", variant="primary")
            import_status = gr.Markdown()

        with gr.Tab("2. Analyze"):
            gr.Markdown(
                "Upload a file on tab 1 (Import is optional — Analyze can import for you). "
                "**First analyze** downloads Demucs + Whisper weights and can take **5–20+ minutes on CPU**. "
                "The terminal window will show Demucs progress; the browser spinner is normal until it finishes."
            )
            analyze_btn = gr.Button("Separate vocals & transcribe", variant="primary")
            analyze_status = gr.Markdown()
            words_table = gr.Markdown(label="Word timings")

        with gr.Tab("3. Edit word"):
            gr.Markdown(
                "Add one row per change. The **melody_guided** engine is only a TTS fallback "
                "and cannot reproduce the original singer. Use **ace_step** with a configured "
                "ACE-Step lyric-edit helper for same-voice singing."
            )
            gr.Markdown(
                f"Lyric analysis model: `{WHISPER_MODEL}`. "
                "Large-v3 downloads several GB and needs substantial RAM/VRAM."
            )
            gr.Markdown(_ace_step_info())
            replacements = gr.Dataframe(
                headers=["Word index", "New word or short phrase"],
                datatype=["number", "str"],
                type="array",
                value=[[None, ""]],
                row_count=(1, "dynamic"),
                column_count=(2, "fixed"),
                label="Replacements",
            )
            add_replacement = gr.Button("+ Add another word")
            backend = gr.Dropdown(
                _backend_choices(),
                value=_default_backend(),
                label="Engine",
                info=(
                    "ACE-Step is selected automatically only when ACE_STEP_ROOT and its "
                    "lyric-edit helper are configured."
                ),
            )
            edit_btn = gr.Button("Apply edit", variant="primary")
            edit_status = gr.Markdown()
            out_song = gr.Audio(label="Full song (edited)", type="filepath")
            out_vocals = gr.Audio(label="Edited vocal stem", type="filepath")

        import_btn.click(import_song, [upload, url], [state, import_status])
        analyze_btn.click(
            analyze_song,
            [state, upload, url],
            [state, words_table, analyze_status],
        )
        add_replacement.click(
            add_replacement_row,
            replacements,
            replacements,
        )
        edit_btn.click(
            render_edit,
            [state, replacements, backend],
            [edit_status, out_song, out_vocals],
        )

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.launch()
