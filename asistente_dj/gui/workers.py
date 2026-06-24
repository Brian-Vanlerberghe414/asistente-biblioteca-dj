from __future__ import annotations

import os
import re
import subprocess
import sys

from PySide6.QtCore import QThread, Signal


class ScanWorker(QThread):
    progreso = Signal(str)
    terminado = Signal(dict)

    def __init__(self, carpeta: str, db_path: str):
        super().__init__()
        self.carpeta = carpeta
        self.db_path = db_path

    def run(self):
        # Agrega la carpeta del proyecto al path para importar los módulos
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import db
        import scanner
        self.progreso.emit(f"Escaneando {self.carpeta}…")
        conn = db.connect(self.db_path)
        res = scanner.scan(self.carpeta, conn)
        conn.close()
        self.terminado.emit(res)


class AnalyzeWorker(QThread):
    """Lanza 'python cli.py analyze' como subproceso y parsea el progreso."""
    progreso = Signal(str)
    terminado = Signal(int)   # cantidad de tracks analizados

    def __init__(self, db_path: str, procesos: int = 0):
        super().__init__()
        self.db_path = db_path
        self.procesos = procesos

    def run(self):
        cli = os.path.join(os.path.dirname(__file__), "..", "cli.py")
        cmd = [
            sys.executable, cli, "analyze",
            "--db", self.db_path,
            "--procesos", str(self.procesos),
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=os.path.dirname(cli),
        )
        analizados = 0
        for line in proc.stdout:
            line = line.rstrip()
            m = re.search(r"(\d+)/(\d+)", line)
            if m:
                actual = int(m.group(1))
                total  = int(m.group(2))
                pct    = int(actual * 100 / total) if total else 0
                if "waveform" in line.lower():
                    self.progreso.emit(f"🔬 Waveform — {pct}%  ({actual}/{total})")
                else:
                    self.progreso.emit(f"🔬 Analizando — {pct}%  ({actual}/{total})")
                analizados = actual
            elif line.strip():
                self.progreso.emit(line)
        proc.wait()
        self.terminado.emit(analizados)


class ArchiveWorker(QThread):
    progreso = Signal(str)
    terminado = Signal(dict)

    def __init__(self, db_path: str, destino: str):
        super().__init__()
        self.db_path = db_path
        self.destino = destino

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import db
        from archiver import build_plan, execute_plan
        self.progreso.emit("Construyendo plan de archivado…")
        conn = db.connect(self.db_path)
        plan = build_plan(conn)
        self.progreso.emit(f"Archivando {len(plan)} tracks…")
        res = execute_plan(conn, plan, self.destino, dry_run=False)
        conn.close()
        self.terminado.emit(res)


class DjImportWorker(QThread):
    """Importa BPM/Key desde Rekordbox (XML) o Traktor (NML) en background."""
    progreso = Signal(str)
    terminado = Signal(object)

    def __init__(self, archivo: str, fuente: str, db_path: str):
        super().__init__()
        self.archivo = archivo
        self.fuente = fuente   # "rekordbox" | "traktor"
        self.db_path = db_path

    def run(self):
        proj = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import db as db_mod
        from cli import _match_y_actualizar

        try:
            self.progreso.emit(f"Leyendo colección de {self.fuente.capitalize()}…")
            if self.fuente == "rekordbox":
                import rekordbox_xml
                registros, version = rekordbox_xml.parse(self.archivo)
                self.progreso.emit(
                    f"Rekordbox {version} — {len(registros)} tracks. Comparando…"
                )
            else:
                import traktor_nml
                registros = traktor_nml.parse(self.archivo)
                self.progreso.emit(
                    f"Traktor — {len(registros)} tracks. Comparando…"
                )
            conn = db_mod.connect(self.db_path)
            act, sin_match, sin_bpm = _match_y_actualizar(conn, registros, self.fuente)

            playlists_importadas = []
            if self.fuente == "rekordbox":
                from cli import importar_playlists_rekordbox
                self.progreso.emit("Importando playlists…")
                playlists_importadas = importar_playlists_rekordbox(
                    conn, self.archivo, registros
                )
            conn.close()
            self.terminado.emit({
                "actualizados": act,
                "sin_match": sin_match,
                "sin_bpm": sin_bpm,
                "playlists": playlists_importadas,
            })
        except Exception as e:
            self.terminado.emit({"error": str(e)})


class YoutubeSearchWorker(QThread):
    """Busca previews candidatos en YouTube para un track de los charts (sin
    API key, vía yt-dlp). Corre en background porque la búsqueda pega a la
    red. Devuelve varios candidatos (no solo el mejor) para que la GUI pueda
    probar el siguiente si el primero no permite embeber."""
    terminado = Signal(list)   # list[youtube_preview.ResultadoYoutube]

    def __init__(self, artistas: list[str], titulo: str, mix_name: str | None):
        super().__init__()
        self.artistas = artistas
        self.titulo = titulo
        self.mix_name = mix_name

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import youtube_preview
        try:
            candidatos = youtube_preview.buscar_candidatos(self.artistas, self.titulo, self.mix_name)
        except Exception:
            candidatos = []
        self.terminado.emit(candidatos)


class SpotifySearchWorker(QThread):
    """Busca un track en Spotify para un track de los charts — fallback
    cuando ningún candidato de YouTube permite embeberse (restricción del
    dueño). Corre en paralelo a YoutubeSearchWorker para no agregar espera
    extra cuando YouTube sí funciona."""
    terminado = Signal(object)   # spotify_preview.ResultadoSpotify | None

    def __init__(self, artistas: list[str], titulo: str, mix_name: str | None):
        super().__init__()
        self.artistas = artistas
        self.titulo = titulo
        self.mix_name = mix_name

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import spotify_preview
        try:
            resultado = spotify_preview.buscar(self.artistas, self.titulo, self.mix_name)
        except Exception:
            resultado = None
        self.terminado.emit(resultado)


