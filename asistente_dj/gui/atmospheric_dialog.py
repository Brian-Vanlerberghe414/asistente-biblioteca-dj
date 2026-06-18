"""Diálogo modal con fondo fotográfico blureado — estética de recital de electrónica."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout,
    QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem,
)


def _blur_pixmap(src: QPixmap, radius: int, target: QSize) -> QPixmap:
    """Escala src a target, aplica desenfoque con QGraphicsScene y retorna el resultado."""
    if src.isNull():
        return QPixmap()

    scaled = src.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    if scaled.width() > target.width() or scaled.height() > target.height():
        x = (scaled.width() - target.width()) // 2
        y = (scaled.height() - target.height()) // 2
        scaled = scaled.copy(x, y, target.width(), target.height())

    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(scaled)
    blur = QGraphicsBlurEffect()
    blur.setBlurRadius(radius)
    item.setGraphicsEffect(blur)
    scene.addItem(item)

    result = QPixmap(target)
    result.fill(Qt.transparent)
    p = QPainter(result)
    scene.render(p, source=QRect(0, 0, target.width(), target.height()))
    p.end()
    return result


class AtmosphericDialog(QDialog):
    """
    Diálogo con:
    - Fondo fotográfico blureado (blur ≈ 12px, brillo 82%)
    - Overlay oscuro semitransparente para legibilidad
    - Glow inferior del color de acento
    - Borde con glow del acento
    """

    def __init__(
        self,
        image_path: str,
        accent: str = "#00E5FF",
        parent=None,
    ):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._bg_px: QPixmap = QPixmap()
        self._bg_ready: QPixmap = QPixmap()
        self._last_size = QSize()

        if image_path and os.path.exists(image_path):
            self._bg_px = QPixmap(image_path)

        # Sin borde del SO — lo pintamos nosotros
        self.setWindowFlags(Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Layout con margen para que el borde pintado no quede pegado al contenido
        self._content_layout = QVBoxLayout(self)
        self._content_layout.setContentsMargins(24, 24, 24, 20)
        self._content_layout.setSpacing(12)

    def paintEvent(self, event):
        r = self.rect()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # ── Fondo blureado (renderizado perezoso cuando cambia el tamaño) ──────
        if not self._bg_px.isNull():
            if r.size() != self._last_size:
                self._bg_ready = _blur_pixmap(self._bg_px, 14, r.size())
                self._last_size = r.size()
            if not self._bg_ready.isNull():
                painter.setOpacity(0.85)
                painter.drawPixmap(0, 0, self._bg_ready)
                painter.setOpacity(1.0)

        # ── Overlay oscuro ────────────────────────────────────────────────────
        painter.fillRect(r, QColor(0, 0, 0, 150))

        # ── Glow inferior del acento ──────────────────────────────────────────
        glow_h = 160
        glow_r = QRect(0, r.height() - glow_h, r.width(), glow_h)
        grad = QLinearGradient(0, r.height() - glow_h, 0, r.height())
        a0 = QColor(self._accent); a0.setAlpha(0)
        a1 = QColor(self._accent); a1.setAlpha(35)
        grad.setColorAt(0, a0)
        grad.setColorAt(1, a1)
        painter.fillRect(glow_r, grad)

        # ── Borde con color de acento ──────────────────────────────────────────
        border_c = QColor(self._accent); border_c.setAlpha(120)
        painter.setPen(QPen(border_c, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(r.adjusted(0, 0, -1, -1), 10, 10)

        painter.end()
