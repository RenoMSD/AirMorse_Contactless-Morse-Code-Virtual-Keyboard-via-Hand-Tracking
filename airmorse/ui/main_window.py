"""Desktop HUD: camera, keyboard, Morse chart, and calibration."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
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
    FINGER_NAMES,
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
from airmorse.ui.mini import MiniView
from airmorse.vision.camera import CameraWorker
from airmorse.vision.model_asset import model_path

logger = logging.getLogger(__name__)

HINT_OFF = (
    "Index–thumb dot, middle–thumb dash, ring–thumb space, pinky–thumb delete. "
    "A letter is sent after you pause."
)
PREVIEW_PLACEHOLDER = "Decoded text appears here"
MINI_IDLE_OPACITY = 0.8
FULL_SIZE = QSize(1180, 800)
FINGER_ACTIONS = {
    INDEX_TIP: "Index + Thumb (Dot)",
    MIDDLE_TIP: "Middle + Thumb (Dash)",
    RING_TIP: "Ring + Thumb (Space)",
    PINKY_TIP: "Pinky + Thumb (Delete)",
}
HINT_ON = (
    "Key sending is on. Click Notepad or a browser so it stays focused. "
    "AirMorse will not type into itself."
)

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
    font-family: Consolas, "Courier New", monospace;
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
QPushButton, QToolButton {
    background: #232a36;
    border: 1px solid #3a4454;
    border-radius: 5px;
    padding: 3px 10px;
    color: #e8eef7;
}
QPushButton:hover, QToolButton:hover { border-color: #3dd68c; }
QToolButton:checked { background: #1f3a2c; border-color: #3dd68c; }
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
        return "No hand"
    parts = []
    for finger_id in TIP_IDS:
        if finger_id not in distances:
            continue
        mark = " *" if finger_id == highlight else ""
        parts.append(f"{FINGER_NAMES[finger_id]} {distances[finger_id]:.2f}{mark}")
    return "  ".join(parts)


class MainWindow(QMainWindow):
    def __init__(self, start_camera: bool = True, config_file: Path | None = None) -> None:
        super().__init__()
        self._closing = False
        self._config_file = Path(config_file) if config_file else config_path()
        self._config = load_config(self._config_file)
        self._rgb = None
        self._compact = False
        self._full_size = QSize(FULL_SIZE)

        self.setWindowTitle("AirMorse")
        self.resize(FULL_SIZE)
        self.setStyleSheet(STYLESHEET)
        if self._config.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self.engine = MorseEngine(self._config.tau_commit)
        self.settings = SharedSettings(self._config)
        self.injector = KeyInjector(is_blocked=self._window_is_foreground)
        self.injector.enabled = self._config.inject_keys
        self.audio = AudioFeedback()

        self._build()
        self._refresh_text()
        self._refresh_hint()
        if not self.audio.available:
            self.camera_label.setText("Audio is off. Gestures still decode on screen.")

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
        if self._config.compact_mode:
            self.set_compact(True)

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        pages = QVBoxLayout(central)
        pages.setContentsMargins(0, 0, 0, 0)
        self.full_page = QWidget()
        self.mini = MiniView()
        self.mini.setVisible(False)
        pages.addWidget(self.full_page)
        pages.addWidget(self.mini)

        root = QHBoxLayout(self.full_page)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(10)
        self.video = QLabel("Starting camera…")
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setWordWrap(True)
        self.video.setMinimumSize(520, 390)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.keyboard = KeyboardHud()
        self.preview = QLabel(PREVIEW_PLACEHOLDER)
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
        self.compact_button = QPushButton("⤡ Mini")
        self.compact_button.setToolTip("Switch to the compact view")
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.compact_button)
        subtitle = QLabel("Contactless Morse keyboard")
        subtitle.setObjectName("muted")
        self.fps_label = QLabel("— FPS")
        self.fps_label.setObjectName("muted")
        self.buffer_label = QLabel("—")
        self.buffer_label.setObjectName("buffer")
        self.buffer_label.setMinimumHeight(36)
        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        self.error_label.setMinimumHeight(18)
        self.distance_label = QLabel("No hand")
        self.distance_label.setObjectName("muted")
        self.distance_label.setWordWrap(True)
        legend = QLabel(
            "Index + thumb    dot\n"
            "Middle + thumb   dash\n"
            "Ring + thumb     space\n"
            "Pinky + thumb    delete"
        )
        legend.setObjectName("legend")

        self.pinch_value = QLabel(f"{self._config.tau_pinch:.2f}")
        self.pinch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pinch_slider.setRange(int(round(TAU_PINCH_MIN * 100)), int(round(TAU_PINCH_MAX * 100)))
        self.pinch_slider.setValue(int(round(self._config.tau_pinch * 100)))
        self.pinch_slider.setAccessibleName("Pinch threshold")
        self.commit_value = QLabel(f"{self.engine.tau_commit:.2f}s")
        self.commit_slider = QSlider(Qt.Orientation.Horizontal)
        self.commit_slider.setRange(int(round(TAU_COMMIT_MIN * 100)), int(round(TAU_COMMIT_MAX * 100)))
        self.commit_slider.setValue(int(round(self.engine.tau_commit * 100)))
        self.commit_slider.setAccessibleName("Commit delay")

        self.inject_box = QCheckBox("Send keys to the focused window")
        self.inject_box.setChecked(self._config.inject_keys)
        self.top_box = QCheckBox("Keep this window on top")
        self.top_box.setChecked(self._config.always_on_top)
        self.hint = QLabel(HINT_OFF)
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        self.camera_label = QLabel("")
        self.camera_label.setObjectName("camera")
        self.camera_label.setWordWrap(True)

        chart_title = QLabel("Morse chart")
        chart_title.setObjectName("muted")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(_cheat_sheet())
        scroll.setMinimumHeight(160)

        right.addLayout(title_row)
        right.addWidget(subtitle)
        right.addWidget(self.fps_label)
        right.addWidget(self.buffer_label)
        right.addWidget(self.error_label)
        right.addWidget(self.distance_label)
        right.addWidget(legend)
        right.addLayout(self._labeled_row("Pinch threshold", self.pinch_value))
        right.addWidget(self.pinch_slider)
        right.addLayout(self._labeled_row("Commit delay", self.commit_value))
        right.addWidget(self.commit_slider)
        right.addWidget(self.inject_box)
        right.addWidget(self.top_box)
        right.addWidget(self.hint)
        right.addWidget(self.camera_label)
        right.addWidget(chart_title)
        right.addWidget(scroll, stretch=1)

        side = QWidget()
        side.setLayout(right)
        side.setMinimumWidth(300)
        root.addLayout(left, stretch=3)
        root.addWidget(side, stretch=2)

        self.pinch_slider.valueChanged.connect(self._on_pinch_changed)
        self.commit_slider.valueChanged.connect(self._on_commit_changed)
        self.pinch_slider.sliderReleased.connect(self._save_config)
        self.commit_slider.sliderReleased.connect(self._save_config)
        self.inject_box.toggled.connect(self._on_inject)
        self.top_box.toggled.connect(self._on_top)

        mini = self.mini
        for source, mirror in ((self.pinch_slider, mini.pinch_slider), (self.commit_slider, mini.commit_slider)):
            mirror.setRange(source.minimum(), source.maximum())
            mirror.setValue(source.value())
            mirror.valueChanged.connect(source.setValue)
            source.valueChanged.connect(mirror.setValue)
            mirror.sliderReleased.connect(self._save_config)
        mini.pinch_value.setText(self.pinch_value.text())
        mini.commit_value.setText(self.commit_value.text())
        self.compact_button.clicked.connect(lambda: self.set_compact(True))
        mini.expand_button.clicked.connect(lambda: self.set_compact(False))
        mini.copy_button.clicked.connect(self._copy_text)
        mini.clear_button.clicked.connect(self._clear_text)
        mini.chart_toggle.clicked.connect(self._toggle_chart)
        mini.settings_button.toggled.connect(lambda _: self._fit_compact())

    @property
    def compact(self) -> bool:
        return self._compact

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        if self.isMaximized() or self.isFullScreen():
            self.showNormal()
        if compact:
            self._full_size = self.size()
        self._compact = compact
        self.full_page.setVisible(not compact)
        self.mini.setVisible(compact)
        self.setWindowTitle("AirMorse Mini" if compact else "AirMorse")
        self._apply_opacity(hovered=self.underMouse())
        if compact:
            self._fit_compact()
        else:
            self.resize(self._full_size)
        self._update_video()
        self._save_config()

    def _fit_compact(self) -> None:
        if not self._compact:
            return
        for layout in (self.mini.layout(), self.centralWidget().layout(), self.layout()):
            layout.activate()
        self.resize(self.minimumSizeHint())

    def _toggle_chart(self) -> None:
        self.mini.set_chart_open(not self.mini.chart_open)
        self._fit_compact()

    def _apply_opacity(self, hovered: bool) -> None:
        self.setWindowOpacity(1.0 if hovered or not self._compact else MINI_IDLE_OPACITY)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._apply_opacity(hovered=True)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._apply_opacity(hovered=False)

    def _copy_text(self) -> None:
        QApplication.clipboard().setText(self.engine.preview)

    def _clear_text(self) -> None:
        self.engine.preview = ""
        self._refresh_text()

    def _labeled_row(self, caption: str, value: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        name = QLabel(caption)
        name.setObjectName("muted")
        value.setMinimumWidth(52)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(value)
        return row

    def _on_pinch_changed(self, value: int) -> None:
        tau = value / 100
        self.settings.set_tau_pinch(tau)
        self.pinch_value.setText(f"{self.settings.snapshot()[0]:.2f}")
        self.mini.pinch_value.setText(self.pinch_value.text())

    def _on_commit_changed(self, value: int) -> None:
        self.engine.tau_commit = value / 100
        self.commit_value.setText(f"{self.engine.tau_commit:.2f}s")
        self.mini.commit_value.setText(self.commit_value.text())

    def _on_inject(self, checked: bool) -> None:
        self.injector.enabled = checked
        self._refresh_hint()
        self._save_config()

    def _on_top(self, checked: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()
        self._save_config()

    def _refresh_hint(self) -> None:
        self.hint.setText(HINT_ON if self.injector.enabled else HINT_OFF)

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
        for finger, stamp in packet.token_times:
            if finger in FINGER_ACTIONS:
                self.mini.pinch_label.setText(FINGER_ACTIONS[finger])
            self._dispatch(self.engine.on_finger(finger, stamp))
        self._dispatch(self.engine.poll(time.monotonic()))

    def _poll_commit(self) -> None:
        if self._closing:
            return
        now = time.monotonic()
        self._dispatch(self.engine.poll(now))
        self.mini.set_commit_countdown(self.engine.commit_remaining(now), self.engine.tau_commit)

    def _show_packet(self, packet) -> None:
        if packet.fps > 0:
            self.fps_label.setText(f"{packet.fps:.0f} FPS")
        self.mini.set_fps(packet.fps)
        if not packet.distances:
            self.mini.pinch_label.setText("No hand")
        elif self.mini.pinch_label.text() == "No hand":
            self.mini.pinch_label.setText("Hand ready")
        self.distance_label.setText(_format_distances(packet.distances, packet.highlight_finger))
        if packet.message:
            self.camera_label.setText(packet.message)
        elif packet.camera_ok:
            note = "" if self.audio.available else "Audio is off. Gestures still decode on screen."
            self.camera_label.setText(note)
        if packet.frame_rgb is None:
            if packet.message:
                self.video.setText(packet.message)
                self.mini.video.setText(packet.message)
            return
        self.video.setText("")
        self.mini.video.setText("")
        self._rgb = packet.frame_rgb
        self._update_video()

    def _update_video(self) -> None:
        video = self.mini.video if self._compact else self.video
        if self._rgb is None or video.width() < 2 or video.height() < 2:
            return
        pixmap = rgb_to_pixmap(self._rgb)
        scaled = pixmap.scaled(
            video.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        video.setPixmap(scaled)

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
            if event.kind in {"char", "space", "backspace"} and self.injector.enabled and not sent:
                blocked = True
            if event.kind == "char":
                self.keyboard.flash(event.value)
                self.error_label.setText("")
            elif event.kind == "space":
                self.keyboard.flash(" ")
            elif event.kind == "error":
                self._show_error(event.value)
        self._refresh_text()
        if blocked:
            self.hint.setText("Focus Notepad or a browser. AirMorse does not type into itself.")

    def _refresh_text(self) -> None:
        self.preview.setText(self.engine.preview or PREVIEW_PLACEHOLDER)
        self.buffer_label.setText(self.engine.buffer or "—")
        self.mini.output.setText(self.engine.preview)
        self.mini.set_buffer(self.engine.buffer)

    def _show_error(self, sequence: str) -> None:
        self.error_label.setText(f"Unknown sequence {sequence}")
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
                    camera_index=self._config.camera_index,
                    compact_mode=self._compact,
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
