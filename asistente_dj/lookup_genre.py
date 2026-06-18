"""Búsqueda de género online: MusicBrainz (sin key) + Last.fm (key gratuita).

Uso:
    from lookup_genre import lookup
    genero, subgenero, fuente = lookup("Amelie Lens", "Forever", lastfm_key="xxx")
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

MB_URL  = "https://musicbrainz.org/ws/2/recording"
LFM_URL = "http://ws.audioscrobbler.com/2.0/"
UA      = "AsistenteDJ/1.0 (emangonz95@gmail.com)"


def _mb_tags(artista: str, titulo: str) -> list[str]:
    """Busca en MusicBrainz y devuelve tags ordenados por popularidad."""
    q = f'artist:"{artista}" AND recording:"{titulo}"'
    url = f"{MB_URL}?query={urllib.parse.quote(q)}&fmt=json&inc=tags"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    recs = data.get("recordings", [])
    if not recs:
        return []
    tags = recs[0].get("tags", [])
    return [t["name"] for t in sorted(tags, key=lambda x: -x.get("count", 0))]


def _lfm_track_tags(artista: str, titulo: str, api_key: str) -> list[str]:
    """Tags del track en Last.fm."""
    params = {
        "method": "track.getInfo",
        "api_key": api_key,
        "artist": artista,
        "track": titulo,
        "format": "json",
        "autocorrect": "1",
    }
    url = LFM_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    if "error" in data:
        return []
    toptags = data.get("track", {}).get("toptags", {}).get("tag", [])
    return [t["name"] for t in toptags]


def _lfm_artist_tags(artista: str, api_key: str) -> list[str]:
    """Tags del artista en Last.fm (fallback cuando el track no tiene tags)."""
    params = {
        "method": "artist.getTopTags",
        "api_key": api_key,
        "artist": artista,
        "format": "json",
        "autocorrect": "1",
    }
    url = LFM_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    if "error" in data:
        return []
    toptags = data.get("toptags", {}).get("tag", [])
    return [t["name"] for t in toptags]


def _lfm_tags(artista: str, titulo: str, api_key: str) -> list[str]:
    """Tags de Last.fm: primero del track, si vacío usa los del artista."""
    tags = _lfm_track_tags(artista, titulo, api_key)
    if not tags:
        tags = _lfm_artist_tags(artista, api_key)
    return tags


def lookup(
    artista: str,
    titulo: str,
    lastfm_key: str | None = None,
) -> tuple[str | None, str | None, str]:
    """Busca el género online por artista+título.

    Retorna (genero, subgenero, fuente) o (None, None, '') si no encontró.
    Intenta MusicBrainz primero; si no hay tags y hay key, prueba Last.fm.
    """
    from classifier import classify

    tags: list[str] = []
    fuente = ""

    try:
        tags = _mb_tags(artista, titulo)
        if tags:
            fuente = "musicbrainz"
    except Exception:
        pass

    if not tags and lastfm_key:
        try:
            tags = _lfm_tags(artista, titulo, lastfm_key)
            if tags:
                fuente = "lastfm"
        except Exception:
            pass

    for tag in tags:
        c = classify(tag)
        if c.genero:
            return c.genero, c.subgenero, fuente

    return None, None, fuente


def lookup_batch(
    tracks: list[dict],
    lastfm_key: str | None = None,
    delay: float = 1.1,
    progreso_cb=None,
) -> dict:
    """Busca géneros para una lista de tracks.

    Cada elemento debe tener 'id', 'artista', 'titulo'.
    progreso_cb(msg: str) se llama por cada track procesado.
    Retorna dict con listas 'ok', 'sin_match', 'errores'.
    """
    import time

    resultado = {"ok": [], "sin_match": [], "errores": []}
    total = len(tracks)

    for i, r in enumerate(tracks, 1):
        artista = r.get("artista") or ""
        titulo  = r.get("titulo")  or ""
        if not artista or not titulo:
            resultado["sin_match"].append(r["id"])
            if progreso_cb:
                progreso_cb(f"[{i}/{total}] (sin artista/título) — saltado")
            continue
        try:
            g, sg, fuente = lookup(artista, titulo, lastfm_key)
            if g:
                resultado["ok"].append({"id": r["id"], "genero": g, "subgenero": sg, "fuente": fuente})
                if progreso_cb:
                    progreso_cb(f"[{i}/{total}] {artista} — {titulo}  →  {g}/{sg or ''}  [{fuente}]")
            else:
                resultado["sin_match"].append(r["id"])
                if progreso_cb:
                    progreso_cb(f"[{i}/{total}] {artista} — {titulo}  →  sin match")
        except Exception as e:
            resultado["errores"].append(r["id"])
            if progreso_cb:
                progreso_cb(f"[{i}/{total}] {artista} — {titulo}  →  error: {e}")

        if i < total:
            time.sleep(delay)

    return resultado
