"""Sincronización de biblioteca personal (género/subgénero/playlists) entre
dispositivos — base para Fase 3 (apps cliente: cuando exista la app de
Android, va a leer/escribir contra estas mismas tablas). Usa la cuenta
PERSONAL del DJ (misma sesión que `cloud_backup.py`), no la cuenta de
servicio.

Resolución de conflictos: "gana el cambio más reciente" — la comparación
real se hace del lado del backend (`/mi-biblioteca/sync`); el pull local
también descarta cambios de la nube más viejos que lo que ya hay acá.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

import requests

import cloud_backup
import settings

BACKEND_URL = cloud_backup.BACKEND_URL

_CLAVE_MARCA = "sync_ultima_marca"


def _norm(texto: str) -> str:
    if not texto:
        return ""
    s = texto.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _headers() -> Optional[dict]:
    jwt = cloud_backup._obtener_jwt()
    if not jwt:
        return None
    return {"Authorization": f"Bearer {jwt}"}


# ------------------------------------------------------------------- tracks

def push_track(track: dict) -> bool:
    """Sube un track editado a la nube. Necesita al menos artista y título.
    Nunca lanza excepción: devuelve False si no se pudo (sin cuenta
    personal configurada, sin red, etc.)."""
    headers = _headers()
    if not headers or not track.get("artista") or not track.get("titulo"):
        return False
    payload = {
        "artista": track["artista"], "titulo": track["titulo"],
        "sello": track.get("sello"), "anio": track.get("anio"),
        "bpm": track.get("bpm"), "key": track.get("key"),
        "camelot": track.get("camelot"), "duracion_seg": track.get("duracion_seg"),
        "genero": track.get("genero"), "subgenero": track.get("subgenero"),
        "energia": track.get("energia"), "r2_key": track.get("r2_key"),
        "actualizado_en": track.get("actualizado_en") or _ahora_iso(),
    }
    try:
        resp = requests.post(
            f"{BACKEND_URL}/mi-biblioteca/sync", headers=headers, json=[payload], timeout=15
        )
        resp.raise_for_status()
        return True
    except Exception:
        return False


def pull_biblioteca(conn) -> int:
    """Trae los cambios de la nube y los aplica al SQLite local si son más
    nuevos que lo que hay ahí (ej. una edición hecha desde Android). Solo
    actualiza tracks que ya existen localmente (matchea por artista/título
    normalizados) — un track que todavía no se escaneó en este dispositivo
    no tiene dónde aplicarse. Devuelve cuántos tracks se actualizaron.

    Incremental: solo pide a la nube lo que cambió desde la última corrida
    exitosa (`since`), guardado en `asistente_config.json` — evita bajar
    toda la biblioteca personal en cada sincronización periódica."""
    headers = _headers()
    if not headers:
        return 0
    marca_previa = settings.get(_CLAVE_MARCA)
    params = {"since": marca_previa} if marca_previa else {}
    try:
        resp = requests.get(
            f"{BACKEND_URL}/mi-biblioteca", headers=headers, params=params, timeout=15
        )
        resp.raise_for_status()
        filas_nube = resp.json()
    except Exception:
        return 0
    if not filas_nube:
        return 0

    locales = conn.execute("SELECT id, artista, titulo, actualizado_en FROM tracks").fetchall()
    indice = {(_norm(r["artista"] or ""), _norm(r["titulo"] or "")): r for r in locales}

    actualizados = 0
    marca_nueva = marca_previa or ""
    for fila in filas_nube:
        if fila["actualizado_en"] > marca_nueva:
            marca_nueva = fila["actualizado_en"]
        clave = (fila["artista_norm"], fila["titulo_norm"])
        local = indice.get(clave)
        if not local:
            continue
        if local["actualizado_en"] and local["actualizado_en"] >= fila["actualizado_en"]:
            continue
        conn.execute(
            "UPDATE tracks SET genero=?, subgenero=?, bpm=?, key=?, camelot=?, "
            "actualizado_en=? WHERE id=?",
            (fila.get("genero"), fila.get("subgenero"), fila.get("bpm"), fila.get("key"),
             fila.get("camelot"), fila["actualizado_en"], local["id"]),
        )
        actualizados += 1
    if actualizados:
        conn.commit()
    if marca_nueva != (marca_previa or ""):
        settings.set_(_CLAVE_MARCA, marca_nueva)
    return actualizados


# ---------------------------------------------------------------- playlists

def push_playlist(nombre: str, ids_locales: list[int], conn) -> bool:
    """Sube una playlist. Los ids locales se traducen a ids de
    `mi_biblioteca` en la nube — solo se pueden subir tracks que ya estén
    sincronizados (vía `push_track`)."""
    headers = _headers()
    if not headers or not ids_locales:
        return False
    placeholders = ",".join("?" * len(ids_locales))
    filas = conn.execute(
        f"SELECT artista, titulo FROM tracks WHERE id IN ({placeholders})", ids_locales
    ).fetchall()
    claves = [(_norm(r["artista"] or ""), _norm(r["titulo"] or "")) for r in filas]

    try:
        resp = requests.get(
            f"{BACKEND_URL}/mi-biblioteca", headers=headers,
            params={"solo_ids": "true"}, timeout=15
        )
        resp.raise_for_status()
        nube = resp.json()
    except Exception:
        return False
    indice_nube = {(f["artista_norm"], f["titulo_norm"]): f["id"] for f in nube}

    ids_nube = [indice_nube[c] for c in claves if c in indice_nube]
    if not ids_nube:
        return False  # ninguno de los tracks de la playlist está sincronizado todavía

    payload = {"nombre": nombre, "ids": ids_nube, "actualizado_en": _ahora_iso()}
    try:
        resp = requests.post(
            f"{BACKEND_URL}/mi-biblioteca/playlists", headers=headers, json=payload, timeout=15
        )
        resp.raise_for_status()
        return True
    except Exception:
        return False


_CLAVE_MARCA_PLAYLISTS = "sync_ultima_marca_playlists"


def pull_playlists(conn) -> int:
    """Trae las playlists de la nube (ej. creadas desde Android) y las
    aplica localmente, traduciendo los ids de `mi_biblioteca` a ids locales
    por artista/título. Devuelve cuántas playlists se aplicaron.

    Las playlists en sí se piden de forma incremental (`since`, marca
    propia); el mapeo id→artista/título de `mi_biblioteca` necesita
    traerse completo siempre (una playlist puede referenciar un track que
    no cambió hace tiempo), pero pesa poco porque solo pide esas 3 columnas
    (`solo_ids`)."""
    headers = _headers()
    if not headers:
        return 0
    marca_previa = settings.get(_CLAVE_MARCA_PLAYLISTS)
    params = {"since": marca_previa} if marca_previa else {}
    try:
        resp = requests.get(
            f"{BACKEND_URL}/mi-biblioteca", headers=headers,
            params={"solo_ids": "true"}, timeout=15
        )
        resp.raise_for_status()
        nube_tracks = resp.json()
        resp2 = requests.get(
            f"{BACKEND_URL}/mi-biblioteca/playlists", headers=headers,
            params=params, timeout=15
        )
        resp2.raise_for_status()
        nube_playlists = resp2.json()
    except Exception:
        return 0
    if not nube_playlists:
        return 0

    marca_nueva = marca_previa or ""
    for pl in nube_playlists:
        if pl["actualizado_en"] > marca_nueva:
            marca_nueva = pl["actualizado_en"]

    id_nube_a_clave = {f["id"]: (f["artista_norm"], f["titulo_norm"]) for f in nube_tracks}
    locales = conn.execute("SELECT id, artista, titulo FROM tracks").fetchall()
    indice_local = {(_norm(r["artista"] or ""), _norm(r["titulo"] or "")): r["id"] for r in locales}

    aplicadas = 0
    for pl in nube_playlists:
        ids_locales = []
        for id_nube in pl["reglas"].get("ids", []):
            clave = id_nube_a_clave.get(id_nube)
            if clave and clave in indice_local:
                ids_locales.append(indice_local[clave])
        if not ids_locales:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO playlists (nombre, reglas) VALUES (?, ?)",
            (pl["nombre"], json.dumps({"ids": ids_locales})),
        )
        aplicadas += 1
    if aplicadas:
        conn.commit()
    if marca_nueva != (marca_previa or ""):
        settings.set_(_CLAVE_MARCA_PLAYLISTS, marca_nueva)
    return aplicadas
