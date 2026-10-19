"""International Morse lookup, buffer, and auto-commit."""

from dataclasses import dataclass

from airmorse.gesture.pinch import ENTER, INDEX_TIP, MIDDLE_TIP, PINKY_TIP, RING_TIP

TAU_COMMIT_DEFAULT = 0.8
TAU_COMMIT_MIN = 0.5
TAU_COMMIT_MAX = 1.5

# ITU codes for A-Z and 0-9. Punctuation is intentionally absent.
MORSE: dict[str, str] = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
}

CHAR_TO_MORSE = {character: code for code, character in MORSE.items()}
DECODED_CHARS = frozenset(CHAR_TO_MORSE)


@dataclass(frozen=True, slots=True)
class MorseEvent:
    """One decoder outcome.

    symbol: a dot or dash was stored.
    char: a letter or digit was committed.
    space: a space was committed.
    enter: a newline was committed.
    backspace: a committed character should be deleted.
    pop: an uncommitted dot or dash was removed.
    error: the buffer was not in the dictionary and was discarded.
    """

    kind: str
    value: str = ""


class MorseEngine:
    def __init__(self, tau_commit: float = TAU_COMMIT_DEFAULT, uppercase: bool = True) -> None:
        self.buffer = ""
        self.preview = ""
        self.uppercase = uppercase
        self._last_symbol_t: float | None = None
        self._tau_commit = TAU_COMMIT_DEFAULT
        self.tau_commit = tau_commit

    @property
    def tau_commit(self) -> float:
        return self._tau_commit

    @tau_commit.setter
    def tau_commit(self, value: float) -> None:
        self._tau_commit = min(TAU_COMMIT_MAX, max(TAU_COMMIT_MIN, float(value)))

    def on_finger(self, finger: int, now: float) -> list[MorseEvent]:
        if finger == INDEX_TIP:
            return self._push(".", now)
        if finger == MIDDLE_TIP:
            return self._push("-", now)
        if finger == RING_TIP:
            return self._space()
        if finger == PINKY_TIP:
            return self._backspace(now)
        if finger == ENTER:
            return self._enter()
        return []

    def poll(self, now: float) -> list[MorseEvent]:
        if not self.buffer or self._last_symbol_t is None:
            return []
        if now - self._last_symbol_t < self.tau_commit:
            return []
        return self._commit()

    def cancel_pending(self) -> None:
        """Drop an unfinished dot or dash sequence without committing it."""
        self.buffer = ""
        self._last_symbol_t = None

    def _push(self, symbol: str, now: float) -> list[MorseEvent]:
        self.buffer += symbol
        self._last_symbol_t = now
        return [MorseEvent("symbol", symbol)]

    def _commit(self) -> list[MorseEvent]:
        sequence = self.buffer
        self.buffer = ""
        self._last_symbol_t = None
        if not sequence:
            return []
        character = MORSE.get(sequence)
        if character is None:
            return [MorseEvent("error", sequence)]
        if character.isalpha() and not self.uppercase:
            character = character.lower()
        self.preview += character
        return [MorseEvent("char", character)]

    def _space(self) -> list[MorseEvent]:
        events: list[MorseEvent] = []
        if self.buffer:
            events.extend(self._commit())
            if events and events[-1].kind == "error":
                return events
        self.preview += " "
        events.append(MorseEvent("space", " "))
        return events

    def _enter(self) -> list[MorseEvent]:
        events: list[MorseEvent] = []
        if self.buffer:
            events.extend(self._commit())
            if events and events[-1].kind == "error":
                return events
        self.preview += "\n"
        events.append(MorseEvent("enter", "\n"))
        return events

    def _backspace(self, now: float) -> list[MorseEvent]:
        if self.buffer:
            removed = self.buffer[-1]
            self.buffer = self.buffer[:-1]
            self._last_symbol_t = now if self.buffer else None
            return [MorseEvent("pop", removed)]
        removed = self.preview[-1] if self.preview else ""
        if self.preview:
            self.preview = self.preview[:-1]
        return [MorseEvent("backspace", removed)]
