"""OS keystrokes for decoded Morse. Off until the user enables it."""

import logging
from collections.abc import Callable

from airmorse.gesture.morse import DECODED_CHARS, MorseEvent

logger = logging.getLogger(__name__)


def _typeable(value: str) -> str | None:
    """One Morse letter or digit. Letters keep the case the decoder chose."""
    if len(value) != 1:
        return None
    upper = value.upper()
    if upper not in DECODED_CHARS:
        return None
    if upper.isalpha():
        return value if value in (upper, upper.lower()) else None
    return upper


class PynputBackend:
    def __init__(self) -> None:
        from pynput.keyboard import Controller, Key

        self._keyboard = Controller()
        self._key = Key

    def type_text(self, text: str) -> None:
        self._keyboard.type(text)

    def tap_space(self) -> None:
        self._keyboard.press(self._key.space)
        self._keyboard.release(self._key.space)

    def tap_backspace(self) -> None:
        self._keyboard.press(self._key.backspace)
        self._keyboard.release(self._key.backspace)

    def tap_enter(self) -> None:
        self._keyboard.press(self._key.enter)
        self._keyboard.release(self._key.enter)


class KeyInjector:
    """Types A-Z, digits, space, enter, and backspace into the focused window."""

    def __init__(
        self,
        backend=None,
        is_blocked: Callable[[], bool] | None = None,
        backend_factory: Callable[[], object] | None = None,
    ) -> None:
        self.enabled = False
        self._backend_obj = backend
        self._is_blocked = is_blocked or (lambda: False)
        self._backend_factory = backend_factory or PynputBackend

    def apply(self, event: MorseEvent) -> bool:
        if not self.enabled:
            return False
        try:
            if self._is_blocked():
                return False
        except Exception:
            logger.exception("focus check failed")
            return False
        try:
            if event.kind == "char":
                text = _typeable(event.value)
                if text is None:
                    return False
                self._backend().type_text(text)
                return True
            if event.kind == "space":
                self._backend().tap_space()
                return True
            if event.kind == "backspace":
                self._backend().tap_backspace()
                return True
            if event.kind == "enter":
                self._backend().tap_enter()
                return True
        except Exception:
            logger.exception("key injection failed")
            return False
        return False

    def _backend(self):
        if self._backend_obj is None:
            self._backend_obj = self._backend_factory()
        return self._backend_obj
