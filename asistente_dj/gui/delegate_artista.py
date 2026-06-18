from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCompleter, QLineEdit, QStyledItemDelegate,
)
from PySide6.QtCore import QStringListModel

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
import artist_db


class ArtistaDelegate(QStyledItemDelegate):
    """Editor de artista con autocompletado desde la BD de artistas.
    Coincide en cualquier posición del nombre (MatchContains).
    Al guardar, si el artista es nuevo se registra automáticamente.
    """

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)

        try:
            conn = db_mod.connect(self._db_path)
            nombres = [r["nombre"] for r in artist_db.todos(conn)]
            conn.close()
        except Exception:
            nombres = []

        model = QStringListModel(nombres, editor)
        completer = QCompleter(model, editor)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        editor.setCompleter(completer)
        return editor

    def setEditorData(self, editor: QLineEdit, index):
        editor.setText(index.data(Qt.EditRole) or "")
        editor.selectAll()

    def setModelData(self, editor: QLineEdit, model, index):
        value = editor.text().strip()
        if value:
            model.setData(index, value, Qt.EditRole)
