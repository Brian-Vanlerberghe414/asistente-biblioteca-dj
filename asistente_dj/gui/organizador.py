from __future__ import annotations

import os
import random
import subprocess
import sys

from PySide6.QtCore import Qt, QSortFilterProxyModel, QUrl, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSlider, QSpinBox, QSplitter, QTableView,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
    QHeaderView, QAbstractItemView, QStyledItemDelegate,
)

from gui.marquee_label import MarqueeLabel
from gui.track_table_view import TrackTableView


def _icon_triangle(direction: str, color: str, size: int = 16) -> QIcon:
    """Ícono ▶/◀ simple dibujado a mano (evita depender de glifos Unicode)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    path = QPainterPath()
    if direction == "right":
        path.moveTo(3, 2); path.lineTo(3, size - 2); path.lineTo(size - 3, size / 2)
    else:
        path.moveTo(size - 3, 2); path.lineTo(size - 3, size - 2); path.lineTo(3, size / 2)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def _icon_play(color: str, size: int = 18) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(size * 0.32, size * 0.18)
    path.lineTo(size * 0.32, size * 0.82)
    path.lineTo(size * 0.82, size * 0.5)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return QIcon(pix)


def _icon_pause(color: str, size: int = 18) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    bar_w = size * 0.18
    p.drawRect(int(size * 0.28), int(size * 0.18), int(bar_w), int(size * 0.64))
    p.drawRect(int(size * 0.54), int(size * 0.18), int(bar_w), int(size * 0.64))
    p.end()
    return QIcon(pix)


def _icon_stop(color: str, size: int = 18) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    s = size * 0.56
    off = (size - s) / 2
    p.drawRoundedRect(int(off), int(off), int(s), int(s), 2, 2)
    p.end()
    return QIcon(pix)


def _icon_shuffle(color: str, size: int = 16) -> QIcon:
    """Ícono de aleatorio (dos flechas cruzadas) dibujado a mano."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    from PySide6.QtGui import QPen
    pen = QPen(QColor(color))
    pen.setWidthF(1.6)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.drawLine(2, 4, size - 4, size - 4)
    p.drawLine(2, size - 4, size - 4, 4)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    for ty in (4, size - 4):
        head = QPainterPath()
        head.moveTo(size - 6, ty - 3)
        head.lineTo(size - 1, ty)
        head.lineTo(size - 6, ty + 3)
        head.closeSubpath()
        p.drawPath(head)
    p.end()
    return QIcon(pix)

# ruta al paquete principal
_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
import artist_db
from config import GENRE_TREE, FOLDER_INCOMING, FOLDER_REVIEW
from gui.bpm_delegate import BpmDelegate as BpmEditDelegate
from gui.delegate_artista import ArtistaDelegate
from gui.detalle_panel import DetallePanelWidget
from gui.genero_delegate import GeneroDelegate
from gui.track_model import (
    TrackModel, COL_CHECK, COL_ARTISTA, COL_BPM, COL_CAMELOT, COL_CARATULA,
    COL_ENERGIA, COL_ESTADO, COL_GENERO, COL_SUBGENERO, COL_TITULO,
)
from gui.visual_delegates import (
    BpmDelegate, CamelotDelegate, CoverDelegate, EnergyDelegate, StatusDelegate,
    PlayButtonDelegate,
)
from gui.cover_loader import obtener as _cover_loader
from gui.waveform_widget import WaveformWidget
from gui.theme import GENRE_COLORS

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    _HAS_MEDIA = True
except ImportError:
    _HAS_MEDIA = False


# ─────────────────────────────────────── compatibilidad Camelot ──────────────

def _camelot_compatibles(cam: str) -> set[str]:
    """Devuelve el conjunto de claves Camelot compatibles (misma clave ± 1 número,
    relativo mayor/menor)."""
    cam = (cam or "").strip().upper()
    if not cam or len(cam) < 2:
        return set()
    letra = cam[-1]   # 'A' o 'B'
    try:
        num = int(cam[:-1])
    except ValueError:
        return set()
    otras = {cam}
    for delta in (-1, 0, 1):
        n = ((num - 1 + delta) % 12) + 1
        otras.add(f"{n}{letra}")
    # relativo mayor/menor: misma escala, letra contraria
    rel_letra = "B" if letra == "A" else "A"
    otras.add(f"{num}{rel_letra}")
    return otras


# ──────────────────────────────────────────────────────── player ──────────────

