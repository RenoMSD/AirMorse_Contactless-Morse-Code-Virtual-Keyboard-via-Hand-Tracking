"""Desktop Command Center Dashboard & Mini HUD Widget controller for AirMorse."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication, QImage, QKeySequence, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from airmorse.config import AppConfig, SharedSettings, config_path, load_config, save_config
from airmorse.gesture.morse import (
    CHAR_TO_MORSE,
    NEWLINE_CODE,
    TAU_COMMIT_MAX,
    TAU_COMMIT_MIN,
    MorseEngine,
    MorseEvent,
    format_morse_signal,
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
from airmorse.gesture.thumb import THUMB_DOWN, THUMB_UP
from airmorse.output.audio import AudioFeedback
from airmorse.output.injector import KeyInjector
from airmorse.ui.keyboard import KeyboardHud
from airmorse.ui.mini_widget import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_DASH,
    COLOR_DELETE,
    COLOR_DOT,
    COLOR_ENTER,
    COLOR_MUTED,
    COLOR_TEXT,
    CommitDelayBar,
    MiniWidget,
)
from airmorse.vision.camera import CameraWorker
from airmorse.vision.model_asset import model_path

logger = logging.getLogger(__name__)

HINT_OFF = (
    "Ngón trỏ–cái: chấm. Ngón giữa–cái: gạch. Ngón áp út–cái: cách. Ngón út–cái: xóa. "
    "Ngón trỏ và ngón giữa cùng lúc, hoặc chuỗi .-.- : xuống dòng. "
    "Một chữ được gửi sau khi bạn dừng."
)
HINT_ON = (
    "Đang gửi phím. Hãy bấm vào Notepad hoặc trình duyệt để cửa sổ đó được chọn. "
    "AirMorse không gõ vào chính nó."
)
AUDIO_OFF = "Tắt âm thanh. Cử chỉ vẫn được giải mã trên màn hình."
HINT_PAUSED = "Đang tạm dừng. Giơ ngón cái lên (👍 Like) để bật ghi nhận chữ."
FINGER_LABELS = {
    INDEX_TIP: "trỏ",
    MIDDLE_TIP: "giữa",
    RING_TIP: "áp út",
    PINKY_TIP: "út",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background: {COLOR_BG};
    color: {COLOR_TEXT};
    font-family: "Segoe UI";
    font-size: 13px;
}}
QFrame#card, QWidget#card {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}
QFrame#headerBar {{
    background: {COLOR_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}
QLabel {{
    background: transparent;
}}
QLabel#title {{
    font-size: 19px;
    font-weight: 700;
    color: {COLOR_TEXT};
}}
QLabel#sectionTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {COLOR_MUTED};
    letter-spacing: 0.5px;
}}
QLabel#muted, QLabel#hint, QLabel#camera {{
    color: {COLOR_MUTED};
    font-size: 12px;
}}
QLabel#fpsBadge {{
    background: {COLOR_BG};
    color: {COLOR_DOT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 3px 10px;
    font-family: Consolas, "Courier New", monospace;
    font-weight: 600;
    font-size: 12px;
}}
QLabel#buffer {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 16px;
    font-weight: 700;
    color: {COLOR_DOT};
}}
QLabel#overlaySignal {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 14px;
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QLabel#error {{
    color: {COLOR_DELETE};
    font-weight: 600;
    font-size: 12px;
}}
QLabel#preview {{
    background: transparent;
    border: none;
    padding: 4px 6px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 18px;
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QLabel#video {{
    background: #050608;
    color: {COLOR_MUTED};
    border-radius: 6px;
}}
QFrame#cameraOverlay {{
    background: rgba(14, 18, 26, 215);
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
}}
QPushButton#miniModeBtn, QPushButton#copyBtn {{
    background: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton#miniModeBtn:hover {{
    border-color: {COLOR_DOT};
    color: {COLOR_DOT};
}}
QPushButton#copyBtn:hover {{
    border-color: {COLOR_DASH};
    color: {COLOR_DASH};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {COLOR_BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {COLOR_DASH};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {COLOR_DASH};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QCheckBox {{
    color: {COLOR_TEXT};
    spacing: 6px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLOR_MUTED};
    background: {COLOR_BG};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background: {COLOR_DASH};
    border-color: {COLOR_DASH};
}}
"""


