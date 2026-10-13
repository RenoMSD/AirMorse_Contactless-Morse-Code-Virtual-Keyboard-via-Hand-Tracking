from airmorse.gesture.fsm import PINCHED, RELEASED, GestureFSM
from airmorse.gesture.pinch import classify_pinch
from tests.support import synthetic_hand


def _pinch(distance: float, finger: int = 8):
    return classify_pinch(synthetic_hand(finger, distance, 0.55))


def test_hold_emits_one_token():
    fsm = GestureFSM(tau_pinch=0.18, cooldown_s=0.15)
    held = _pinch(0.10)
    tokens = []
    clock = 0.0
    while clock <= 0.5:
        token = fsm.update(held, clock)
        if token is not None:
            tokens.append(token)
        clock += 1 / 30
    assert tokens == [8]
    assert fsm.state == PINCHED


def test_release_inside_hysteresis_does_not_retrigger():
    fsm = GestureFSM(tau_pinch=0.18, cooldown_s=0.15)
    assert fsm.update(_pinch(0.10), 0.0) == 8
    assert fsm.update(_pinch(0.20), 0.05) is None
    assert fsm.state == PINCHED
    assert fsm.update(_pinch(0.30), 0.10) is None
    assert fsm.state == RELEASED
    assert fsm.update(_pinch(0.10), 0.20) == 8


def test_cooldown_blocks_a_second_tap():
    fsm = GestureFSM(tau_pinch=0.18, cooldown_s=0.15)
    engaged = _pinch(0.10)
    released = _pinch(0.40)
    assert fsm.update(engaged, 0.00) == 8
    assert fsm.update(released, 0.05) is None
    assert fsm.state == RELEASED
    assert fsm.update(engaged, 0.10) is None
    assert fsm.state == PINCHED
    assert fsm.update(released, 0.12) is None
    assert fsm.update(engaged, 0.20) == 8


def test_lost_hand_releases_without_a_token():
    fsm = GestureFSM()
    assert fsm.update(_pinch(0.10), 0.0) == 8
    assert fsm.update(None, 0.4) is None
    assert fsm.state == RELEASED
