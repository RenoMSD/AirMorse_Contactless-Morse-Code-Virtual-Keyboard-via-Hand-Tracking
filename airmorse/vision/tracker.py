"""MediaPipe video hand tracker."""

from pathlib import Path

import numpy as np

from airmorse.vision.hands import select_hand_points


class HandTracker:
    """Video-mode hand landmarker. Create and use it on one thread."""

    def __init__(self, model_file: Path) -> None:
        import mediapipe as mp

        if not Path(model_file).is_file():
            raise FileNotFoundError(f"hand model not found: {model_file}")
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_file)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self._image_cls = mp.Image
        self._image_format = mp.ImageFormat.SRGB

    def detect(self, rgb: np.ndarray, timestamp_ms: int) -> np.ndarray | None:
        array = np.ascontiguousarray(rgb, dtype=np.uint8)
        image = self._image_cls(image_format=self._image_format, data=array)
        result = self._landmarker.detect_for_video(image, int(timestamp_ms))
        return select_hand_points(result.hand_landmarks, result.handedness)

    def close(self) -> None:
        landmarker = getattr(self, "_landmarker", None)
        if landmarker is not None:
            landmarker.close()
            self._landmarker = None
