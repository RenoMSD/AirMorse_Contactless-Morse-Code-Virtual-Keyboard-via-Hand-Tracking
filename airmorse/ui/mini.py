"""Compact HUD: small camera, live buffer, decoded text, and a filtering Morse chart."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from airmorse.gesture.morse import CHAR_TO_MORSE, MORSE

MINI_VIDEO_SIZE = (120, 90)
CHART_COLUMNS = 5
CHART_CHARACTERS = [chr(code) for code in range(ord("A"), ord("Z") + 1)] + [str(digit) for digit in range(10)]

MINI_STYLESHEET = """
QLabel#miniTitle { font-size: 14px; font-weight: 600; color: #f4f7fb; }
QLabel#miniLive { color: #93a0b5; }
QLabel#miniLive[live="true"] { color: #3dd68c; }
QLabel#miniSection { color: #93a0b5; font-size: 11px; font-weight: 600; }
QLabel#miniBuffer {
    font-family: Consolas, "Courier New", monospace;
    font-size: 18px;
    color: #f0c14a;
}
QLabel#miniMatch {
    font-family: Consolas, "Courier New", monospace;
    font-size: 16px;
    font-weight: 600;
    color: #3dd68c;
    border: 1px solid #2c3544;
    border-radius: 4px;
    padding: 0 6px;
}
QLabel#miniOutput {
    background: #07090c;
    border: 1px solid #2c3544;
    border-radius: 6px;
    padding: 0 8px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 15px;
    color: #ffffff;
}
QLabel#miniFooter { color: #c5d0e0; }
QProgressBar {
    background: #1b212b;
    border: 1px solid #2c3544;
    border-radius: 3px;
    max-height: 8px;
}
QProgressBar::chunk { background: #f0c14a; border-radius: 2px; }
QLabel[cell="true"] {
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
    padding: 1px 4px;
    border: 1px solid transparent;
    border-radius: 3px;
    color: #d5dbe6;
}
QLabel[cell="true"][state="prefix"] { color: #f4f7fb; background: #1f2a3a; border-color: #3a4454; }
QLabel[cell="true"][state="dim"] { color: #3f4857; }
QLabel[cell="true"][state="match"] { color: #3dd68c; background: #13261c; border-color: #3dd68c; }
QLabel[cell="true"][state="match"][blink="true"] { border-color: #1b5e3e; }
"""


def pretty_code(code: str) -> str:
    return " ".join("·" if symbol == "." else "–" for symbol in code)


def chart_state(code: str, buffer: str) -> str:
    if not buffer:
        return "normal"
    if code == buffer:
        return "match"
    if code.startswith(buffer):
        return "prefix"
    return "dim"


def _restyle(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class MorseGrid(QWidget):
    """A–Z and 0–9 in five columns; cells reachable from the buffer light up, the exact match blinks."""

    def __init__(self) -> None:
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(2)
        rows = -(-len(CHART_CHARACTERS) // CHART_COLUMNS)
        self.cells: dict[str, QLabel] = {}
        for index, character in enumerate(CHART_CHARACTERS):
            cell = QLabel(f"{character} {CHAR_TO_MORSE[character].replace('.', '·')}")
            cell.setProperty("cell", True)
            cell.setProperty("state", "normal")
            grid.addWidget(cell, index % rows, index // rows)
            self.cells[character] = cell
        self._matched: QLabel | None = None
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(250)
        self._blink_timer.timeout.connect(self._blink)

    def set_buffer(self, buffer: str) -> None:
        self._matched = None
        for character, cell in self.cells.items():
            state = chart_state(CHAR_TO_MORSE[character], buffer)
            if state == "match":
                self._matched = cell
            if cell.property("state") != state or cell.property("blink"):
                cell.setProperty("state", state)
                cell.setProperty("blink", False)
                _restyle(cell)
        if self._matched is None:
            self._blink_timer.stop()
        elif not self._blink_timer.isActive():
            self._blink_timer.start()

    def state_of(self, character: str) -> str:
        return self.cells[character].property("state")

    def _blink(self) -> None:
        if self._matched is None:
            return
        self._matched.setProperty("blink", not self._matched.property("blink"))
        _restyle(self._matched)


class MiniView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(MINI_STYLESHEET)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("AirMorse Mini")
        title.setObjectName("miniTitle")
        self.live_label = QLabel("● Offline")
        self.live_label.setObjectName("miniLive")
        self.expand_button = QToolButton()
        self.expand_button.setText("⤢")
        self.expand_button.setToolTip("Open the full view")
        self.expand_button.setAccessibleName("Full view")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.live_label)
        header.addWidget(self.expand_button)

        self.video = QLabel("Starting camera…")
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setWordWrap(True)
        self.video.setFont(QFont("Segoe UI", 8))
        self.video.setFixedSize(*MINI_VIDEO_SIZE)

        self.buffer_label = QLabel("—")
        self.buffer_label.setObjectName("miniBuffer")
        self.match_label = QLabel("")
        self.match_label.setObjectName("miniMatch")
        self.match_label.setVisible(False)
        self.pinch_label = QLabel("No hand")
        self.pinch_label.setObjectName("muted")
        self.delay_bar = QProgressBar()
        self.delay_bar.setRange(0, 100)
        self.delay_bar.setValue(0)
        self.delay_bar.setTextVisible(False)
        self.delay_label = QLabel("")
        self.delay_label.setObjectName("muted")
        self.delay_label.setMinimumWidth(40)
        self.delay_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        signal = QGridLayout()
        signal.setHorizontalSpacing(8)
        signal.setVerticalSpacing(4)
        signal.addWidget(self._section("TÍN HIỆU REALTIME"), 0, 0, 1, 3)
        signal.addWidget(self._muted("Buffer"), 1, 0)
        buffer_row = QHBoxLayout()
        buffer_row.addWidget(self.buffer_label)
        buffer_row.addWidget(self.match_label)
        buffer_row.addStretch(1)
        signal.addLayout(buffer_row, 1, 1, 1, 2)
        signal.addWidget(self._muted("Pinch"), 2, 0)
        signal.addWidget(self.pinch_label, 2, 1, 1, 2)
        signal.addWidget(self._muted("Delay"), 3, 0)
        signal.addWidget(self.delay_bar, 3, 1)
        signal.addWidget(self.delay_label, 3, 2)
        signal.setColumnStretch(1, 1)

        top = QHBoxLayout()
        top.setSpacing(12)
        top.addWidget(self.video, alignment=Qt.AlignmentFlag.AlignTop)
        top.addLayout(signal, stretch=1)

        self.output = QLabel("")
        self.output.setObjectName("miniOutput")
        self.output.setFixedHeight(36)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.copy_button = QPushButton("Copy")
        self.clear_button = QPushButton("Del")
        self.clear_button.setToolTip("Clear the decoded text")
        output_row = QHBoxLayout()
        output_row.addWidget(self.output, stretch=1)
        output_row.addWidget(self.copy_button)
        output_row.addWidget(self.clear_button)

        self.chart_toggle = QToolButton()
        self.chart_toggle.setAccessibleName("Show or hide the Morse chart")
        chart_header = QHBoxLayout()
        chart_header.addWidget(self._section("BẢNG TRA CỨU MORSE (A – Z, 0 – 9)"))
        chart_header.addStretch(1)
        chart_header.addWidget(self.chart_toggle)
        self.grid = MorseGrid()

        self.pinch_value = QLabel("")
        self.pinch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pinch_slider.setAccessibleName("Pinch threshold")
        self.commit_value = QLabel("")
        self.commit_slider = QSlider(Qt.Orientation.Horizontal)
        self.commit_slider.setAccessibleName("Commit delay")
        self.settings_panel = QWidget()
        settings = QGridLayout(self.settings_panel)
        settings.setContentsMargins(0, 0, 0, 0)
        settings.addWidget(self._muted("Threshold"), 0, 0)
        settings.addWidget(self.pinch_slider, 0, 1)
        settings.addWidget(self.pinch_value, 0, 2)
        settings.addWidget(self._muted("Delay"), 1, 0)
        settings.addWidget(self.commit_slider, 1, 1)
        settings.addWidget(self.commit_value, 1, 2)
        settings.setColumnStretch(1, 1)
        self.settings_panel.setVisible(False)

        footer_legend = QLabel("[·] Trỏ   [–] Giữa   [␣] Áp út   [⌫] Út")
        footer_legend.setObjectName("miniFooter")
        self.settings_button = QToolButton()
        self.settings_button.setText("⚙")
        self.settings_button.setCheckable(True)
        self.settings_button.setToolTip("Threshold and delay")
        self.settings_button.setAccessibleName("Settings")
        footer = QHBoxLayout()
        footer.addWidget(footer_legend)
        footer.addStretch(1)
        footer.addWidget(self.settings_button)

        root.addLayout(header)
        root.addLayout(top)
        root.addLayout(output_row)
        root.addLayout(chart_header)
        root.addWidget(self.grid)
        root.addWidget(self.settings_panel)
        root.addLayout(footer)

        self.settings_button.toggled.connect(self.settings_panel.setVisible)
        self.set_chart_open(True)

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("miniSection")
        return label

    def _muted(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("muted")
        return label

    @property
    def chart_open(self) -> bool:
        return not self.grid.isHidden()

    def set_chart_open(self, open_: bool) -> None:
        self.grid.setVisible(open_)
        self.chart_toggle.setText("▲" if open_ else "▼")

    def set_buffer(self, buffer: str) -> None:
        self.buffer_label.setText(pretty_code(buffer) if buffer else "—")
        character = MORSE.get(buffer) if buffer else None
        self.match_label.setText(character or "")
        self.match_label.setVisible(character is not None)
        self.grid.set_buffer(buffer)

    def set_fps(self, fps: float) -> None:
        live = fps > 0
        self.live_label.setText(f"● Live: {fps:.0f} FPS" if live else "● Offline")
        if self.live_label.property("live") != live:
            self.live_label.setProperty("live", live)
            _restyle(self.live_label)

    def set_commit_countdown(self, remaining: float | None, tau_commit: float) -> None:
        if remaining is None:
            self.delay_bar.setValue(0)
            self.delay_label.setText(f"{tau_commit:.1f}s")
            return
        self.delay_bar.setValue(int(round(100 * remaining / tau_commit)))
        self.delay_label.setText(f"{remaining:.1f}s")
