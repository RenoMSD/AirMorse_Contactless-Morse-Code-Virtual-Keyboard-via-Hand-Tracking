from airmorse.gesture.morse import MORSE, TAU_COMMIT_DEFAULT, MorseEngine, MorseEvent
from airmorse.gesture.pinch import INDEX_TIP, MIDDLE_TIP, PINKY_TIP, RING_TIP


def test_commit_delay_matches_the_proposal():
    assert TAU_COMMIT_DEFAULT == 0.8


def test_dictionary_covers_letters_and_digits():
    assert set(MORSE.values()) == set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def test_every_code_roundtrips():
    for code, character in MORSE.items():
        engine = MorseEngine(tau_commit=0.5)
        clock = 0.0
        for symbol in code:
            finger = INDEX_TIP if symbol == "." else MIDDLE_TIP
            engine.on_finger(finger, clock)
            clock += 0.05
        events = engine.poll(clock + 0.5)
        assert events == [MorseEvent("char", character)]
        assert engine.preview == character
        assert engine.buffer == ""


def test_commit_waits_for_the_timeout():
    engine = MorseEngine(tau_commit=0.8)
    engine.on_finger(INDEX_TIP, 0.0)
    assert engine.poll(0.79) == []
    assert engine.buffer == "."
    assert engine.poll(0.80) == [MorseEvent("char", "E")]


def test_unknown_sequence_is_discarded():
    engine = MorseEngine(tau_commit=0.5)
    clock = 0.0
    for _ in range(6):
        engine.on_finger(INDEX_TIP, clock)
        clock += 0.05
    events = engine.poll(clock + 0.5)
    assert events == [MorseEvent("error", "......")]
    assert engine.preview == ""
    assert engine.buffer == ""


def test_space_commits_a_valid_buffer_then_inserts_a_space():
    engine = MorseEngine()
    engine.on_finger(INDEX_TIP, 0.0)
    events = engine.on_finger(RING_TIP, 0.1)
    assert events == [MorseEvent("char", "E"), MorseEvent("space", " ")]
    assert engine.preview == "E "


def test_space_on_an_invalid_buffer_does_not_insert_a_space():
    engine = MorseEngine()
    clock = 0.0
    for _ in range(6):
        engine.on_finger(INDEX_TIP, clock)
        clock += 0.05
    events = engine.on_finger(RING_TIP, clock)
    assert events == [MorseEvent("error", "......")]
    assert engine.preview == ""


def test_space_on_an_empty_buffer():
    engine = MorseEngine()
    assert engine.on_finger(RING_TIP, 0.0) == [MorseEvent("space", " ")]
    assert engine.preview == " "


def test_backspace_pops_the_latest_symbol_and_resets_the_timer():
    engine = MorseEngine(tau_commit=0.8)
    engine.on_finger(INDEX_TIP, 0.0)
    engine.on_finger(MIDDLE_TIP, 0.1)
    assert engine.on_finger(PINKY_TIP, 0.2) == [MorseEvent("pop", "-")]
    assert engine.buffer == "."
    assert engine.poll(0.99) == []
    assert engine.poll(1.0) == [MorseEvent("char", "E")]


def test_backspace_on_an_empty_buffer_deletes_preview_text():
    engine = MorseEngine()
    engine.preview = "AB"
    assert engine.on_finger(PINKY_TIP, 0.0) == [MorseEvent("backspace", "B")]
    assert engine.preview == "A"
    assert engine.on_finger(PINKY_TIP, 0.2) == [MorseEvent("backspace", "A")]
    assert engine.on_finger(PINKY_TIP, 0.4) == [MorseEvent("backspace", "")]
    assert engine.preview == ""


def test_clearing_the_buffer_cancels_commit():
    engine = MorseEngine(tau_commit=0.5)
    engine.on_finger(INDEX_TIP, 0.0)
    engine.on_finger(PINKY_TIP, 0.1)
    assert engine.buffer == ""
    assert engine.poll(5.0) == []


def test_commit_remaining_counts_down():
    engine = MorseEngine(tau_commit=0.8)
    assert engine.commit_remaining(0.0) is None
    engine.on_finger(INDEX_TIP, 1.0)
    assert abs(engine.commit_remaining(1.3) - 0.5) < 1e-9
    assert engine.commit_remaining(5.0) == 0.0
