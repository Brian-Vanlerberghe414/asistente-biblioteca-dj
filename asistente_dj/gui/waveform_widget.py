"""Widget de waveform estilo Beatport para el reproductor DJ.

Muestra la forma de onda del track completo coloreada por contenido frecuencial:
- Azul: graves/kicks  - Verde/amarillo: medios  - Naranja: agudos/hats
La porción ya reproducida se muestra en colores vivos; la restante atenuada.
Soporta seek con click y drag del mouse.
Sin dependencias extra (solo numpy y PySide6).
"""
from __future__ import annotations

import base64
import json
import zlib

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class WaveformWidget(QWidget):
    seek_requested = Signal(int)   # ms solicitados por el usuario

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64)
        self.setMaximumHeight(80)
        self.setCursor(Qt.PointingHandCursor)

        self._peaks:  np.ndarray | None = None   # float32, 0-1
        self._colors: np.ndarray | None = None   # uint8, (n, 3)
        self._n: int = 0
        self._pos_ms: int = 0
        self._dur_ms: int = 0
        self._dragging = False

        # barras "agrupadas" (estilo Claude Design): se recalculan por ancho
        self._bars_cache: np.ndarray | None = None
        self._bars_w: int = -1

    # ─────────────────────────────────────────────────── API pública ──────────

    def set_track(self, waveform_json: str | None, duracion_ms: int = 0):
        """Carga los datos del track. Llama antes de reproducir."""
        self._pos_ms = 0
        self._dur_ms = max(duracion_ms, 0)
        self._peaks = self._colors = None
        self._n = 0

        if waveform_json:
            try:
                d = json.loads(waveform_json)
                n = d["n"]
                peaks_raw  = zlib.decompress(base64.b64decode(d["peaks"]))
                colors_raw = zlib.decompress(base64.b64decode(d["colors"]))
                self._peaks  = np.frombuffer(peaks_raw,  dtype=np.float32).copy()
                self._colors = np.frombuffer(colors_raw, dtype=np.uint8).reshape(n, 3).copy()
                self._n = n
            except Exception:
                pass

        self._bars_cache = None
        self._bars_w = -1
        self.update()

    def set_position(self, ms: int):
        self._pos_ms = ms
        self.update()

    def set_duration(self, ms: int):
        self._dur_ms = ms
        self.update()

    # ─────────────────────────────────────────────────── pintura ──────────────

    # Colores del diseño
    _CYAN        = QColor(0, 229, 255)          # reproducido
    _CYAN_DIM    = QColor(0, 229, 255, 56)      # restante (~22%)
    _ORANGE      = QColor(255, 107, 0)          # cabezal
    _BG          = QColor(15, 15, 16)

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        mid = h // 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.fillRect(0, 0, w, h, self._BG)

        if self._peaks is not None and self._n > 0:
            self._draw_waveform(painter, w, h, mid)
        else:
            self._draw_progress_bar(painter, w, h)

        # Cabezal naranja con punto
        if self._dur_ms > 0:
            cx = int(w * self._pos_ms / self._dur_ms)
            pen = QPen(self._ORANGE, 2)
            painter.setPen(pen)
            painter.drawLine(cx, 0, cx, h)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setBrush(self._ORANGE)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(cx - 4, mid - 4, 8, 8)

        painter.end()

    def _bars_for_width(self, w: int) -> np.ndarray:
        """Reduce los picos a un número fijo de barras "gruesas" (estilo
        Claude Design: barras separadas en vez de un relleno casi continuo)."""
        if self._bars_cache is not None and self._bars_w == w:
            return self._bars_cache

        target = max(24, min(140, w // 6))
        n = self._n
        if n <= target:
            bars = self._peaks.copy()
        else:
            idx = np.linspace(0, n, target + 1).astype(int)
            bars = np.array([
                self._peaks[idx[i]:idx[i + 1]].max() if idx[i + 1] > idx[i] else 0.0
                for i in range(target)
            ], dtype=np.float32)

        self._bars_cache = bars
        self._bars_w = w
        return bars

    def _draw_waveform(self, painter: QPainter, w: int, h: int, mid: int):
        progress = self._pos_ms / self._dur_ms if self._dur_ms > 0 else 0.0
        bars = self._bars_for_width(w)
        nb = len(bars)
        cursor_col = int(progress * nb)

        col_w = max(w / nb, 1.0)
        gap = max(int(col_w * 0.3), 2)   # separación marcada entre barras

        for i in range(nb):
            amp = float(bars[i])
            bar_h = max(int(amp * (mid - 2)), 2)

            x1 = int(i * col_w)
            x2 = max(int((i + 1) * col_w) - gap, x1)
            bw = x2 - x1 + 1

            if i < cursor_col:
                color = self._CYAN
            else:
                color = self._CYAN_DIM

            # Barra redondeada hacia arriba + reflejo hacia abajo
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.drawRoundedRect(x1, mid - bar_h, bw, bar_h, bw / 2, bw / 2)

            ref_h = max(int(bar_h * 0.35), 1)
            ref_c = QColor(color.red(), color.green(), color.blue(),
                           color.alpha() // 2)
            painter.setBrush(ref_c)
            painter.drawRoundedRect(x1, mid, bw, ref_h, bw / 2, bw / 2)
            painter.setRenderHint(QPainter.Antialiasing, False)

    def _draw_progress_bar(self, painter: QPainter, w: int, h: int):
        """Fallback cuando no hay waveform: barra de progreso cyan."""
        painter.fillRect(0, 0, w, h, self._BG)
        if self._dur_ms > 0:
            filled = int(w * self._pos_ms / self._dur_ms)
            painter.fillRect(0, 0, filled, h, QColor(0, 229, 255, 45))
        painter.setPen(QColor(117, 119, 123))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(0, 0, w, h, Qt.AlignCenter, "Sin waveform — ejecutá Analizar")

    # ─────────────────────────────────────────────────── mouse / seek ─────────

    def _seek_from_mouse(self, x: int):
        if self._dur_ms > 0:
            w = max(self.width(), 1)
            ms = int(self._dur_ms * max(0, min(x, w)) / w)
            self.seek_requested.emit(ms)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._seek_from_mouse(event.position().x())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._seek_from_mouse(event.position().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
