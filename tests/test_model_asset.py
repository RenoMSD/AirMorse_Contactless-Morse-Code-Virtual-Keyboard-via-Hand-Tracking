from airmorse.vision.model_asset import ensure_model


def test_existing_model_is_not_replaced(tmp_path):
    path = tmp_path / "hand_landmarker.task"
    payload = b"x" * 100_001
    path.write_bytes(payload)
    assert ensure_model(path) == path
    assert path.read_bytes() == payload