def rgb_to_pixmap(rgb: np.ndarray) -> QPixmap:
    array = np.ascontiguousarray(rgb)
    height, width, _ = array.shape
    image = QImage(array.data, width, height, array.strides[0], QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def _gesture_guide_card() -> QFrame:
    """Card 1 on Right Column: Compact Gesture Guide with Signal Palette colors."""
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)

    header = QLabel("1. HƯỚNG DẪN CỬ CHỈ")
    header.setObjectName("sectionTitle")
    layout.addWidget(header)

    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(10)
    grid.setVerticalSpacing(4)

    items = [
        ("[👍]", COLOR_DASH, "Like: Bật ghi nhận"),
        ("[👎]", COLOR_MUTED, "Dislike: Tắt ghi"),
        ("[·]", COLOR_DOT, "Trỏ: Chấm (Dot)"),
        ("[—]", COLOR_DASH, "Giữa: Gạch (Dash)"),
        ("[↲]", COLOR_ENTER, "Trỏ+Giữa: Xuống dòng"),
        ("[␣]", COLOR_ENTER, "Áp út: Dấu cách"),
        ("[⌫]", COLOR_DELETE, "Út: Xóa ký tự"),
        ("[.-.-]", COLOR_ENTER, "Chuỗi AA: Xuống dòng"),
    ]
    for idx, (badge, color, desc) in enumerate(items):
        r = idx // 2
        c = idx % 2
        lbl = QLabel(
            f"<span style='color:{color}; font-family:Consolas,monospace; font-weight:700;'>{badge}</span> "
            f"<span style='color:{COLOR_TEXT}; font-size:12px;'>{desc}</span>"
        )
        lbl.setTextFormat(Qt.TextFormat.RichText)
        grid.addWidget(lbl, r, c)

    layout.addLayout(grid)
    return card


