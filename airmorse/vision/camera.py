"""Webcam capture on a worker thread."""

from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from airmorse.config import SharedSettings
from airmorse.gesture.fsm import GestureFSM
from airmorse.gesture.pinch import classify_pinch
from airmorse.vision.frames import FramePacket, LatestFrame
from airmorse.vision.hands import landmarks_to_frame, letterbox_rgb
from airmorse.vision.model_asset import ensure_model
from airmorse.vision.overlay import draw_hand
from airmorse.vision.tracker import HandTracker

logger = logging.getLogger(__name__)

FRAME_WIDTH = 640
FRAME_HEIGHT = 480


def _backends() -> list[int]:
    if sys.platform == "win32":
        return [cv2.CAP_MSMF, cv2.CAP_DSHOW]
    return [cv2.CAP_ANY]


def open_capture(camera_index: int) -> cv2.VideoCapture | None:
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except Exception:
        pass
    backends = _backends()
    for backend in backends:
        capture = cv2.VideoCapture(camera_index, backend)
        if not capture.isOpened():
            capture.release()
            continue
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        capture.set(cv2.CAP_PROP_FPS, 30)
        try:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            logger.debug("camera buffer size was not accepted", exc_info=True)
        return capture
    return None


class CameraWorker(QThread):
    frame_ready = pyqtSignal()

    def __init__(self, settings: SharedSettings, model_file: Path, camera_index: int = 0) -> None:
        super().__init__()
        self.settings = settings
        self.model_file = Path(model_file)
        self.camera_index = camera_index
        self.frames = LatestFrame()
        self._stop = threading.Event()
        self._tracker_logged = False

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            self._loop()
        except Exception as exc:
            logger.exception("camera worker failed")
            self._emit(FramePacket(message=f"Vision stopped: {exc}"))

    def _emit(self, packet: FramePacket) -> None:
        if self.frames.publish(packet):
            self.frame_ready.emit()

    def _loop(self) -> None:
        self._emit(FramePacket(message="Loading hand model…"))
        if self._stop.is_set():
            return
        model = ensure_model(self.model_file)
        tracker = HandTracker(model)
        capture = None
        try:
            capture = open_capture(self.camera_index)
            if capture is None:
                self._emit(
                    FramePacket(
                        message="Could not open the webcam. Check Windows camera privacy settings."
                    )
                )
                while not self._stop.wait(1.0):
                    capture = open_capture(self.camera_index)
                    if capture is not None:
                        break
            if self._stop.is_set() or capture is None:
                return

            fsm = GestureFSM()
            misses = 0
            last_timestamp = -1
            previous_tick = None
            fps = 0.0
            while not self._stop.is_set():
                if capture is None:
                    self._emit(FramePacket(message="Waiting for the webcam…", fps=fps))
                    if self._stop.wait(1.0):
                        break
                    capture = open_capture(self.camera_index)
                    continue
                try:
                    ok, frame = capture.read()
                except cv2.error:
                    ok, frame = False, None
                if not ok or frame is None:
                    misses += 1
                    self._emit(FramePacket(message="Waiting for the webcam…", fps=fps))
                    if misses >= 15:
                        capture.release()
                        capture = open_capture(self.camera_index)
                        misses = 0
                    if self._stop.wait(0.1):
                        break
                    continue

                misses = 0
                # Mirror the preview so a raised right hand appears on the right.
                frame = cv2.flip(frame, 1)
                if frame.shape[1] != FRAME_WIDTH or frame.shape[0] != FRAME_HEIGHT:
                    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                now_perf = time.perf_counter()
                if previous_tick is None:
                    previous_tick = now_perf
                else:
                    elapsed = now_perf - previous_tick
                    previous_tick = now_perf
                    if elapsed > 0:
                        instant = 1.0 / elapsed
                        fps = instant if fps == 0 else (0.9 * fps + 0.1 * instant)

                timestamp = int(time.monotonic() * 1000)
                if timestamp <= last_timestamp:
                    timestamp = last_timestamp + 1
                last_timestamp = timestamp

                points = None
                message = ""
                try:
                    square, side, pad_x, pad_y = letterbox_rgb(rgb)
                    detected = tracker.detect(square, timestamp)
                    if detected is not None:
                        points = landmarks_to_frame(
                            detected, side, pad_x, pad_y, rgb.shape[1], rgb.shape[0]
                        )
                except Exception:
                    if not self._tracker_logged:
                        logger.exception("hand tracker failed")
                        self._tracker_logged = True
                    message = "Hand tracker error. Video is still running."

                tau, delta = self.settings.snapshot()
                fsm.tau_pinch = tau
                pinch = classify_pinch(points, tau, delta) if points is not None else None
                now = time.monotonic()
                token = fsm.update(pinch, now)
                if points is not None:
                    draw_hand(rgb, points, fsm.active_finger)
                self._emit(
                    FramePacket(
                        frame_rgb=np.ascontiguousarray(rgb).copy(),
                        fps=fps,
                        token_times=[(token, now)] if token is not None else [],
                        hand_present=points is not None,
                        camera_ok=True,
                        message=message,
                        distances=dict(pinch.distances) if pinch is not None else {},
                        highlight_finger=fsm.active_finger,
                    )
                )
        finally:
            if capture is not None:
                capture.release()
            tracker.close()
