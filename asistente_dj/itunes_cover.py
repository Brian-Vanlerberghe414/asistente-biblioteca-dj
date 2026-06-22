"""Carátulas (cover art) de tracks vía la API pública de búsqueda de
iTunes/Apple Music (https://itunes.apple.com/search). Gratis, sin API key.

  https://itunes.apple.com/search?term=ARTISTA+TITULO&entity=song&limit=5

La API devuelve `artworkUrl100` en formato .../100x100bb.jpg; se reemplaza
por una resolución más alta cambiando "100x100bb" por "{size}x{size}bb"
(parámetro `size`, 600 por defecto).

Límite documentado de Apple: ~20 requests/minuto por IP. Para uso en lote
(`obtener_caratulas_lote`) las llamadas se espacian con un delay mínimo
configurable en vez de mandarlas todas juntas.
"""
from __future__ import annotations

import time

import requests

BASE = "https://itunes.apple.com/search"

# Espacio mínimo entre requests (seg) para no pasar el límite de ~20/min de Apple.
DELAY_MIN_DEFAULT = 3.0

# Caché en memoria: evita repetir requests del mismo track en la misma sesión.
_cache: dict[str, str | None] = {}
_ultimo_request = 0.0


def _clave(artista: str, titulo: str) -> str:
    return f"{(artista or '').strip().lower()}|{(titulo or '').strip().lower()}"


def _esperar_turno(delay_min: float) -> None:
    """Throttle simple: si la última llamada fue hace menos de delay_min
    segundos, duerme lo que falte antes de dejar pasar la siguiente."""
    global _ultimo_request
    transcurrido = time.monotonic() - _ultimo_request
    if transcurrido < delay_min:
        time.sleep(delay_min - transcurrido)
    _ultimo_request = time.monotonic()


def obtener_caratula(
    artista: str,
    titulo: str,
    size: int = 600,
    timeout: int = 5,
    delay_min: float = DELAY_MIN_DEFAULT,
) -> str | None:
    """Busca la carátula de un track por artista+título en la iTunes Search
    API y devuelve la URL en alta resolución (size x size), o None si no hay
    resultados, si falla la consulta, o si no se pudo conectar — nunca
    lanza excepción (es seguro llamarla en un loop de procesamiento masivo).

    Cachea el resultado en memoria por (artista, título) normalizados: una
    segunda llamada con el mismo track no genera un request nuevo.
    """
    clave = _clave(artista, titulo)
    if clave in _cache:
        return _cache[clave]

    termino = f"{artista or ''} {titulo or ''}".strip()
    if not termino:
        _cache[clave] = None
        return None

    _esperar_turno(delay_min)
    try:
        resp = requests.get(
            BASE,
            params={"term": termino, "entity": "song", "limit": 5},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[itunes_cover] error buscando '{termino}': {e}")
        _cache[clave] = None
        return None

    url = None
    for r in data.get("results") or []:
        artwork = r.get("artworkUrl100")
        if artwork:
            url = artwork.replace("100x100bb", f"{size}x{size}bb")
            break

    _cache[clave] = url
    return url


def obtener_caratulas_lote(
    tracks: list[dict],
    size: int = 600,
    timeout: int = 5,
    delay_min: float = DELAY_MIN_DEFAULT,
) -> list[dict]:
    """Resuelve la carátula de varios tracks respetando el rate limit.

    tracks: lista de dicts con al menos "artista" y "titulo".
    Devuelve una lista paralela de dicts {"artista", "titulo", "cover_url"}
    (cover_url es None si no se encontró). Los tracks repetidos dentro del
    mismo lote no generan requests adicionales gracias a la caché.
    """
    resultado = []
    for t in tracks:
        artista = t.get("artista", "")
        titulo = t.get("titulo", "")
        url = obtener_caratula(
            artista, titulo, size=size, timeout=timeout, delay_min=delay_min
        )
        resultado.append({"artista": artista, "titulo": titulo, "cover_url": url})
    return resultado


def limpiar_cache() -> None:
    """Vacía la caché en memoria (útil en tests, o para forzar un re-fetch)."""
    _cache.clear()


if __name__ == "__main__":
    # ── Ejemplo 1: un solo track ─────────────────────────────────────────
    url = obtener_caratula("Daft Punk", "One More Time")
    print("Carátula:", url)

    # ── Ejemplo 2: lote, respetando el rate limit ───────────────────────
    lote = obtener_caratulas_lote(
        [
            {"artista": "Daft Punk", "titulo": "One More Time"},
            {"artista": "Justice", "titulo": "D.A.N.C.E."},
            {"artista": "Daft Punk", "titulo": "One More Time"},  # repetido: sale de la caché
        ]
    )
    for item in lote:
        print(f"{item['artista']} - {item['titulo']} -> {item['cover_url']}")
