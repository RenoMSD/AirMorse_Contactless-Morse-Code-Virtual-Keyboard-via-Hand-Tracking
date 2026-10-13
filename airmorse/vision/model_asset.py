"""Locate and download the MediaPipe hand landmarker file."""

import urllib.request
from pathlib import Path

from airmorse.paths import project_root

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MIN_MODEL_BYTES = 100_000


def model_path() -> Path:
    return project_root() / "models" / "hand_landmarker.task"


def ensure_model(path: Path, timeout: float = 60.0) -> Path:
    if path.is_file() and path.stat().st_size > MIN_MODEL_BYTES:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "AirMorse/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            temporary.write_bytes(response.read())
        if temporary.stat().st_size < MIN_MODEL_BYTES:
            raise OSError("downloaded hand landmarker model is incomplete")
        temporary.replace(path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
    return path
