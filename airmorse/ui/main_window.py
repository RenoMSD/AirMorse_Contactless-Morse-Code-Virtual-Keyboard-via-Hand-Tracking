"""Desktop HUD: camera, keyboard, Morse chart, and calibration."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from airmorse.config import AppConfig, SharedSettings, config_path, load_config, save_config
from airmorse.gesture.morse import (
    CHAR_TO_MORSE,
    TAU_COMMIT_MAX,
    TAU_COMMIT_MIN,
    MorseEngine,
    MorseEvent,
)
from airmorse.gesture.pinch import (
    ENTER,
    INDEX_TIP,
    MIDDLE_TIP,
    PINKY_TIP,
    RING_TIP,
    TAU_PINCH_MAX,
    TAU_PINCH_MIN,
    TIP_IDS,
)
from airmorse.output.audio import AudioFeedback
from airmorse.output.injector import KeyInjector
from airmorse.ui.keyboard import KeyboardHud
from airmorse.vision.camera import CameraWorker
from airmorse.vision.model_asset import model_path

logger = logging.getLogger(__name__)

HINT_OFF = (
    "Ngón trỏ–cái: chấm. Ngón giữa–cái: gạch. Ngón áp út–cái: cách. Ngón út–cái: xóa. "
    "Ngón trỏ và ngón giữa cùng lúc: Enter. Một chữ được gửi sau khi bạn dừng."
)
HINT_ON = (
    "Đang gửi phím. Hãy bấm vào Notepad hoặc trình duyệt để cửa sổ đó được chọn. "
    "AirMorse không gõ vào chính nó."
)
AUDIO_OFF = "Tắt âm thanh. Cử chỉ vẫn được giải mã trên màn hình."
HINT_PAUSED = "Đang tạm dừng, chưa ghi chữ. Bật Ghi nhận chữ khi bạn muốn nhập."
FINGER_LABELS = {
    INDEX_TIP: "trỏ",
    MIDDLE_TIP: "giữa",
    RING_TIP: "áp út",
    PINKY_TIP: "út",
}

STYLESHEET = """
QMainWindow, QWidget {
    background: #121418;
    color: #e7ecf3;
    font-family: "Segoe UI";
    font-size: 13px;
}
QLabel#title { font-size: 20px; font-weight: 600; color: #f4f7fb; }
QLabel#muted, QLabel#hint, QLabel#camera { color: #93a0b5; }
QLabel#buffer {
    font-family: Consolas, "Courier New", monospace;
    font-size: 26px;
    color: #f0c14a;
}
QLabel#error { color: #ff8b8b; }
QLabel#preview {
    background: #0e1116;
    border: 1px solid #2c3544;
    border-radius: 8px;
    padding: 8px 10px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 18px;
    color: #f4f7fb;
}
QLabel#video { background: #050608; color: #93a0b5; }
QLabel#legend {
    color: #c5d0e0;
}
QSlider::groove:horizontal { height: 4px; background: #2c3340; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #3dd68c;
    width: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #6d7b90;
    background: #1b212b;
    border-radius: 3px;
}
QCheckBox::indicator:checked { background: #3dd68c; border-color: #3dd68c; }
QScrollArea { border: none; background: #121418; }
"""


def rgb_to_pixmap(rgb: np.ndarray) -> QPixmap:
    array = np.ascontiguousarray(rgb)
    height, width, _ = array.shape
    image = QImage(array.data, width, height, array.strides[0], QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def _cheat_sheet() -> QWidget:
    sheet = QWidget()
    grid = QGridLayout(sheet)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(2)
    characters = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    characters.extend(str(digit) for digit in range(10))
    row_count = (len(characters) + 1) // 2
    for index, character in enumerate(characters):
        label = QLabel(f"{character}   {CHAR_TO_MORSE[character]}")
        label.setFont(QFont("Consolas", 10))
        label.setStyleSheet("color: #d5dbe6; background: transparent;")
        grid.addWidget(label, index % row_count, index // row_count)
    sheet.setStyleSheet("background: #121418;")
    return sheet


def _format_distances(distances: dict[int, float], highlight: int | None) -> str:
    if not distances:
        return "Không thấy tay"
    parts = []
    for finger_id in TIP_IDS:
        if finger_id not in distances:
            continue
        marked = finger_id == highlight or (
            highlight == ENTER and finger_id in (INDEX_TIP, MIDDLE_TIP)
        )
        mark = " *" if marked else ""
        parts.append(f"{FINGER_LABELS[finger_id]} {distances[finger_id]:.2f}{mark}")
    return "  ".join(parts)


class MainWindow(QMainWindow):
    def __init__(self, start_camera: bool = True, config_file: Path | None = None) -> None:
        super().__init__()
        self._closing = False
        self._config_file = Path(config_file) if config_file else config_path()
        self._config = load_config(self._config_file)
        self._rgb = None

        self.setWindowTitle("AirMorse")
        self.resize(1180, 800)
        self.setStyleSheet(STYLESHEET)
        if self._config.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self.engine = MorseEngine(self._config.tau_commit, uppercase=self._config.uppercase)
        self.settings = SharedSettings(self._config)
        self.injector = KeyInjector(is_blocked=self._window_is_foreground)
        self.injector.enabled = self._config.inject_keys
        self.audio = AudioFeedback()

        self._build()
        self._refresh_hint()
        if not self.audio.available:
            self.camera_label.setText(AUDIO_OFF)

        self._commit_timer = QTimer(self)
        self._commit_timer.setInterval(50)
        self._commit_timer.timeout.connect(self._poll_commit)
        self._commit_timer.start()
        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(lambda: self.error_label.setText(""))

        self.worker = CameraWorker(self.settings, model_path(), self._config.camera_index)
        self.worker.frame_ready.connect(self._on_frame)
        if start_camera:
            self.worker.start()

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(10)
        self.video = QLabel("Đang mở camera…")
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setWordWrap(True)
        self.video.setMinimumSize(520, 390)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.keyboard = KeyboardHud()
        self.keyboard.set_uppercase(self._config.uppercase)
        self.preview = QLabel("Chữ đã giải mã hiện ở đây")
        self.preview.setObjectName("preview")
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(52)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        left.addWidget(self.video, stretch=1)
        left.addWidget(self.keyboard)
        left.addWidget(self.preview)

        right = QVBoxLayout()
        right.setSpacing(8)
        title = QLabel("AirMorse")
        title.setObjectName("title")
        subtitle = QLabel("Bàn phím Morse không chạm")
        subtitle.setObjectName("muted")
        self.capture_box = QCheckBox("Ghi nhận chữ")
        self.capture_box.setChecked(False)
        self.fps_label = QLabel("— khung/giây")
        self.fps_label.setObjectName("muted")
        self.buffer_label = QLabel("—")
        self.buffer_label.setObjectName("buffer")
        self.buffer_label.setMinimumHeight(36)
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        self.error_label.setMinimumHeight(18)
        self.distance_label = QLabel("Không thấy tay")
        self.distance_label.setObjectName("muted")
        self.distance_label.setWordWrap(True)
        legend = QLabel(
            "Ngón trỏ + ngón cái: chấm\n"
            "Ngón giữa + ngón cái: gạch\n"
            "Ngón trỏ + ngón giữa cùng lúc: Enter\n"
            "Ngón áp út + ngón cái: cách\n"
            "Ngón út + ngón cái: xóa"
        )
        legend.setObjectName("legend")

        self.pinch_value = QLabel(f"{self._config.tau_pinch:.2f}")
        self.pinch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pinch_slider.setRange(int(round(TAU_PINCH_MIN * 100)), int(round(TAU_PINCH_MAX * 100)))
        self.pinch_slider.setValue(int(round(self._config.tau_pinch * 100)))
        self.pinch_slider.setAccessibleName("Ngưỡng chụm")
        self.commit_value = QLabel(f"{self.engine.tau_commit:.2f} giây")
        self.commit_slider = QSlider(Qt.Orientation.Horizontal)
        self.commit_slider.setRange(int(round(TAU_COMMIT_MIN * 100)), int(round(TAU_COMMIT_MAX * 100)))
        self.commit_slider.setValue(int(round(self.engine.tau_commit * 100)))
        self.commit_slider.setAccessibleName("Thời gian chờ")

        self.case_box = QCheckBox("In hoa")
        self.case_box.setChecked(self._config.uppercase)
        self.inject_box = QCheckBox("Gửi phím vào cửa sổ đang chọn")
        self.inject_box.setChecked(self._config.inject_keys)
        self.top_box = QCheckBox("Ghim cửa sổ này lên trên")
        self.top_box.setChecked(self._config.always_on_top)
        self.hint = QLabel(HINT_OFF)
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        self.camera_label = QLabel("")
        self.camera_label.setObjectName("camera")
        self.camera_label.setWordWrap(True)

        chart_title = QLabel("Bảng mã Morse")
        chart_title.setObjectName("muted")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(_cheat_sheet())
        scroll.setMinimumHeight(160)

        right.addWidget(title)
        right.addWidget(subtitle)
        right.addWidget(self.capture_box)
        right.addWidget(self.fps_label)
        right.addWidget(self.buffer_label)
        right.addWidget(self.error_label)
        right.addWidget(self.distance_label)
        right.addWidget(legend)
        right.addLayout(self._labeled_row("Ngưỡng chụm", self.pinch_value))
        right.addWidget(self.pinch_slider)
        right.addLayout(self._labeled_row("Thời gian chờ", self.commit_value))
        right.addWidget(self.commit_slider)
        right.addWidget(self.case_box)
        right.addWidget(self.inject_box)
        right.addWidget(self.top_box)
        right.addWidget(self.hint)
        right.addWidget(self.camera_label)
        right.addWidget(chart_title)
        right.addWidget(scroll, stretch=1)

        side = QWidget()
        side.setLayout(right)
        side.setMinimumWidth(360)
        root.addLayout(left, stretch=3)
        root.addWidget(side, stretch=2)

        self.pinch_slider.valueChanged.connect(self._on_pinch_changed)
        self.commit_slider.valueChanged.connect(self._on_commit_changed)
        self.pinch_slider.sliderReleased.connect(self._save_config)
        self.commit_slider.sliderReleased.connect(self._save_config)
        self.capture_box.toggled.connect(self._on_capture)
        self.case_box.toggled.connect(self._on_case)
        self.inject_box.toggled.connect(self._on_inject)
        self.top_box.toggled.connect(self._on_top)

    def _labeled_row(self, caption: str, value: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        name = QLabel(caption)
        name.setObjectName("muted")
        value.setMinimumWidth(72)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(value)
        return row

    def _on_pinch_changed(self, value: int) -> None:
        tau = value / 100
        self.settings.set_tau_pinch(tau)
        self.pinch_value.setText(f"{self.settings.snapshot()[0]:.2f}")

    def _on_commit_changed(self, value: int) -> None:
        self.engine.tau_commit = value / 100
        self.commit_value.setText(f"{self.engine.tau_commit:.2f} giây")

    def _on_capture(self, checked: bool) -> None:
        if not checked:
            self.engine.cancel_pending()
            self.buffer_label.setText("—")
            self.error_label.setText("")
        self._refresh_hint()

    def _on_case(self, checked: bool) -> None:
        self.engine.uppercase = checked
        self.keyboard.set_uppercase(checked)
        self._save_config()

    def _on_inject(self, checked: bool) -> None:
        self.injector.enabled = checked
        self._refresh_hint()
        self._save_config()

    def _on_top(self, checked: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()
        self._save_config()

    def _refresh_hint(self) -> None:
        if not self.capture_box.isChecked():
            self.hint.setText(HINT_PAUSED)
            return
        self.hint.setText(HINT_ON if self.injector.enabled else HINT_OFF)

    def _ingest_finger(self, finger: int, stamp: float) -> None:
        if not self.capture_box.isChecked():
            return
        self._dispatch(self.engine.on_finger(finger, stamp))

    def _window_is_foreground(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            hwnd = int(self.winId())
            if hwnd == 0:
                return False
            foreground = int(ctypes.windll.user32.GetForegroundWindow())
        except (OSError, ValueError, AttributeError):
            return False
        return foreground == hwnd

    def _on_frame(self) -> None:
        packet = self.worker.frames.take()
        if packet is None or self._closing:
            return
        self._show_packet(packet)
        if not self.capture_box.isChecked():
            return
        for finger, stamp in packet.token_times:
            self._ingest_finger(finger, stamp)
        self._dispatch(self.engine.poll(time.monotonic()))

    def _poll_commit(self) -> None:
        if self._closing or not self.capture_box.isChecked():
            return
        self._dispatch(self.engine.poll(time.monotonic()))

    def _show_packet(self, packet) -> None:
        if packet.fps > 0:
            self.fps_label.setText(f"{packet.fps:.0f} khung/giây")
        self.distance_label.setText(_format_distances(packet.distances, packet.highlight_finger))
        if packet.message:
            self.camera_label.setText(packet.message)
        elif packet.camera_ok:
            note = "" if self.audio.available else AUDIO_OFF
            self.camera_label.setText(note)
        if packet.frame_rgb is None:
            if packet.message:
                self.video.setText(packet.message)
            return
        self.video.setText("")
        self._rgb = packet.frame_rgb
        self._update_video()

    def _update_video(self) -> None:
        if self._rgb is None or self.video.width() < 2 or self.video.height() < 2:
            return
        pixmap = rgb_to_pixmap(self._rgb)
        scaled = pixmap.scaled(
            self.video.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.video.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_video()

    def _dispatch(self, events: list[MorseEvent]) -> None:
        if not events:
            return
        blocked = False
        for event in events:
            self.audio.play(event)
            sent = self.injector.apply(event)
            if event.kind in {"char", "space", "backspace", "enter"} and self.injector.enabled and not sent:
                blocked = True
            if event.kind == "char":
                self.keyboard.flash(event.value)
                self.error_label.setText("")
            elif event.kind == "space":
                self.keyboard.flash(" ")
            elif event.kind == "enter":
                self.keyboard.flash("\n")
            elif event.kind == "error":
                self._show_error(event.value)
        self.preview.setText(self.engine.preview or "Chữ đã giải mã hiện ở đây")
        self.buffer_label.setText(self.engine.buffer or "—")
        if blocked:
            self.hint.setText("Hãy chọn Notepad hoặc trình duyệt. AirMorse không gõ vào chính nó.")

    def _show_error(self, sequence: str) -> None:
        self.error_label.setText(f"Chuỗi không hợp lệ {sequence}")
        self._error_timer.start(1200)

    def _save_config(self) -> None:
        tau, delta = self.settings.snapshot()
        try:
            save_config(
                self._config_file,
                AppConfig(
                    tau_pinch=tau,
                    delta=delta,
                    tau_commit=self.engine.tau_commit,
                    inject_keys=self.inject_box.isChecked(),
                    always_on_top=self.top_box.isChecked(),
                    uppercase=self.case_box.isChecked(),
                    camera_index=self._config.camera_index,
                ),
            )
        except OSError:
            logger.exception("could not save config")

    def closeEvent(self, event) -> None:
        self._closing = True
        self._save_config()
        self._commit_timer.stop()
        self._error_timer.stop()
        if self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(2000):
                self.worker.terminate()
                self.worker.wait(1000)
        event.accept()


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("AirMorse")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()
