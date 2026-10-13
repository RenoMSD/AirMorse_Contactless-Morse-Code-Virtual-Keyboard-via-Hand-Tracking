"""Rising-edge pinch detector with hysteresis and a cooldown."""

from airmorse.gesture.pinch import COOLDOWN_S, RELEASE_RATIO, TAU_PINCH_DEFAULT, PinchResult

RELEASED = "RELEASED"
PINCHED = "PINCHED"


class GestureFSM:
    """Emit one finger id on the transition into a pinch, never while it is held."""

    def __init__(
        self,
        tau_pinch: float = TAU_PINCH_DEFAULT,
        cooldown_s: float = COOLDOWN_S,
    ) -> None:
        self.tau_pinch = tau_pinch
        self.cooldown_s = cooldown_s
        self.state = RELEASED
        self.active_finger: int | None = None
        self._last_emit_t: float | None = None

    def update(self, pinch: PinchResult | None, now: float) -> int | None:
        if self.state == PINCHED:
            distance = None
            if pinch is not None and self.active_finger is not None:
                distance = pinch.distances.get(self.active_finger)
            if distance is None or distance > self.tau_pinch * RELEASE_RATIO:
                self.state = RELEASED
                self.active_finger = None
            return None

        if pinch is None or pinch.finger is None:
            return None

        self.state = PINCHED
        self.active_finger = pinch.finger
        if self._last_emit_t is not None and (now - self._last_emit_t) < self.cooldown_s:
            return None
        self._last_emit_t = now
        return pinch.finger
