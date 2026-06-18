"""Panel derecho: detalle del track seleccionado."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap,
)
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from gui.theme import (
    BG_PANEL, BG_ELEVATED, LINE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    CYAN, ENERGY_COLORS, CAMELOT_COLORS,
)


def _energy_color(nivel: int) -> QColor:
    return QColor(ENERGY_COLORS[max(0, min(int(nivel) - 1, 9))])


def _camelot_color(cam: str) -> QColor:
    cam = (cam or "").strip().upper()
    if not cam or len(cam) < 2:
        return QColor("#888888")
    try:
        return QColor(CAMELOT_COLORS[(int(cam[:-1]) - 1) % 12])
    except ValueError:
        return QColor("#888888")


# ─────────────────────────────────────────── artwork placeholder ──────────────

class ArtworkWidget(QWidget):
    """Placeholder de artwork: gradiente atmosférico + scrim con título/artista."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)
        self.setMaximumHeight(200)
        self._titulo  = ""
        self._artista = ""
        self._pixmap: QPixmap | None = None

    def set_track(self, titulo: str, artista: str, cover_path: str | None = None):
        self._titulo  = titulo  or ""
        self._artista = artista or ""
        self._pixmap  = None
        if cover_path and os.path.exists(cover_path):
            self._pixmap = QPixmap(cover_path)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(r.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (scaled.width()  - r.width())  // 2
            y = (scaled.height() - r.height()) // 2
            painter.drawPixmap(-x, -y, scaled)
        else:
            # Gradiente placeholder atmosférico
            g = QLinearGradient(0, 0, r.width(), r.height())
            g.setColorAt(0.0, QColor(10, 30, 60))
            g.setColorAt(0.5, QColor(30, 10, 50))
            g.setColorAt(1.0, QColor(10, 20, 35))
            painter.fillRect(r, g)

        # Scrim inferior para legibilidad
        scrim = QLinearGradient(0, r.height() - 80, 0, r.height())
        scrim.setColorAt(0, QColor(0, 0, 0, 0))
        scrim.setColorAt(1, QColor(0, 0, 0, 200))
        painter.fillRect(r, scrim)

        # Texto
        painter.setPen(QColor(TEXT_PRIMARY))
        font_t = QFont("Space Grotesk", 13, QFont.Weight.Bold)
        painter.setFont(font_t)
        painter.drawText(r.adjusted(12, 0, -8, -28), Qt.AlignBottom | Qt.AlignLeft, self._titulo)

        painter.setPen(QColor(TEXT_SECONDARY))
        font_a = QFont("Space Grotesk", 10)
        painter.setFont(font_a)
        painter.drawText(r.adjusted(12, 0, -8, -10), Qt.AlignBottom | Qt.AlignLeft, self._artista)

        painter.end()


# ─────────────────────────────────────────── stat card ────────────────────────

class StatCard(QFrame):
    """Tarjeta con label + valor grande (BPM o Key)."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background: {BG_ELEVATED}; border: 1px solid {LINE}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; font-weight: 600; letter-spacing: 1.2px;"
        )
        self._val = QLabel("—")
        self._val.setStyleSheet(
            f"color: {CYAN}; font-family: 'JetBrains Mono','Consolas',monospace;"
            "font-size: 20px; font-weight: 700;"
        )
        lay.addWidget(lbl)
        lay.addWidget(self._val)

    def set_value(self, text: str, color: str = CYAN):
        self._val.setText(text or "—")
        self._val.setStyleSheet(
            f"color: {color}; font-family: 'JetBrains Mono','Consolas',monospace;"
            "font-size: 20px; font-weight: 700;"
        )


# ─────────────────────────────────────────── energy selector ─────────────────

class EnergySelectorWidget(QWidget):
    """10 segmentos clicables para fijar la energía manual."""

    energy_changed = Signal(int)  # nivel 1-10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._nivel = 0
        self.setCursor(Qt.PointingHandCursor)

    def set_nivel(self, n: int | None):
        self._nivel = int(n) if n is not None else 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        seg_w = (w - 9 * 3) / 10  # 9 gaps de 3px

        for i in range(10):
            x = int(i * (seg_w + 3))
            seg_r_w = max(int(seg_w), 4)
            active = (i + 1) <= self._nivel

            if active:
                c = _energy_color(i + 1)
            else:
                c = QColor(255, 255, 255, 13)

            path = QPainterPath()
            path.addRoundedRect(x, 2, seg_r_w, h - 4, 3, 3)
            painter.fillPath(path, c)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            w = max(self.width(), 1)
            frac = event.position().x() / w
            nivel = max(1, min(10, int(frac * 10) + 1))
            self._nivel = nivel
            self.update()
            self.energy_changed.emit(nivel)


# ─────────────────────────────────────────── fila metadata ───────────────────

def _meta_row(label: str, value: str, mono: bool = False) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(8)

    lbl = QLabel(label)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
    lbl.setFixedWidth(68)

    val = QLabel(value or "—")
    val.setWordWrap(True)
    mono_style = "font-family: 'JetBrains Mono','Consolas',monospace; " if mono else ""
    val.setStyleSheet(f"{mono_style}color: {TEXT_SECONDARY}; font-size: 11px;")
    val.setTextInteractionFlags(Qt.TextSelectableByMouse)

    lay.addWidget(lbl)
    lay.addWidget(val, stretch=1)
    return w


# ─────────────────────────────────────────── panel principal ─────────────────

class DetallePanelWidget(QWidget):
    """Panel derecho de detalle del track: artwork, stats, energía manual, metadata."""

    energy_manual_changed = Signal(int, int)  # (track_id, nivel)

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._track_id: int | None = None
        self.setFixedWidth(280)
        self.setMinimumWidth(240)
        self.setStyleSheet(
            f"QWidget {{ background: {BG_PANEL}; }}"
            f"QScrollArea {{ border: none; background: {BG_PANEL}; }}"
        )
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QLabel("DETALLE DEL TRACK")
        hdr.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; font-weight: 600; letter-spacing: 1.4px;"
            f"padding: 10px 14px 6px; background: {BG_PANEL}; border-bottom: 1px solid {LINE};"
        )
        root.addWidget(hdr)

        # Área scrolleable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {BG_PANEL}; }}")

        inner = QWidget()
        inner.setStyleSheet(f"background: {BG_PANEL};")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 10, 14, 14)
        lay.setSpacing(12)

        # Artwork
        self._artwork = ArtworkWidget()
        lay.addWidget(self._artwork)

        # Stats (BPM + Key)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._card_bpm = StatCard("BPM")
        self._card_key = StatCard("Key · Camelot")
        stats_row.addWidget(self._card_bpm)
        stats_row.addWidget(self._card_key)
        lay.addLayout(stats_row)

        # Energía manual
        ener_hdr = QHBoxLayout()
        ener_lbl = QLabel("ENERGÍA — MANUAL")
        ener_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 9px; font-weight: 600; letter-spacing: 1.2px;"
        )
        self._ener_val = QLabel("—")
        self._ener_val.setStyleSheet(
            f"color: {TEXT_MUTED}; font-family: 'JetBrains Mono','Consolas',monospace; font-size: 11px;"
        )
        ener_hdr.addWidget(ener_lbl)
        ener_hdr.addStretch()
        ener_hdr.addWidget(self._ener_val)
        lay.addLayout(ener_hdr)

        self._energy_sel = EnergySelectorWidget()
        self._energy_sel.energy_changed.connect(self._on_energy_changed)
        lay.addWidget(self._energy_sel)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {LINE}; max-height: 1px;")
        lay.addWidget(sep)

        # Metadata
        self._meta_container = QVBoxLayout()
        self._meta_container.setSpacing(0)
        lay.addLayout(self._meta_container)

        lay.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

    # ───────────────────────────────────────── API pública ────────────────────

    def mostrar_track(self, track: dict | None):
        """Actualiza el panel con los datos del track dado."""
        # Limpiar metadata anterior
        while self._meta_container.count():
            item = self._meta_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not track:
            self._track_id = None
            self._artwork.set_track("", "")
            self._card_bpm.set_value("—")
            self._card_key.set_value("—")
            self._energy_sel.set_nivel(0)
            self._ener_val.setText("—")
            return

        self._track_id = track.get("id")

        # Artwork
        self._artwork.set_track(
            track.get("titulo") or "",
            track.get("artista") or "",
        )

        # BPM
        bpm = track.get("bpm")
        try:
            bpm_str = str(int(float(bpm))) if bpm and float(bpm) > 0 else "—"
        except (TypeError, ValueError):
            bpm_str = "—"
        self._card_bpm.set_value(bpm_str, CYAN)

        # Key Camelot
        cam = (track.get("camelot") or "").strip()
        cam_color = _camelot_color(cam).name() if cam else TEXT_MUTED
        self._card_key.set_value(cam or "—", cam_color)

        # Energía
        energia = track.get("energia_ef") or track.get("energia_manual") or track.get("energia")
        if energia is not None:
            nivel = max(1, min(10, int(round(float(energia)))))
            self._energy_sel.set_nivel(nivel)
            color = _energy_color(nivel).name()
            self._ener_val.setText(f'<span style="color:{color}; font-weight:700">{nivel}</span>/10')
        else:
            self._energy_sel.set_nivel(0)
            self._ener_val.setText("—")

        # Metadata
        def _fmt_dur(seg):
            try:
                s = int(float(seg))
                return f"{s//60:d}:{s%60:02d}"
            except Exception:
                return "—"

        rows = [
            ("Sello",    track.get("sello"),      False),
            ("Año",      track.get("anio"),        True),
            ("Formato",  (track.get("formato") or "").upper(), True),
            ("Bitrate",  f"{track.get('bitrate_kbps') or '—'} kbps", True),
            ("Duración", _fmt_dur(track.get("duracion_seg")), True),
            ("Género",   track.get("genero"),      False),
            ("Subgénero",track.get("subgenero"),   False),
        ]
        for label, val, mono in rows:
            row_w = _meta_row(label, str(val) if val else "—", mono)
            self._meta_container.addWidget(row_w)

        # Ruta (truncada)
        ruta = track.get("ruta_origen") or ""
        if ruta:
            ruta_lbl = QLabel(ruta)
            ruta_lbl.setStyleSheet(
                "font-family: 'JetBrains Mono','Consolas',monospace; font-size: 9px;"
                f"color: {TEXT_MUTED}; padding-top: 6px;"
            )
            ruta_lbl.setWordWrap(True)
            ruta_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._meta_container.addWidget(ruta_lbl)

    # ───────────────────────────────────────── señales ────────────────────────

    def _on_energy_changed(self, nivel: int):
        if self._track_id is None:
            return
        self.energy_manual_changed.emit(self._track_id, nivel)
        color = _energy_color(nivel).name()
        self._ener_val.setText(f'<span style="color:{color}; font-weight:700">{nivel}</span>/10')
