from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

import os, sys
_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

from config import GENRE_TREE
from gui.track_model import COL_GENERO, COL_SUBGENERO


class GeneroDelegate(QStyledItemDelegate):
    """Delegate que muestra un QComboBox para editar género y subgénero."""

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        col = index.column()

        if col == COL_GENERO:
            combo.addItem("")
            for g in GENRE_TREE:
                combo.addItem(g)

        elif col == COL_SUBGENERO:
            genero_idx = index.sibling(index.row(), COL_GENERO)
            genero = index.model().data(genero_idx, Qt.DisplayRole) or ""
            combo.addItem("")
            for sub in GENRE_TREE.get(genero, []):
                combo.addItem(sub)

        # Commit inmediato al elegir una opción: no depender del FocusOut
        # (con el editor creado a mano, Qt no conecta esto automáticamente,
        # lo que hacía que la selección de subgénero quedara sin guardar).
        combo.activated.connect(lambda _i, c=combo: self._commit(c))

        QTimer.singleShot(0, combo.showPopup)
        return combo

    def _commit(self, editor):
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole) or ""
        i = editor.findText(value)
        editor.setCurrentIndex(i if i >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
