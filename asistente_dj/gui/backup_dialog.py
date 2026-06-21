"""Diálogo de "Backup en la nube" — Fase 2 del Módulo 3.

El DJ elige qué subir: toda la biblioteca, un género/subgénero puntual del
árbol que ya usa para organizar su música, o una de sus playlists guardadas.
Devuelve la lista de IDs de tracks a subir (`ids_seleccionados()`); el
llamador (`MainWindow._on_backup_nube`) arranca el `BackupNubeWorker` con esa
lista.
"""
from __future__ import annotations

import json
import os
import sys

from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QListWidget, QRadioButton, QStackedWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
from config import GENRE_TREE


class BackupDialog(QDialog):
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._ids: list[int] = []
        self.setWindowTitle("Backup en la nube")
        self.resize(420, 480)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("¿Qué querés subir?"))

        self._grupo = QButtonGroup(self)
        self._rb_todo = QRadioButton("Toda mi música")
        self._rb_genero = QRadioButton("Por género")
        self._rb_playlist = QRadioButton("Por playlist")
        self._rb_todo.setChecked(True)
        for i, rb in enumerate((self._rb_todo, self._rb_genero, self._rb_playlist)):
            self._grupo.addButton(rb, i)
            lay.addWidget(rb)
        self._grupo.idClicked.connect(self._on_modo_cambiado)

        self._pila = QStackedWidget()
        self._pila.addWidget(QWidget())          # 0: toda mi música, nada que elegir
        self._pila.addWidget(self._crear_arbol_generos())   # 1
        self._pila.addWidget(self._crear_lista_playlists())  # 2
        lay.addWidget(self._pila, stretch=1)

        self._lbl_resumen = QLabel("")
        lay.addWidget(self._lbl_resumen)

        botones = QDialogButtonBox(QDialogButtonBox.Cancel)
        self._btn_subir = botones.addButton("☁ Subir", QDialogButtonBox.AcceptRole)
        botones.accepted.connect(self._aceptar)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)

        self._actualizar_resumen()

    # ------------------------------------------------------------ árbol género
    def _crear_arbol_generos(self) -> QTreeWidget:
        """Solo muestra géneros/subgéneros que este DJ realmente tiene en su
        biblioteca (cada usuario tiene géneros distintos) — mismo criterio
        que el árbol de la pantalla principal (`organizador.py:_poblar_arbol`)."""
        tree = QTreeWidget()
        tree.setHeaderHidden(True)

        conn = db_mod.connect(self._db_path)
        contadores: dict[tuple, int] = {}
        for r in conn.execute(
            "SELECT genero, subgenero, COUNT(*) AS n FROM tracks "
            "WHERE genero IS NOT NULL GROUP BY genero, subgenero"
        ):
            contadores[(r["genero"], r["subgenero"])] = r["n"]
        conn.close()

        for genero, subgeneros in GENRE_TREE.items():
            total_g = sum(v for (g, _), v in contadores.items() if g == genero)
            if total_g == 0:
                continue
            item_g = QTreeWidgetItem(tree, [f"{genero}  ({total_g})"])
            item_g.setData(0, 1, (genero, None))
            for sub in subgeneros:
                n = contadores.get((genero, sub), 0)
                if n == 0:
                    continue
                item_s = QTreeWidgetItem(item_g, [f"{sub}  ({n})"])
                item_s.setData(0, 1, (genero, sub))
        tree.itemSelectionChanged.connect(self._actualizar_resumen)
        self._tree_generos = tree
        return tree

    # ----------------------------------------------------------- lista playlist
    def _crear_lista_playlists(self) -> QListWidget:
        lista = QListWidget()
        conn = db_mod.connect(self._db_path)
        nombres = [r["nombre"] for r in conn.execute(
            "SELECT nombre FROM playlists ORDER BY nombre"
        ).fetchall()]
        conn.close()
        lista.addItems(nombres)
        lista.itemSelectionChanged.connect(self._actualizar_resumen)
        self._lista_playlists = lista
        return lista

    # --------------------------------------------------------------- lógica
    def _on_modo_cambiado(self, idx: int):
        self._pila.setCurrentIndex(idx)
        self._actualizar_resumen()

    def _calcular_ids(self) -> list[int]:
        conn = db_mod.connect(self._db_path)
        try:
            modo = self._grupo.checkedId()
            if modo == 0:
                rows = conn.execute("SELECT id FROM tracks").fetchall()
                return [r["id"] for r in rows]
            if modo == 1:
                items = self._tree_generos.selectedItems()
                if not items:
                    return []
                genero, subgenero = items[0].data(0, 1)
                sql = "SELECT id FROM tracks WHERE genero=?"
                params = [genero]
                if subgenero:
                    sql += " AND subgenero=?"
                    params.append(subgenero)
                return [r["id"] for r in conn.execute(sql, params).fetchall()]
            if modo == 2:
                items = self._lista_playlists.selectedItems()
                if not items:
                    return []
                row = conn.execute(
                    "SELECT reglas FROM playlists WHERE nombre=?", (items[0].text(),)
                ).fetchone()
                return json.loads(row["reglas"]).get("ids", []) if row else []
            return []
        finally:
            conn.close()

    def _actualizar_resumen(self):
        ids = self._calcular_ids()
        self._lbl_resumen.setText(f"{len(ids)} track(s) seleccionados para subir.")
        self._btn_subir.setEnabled(bool(ids))

    def _aceptar(self):
        self._ids = self._calcular_ids()
        self.accept()

    def ids_seleccionados(self) -> list[int]:
        return self._ids
