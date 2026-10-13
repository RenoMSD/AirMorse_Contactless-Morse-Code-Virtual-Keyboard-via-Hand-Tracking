import numpy as np
import pytest

from airmorse.gesture.pinch import (
    COOLDOWN_S,
    DELTA_DEFAULT,
    RELEASE_RATIO,
    TAU_PINCH_DEFAULT,
    classify_pinch,
)
from tests.support import synthetic_hand


def test_spec_thresholds():
    assert TAU_PINCH_DEFAULT == 0.18
    assert DELTA_DEFAULT == 0.08
    assert RELEASE_RATIO == 1.4
    assert COOLDOWN_S == 0.15


def test_scale_invariance():
    near = classify_pinch(synthetic_hand(8, 0.12, 0.50, scale=1.0))
    far = classify_pinch(synthetic_hand(8, 0.12, 0.50, scale=3.0))
    assert near.finger == far.finger == 8
    assert near.distances[8] == pytest.approx(far.distances[8])
    assert near.distances[8] == pytest.approx(0.12)


def test_fist_is_rejected():
    result = classify_pinch(synthetic_hand(None, 0.10, 0.10))
    assert result.finger is None
    assert result.closest == 8


def test_single_finger_wins():
    result = classify_pinch(synthetic_hand(8, 0.10, 0.50))
    assert result.finger == 8


def test_coflexion_margin_rejects_near_neighbor():
    crowded = synthetic_hand(distances={8: 0.10, 12: 0.16, 16: 0.55, 20: 0.55})
    clear = synthetic_hand(distances={8: 0.10, 12: 0.20, 16: 0.55, 20: 0.55})
    assert classify_pinch(crowded).finger is None
    assert classify_pinch(clear).finger == 8


def test_threshold_is_strict():
    at_limit = classify_pinch(synthetic_hand(8, 0.18, 0.50), tau_pinch=0.18)
    under = classify_pinch(synthetic_hand(8, 0.179, 0.50), tau_pinch=0.18)
    assert at_limit.finger is None
    assert under.finger == 8


def test_higher_threshold_accepts_a_wider_pinch():
    points = synthetic_hand(8, 0.22, 0.50)
    assert classify_pinch(points, tau_pinch=0.18).finger is None
    assert classify_pinch(points, tau_pinch=0.25).finger == 8


def test_missing_palm_scale_is_not_a_pinch():
    result = classify_pinch(np.zeros((21, 2)))
    assert result.finger is None


def test_short_landmark_list_is_rejected():
    with pytest.raises(ValueError):
        classify_pinch(np.zeros((5, 2)))