class PlayerWidget(QFrame):
    """Reproductor con QMediaPlayer (pausa, seek, posición), waveform y shuffle."""

    track_actual_changed = Signal(object)  # id del track que empieza a sonar (o None)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)

        self._cola: list[dict] = []
        self._idx: int = 0
        self._shuffle: bool = False
        self._fallback_proc = None   # subprocess ffplay para formatos sin soporte

        # ── QMediaPlayer ──────────────────────────────────────────────────────
        if _HAS_MEDIA:
            self._player = QMediaPlayer(self)
            self._audio  = QAudioOutput(self)
            self._player.setAudioOutput(self._audio)
            self._audio.setVolume(1.0)
            self._player.positionChanged.connect(self._on_position)
            self._player.durationChanged.connect(self._on_duration)
            self._player.mediaStatusChanged.connect(self._on_media_status)
            self._player.errorOccurred.connect(self._on_error)
        else:
            self._player = None
            self._audio  = None

        self._build_ui()

    def _build_ui(self):
        from gui.theme import BG_ELEVATED, LINE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CYAN
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.setStyleSheet(
            f"background: {BG_ELEVATED}; border-top: 1px solid {LINE};"
        )

        # ── fila principal: now-playing | controles | waveform | volumen ─────
        main_row = QHBoxLayout()
        main_row.setContentsMargins(12, 8, 12, 4)
        main_row.setSpacing(12)

        # Now-playing (artwork placeholder + texto)
        self._thumb = QLabel()
        self._thumb.setFixedSize(48, 48)
        self._thumb.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #0a1e3c, stop:1 #1e0a30); border-radius: 6px;"
        )
        main_row.addWidget(self._thumb)

        now_col = QVBoxLayout()
        now_col.setSpacing(2)
        self._lbl_track = MarqueeLabel(220, TEXT_PRIMARY, font_size=13, weight=600)
        self._lbl_artist = MarqueeLabel(220, TEXT_SECONDARY, font_size=11)
        self._lbl_bpm_key = QLabel("")
        self._lbl_bpm_key.setStyleSheet(
            "font-family: 'JetBrains Mono','Consolas',monospace; font-size: 12px;"
        )
        now_col.addWidget(self._lbl_track)
        now_col.addWidget(self._lbl_artist)
        now_col.addWidget(self._lbl_bpm_key)
        main_row.addLayout(now_col)
        main_row.addSpacing(8)

        # Controles de transporte — íconos dibujados a mano (sin chrome de botón)
        icon_btn_qss = (
            "QPushButton { background: transparent; border: none; }"
        )
        self._icon_shuffle_off = _icon_shuffle(TEXT_SECONDARY)
        self._icon_shuffle_on  = _icon_shuffle(CYAN)

        self.btn_shuffle = self._make_btn("", 32)
        self.btn_shuffle.setIcon(self._icon_shuffle_off)
        self.btn_shuffle.setIconSize(QSize(16, 16))
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setToolTip("Aleatorio")
        self.btn_shuffle.setStyleSheet(icon_btn_qss)

        self.btn_prev = self._make_btn("", 32)
        self.btn_prev.setIcon(_icon_triangle("left", TEXT_SECONDARY))
        self.btn_prev.setIconSize(QSize(16, 16))
        self.btn_prev.setStyleSheet(icon_btn_qss)

        self._icon_play  = _icon_play("#06181C")
        self._icon_pause = _icon_pause("#06181C")
        self._icon_stop  = _icon_stop("#06181C")
        self.btn_play = self._make_btn("", 52)
        self.btn_play.setIcon(self._icon_play)
        self.btn_play.setIconSize(QSize(18, 18))
        self.btn_play.setFixedHeight(52)
        self.btn_play.setStyleSheet(
            f"QPushButton {{ background: {CYAN}; border-radius: 26px;"
            "border: none; }}"
            f"QPushButton:hover {{ background: #33EBFF; }}"
        )

        self.btn_next = self._make_btn("", 32)
        self.btn_next.setIcon(_icon_triangle("right", TEXT_SECONDARY))
        self.btn_next.setIconSize(QSize(16, 16))
        self.btn_next.setStyleSheet(icon_btn_qss)

        self.btn_shuffle.toggled.connect(self._on_shuffle_icon)
        self.btn_shuffle.toggled.connect(self._on_shuffle_toggle)
        self.btn_prev.clicked.connect(self.anterior)
        self.btn_play.clicked.connect(self._toggle)
        self.btn_next.clicked.connect(self.siguiente)

        transport = QHBoxLayout()
        transport.setSpacing(12)
        transport.addWidget(self.btn_shuffle)
        transport.addWidget(self.btn_prev)
        transport.addWidget(self.btn_play)
        transport.addWidget(self.btn_next)
        main_row.addLayout(transport)
        main_row.addSpacing(8)

        # opciones shuffle ocultas
        self._chk_bpm = QCheckBox("BPM ±8")
        self._chk_bpm.setChecked(True)
        self._chk_bpm.setVisible(False)
        self._chk_harm = QCheckBox("Armónico")
        self._chk_harm.setChecked(True)
        self._chk_harm.setVisible(False)
        main_row.addWidget(self._chk_bpm)
        main_row.addWidget(self._chk_harm)

        # Waveform + tiempo
        wave_col = QVBoxLayout()
        wave_col.setSpacing(2)
        self._waveform = WaveformWidget(self)
        self._waveform.seek_requested.connect(self._seek)
        self._waveform.setMinimumHeight(48)
        self._waveform.setMaximumHeight(56)
        wave_col.addWidget(self._waveform)

        time_row = QHBoxLayout()
        self._lbl_pos = QLabel("--:--")
        self._lbl_pos.setStyleSheet(
            f"color: {CYAN}; font-family: 'JetBrains Mono','Consolas',monospace; font-size: 11px;"
        )
        self._lbl_dur = QLabel("--:--")
        self._lbl_dur.setStyleSheet(
            f"color: {TEXT_MUTED}; font-family: 'JetBrains Mono','Consolas',monospace; font-size: 11px;"
        )
        # mantiene compatibilidad con código que usa _lbl_time
        self._lbl_time = self._lbl_pos
        time_row.addWidget(self._lbl_pos)
        time_row.addStretch()
        time_row.addWidget(self._lbl_dur)
        wave_col.addLayout(time_row)
        main_row.addLayout(wave_col, stretch=1)
        main_row.addSpacing(8)

        # Volumen
        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        self._lbl_vol = QLabel("🔊")
        self._lbl_vol.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        self._slider_vol = QSlider(Qt.Horizontal)
        self._slider_vol.setRange(0, 100)
        self._slider_vol.setValue(80)
        self._slider_vol.setFixedWidth(90)
        self._slider_vol.setToolTip("Volumen")
        self._slider_vol.valueChanged.connect(self._on_volumen)
        vol_row.addWidget(self._lbl_vol)
        vol_row.addWidget(self._slider_vol)
        main_row.addLayout(vol_row)

        lay.addLayout(main_row)

    def _make_btn(self, label: str, w: int) -> QPushButton:
        b = QPushButton(label, self)
        b.setFixedWidth(w)
        return b

    # ──────────────────────────────────────────────────── API pública ─────────

    def cargar_cola(self, filas: list[dict], idx: int = 0):
        """Carga una nueva lista de tracks y comienza reproducción en idx."""
        self.parar()
        self._cola = list(filas)
        self._idx  = max(0, min(idx, len(filas) - 1))
        self._reproducir()

    def parar(self):
        if self._player:
            self._player.stop()
        if self._fallback_proc and self._fallback_proc.poll() is None:
            self._fallback_proc.terminate()
        self._fallback_proc = None
        self.btn_play.setIcon(self._icon_play)

    def siguiente(self):
        if not self._cola:
            return
        if self._shuffle:
            nxt = self._elegir_aleatorio()
        else:
            nxt = self._idx + 1 if self._idx < len(self._cola) - 1 else None
        if nxt is not None:
            self._idx = nxt
            self._reproducir()

    def anterior(self):
        if self._idx > 0:
            self._idx -= 1
            self._reproducir()

    # ──────────────────────────────────────────────────── shuffle ─────────────

    def _on_shuffle_icon(self, activo: bool):
        self.btn_shuffle.setIcon(self._icon_shuffle_on if activo else self._icon_shuffle_off)

    def _on_shuffle_toggle(self, activo: bool):
        self._shuffle = activo
        self._chk_bpm.setVisible(activo)
        self._chk_harm.setVisible(activo)

    def _elegir_aleatorio(self) -> int | None:
        """Elige el próximo índice usando las prioridades configuradas."""
        if len(self._cola) <= 1:
            return None
        actual = self._cola[self._idx]
        bpm_actual  = _parse_bpm_f(actual.get("bpm"))
        cam_actual  = (actual.get("camelot") or "").strip().upper()
        compatibles = _camelot_compatibles(cam_actual)

        candidatos = [i for i in range(len(self._cola)) if i != self._idx]

        usar_bpm  = self._chk_bpm.isChecked()
        usar_harm = self._chk_harm.isChecked()

        if usar_bpm or usar_harm:
            filtrados = candidatos
            if usar_bpm and bpm_actual:
                filtrados = [i for i in filtrados
                             if _bpm_cerca(self._cola[i].get("bpm"), bpm_actual, 8)]
            if usar_harm and compatibles:
                filtrados = [i for i in filtrados
                             if (self._cola[i].get("camelot") or "").upper() in compatibles]
            if filtrados:
                return random.choice(filtrados)
            # Fallback: sin restricciones
        return random.choice(candidatos)

    # ──────────────────────────────────────────────────── reproducción ────────

    def _reproducir(self):
        self.parar()
        if not self._cola:
            return
        r   = self._cola[self._idx]
        ruta = r.get("ruta_origen", "")
        self.track_actual_changed.emit(r.get("id"))
        self._actualizar_label(r)
        self._waveform.set_track(r.get("waveform_data"), 0)

        if not ruta or not os.path.exists(ruta):
            self._lbl_track.setText(self._lbl_track.text() + "  [archivo no encontrado]")
            return

        if self._player:
            self._player.setSource(QUrl.fromLocalFile(ruta))
            self._player.play()
            self.btn_play.setIcon(self._icon_pause)
        else:
            self._fallback_ffplay(ruta)

    def _toggle(self):
        if self._player:
            st = self._player.playbackState()
            from PySide6.QtMultimedia import QMediaPlayer as QMP
            if st == QMP.PlayingState:
                self._player.pause()
                self.btn_play.setIcon(self._icon_play)
            else:
                self._player.play()
                self.btn_play.setIcon(self._icon_pause)
        else:
            if self._fallback_proc and self._fallback_proc.poll() is None:
                self._fallback_proc.terminate()
                self._fallback_proc = None
                self.btn_play.setIcon(self._icon_play)
            elif self._cola:
                self._fallback_ffplay(self._cola[self._idx].get("ruta_origen", ""))

    def _seek(self, ms: int):
        if self._player:
            self._player.setPosition(ms)

    # ──────────────────────────────────────────────── señales QMediaPlayer ────

    def _on_position(self, ms: int):
        self._waveform.set_position(ms)
        self._lbl_pos.setText(_fmt_tiempo(ms))
        self._lbl_dur.setText(_fmt_tiempo(self._player.duration()))

    def _on_duration(self, ms: int):
        self._waveform.set_duration(ms)

    def _on_media_status(self, status):
        from PySide6.QtMultimedia import QMediaPlayer as QMP
        if status == QMP.MediaStatus.EndOfMedia:
            self.siguiente()

    def _on_error(self, error, msg: str):
        """QMediaPlayer no pudo abrir el formato → fallback a ffplay."""
        if self._cola:
            ruta = self._cola[self._idx].get("ruta_origen", "")
            if ruta:
                self._fallback_ffplay(ruta)

    # ─────────────────────────────────────────────────── helpers ──────────────

    def _on_volumen(self, val: int):
        if self._audio:
            self._audio.setVolume(val / 100.0)

    def _fallback_ffplay(self, ruta: str):
        try:
            self._fallback_proc = subprocess.Popen(
                ["ffplay", "-autoexit", "-nodisp", "-loglevel", "quiet", ruta]
            )
            self.btn_play.setIcon(self._icon_stop)
        except FileNotFoundError:
            self._lbl_track.setText(self._lbl_track.text() + "  [ffplay no encontrado]")

    def _actualizar_label(self, r: dict):
        artista = r.get("artista") or "?"
        titulo  = r.get("titulo")  or "?"
        bpm     = r.get("bpm")     or "—"
        cam     = (r.get("camelot") or "").strip()
        self._lbl_track.setText(titulo)
        self._lbl_artist.setText(artista)
        bpm_str = str(int(float(bpm))) if bpm and str(bpm) not in ("—", "0", "") else "—"
        from gui.theme import TEXT_SECONDARY, TEXT_MUTED, CYAN
        self._lbl_bpm_key.setText(
            f'<span style="color:{TEXT_SECONDARY}">{bpm_str} BPM</span>'
            f'<span style="color:{TEXT_MUTED}"> · </span>'
            f'<span style="color:{CYAN}">{cam or "—"}</span>'
        )
        self._lbl_pos.setText("--:--")
        self._lbl_dur.setText("--:--")

    def set_cola_silente(self, filas: list[dict]):
        """Actualiza la cola sin interrumpir la reproducción.
        Intenta conservar el track actual por ruta_origen."""
        if not filas:
            self._cola = []
            self._idx  = 0
            return
        ruta_actual = (self._cola[self._idx].get("ruta_origen")
                       if self._cola else None)
        self._cola = list(filas)
        # Buscar el track actual en la nueva cola
        nuevo_idx = 0
        if ruta_actual:
            for i, r in enumerate(self._cola):
                if r.get("ruta_origen") == ruta_actual:
                    nuevo_idx = i
                    break
        self._idx = nuevo_idx

    def closeEvent(self, event):
        self.parar()
        super().closeEvent(event)


