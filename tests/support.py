"""Shared landmark fixtures for gesture tests."""

import numpy as np

from airmorse.gesture.fsm import GestureFSM
from airmorse.gesture.morse import CHAR_TO_MORSE, MorseEngine
from airmorse.gesture.pinch import INDEX_TIP, MIDDLE_TIP, RING_TIP, classify_pinch


def synthetic_hand(
    pinch_finger: int | None = None,
    pinch_dist: float = 0.10,
    other_dist: float = 0.55,
    scale: float = 1.0,
    distances: dict[int, float] | None = None,
) -> np.ndarray:
    points = np.zeros((21, 2), dtype=np.float64)
    points[0] = (0.0, 0.0)
    points[9] = (0.0, 0.2 * scale)
    points[4] = (0.1 * scale, 0.1 * scale)
    lref = 0.2 * scale
    for finger_id in (8, 12, 16, 20):
        if distances is not None and finger_id in distances:
            distance = distances[finger_id]
        elif finger_id == pinch_finger:
            distance = pinch_dist
        else:
            distance = other_dist
        points[finger_id, 0] = points[4, 0] + distance * lref
        points[finger_id, 1] = points[4, 1]
    return points


def drive_text(text: str, tau_commit: float = 0.8) -> MorseEngine:
    fsm = GestureFSM(tau_pinch=0.18, cooldown_s=0.15)
    engine = MorseEngine(tau_commit=tau_commit)
    clock = 0.0
    released = classify_pinch(synthetic_hand(None, 0.55, 0.55))

    def pinched(finger: int):
        return classify_pinch(synthetic_hand(finger, 0.10, 0.55))

    for character in text:
        if character == " ":
            fsm.update(released, clock)
            clock += 0.05
            finger = fsm.update(pinched(RING_TIP), clock)
            if finger != RING_TIP:
                raise AssertionError(f"space pinch missing at t={clock}")
            engine.on_finger(finger, clock)
            clock += 0.05
            fsm.update(released, clock)
            clock += 0.2
            continue
        for symbol in CHAR_TO_MORSE[character]:
            tip = INDEX_TIP if symbol == "." else MIDDLE_TIP
            fsm.update(released, clock)
            clock += 0.02
            finger = fsm.update(pinched(tip), clock)
            if finger != tip:
                raise AssertionError(f"{character} {symbol} missing at t={clock} state={fsm.state}")
            engine.on_finger(finger, clock)
            clock += 0.05
            fsm.update(released, clock)
            clock += 0.20
        clock += tau_commit
        engine.poll(clock)
        clock += 0.05
    return engine
