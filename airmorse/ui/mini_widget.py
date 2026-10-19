"""Mini Floating HUD Widget with expandable Morse drawer, edge flash, snapping, and dynamic opacity."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from airmorse.gesture.morse import CHAR_TO_MORSE, format_morse_signal
from airmorse.gesture.pinch import ENTER, INDEX_TIP, MIDDLE_TIP, PINKY_TIP, RING_TIP, THUMB_TIP

# Cyber Minimalist / Sleek Dark Palette
COLOR_BG = "#0E121A"
COLOR_CARD = "#181E29"
COLOR_BORDER = "#263043"
COLOR_TEXT = "#FFFFFF"
COLOR_MUTED = "#8A99AD"

# Signal Palette
COLOR_DOT = "#00E5FF"     # Cyan neon (Index - Dot)
COLOR_DASH = "#00E676"    # Mint neon (Middle - Dash / Active)
COLOR_ENTER = "#7C4DFF"   # Purple (Enter / Space)
COLOR_DELETE = "#FF5252"  # Coral Red (Pinky - Delete / Error)

MINI_WIDTH = 340
MINI_HEIGHT_COLLAPSED = 160
MINI_HEIGHT_EXPANDED = 330
SNAP_MARGIN = 20

IDLE_OPACITY = 0.75
ACTIVE_OPACITY = 1.00

PINCH_DESCRIPTIONS: dict[int, tuple[str, str]] = {
    INDEX_TIP: ("Trỏ + Cái (Chấm)", COLOR_DOT),
    MIDDLE_TIP: ("Giữa + Cái (Gạch)", COLOR_DASH),
    RING_TIP: ("Áp út + Cái (Cách)", COLOR_ENTER),
    PINKY_TIP: ("Út + Cái (Xóa)", COLOR_DELETE),
    ENTER: ("Trỏ + Giữa (Xuống dòng)", COLOR_ENTER),
    THUMB_TIP: ("Ngón cái (Bật/Tắt)", COLOR_DASH),
}


def format_block_bar(ratio: float, width: int = 8) -> str:
    """Render an ASCII block progress bar like [■■■■■□□□]."""
    clamped = min(1.0, max(0.0, float(ratio)))
    filled = int(round(clamped * width))
    return "[" + ("■" * filled) + ("□" * (width - filled)) + "]"


def compute_snap_position(
    window_rect: QRect,
    screen_rect: QRect,
    margin: int = SNAP_MARGIN,
    corner_padding: int = 12,
) -> QPoint:
    """Snap window_rect to screen edges/corners when released within `margin` pixels."""
    x = window_rect.x()
    y = window_rect.y()
    w = window_rect.width()
    h = window_rect.height()

    left_dist = abs(x - screen_rect.left())
    right_dist = abs((screen_rect.right() + 1) - (x + w))
    top_dist = abs(y - screen_rect.top())
    bottom_dist = abs((screen_rect.bottom() + 1) - (y + h))

    near_left = left_dist <= margin or x < screen_rect.left()
    near_right = right_dist <= margin or (x + w) > (screen_rect.right() + 1)
    near_top = top_dist <= margin or y < screen_rect.top()
    near_bottom = bottom_dist <= margin or (y + h) > (screen_rect.bottom() + 1)

    # If near any edge, snap to the closest horizontal and/or vertical edge
    # If near any edge at all, snap to the nearest corner when close to an edge
    if near_left:
        x = screen_rect.left() + corner_padding
    elif near_right:
        x = screen_rect.right() + 1 - w - corner_padding

    if near_top:
        y = screen_rect.top() + corner_padding
    elif near_bottom:
        y = screen_rect.bottom() + 1 - h - corner_padding

    # If user dragged near left/right edge, also snap to nearest top/bottom corner if within 80px,
    # or if dragged near top/bottom edge, snap to nearest left/right corner if within 80px
    if (near_left or near_right) and not (near_top or near_bottom):
        if top_dist <= 80:
            y = screen_rect.top() + corner_padding
        elif bottom_dist <= 80:
            y = screen_rect.bottom() + 1 - h - corner_padding
    elif (near_top or near_bottom) and not (near_left or near_right):
        if left_dist <= 80:
            x = screen_rect.left() + corner_padding
        elif right_dist <= 80:
            x = screen_rect.right() + 1 - w - corner_padding

    return QPoint(x, y)


class CommitDelayBar(QWidget):
    """Ultra-thin 2px progress bar for commit delay visualization."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ratio = 0.0
        self._color = QColor(COLOR_DOT)
        self.setFixedHeight(2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @property
    def ratio(self) -> float:
        return self._ratio

    def set_progress(self, ratio: float, color: str = COLOR_DOT) -> None:
        clamped = min(1.0, max(0.0, float(ratio)))
        if abs(clamped - self._ratio) > 0.005 or self._color.name().lower() != color.lower():
            self._ratio = clamped
            self._color = QColor(color)
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#1F2937"))
        if self._ratio > 0.0:
            fill_w = max(2.0, self.width() * self._ratio)
            painter.fillRect(QRectF(0, 0, fill_w, self.height()), self._color)
        painter.end()


def _build_mini_morse_grid() -> QWidget:
    """Compact 5-column Morse reference table for the Mini Widget drawer."""
    container = QWidget()
    grid = QGridLayout(container)
    grid.setContentsMargins(4, 2, 4, 2)
    grid.setHorizontalSpacing(6)
    grid.setVerticalSpacing(1)

    chars = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [str(d) for d in range(10)]
    cols = 5
    rows = (len(chars) + cols - 1) // cols  # 8 rows for 36 items
    font = QFont("Consolas", 8)
    for idx, ch in enumerate(chars):
        r = idx % rows
        c = idx // rows
        raw = CHAR_TO_MORSE[ch]
        pretty = "".join("·" if s == "." else "—" for s in raw)
        lbl = QLabel(f"<b style='color:#FFFFFF'>{ch}</b> <span style='color:#00E5FF'>{pretty}</span>")
        lbl.setFont(font)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("background: transparent;")
        grid.addWidget(lbl, r, c)
    return container


class MiniWidget(QWidget):
    """Floating HUD Mini Widget (340x160 collapsed, 340x330 expanded)."""

    expand_requested = pyqtSignal()
    capture_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = False
        self._capture_active = False
        self._hand_present = False
        self._hovered = False
        self._drag_offset: QPoint | None = None
        self._edge_color: str | None = None
        self._raw_text = ""

        # Frameless, always-on-top, tool window, focus-safe so background key injection never steals focus
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("AirMorse Mini")
        self.setFixedSize(MINI_WIDTH, MINI_HEIGHT_COLLAPSED)
        self.setWindowOpacity(IDLE_OPACITY)

        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._clear_edge_flash)

        self._copy_reset_timer = QTimer(self)
        self._copy_reset_timer.setSingleShot(True)
        self._copy_reset_timer.timeout.connect(lambda: self.copy_btn.setText("Sao chép"))

        self._build_ui()

    @property
    def is_expanded(self) -> bool:
        return self._expanded

    @property
    def edge_flash_color(self) -> str | None:
        return self._edge_color

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)

        # 1. Title Bar: [::] AirMorse Mini   [● Live] [ ⤢ Phóng to]
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.drag_handle = QLabel("[::] AirMorse Mini")
        self.drag_handle.setStyleSheet(
            f"color: {COLOR_TEXT}; font-weight: 600; font-size: 12px; background: transparent;"
        )

        self.live_btn = QPushButton("○ Tạm dừng")
        self.live_btn.setCheckable(True)
        self.live_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.live_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.live_btn.clicked.connect(self._on_live_clicked)

        self.expand_btn = QPushButton("⤢ Phóng to")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.expand_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLOR_CARD};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_DOT};
                color: {COLOR_DOT};
            }}
            """
        )
        self.expand_btn.clicked.connect(self.expand_requested.emit)

        header.addWidget(self.drag_handle)
        header.addStretch(1)
        header.addWidget(self.live_btn)
        header.addWidget(self.expand_btn)
        root.addLayout(header)

        # 2. Middle Row: Camera Mini (96x68 or 120x90 scaled) + Live Signal Info
        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(8)

        self.video_label = QLabel("CAMERA\nMINI")
        self.video_label.setFixedSize(104, 72)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet(
            f"""
            QLabel {{
                background: #050608;
                color: {COLOR_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                font-size: 10px;
            }}
            """
        )

        sig_col = QVBoxLayout()
        sig_col.setContentsMargins(0, 0, 0, 0)
        sig_col.setSpacing(2)

        self.signal_label = QLabel("Tín hiệu: —")
        self.signal_label.setStyleSheet(
            f"color: {COLOR_TEXT}; font-family: Consolas, monospace; font-size: 12px; font-weight: 600; background: transparent;"
        )

        self.pinch_label = QLabel("Chụm: —")
        self.pinch_label.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: 11px; background: transparent;"
        )

        self.wait_label = QLabel("Chờ gửi: [□□□□□□□□] 0.00s")
        self.wait_label.setStyleSheet(
            f"color: {COLOR_MUTED}; font-family: Consolas, monospace; font-size: 11px; background: transparent;"
        )

        self.commit_bar = CommitDelayBar()

        sig_col.addWidget(self.signal_label)
        sig_col.addWidget(self.pinch_label)
        sig_col.addWidget(self.wait_label)
        sig_col.addWidget(self.commit_bar)
        sig_col.addStretch(1)

        mid.addWidget(self.video_label)
        mid.addLayout(sig_col, stretch=1)
        root.addLayout(mid)

        # 3. Decoded Text Bar: Văn bản: ... | [Sao chép]
        text_row = QHBoxLayout()
        text_row.setContentsMargins(4, 2, 4, 2)
        text_row.setSpacing(6)

        self.text_label = QLabel("Văn bản: |")
        self.text_label.setStyleSheet(
            f"color: {COLOR_TEXT}; font-family: Consolas, monospace; font-size: 12px; background: transparent;"
        )
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.copy_btn = QPushButton("Sao chép")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.copy_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLOR_CARD};
                color: {COLOR_MUTED};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT};
                border-color: {COLOR_DASH};
            }}
            """
        )
        self.copy_btn.clicked.connect(self.copy_text)

        text_row.addWidget(self.text_label, stretch=1)
        text_row.addWidget(self.copy_btn)
        root.addLayout(text_row)

        # 4. Expandable Morse Drawer (hidden when collapsed)
        self.morse_drawer = QFrame()
        self.morse_drawer.setStyleSheet(
            f"""
            QFrame {{
                background: {COLOR_CARD};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
            }}
            """
        )
        drawer_layout = QVBoxLayout(self.morse_drawer)
        drawer_layout.setContentsMargins(6, 4, 6, 4)
        drawer_layout.setSpacing(2)

        drawer_header = QHBoxLayout()
        drawer_title = QLabel("BẢNG CHỮ CÁI MORSE")
        drawer_title.setStyleSheet(
            f"color: {COLOR_MUTED}; font-size: 10px; font-weight: 600; border: none; background: transparent;"
        )
        self.collapse_drawer_btn = QPushButton("▴ Thu gọn")
        self.collapse_drawer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_drawer_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.collapse_drawer_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {COLOR_DOT};
                border: none;
                font-size: 10px;
                font-weight: 600;
            }}
            """
        )
        self.collapse_drawer_btn.clicked.connect(lambda: self.set_expanded(False))
        drawer_header.addWidget(drawer_title)
        drawer_header.addStretch(1)
        drawer_header.addWidget(self.collapse_drawer_btn)

        drawer_layout.addLayout(drawer_header)
        drawer_layout.addWidget(_build_mini_morse_grid())
        self.morse_drawer.setVisible(False)
        root.addWidget(self.morse_drawer)

        # 5. Footer Bar: [·]Trỏ  [—]Giữa  [␣]Áp út  [⌫]Út | [ ▾ Mở bảng mã ]
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(4)

        self.legend_label = QLabel(
            f"<span style='color:{COLOR_DOT}'>[·]</span>Trỏ "
            f"<span style='color:{COLOR_DASH}'>[—]</span>Giữa "
            f"<span style='color:{COLOR_ENTER}'>[␣]</span>Áp út "
            f"<span style='color:{COLOR_DELETE}'>[⌫]</span>Út"
        )
        self.legend_label.setTextFormat(Qt.TextFormat.RichText)
        self.legend_label.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 10px; background: transparent;")

        self.toggle_drawer_btn = QPushButton("▾ Mở bảng mã")
        self.toggle_drawer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_drawer_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle_drawer_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLOR_CARD};
                color: {COLOR_DOT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {COLOR_DOT};
            }}
            """
        )
        self.toggle_drawer_btn.clicked.connect(self.toggle_expanded)

        footer.addWidget(self.legend_label)
        footer.addStretch(1)
        footer.addWidget(self.toggle_drawer_btn)
        root.addLayout(footer)

        self._update_live_badge()

    def _on_live_clicked(self, checked: bool) -> None:
        self.set_capture_state(checked)
        self.capture_toggled.emit(checked)

    def set_capture_state(self, active: bool) -> None:
        self._capture_active = bool(active)
        self.live_btn.blockSignals(True)
        self.live_btn.setChecked(self._capture_active)
        self.live_btn.blockSignals(False)
        self._update_live_badge()

    def _update_live_badge(self) -> None:
        if self._capture_active:
            self.live_btn.setText("● Live")
            self.live_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: rgba(0, 230, 118, 0.15);
                    color: {COLOR_DASH};
                    border: 1px solid {COLOR_DASH};
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                """
            )
        else:
            self.live_btn.setText("○ Tạm dừng")
            self.live_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {COLOR_CARD};
                    color: {COLOR_MUTED};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 11px;
                }}
                """
            )

    def toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = bool(expanded)
        self.morse_drawer.setVisible(self._expanded)
        if self._expanded:
            self.toggle_drawer_btn.setText("▴ Thu gọn")
            self.setFixedSize(MINI_WIDTH, MINI_HEIGHT_EXPANDED)
        else:
            self.toggle_drawer_btn.setText("▾ Mở bảng mã")
            self.setFixedSize(MINI_WIDTH, MINI_HEIGHT_COLLAPSED)
        self.update()

    def update_signal(
        self,
        buffer: str,
        pending_char: str,
        remaining_sec: float,
        progress_ratio: float,
    ) -> None:
        if buffer:
            formatted = format_morse_signal(buffer)
            target = pending_char or "?"
            self.signal_label.setText(f"Tín hiệu: {formatted}  ➔ [{target}]")
            bar_str = format_block_bar(progress_ratio, 8)
            self.wait_label.setText(f"Chờ gửi:  {bar_str} {remaining_sec:.2f}s")
            bar_color = COLOR_DASH if buffer.endswith("-") else COLOR_DOT
            self.commit_bar.set_progress(progress_ratio, bar_color)
        else:
            self.signal_label.setText("Tín hiệu: —")
            self.wait_label.setText("Chờ gửi:  [□□□□□□□□] 0.00s")
            self.commit_bar.set_progress(0.0, COLOR_DOT)

    def update_pinch(self, highlight_finger: int | None) -> None:
        if highlight_finger in PINCH_DESCRIPTIONS:
            desc, color = PINCH_DESCRIPTIONS[highlight_finger]
            self.pinch_label.setText(f"Chụm:     {desc}")
            self.pinch_label.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;")
        else:
            self.pinch_label.setText("Chụm:     —")
            self.pinch_label.setStyleSheet(f"color: {COLOR_MUTED}; font-size: 11px; background: transparent;")

    def update_decoded_text(self, text: str) -> None:
        self._raw_text = text
        single_line = text.replace("\n", "↵ ")
        if len(single_line) > 22:
            single_line = "…" + single_line[-21:]
        self.text_label.setText(f"Văn bản: {single_line}|")

    def copy_text(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._raw_text)
        self.copy_btn.setText("Đã chép")
        self._copy_reset_timer.start(1000)

    def update_frame(self, pixmap: QPixmap | None, message: str = "") -> None:
        if pixmap is None:
            if message:
                self.video_label.setPixmap(QPixmap())
                self.video_label.setText(message[:24])
            return
        self.video_label.setText("")
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.video_label.setPixmap(scaled)

    def set_hand_present(self, hand_present: bool) -> None:
        self._hand_present = bool(hand_present)
        self._refresh_opacity()

    def _refresh_opacity(self) -> None:
        target = ACTIVE_OPACITY if (self._hand_present or self._hovered) else IDLE_OPACITY
        if abs(self.windowOpacity() - target) > 0.01:
            self.setWindowOpacity(target)

    def flash_edge_for_event(self, kind: str, value: str = "") -> None:
        """Flash the outer border of the Mini Widget based on the gesture signal."""
        if kind == "symbol":
            color = COLOR_DOT if value == "." else COLOR_DASH
        elif kind == "char":
            color = COLOR_DASH
        elif kind in {"space", "enter"}:
            color = COLOR_ENTER
        elif kind in {"backspace", "pop", "error"}:
            color = COLOR_DELETE
        else:
            return
        self.flash_edge(color)

    def flash_edge(self, color: str, duration_ms: int = 350) -> None:
        self._edge_color = color
        self.update()
        self._flash_timer.start(duration_ms)

    def _clear_edge_flash(self) -> None:
        self._edge_color = None
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._hovered = True
        self._refresh_opacity()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hovered = False
        self._refresh_opacity()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._drag_offset is not None:
            self._drag_offset = None
            self.snap_to_screen()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def snap_to_screen(self, screen_rect: QRect | None = None) -> QPoint:
        """Snap the widget to the nearest screen edge/corner if within SNAP_MARGIN."""
        if screen_rect is None:
            screen = self.screen() or QGuiApplication.primaryScreen()
            if screen is None:
                return self.pos()
            screen_rect = screen.availableGeometry()
        snapped = compute_snap_position(self.frameGeometry(), screen_rect, margin=SNAP_MARGIN)
        self.move(snapped)
        return snapped

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        painter.setBrush(QColor(COLOR_BG))
        if self._edge_color:
            pen = QPen(QColor(self._edge_color), 2.5)
        else:
            pen = QPen(QColor(COLOR_BORDER), 1.2)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 10, 10)
        painter.end()
