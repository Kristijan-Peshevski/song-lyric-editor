from lyric_edit.backends.melody_guided import MelodyGuidedBackend
from lyric_edit.backends.ace_step import AceStepBackend

BACKENDS = {
    "melody_guided": MelodyGuidedBackend(),
    "ace_step": AceStepBackend(),
}
