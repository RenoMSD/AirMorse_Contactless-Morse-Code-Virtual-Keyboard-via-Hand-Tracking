"""Thumbs-up starts capture. Thumbs-down stops it."""

import numpy as np

WRIST = 0
THUMB_MCP = 2
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_TIP = 12
RING_MCP = 13
RING_TIP = 16
PINKY_MCP = 17
PINKY_TIP = 20

# Not landmarks. The camera thread emits these once a pose has been held.
THUMB_UP = -2
THUMB_DOWN = -3

HOLD_S = 0.35
CURLED_FINGERS = (
    (INDEX_TIP, INDEX_MCP),
    (MIDDLE_TIP, MIDDLE_MCP),
    (RING_TIP, RING_MCP),
    (PINKY_TIP, PINKY_MCP),
)


def classify_thumb(points) -> int | None:
    """Return a like or an upside-down like when the other fingers are folded."""
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[0] < 21 or pts.shape[1] < 2:
        return None
    wrist = pts[WRIST, :2]
    middle_mcp = pts[MIDDLE_MCP, :2]
    scale = float(np.linalg.norm(middle_mcp - wrist))
    if not np.isfinite(scale) or scale < 1e-6:
        return None

    def span(start: int, end: int) -> float:
        return float(np.linalg.norm(pts[end, :2] - pts[start, :2]))

    for tip, knuckle in CURLED_FINGERS:
        if span(knuckle, tip) > 0.85 * scale:
            return None
    if span(INDEX_MCP, THUMB_TIP) < 0.55 * scale:
        return None
    if span(THUMB_MCP, THUMB_TIP) < 0.45 * scale:
        return None

    vertical = (float(pts[THUMB_TIP, 1]) - float(wrist[1])) / scale
    above_fist = all(float(pts[THUMB_TIP, 1]) < float(pts[tip, 1]) for tip, _ in CURLED_FINGERS)
    below_fist = all(float(pts[THUMB_TIP, 1]) > float(pts[tip, 1]) for tip, _ in CURLED_FINGERS)
    if vertical <= -0.70 and above_fist:
        return THUMB_UP
    if vertical >= 0.70 and below_fist:
        return THUMB_DOWN
    return None


class ThumbGesture:
    """Emit one pose after it stays still, then wait until the hand leaves it."""

    def __init__(self, hold_s: float = HOLD_S) -> None:
        self.hold_s = hold_s
        self.pose: int | None = None
        self._since: float | None = None
        self._emitted = False

    def update(self, pose: int | None, now: float) -> int | None:
        if pose != self.pose:
            self.pose = pose
            self._since = now if pose is not None else None
            self._emitted = False
            return None
        if pose is None or self._since is None or self._emitted:
            return None
        if now - self._since < self.hold_s:
            return None
        self._emitted = True
        return pose