def _fmt_tiempo(ms: int) -> str:
    s = max(ms, 0) // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


def _parse_bpm_f(v) -> float | None:
    try:
        f = float(str(v).replace(",", "."))
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _bpm_cerca(v, ref: float, margen: float) -> bool:
    b = _parse_bpm_f(v)
    return b is not None and abs(b - ref) <= margen


# ───────────────────────────────────────────────────────── proxy con filtros ──

class FiltroProxy(QSortFilterProxyModel):
    """Proxy que filtra por texto (artista/título/sello), BPM, Key Camelot y Energía."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._texto    = ""
        self._bpm_min  = 0
        self._bpm_max  = 0
        self._key      = ""
        self._energia  = 0

    def set_texto(self, t: str):
        self._texto = t.strip()
        self.invalidateFilter()

    def set_bpm(self, min_v: int, max_v: int):
        self._bpm_min = min_v
        self._bpm_max = max_v
        self.invalidateFilter()

    def set_key(self, k: str):
        self._key = k.strip().upper()
        self.invalidateFilter()

    def set_energia(self, v: int):
        self._energia = v
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent):
        fila = self.sourceModel().fila(source_row)

        # Texto: artista, título, sello
        if self._texto:
            t = self._texto.lower()
            if not any(t in str(fila.get(c) or "").lower()
                       for c in ("artista", "titulo", "sello")):
                return False

        # BPM
        if self._bpm_min or self._bpm_max:
            try:
                bpm = float(fila.get("bpm") or 0)
                if self._bpm_min and bpm < self._bpm_min:
                    return False
                if self._bpm_max and bpm > self._bpm_max:
                    return False
            except (ValueError, TypeError):
                if self._bpm_min:
                    return False

        # Key (Camelot exacto)
        if self._key:
            if (fila.get("camelot") or "").upper() != self._key:
                return False

        # Energía mínima
        if self._energia:
            ener = fila.get("energia_ef")
            if ener is None or int(ener) < self._energia:
                return False

        return True


# ──────────────────────────────────────────────────────────────── organizador ──

class OrganizadorWidget(QWidget):
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._filtro_genero: str | None = None
        self._filtro_subgenero: str | None = None

        # Modelo de datos
        self._model = TrackModel(self._db_path, self)
        self._proxy = FiltroProxy(self)
        self._proxy.setSourceModel(self._model)

        self._build_ui()
        self.recargar()

    # --------------------------------------------------------------- layout
    def _build_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self._splitter = QSplitter(Qt.Horizontal, self)
        splitter = self._splitter

        # ---- panel izquierdo: árbol de géneros (fijo, no colapsable) ----
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setMinimumWidth(160)
        self._tree.setMaximumWidth(260)
        # Sin flechita de expandir (un click en el nombre ya abre/cierra, ver
        # _on_tree_click): así los géneros sin subgénero no quedan más a la
        # izquierda que los que sí tienen — todos arrancan en la misma
        # columna. setItemsExpandable(False) saca el control nativo, pero
        # item.setExpanded() programático sigue funcionando igual.
        self._tree.setRootIsDecorated(False)
        self._tree.setItemsExpandable(False)
        self._tree.setIndentation(10)
        self._tree.currentItemChanged.connect(self._on_tree_click)
        self._tree.itemExpanded.connect(self._on_genero_expandido)

        splitter.addWidget(self._tree)

        # ---- área central ----
        centro = QWidget()
        centro_lay = QVBoxLayout(centro)
        centro_lay.setContentsMargins(4, 4, 4, 0)
        centro_lay.setSpacing(4)

        # ── barra de búsqueda ─────────────────────────────────────────────────
        busq_bar = QHBoxLayout()
        self._lbl_count = QLabel()
        self._busq = QLineEdit()
        self._busq.setPlaceholderText("🔍 Buscar artista, título, sello…")
        self._busq.textChanged.connect(self._proxy.set_texto)
        self._busq.textChanged.connect(self._actualizar_contador)
        busq_bar.addWidget(self._busq, stretch=1)
        busq_bar.addWidget(self._lbl_count)

        # Guardar / Cancelar — al margen derecho de esta misma barra,
        # oculto hasta que haya cambios pendientes en la grilla.
        self._barra_guardado = QWidget()
        guardado_lay = QHBoxLayout(self._barra_guardado)
        guardado_lay.setContentsMargins(12, 0, 0, 0)
        guardado_lay.setSpacing(6)
        self._btn_cancelar = QPushButton("✗  Cancelar")
        self._btn_guardar  = QPushButton("✓  Guardar")
        self._btn_guardar.setStyleSheet(
            "QPushButton { background:#2a7ae2; color:white; font-weight:bold;"
            " padding:4px 16px; border-radius:4px; }"
            "QPushButton:hover { background:#1a5cb8; }"
        )
        self._btn_cancelar.clicked.connect(self._on_cancelar)
        self._btn_guardar.clicked.connect(self._on_guardar)
        guardado_lay.addWidget(self._btn_cancelar)
        guardado_lay.addWidget(self._btn_guardar)
        self._barra_guardado.setVisible(False)
        busq_bar.addWidget(self._barra_guardado)

        centro_lay.addLayout(busq_bar)

        # ── fila de filtros BPM / Key / Energía ──────────────────────────────
        filtros_bar = QHBoxLayout()
        filtros_bar.setSpacing(6)

        self._btn_seleccionar = QPushButton("☐  Seleccionar")
        self._btn_seleccionar.setCheckable(True)
        self._btn_seleccionar.setToolTip(
            "Mostrar checkboxes para elegir varios tracks (crear playlist / eliminar)")
        self._btn_seleccionar.toggled.connect(self._on_toggle_seleccion)
        filtros_bar.addWidget(self._btn_seleccionar)
        filtros_bar.addSpacing(10)

        filtros_bar.addWidget(QLabel("BPM:"))
        self._bpm_min_spin = QSpinBox()
        self._bpm_min_spin.setRange(0, 220)
        self._bpm_min_spin.setValue(0)
        self._bpm_min_spin.setSpecialValueText("—")
        self._bpm_min_spin.setFixedWidth(55)
        self._bpm_min_spin.setToolTip("BPM mínimo (0 = sin límite)")
        filtros_bar.addWidget(self._bpm_min_spin)
        filtros_bar.addWidget(QLabel("–"))
        self._bpm_max_spin = QSpinBox()
        self._bpm_max_spin.setRange(0, 220)
        self._bpm_max_spin.setValue(0)
        self._bpm_max_spin.setSpecialValueText("—")
        self._bpm_max_spin.setFixedWidth(55)
        self._bpm_max_spin.setToolTip("BPM máximo (0 = sin límite)")
        filtros_bar.addWidget(self._bpm_max_spin)

        filtros_bar.addSpacing(12)
        filtros_bar.addWidget(QLabel("Key:"))
        self._key_combo = QComboBox()
        self._key_combo.setFixedWidth(80)
        self._key_combo.addItem("— Todas —")
        for n in range(1, 13):
            self._key_combo.addItem(f"{n}A")
        for n in range(1, 13):
            self._key_combo.addItem(f"{n}B")
        filtros_bar.addWidget(self._key_combo)

        filtros_bar.addSpacing(12)
        filtros_bar.addWidget(QLabel("E ≥"))
        self._energia_spin = QSpinBox()
        self._energia_spin.setRange(0, 10)
        self._energia_spin.setValue(0)
        self._energia_spin.setSpecialValueText("—")
        self._energia_spin.setFixedWidth(50)
        self._energia_spin.setToolTip("Energía mínima (0 = sin filtro)")
        filtros_bar.addWidget(self._energia_spin)

        filtros_bar.addSpacing(8)
        btn_reset = QPushButton("✕")
        btn_reset.setFixedWidth(28)
        btn_reset.setToolTip("Limpiar todos los filtros")
        btn_reset.clicked.connect(self._reset_filtros)
        filtros_bar.addWidget(btn_reset)
        filtros_bar.addStretch()

        self._bpm_min_spin.valueChanged.connect(self._aplicar_filtros_bpm)
        self._bpm_max_spin.valueChanged.connect(self._aplicar_filtros_bpm)
        self._key_combo.currentTextChanged.connect(self._aplicar_filtro_key)
        self._energia_spin.valueChanged.connect(
            lambda v: self._proxy.set_energia(v))

        centro_lay.addLayout(filtros_bar)

        # El proxy avisa cuando cambió el filtro → actualizar cola y contador
        self._proxy.layoutChanged.connect(self._actualizar_contador)
        self._proxy.layoutChanged.connect(self._on_filtro_cambiado)

        # tabla
        self._tabla = TrackTableView()
        self._tabla.setModel(self._proxy)
        self._tabla.setSortingEnabled(True)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.horizontalHeader().setStretchLastSection(False)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tabla.verticalHeader().setDefaultSectionSize(30)
        self._tabla.verticalHeader().hide()
        self._tabla.setShowGrid(True)
        self._tabla.doubleClicked.connect(self._on_double_click)
        self._tabla.clicked.connect(self._on_click)
        # Delegates de edición
        self._tabla.setItemDelegateForColumn(COL_ARTISTA, ArtistaDelegate(self._db_path, self._tabla))
        self._tabla.setItemDelegateForColumn(COL_BPM, BpmEditDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_GENERO, GeneroDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_SUBGENERO, GeneroDelegate(self._tabla))
        # Delegates de visualización
        self._tabla.setItemDelegateForColumn(COL_CARATULA, CoverDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_BPM,     BpmDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_CAMELOT, CamelotDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_ENERGIA, EnergyDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_ESTADO,  StatusDelegate(self._tabla))
        # Repintar la grilla cuando una carátula termina de descargarse
        # (la celda ya tiene la URL desde antes; solo falta la imagen).
        _cover_loader().cargada.connect(lambda _u: self._tabla.viewport().update())
        # Columna 0: modo dual Play / Selección (checkbox)
        self._delegate_play = PlayButtonDelegate(self._tabla)
        self._delegate_play.play_requested.connect(self._on_play_clicked)
        self._delegate_checkbox = QStyledItemDelegate(self._tabla)
        self._tabla.setItemDelegateForColumn(COL_CHECK, self._delegate_play)
        centro_lay.addWidget(self._tabla, stretch=1)

        splitter.addWidget(centro)

        # ---- panel derecho: detalle del track ----
        self._detalle = DetallePanelWidget(self._db_path, self)
        self._detalle.energy_manual_changed.connect(self._on_energy_manual)
        splitter.addWidget(self._detalle)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setCollapsible(0, False)

        root_lay.addWidget(splitter, stretch=1)

        # ---- player ----
        self._player = PlayerWidget(self)
        self._player.track_actual_changed.connect(self._on_track_actual_changed)
        root_lay.addWidget(self._player)

        # Mostrar/ocultar la barra de Guardar/Cancelar (en busq_bar) según
        # cambios pendientes en el modelo.
        self._model.dataChanged.connect(self._actualizar_barra_guardado)
        self._model.modelReset.connect(self._actualizar_barra_guardado)

    # ---------------------------------------------------------------- datos
    def recargar(self):
        """Recarga árbol y tabla desde la BD."""
        conn = db_mod.connect(self._db_path)
        self._poblar_arbol(conn)
        self._model.recargar(conn, self._filtro_genero, self._filtro_subgenero)
        conn.close()
        self._actualizar_contador()
        self._ajustar_columnas()

    def _poblar_arbol(self, conn):
        """Llena el QTreeWidget con géneros + contadores desde la BD."""
        contadores: dict[tuple, int] = {}
        for r in conn.execute(
            "SELECT genero, subgenero, COUNT(*) AS n FROM tracks "
            "GROUP BY genero, subgenero"
        ):
            contadores[(r["genero"], r["subgenero"])] = r["n"]

        sin_genero = conn.execute(
            "SELECT COUNT(*) AS n FROM tracks WHERE genero IS NULL"
        ).fetchone()["n"]

        self._tree.clear()

        # raíz: Tu Música (todos los tracks clasificados)
        total_todos = sum(contadores.values())
        root = QTreeWidgetItem(self._tree, [f"Tu Música  ({total_todos})"])
        root.setData(0, Qt.UserRole, None)   # None = sin filtro = todos clasificados
        root.setExpanded(True)

        # géneros del árbol bajo la raíz
        for genero, subgeneros in GENRE_TREE.items():
            total_g = sum(
                v for (g, _), v in contadores.items() if g == genero
            )
            if total_g == 0:
                continue
            item_g = QTreeWidgetItem(root, [f"● {genero}  ({total_g})"])
            item_g.setData(0, Qt.UserRole, (genero, None))
            # Acordeón: solo el género activo queda desplegado.
            item_g.setExpanded(genero == self._filtro_genero)
            g_color = QColor(GENRE_COLORS.get(genero, "#9A9CA1"))
            item_g.setForeground(0, g_color)
            font_g = item_g.font(0)
            font_g.setWeight(font_g.Weight.DemiBold)
            item_g.setFont(0, font_g)
            for sub in subgeneros:
                n = contadores.get((genero, sub), 0)
                if n == 0:
                    continue
                item_s = QTreeWidgetItem(item_g, [f"  {sub}  ({n})"])
                item_s.setData(0, Qt.UserRole, (genero, sub))
                item_s.setForeground(0, QColor("#9A9CA1"))

        # "Género no reconocido" como hijo de la raíz
        if sin_genero > 0:
            item_rev = QTreeWidgetItem(root, [f"Género no reconocido  ({sin_genero})"])
            item_rev.setData(0, Qt.UserRole, ("_Por revisar", None))

    def _on_tree_click(self, current, _previous):
        if current is None:
            return
        dato = current.data(0, Qt.UserRole)
        if dato is None:
            self._filtro_genero = "_todos"
            self._filtro_subgenero = None
            conn = db_mod.connect(self._db_path)
            self._model.recargar(conn, self._filtro_genero, self._filtro_subgenero)
            conn.close()
        else:
            self._filtro_genero, self._filtro_subgenero = dato
            conn = db_mod.connect(self._db_path)
            self._model.recargar(conn, self._filtro_genero, self._filtro_subgenero)
            conn.close()
            # Clickear un género lo despliega (el acordeón cierra los demás).
            if dato[0] != "_Por revisar":
                current.setExpanded(True)
        self._actualizar_contador()
        self._on_filtro_cambiado()

    def _on_genero_expandido(self, item):
        """Acordeón: al desplegar un género, compacta sus hermanos."""
        padre = item.parent()
        if padre is None:
            return
        for i in range(padre.childCount()):
            hermano = padre.child(i)
            if hermano is not item and hermano.isExpanded():
                hermano.setExpanded(False)

    def _actualizar_contador(self):
        n = self._proxy.rowCount()
        self._lbl_count.setText(f"{n} tracks")

    def _filas_visibles(self) -> list[dict]:
        """Filas del modelo en el orden visible del proxy."""
        return [
            self._model.fila(self._proxy.mapToSource(
                self._proxy.index(i, 0)).row())
            for i in range(self._proxy.rowCount())
        ]

    def _on_filtro_cambiado(self, *_):
        """Al cambiar filtro o búsqueda: actualiza la cola del player silenciosamente."""
        if not hasattr(self, '_player'):
            return
        self._player.set_cola_silente(self._filas_visibles())

    def _ajustar_columnas(self):
        hdr = self._tabla.horizontalHeader()
        t   = self._tabla

        # Anchos de columnas visibles
        hdr.resizeSection(0,   28)   # Play / Selección
        hdr.resizeSection(COL_CARATULA, 34)   # Carátula
        hdr.resizeSection(2,  175)   # Artista
        hdr.resizeSection(3,  200)   # Título
        hdr.resizeSection(4,  120)   # Sello
        hdr.resizeSection(5,   58)   # BPM
        hdr.resizeSection(7,   72)   # Camelot
        hdr.resizeSection(8,   96)   # Energía
        hdr.resizeSection(COL_GENERO,    110)   # Género
        hdr.resizeSection(COL_SUBGENERO, 140)   # Subgénero
        hdr.resizeSection(11,  52)   # Formato
        hdr.resizeSection(13,  46)   # Año
        hdr.resizeSection(14, 100)   # Estado

        # Ocultar columnas no mostradas en la vista principal
        t.setColumnHidden(6,  True)  # Key (raw)
        t.setColumnHidden(12, True)  # kbps

    def _on_click(self, proxy_index):
        """Single click: actualiza el panel de detalle; en Género/Subgénero
        abre el editor inline directamente."""
        if proxy_index.column() == COL_CHECK:
            if self._btn_seleccionar.isChecked():
                # En modo selección, el delegate es un QStyledItemDelegate
                # genérico: el click solo en algunas plataformas alterna el
                # checkbox sin ayuda — lo hacemos explícito para que
                # funcione siempre, en vez de depender de eso.
                actual = proxy_index.data(Qt.CheckStateRole)
                nuevo = Qt.Unchecked if actual == Qt.Checked else Qt.Checked
                self._proxy.setData(proxy_index, nuevo, Qt.CheckStateRole)
            return
        row = proxy_index.row()
        src = self._proxy.mapToSource(self._proxy.index(row, 0))
        fila = self._model.fila(src.row())
        self._detalle.mostrar_track(fila)
        if proxy_index.column() in (COL_GENERO, COL_SUBGENERO):
            self._tabla.edit(proxy_index)

    def _on_play_clicked(self, proxy_index):
        """Click en el botón ▶ de una fila: única forma de reproducir un track."""
        row = proxy_index.row()
        src = self._proxy.mapToSource(self._proxy.index(row, 0))
        fila = self._model.fila(src.row())
        self._detalle.mostrar_track(fila)
        self._player.cargar_cola(self._filas_visibles(), row)

    def _on_toggle_seleccion(self, activo: bool):
        """Alterna la columna 0 entre botones Play y checkboxes de selección."""
        self._tabla.setItemDelegateForColumn(
            COL_CHECK, self._delegate_checkbox if activo else self._delegate_play)
        self._btn_seleccionar.setText("✓  Seleccionando" if activo else "☐  Seleccionar")
        self._tabla.viewport().update()

    def _on_track_actual_changed(self, track_id):
        self._model.set_id_reproduciendo(track_id)

    def _ids_visibles(self) -> list[int]:
        """IDs de los tracks actualmente visibles en la grilla (respeta filtro y búsqueda)."""
        ids = []
        for proxy_row in range(self._proxy.rowCount()):
            src = self._proxy.mapToSource(self._proxy.index(proxy_row, 0))
            fila = self._model.fila(src.row())
            tid = fila.get("id")
            if tid:
                ids.append(tid)
        return ids

    def _actualizar_barra_guardado(self, *_):
        """Muestra la barra Guardar/Cancelar solo si hay cambios pendientes."""
        self._barra_guardado.setVisible(self._model.hay_pendientes())

    def _aplicar_filtros_bpm(self):
        self._proxy.set_bpm(self._bpm_min_spin.value(), self._bpm_max_spin.value())

    def _aplicar_filtro_key(self, texto: str):
        self._proxy.set_key("" if texto == "— Todas —" else texto)

    def _reset_filtros(self):
        self._busq.clear()
        self._bpm_min_spin.setValue(0)
        self._bpm_max_spin.setValue(0)
        self._key_combo.setCurrentIndex(0)
        self._energia_spin.setValue(0)

    def _on_guardar(self):
        ids = self._ids_visibles()
        if not ids:
            return
        self._model.guardar_ids(ids)
        conn = db_mod.connect(self._db_path)
        self._poblar_arbol(conn)
        artist_db.registrar_desde_biblioteca(conn)
        # Recarga con el filtro activo: los tracks que cambiaron de género desaparecen
        self._model.recargar(conn, self._filtro_genero, self._filtro_subgenero)
        conn.close()
        self._actualizar_contador()
        self._ofrecer_contribucion(ids)

    def _ofrecer_contribucion(self, ids: list[int]):
        """Ofrece enviar los cambios guardados a la BD compartida Overcome Harmony."""
        try:
            import cloud_db
            if not cloud_db.configurado():
                return
        except Exception:
            return

        # Filtrar solo los que tienen huella acústica (necesaria para identificarlos)
        conn = db_mod.connect(self._db_path)
        con_huella = [
            r["id"] for r in conn.execute(
                f"SELECT id FROM tracks WHERE id IN ({','.join('?'*len(ids))}) "
                "AND huella IS NOT NULL", ids
            ).fetchall()
        ]
        conn.close()
        if not con_huella:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Contribuir a Overcome Harmony DB")
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)

        lay.addWidget(QLabel(
            f"¿Enviar {len(con_huella)} corrección(es) a la base de datos\n"
            "compartida de Overcome Harmony?\n\n"
            "Tu contribución ayuda a enriquecer la BD para todos los DJs."
        ))
        lbl_com = QLabel("Comentario opcional:")
        lay.addWidget(lbl_com)
        comentario_edit = QTextEdit()
        comentario_edit.setPlaceholderText("Ej: corregí el género de este track a Tech House…")
        comentario_edit.setMaximumHeight(70)
        lay.addWidget(comentario_edit)

        btns = QDialogButtonBox()
        btn_si = btns.addButton("Sí, enviar", QDialogButtonBox.AcceptRole)
        btn_no = btns.addButton("Solo guardar local", QDialogButtonBox.RejectRole)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() != QDialog.Accepted:
            return

        comentario = comentario_edit.toPlainText().strip()
        conn = db_mod.connect(self._db_path)
        enviados = fallidos = 0
        for tid in con_huella:
            try:
                ok = cloud_db.push_contribucion(conn, tid, comentario)
                if ok:
                    enviados += 1
                else:
                    cloud_db.encolar_pendiente(conn, tid)
                    fallidos += 1
            except Exception:
                cloud_db.encolar_pendiente(conn, tid)
                fallidos += 1
        conn.close()

        msg = f"Enviados: {enviados}"
        if fallidos:
            msg += f"  (quedaron {fallidos} en cola para reenviar cuando haya red)"
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "BD Compartida", msg)

    def _on_cancelar(self):
        ids = self._ids_visibles()
        if not ids:
            return
        self._model.cancelar_ids(ids)

    def _on_double_click(self, proxy_index):
        """Double-click: abre el editor inline en columnas editables.
        Género/Subgénero ya se abren con un solo click (ver _on_click)."""
        if proxy_index.column() in (COL_ARTISTA, COL_TITULO, COL_BPM):
            self._tabla.edit(proxy_index)

# -------------------------------------------------- acciones batch públicas
    def _on_energy_manual(self, track_id: int, nivel: int):
        """Guarda la energía manual editada desde el panel de detalle."""
        import db as _db
        conn = _db.connect(self._db_path)
        conn.execute(
            "UPDATE tracks SET energia_manual=? WHERE id=?", (nivel, track_id)
        )
        conn.commit()
        conn.close()
        for fila in self._model._filas:
            if fila.get("id") == track_id:
                fila["energia_manual"] = nivel
                fila["energia_ef"] = nivel
                break
        idx_top = self._model.index(0, COL_ENERGIA)
        idx_bot = self._model.index(self._model.rowCount() - 1, COL_ENERGIA)
        self._model.dataChanged.emit(idx_top, idx_bot)

    def ids_seleccionados(self) -> list[int]:
        return self._model.ids_seleccionados()

    def eliminar_seleccionados(self, borrar_disco: bool = False):
        ids = self._model.ids_seleccionados()
        if not ids:
            return
        conn = db_mod.connect(self._db_path)
        if borrar_disco:
            for tid in ids:
                row = conn.execute(
                    "SELECT ruta_origen FROM tracks WHERE id=?", (tid,)
                ).fetchone()
                if row and row["ruta_origen"] and os.path.exists(row["ruta_origen"]):
                    try:
                        os.remove(row["ruta_origen"])
                    except Exception:
                        pass
        ph = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM tracks WHERE id IN ({ph})", ids)
        conn.commit()
        conn.close()
        self._model.limpiar_seleccion()
        self.recargar()

    def closeEvent(self, event):
        self._player.parar()
        super().closeEvent(event)
