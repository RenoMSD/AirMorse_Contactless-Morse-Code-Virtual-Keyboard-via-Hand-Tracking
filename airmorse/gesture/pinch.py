"""Scale-normalized pinch classification."""

from dataclasses import dataclass

import numpy as np

WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20
TIP_IDS = (INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)

TAU_PINCH_DEFAULT = 0.18
TAU_PINCH_MIN = 0.08
TAU_PINCH_MAX = 0.40
DELTA_DEFAULT = 0.08
DELTA_MIN = 0.02
DELTA_MAX = 0.20
RELEASE_RATIO = 1.4
COOLDOWN_S = 0.15

FINGER_NAMES = {
    INDEX_TIP: "index",
    MIDDLE_TIP: "middle",
    RING_TIP: "ring",
    PINKY_TIP: "pinky",
}


@dataclass(frozen=True)
class PinchResult:
    finger: int | None
    distances: dict[int, float]
    lref: float
    closest: int | None


def classify_pinch(
    points,
    tau_pinch: float = TAU_PINCH_DEFAULT,
    delta: float = DELTA_DEFAULT,
) -> PinchResult:
    """Choose the pinched fingertip.

    Lref is the palm scale ||P0 - P9||. Each fingertip distance is
    di = ||Pi - P4|| / Lref. The closest tip wins only when it is inside
    tau_pinch and at least delta closer than every other tip.
    """
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[0] < 21 or pts.shape[1] < 2:
        raise ValueError("expected 21 landmarks with x and y")

    wrist = pts[WRIST, :2]
    middle_mcp = pts[MIDDLE_MCP, :2]
    thumb = pts[THUMB_TIP, :2]
    lref = float(np.linalg.norm(wrist - middle_mcp))
    if not np.isfinite(lref) or lref < 1e-6:
        return PinchResult(None, {}, lref, None)

    distances: dict[int, float] = {}
    for finger_id in TIP_IDS:
        distance = float(np.linalg.norm(pts[finger_id, :2] - thumb) / lref)
        distances[finger_id] = distance
    if not all(np.isfinite(value) for value in distances.values()):
        return PinchResult(None, {}, lref, None)

    closest = min(distances, key=distances.get)
    winner = distances[closest]
    others = [value for finger_id, value in distances.items() if finger_id != closest]
    if not others:
        return PinchResult(None, distances, lref, closest)
    valid = winner < tau_pinch and winner + delta < min(others)
    return PinchResult(closest if valid else None, distances, lref, closest)
