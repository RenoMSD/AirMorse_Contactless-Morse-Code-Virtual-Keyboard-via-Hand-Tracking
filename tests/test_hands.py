import numpy as np
import pytest

from airmorse.vision.hands import landmarks_to_frame, letterbox_rgb, select_hand_points


class _Landmark:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _Category:
    def __init__(self, score: float) -> None:
        self.score = score


def _hand(x: float):
    return [_Landmark(x, 0.2) for _ in range(21)]


def test_higher_score_wins():
    points = select_hand_points([_hand(0.2), _hand(0.8)], [[_Category(0.2)], [_Category(0.9)]])
    assert points is not None
    assert points[0, 0] == pytest.approx(0.8)


def test_tie_keeps_the_first_hand():
    points = select_hand_points([_hand(0.2), _hand(0.8)], [[_Category(0.5)], [_Category(0.5)]])
    assert points is not None
    assert points[0, 0] == pytest.approx(0.2)


def test_empty_and_incomplete_hands():
    assert select_hand_points([], []) is None
    assert select_hand_points([[_Landmark(0.1, 0.1)]], [[_Category(1.0)]]) is None


def test_incomplete_hand_is_skipped():
    points = select_hand_points(
        [[_Landmark(0.1, 0.1)], _hand(0.4)],
        [[_Category(0.99)], [_Category(0.4)]],
    )
    assert points is not None
    assert points[0, 0] == pytest.approx(0.4)


def test_letterbox_maps_the_original_frame():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    _square, side, pad_x, pad_y = letterbox_rgb(frame)
    assert side == 640
    assert pad_x == 0
    assert pad_y == 80
    center = landmarks_to_frame(np.array([[0.5, 0.5]]), side, pad_x, pad_y, 640, 480)
    top = landmarks_to_frame(np.array([[0.5, 80 / 640]]), side, pad_x, pad_y, 640, 480)
    assert center[0, 0] == pytest.approx(0.5)
    assert center[0, 1] == pytest.approx(0.5)
    assert top[0, 1] == pytest.approx(0.0)
