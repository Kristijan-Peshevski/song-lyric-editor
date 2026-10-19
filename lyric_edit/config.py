import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Use the highest-accuracy Faster-Whisper model by default. Override this before
# starting the app if the machine cannot load it.
WHISPER_MODEL = os.environ.get("SONGLYRIC_WHISPER_MODEL", "large-v3")
DEMUCS_MODEL = "htdemucs_ft"
CROSSFADE_MS = 40
