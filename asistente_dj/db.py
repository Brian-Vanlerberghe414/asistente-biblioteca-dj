"""Base de datos SQLite del Asistente DJ (prototipo: tabla tracks)."""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ruta_origen     TEXT UNIQUE,
    ruta_destino    TEXT,
    titulo          TEXT,
    artista         TEXT,
    sello           TEXT,
    anio            TEXT,
    bpm             TEXT,
    key             TEXT,
    duracion_seg    REAL,
    genero_raw      TEXT,
    genero          TEXT,
    subgenero       TEXT,
    confianza       TEXT,
    bitrate_kbps    INTEGER,
    formato         TEXT,
    baja_calidad    INTEGER DEFAULT 0,
    estado          TEXT DEFAULT 'escaneado',   -- escaneado | archivado | por_revisar
    fecha_ingreso   TEXT
);

CREATE TABLE IF NOT EXISTS playlists (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT UNIQUE,
    reglas  TEXT     -- JSON con los filtros de la playlist inteligente
);

CREATE TABLE IF NOT EXISTS modelo_energia (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    coef    TEXT,    -- JSON con los coeficientes aprendidos del oído del DJ
    n_muestras INTEGER,
    fecha   TEXT
);

CREATE TABLE IF NOT EXISTS artistas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre              TEXT UNIQUE NOT NULL,
    nombre_norm         TEXT NOT NULL,
    generos             TEXT,   -- JSON: [["Techno","Peak Time"],["Techno",null]]
    fuente              TEXT,   -- 'lastfm' | 'beatport' | 'manual' | 'ninguna'
    fecha_actualizacion TEXT
);

-- Módulo 2 (Descubrimiento): charts de Beatport scrapeados (sin credenciales).
CREATE TABLE IF NOT EXISTS charts_tracks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    beatport_id     TEXT NOT NULL,
    genero_slug     TEXT NOT NULL,    -- 'global' o el slug del género/subgénero
    genero_nombre   TEXT,
    posicion        INTEGER,
    nombre          TEXT,
    mix_name        TEXT,
    artistas        TEXT,             -- JSON: lista de nombres
    remixers        TEXT,             -- JSON: lista de nombres
    release         TEXT,
    sello           TEXT,
    bpm             REAL,
    key             TEXT,
    genero_pista    TEXT,             -- género de Beatport para ESTE track (chart global)
    duracion_ms     INTEGER,
    publish_date    TEXT,
    image_url       TEXT,
    primera_vez     TEXT,             -- fecha en que se vio por 1ra vez en este género
    fecha_scrape    TEXT,             -- fecha del scrape más reciente donde apareció
    UNIQUE(beatport_id, genero_slug)
);

-- Módulo 2: lista de "para conseguir" (tracks vistos en charts o a mano).
CREATE TABLE IF NOT EXISTS para_conseguir (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    beatport_id     TEXT,
    nombre          TEXT NOT NULL,
    artistas        TEXT,
    sello           TEXT,
    notas           TEXT,
    fecha_agregado  TEXT,
    conseguido      INTEGER DEFAULT 0
);
"""


# Columnas agregadas por el módulo de análisis de audio (migración suave).
_NEW_COLS = {
    "energia": "INTEGER",            # energía automática (1-10, por percentiles)
    "energia_manual": "INTEGER",     # ajuste manual de Brian (manda sobre la auto)
    "energia_raw": "REAL",           # valor crudo de intensidad (para percentiles)
    "camelot": "TEXT",
    "genero_sugerido": "TEXT",
    "subgenero_sugerido": "TEXT",
    "nota_sugerencia": "TEXT",
    "analizado": "INTEGER DEFAULT 0",
    "bpm_fuente": "TEXT",       # 'rekordbox' | 'tag' | 'audio'
    # rasgos acústicos individuales (inputs del aprendizaje de energía)
    "f_loud": "REAL",
    "f_bright": "REAL",
    "f_low": "REAL",
    "f_busy": "REAL",
    # huella acústica (Chromaprint) para detectar duplicados
    "huella": "TEXT",
    "huella_dur": "REAL",
    # waveform pre-computada para visualización (base64+zlib, JSON)
    "waveform_data": "TEXT",
    # estado de sincronización con la BD compartida en la nube
    "cloud_status": "TEXT",   # NULL | 'pendiente' | 'enviado'
    # última edición manual (genero/subgenero/etc.) — para sincronización
    # de biblioteca personal multi-dispositivo ("gana el más reciente")
    "actualizado_en": "TEXT",
}


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tracks)").fetchall()}
    for col, typ in _NEW_COLS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE tracks ADD COLUMN {col} {typ}")

    existing_charts = {r[1] for r in conn.execute("PRAGMA table_info(charts_tracks)").fetchall()}
    if "genero_pista" not in existing_charts:
        conn.execute("ALTER TABLE charts_tracks ADD COLUMN genero_pista TEXT")


def _limpiar_basura(conn: sqlite3.Connection) -> int:
    """Elimina registros que no son música (resource forks ._*, .DS_Store)."""
    rows = conn.execute("SELECT id, ruta_origen FROM tracks").fetchall()
    n = 0
    for r in rows:
        base = r[1].replace("\\", "/").rsplit("/", 1)[-1]
        if base.startswith("._") or base in (".DS_Store", "Thumbs.db"):
            conn.execute("DELETE FROM tracks WHERE id=?", (r[0],))
            n += 1
    if n:
        conn.commit()
    return n


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    _limpiar_basura(conn)
    return conn


def upsert_track(conn: sqlite3.Connection, data: dict) -> None:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    updates = ", ".join(f"{k}=excluded.{k}" for k in data if k != "ruta_origen")
    sql = (
        f"INSERT INTO tracks ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(ruta_origen) DO UPDATE SET {updates}"
    )
    conn.execute(sql, list(data.values()))


def upsert_chart_track(conn: sqlite3.Connection, data: dict, fecha: str) -> bool:
    """Inserta o actualiza una fila de `charts_tracks`. `data` no debe traer
    `primera_vez`/`fecha_scrape` (los pone esta función). Devuelve True si es
    una entrada nueva en ese género (para detectar "novedades")."""
    existe = conn.execute(
        "SELECT 1 FROM charts_tracks WHERE beatport_id=? AND genero_slug=?",
        (data["beatport_id"], data["genero_slug"]),
    ).fetchone()
    payload = dict(data, fecha_scrape=fecha)
    if existe:
        sets = ", ".join(f"{k}=?" for k in payload if k not in ("beatport_id", "genero_slug"))
        vals = [v for k, v in payload.items() if k not in ("beatport_id", "genero_slug")]
        conn.execute(
            f"UPDATE charts_tracks SET {sets} WHERE beatport_id=? AND genero_slug=?",
            vals + [data["beatport_id"], data["genero_slug"]],
        )
        return False
    payload["primera_vez"] = fecha
    cols = ", ".join(payload.keys())
    placeholders = ", ".join(["?"] * len(payload))
    conn.execute(f"INSERT INTO charts_tracks ({cols}) VALUES ({placeholders})",
                 list(payload.values()))
    return True


def count(conn: sqlite3.Connection, where: str = "", params=()) -> int:
    sql = "SELECT COUNT(*) FROM tracks"
    if where:
        sql += f" WHERE {where}"
    return conn.execute(sql, params).fetchone()[0]
