"""Scraper de los charts Top 100 de Beatport (global + por género).

Módulo 2 — Descubrimiento, primera pieza: leer los charts públicos de
Beatport sin credenciales. Beatport es una SPA en Next.js, así que no basta
con requests+BeautifulSoup; usamos Playwright para cargar la página e
interceptar la respuesta de su API interna (api-internal.beatportprod.com),
con el JSON embebido en __NEXT_DATA__ como respaldo si la API no aparece.

Diseño con backend intercambiable (decisión en CLAUDE.md): cuando haya
credenciales de la API oficial v4 (OAuth), se reemplaza este módulo sin
tocar el resto — el contrato hacia afuera son listas de dicts con las
mismas claves, consumidas por `cli.py` para upsertear en `charts_tracks`.

Basado en el scraper que pegó el usuario en "charts beatport/beatport_scraper.py".
"""
from __future__ import annotations

import asyncio
import logging
import re

BEATPORT_BASE = "https://www.beatport.com"
BEATPORT_GLOBAL_TOP100 = f"{BEATPORT_BASE}/top-100"
BEATPORT_CHARTS_PAGE = f"{BEATPORT_BASE}/charts"
REQUEST_DELAY = 1800.0  # 30 min entre cada Top 100 (global o de un género).
# Subido de 2s a 30min tras varios bloqueos de Cloudflare durante pruebas con
# corridas seguidas en poco tiempo (sesión 2026-06-18). Con ~46 géneros, una
# corrida completa de `charts-scrape` tarda muchas horas — pensado para
# dejarlo corriendo en segundo plano, no para una espera interactiva.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

GENRE_URL_RE = re.compile(r"^/genre/([^/]+)/(\d+)")

log = logging.getLogger(__name__)


def _parsear_tracks(results: list) -> list[dict]:
    tracks = []
    for i, track in enumerate(results, start=1):
        try:
            release = track.get("release") or {}
            tracks.append({
                "beatport_id": str(track.get("id")),
                "posicion": i,
                "nombre": track.get("name"),
                "mix_name": track.get("mix_name"),
                "artistas": [a["name"] for a in track.get("artists", [])],
                "remixers": [r["name"] for r in track.get("remixers", [])],
                "release": release.get("name"),
                "sello": (release.get("label") or {}).get("name"),
                "bpm": track.get("bpm"),
                "key": (track.get("key") or {}).get("name"),
                "genero_pista": (track.get("genre") or {}).get("name"),
                "duracion_ms": track.get("length_ms"),
                "publish_date": track.get("publish_date"),
                "image_url": (release.get("image") or {}).get("uri"),
            })
        except Exception as exc:
            log.warning(f"Track en posición {i} salteado: {exc}")
    return tracks


def _results_from_next_data(next_data: dict) -> list:
    queries = (
        next_data.get("props", {}).get("pageProps", {})
        .get("dehydratedState", {}).get("queries", [])
    )
    for query in queries:
        results = query.get("state", {}).get("data", {}).get("results", [])
        if results:
            return results
    return []


async def _scrape_pagina(page, url: str) -> list:
    """Carga `url` y devuelve la lista cruda de resultados (intercepta la API
    interna primero; si no aparece, cae al JSON embebido en __NEXT_DATA__).

    Beatport nunca llega a "networkidle" de verdad (pings de analytics
    constantes), así que esperar eso solo agrega 30s de timeout garantizado;
    en cambio esperamos el DOM y le damos un margen fijo a la hidratación
    de React/Next para que el JSON quede armado."""
    api_results: list = []

    async def on_response(response):
        if api_results:
            return
        if "api-internal.beatportprod.com" in response.url and "top-100" in response.url:
            try:
                data = await response.json()
                items = data.get("results", [])
                if items:
                    api_results.extend(items)
            except Exception:
                pass

    page.on("response", on_response)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    except Exception as exc:
        log.warning(f"goto falló para {url}: {exc}")
    await page.wait_for_timeout(8_000)
    page.remove_listener("response", on_response)

    if api_results:
        return api_results

    try:
        js = ("() => { const el = document.getElementById('__NEXT_DATA__'); "
              "return el ? JSON.parse(el.textContent) : null; }")
        next_data = await page.evaluate(js)
        if next_data:
            results = _results_from_next_data(next_data)
            if results:
                return results
    except Exception as exc:
        log.warning(f"__NEXT_DATA__ falló para {url}: {exc}")

    return []


async def _descubrir_generos(page) -> list[dict]:
    """Recolecta todas las URL de Top 100 por género/subgénero desde la
    página de charts de Beatport."""
    try:
        await page.goto(BEATPORT_CHARTS_PAGE, wait_until="domcontentloaded", timeout=30_000)
    except Exception as exc:
        log.warning(f"goto falló para {BEATPORT_CHARTS_PAGE}: {exc}")
    await page.wait_for_timeout(8_000)

    anchors = await page.query_selector_all("a[href]")
    seen: set = set()
    generos: list = []
    for anchor in anchors:
        href = await anchor.get_attribute("href") or ""
        m = GENRE_URL_RE.match(href)
        if not m:
            continue
        slug, genre_id = m.group(1), m.group(2)
        key = f"{slug}/{genre_id}"
        if key in seen:
            continue
        seen.add(key)
        nombre = (await anchor.inner_text()).strip() or slug.replace("-", " ").title()
        generos.append({
            "nombre": nombre, "slug": slug, "id": genre_id,
            "url": f"{BEATPORT_BASE}/genre/{slug}/{genre_id}/top-100",
        })
    return generos


