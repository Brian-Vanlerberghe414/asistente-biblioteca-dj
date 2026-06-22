from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QTabWidget, QToolBar, QVBoxLayout, QCheckBox, QFrame,
)
from PySide6.QtGui import QColor, QFont

_PROJ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_GUI  = os.path.dirname(os.path.abspath(__file__))

if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)


def _asset(name: str) -> str:
    return os.path.join(_GUI, "assets", name)

from gui.artistas_widget import ArtistasWidget
from gui.charts_widget import ChartsWidget
from gui.organizador import OrganizadorWidget
from gui.workers import (
    AnalyzeWorker, ArchiveWorker, BackupNubeWorker, DjImportWorker, ScanWorker,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente DJ by Overcome Harmony")
        self.resize(1280, 780)

        self._db_path = os.path.join(_PROJ, "asistente_dj.db")

        # Toolbar
        tb: QToolBar = self.addToolBar("Principal")
        tb.setMovable(False)
        tb.addAction("📂 Escanear", self._on_scan)
        tb.addAction("📦 Archivar", self._on_archive)
        tb.addAction("🎛 Afinar BPM/KEY", self._on_afinar_bpm)
        tb.addSeparator()
        tb.addAction("🗑 Eliminar", self._on_eliminar)
        tb.addAction("➕ Playlist", self._on_crear_playlist)
        tb.addSeparator()
        tb.addAction("🌐 BD Online", self._on_bd_online)
        tb.addAction("☁ Backup en la nube", self._on_backup_nube)
        tb.addAction("🔄 Sincronizar", self._on_sincronizar)
        tb.addAction("⚙ Configurar", self._on_configurar)

        # Tabs
        self._tabs = QTabWidget(self)
        self._org = OrganizadorWidget(self._db_path, self)
        self._tabs.addTab(self._org, "Biblioteca")
        self._charts = ChartsWidget(self._db_path, self)
        self._tabs.addTab(self._charts, "Charts")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)
        self.statusBar().showMessage("Listo")

        self._worker = None

        # Limpieza automática al arrancar
        self._auto_limpiar()

    # --------------------------------------------------------- limpieza auto
    def _auto_limpiar(self):
        import db as db_mod
        import tagfix
        conn = db_mod.connect(self._db_path)
        res = tagfix.limpiar_todo(conn)
        conn.close()
        if sum(res.values()):
            self._org.recargar()

    def _on_tab_changed(self, index: int):
        if self._tabs.widget(index) is self._charts:
            self._charts.recargar()

    # -------------------------------------------------------------- acciones
    def _on_scan(self):
        carpeta = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de música"
        )
        if not carpeta:
            return
        self._lanzar(ScanWorker(carpeta, self._db_path))

    def _on_analyze(self):
        self._lanzar(AnalyzeWorker(self._db_path))

    def _on_archive(self):
        destino = QFileDialog.getExistingDirectory(
            self, "Carpeta de destino para el archivado"
        )
        if not destino:
            return
        self._lanzar(ArchiveWorker(self._db_path, destino))

    # --------------------------------------------------------------- worker
    def _lanzar(self, worker):
        self._worker = worker
        worker.progreso.connect(self.statusBar().showMessage)
        worker.terminado.connect(self._on_done)
        self._set_toolbar(False)
        worker.start()

    def _on_done(self, resultado):
        was_scan = isinstance(self._worker, ScanWorker)

        self._auto_limpiar()
        self._org.recargar()

        # Error → siempre cortar la cadena y rehabilitar toolbar
        if isinstance(resultado, dict) and "error" in resultado:
            self._set_toolbar(True)
            QMessageBox.warning(self, "Error", str(resultado["error"]))
            self.statusBar().showMessage("Error en la operación")
            return

        # Scan terminado → arrancar análisis automáticamente
        if was_scan:
            if isinstance(resultado, dict):
                partes = "  ".join(f"{k}: {v}" for k, v in resultado.items())
                self.statusBar().showMessage(f"Escaneo listo ({partes}) — analizando…")
            else:
                self.statusBar().showMessage("Escaneo listo — analizando…")
            self._lanzar(AnalyzeWorker(self._db_path))
            return

        # Cualquier otro worker → rehabilitar toolbar y mostrar resultado
        self._set_toolbar(True)
        if isinstance(resultado, dict):
            msg = "  ".join(f"{k}: {v}" for k, v in resultado.items())
            self.statusBar().showMessage(f"Listo — {msg}")
        elif isinstance(resultado, int):
            self.statusBar().showMessage(f"Listo — {resultado} tracks analizados")
        else:
            self.statusBar().showMessage("Listo")

    def _set_toolbar(self, enabled: bool):
        for tb in self.findChildren(QToolBar):
            for action in tb.actions():
                action.setEnabled(enabled)

    def _on_afinar_bpm(self):
        """Importa BPM/Key exactos desde Rekordbox o Traktor."""
        from PySide6.QtWidgets import QInputDialog
        opciones = ["Rekordbox", "Traktor"]
        software, ok = QInputDialog.getItem(
            self, "Afinar BPM/KEY",
            "¿Con qué software tenés analizada tu biblioteca?",
            opciones, 0, False,
        )
        if not ok:
            return
        if software == "Rekordbox":
            self._iniciar_import_rekordbox()
        else:
            self._iniciar_import_traktor()

    def _iniciar_import_rekordbox(self):
        """Diálogo atmosférico para importar BPM/KEY desde Rekordbox."""
        from gui.atmospheric_dialog import AtmosphericDialog

        dlg = AtmosphericDialog(_asset("dj-booth-festival.jpg"), "#00E5FF", self)
        dlg.setWindowTitle("Afinar BPM / KEY — Rekordbox")
        dlg.setMinimumWidth(580)
        dlg.setMinimumHeight(380)
        lay = dlg._content_layout

        # ── Eyebrow ──────────────────────────────────────────────────────────
        eyebrow = QLabel("● REKORDBOX · IMPORTAR ANÁLISIS")
        eyebrow.setStyleSheet(
            "color: #00E5FF; font-size: 10px; font-weight: 600; letter-spacing: 1.5px;"
        )
        lay.addWidget(eyebrow)

        # ── Título ────────────────────────────────────────────────────────────
        titulo = QLabel("Afinar BPM / KEY")
        titulo.setStyleSheet(
            "color: #E9E9EC; font-size: 24px; font-weight: 700; letter-spacing: -0.4px;"
        )
        lay.addWidget(titulo)

        subtitulo = QLabel(
            "Exportá tu colección desde Rekordbox (Archivo → Exportar colección en formato XML)\n"
            "y seleccioná el archivo .xml para actualizar BPM y Key con los datos exactos de Rekordbox."
        )
        subtitulo.setStyleSheet("color: #9A9CA1; font-size: 12px;")
        subtitulo.setWordWrap(True)
        lay.addWidget(subtitulo)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.08); margin: 4px 0;")
        lay.addWidget(sep)

        # ── Campo de archivo ──────────────────────────────────────────────────
        self._rb_ruta_elegida = ""
        lbl_ruta = QLabel("Ningún archivo seleccionado")
        lbl_ruta.setStyleSheet(
            "font-family: 'JetBrains Mono','Consolas',monospace; font-size: 11px;"
            "color: #75777B; background: rgba(0,0,0,0.3); border-radius: 5px; padding: 6px 10px;"
        )
        lbl_ruta.setWordWrap(True)

        btn_buscar = QPushButton("📂  Buscar XML…")
        btn_buscar.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18);"
            " border-radius: 7px; color: #E9E9EC; padding: 7px 16px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.14); }"
        )

        buscar_row = QHBoxLayout()
        buscar_row.addWidget(lbl_ruta, stretch=1)
        buscar_row.addWidget(btn_buscar)
        lay.addLayout(buscar_row)

        def _elegir_archivo():
            archivo, _ = QFileDialog.getOpenFileName(
                dlg, "Seleccionar el XML exportado de Rekordbox",
                os.path.expanduser("~"), "XML (*.xml)",
            )
            if archivo:
                self._rb_ruta_elegida = archivo
                lbl_ruta.setText(archivo)
                lbl_ruta.setStyleSheet(
                    "font-family: 'JetBrains Mono','Consolas',monospace; font-size: 11px;"
                    "color: #16D6A6; background: rgba(0,0,0,0.3); border-radius: 5px; padding: 6px 10px;"
                )

        btn_buscar.clicked.connect(_elegir_archivo)

        # ── Opciones ──────────────────────────────────────────────────────────
        chk_bpm = QCheckBox("Sobrescribir BPM existente")
        chk_key = QCheckBox("Importar Key (Camelot)")
        chk_sel = QCheckBox("Solo tracks seleccionados")
        chk_bpm.setChecked(True); chk_key.setChecked(True)
        for chk in (chk_bpm, chk_key, chk_sel):
            chk.setStyleSheet("color: #E9E9EC; font-size: 12px;")
            lay.addWidget(chk)

        lay.addStretch()

        # ── Footer ────────────────────────────────────────────────────────────
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background: rgba(255,255,255,0.08); margin: 4px 0;")
        lay.addWidget(sep2)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_ok = QPushButton("Afinar BPM/KEY")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet(
            "QPushButton { background: rgba(0,229,255,0.15); border: 1px solid rgba(0,229,255,0.60);"
            " border-radius: 7px; color: #00E5FF; padding: 8px 20px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: rgba(0,229,255,0.25); }"
        )
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_ok)
        lay.addLayout(btns)

        btn_cancel.clicked.connect(dlg.reject)

        def _confirmar():
            if not self._rb_ruta_elegida:
                QMessageBox.warning(dlg, "Falta el archivo",
                    "Seleccioná el archivo XML con el botón 'Buscar XML…'.")
                return
            if not os.path.exists(self._rb_ruta_elegida):
                QMessageBox.warning(dlg, "Archivo no encontrado",
                    f"No se encontró:\n{self._rb_ruta_elegida}")
                return
            dlg.accept()

        btn_ok.clicked.connect(_confirmar)

        if dlg.exec() != QDialog.Accepted:
            return
        self._lanzar(DjImportWorker(self._rb_ruta_elegida, "rekordbox", self._db_path))

    def _iniciar_import_traktor(self):
        ruta_nml = os.path.join(
            os.path.expanduser("~"), "Documents",
            "Native Instruments", "Traktor", "collection.nml"
        )
        if os.path.exists(ruta_nml):
            resp = QMessageBox.question(
                self, "Afinar BPM/KEY — Traktor",
                f"Se encontró la colección de Traktor en:\n{ruta_nml}\n\n¿Importar BPM y Key?",
            )
            if resp != QMessageBox.Yes:
                return
            archivo = ruta_nml
        else:
            archivo, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar colección de Traktor", "", "NML (*.nml)"
            )
        if not archivo:
            return
        self._lanzar(DjImportWorker(archivo, "traktor", self._db_path))

    def _on_eliminar(self):
        ids = self._org.ids_seleccionados()
        if not ids:
            QMessageBox.information(
                self, "Eliminar",
                "No hay tracks seleccionados.\n"
                "Apretá el botón 'Seleccionar' (junto a los filtros de BPM/Key) y marcá los tracks."
            )
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Eliminar tracks")
        msg.setText(f"Vas a eliminar {len(ids)} track(s) seleccionado(s).")
        msg.setInformativeText("¿Cómo querés eliminarlos?")
        btn_asistente = msg.addButton("Solo del Asistente", QMessageBox.AcceptRole)
        btn_pc        = msg.addButton("Del Asistente y de la PC  ⚠", QMessageBox.DestructiveRole)
        msg.addButton(QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_asistente:
            self._org.eliminar_seleccionados(borrar_disco=False)
        elif clicked == btn_pc:
            resp = QMessageBox.warning(
                self, "Confirmar borrado permanente",
                f"Esto eliminará {len(ids)} archivo(s) del disco.\n"
                "Esta acción no se puede deshacer.\n\n¿Confirmar?",
                QMessageBox.Yes | QMessageBox.Cancel,
            )
            if resp == QMessageBox.Yes:
                self._org.eliminar_seleccionados(borrar_disco=True)

    def _on_crear_playlist(self):
        from gui.atmospheric_dialog import AtmosphericDialog

        ids = self._org.ids_seleccionados()
        if not ids:
            QMessageBox.information(
                self, "Crear Playlist",
                "Activá el botón 'Seleccionar' (junto a los filtros) y marcá los tracks "
                "antes de crear una playlist."
            )
            return

        dlg = AtmosphericDialog(_asset("dancefloor-lasers.jpg"), "#FF6B00", self)
        dlg.setWindowTitle("Nueva Playlist")
        dlg.setMinimumWidth(560)
        dlg.setMinimumHeight(340)
        lay = dlg._content_layout

        # ── Eyebrow ──────────────────────────────────────────────────────────
        eyebrow = QLabel("● PLAYLIST · EXPORTAR A REKORDBOX")
        eyebrow.setStyleSheet(
            "color: #FF6B00; font-size: 10px; font-weight: 600; letter-spacing: 1.5px;"
        )
        lay.addWidget(eyebrow)

        titulo_lbl = QLabel("Nueva Playlist")
        titulo_lbl.setStyleSheet(
            "color: #E9E9EC; font-size: 24px; font-weight: 700; letter-spacing: -0.4px;"
        )
        lay.addWidget(titulo_lbl)

        # ── Campo nombre ──────────────────────────────────────────────────────
        lbl_nombre = QLabel("Nombre")
        lbl_nombre.setStyleSheet("color: #9A9CA1; font-size: 10px; font-weight: 600; letter-spacing: 1px;")
        lay.addWidget(lbl_nombre)

        nombre_edit = QLineEdit()
        nombre_edit.setPlaceholderText("p.ej. Warm-up · Melodic 122–126")
        nombre_edit.setStyleSheet(
            "QLineEdit { background: rgba(0,0,0,0.35); border: 1px solid rgba(255,107,0,0.60);"
            " border-radius: 7px; color: #E9E9EC; padding: 8px 12px; font-size: 13px; }"
            "QLineEdit:focus { border-color: #FF6B00; }"
        )
        lay.addWidget(nombre_edit)

        # ── Info de tracks ────────────────────────────────────────────────────
        info = QLabel(f"  {len(ids)} track(s) seleccionado(s) se agregarán a la playlist.")
        info.setStyleSheet("color: #9A9CA1; font-size: 11px; padding: 4px 0;")
        lay.addWidget(info)

        lay.addStretch()

        # ── Footer ────────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(255,255,255,0.08); margin: 4px 0;")
        lay.addWidget(sep)

        btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_ok = QPushButton(f"Crear playlist  ({len(ids)})")
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet(
            "QPushButton { background: rgba(255,107,0,0.18); border: 1px solid rgba(255,107,0,0.65);"
            " border-radius: 7px; color: #FF6B00; padding: 8px 20px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: rgba(255,107,0,0.28); }"
        )
        btns.addWidget(btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_ok)
        lay.addLayout(btns)

        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        nombre_edit.returnPressed.connect(dlg.accept)

        if dlg.exec() != QDialog.Accepted:
            return
        nombre = nombre_edit.text().strip()
        if not nombre:
            return

        import db as db_mod
        import json
        conn = db_mod.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO playlists (nombre, reglas) VALUES (?, ?)",
            (nombre, json.dumps({"ids": ids}))
        )
        conn.commit()

        # Base para que esta playlist se vea desde otros dispositivos
        # (Fase 3 — apps cliente): se sube a mis_playlists en la nube si
        # el DJ tiene su cuenta personal configurada.
        import cloud_backup
        if cloud_backup.esta_configurado():
            import cloud_sync
            cloud_sync.push_playlist(nombre, ids, conn)
        conn.close()

        self._org.recargar_playlists()
        QMessageBox.information(
            self, "Playlist creada",
            f"Playlist «{nombre}» creada con {len(ids)} tracks."
        )

    def _on_backup_nube(self):
        """Sube tracks seleccionados al backup personal en la nube
        (Cloudflare R2) — Fase 2 del Módulo 3. Usa la cuenta PERSONAL del
        DJ, separada de la cuenta de servicio del scraper de charts."""
        from PySide6.QtWidgets import QInputDialog
        import cloud_backup

        if not cloud_backup.esta_configurado():
            email, ok = QInputDialog.getText(
                self, "Backup en la nube",
                "Todavía no tenés una cuenta personal configurada.\n"
                "Ingresá tu email para crearla:"
            )
            if not ok or not email.strip():
                return
            password, ok = QInputDialog.getText(
                self, "Backup en la nube", "Elegí una contraseña:",
                QLineEdit.Password
            )
            if not ok or not password.strip():
                return
            creada, msg = cloud_backup.crear_cuenta(email.strip(), password.strip())
            QMessageBox.information(self, "Backup en la nube", msg)
            if not creada:
                return

        from gui.backup_dialog import BackupDialog
        dialogo = BackupDialog(self._db_path, self)
        if dialogo.exec() != QDialog.Accepted:
            return
        ids = dialogo.ids_seleccionados()
        if not ids:
            return

        self._lanzar(BackupNubeWorker(self._db_path, ids))

    def _on_sincronizar(self):
        """Trae cambios de género/playlists hechos desde otro dispositivo
        (ej. Android, más adelante) y los aplica localmente. Base de la
        Fase 3 — apps cliente, gana el cambio más reciente."""
        import cloud_backup
        if not cloud_backup.esta_configurado():
            QMessageBox.information(
                self, "Sincronizar",
                "Todavía no tenés una cuenta personal configurada. "
                "Usá primero 'Backup en la nube' para crearla."
            )
            return

        import cloud_sync
        import db as db_mod
        conn = db_mod.connect(self._db_path)
        n_tracks = cloud_sync.pull_biblioteca(conn)
        n_playlists = cloud_sync.pull_playlists(conn)
        conn.close()

        if n_tracks or n_playlists:
            self._org.recargar()
            self._org.recargar_playlists()
        self.statusBar().showMessage(
            f"Sincronizado: {n_tracks} track(s), {n_playlists} playlist(s) actualizadas."
        )

    def _on_bd_online(self):
        """Consulta tracks_canonical para los tracks visibles y muestra sugerencias."""
        try:
            import cloud_db
        except Exception as e:
            QMessageBox.warning(self, "BD Online", f"Error al cargar módulo: {e}")
            return

        if not cloud_db.configurado():
            QMessageBox.information(
                self, "BD Online",
                "Configurá primero la URL y la API key de Supabase\n"
                "usando el botón ⚙ Configurar."
            )
            return

        import db as db_mod
        conn = db_mod.connect(self._db_path)

        # Primero enviar pendientes
        enviados = cloud_db.enviar_pendientes(conn)
        if enviados:
            self.statusBar().showMessage(f"Reenviados {enviados} pendientes…")

        # Consultar tracks con huella para los que hay datos en la BD canonical
        rows = conn.execute(
            "SELECT id, huella, artista, titulo FROM tracks "
            "WHERE huella IS NOT NULL LIMIT 500"
        ).fetchall()
        conn.close()

        if not rows:
            QMessageBox.information(
                self, "BD Online",
                "No hay tracks con huella acústica calculada.\n"
                "Corré 'fingerprint' primero desde la línea de comandos."
            )
            return

        self.statusBar().showMessage(f"Consultando BD online para {len(rows)} tracks…")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        fp_map = {cloud_db.fp_hash(r["huella"]): r for r in rows}
        resultados = cloud_db.pull_tracks_batch(list(fp_map.keys()))

        if not resultados:
            QMessageBox.information(
                self, "BD Online",
                "No se encontraron tracks en la BD canónica todavía.\n"
                "La BD crece con las contribuciones de los DJs."
            )
            self.statusBar().showMessage("Listo")
            return

        # Mostrar resumen
        lineas = [f"Encontrados {len(resultados)} tracks en la BD canónica:\n"]
        for fph, cloud in list(resultados.items())[:20]:
            local = fp_map.get(fph)
            lineas.append(
                f"  {cloud.get('artista','?')} — {cloud.get('titulo','?')}\n"
                f"    {cloud.get('genero','?')}/{cloud.get('subgenero','?')}  "
                f"{cloud.get('camelot','?')}  BPM {cloud.get('bpm','?')}"
            )
        if len(resultados) > 20:
            lineas.append(f"\n  … y {len(resultados)-20} más.")

        QMessageBox.information(self, "BD Online — Resultados", "\n".join(lineas))
        self.statusBar().showMessage(f"BD Online: {len(resultados)} matches encontrados")

    def _on_configurar(self):
        """Diálogo para configurar Supabase URL, keys y ver el DJ UID."""
        import settings as cfg
        try:
            import cloud_db
            uid = cloud_db.dj_uid()
        except Exception:
            uid = cfg.get("dj_uid", "(no generado aún)")

        dlg = QDialog(self)
        dlg.setWindowTitle("Configuración — BD Compartida")
        dlg.setMinimumWidth(480)
        form = QFormLayout(dlg)

        url_edit = QLineEdit(cfg.get("supabase_url", ""))
        url_edit.setPlaceholderText("https://xxxx.supabase.co")
        form.addRow("Supabase URL:", url_edit)

        key_edit = QLineEdit(cfg.get("supabase_key", ""))
        key_edit.setPlaceholderText("eyJ… (anon key)")
        key_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Anon Key:", key_edit)

        svc_edit = QLineEdit(cfg.get("supabase_service_key", ""))
        svc_edit.setPlaceholderText("eyJ… (service key, solo para admin)")
        svc_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Service Key (admin):", svc_edit)

        uid_lbl = QLabel(uid)
        uid_lbl.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow("Tu DJ UID (anónimo):", uid_lbl)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() == QDialog.Accepted:
            if url_edit.text().strip():
                cfg.set_("supabase_url", url_edit.text().strip())
            if key_edit.text().strip():
                cfg.set_("supabase_key", key_edit.text().strip())
            if svc_edit.text().strip():
                cfg.set_("supabase_service_key", svc_edit.text().strip())
            QMessageBox.information(self, "Configuración", "Guardado correctamente.")

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            resp = QMessageBox.question(
                self, "Operación en curso",
                "Hay una operación en curso. ¿Salir de todos modos?",
            )
            if resp != QMessageBox.Yes:
                event.ignore()
                return
            self._worker.terminate()
        self._org._player.parar()
        super().closeEvent(event)
