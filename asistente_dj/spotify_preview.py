"""Búsqueda de tracks en Spotify — fallback de preview cuando YouTube no deja
embeber un video (restricción del dueño por Content ID, ver
`youtube_preview.py`). El embed de Spotify es mucho más permisivo (está
diseñado para insertarse en cualquier sitio), pero sin que el usuario inicie
sesión solo reproduce 30s de preview, no el track completo — por eso es un
fallback, no el primer intento.

Credenciales: Client ID + Secret de una app gratis en
https://developer.spotify.com/dashboard (flujo Client Credentials — no hace
falta que ningún usuario inicie sesión, sirve solo para *buscar* tracks; el
embed en sí no necesita key).
  python cli.py config --spotify-client-id ID --spotify-client-secret SECRET
"""
from __future__ import annotations

import base64
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Optional

import requests

import settings

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SEARCH_URL = "https://api.spotify.com/v1/search"
_UMBRAL_MINIMO = 1.5

_token_cache = {"token": None, "expira": 0.0}


def esta_configurado() -> bool:
    cfg = settings.cargar()
    return bool(cfg.get("spotify_client_id") and cfg.get("spotify_client_secret"))


def _get_token() -> Optional[str]:
    if _token_cache["token"] and time.time() < _token_cache["expira"]:
        return _token_cache["token"]
    cfg = settings.cargar()
    client_id = cfg.get("spotify_client_id", "").strip()
    client_secret = cfg.get("spotify_client_secret", "").strip()
    if not client_id or not client_secret:
        return None
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        resp = requests.post(
            _TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {auth}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    _token_cache["token"] = data["access_token"]
    _token_cache["expira"] = time.time() + data.get("expires_in", 3600) - 30
    return _token_cache["token"]


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class ResultadoSpotify:
    track_id: str
    titulo: str
    es_extended: bool


def buscar(artistas: list[str], titulo: str, mix_name: Optional[str] = None) -> Optional[ResultadoSpotify]:
    """Busca el mejor match en Spotify para `titulo` de `artistas`. Nunca
    lanza excepción: devuelve None si no está configurado, falla la red, o
    no hay un match con confianza suficiente."""
    token = _get_token()
    if not token or not titulo:
        return None

    quiere_extended = bool(mix_name) and "extended" in mix_name.lower()
    query = f"{' '.join((artistas or [])[:2])} {titulo}".strip()
    try:
        resp = requests.get(
            _SEARCH_URL,
            params={"q": query, "type": "track", "limit": 10},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("tracks", {}).get("items", [])
    except Exception:
        return None

    tit_norm = _norm(titulo)
    artistas_norm = [_norm(a) for a in (artistas or []) if a]
    mejor, mejor_score = None, 0.0
    for item in items:
        nombre_norm = _norm(item.get("name") or "")
        if tit_norm and tit_norm in nombre_norm:
            score = 3.0
        else:
            palabras = tit_norm.split()
            score = 3.0 * sum(1 for p in palabras if p in nombre_norm) / len(palabras) if palabras else 0.0
        artistas_item_norm = [_norm(a["name"]) for a in item.get("artists", [])]
        if any(a in artistas_item_norm for a in artistas_norm):
            score += 1.5
        es_ext = "extended" in nombre_norm
        if quiere_extended and es_ext:
            score += 2.0
        elif not quiere_extended and not es_ext:
            score += 0.5
        if score > mejor_score:
            mejor_score, mejor = score, (item, es_ext)

    if mejor is None or mejor_score < _UMBRAL_MINIMO:
        return None
    item, es_ext = mejor
    return ResultadoSpotify(track_id=item["id"], titulo=item.get("name") or titulo, es_extended=es_ext)
