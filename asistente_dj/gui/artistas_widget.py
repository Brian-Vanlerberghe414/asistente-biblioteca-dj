"""Vista de artistas: tabla con nombre, géneros, fuente y fecha de actualización."""
from __future__ import annotations

import json
import os
import sys

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QTableView, QVBoxLayout, QWidget,
)

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
import artist_db
import settings as cfg


# ──────────────────────────────────────────────────────── modelo ──────────────

_COLS    = ["nombre", "generos_display", "fuente", "fecha_actualizacion"]
_HEADERS = ["Artista", "Géneros", "Fuente", "Actualizado"]


def _generos_display(generos_json: str | None) -> str:
    if not generos_json:
        return "—"
    try:
        pares = json.loads(generos_json)
    except (json.JSONDecodeError, TypeError):
        return "—"
    if not pares:
        return "—"
    partes = []
    for p in pares:
        g = p[0] if p else ""
        s = p[1] if len(p) > 1 and p[1] else None
        partes.append(f"{g} / {s}" if s else g)
    return ",  ".join(partes)


class ArtistasModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filas: list[dict] = []

    def recargar(self, conn):
        self.beginResetModel()
        self._filas = artist_db.todos(conn)
        for f in self._filas:
            f["generos_display"] = _generos_display(f.get("generos"))
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(_COLS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            v = self._filas[index.row()].get(_COLS[index.column()])
            return str(v) if v else "—"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _HEADERS[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):
        col = _COLS[column]
        self.beginResetModel()
        self._filas.sort(
            key=lambda r: (str(r.get(col) or "").lower()),
            reverse=(order == Qt.DescendingOrder),
        )
        self.endResetModel()


# ─────────────────────────────────────────────────────── widget ──────────────

class ArtistasWidget(QWidget):
    """Tab de artistas: gestión de BD de artistas con géneros permitidos."""

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._worker = None

        self._model = ArtistasModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(0)

        self._build_ui()
        self.recargar()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # ── fila 1: API key ──────────────────────────────────────────────
        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("Last.fm API Key:"))
        self._api_key = QLineEdit()
        self._api_key.setPlaceholderText("Ingresá tu API key de Last.fm…")
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setText(cfg.get("lastfm_api_key", ""))
        self._api_key.textChanged.connect(
            lambda v: cfg.set_("lastfm_api_key", v)
        )
        api_row.addWidget(self._api_key, stretch=1)
        lay.addLayout(api_row)

        # ── fila 2: búsqueda + contador ──────────────────────────────────
        top = QHBoxLayout()
        self._busq = QLineEdit()
        self._busq.setPlaceholderText("🔍 Buscar artista…")
        self._busq.textChanged.connect(self._proxy.setFilterFixedString)
        self._busq.textChanged.connect(self._actualizar_contador)
        self._lbl_count = QLabel()
        top.addWidget(self._busq, stretch=1)
        top.addWidget(self._lbl_count)
        lay.addLayout(top)

        # ── tabla ────────────────────────────────────────────────────────
        self._tabla = QTableView()
        self._tabla.setModel(self._proxy)
        self._tabla.setSortingEnabled(True)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.horizontalHeader().setStretchLastSection(True)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tabla.verticalHeader().setDefaultSectionSize(22)
        self._tabla.verticalHeader().hide()
        self._tabla.horizontalHeader().resizeSection(0, 220)
        self._tabla.horizontalHeader().resizeSection(1, 420)
        self._tabla.horizontalHeader().resizeSection(2, 90)
        lay.addWidget(self._tabla, stretch=1)

        # ── barra inferior ───────────────────────────────────────────────
        bot = QHBoxLayout()
        self._lbl_estado = QLabel(
            "Ingresá tu API key de Last.fm y hacé click en Actualizar para "
            "obtener los géneros de cada artista."
        )
        self._lbl_estado.setWordWrap(True)
        self._btn_actualizar = QPushButton("🌐  Actualizar desde Online")
        self._btn_actualizar.setToolTip(
            "Consulta Last.fm (con API key) y Beatport para obtener géneros — "
            "procesa hasta 200 artistas por corrida"
        )
        self._btn_actualizar.clicked.connect(self._on_actualizar)
        bot.addWidget(self._lbl_estado, stretch=1)
        bot.addWidget(self._btn_actualizar)
        lay.addLayout(bot)

    # ----------------------------------------------------------------- datos
    def recargar(self):
        conn = db_mod.connect(self._db_path)
        artist_db.registrar_desde_biblioteca(conn)
        self._model.recargar(conn)
        conn.close()
        self._actualizar_contador()

    def _actualizar_contador(self):
        total = self._model.rowCount()
        con_generos = sum(
            1 for f in self._model._filas
            if f.get("generos_display") not in ("—", "", None)
        )
        visible = self._proxy.rowCount()
        self._lbl_count.setText(
            f"{visible} mostrados  |  {con_generos}/{total} con géneros"
        )

    # --------------------------------------------------------------- worker
    def _on_actualizar(self):
        from gui.workers import ArtistasWorker
        if self._worker and self._worker.isRunning():
            return
        api_key = self._api_key.text().strip()
        if not api_key:
            self._lbl_estado.setText(
                "⚠ Ingresá primero tu API key de Last.fm para poder consultar géneros."
            )
            return
        self._btn_actualizar.setEnabled(False)
        self._lbl_estado.setText("Iniciando consulta…")
        self._worker = ArtistasWorker(self._db_path, api_key=api_key)
        self._worker.progreso.connect(self._lbl_estado.setText)
        self._worker.terminado.connect(self._on_worker_done)
        self._worker.start()

    def _on_worker_done(self, resumen: dict):
        self._btn_actualizar.setEnabled(True)
        nuevos = resumen.get("nuevos", 0)
        sin_info = resumen.get("sin_info", 0)
        pendientes = resumen.get("total_pendientes", 0)
        self._lbl_estado.setText(
            f"Listo — {nuevos} artistas con géneros encontrados, "
            f"{sin_info} sin info  |  "
            f"Pendientes restantes: {max(0, pendientes - resumen.get('procesados', 0))}"
        )
        self.recargar()
