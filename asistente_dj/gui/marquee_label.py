"""Label de ancho fijo: si el texto no entra, hace scroll horizontal continuo
en vez de elidirlo o forzar el crecimiento del layout contenedor."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget


class MarqueeLabel(QWidget):
    def __init__(self, width: int, color: str, font_size: int = 13,
                 weight: int = 400, parent=None):
        super().__init__(parent)
        self.setFixedWidth(width)
        self._color = QColor(color)
        self._font = QFont()
        self._font.setPixelSize(font_size)
        if weight >= 600:
            self._font.setWeight(QFont.Weight.DemiBold)
        self._text = ""
        self._offset = 0.0
        self._gap = 40
        self._timer = QTimer(self)
        self._timer.setInterval(35)
        self._timer.timeout.connect(self._tick)
        self.setFixedHeight(QFontMetrics(self._font).height())

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        text = text or ""
        if text == self._text:
            return
        self._text = text
        self._offset = 0.0
        fm = QFontMetrics(self._font)
        if fm.horizontalAdvance(self._text) > self.width():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self):
        fm = QFontMetrics(self._font)
        total = fm.horizontalAdvance(self._text) + self._gap
        self._offset += 1.2
        if self._offset >= total:
            self._offset = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self._font)
        painter.setPen(self._color)
        fm = painter.fontMetrics()
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        if not self._timer.isActive():
            painter.drawText(0, y, self._text)
        else:
            tw = fm.horizontalAdvance(self._text)
            x = -int(self._offset)
            painter.drawText(x, y, self._text)
            painter.drawText(x + tw + self._gap, y, self._text)
        painter.end()
