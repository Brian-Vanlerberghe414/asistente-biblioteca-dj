from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QStyledItemDelegate


class BpmDelegate(QStyledItemDelegate):
    """Delegate para editar BPM con un spinner numérico."""

    def createEditor(self, parent, option, index):
        sb = QDoubleSpinBox(parent)
        sb.setRange(40.0, 250.0)
        sb.setDecimals(1)
        sb.setSingleStep(1.0)
        sb.setSuffix(" BPM")
        return sb

    def setEditorData(self, editor, index):
        try:
            val = float(index.model().data(index, Qt.DisplayRole) or 0)
        except ValueError:
            val = 0.0
        editor.setValue(val)

    def setModelData(self, editor, model, index):
        model.setData(index, str(editor.value()), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
