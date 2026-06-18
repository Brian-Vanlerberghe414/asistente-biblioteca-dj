"""Cliente de la tabla `charts_tracks` en Supabase — charts de Beatport en la
nube (Módulo 2), espejo de la tabla local homónima en db.py.

Existe para que el scrape pueda correr en un agente en la nube (sin acceso al
SQLite local de la PC del DJ) y que tanto ese agente como la app local lean
y escriban del mismo lugar. Mismo enfoque a prueba de fallos que
biblioteca_confiable.py: si Supabase no está configurado o falla la red, las
funciones devuelven valores vacíos sin romper nada — quien llama decide si
cae al SQLite local.

Credenciales: las mismas de la Biblioteca Confiable
  python cli.py config --supabase-url URL --supabase-key KEY
"""
from __future__ import annotations

from typing import Optional

import settings

try:
    from supabase import create_client, Client as _Client
    _SUPABASE_DISPONIBLE = True
except ImportError:
    _SUPABASE_DISPONIBLE = False

_TABLA = "charts_tracks"
_cliente: Optional["_Client"] = None


def _get_cliente() -> Optional["_Client"]:
    global _cliente
    if not _SUPABASE_DISPONIBLE:
        return None
    if _cliente is not None:
        return _cliente
    cfg = settings.cargar()
    url = cfg.get("supabase_url", "").strip()
    key = cfg.get("supabase_key", "").strip()
    if not url or not key:
        return None
    try:
        _cliente = create_client(url, key)
    except Exception as e:
        print(f"  [charts] No se pudo conectar a Supabase: {e}")
        _cliente = None
    return _cliente


def esta_configurado() -> bool:
    cfg = settings.cargar()
    return bool(cfg.get("supabase_url") and cfg.get("supabase_key"))


def upsert_tracks(tracks: list[dict], slug: str, nombre_genero: Optional[str], fecha: str) -> int:
    """Sube/actualiza los tracks de un chart (slug de género o 'global').

    `tracks` viene con las mismas claves que devuelve `charts_beatport`
    (beatport_id, posicion, nombre, mix_name, artistas, remixers, release,
    sello, bpm, key, genero_pista, duracion_ms, publish_date, image_url).
    Devuelve la cantidad de tracks nuevos (no vistos antes en este género).
    Nunca lanza excepción: si Supabase no está configurado, devuelve 0.
    """
    cliente = _get_cliente()
    if cliente is None or not tracks:
        return 0

    ids = [t["beatport_id"] for t in tracks]
    try:
        existentes = (
            cliente.table(_TABLA)
            .select("beatport_id, primera_vez")
            .eq("genero_slug", slug)
            .in_("beatport_id", ids)
            .execute()
        )
        primera_vez_por_id = {r["beatport_id"]: r["primera_vez"] for r in (existentes.data or [])}
    except Exception as e:
        print(f"  [charts] Error consultando Supabase: {e}")
        return 0

    filas = []
    nuevos = 0
    for t in tracks:
        es_nuevo = t["beatport_id"] not in primera_vez_por_id
        if es_nuevo:
            nuevos += 1
        filas.append({
            "beatport_id": t["beatport_id"], "genero_slug": slug,
            "genero_nombre": nombre_genero, "posicion": t["posicion"],
            "nombre": t["nombre"], "mix_name": t["mix_name"],
            "artistas": t["artistas"], "remixers": t["remixers"],
            "release": t["release"], "sello": t["sello"], "bpm": t["bpm"],
            "key": t["key"], "genero_pista": t.get("genero_pista"),
            "duracion_ms": t["duracion_ms"], "publish_date": t.get("publish_date"),
            "image_url": t.get("image_url"),
            "primera_vez": primera_vez_por_id.get(t["beatport_id"], fecha),
            "fecha_scrape": fecha,
        })

    try:
        cliente.table(_TABLA).upsert(filas, on_conflict="beatport_id,genero_slug").execute()
    except Exception as e:
        print(f"  [charts] Error guardando en Supabase: {e}")
        return 0
    return nuevos


def generos_disponibles() -> list[dict]:
    """Lista los géneros que ya tienen datos guardados (slug, nombre, último
    scrape, cantidad de tracks) — para poblar el combo de la GUI."""
    cliente = _get_cliente()
    if cliente is None:
        return []
    try:
        resp = cliente.table(_TABLA).select("genero_slug, genero_nombre, fecha_scrape").execute()
        rows = resp.data or []
    except Exception:
        return []
    agregados: dict[str, dict] = {}
    for r in rows:
        slug = r["genero_slug"]
        agg = agregados.setdefault(slug, {"genero_slug": slug, "nombre": r.get("genero_nombre") or slug, "ultima": None, "n": 0})
        agg["n"] += 1
        if r.get("genero_nombre"):
            agg["nombre"] = r["genero_nombre"]
        if r.get("fecha_scrape") and (agg["ultima"] is None or r["fecha_scrape"] > agg["ultima"]):
            agg["ultima"] = r["fecha_scrape"]
    return list(agregados.values())


def obtener_chart(slug: str, top: int = 100) -> list[dict]:
    """Tracks de un género/global, ordenados por posición."""
    cliente = _get_cliente()
    if cliente is None:
        return []
    try:
        resp = (
            cliente.table(_TABLA).select("*")
            .eq("genero_slug", slug).order("posicion").limit(top).execute()
        )
        return resp.data or []
    except Exception:
        return []


def ultima_fecha(slug: str) -> Optional[str]:
    """Fecha del scrape más reciente guardado para ese género, o None si no
    hay nada guardado todavía."""
    cliente = _get_cliente()
    if cliente is None:
        return None
    try:
        resp = (
            cliente.table(_TABLA).select("fecha_scrape")
            .eq("genero_slug", slug).order("fecha_scrape", desc=True).limit(1).execute()
        )
        return resp.data[0]["fecha_scrape"] if resp.data else None
    except Exception:
        return None


def obtener_novedades(slug: str) -> list[dict]:
    """Tracks que aparecieron por primera vez en el último scrape de ese género."""
    cliente = _get_cliente()
    if cliente is None:
        return []
    ultima = ultima_fecha(slug)
    if not ultima:
        return []
    try:
        resp = (
            cliente.table(_TABLA).select("*")
            .eq("genero_slug", slug).eq("fecha_scrape", ultima).eq("primera_vez", ultima)
            .order("posicion").execute()
        )
        return resp.data or []
    except Exception:
        return []
