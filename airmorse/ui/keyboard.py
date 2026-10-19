"""On-screen QWERTY keyboard that flashes the decoded key."""

from PyQt6.QtCore import QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

ROWS = (
    tuple("1234567890"),
    tuple("QWERTYUIOP"),
    tuple("ASDFGHJKL"),
    tuple("ZXCVBNM"),
)


class KeyboardHud(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._active = ""
        self._uppercase = True
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._clear)
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Bàn phím ảo")

    def sizeHint(self) -> QSize:
        return QSize(640, 200)

    def set_uppercase(self, uppercase: bool) -> None:
        self._uppercase = uppercase
        self.update()

    def flash(self, character: str) -> None:
        self._active = " " if character == " " else character.upper()
        self.update()
        self._timer.start(400)

    def _label(self, character: str) -> str:
        if character.isalpha() and not self._uppercase:
            return character.lower()
        return character

    def _clear(self) -> None:
        self._active = ""
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#181E29"))
        font = QFont("Segoe UI", 10)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        width = self.width()
        gap = 6
        key_h = 30
        key_w = int(min(56, max(28, (width - gap * 11) / 10)))
        y = 6
        for row in ROWS:
            row_w = len(row) * key_w + (len(row) - 1) * gap
            x = max(gap, (width - row_w) // 2)
            for character in row:
                self._draw_key(
                    painter,
                    QRectF(x, y, key_w, key_h),
                    self._label(character),
                    character == self._active,
                )
                x += key_w + gap
            y += key_h + gap
        enter_w = key_w * 2.5 + gap
        space_w = key_w * 4 + gap * 3
        row_w = space_w + gap * 2 + enter_w
        space_x = max(gap, (width - row_w) // 2)
        self._draw_key(
            painter,
            QRectF(space_x, y, space_w, key_h),
            "Dấu cách",
            self._active == " ",
        )
        self._draw_key(
            painter,
            QRectF(space_x + space_w + gap * 2, y, enter_w, key_h),
            "Xuống dòng",
            self._active == "\n",
            accent_color="#7C4DFF",
        )
        painter.end()

    def _draw_key(
        self,
        painter: QPainter,
        rect: QRectF,
        label: str,
        active: bool,
        accent_color: str = "#00E676",
    ) -> None:
        if active:
            painter.setBrush(QColor(accent_color))
            painter.setPen(Qt.PenStyle.NoPen)
            text = QColor("#0E121A" if accent_color == "#00E676" else "#FFFFFF")
        else:
            painter.setBrush(QColor("#0E121A"))
            painter.setPen(QPen(QColor("#263043"), 1))
            text = QColor("#FFFFFF")
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(text)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
