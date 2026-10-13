import numpy as np
import pytest


def test_blank_frame_has_no_hand():
    pytest.importorskip("mediapipe")
    from airmorse.vision.model_asset import model_path
    from airmorse.vision.tracker import HandTracker

    path = model_path()
    if not path.is_file():
        pytest.skip("hand landmarker model is not downloaded")
    tracker = HandTracker(path)
    try:
        blank = np.zeros((64, 64, 3), dtype=np.uint8)
        assert tracker.detect(blank, 0) is None
        assert tracker.detect(blank, 33) is None
    finally:
        tracker.close()
