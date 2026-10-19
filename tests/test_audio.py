import os

import numpy as np
import pytest

from airmorse.gesture.morse import MorseEvent
from airmorse.output.audio import sound_key, synth_tone


def test_dash_is_longer_than_dot():
    dot = synth_tone(800, 60)
    dash = synth_tone(800, 180)
    assert dot.dtype == np.int16
    assert len(dash) > len(dot) * 2


def test_error_tone_is_distinct():
    dash = synth_tone(800, 180)
    error = synth_tone(360, 180)
    assert not np.array_equal(dash, error)


def test_sound_keys():
    assert sound_key(MorseEvent("symbol", ".")) == "dot"
    assert sound_key(MorseEvent("symbol", "-")) == "dash"
    assert sound_key(MorseEvent("char", "A")) == "click"
    assert sound_key(MorseEvent("space", " ")) == "click"
    assert sound_key(MorseEvent("enter", "\n")) == "click"
    assert sound_key(MorseEvent("pop", ".")) == "click"
    assert sound_key(MorseEvent("backspace", "A")) == "click"
    assert sound_key(MorseEvent("error", "......")) == "error"


def test_audio_feedback_plays_without_blocking():
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from airmorse.output.audio import AudioFeedback

    audio = AudioFeedback()
    if not audio.available:
        pytest.skip(audio.error or "audio device unavailable")
    audio.play(MorseEvent("symbol", "."))
    audio.play(MorseEvent("symbol", "-"))
    audio.play(MorseEvent("char", "S"))
    audio.play(MorseEvent("error", "......"))
