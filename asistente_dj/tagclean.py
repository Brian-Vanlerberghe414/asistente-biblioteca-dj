"""Limpieza de "tags basura": URLs y nombres de sitios de descarga que se
cuelan en los metadatos (título, artista, sello, género).

Ej: 'Not The Same (Extended Mix) [WwW.BaniCrazy.NeT]' -> 'Not The Same (Extended Mix)'
    'djsoundtop.com' (como género) -> '' (vacío)
"""
from __future__ import annotations

import re

# URLs, www.algo, o tokens tipo dominio (palabra.tld) con extensiones comunes
_TLD = ("com", "net", "org", "info", "biz", "pl", "io", "me", "co", "cc",
        "tv", "ru", "to", "club", "store", "download", "music", "online", "xyz")
# Captura un eventual corchete/paréntesis que envuelve a la URL, para no dejarlo huérfano
_PATRON = re.compile(
    r"[\(\[\{]?\s*"
    r"(?:https?://[^\s\)\]\}]+|www\.[^\s\)\]\}]+|"
    r"\b[\w-]{2,}\.(?:" + "|".join(_TLD) + r")\b[^\s\)\]\}]*)"
    r"\s*[\)\]\}]?",
    re.IGNORECASE)


def tiene_basura(s: str) -> bool:
    return bool(s) and bool(_PATRON.search(s))


def limpiar(s: str) -> str:
    """Quita URLs/dominios y la puntuación que queda colgando."""
    if not s:
        return s
    out = _PATRON.sub(" ", s)
    out = re.sub(r"[\(\[\{]\s*[\)\]\}]", " ", out)      # paréntesis/corchetes vacíos
    out = re.sub(r"\s{2,}", " ", out)
    out = out.strip(" -_|/·•@~.")                        # separadores colgantes
    return out.strip()


def limpiar_campo(valor: str, permitir_vacio: bool) -> str:
    """Limpia un campo. Si tras limpiar queda vacío:
      - permitir_vacio=True  -> devuelve '' (campos como sello/género)
      - permitir_vacio=False -> conserva el original (campos como título/artista)."""
    if not valor:
        return valor
    limpio = limpiar(valor)
    if not limpio and not permitir_vacio:
        return valor
    return limpio


# Campos a limpiar y si pueden quedar vacíos
CAMPOS = {
    "titulo": False,
    "artista": False,
    "sello": True,
    "genero_raw": True,
}
