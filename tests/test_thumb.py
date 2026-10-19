import numpy as np

from airmorse.gesture.thumb import THUMB_DOWN, THUMB_UP, ThumbGesture, classify_thumb
from tests.support import synthetic_hand


def _like(direction: str) -> np.ndarray:
    points = np.zeros((21, 2), dtype=np.float64)
    points[0] = (0.50, 0.60)
    points[9] = (0.50, 0.40)
    points[5] = (0.42, 0.42)
    points[13] = (0.58, 0.42)
    points[17] = (0.64, 0.44)
    points[2] = (0.38, 0.52)
    points[8] = (0.44, 0.48)
    points[12] = (0.52, 0.48)
    points[16] = (0.58, 0.48)
    points[20] = (0.64, 0.48)
    points[4] = (0.36, 0.22) if direction == "up" else (0.36, 0.98)
    return points


def test_thumbs_up_and_down_are_distinct_from_an_open_hand():
    assert classify_thumb(_like("up")) == THUMB_UP
    assert classify_thumb(_like("down")) == THUMB_DOWN
    opened = _like("up")
    opened[8] = (0.20, 0.10)
    opened[12] = (0.50, 0.05)
    assert classify_thumb(opened) is None


def test_a_pinch_is_not_a_like():
    assert classify_thumb(synthetic_hand(8, 0.10, 0.55)) is None


def test_pose_must_be_held_and_does_not_repeat():
    gesture = ThumbGesture(hold_s=0.35)
    assert gesture.update(THUMB_UP, 0.00) is None
    assert gesture.update(THUMB_UP, 0.34) is None
    assert gesture.update(THUMB_UP, 0.35) == THUMB_UP
    assert gesture.update(THUMB_UP, 0.80) is None
    assert gesture.update(None, 1.00) is None
    assert gesture.update(THUMB_DOWN, 1.10) is None
    assert gesture.update(THUMB_DOWN, 1.50) == THUMB_DOWN
