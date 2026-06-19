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
            conn.close()
            self.terminado.emit({
                "actualizados": act,
                "sin_match": sin_match,
                "sin_bpm": sin_bpm,
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