def _cheat_sheet(columns: int = 4) -> QWidget:
    """4-column Morse code lookup grid (A-Z and 0-9) without vertical scrollbar."""
    sheet = QWidget()
    grid = QGridLayout(sheet)
    grid.setContentsMargins(0, 2, 0, 2)
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(3)

    characters = [chr(code) for code in range(ord("A"), ord("Z") + 1)]
    characters.extend(str(digit) for digit in range(10))
    row_count = (len(characters) + columns - 1) // columns  # 9 rows for 36 items across 4 columns

    font = QFont("Consolas", 10)
    for index, character in enumerate(characters):
        raw = CHAR_TO_MORSE[character]
        pretty = "".join("·" if s == "." else "—" for s in raw)
        label = QLabel(
            f"<b style='color:{COLOR_TEXT}'>{character}</b> "
            f"<span style='color:{COLOR_DOT}'>{pretty}</span>"
        )
        label.setFont(font)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setStyleSheet("background: transparent;")
        grid.addWidget(label, index % row_count, index // row_count)

    sheet.setStyleSheet("background: transparent;")
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


class _GlobalHotkeyBridge(QObject):
    """Thread-safe bridge from pynput GlobalHotKeys thread to the Qt GUI thread."""

    activated = pyqtSignal()


class MainWindow(QMainWindow):
    def __init__(self, start_camera: bool = True, config_file: Path | None = None) -> None:
        super().__init__()
        self._closing = False
        self._config_file = Path(config_file) if config_file else config_path()
        self._config = load_config(self._config_file)
        self._rgb: np.ndarray | None = None
        self._last_highlight: int | None = None
        self._global_hotkey_listener = None

        self.setWindowTitle("AirMorse")
        self.resize(1220, 800)
        self.setStyleSheet(STYLESHEET)
        if self._config.always_on_top:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self.engine = MorseEngine(self._config.tau_commit, uppercase=self._config.uppercase)
        self.settings = SharedSettings(self._config)
        self.injector = KeyInjector(is_blocked=self._window_is_foreground)
        self.injector.enabled = self._config.inject_keys
        self.audio = AudioFeedback()

        self.mini_widget = MiniWidget()
        self.mini_widget.expand_requested.connect(self.exit_mini_mode)
        self.mini_widget.capture_toggled.connect(self._on_mini_capture_toggled)

        self._build()
        self._setup_hotkeys(enable_os_listener=start_camera)
        self._refresh_hint()
        self._refresh_overlay()
        if not self.audio.available:
            self.camera_label.setText(AUDIO_OFF)

        self._commit_timer = QTimer(self)
        self._commit_timer.setInterval(40)
        self._commit_timer.timeout.connect(self._poll_commit)
        self._commit_timer.start()

        self._error_timer = QTimer(self)
        self._error_timer.setSingleShot(True)
        self._error_timer.timeout.connect(self._clear_error)

        self._copy_reset_timer = QTimer(self)
        self._copy_reset_timer.setSingleShot(True)
        self._copy_reset_timer.timeout.connect(lambda: self.copy_btn.setText("Copy"))

        self.worker = CameraWorker(self.settings, model_path(), self._config.camera_index)
        self.worker.frame_ready.connect(self._on_frame)
        if start_camera:
            self.worker.start()

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_v = QVBoxLayout(central)
        main_v.setContentsMargins(14, 12, 14, 14)
        main_v.setSpacing(12)

        # --- TOP HEADER BAR ---
        header_bar = QFrame()
        header_bar.setObjectName("headerBar")
        header_row = QHBoxLayout(header_bar)
        header_row.setContentsMargins(14, 8, 14, 8)
        header_row.setSpacing(12)

        title = QLabel("AirMorse")
        title.setObjectName("title")
        sep = QLabel("|")
        sep.setObjectName("muted")
        subtitle = QLabel("Bàn phím Morse không chạm")
        subtitle.setObjectName("muted")

        self.capture_box = QCheckBox("○ Ghi nhận: TẮT")
        self.capture_box.setChecked(False)
        self.capture_box.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_capture_box(False)

        self.fps_label = QLabel("— FPS")
        self.fps_label.setObjectName("fpsBadge")

        self.mini_mode_btn = QPushButton("⧉ Chế độ Thu gọn")
        self.mini_mode_btn.setObjectName("miniModeBtn")
        self.mini_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mini_mode_btn.setToolTip("Thu nhỏ thành Mini Widget góc màn hình (Ctrl+Shift+M)")
        self.mini_mode_btn.clicked.connect(self.enter_mini_mode)

        header_row.addWidget(title)
        header_row.addWidget(sep)
        header_row.addWidget(subtitle)
        header_row.addStretch(1)
        header_row.addWidget(self.capture_box)
        header_row.addWidget(self.fps_label)
        header_row.addWidget(self.mini_mode_btn)
        main_v.addWidget(header_bar)

        # --- 2-COLUMN BODY (6 : 4 RATIO) ---
        columns = QHBoxLayout()
        columns.setSpacing(14)

        # === LEFT COLUMN: TƯƠNG TÁC CHÍNH (60% -> stretch 6) ===
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # 1. KHUNG CAMERA (Tỷ lệ 16:9, bo góc 8px + Real-time Bottom Overlay)
        camera_card = QFrame()
        camera_card.setObjectName("card")
        camera_card_layout = QVBoxLayout(camera_card)
        camera_card_layout.setContentsMargins(10, 10, 10, 10)
        camera_card_layout.setSpacing(6)

        self.video = QLabel("Đang mở camera…")
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setWordWrap(True)
        self.video.setMinimumSize(520, 292)
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Real-time bottom overlay inside camera card
        self.camera_overlay = QFrame()
        self.camera_overlay.setObjectName("cameraOverlay")
        overlay_v = QVBoxLayout(self.camera_overlay)
        overlay_v.setContentsMargins(10, 6, 10, 6)
        overlay_v.setSpacing(4)

        overlay_top = QHBoxLayout()
        overlay_top.setContentsMargins(0, 0, 0, 0)
        overlay_top.setSpacing(10)

        self.overlay_signal_label = QLabel("Tín hiệu: — | Đang chờ: 0.00s")
        self.overlay_signal_label.setObjectName("overlaySignal")

        # Keep buffer_label and error_label for full test compatibility
        self.buffer_label = QLabel("—")
        self.buffer_label.setObjectName("buffer")
        self.buffer_label.setVisible(False)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        overlay_top.addWidget(self.overlay_signal_label)
        overlay_top.addStretch(1)
        overlay_top.addWidget(self.error_label)

        self.commit_bar = CommitDelayBar()

        overlay_v.addLayout(overlay_top)
        overlay_v.addWidget(self.commit_bar)

        camera_card_layout.addWidget(self.video, stretch=1)
        camera_card_layout.addWidget(self.camera_overlay)
        left_col.addWidget(camera_card, stretch=1)

        # 2. Ô HIỂN THỊ VĂN BẢN (Decoded Output Box - directly below Camera, above Keyboard!)
        output_card = QFrame()
        output_card.setObjectName("card")
        output_row = QHBoxLayout(output_card)
        output_row.setContentsMargins(12, 8, 12, 8)
        output_row.setSpacing(10)

        self.preview = QLabel("Chữ đã giải mã hiện ở đây")
        self.preview.setObjectName("preview")
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(42)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("copyBtn")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setFixedWidth(72)
        self.copy_btn.clicked.connect(self.copy_preview_text)

        output_row.addWidget(self.preview, stretch=1)
        output_row.addWidget(self.copy_btn)
        left_col.addWidget(output_card)

        # 3. BÀN PHÍM ẢO (Virtual Keyboard)
        kb_card = QFrame()
        kb_card.setObjectName("card")
        kb_layout = QVBoxLayout(kb_card)
        kb_layout.setContentsMargins(8, 6, 8, 6)
        self.keyboard = KeyboardHud()
        self.keyboard.set_uppercase(self._config.uppercase)
        kb_layout.addWidget(self.keyboard)
        left_col.addWidget(kb_card)

        # === RIGHT COLUMN: BẢNG TRA & CÀI ĐẶT (40% -> stretch 4) ===
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # 1. HƯỚNG DẪN CỬ CHỈ (Thẻ Card)
        self.legend_card = _gesture_guide_card()
        right_col.addWidget(self.legend_card)

        # 2. BẢNG MÃ MORSE (Lưới 4 cột - Không cần thanh cuộn dọc)
        morse_card = QFrame()
        morse_card.setObjectName("card")
        morse_layout = QVBoxLayout(morse_card)
        morse_layout.setContentsMargins(12, 10, 12, 10)
        morse_layout.setSpacing(4)

        chart_header = QHBoxLayout()
        chart_title = QLabel("2. BẢNG MÃ MORSE (4 CỘT)")
        chart_title.setObjectName("sectionTitle")
        newline_badge = QLabel(
            f"<span style='color:{COLOR_MUTED}'>Xuống dòng:</span> "
            f"<b style='color:{COLOR_ENTER}'>· — · —</b>"
        )
        newline_badge.setTextFormat(Qt.TextFormat.RichText)
        newline_badge.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        chart_header.addWidget(chart_title)
        chart_header.addStretch(1)
        chart_header.addWidget(newline_badge)

        morse_layout.addLayout(chart_header)
        morse_layout.addWidget(_cheat_sheet(columns=4), stretch=1)
        right_col.addWidget(morse_card, stretch=1)

        # 3. CÀI ĐẶT & THIẾT LẬP (Thẻ Card)
        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(12, 10, 12, 10)
        settings_layout.setSpacing(6)

        settings_title = QLabel("3. CÀI ĐẶT & THIẾT LẬP")
        settings_title.setObjectName("sectionTitle")
        settings_layout.addWidget(settings_title)

        self.pinch_value = QLabel(f"{self._config.tau_pinch:.2f}")
        self.pinch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pinch_slider.setRange(int(round(TAU_PINCH_MIN * 100)), int(round(TAU_PINCH_MAX * 100)))
        self.pinch_slider.setValue(int(round(self._config.tau_pinch * 100)))
        self.pinch_slider.setAccessibleName("Ngưỡng chụm")

        self.commit_value = QLabel(f"{self.engine.tau_commit:.2f}s")
        self.commit_slider = QSlider(Qt.Orientation.Horizontal)
        self.commit_slider.setRange(int(round(TAU_COMMIT_MIN * 100)), int(round(TAU_COMMIT_MAX * 100)))
        self.commit_slider.setValue(int(round(self.engine.tau_commit * 100)))
        self.commit_slider.setAccessibleName("Thời gian chờ")

        settings_layout.addLayout(self._slider_row("Ngưỡng chụm:", self.pinch_slider, self.pinch_value))
        settings_layout.addLayout(self._slider_row("Thời gian chờ:", self.commit_slider, self.commit_value))

        # Checkboxes row
        checks_grid = QGridLayout()
        checks_grid.setContentsMargins(0, 2, 0, 2)
        checks_grid.setHorizontalSpacing(12)
        checks_grid.setVerticalSpacing(4)

        self.case_box = QCheckBox("In hoa")
        self.case_box.setChecked(self._config.uppercase)
        self.top_box = QCheckBox("Ghim lên trên")
        self.top_box.setChecked(self._config.always_on_top)
        self.inject_box = QCheckBox("Gửi phím vào cửa sổ khác")
        self.inject_box.setChecked(self._config.inject_keys)

        checks_grid.addWidget(self.case_box, 0, 0)
        checks_grid.addWidget(self.top_box, 0, 1)
        checks_grid.addWidget(self.inject_box, 1, 0, 1, 2)
        settings_layout.addLayout(checks_grid)

        self.distance_label = QLabel("Không thấy tay")
        self.distance_label.setObjectName("muted")
        self.distance_label.setWordWrap(True)

        self.hint = QLabel(HINT_OFF)
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)

        self.camera_label = QLabel("")
        self.camera_label.setObjectName("camera")
        self.camera_label.setWordWrap(True)

        settings_layout.addWidget(self.distance_label)
        settings_layout.addWidget(self.hint)
        settings_layout.addWidget(self.camera_label)
        right_col.addWidget(settings_card)

        columns.addLayout(left_col, stretch=6)
        columns.addLayout(right_col, stretch=4)
        main_v.addLayout(columns, stretch=1)

        self.pinch_slider.valueChanged.connect(self._on_pinch_changed)
        self.commit_slider.valueChanged.connect(self._on_commit_changed)
        self.pinch_slider.sliderReleased.connect(self._save_config)
        self.commit_slider.sliderReleased.connect(self._save_config)
        self.capture_box.toggled.connect(self._on_capture)
        self.case_box.toggled.connect(self._on_case)
        self.inject_box.toggled.connect(self._on_inject)
        self.top_box.toggled.connect(self._on_top)

    def _slider_row(self, caption: str, slider: QSlider, value: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        name = QLabel(caption)
        name.setObjectName("muted")
        name.setFixedWidth(96)
        value.setFixedWidth(48)
        value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value.setStyleSheet(f"color: {COLOR_DASH}; font-family: Consolas, monospace; font-weight: 600;")
        row.addWidget(name)
        row.addWidget(slider, stretch=1)
        row.addWidget(value)
        return row

    def _style_capture_box(self, checked: bool) -> None:
        if checked:
            self.capture_box.setText("● Ghi nhận: BẬT")
            self.capture_box.setStyleSheet(
                f"""
                QCheckBox {{
                    background: rgba(0, 230, 118, 0.14);
                    color: {COLOR_DASH};
                    border: 1px solid {COLOR_DASH};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-weight: 700;
                }}
                QCheckBox::indicator {{ width: 0px; height: 0px; border: none; }}
                """
            )
        else:
            self.capture_box.setText("○ Ghi nhận: TẮT")
            self.capture_box.setStyleSheet(
                f"""
                QCheckBox {{
                    background: {COLOR_BG};
                    color: {COLOR_MUTED};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-weight: 600;
                }}
                QCheckBox::indicator {{ width: 0px; height: 0px; border: none; }}
                """
            )

    def _setup_hotkeys(self, enable_os_listener: bool = False) -> None:
        """Bind Ctrl+Shift+M both in Qt windows and optionally via OS GlobalHotKeys."""
        self._shortcut_main = QShortcut(QKeySequence("Ctrl+Shift+M"), self)
        self._shortcut_main.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut_main.activated.connect(self.toggle_mini_mode)

        self._shortcut_mini = QShortcut(QKeySequence("Ctrl+Shift+M"), self.mini_widget)
        self._shortcut_mini.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._shortcut_mini.activated.connect(self.toggle_mini_mode)

        self._hotkey_bridge = _GlobalHotkeyBridge(self)
        self._hotkey_bridge.activated.connect(self.toggle_mini_mode)

        if enable_os_listener:
            try:
                from pynput.keyboard import GlobalHotKeys

                self._global_hotkey_listener = GlobalHotKeys(
                    {"<ctrl>+<shift>+m": self._hotkey_bridge.activated.emit}
                )
                self._global_hotkey_listener.daemon = True
                self._global_hotkey_listener.start()
            except Exception:
                logger.debug("OS global hotkey listener unavailable", exc_info=True)

    @property
    def is_mini_mode(self) -> bool:
        return self.mini_widget.isVisible()

    def toggle_mini_mode(self) -> None:
        if self.is_mini_mode:
            self.exit_mini_mode()
        else:
            self.enter_mini_mode()

    def enter_mini_mode(self) -> None:
        """Collapse Full Dashboard into the floating Mini Widget at the screen corner."""
        self.mini_widget.set_capture_state(self.capture_box.isChecked())
        self.mini_widget.update_decoded_text(self.engine.preview)
        self._refresh_overlay()
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            # Default position: bottom-right corner with 12px padding
            x = avail.right() + 1 - self.mini_widget.width() - 12
            y = avail.bottom() + 1 - self.mini_widget.height() - 12
            self.mini_widget.move(x, y)
        self.hide()
        self.mini_widget.show()

    def exit_mini_mode(self) -> None:
        """Expand back to the Full Dashboard."""
        self.mini_widget.hide()
        self.show()
        self.raise_()

    def _on_mini_capture_toggled(self, checked: bool) -> None:
        self.capture_box.setChecked(checked)

    def copy_preview_text(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.engine.preview)
        self.copy_btn.setText("Đã chép")
        self._copy_reset_timer.start(1000)

    def _on_pinch_changed(self, value: int) -> None:
        tau = value / 100
        self.settings.set_tau_pinch(tau)
        self.pinch_value.setText(f"{self.settings.snapshot()[0]:.2f}")

    def _on_commit_changed(self, value: int) -> None:
        self.engine.tau_commit = value / 100
        self.commit_value.setText(f"{self.engine.tau_commit:.2f}s")

    def _on_capture(self, checked: bool) -> None:
        self._style_capture_box(checked)
        self.mini_widget.set_capture_state(checked)
        if not checked:
            self.engine.cancel_pending()
            self.buffer_label.setText("—")
            self.error_label.setText("")
        self._refresh_hint()
        self._refresh_overlay()

    def _on_case(self, checked: bool) -> None:
        self.engine.uppercase = checked
        self.keyboard.set_uppercase(checked)
        self._refresh_overlay()
        self._save_config()

    def _on_inject(self, checked: bool) -> None:
        self.injector.enabled = checked
        self._refresh_hint()
        self._save_config()

    def _on_top(self, checked: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        if not self.is_mini_mode:
            self.show()
        self._save_config()

    def _refresh_hint(self) -> None:
        if not self.capture_box.isChecked():
            self.hint.setText(HINT_PAUSED)
            return
        self.hint.setText(HINT_ON if self.injector.enabled else HINT_OFF)

    def _refresh_overlay(self, now: float | None = None) -> None:
        if now is None:
            now = time.monotonic()
        buf = self.engine.buffer
        self.buffer_label.setText(buf or "—")
        remaining, ratio = self.engine.commit_progress(now)
        pending = self.engine.pending_char()
        if buf:
            pretty = format_morse_signal(buf)
            self.overlay_signal_label.setText(
                f"Tín hiệu: {pretty}  (Ký tự: {pending}) | Đang chờ: {remaining:.2f}s"
            )
            bar_color = COLOR_DASH if buf.endswith("-") else COLOR_DOT
            self.commit_bar.set_progress(ratio, bar_color)
        else:
            self.overlay_signal_label.setText(
                f"Tín hiệu: — | Đang chờ: {self.engine.tau_commit:.2f}s"
            )
            self.commit_bar.set_progress(0.0, COLOR_DOT)
        self.mini_widget.update_signal(buf, pending, remaining, ratio)

    def _clear_error(self) -> None:
        self.error_label.setText("")

    def _handle_tokens(self, token_times: list[tuple[int, float]]) -> None:
        for finger, _stamp in token_times:
            if finger == THUMB_UP:
                self.capture_box.setChecked(True)
                self.mini_widget.flash_edge(COLOR_DASH)
                return
            if finger == THUMB_DOWN:
                self.capture_box.setChecked(False)
                self.mini_widget.flash_edge(COLOR_DELETE)
                return
        if not self.capture_box.isChecked():
            return
        for finger, stamp in token_times:
            self._ingest_finger(finger, stamp)
        now = time.monotonic()
        self._dispatch(self.engine.poll(now))
        self._refresh_overlay(now)

    def _ingest_finger(self, finger: int, stamp: float) -> None:
        if not self.capture_box.isChecked():
            return
        self._dispatch(self.engine.on_finger(finger, stamp))
        self._refresh_overlay(stamp)

    def _window_is_foreground(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            foreground = int(ctypes.windll.user32.GetForegroundWindow())
            if foreground == 0:
                return False
            main_hwnd = int(self.winId()) if self.isVisible() else 0
            return main_hwnd != 0 and foreground == main_hwnd
        except (OSError, ValueError, AttributeError):
            return False

    def _on_frame(self) -> None:
        packet = self.worker.frames.take()
        if packet is None or self._closing:
            return
        self._show_packet(packet)
        self._handle_tokens(packet.token_times)

    def _poll_commit(self) -> None:
        if self._closing or not self.capture_box.isChecked():
            return
        now = time.monotonic()
        self._dispatch(self.engine.poll(now))
        self._refresh_overlay(now)

    def _show_packet(self, packet) -> None:
        if packet.fps > 0:
            self.fps_label.setText(f"{packet.fps:.0f} FPS")
        self._last_highlight = packet.highlight_finger
        self.distance_label.setText(_format_distances(packet.distances, packet.highlight_finger))
        self.mini_widget.update_pinch(packet.highlight_finger)
        self.mini_widget.set_hand_present(packet.hand_present)

        if packet.message:
            self.camera_label.setText(packet.message)
        elif packet.camera_ok:
            note = "" if self.audio.available else AUDIO_OFF
            self.camera_label.setText(note)
        if packet.frame_rgb is None:
            if packet.message:
                self.video.setText(packet.message)
                self.mini_widget.update_frame(None, packet.message)
            return
        self.video.setText("")
        self._rgb = packet.frame_rgb
        self._update_video()

    def _update_video(self) -> None:
        if self._rgb is None:
            return
        pixmap = rgb_to_pixmap(self._rgb)
        if self.video.width() >= 2 and self.video.height() >= 2:
            scaled = pixmap.scaled(
                self.video.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.video.setPixmap(scaled)
        self.mini_widget.update_frame(pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_video()

    def _dispatch(self, events: list[MorseEvent]) -> None:
        if not events:
            return
        blocked = False
        for event in events:
            self.audio.play(event)
            self.mini_widget.flash_edge_for_event(event.kind, event.value)
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
        self.mini_widget.update_decoded_text(self.engine.preview)
        self._refresh_overlay()
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
        self._copy_reset_timer.stop()
        if self._global_hotkey_listener is not None:
            try:
                self._global_hotkey_listener.stop()
            except Exception:
                pass
            self._global_hotkey_listener = None
        self.mini_widget.close()
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
