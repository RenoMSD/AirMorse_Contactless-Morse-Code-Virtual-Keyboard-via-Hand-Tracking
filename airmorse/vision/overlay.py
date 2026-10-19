"""Draw the hand skeleton on an RGB frame."""

import cv2
import numpy as np

from airmorse.gesture.pinch import ENTER, INDEX_TIP, MIDDLE_TIP, THUMB_TIP

# MediaPipe hand connections. Finger groups include the palm link so a pinch
# lights the whole digit.
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
)

FINGER_EDGES = {
    8: ((0, 5), (5, 6), (6, 7), (7, 8)),
    12: ((5, 9), (9, 10), (10, 11), (11, 12)),
    16: ((9, 13), (13, 14), (14, 15), (15, 16)),
    20: ((13, 17), (0, 17), (17, 18), (18, 19), (19, 20)),
}

WHITE = (245, 245, 245)
GREEN = (80, 220, 120)


def _pixel(points: np.ndarray, index: int, width: int, height: int) -> tuple[int, int]:
    x = int(round(float(points[index, 0]) * width))
    y = int(round(float(points[index, 1]) * height))
    return min(width - 1, max(0, x)), min(height - 1, max(0, y))


def draw_hand(frame_rgb: np.ndarray, points, highlight_finger: int | None) -> None:
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[0] < 21 or frame_rgb.size == 0:
        return
    height, width = frame_rgb.shape[:2]
    if width < 2 or height < 2:
        return

    def xy(index: int) -> tuple[int, int]:
        return _pixel(pts, index, width, height)

    for start, end in HAND_CONNECTIONS:
        cv2.line(frame_rgb, xy(start), xy(end), WHITE, 2, cv2.LINE_AA)
    if highlight_finger == ENTER:
        edges = FINGER_EDGES[INDEX_TIP] + FINGER_EDGES[MIDDLE_TIP]
        highlighted = {INDEX_TIP, MIDDLE_TIP}
    elif highlight_finger == THUMB_TIP:
        edges = ((1, 2), (2, 3), (3, 4))
        highlighted = {2, 3, THUMB_TIP}
    else:
        edges = FINGER_EDGES.get(highlight_finger if highlight_finger is not None else -1, ())
        highlighted = {highlight_finger} if highlight_finger is not None else set()
    for start, end in edges:
        cv2.line(frame_rgb, xy(start), xy(end), GREEN, 4, cv2.LINE_AA)
    for index in range(21):
        color = GREEN if index in highlighted else WHITE
        radius = 6 if index in highlighted else 3
        cv2.circle(frame_rgb, xy(index), radius, color, -1, cv2.LINE_AA)
