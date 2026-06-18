"""Buscador de BPM/key vía la API pública de GetSongBPM (https://getsongbpm.com).

Gratis, pero requiere una API key (registro + backlink obligatorio a
getsongbpm.com). Devuelve BPM y key por artista+título.

  Base: https://api.getsong.co/
  /search/?api_key=KEY&type=both&lookup=song:TITULO artist:ARTISTA&limit=N

Como los tracks de DJ suelen venir con títulos "sucios" (Original Mix, feat.,
números de pista) y artistas múltiples, antes de consultar se limpian los
nombres, y si no hay match se reintenta solo con el título.

Límite: 3000 requests/hora por key.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE = "https://api.getsong.co"


@dataclass
class SongData:
    bpm: str = ""
    key: str = ""        # key_of normalizada, ej. "Gbm"
    camelot: str = ""
    danceability: int | None = None
    ok: bool = False
    error: str = ""


# ----------------------------------------------------- limpieza de nombres
def limpiar_titulo(t: str) -> str:
    if not t:
        return ""
    s = t
    s = re.sub(r"^\s*\d{1,3}\s*[-_.\)]?\s*", "", s)           # número de pista
    s = re.sub(r"[\(\[].*?[\)\]]", "", s)                      # (...) [...]
    s = re.sub(r"\b(feat\.?|ft\.?|featuring)\b.*$", "", s, flags=re.I)
    s = re.sub(r"\s*-\s*[^-]*\b(mix|edit|version|remix|dub|rework|bootleg)\b.*$",
               "", s, flags=re.I)
    return s.strip(" -_").strip()


def limpiar_artista(a: str) -> str:
    if not a:
        return ""
    return re.split(r"\s*(?:,| feat\.?| ft\.?| featuring | with | vs\.?| x )\s*",
                    a, flags=re.I)[0].strip()


def _norm(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum())


# ----------------------------------------------------- key -> Camelot
_NOTE_ALIAS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
_CAMELOT_MIN = {"A": "8A", "E": "9A", "B": "10A", "F#": "11A", "C#": "12A",
                "G#": "1A", "D#": "2A", "A#": "3A", "F": "4A", "C": "5A",
                "G": "6A", "D": "7A"}
_CAMELOT_MAJ = {"C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B",
                "B": "1B", "F#": "2B", "C#": "3B", "G#": "4B", "D#": "5B",
                "A#": "6B", "F": "7B"}


def normalizar_key(k: str) -> str:
    """Convierte símbolos unicode ♭/♯ a b/# y limpia espacios."""
    if not k:
        return ""
    return k.replace("♭", "b").replace("♯", "#").strip()


def key_a_camelot(key_of: str) -> str:
    if not key_of:
        return ""
    s = normalizar_key(key_of)
    menor = s.endswith("m")
    nota = (s[:-1] if menor else s).strip()
    if not nota:
        return ""
    base = nota[0].upper()
    acc = nota[1:2]
    if acc == "B":
        acc = "b"
    nota = base + (acc if acc in ("#", "b") else "")
    nota = _NOTE_ALIAS.get(nota, nota)
    return (_CAMELOT_MIN if menor else _CAMELOT_MAJ).get(nota, "")


# ----------------------------------------------------- HTTP
def _query(api_key: str, tipo: str, lookup: str, timeout: int):
    """Devuelve la lista de songs, [] si no hay resultados, o None si falla la red."""
    params = urllib.parse.urlencode(
        {"api_key": api_key, "type": tipo, "lookup": lookup, "limit": 5})
    url = f"{BASE}/search/?{params}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "ignore")
    except Exception:
        return None
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    songs = data.get("search") if isinstance(data, dict) else None
    # En "sin resultados" la API devuelve search como dict de error, no lista
    return songs if isinstance(songs, list) else []


def _mejor(songs, art_norm: str, verificar: bool):
    """Elige el mejor match; si verificar, exige que el artista coincida algo."""
    if not songs:
        return None
    if not verificar or not art_norm:
        return songs[0]
    for s in songs:
        a = s.get("artist") or {}
        nombre = _norm(a.get("name") if isinstance(a, dict) else "")
        if nombre and (nombre in art_norm or art_norm in nombre
                       or _solapan(nombre, art_norm)):
            return s
    return None


def _solapan(a: str, b: str) -> bool:
    # comparten al menos 4 caracteres consecutivos significativos
    return len(a) >= 4 and len(b) >= 4 and (a[:5] in b or b[:5] in a)


def buscar(api_key: str, artista: str, titulo: str, timeout: int = 12) -> SongData:
    out = SongData()
    tit = limpiar_titulo(titulo)
    art = limpiar_artista(artista)
    if not tit:
        out.error = "sin título"
        return out

    # Intento 1: título + artista
    lookup = f"song:{tit}" + (f" artist:{art}" if art else "")
    res = _query(api_key, "both", lookup, timeout)
    if res is None:
        out.error = "red"
        return out
    song = _mejor(res, _norm(art), verificar=False)

    # Intento 2: solo título (verificando que el artista coincida)
    if song is None:
        res2 = _query(api_key, "song", tit, timeout)
        if res2 is None:
            out.error = "red"
            return out
        song = _mejor(res2, _norm(art), verificar=True)

    if song is None:
        out.error = "sin resultados"
        return out

    out.bpm = str(song.get("tempo") or "")
    out.key = normalizar_key(song.get("key_of") or "")
    out.camelot = key_a_camelot(out.key)
    try:
        out.danceability = int(song.get("danceability")) if song.get("danceability") is not None else None
    except Exception:
        out.danceability = None
    out.ok = bool(out.bpm) or bool(out.key)
    return out
