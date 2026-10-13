import numpy as np

from airmorse.vision.overlay import draw_hand


def _index_line() -> np.ndarray:
    points = np.full((21, 2), 0.02)
    points[7] = (0.25, 0.5)
    points[8] = (0.75, 0.5)
    return points


def test_active_finger_is_green():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    draw_hand(frame, _index_line(), 8)
    row = frame[240]
    green = (row[:, 1] > row[:, 0] + 40) & (row[:, 1] > 80)
    assert np.any(green)


def test_idle_bones_are_white():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    draw_hand(frame, _index_line(), None)
    row = frame[240]
    white = (row[:, 0] > 180) & (row[:, 1] > 180) & (row[:, 2] > 180)
    assert np.any(white)