async def _ejecutar_async(generos_filtro: list[str] | None, incluir_global: bool) -> dict:
    """Devuelve {"global": [tracks] | None, "generos": {slug: {"nombre":..,
    "tracks": [...]}}}. `generos_filtro` es una lista de slugs (ej. ["techno",
    "tech-house"]); None = todos los géneros descubiertos."""
    from playwright.async_api import async_playwright

    resultado = {"global": None, "generos": {}}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = await context.new_page()

        if incluir_global:
            log.info("Beatport: scrapeando Top 100 global...")
            raw = await _scrape_pagina(page, BEATPORT_GLOBAL_TOP100)
            if raw:
                resultado["global"] = _parsear_tracks(raw)

        if incluir_global:
            await asyncio.sleep(REQUEST_DELAY)
        todos_generos = await _descubrir_generos(page)
        if not todos_generos:
            log.warning("Descubrimiento de géneros devolvió vacío, reintentando una vez...")
            await asyncio.sleep(REQUEST_DELAY)
            todos_generos = await _descubrir_generos(page)
        if generos_filtro:
            filtro = set(generos_filtro)
            todos_generos = [g for g in todos_generos if g["slug"] in filtro]

        for genero in todos_generos:
            await asyncio.sleep(REQUEST_DELAY)
            log.info(f"Beatport: scrapeando [{genero['nombre']}]...")
            raw = await _scrape_pagina(page, genero["url"])
            if not raw:
                log.warning(f"  Sin resultados para [{genero['nombre']}], salteo")
                continue
            resultado["generos"][genero["slug"]] = {
                "nombre": genero["nombre"], "tracks": _parsear_tracks(raw),
            }

        await browser.close()
    return resultado


def ejecutar(generos_filtro: list[str] | None = None, incluir_global: bool = True) -> dict:
    """Wrapper sincrónico para llamar desde `cli.py`. Requiere
    `pip install playwright` + `playwright install chromium`."""
    return asyncio.run(_ejecutar_async(generos_filtro, incluir_global))


async def _listar_generos_async() -> list[dict]:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = await context.new_page()
        generos = await _descubrir_generos(page)
        await browser.close()
        return generos


def listar_generos_disponibles() -> list[dict]:
    """Lista los géneros/sub-géneros de Beatport disponibles para scrapear
    (slug + nombre), sin bajar ningún Top 100 todavía."""
    return asyncio.run(_listar_generos_async())


# ---------------------------------------------------------------------------
# Mapeo de género de Beatport -> árbol propio (config.GENRE_TREE), para poder
# subir automáticamente lo scrapeado a la Biblioteca Confiable.
# ---------------------------------------------------------------------------

# Slugs donde el nombre del slug de Beatport no calza 1:1 con el id usado en
# genre_profiles.py / el JSON de perfiles (ver MAPEO_A_ARBOL).
_ALIAS_SLUG = {
    "drum-bass": "drum_and_bass",
    "trap-future-bass": "trap_wave",
}

_nombre_a_mapeo_cache: dict | None = None


def _nombre_a_mapeo() -> dict:
    """nombre_beatport (en minúsculas) -> (genero, subgenero), construido a
    partir de genre_profiles.py. Sirve para mapear el género de UN track
    (ej. dentro del chart global, donde cada track trae su propio género)."""
    global _nombre_a_mapeo_cache
    if _nombre_a_mapeo_cache is None:
        import genre_profiles
        _nombre_a_mapeo_cache = {}
        for perfil in genre_profiles._cargar_perfiles():
            mapeo = genre_profiles.MAPEO_A_ARBOL.get(perfil["id"])
            if mapeo:
                _nombre_a_mapeo_cache[perfil["nombre_beatport"].lower()] = mapeo
    return _nombre_a_mapeo_cache


def mapear_genero_por_slug(slug: str) -> tuple[str | None, str | None]:
    """Mapea el slug de un chart (ej. 'tech-house') al árbol propio.
    Devuelve (None, None) si no es un género electrónico reconocido."""
    import genre_profiles
    id_perfil = _ALIAS_SLUG.get(slug, slug.replace("-", "_"))
    return genre_profiles.MAPEO_A_ARBOL.get(id_perfil) or (None, None)


def mapear_genero_por_nombre(nombre: str | None) -> tuple[str | None, str | None]:
    """Mapea el nombre de género de UN track (campo `genero_pista`) al árbol
    propio. Útil para el chart global, donde cada track trae su género."""
    if not nombre:
        return (None, None)
    return _nombre_a_mapeo().get(nombre.strip().lower(), (None, None))


def key_a_camelot(key_beatport: str | None) -> str:
    """Convierte el formato de Beatport ('A Minor', 'G# Major') a Camelot,
    reusando el conversor de getsongbpm.py (que espera 'Am' / 'G#')."""
    if not key_beatport:
        return ""
    from getsongbpm import key_a_camelot as _conv
    s = key_beatport.strip()
    menor = s.lower().endswith("minor")
    nota = s.split()[0] if s else ""
    if not nota:
        return ""
    return _conv(nota + ("m" if menor else ""))
