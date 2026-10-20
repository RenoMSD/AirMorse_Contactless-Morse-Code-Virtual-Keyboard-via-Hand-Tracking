"""Short Morse tones. Playback does not block the camera loop."""

import numpy as np

from airmorse.gesture.morse import MorseEvent


def synth_tone(
    freq: float,
    duration_ms: int,
    sample_rate: int = 22050,
    volume: float = 0.35,
) -> np.ndarray:
    count = max(1, int(sample_rate * duration_ms / 1000))
    times = np.arange(count, dtype=np.float64) / sample_rate
    wave = np.sin(2 * np.pi * freq * times)
    attack = min(count // 4, int(sample_rate * 0.008))
    if attack > 0:
        envelope = np.ones(count, dtype=np.float64)
        envelope[:attack] = np.linspace(0, 1, attack, endpoint=False)
        envelope[-attack:] = np.linspace(1, 0, attack, endpoint=False)
        wave *= envelope
    return (wave * volume * 32767).astype(np.int16)


def sound_key(event: MorseEvent) -> str | None:
    if event.kind == "symbol" and event.value == ".":
        return "dot"
    if event.kind == "symbol" and event.value == "-":
        return "dash"
    if event.kind in {"char", "space", "newline", "enter", "pop", "backspace"}:
        return "click"
    if event.kind == "error":
        return "error"
    return None


class AudioFeedback:
    def __init__(self) -> None:
        self.available = False
        self.error = ""
        self._sounds: dict[str, object] = {}
        try:
            import os

            os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            import pygame

            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            init = pygame.mixer.get_init()
            self._mono = bool(init and init[2] == 1)
            pygame.mixer.set_num_channels(8)
            self._sounds = {
                "dot": self._make(pygame, 800, 60),
                "dash": self._make(pygame, 800, 180),
                "click": self._make(pygame, 1400, 30),
                "error": self._make(pygame, 360, 220),
            }
            self.available = True
        except Exception as exc:
            self.error = str(exc)
            self.available = False

    def _make(self, pygame, freq: float, duration_ms: int):
        samples = np.ascontiguousarray(synth_tone(freq, duration_ms))
        if not self._mono:
            samples = np.ascontiguousarray(np.column_stack((samples, samples)))
        return pygame.sndarray.make_sound(samples)

    def play(self, event: MorseEvent) -> None:
        if not self.available:
            return
        key = sound_key(event)
        sound = self._sounds.get(key) if key else None
        if sound is None:
            return
        try:
            sound.play()
        except Exception as exc:
            self.available = False
            self.error = str(exc)
