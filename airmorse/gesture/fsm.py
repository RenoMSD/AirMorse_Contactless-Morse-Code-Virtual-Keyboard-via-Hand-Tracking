"""Rising-edge pinch detector with hysteresis and a cooldown."""

from airmorse.gesture.pinch import (
    COOLDOWN_S,
    ENTER,
    INDEX_TIP,
    MIDDLE_TIP,
    RELEASE_RATIO,
    TAU_PINCH_DEFAULT,
    PinchResult,
)

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
            if not self._gesture_held(pinch):
                leftover = self._leftover_finger(pinch) if self.active_finger == ENTER else None
                if leftover is not None:
                    self.active_finger = leftover
                else:
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

    def _limit(self) -> float:
        return self.tau_pinch * RELEASE_RATIO

    def _distance(self, pinch: PinchResult | None, finger: int | None) -> float | None:
        if pinch is None or finger is None:
            return None
        return pinch.distances.get(finger)

    def _gesture_held(self, pinch: PinchResult | None) -> bool:
        limit = self._limit()
        if self.active_finger == ENTER:
            index_distance = self._distance(pinch, INDEX_TIP)
            middle_distance = self._distance(pinch, MIDDLE_TIP)
            return (
                index_distance is not None
                and middle_distance is not None
                and index_distance <= limit
                and middle_distance <= limit
            )
        distance = self._distance(pinch, self.active_finger)
        return distance is not None and distance <= limit

    def _leftover_finger(self, pinch: PinchResult | None) -> int | None:
        if pinch is None:
            return None
        limit = self._limit()
        held = []
        for finger in (INDEX_TIP, MIDDLE_TIP):
            distance = pinch.distances.get(finger)
            if distance is not None and distance <= limit:
                held.append(finger)
        if len(held) == 1:
            return held[0]
        return None