class BackupNubeWorker(QThread):
    """Sube tracks seleccionados al backup personal en la nube (Cloudflare
    R2, vía el backend) — Fase 2 del Módulo 3. Usa la cuenta PERSONAL del DJ
    (`cloud_backup._obtener_jwt`), nunca la cuenta de servicio."""
    progreso = Signal(str)
    terminado = Signal(dict)

    def __init__(self, db_path: str, ids: list[int]):
        super().__init__()
        self.db_path = db_path
        self.ids = ids

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import db as db_mod
        import cloud_backup

        jwt = cloud_backup._obtener_jwt()
        if not jwt:
            self.terminado.emit({"error": "No se pudo iniciar sesión con tu cuenta personal."})
            return

        conn = db_mod.connect(self.db_path)
        subidos = fallidos = 0
        total = len(self.ids)
        for i, tid in enumerate(self.ids, start=1):
            row = conn.execute(
                "SELECT ruta_origen, artista, titulo FROM tracks WHERE id=?", (tid,)
            ).fetchone()
            if not row:
                fallidos += 1
                continue
            etiqueta = f"{row['artista'] or '—'} - {row['titulo'] or '—'}"
            self.progreso.emit(f"☁ Subiendo {i}/{total}: {etiqueta}…")
            ok, msg = cloud_backup.subir_track(
                jwt, row["ruta_origen"], row["titulo"] or "", row["artista"] or ""
            )
            if ok:
                subidos += 1
            else:
                fallidos += 1
                self.progreso.emit(f"  ⚠ {etiqueta}: {msg}")
        conn.close()
        self.terminado.emit({"subidos": subidos, "fallidos": fallidos})


class ArtistasWorker(QThread):
    """Enriquece la BD de artistas consultando Last.fm y Beatport."""
    progreso = Signal(str)
    terminado = Signal(dict)

    def __init__(self, db_path: str, api_key: str = ""):
        super().__init__()
        self.db_path = db_path
        self.api_key = api_key

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import db
        import artist_db
        conn = db.connect(self.db_path)
        res = artist_db.poblar_desde_biblioteca(
            conn,
            api_key=self.api_key,
            progreso_cb=self.progreso.emit,
        )
        conn.close()
        self.terminado.emit(res)


class CoverFillWorker(QThread):
    """Completa carátulas faltantes en segundo plano, sin bloquear la
    toolbar (se lanza directo, no vía MainWindow._lanzar): para cada track
    local sin cover_url, primero pregunta a la Biblioteca Confiable (puede
    que otro DJ ya la haya subido) y si no está ahí, busca en iTunes; lo que
    encuentra por iTunes lo sube de vuelta a la nube para que no haga falta
    volver a buscarlo. Emite encontrada(track_id, url) por cada track
    resuelto para que la grilla se actualice en vivo, sin esperar a que
    termine todo el lote."""
    encontrada = Signal(int, str)      # track_id, cover_url
    progreso_n = Signal(int, int)       # resueltos, total
    terminado = Signal(dict)

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import db
        import biblioteca_confiable
        import itunes_cover

        conn = db.connect(self.db_path)
        filas = conn.execute(
            "SELECT id, artista, titulo, duracion_seg FROM tracks "
            "WHERE (cover_url IS NULL OR cover_url='') "
            "AND artista IS NOT NULL AND titulo IS NOT NULL "
            "AND artista != '' AND titulo != ''"
        ).fetchall()
        total = len(filas)

        desde_nube = desde_itunes = sin_encontrar = 0
        for i, f in enumerate(filas, start=1):
            artista, titulo = f["artista"], f["titulo"]
            url = None

            hit = biblioteca_confiable.buscar(artista, titulo, f["duracion_seg"] or 0)
            if hit and hit.cover_url:
                url = hit.cover_url
                desde_nube += 1
            else:
                url = itunes_cover.obtener_caratula(artista, titulo)
                if url:
                    desde_itunes += 1
                    biblioteca_confiable.actualizar_cover_url(artista, titulo, url)

            if url:
                conn.execute("UPDATE tracks SET cover_url=? WHERE id=?", (url, f["id"]))
                conn.commit()
                self.encontrada.emit(f["id"], url)
            else:
                sin_encontrar += 1
            self.progreso_n.emit(i, total)

        conn.close()
        self.terminado.emit({
            "total": total, "desde_nube": desde_nube,
            "desde_itunes": desde_itunes, "sin_encontrar": sin_encontrar,
        })


class SyncWorker(QThread):
    """Trae cambios de género/playlists hechos desde otro dispositivo (ej.
    Android, más adelante) — corre en background, sin botón ni popups, al
    arrancar la app y cada cierto intervalo (ver MainWindow). Silenciosa:
    si no hay cuenta personal configurada o falla la red, simplemente no
    hace nada (no interrumpe al DJ)."""
    terminado = Signal(dict)

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path

    def run(self):
        proj = os.path.join(os.path.dirname(__file__), "..")
        if proj not in sys.path:
            sys.path.insert(0, proj)
        import cloud_backup
        if not cloud_backup.esta_configurado():
            self.terminado.emit({"tracks": 0, "playlists": 0})
            return

        import cloud_sync
        import db as db_mod
        conn = db_mod.connect(self.db_path)
        n_tracks = cloud_sync.pull_biblioteca(conn)
        n_playlists = cloud_sync.pull_playlists(conn)
        conn.close()
        self.terminado.emit({"tracks": n_tracks, "playlists": n_playlists})


