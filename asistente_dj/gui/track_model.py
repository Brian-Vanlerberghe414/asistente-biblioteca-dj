from __future__ import annotations

import os
import sys

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

COLS = [
    "artista", "titulo", "sello", "bpm", "key", "camelot",
    "energia_ef", "genero", "subgenero", "formato", "bitrate_kbps", "anio",
    "analizado",
]
HEADERS = [
    "Artista", "Título", "Sello", "BPM", "Key", "Cam",
    "E", "Género", "Subgénero", "Fmt", "kbps", "Año",
    "Estado",
]

# Columna 0 es Play/Selección (modo dual); las columnas de datos empiezan en 1
COL_CHECK     = 0
ROLE_REPRODUCIENDO = Qt.UserRole + 1   # bool: es la fila que está sonando ahora
COL_ARTISTA   = 1 + COLS.index("artista")
COL_TITULO    = 1 + COLS.index("titulo")
COL_BPM       = 1 + COLS.index("bpm")
COL_CAMELOT   = 1 + COLS.index("camelot")
COL_ENERGIA   = 1 + COLS.index("energia_ef")
COL_GENERO    = 1 + COLS.index("genero")
COL_SUBGENERO = 1 + COLS.index("subgenero")
COL_ESTADO    = 1 + COLS.index("analizado")

_COLS_EDITABLES = {COL_ARTISTA, COL_TITULO, COL_BPM, COL_GENERO, COL_SUBGENERO}

_COLOR_PENDIENTE = QColor(180, 210, 255)   # azul claro


