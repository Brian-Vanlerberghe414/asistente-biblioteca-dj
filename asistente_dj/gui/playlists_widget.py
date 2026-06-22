"""Pestaña "Playlist": lista de playlists guardadas (crear/renombrar/borrar/
exportar a Rekordbox) + grilla de los tracks de la playlist seleccionada.

La creación de playlists sigue viviendo en la pestaña Biblioteca (selección
de tracks en la grilla + botón "➕ Playlist" de la toolbar) — acá se
administran y se visualizan las que ya existen."""
from __future__ import annotations

import json
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
from gui.track_model import (
    COL_BPM, COL_CAMELOT, COL_CHECK, COL_ENERGIA, COL_ESTADO, TrackModel,
)
from gui.track_table_view import TrackTableView
from gui.visual_delegates import BpmDelegate, CamelotDelegate, EnergyDelegate, StatusDelegate


class PlaylistsWidget(QWidget):
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path

        lay = QHBoxLayout(self)

        # ── Panel izquierdo: lista de playlists ──────────────────────────
        panel = QVBoxLayout()
        panel.addWidget(QLabel("Tus playlists"))
        self._lista = QListWidget()
        self._lista.currentItemChanged.connect(self._on_seleccion)
        panel.addWidget(self._lista, stretch=1)

        fila_btns = QHBoxLayout()
        btn_renombrar = QPushButton("Renombrar")
        btn_borrar = QPushButton("Borrar")
        btn_renombrar.clicked.connect(self._on_renombrar)
        btn_borrar.clicked.connect(self._on_borrar)
        fila_btns.addWidget(btn_renombrar)
        fila_btns.addWidget(btn_borrar)
        panel.addLayout(fila_btns)

        btn_exportar = QPushButton("📤 Exportar a Rekordbox")
        btn_exportar.clicked.connect(self._on_exportar)
        panel.addWidget(btn_exportar)

        panel_widget = QWidget()
        panel_widget.setLayout(panel)
        panel_widget.setMaximumWidth(260)
        lay.addWidget(panel_widget)

        # ── Panel derecho: grilla de tracks (solo lectura) ───────────────
        derecha = QVBoxLayout()
        self._lbl_titulo = QLabel("Elegí una playlist")
        self._lbl_titulo.setStyleSheet("font-size: 15px; font-weight: 600;")
        derecha.addWidget(self._lbl_titulo)

        self._model = TrackModel(self._db_path, self)
        self._tabla = TrackTableView()
        self._tabla.setModel(self._model)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tabla.verticalHeader().setDefaultSectionSize(30)
        self._tabla.verticalHeader().hide()
        self._tabla.setColumnHidden(COL_CHECK, True)
        self._tabla.setItemDelegateForColumn(COL_BPM, BpmDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_CAMELOT, CamelotDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_ENERGIA, EnergyDelegate(self._tabla))
        self._tabla.setItemDelegateForColumn(COL_ESTADO, StatusDelegate(self._tabla))
        derecha.addWidget(self._tabla, stretch=1)

        lay.addLayout(derecha, stretch=1)

        self.recargar()

    # ------------------------------------------------------------------ datos
    def recargar(self):
        """Refresca la lista de playlists. Se llama también desde fuera
        (al crear una playlist nueva, al importar de Rekordbox, o al
        sincronizar con la nube)."""
        actual = self._nombre_actual()
        self._lista.clear()
        conn = db_mod.connect(self._db_path)
        filas = conn.execute(
            "SELECT nombre, reglas FROM playlists ORDER BY nombre"
        ).fetchall()
        conn.close()

        seleccionar = None
        for r in filas:
            n_tracks = len(json.loads(r["reglas"]).get("ids", []))
            item = QListWidgetItem(f"{r['nombre']}  ({n_tracks})")
            item.setData(Qt.UserRole, r["nombre"])
            self._lista.addItem(item)
            if r["nombre"] == actual:
                seleccionar = item

        if seleccionar:
            self._lista.setCurrentItem(seleccionar)
        elif self._lista.count():
            self._lista.setCurrentRow(0)
        else:
            conn = db_mod.connect(self._db_path)
            self._model.recargar_por_ids(conn, [])
            conn.close()
            self._lbl_titulo.setText("No tenés playlists todavía")

    def _nombre_actual(self) -> str | None:
        item = self._lista.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _ids_de(self, conn, nombre: str) -> list[int]:
        row = conn.execute(
            "SELECT reglas FROM playlists WHERE nombre=?", (nombre,)
        ).fetchone()
        return json.loads(row["reglas"]).get("ids", []) if row else []

    # ----------------------------------------------------------------- slots
    def _on_seleccion(self, current, _previous):
        if current is None:
            return
        nombre = current.data(Qt.UserRole)
        conn = db_mod.connect(self._db_path)
        ids = self._ids_de(conn, nombre)
        self._model.recargar_por_ids(conn, ids)
        conn.close()
        self._lbl_titulo.setText(f"{nombre}  —  {len(ids)} tracks")

    def _on_renombrar(self):
        nombre = self._nombre_actual()
        if not nombre:
            return
        nuevo, ok = QInputDialog.getText(
            self, "Renombrar playlist", "Nuevo nombre:", text=nombre
        )
        nuevo = (nuevo or "").strip()
        if not ok or not nuevo or nuevo == nombre:
            return
        conn = db_mod.connect(self._db_path)
        if conn.execute("SELECT 1 FROM playlists WHERE nombre=?", (nuevo,)).fetchone():
            QMessageBox.warning(self, "Ya existe",
                                 f"Ya hay una playlist llamada '{nuevo}'.")
            conn.close()
            return
        conn.execute("UPDATE playlists SET nombre=? WHERE nombre=?", (nuevo, nombre))
        conn.commit()
        conn.close()
        self.recargar()

    def _on_borrar(self):
        nombre = self._nombre_actual()
        if not nombre:
            return
        resp = QMessageBox.question(
            self, "Borrar playlist",
            f"¿Borrar la playlist '{nombre}'? (los tracks no se tocan, "
            "solo se borra la lista)"
        )
        if resp != QMessageBox.Yes:
            return
        conn = db_mod.connect(self._db_path)
        conn.execute("DELETE FROM playlists WHERE nombre=?", (nombre,))
        conn.commit()
        conn.close()
        self.recargar()

    def _on_exportar(self):
        nombre = self._nombre_actual()
        if not nombre:
            return
        salida, _ = QFileDialog.getSaveFileName(
            self, "Exportar a Rekordbox XML", f"{nombre}.xml", "XML (*.xml)"
        )
        if not salida:
            return
        import rekordbox_export
        from cli import _tracks_por_reglas
        conn = db_mod.connect(self._db_path)
        reglas = {"ids": self._ids_de(conn, nombre)}
        tracks = _tracks_por_reglas(conn, reglas)
        conn.close()
        if not tracks:
            QMessageBox.information(self, "Vacía",
                                     "Esta playlist no tiene tracks para exportar.")
            return
        n = rekordbox_export.escribir_playlist(tracks, nombre, salida)
        QMessageBox.information(
            self, "Exportado",
            f"Se exportaron {n} tracks a:\n{salida}\n\n"
            "En Rekordbox: Preferences > View > Layout: activá 'rekordbox xml';\n"
            "Preferences > Advanced > rekordbox xml: apuntá a este archivo."
        )
