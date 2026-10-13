"""Latest camera packet, with pinch tokens kept when frames are coalesced."""

from dataclasses import dataclass, field
import threading


@dataclass
class FramePacket:
    frame_rgb: object | None = None
    fps: float = 0.0
    token_times: list[tuple[int, float]] = field(default_factory=list)
    hand_present: bool = False
    camera_ok: bool = False
    message: str = ""
    distances: dict[int, float] = field(default_factory=dict)
    highlight_finger: int | None = None

    def with_tokens(self, token_times: list[tuple[int, float]]) -> "FramePacket":
        return FramePacket(
            frame_rgb=self.frame_rgb,
            fps=self.fps,
            token_times=list(token_times),
            hand_present=self.hand_present,
            camera_ok=self.camera_ok,
            message=self.message,
            distances=dict(self.distances),
            highlight_finger=self.highlight_finger,
        )


class LatestFrame:
    """Keep the newest frame and append gesture tokens that have not been taken."""

    def __init__(self, limit: int = 32) -> None:
        self._lock = threading.Lock()
        self._latest: FramePacket | None = None
        self._emit_queued = False
        self._limit = limit

    def publish(self, packet: FramePacket) -> bool:
        should_emit = False
        with self._lock:
            if self._latest is not None and self._latest.token_times:
                merged = [*self._latest.token_times, *packet.token_times][-self._limit :]
                packet = packet.with_tokens(merged)
            self._latest = packet
            if not self._emit_queued:
                self._emit_queued = True
                should_emit = True
        return should_emit

    def take(self) -> FramePacket | None:
        with self._lock:
            packet = self._latest
            self._latest = None
            self._emit_queued = False
        return packet
