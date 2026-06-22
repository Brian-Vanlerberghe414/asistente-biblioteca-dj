"""Delegates de visualización custom para la tabla de tracks."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRect, QSize, QEvent, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPen, QFont, QLinearGradient, QFontDatabase, QPainterPath,
)
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

from gui.theme import ENERGY_COLORS, CAMELOT_COLORS, CYAN, ORANGE, GREEN, AMBER
from gui.track_model import ROLE_REPRODUCIENDO


def _energy_color(nivel: int) -> QColor:
    idx = max(0, min(int(nivel) - 1, 9))
    return QColor(ENERGY_COLORS[idx])


def _camelot_color(cam: str) -> QColor:
    cam = (cam or "").strip().upper()
    if not cam or len(cam) < 2:
        return QColor("#888888")
    try:
        num = int(cam[:-1])
        return QColor(CAMELOT_COLORS[(num - 1) % 12])
    except ValueError:
        return QColor("#888888")


def _sel_bg(option):
    if option.state & option.state.State_Selected:
        return QColor(0, 229, 255, 23)
    if option.state & option.state.State_MouseOver:
        return QColor(255, 255, 255, 9)
    return None


class EnergyDelegate(QStyledItemDelegate):
    """Barra horizontal de gradiente frío→caliente + número de nivel."""

    BAR_W = 54
    BAR_H = 6

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        bg = _sel_bg(option)
        if bg:
            painter.fillRect(option.rect, bg)

        val_str = index.data(Qt.DisplayRole) or ""
        try:
            nivel = int(round(float(val_str)))
        except (ValueError, TypeError):
            painter.restore()
            return

        nivel = max(1, min(nivel, 10))
        color = _energy_color(nivel)

        rect = option.rect
        mid_y = rect.center().y()

        # ── barra ─────────────────────────────────────────────────────────────
        bar_x = rect.left() + 10
        bar_y = mid_y - self.BAR_H // 2
        track_r = QRect(bar_x, bar_y, self.BAR_W, self.BAR_H)

        painter.fillRect(track_r, QColor(255, 255, 255, 18))

        fill_w = max(2, int(self.BAR_W * nivel / 10))
        fill_r = QRect(bar_x, bar_y, fill_w, self.BAR_H)
        grad = QLinearGradient(bar_x, 0, bar_x + self.BAR_W, 0)
        grad.setColorAt(0.00, QColor("#2F6BFF"))
        grad.setColorAt(0.30, QColor("#16D6A6"))
        grad.setColorAt(0.60, QColor("#FFD23A"))
        grad.setColorAt(1.00, QColor("#FF3326"))
        painter.fillRect(fill_r, grad)

        # ── número ────────────────────────────────────────────────────────────
        font = QFont("JetBrains Mono", 11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(color)
        num_r = QRect(bar_x + self.BAR_W + 5, rect.top(), 18, rect.height())
        painter.drawText(num_r, Qt.AlignVCenter | Qt.AlignLeft, str(nivel))

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(self.BAR_W + 32, 30)


class CamelotDelegate(QStyledItemDelegate):
    """Badge coloreado con el código Camelot (p.ej. '11A')."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        bg = _sel_bg(option)
        if bg:
            painter.fillRect(option.rect, bg)

        text = (index.data(Qt.DisplayRole) or "").strip()
        if not text:
            painter.restore()
            return

        color = _camelot_color(text)

        font = QFont("JetBrains Mono", 11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        fm = painter.fontMetrics()

        # Ancho fijo (el del código Camelot más largo posible, "12A"/"12B")
        # para que todos los badges midan igual, sin importar 1 o 2 dígitos.
        th = fm.height()
        ph, pv = 7, 3
        bw = fm.horizontalAdvance("12A") + ph * 2
        bh = th + pv * 2

        rect = option.rect
        bx = rect.left() + 8
        by = rect.center().y() - bh // 2
        badge = QRect(bx, by, bw, bh)

        bg_c = QColor(color); bg_c.setAlpha(30)
        painter.fillRect(badge, bg_c)

        brd = QColor(color); brd.setAlpha(90)
        painter.setPen(QPen(brd, 1))
        painter.drawRoundedRect(badge, 5, 5)

        painter.setPen(color)
        painter.drawText(badge, Qt.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(72, 30)


class StatusDelegate(QStyledItemDelegate):
    """Chip redondeado de estado (Analizado / Pendiente / Duplicado)."""

    _MAP = {
        "1":          (GREEN,  0x1E, "Analizado"),
        "true":       (GREEN,  0x1E, "Analizado"),
        "analizado":  (GREEN,  0x1E, "Analizado"),
        "0":          (AMBER,  0x1A, "Pendiente"),
        "false":      (AMBER,  0x1A, "Pendiente"),
        "pendiente":  (AMBER,  0x1A, "Pendiente"),
        "duplicado":  (ORANGE, 0x24, "Duplicado"),
        "ingreso":    ("#9A9CA1", 0x18, "Ingreso"),
    }
    _DEFAULT = (AMBER, 0x1A, "Pendiente")

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        bg = _sel_bg(option)
        if bg:
            painter.fillRect(option.rect, bg)

        raw = str(index.data(Qt.DisplayRole) or "").strip().lower()
        color_hex, alpha, label = self._MAP.get(raw, self._DEFAULT)
        color = QColor(color_hex)

        font = QFont("Space Grotesk", 11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        fm = painter.fontMetrics()

        tw = fm.horizontalAdvance(label)
        th = fm.height()
        ph, pv = 8, 3
        bw = tw + ph * 2
        bh = th + pv * 2

        rect = option.rect
        bx = rect.left() + 8
        by = rect.center().y() - bh // 2
        badge = QRect(bx, by, bw, bh)

        bg_c = QColor(color); bg_c.setAlpha(alpha)
        painter.fillRect(badge, bg_c)

        painter.setPen(QPen(color, 1))
        painter.drawRoundedRect(badge, 10, 10)

        painter.setPen(color)
        painter.drawText(badge, Qt.AlignCenter, label)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 30)


class BpmDelegate(QStyledItemDelegate):
    """BPM en tipografía monoespaciada."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()

        bg = _sel_bg(option)
        if bg:
            painter.fillRect(option.rect, bg)

        text = (index.data(Qt.DisplayRole) or "").strip()
        if not text or text == "0":
            painter.restore()
            return

        font = QFont("JetBrains Mono")
        font.setPixelSize(12)   # mismo tamaño que el resto de la grilla (font-size: 12px)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor("#E9E9EC"))
        painter.drawText(
            option.rect.adjusted(10, 0, -4, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            text,
        )
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(56, 30)


class PlayButtonDelegate(QStyledItemDelegate):
    """Botón ▶ por fila; única forma de reproducir un track. Resalta la fila
    que está sonando ahora."""

    play_requested = Signal(object)  # QModelIndex (proxy) de la fila clickeada

    SIZE = 28

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        bg = _sel_bg(option)
        if bg:
            painter.fillRect(option.rect, bg)

        sonando = bool(index.data(ROLE_REPRODUCIENDO))
        rect = option.rect
        cx, cy = rect.center().x(), rect.center().y()

        if sonando:
            halo = QColor(ORANGE); halo.setAlpha(40)
            painter.setPen(Qt.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(rect.center(), 11, 11)
            color = QColor(ORANGE)
        else:
            color = QColor(CYAN)

        path = QPainterPath()
        path.moveTo(cx - 4, cy - 6)
        path.lineTo(cx - 4, cy + 6)
        path.lineTo(cx + 6, cy)
        path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawPath(path)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if option.rect.contains(event.position().toPoint()):
                self.play_requested.emit(index)
            return True
        return False

    def sizeHint(self, option, index):
        return QSize(self.SIZE, 30)
