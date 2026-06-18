"""Tab de Charts (Módulo 2): Top 100 de Beatport guardado en `charts_tracks`,
con novedades resaltadas y un botón para mandar un track a 'para conseguir'.

El scrape en sí (Playwright, ~30 min entre pedidos por el límite de
Cloudflare) corre por CLI/background — esta vista es de solo lectura sobre
lo que ya está guardado en la base, no dispara un scrape nuevo."""
from __future__ import annotations

import json
import os
import sys
from datetime import date

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QSplitter, QTableView, QVBoxLayout, QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
from gui.workers import YoutubeSearchWorker
from gui import local_preview_server

_COLS    = ["posicion", "track", "artistas_str", "sello", "bpm_str", "key"]
_HEADERS = ["#", "Track", "Artistas", "Sello", "BPM", "Key"]
_COLOR_NOVEDAD = QColor(0, 229, 255, 28)   # halo cyan tenue (ver theme.CYAN)


def _nombre_track(nombre: str | None, mix_name: str | None) -> str:
    nombre = nombre or "—"
    if mix_name and mix_name.lower() not in ("original mix", "extended mix"):
        return f"{nombre} ({mix_name})"
    return nombre


class ChartsModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filas: list[dict] = []

    def recargar(self, conn, slug: str):
        self.beginResetModel()
        rows = conn.execute(
            "SELECT * FROM charts_tracks WHERE genero_slug=? ORDER BY posicion",
            (slug,),
        ).fetchall()
        ultima = max((r["fecha_scrape"] for r in rows), default=None)
        self._filas = []
        for r in rows:
            artistas = json.loads(r["artistas"] or "[]")
            es_novedad = bool(ultima) and r["fecha_scrape"] == ultima and r["primera_vez"] == ultima
            self._filas.append({
                "posicion": r["posicion"],
                "track": _nombre_track(r["nombre"], r["mix_name"]),
                "artistas_str": ", ".join(artistas) or "—",
                "sello": r["sello"] or "—",
                "bpm_str": f"{r['bpm']:.0f}" if r["bpm"] else "—",
                "key": r["key"] or "—",
                "es_novedad": es_novedad,
                "beatport_id": r["beatport_id"],
                "nombre_raw": r["nombre"],
                "artistas_raw": artistas,
                "sello_raw": r["sello"],
                "mix_name_raw": r["mix_name"],
            })
        self._ultima_fecha = ultima
        self.endResetModel()

    def fila(self, row: int) -> dict | None:
        return self._filas[row] if 0 <= row < len(self._filas) else None

    def n_novedades(self) -> int:
        return sum(1 for f in self._filas if f["es_novedad"])

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._filas)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(_COLS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        fila = self._filas[index.row()]
        if role == Qt.DisplayRole:
            return str(fila.get(_COLS[index.column()]))
        if role == Qt.BackgroundRole and fila["es_novedad"]:
            return _COLOR_NOVEDAD
        if role == Qt.ToolTipRole and fila["es_novedad"]:
            return "Novedad — apareció por primera vez en el último scrape"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _HEADERS[section]
        return None


class ChartsWidget(QWidget):
    """Tab de Charts: Top 100 global/por género, novedades resaltadas y
    botón para agregar un track a la lista de 'para conseguir'."""

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._model = ChartsModel(self)
        self._yt_worker: YoutubeSearchWorker | None = None
        self._build_ui()
        self.recargar()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        top.addWidget(QLabel("Género:"))
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_genero_cambiado)
        top.addWidget(self._combo)

        self._lbl_estado = QLabel()
        top.addWidget(self._lbl_estado, stretch=1)

        self._btn_refrescar = QPushButton("⟳  Refrescar")
        self._btn_refrescar.setToolTip(
            "Vuelve a leer lo guardado en la base (el scrape en sí corre por "
            "CLI en segundo plano, espaciado para no bloquear con Beatport)."
        )
        self._btn_refrescar.clicked.connect(self.recargar)
        top.addWidget(self._btn_refrescar)
        lay.addLayout(top)

        self._tabla = QTableView()
        self._tabla.setModel(self._model)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.horizontalHeader().setStretchLastSection(True)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._tabla.verticalHeader().setDefaultSectionSize(24)
        self._tabla.verticalHeader().hide()
        self._tabla.horizontalHeader().resizeSection(0, 40)
        self._tabla.horizontalHeader().resizeSection(1, 340)
        self._tabla.horizontalHeader().resizeSection(2, 240)
        self._tabla.horizontalHeader().resizeSection(3, 180)
        self._tabla.horizontalHeader().resizeSection(4, 60)
        self._tabla.doubleClicked.connect(self._on_escuchar_youtube)

        self._panel_yt = QWidget()
        panel_lay = QVBoxLayout(self._panel_yt)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.setSpacing(4)
        self._lbl_yt_estado = QLabel(
            "Doble click en un track (o ➤ Escuchar) para buscar un preview en YouTube."
        )
        self._lbl_yt_estado.setWordWrap(True)
        panel_lay.addWidget(self._lbl_yt_estado)
        self._yt_view = QWebEngineView()
        panel_lay.addWidget(self._yt_view, stretch=1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._tabla)
        splitter.addWidget(self._panel_yt)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        lay.addWidget(splitter, stretch=1)

        bot = QHBoxLayout()
        bot.addStretch()
        self._btn_escuchar = QPushButton("➤  Escuchar en YouTube")
        self._btn_escuchar.clicked.connect(self._on_escuchar_youtube)
        bot.addWidget(self._btn_escuchar)
        self._btn_conseguir = QPushButton("➕  Agregar a 'para conseguir'")
        self._btn_conseguir.clicked.connect(self._on_agregar_conseguir)
        bot.addWidget(self._btn_conseguir)
        lay.addLayout(bot)

    # ----------------------------------------------------------------- datos
    def recargar(self):
        conn = db_mod.connect(self._db_path)
        generos = conn.execute(
            "SELECT genero_slug, COALESCE(MAX(genero_nombre), genero_slug) AS nombre, "
            "MAX(fecha_scrape) AS ultima, COUNT(*) AS n "
            "FROM charts_tracks GROUP BY genero_slug"
        ).fetchall()
        conn.close()

        generos = sorted(generos, key=lambda g: (g["genero_slug"] != "global", g["nombre"] or ""))

        slug_actual = self._combo.currentData()
        self._combo.blockSignals(True)
        self._combo.clear()
        for g in generos:
            etiqueta = "🌐 Global Top 100" if g["genero_slug"] == "global" else g["nombre"]
            self._combo.addItem(etiqueta, g["genero_slug"])
        self._combo.blockSignals(False)

        if not generos:
            self._lbl_estado.setText(
                "Sin charts guardados todavía — corré `charts-scrape` desde la línea de comandos."
            )
            self._model.recargar(db_mod.connect(self._db_path), "global")
            return

        idx = self._combo.findData(slug_actual) if slug_actual else -1
        self._combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._cargar_genero_actual()

    def _on_genero_cambiado(self, _idx: int):
        self._cargar_genero_actual()

    def _cargar_genero_actual(self):
        slug = self._combo.currentData()
        if not slug:
            return
        conn = db_mod.connect(self._db_path)
        self._model.recargar(conn, slug)
        conn.close()

        n = self._model.rowCount()
        novedades = self._model.n_novedades()
        ultima = getattr(self._model, "_ultima_fecha", None)
        partes = [f"{n} tracks"]
        if ultima:
            partes.append(f"último scrape: {ultima}")
        if novedades:
            partes.append(f"{novedades} novedades")
        self._lbl_estado.setText("  ·  ".join(partes))

    # --------------------------------------------------------------- acción
    def _on_agregar_conseguir(self):
        filas = sorted({i.row() for i in self._tabla.selectionModel().selectedRows()})
        if not filas:
            QMessageBox.information(
                self, "Agregar a 'para conseguir'",
                "Seleccioná uno o más tracks de la tabla primero."
            )
            return

        conn = db_mod.connect(self._db_path)
        agregados = ya_estaban = 0
        for row in filas:
            fila = self._model.fila(row)
            if fila is None:
                continue
            existe = conn.execute(
                "SELECT 1 FROM para_conseguir WHERE beatport_id=?", (fila["beatport_id"],)
            ).fetchone()
            if existe:
                ya_estaban += 1
                continue
            conn.execute(
                "INSERT INTO para_conseguir "
                "(beatport_id, nombre, artistas, sello, notas, fecha_agregado, conseguido) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (
                    fila["beatport_id"], fila["nombre_raw"],
                    ", ".join(fila["artistas_raw"]), fila["sello_raw"],
                    f"Beatport Top 100 — #{fila['posicion']}", date.today().isoformat(),
                ),
            )
            agregados += 1
        conn.commit()
        conn.close()

        msg = f"{agregados} track(s) agregados a 'para conseguir'."
        if ya_estaban:
            msg += f"  ({ya_estaban} ya estaban en la lista)"
        QMessageBox.information(self, "Agregar a 'para conseguir'", msg)

    # ------------------------------------------------------------ youtube
    def _on_escuchar_youtube(self, *_args):
        filas = sorted({i.row() for i in self._tabla.selectionModel().selectedRows()})
        if not filas:
            QMessageBox.information(
                self, "Escuchar en YouTube",
                "Seleccioná un track de la tabla primero."
            )
            return
        fila = self._model.fila(filas[0])
        if fila is None:
            return

        if self._yt_worker is not None and self._yt_worker.isRunning():
            return  # ya hay una búsqueda en curso

        self._btn_escuchar.setEnabled(False)
        self._yt_view.setUrl(QUrl("about:blank"))
        self._lbl_yt_estado.setText(f"Buscando en YouTube: {fila['artistas_str']} — {fila['nombre_raw']}…")

        self._yt_worker = YoutubeSearchWorker(
            fila["artistas_raw"], fila["nombre_raw"], fila["mix_name_raw"]
        )
        self._yt_worker.terminado.connect(self._on_youtube_encontrado)
        self._yt_worker.start()

    def _on_youtube_encontrado(self, candidatos: list):
        self._btn_escuchar.setEnabled(True)
        if not candidatos:
            self._lbl_yt_estado.setText(
                "No se encontró un preview en YouTube para este track."
            )
            return
        mejor = candidatos[0]
        ids_js = ",".join(f"'{c.video_id}'" for c in candidatos)
        # YouTube rechaza el embed si el documento no tiene un origen http(s)
        # real (sin eso manda "video no disponible", error 152 — confirmado
        # probándolo). setHtml() da un origen opaco, así que se sirve este
        # HTML desde un mini servidor local (gui/local_preview_server.py) en
        # vez de cargarlo directo. Además, algunos videos no permiten
        # embeber (restricción del dueño, error 101/150) — el handler
        # onError prueba el siguiente candidato.
        html = f"""<html><head><style>
            html,body{{margin:0;background:#000;height:100%;}}
            #player{{width:100%;height:100%;}}
            #msg{{color:#999;font-family:sans-serif;padding:20px;}}
            </style></head><body>
            <div id="player"></div>
            <script>
            var candidatos = [{ids_js}];
            var idx = 0;
            var player;
            function onYouTubeIframeAPIReady() {{
                player = new YT.Player('player', {{
                    height: '100%', width: '100%', videoId: candidatos[idx],
                    playerVars: {{autoplay: 1, rel: 0}},
                    events: {{'onError': onPlayerError}}
                }});
            }}
            function onPlayerError(e) {{
                idx++;
                if (idx < candidatos.length) {{
                    player.loadVideoById(candidatos[idx]);
                }} else {{
                    document.getElementById('player').outerHTML =
                        '<div id="msg">Ninguno de los resultados encontrados está '
                        + 'disponible para reproducir embebido.</div>';
                }}
            }}
            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            document.head.appendChild(tag);
            </script></body></html>"""
        self._yt_view.setUrl(QUrl(local_preview_server.set_html(html)))
        if mejor.es_extended:
            badge = "✓ Extended Mix"
        else:
            badge = "⚠ No se encontró la Extended Mix — reproduciendo la versión corta"
        self._lbl_yt_estado.setText(f"{badge}  ·  {mejor.titulo}")
