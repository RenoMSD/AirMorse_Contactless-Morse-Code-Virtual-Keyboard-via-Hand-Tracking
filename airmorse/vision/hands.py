"""Pure landmark selection and the square crop used before MediaPipe."""

import numpy as np


def select_hand_points(hand_landmarks, handedness) -> np.ndarray | None:
    """Return xy for the hand with the highest handedness score."""
    best_score = None
    best_index = None
    best_points = None
    if not hand_landmarks:
        return None
    for index, hand in enumerate(hand_landmarks):
        if hand is None or len(hand) < 21:
            continue
        score = 0.0
        if handedness is not None and index < len(handedness) and handedness[index]:
            category = handedness[index][0]
            score = float(getattr(category, "score", 0.0) or 0.0)
        if (
            best_score is None
            or score > best_score
            or (score == best_score and best_index is not None and index < best_index)
        ):
            best_score = score
            best_index = index
            best_points = np.array(
                [(float(landmark.x), float(landmark.y)) for landmark in hand[:21]],
                dtype=np.float64,
            )
    return best_points


def letterbox_rgb(rgb: np.ndarray) -> tuple[np.ndarray, int, int, int]:
    """Pad a frame to a square so landmark x and y share one scale."""
    height, width = rgb.shape[:2]
    side = max(height, width)
    pad_x = (side - width) // 2
    pad_y = (side - height) // 2
    canvas = np.zeros((side, side, 3), dtype=rgb.dtype)
    canvas[pad_y : pad_y + height, pad_x : pad_x + width] = rgb
    return canvas, side, pad_x, pad_y


def landmarks_to_frame(
    points: np.ndarray,
    side: int,
    pad_x: int,
    pad_y: int,
    width: int,
    height: int,
) -> np.ndarray:
    """Map square-normalized landmarks back onto the original frame."""
    mapped = np.array(points, dtype=np.float64, copy=True)
    mapped[:, 0] = (points[:, 0] * side - pad_x) / width
    mapped[:, 1] = (points[:, 1] * side - pad_y) / height
    return mapped
