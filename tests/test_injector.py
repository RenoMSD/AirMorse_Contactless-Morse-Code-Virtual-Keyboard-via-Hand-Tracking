from airmorse.gesture.morse import MorseEvent
from airmorse.output.injector import KeyInjector


class FakeKeys:
    def __init__(self) -> None:
        self.events = []

    def type_text(self, text: str) -> None:
        self.events.append(("type", text))

    def tap_space(self) -> None:
        self.events.append(("space",))

    def tap_backspace(self) -> None:
        self.events.append(("backspace",))

    def tap_enter(self) -> None:
        self.events.append(("enter",))


def test_disabled_injector_types_nothing():
    fake = FakeKeys()
    injector = KeyInjector(backend=fake)
    assert injector.apply(MorseEvent("char", "A")) is False
    assert fake.events == []


def test_enabled_injector_sends_only_commit_keys():
    fake = FakeKeys()
    injector = KeyInjector(backend=fake)
    injector.enabled = True
    assert injector.apply(MorseEvent("char", "A")) is True
    assert injector.apply(MorseEvent("space", " ")) is True
    assert injector.apply(MorseEvent("backspace", "")) is True
    assert injector.apply(MorseEvent("pop", ".")) is False
    assert injector.apply(MorseEvent("error", "......")) is False
    assert injector.apply(MorseEvent("symbol", ".")) is False
    assert injector.apply(MorseEvent("enter", "\n")) is True
    assert fake.events == [("type", "A"), ("space",), ("backspace",), ("enter",)]


def test_injector_refuses_to_type_into_itself():
    fake = FakeKeys()
    injector = KeyInjector(backend=fake, is_blocked=lambda: True)
    injector.enabled = True
    assert injector.apply(MorseEvent("char", "A")) is False
    assert fake.events == []


def test_injector_types_lowercase_letters_and_digits():
    fake = FakeKeys()
    injector = KeyInjector(backend=fake)
    injector.enabled = True
    assert injector.apply(MorseEvent("char", "a")) is True
    assert injector.apply(MorseEvent("char", "5")) is True
    assert fake.events == [("type", "a"), ("type", "5")]


def test_injector_rejects_characters_outside_the_morse_alphabet():
    fake = FakeKeys()
    injector = KeyInjector(backend=fake)
    injector.enabled = True
    assert injector.apply(MorseEvent("char", "Hello")) is False
    assert injector.apply(MorseEvent("char", "á")) is False
    assert injector.apply(MorseEvent("char", "")) is False
    assert fake.events == []
