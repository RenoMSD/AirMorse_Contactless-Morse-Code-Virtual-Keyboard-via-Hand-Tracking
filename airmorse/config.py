"""Thresholds and the small JSON file that remembers them."""

import json
import threading
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from airmorse.gesture.morse import TAU_COMMIT_DEFAULT, TAU_COMMIT_MAX, TAU_COMMIT_MIN
from airmorse.gesture.pinch import (
    DELTA_DEFAULT,
    DELTA_MAX,
    DELTA_MIN,
    TAU_PINCH_DEFAULT,
    TAU_PINCH_MAX,
    TAU_PINCH_MIN,
)
from airmorse.paths import project_root


def config_path() -> Path:
    return project_root() / "config.json"


def _finite_float(value, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return min(high, max(low, number))


@dataclass
class AppConfig:
    tau_pinch: float = TAU_PINCH_DEFAULT
    delta: float = DELTA_DEFAULT
    tau_commit: float = TAU_COMMIT_DEFAULT
    inject_keys: bool = False
    always_on_top: bool = False
    uppercase: bool = True
    camera_index: int = 0

    def clamped(self) -> "AppConfig":
        return AppConfig(
            tau_pinch=_finite_float(self.tau_pinch, TAU_PINCH_MIN, TAU_PINCH_MAX, TAU_PINCH_DEFAULT),
            delta=_finite_float(self.delta, DELTA_MIN, DELTA_MAX, DELTA_DEFAULT),
            tau_commit=_finite_float(self.tau_commit, TAU_COMMIT_MIN, TAU_COMMIT_MAX, TAU_COMMIT_DEFAULT),
            inject_keys=self.inject_keys if isinstance(self.inject_keys, bool) else False,
            always_on_top=self.always_on_top if isinstance(self.always_on_top, bool) else False,
            uppercase=self.uppercase if isinstance(self.uppercase, bool) else True,
            camera_index=max(0, int(self.camera_index)),
        )


def _coerce(kind, value, default):
    try:
        if kind is bool:
            return value if isinstance(value, bool) else default
        if kind is int:
            return int(value)
        if kind is float:
            return float(value)
    except (TypeError, ValueError):
        return default
    return default


def load_config(path: Path) -> AppConfig:
    defaults = AppConfig()
    if not path.exists():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
    values = {}
    for item in fields(AppConfig):
        if item.name not in raw:
            continue
        values[item.name] = _coerce(item.type, raw[item.name], getattr(defaults, item.name))
    return AppConfig(**{**asdict(defaults), **values}).clamped()


def save_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(config.clamped()), indent=2)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(payload + "\n", encoding="utf-8")
    temporary.replace(path)


class SharedSettings:
    """Pinch thresholds shared by the UI thread and the camera thread."""

    def __init__(self, config: AppConfig) -> None:
        self._lock = threading.Lock()
        self._tau_pinch = config.tau_pinch
        self._delta = config.delta

    def set_tau_pinch(self, value: float) -> None:
        clamped = _finite_float(value, TAU_PINCH_MIN, TAU_PINCH_MAX, TAU_PINCH_DEFAULT)
        with self._lock:
            self._tau_pinch = clamped

    def snapshot(self) -> tuple[float, float]:
        with self._lock:
            return self._tau_pinch, self._delta