class TrackModel(QAbstractTableModel):
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._filas: list[dict] = []
        self._pendientes: dict[int, dict] = {}
        self._seleccionados: set[int] = set()
        self._id_reproduciendo: int | None = None

    # ------------------------------------------------------------------ carga
    def recargar(self, conn, genero=None, subgenero=None):
        self.beginResetModel()
        where: list[str] = []
        params: list = []
        if genero == "_Por revisar":
            where.append("genero IS NULL")
        elif genero == "_Ingreso":
            where.append("estado = 'ingreso'")
        elif genero == "_todos":
            where.append("genero IS NOT NULL")
        elif genero:
            where.append("genero = ?")
            params.append(genero)
        if subgenero:
            where.append("subgenero = ?")
            params.append(subgenero)
        sql = (
            "SELECT *, COALESCE(energia_manual, energia) AS energia_ef "
            "FROM tracks"
            + (f" WHERE {' AND '.join(where)}" if where else "")
            + " ORDER BY artista, titulo"
        )
        self._filas = [dict(r) for r in conn.execute(sql, params)]
        for fila in self._filas:
            tid = fila.get("id")
            if tid in self._pendientes:
                fila.update(self._pendientes[tid]["nuevo"])
        self.endResetModel()

    def recargar_por_ids(self, conn, ids: list[int]):
        """Carga solo los tracks con los IDs dados, en ese orden."""
        self.beginResetModel()
        if not ids:
            self._filas = []
        else:
            ph = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT *, COALESCE(energia_manual, energia) AS energia_ef "
                f"FROM tracks WHERE id IN ({ph})",
                ids,
            ).fetchall()
            orden = {tid: i for i, tid in enumerate(ids)}
            self._filas = sorted(
                [dict(r) for r in rows],
                key=lambda r: orden.get(r["id"], 0),
            )
        self.endResetModel()

    def todas(self) -> list[dict]:
        return list(self._filas)

    def fila(self, idx: int) -> dict:
        return self._filas[idx]

    def hay_pendientes(self) -> bool:
        return bool(self._pendientes)

    # --------------------------------------------------------- selección batch
    def ids_seleccionados(self) -> list[int]:
        return list(self._seleccionados)

    def limpiar_seleccion(self):
        self._seleccionados.clear()
        if self._filas:
            self.dataChanged.emit(
                self.index(0, COL_CHECK),
                self.index(len(self._filas) - 1, COL_CHECK),
                [Qt.CheckStateRole],
            )

    # ------------------------------------------------------- track sonando
    def set_id_reproduciendo(self, track_id: int | None):
        if track_id == self._id_reproduciendo:
            return
        self._id_reproduciendo = track_id
        if self._filas:
            self.dataChanged.emit(
                self.index(0, COL_CHECK),
                self.index(len(self._filas) - 1, COL_CHECK),
                [ROLE_REPRODUCIENDO],
            )

    # ------------------------------------------------------- guardar / cancelar
    def guardar_ids(self, ids: list[int]):
        import db as db_mod
        conn = db_mod.connect(self._db_path)
        for track_id in ids:
            if track_id not in self._pendientes:
                continue
            nuevo = self._pendientes.pop(track_id)["nuevo"]
            sets = ", ".join(f"{k}=?" for k in nuevo)
            vals = list(nuevo.values()) + [track_id]
            conn.execute(
                f"UPDATE tracks SET {sets}, confianza='manual' WHERE id=?", vals
            )
        conn.commit()
        conn.close()
        self.beginResetModel()
        self.endResetModel()

    def cancelar_ids(self, ids: list[int]):
        ids_set = set(ids)
        for fila in self._filas:
            tid = fila.get("id")
            if tid in ids_set and tid in self._pendientes:
                fila.update(self._pendientes.pop(tid)["orig"])
        self.beginResetModel()
        self.endResetModel()

    # ---------------------------------------------------------------- Qt API
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLS) + 1   # +1 por la columna checkbox

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.column() == COL_CHECK:
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable
        base = super().flags(index)
        if index.column() in _COLS_EDITABLES:
            return base | Qt.ItemIsEditable
        return base

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        r = self._filas[index.row()]

        # Columna checkbox
        if col == COL_CHECK:
            if role == Qt.CheckStateRole:
                return Qt.Checked if r.get("id") in self._seleccionados else Qt.Unchecked
            if role == ROLE_REPRODUCIENDO:
                return r.get("id") == self._id_reproduciendo
            return None

        # Columnas de datos (desplazadas 1 posición)
        data_col = col - 1
        if data_col < 0 or data_col >= len(COLS):
            return None

        if role in (Qt.DisplayRole, Qt.EditRole):
            v = r.get(COLS[data_col])
            if v is None:
                return ""
            if col == COL_BPM:
                try:
                    f = float(v)
                    return str(int(f)) if f == int(f) else f"{f:.1f}"
                except (TypeError, ValueError):
                    pass
            return str(v)

        if role == Qt.BackgroundRole:
            if col in _COLS_EDITABLES and r.get("id") in self._pendientes:
                return _COLOR_PENDIENTE

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        col = index.column()

        # Toggle checkbox
        if col == COL_CHECK and role == Qt.CheckStateRole:
            tid = self._filas[index.row()].get("id")
            if tid:
                if value == Qt.Checked:
                    self._seleccionados.add(tid)
                else:
                    self._seleccionados.discard(tid)
                self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        # Edición de datos
        if role != Qt.EditRole:
            return False
        data_col = col - 1
        if data_col < 0 or data_col >= len(COLS):
            return False
        campo = COLS[data_col]
        if campo not in ("artista", "titulo", "bpm", "genero", "subgenero"):
            return False

        row = self._filas[index.row()]
        track_id = row.get("id")
        if not track_id:
            return False

        if campo == "bpm":
            try:
                value = float(str(value).replace(" BPM", "").strip())
            except ValueError:
                return False
        else:
            value = (str(value) if value else "").strip() or None

        if track_id not in self._pendientes:
            self._pendientes[track_id] = {
                "orig": {
                    "artista":   row.get("artista"),
                    "titulo":    row.get("titulo"),
                    "genero":    row.get("genero"),
                    "subgenero": row.get("subgenero"),
                    "bpm":       row.get("bpm"),
                },
                "nuevo": {
                    "artista":   row.get("artista"),
                    "titulo":    row.get("titulo"),
                    "genero":    row.get("genero"),
                    "subgenero": row.get("subgenero"),
                    "bpm":       row.get("bpm"),
                },
            }

        self._pendientes[track_id]["nuevo"][campo] = value
        row[campo] = value

        if campo == "genero":
            self._pendientes[track_id]["nuevo"]["subgenero"] = None
            row["subgenero"] = None
            top = self.index(index.row(), COL_GENERO)
            bot = self.index(index.row(), COL_SUBGENERO)
            self.dataChanged.emit(top, bot, [Qt.DisplayRole, Qt.BackgroundRole])
        else:
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.BackgroundRole])

        p = self._pendientes[track_id]
        if all(p["nuevo"].get(k) == p["orig"].get(k)
               for k in ("artista", "titulo", "genero", "subgenero", "bpm")):
            del self._pendientes[track_id]
            top = self.index(index.row(), COL_ARTISTA)
            bot = self.index(index.row(), COL_SUBGENERO)
            self.dataChanged.emit(top, bot, [Qt.BackgroundRole])

        return True

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == COL_CHECK:
                return ""
            data_col = section - 1
            if 0 <= data_col < len(HEADERS):
                return HEADERS[data_col]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder):
        if column == COL_CHECK:
            return
        data_col = column - 1
        if data_col < 0 or data_col >= len(COLS):
            return
        campo = COLS[data_col]
        rev = (order == Qt.DescendingOrder)
        self.beginResetModel()
        self._filas.sort(
            key=lambda r: (str(r.get(campo) or "").lower()),
            reverse=rev,
        )
        self.endResetModel()
