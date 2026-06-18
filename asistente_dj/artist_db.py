"""Base de datos de artistas: géneros por artista, lookup online.

Flujo de datos:
- split_artistas()       → parsea "ARTBAT, Anyma" → ["ARTBAT", "Anyma"]
- buscar()               → busca en tabla `artistas` por nombre normalizado
- guardar()              → upsert en tabla `artistas`
- generos_permitidos()   → unión de géneros de todos los artistas de un string
- lookup_lastfm()        → Last.fm artist.getTopTags → géneros reconocidos
- lookup_beatport()      → scraping Beatport → géneros reconocidos
- registrar_desde_biblioteca() → registra artistas de `tracks` sin hacer red
- poblar_desde_biblioteca()    → registra + enriquece online
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime

_SEP_RE = re.compile(
    r"\s*(?:,\s*|\s+feat\.?\s+|\s+ft\.?\s+|\s+featuring\s+|\s+with\s+|\s+vs\.?\s+|\s+x\s+|&)\s*",
    re.IGNORECASE,
)


def split_artistas(artista_str: str) -> list[str]:
    """'ARTBAT, Anyma feat. CamelPhat' → ['ARTBAT', 'Anyma', 'CamelPhat']"""
    if not artista_str:
        return []
    partes = _SEP_RE.split(artista_str.strip())
    return [p.strip() for p in partes if p.strip()]


def _norm(nombre: str) -> str:
    s = nombre.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ─────────────────────────────────────────────────── BD local ────────────────

def buscar(conn, nombre: str) -> dict | None:
    nn = _norm(nombre)
    row = conn.execute(
        "SELECT * FROM artistas WHERE nombre_norm = ?", (nn,)
    ).fetchone()
    return dict(row) if row else None


def guardar(conn, nombre: str, generos: list[tuple], fuente: str) -> None:
    """Upsert de artista. generos = [(genero, subgenero), ...]"""
    nn = _norm(nombre)
    generos_json = json.dumps([[g, s] for g, s in generos], ensure_ascii=False)
    ahora = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO artistas (nombre, nombre_norm, generos, fuente, fecha_actualizacion) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(nombre) DO UPDATE SET "
        "generos=excluded.generos, fuente=excluded.fuente, "
        "fecha_actualizacion=excluded.fecha_actualizacion",
        (nombre, nn, generos_json, fuente, ahora),
    )


def generos_permitidos(conn, artista_str: str) -> set[tuple] | None:
    """
    Retorna el conjunto de (genero, subgenero) permitidos.
    - None si ningún artista del string está en la BD (sin restricción).
    - Set vacío si están pero sin géneros (tampoco restringe).
    - Set con pares si hay datos → filtra clasificaciones imposibles.
    """
    nombres = split_artistas(artista_str)
    permitidos: set[tuple] | None = None
    for nombre in nombres:
        row = buscar(conn, nombre)
        if row is None:
            continue
        generos_raw = row.get("generos") or "[]"
        try:
            pares = json.loads(generos_raw)
        except json.JSONDecodeError:
            continue
        if not pares:
            continue
        s = {(p[0], p[1] if len(p) > 1 else None) for p in pares}
        if permitidos is None:
            permitidos = s
        else:
            permitidos |= s
    return permitidos


# ─────────────────────────────────────────────── lookup online ───────────────

def lookup_lastfm(nombre: str, api_key: str) -> list[tuple]:
    """Last.fm artist.getTopTags → lista de (genero, subgenero) reconocidos."""
    if not api_key:
        return []
    try:
        import requests
        from classifier import classify

        r = requests.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "artist.getTopTags",
                "artist": nombre,
                "api_key": api_key,
                "format": "json",
            },
            timeout=8,
        )
        data = r.json()
        tags = data.get("toptags", {}).get("tag", [])
        resultados: list[tuple] = []
        vistos: set[tuple] = set()
        for tag in tags[:20]:
            tag_name = tag.get("name", "")
            c = classify(tag_name)
            if c.genero and (c.genero, c.subgenero) not in vistos:
                resultados.append((c.genero, c.subgenero))
                vistos.add((c.genero, c.subgenero))
        return resultados
    except Exception:
        return []


def lookup_beatport(nombre: str) -> list[tuple]:
    """Scraping Beatport: busca artista y extrae géneros de su página."""
    try:
        import requests
        from bs4 import BeautifulSoup
        from classifier import classify

        headers = {"User-Agent": "Mozilla/5.0 (compatible; AsistenteDJ/1.0)"}
        search_url = (
            "https://www.beatport.com/search/artists?q="
            + requests.utils.quote(nombre)
        )
        r = requests.get(search_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")

        artist_link = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/artist/" in href and not href.startswith("http"):
                artist_link = "https://www.beatport.com" + href.split("?")[0]
                break
        if not artist_link:
            return []

        time.sleep(2)
        r2 = requests.get(artist_link, headers=headers, timeout=10)
        if r2.status_code != 200:
            return []
        soup2 = BeautifulSoup(r2.text, "html.parser")

        resultados: list[tuple] = []
        vistos: set[tuple] = set()
        for elem in soup2.find_all(["span", "a"]):
            txt = elem.get_text(strip=True)
            if not txt or len(txt) > 50:
                continue
            c = classify(txt)
            if c.genero and (c.genero, c.subgenero) not in vistos:
                resultados.append((c.genero, c.subgenero))
                vistos.add((c.genero, c.subgenero))
        return resultados
    except Exception:
        return []


# ──────────────────────────────────────────── población desde biblioteca ─────

def registrar_desde_biblioteca(conn) -> int:
    """Agrega todos los artistas únicos de `tracks` a `artistas` (sin red).
    No sobreescribe artistas que ya tengan géneros. Devuelve cantidad añadida."""
    rows = conn.execute(
        "SELECT DISTINCT artista FROM tracks WHERE artista IS NOT NULL AND artista != ''"
    ).fetchall()
    nuevos = 0
    for r in rows:
        for nombre in split_artistas(r["artista"]):
            if not nombre:
                continue
            existente = buscar(conn, nombre)
            if existente is None:
                guardar(conn, nombre, [], "ninguna")
                nuevos += 1
    conn.commit()
    return nuevos


def poblar_desde_biblioteca(
    conn, api_key: str = "", progreso_cb=None, limite: int = 200
) -> dict:
    """Itera artistas de la biblioteca y los enriquece online.

    Procesa hasta `limite` artistas por corrida (los que aún no tienen géneros
    o fueron actualizados hace más de 30 días). Llama progreso_cb(msg) si se da.
    """
    registrar_desde_biblioteca(conn)

    # Priorizar artistas sin géneros aún
    rows = conn.execute(
        "SELECT nombre, generos, fecha_actualizacion FROM artistas ORDER BY nombre COLLATE NOCASE"
    ).fetchall()

    pendientes = []
    for r in rows:
        generos_raw = r["generos"] or "[]"
        try:
            lista = json.loads(generos_raw)
        except json.JSONDecodeError:
            lista = []
        if lista:
            # ya tiene géneros: saltar si fue actualizado en los últimos 30 días
            fecha_s = r["fecha_actualizacion"] or ""
            try:
                fecha = datetime.fromisoformat(fecha_s)
                if (datetime.now() - fecha).days < 30:
                    continue
            except ValueError:
                pass
        pendientes.append(r["nombre"])

    pendientes = pendientes[:limite]
    resumen = {"procesados": 0, "nuevos": 0, "actualizados": 0, "sin_info": 0, "total_pendientes": len(pendientes)}

    for i, nombre in enumerate(pendientes):
        if progreso_cb:
            progreso_cb(f"[{i+1}/{len(pendientes)}] {nombre}…")

        existente = buscar(conn, nombre)
        ya_tenia = bool(
            existente and existente.get("generos")
            and json.loads(existente.get("generos") or "[]")
        )

        generos = lookup_lastfm(nombre, api_key)
        if generos:
            time.sleep(0.3)
        else:
            time.sleep(0.5)
            generos = lookup_beatport(nombre)
            if generos:
                time.sleep(1)

        resumen["procesados"] += 1
        if generos:
            fuente = "lastfm" if (api_key and generos) else "beatport"
            guardar(conn, nombre, generos, fuente)
            conn.commit()
            if ya_tenia:
                resumen["actualizados"] += 1
            else:
                resumen["nuevos"] += 1
        else:
            # Guardar fecha de intento aunque no haya géneros (para no reintentar pronto)
            guardar(conn, nombre, [], "ninguna")
            conn.commit()
            resumen["sin_info"] += 1

    return resumen


def todos(conn) -> list[dict]:
    """Lista completa de artistas para mostrar en la GUI."""
    rows = conn.execute(
        "SELECT nombre, generos, fuente, fecha_actualizacion "
        "FROM artistas ORDER BY nombre COLLATE NOCASE"
    ).fetchall()
    return [dict(r) for r in rows]
