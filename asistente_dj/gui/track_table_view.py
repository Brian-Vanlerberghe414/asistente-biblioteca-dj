"""QTableView con una imagen de fondo sutil detrás de las filas (estilo
glow ambiental, no compite con el texto)."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QTableView

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
BG_IMAGE_PATH = os.path.join(_ASSETS, "grid_bg.jpg")


class TrackTableView(QTableView):
    def __init__(self, bg_path: str = BG_IMAGE_PATH, parent=None):
        super().__init__(parent)
        self._bg = QPixmap(bg_path) if bg_path and os.path.exists(bg_path) else QPixmap()
        self._bg_cache = QPixmap()
        self._bg_cache_size = None
        # El fill sólido del tema lo pintamos nosotros: dejamos transparente
        # el viewport para que se vea la imagen de fondo detrás de las filas.
        self.setStyleSheet("QTableView { background: transparent; }")

    def _scaled_bg(self) -> QPixmap:
        size = self.viewport().size()
        if self._bg.isNull() or size.width() <= 0 or size.height() <= 0:
            return QPixmap()
        if self._bg_cache_size == size:
            return self._bg_cache
        self._bg_cache = self._bg.scaled(
            size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self._bg_cache_size = size
        return self._bg_cache

    def paintEvent(self, event):
        bg = self._scaled_bg()
        if not bg.isNull():
            vp = self.viewport()
            painter = QPainter(vp)
            x = (bg.width() - vp.width()) // 2
            y = (bg.height() - vp.height()) // 2
            painter.drawPixmap(0, 0, bg, x, y, vp.width(), vp.height())
            painter.end()
        super().paintEvent(event)
