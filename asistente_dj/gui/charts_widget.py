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
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QSplitter, QTableView, QVBoxLayout, QWidget,
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import db as db_mod
import charts_confiable
from gui.workers import YoutubeSearchWorker, SpotifySearchWorker
from gui import local_preview_server

_COLS    = ["posicion", "track", "artistas_str", "sello", "bpm_str", "key"]
_HEADERS = ["#", "Track", "Artistas", "Sello", "BPM", "Key"]
_COLOR_NOVEDAD = QColor(0, 229, 255, 28)   # halo cyan tenue (ver theme.CYAN)


class _PreviewPage(QWebEnginePage):
    """QWebEngineView no abre ventanas emergentes por defecto — sin esto, el
    botón "Log in" del widget de Spotify (necesario para reproducir el track
    completo en vez de los 30s de preview, si el DJ tiene Premium) no hace
    nada. Acá se le da un diálogo real donde mostrar ese popup de login."""

    def createWindow(self, _tipo):
        vista = self.parent()
        dialogo = QDialog(vista.window() if vista else None)
        dialogo.setWindowTitle("Iniciar sesión en Spotify")
        dialogo.resize(420, 600)
        lay = QVBoxLayout(dialogo)
        lay.setContentsMargins(0, 0, 0, 0)
        vista_popup = QWebEngineView(dialogo)
        lay.addWidget(vista_popup)
        vista_popup.page().windowCloseRequested.connect(dialogo.close)
        dialogo.show()
        # Guardar referencias para que no se destruyan apenas vuelve esta función.
        self._popups = getattr(self, "_popups", [])
        self._popups.append((dialogo, vista_popup))
        return vista_popup.page()


def _nombre_track(nombre: str | None, mix_name: str | None) -> str:
    nombre = nombre or "—"
    if mix_name and mix_name.lower() not in ("original mix", "extended mix"):
        return f"{nombre} ({mix_name})"
    return nombre


def _filas_chart(db_path: str, slug: str) -> list[dict]:
    """Filas de un chart, normalizadas (artistas siempre como lista). Lee de
    Supabase si está configurado (ahí escribe el agente en la nube); si no
    hay datos ahí, cae al SQLite local."""
    if charts_confiable.esta_configurado():
        rows = charts_confiable.obtener_chart(slug, top=200)
        if rows:
            return rows
    conn = db_mod.connect(db_path)
    rows = conn.execute(
        "SELECT * FROM charts_tracks WHERE genero_slug=? ORDER BY posicion",
        (slug,),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["artistas"] = json.loads(d["artistas"] or "[]")
        out.append(d)
    return out


def _generos_disponibles(db_path: str) -> list[dict]:
    """[{'genero_slug', 'nombre', 'ultima'}], de Supabase si está configurado
    (refleja lo que va subiendo el agente en la nube); si no, del SQLite local."""
    if charts_confiable.esta_configurado():
        rows = charts_confiable.generos_disponibles()
        if rows:
            return rows
    conn = db_mod.connect(db_path)
    rows = conn.execute(
        "SELECT genero_slug, COALESCE(MAX(genero_nombre), genero_slug) AS nombre, "
        "MAX(fecha_scrape) AS ultima, COUNT(*) AS n "
        "FROM charts_tracks GROUP BY genero_slug"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class ChartsModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._filas: list[dict] = []
        self._ultima_fecha = None

    def recargar(self, db_path: str, slug: str):
        self.beginResetModel()
        rows = _filas_chart(db_path, slug)
        ultima = max((r["fecha_scrape"] for r in rows), default=None)
        self._filas = []
        for r in rows:
            artistas = r["artistas"]
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
        self._spotify_worker: SpotifySearchWorker | None = None
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
        self._tabla.doubleClicked.connect(self._on_elegir_youtube)

        self._panel_yt = QWidget()
        panel_lay = QVBoxLayout(self._panel_yt)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.setSpacing(4)

        elegir = QHBoxLayout()
        self._btn_youtube = QPushButton("▶  YouTube")
        self._btn_youtube.setStyleSheet(
            "QPushButton { background:#FF0000; color:white; font-weight:bold; "
            "border-radius:4px; padding:6px; } QPushButton:hover { background:#cc0000; }"
        )
        self._btn_youtube.clicked.connect(self._on_elegir_youtube)
        elegir.addWidget(self._btn_youtube)
        self._btn_spotify = QPushButton("♪  Spotify")
        self._btn_spotify.setStyleSheet(
            "QPushButton { background:#1DB954; color:white; font-weight:bold; "
            "border-radius:4px; padding:6px; } QPushButton:hover { background:#169c46; }"
        )
        self._btn_spotify.clicked.connect(self._on_elegir_spotify)
        elegir.addWidget(self._btn_spotify)
        panel_lay.addLayout(elegir)

        self._lbl_yt_estado = QLabel(
            "Seleccioná un track y elegí YouTube o Spotify para escucharlo."
        )
        self._lbl_yt_estado.setWordWrap(True)
        panel_lay.addWidget(self._lbl_yt_estado)
        self._yt_view = QWebEngineView()
        self._yt_view.setPage(_PreviewPage(self._yt_view))
        panel_lay.addWidget(self._yt_view, stretch=1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._tabla)
        splitter.addWidget(self._panel_yt)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        lay.addWidget(splitter, stretch=1)

        bot = QHBoxLayout()
        bot.addStretch()
        self._btn_conseguir = QPushButton("➕  Agregar a 'para conseguir'")
        self._btn_conseguir.clicked.connect(self._on_agregar_conseguir)
        bot.addWidget(self._btn_conseguir)
        lay.addLayout(bot)

    # ----------------------------------------------------------------- datos
    def recargar(self):
        generos = _generos_disponibles(self._db_path)
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
            self._model.recargar(self._db_path, "global")
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
        self._model.recargar(self._db_path, slug)

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

    # --------------------------------------------------------- previews
    def _fila_seleccionada(self):
        filas = sorted({i.row() for i in self._tabla.selectionModel().selectedRows()})
        if not filas:
            QMessageBox.information(self, "Escuchar", "Seleccioná un track de la tabla primero.")
            return None
        return self._model.fila(filas[0])

    def _on_elegir_youtube(self, *_args):
        fila = self._fila_seleccionada()
        if fila is None:
            return
        if self._yt_worker is not None and self._yt_worker.isRunning():
            return  # ya hay una búsqueda en curso

        self._yt_view.setUrl(QUrl("about:blank"))
        self._lbl_yt_estado.setText(f"Buscando en YouTube: {fila['artistas_str']} — {fila['nombre_raw']}…")
        self._yt_worker = YoutubeSearchWorker(
            fila["artistas_raw"], fila["nombre_raw"], fila["mix_name_raw"]
        )
        self._yt_worker.terminado.connect(self._on_youtube_encontrado)
        self._yt_worker.start()

    def _on_youtube_encontrado(self, candidatos: list):
        if not candidatos:
            self._lbl_yt_estado.setText(
                "No se encontró un preview en YouTube para este track — probá con el botón de Spotify."
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
        # onError prueba el siguiente candidato encontrado en YouTube (no
        # cruza a Spotify: esa es una elección aparte del usuario, no un
        # fallback automático).
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
                        '<div id="msg">Ninguno de los resultados de YouTube está disponible '
                        + 'para reproducir embebido. Probá con el botón de Spotify.</div>';
                }}
            }}
            var tag = document.createElement('script');
            tag.src = "https://www.youtube.com/iframe_api";
            document.head.appendChild(tag);
            </script></body></html>"""
        self._yt_view.setUrl(QUrl(local_preview_server.set_html(html)))
        badge = "✓ Extended Mix" if mejor.es_extended else "⚠ Sin Extended Mix — versión corta"
        self._lbl_yt_estado.setText(f"YouTube: {badge}  ·  {mejor.titulo}")

    def _on_elegir_spotify(self, *_args):
        fila = self._fila_seleccionada()
        if fila is None:
            return
        if self._spotify_worker is not None and self._spotify_worker.isRunning():
            return  # ya hay una búsqueda en curso

        self._yt_view.setUrl(QUrl("about:blank"))
        self._lbl_yt_estado.setText(f"Buscando en Spotify: {fila['artistas_str']} — {fila['nombre_raw']}…")
        self._spotify_worker = SpotifySearchWorker(
            fila["artistas_raw"], fila["nombre_raw"], fila["mix_name_raw"]
        )
        self._spotify_worker.terminado.connect(self._on_spotify_encontrado)
        self._spotify_worker.start()

    def _on_spotify_encontrado(self, resultado):
        if not resultado:
            self._lbl_yt_estado.setText(
                "No se encontró este track en Spotify — probá con el botón de YouTube."
            )
            return
        html = f"""<html><body style='margin:0;background:#000;'>
            <iframe style="border-radius:12px" width="100%" height="100%"
             src="https://open.spotify.com/embed/track/{resultado.track_id}?utm_source=generator"
             frameBorder="0" allowfullscreen
             allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe>
            </body></html>"""
        self._yt_view.setUrl(QUrl(local_preview_server.set_html(html)))
        badge = "✓ Extended Mix" if resultado.es_extended else "⚠ Versión corta"
        self._lbl_yt_estado.setText(f"Spotify (30s): {badge}  ·  {resultado.titulo}")
