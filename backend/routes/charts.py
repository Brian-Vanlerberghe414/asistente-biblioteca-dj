"""Charts de Beatport guardados — mismas queries que
`asistente_dj/charts_confiable.py`. Esta tabla la escribe el scraper
automático (credencial propia, no un usuario final); los clientes solo
necesitan leerla."""
from __future__ import annotations

import asyncio
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from supabase._async.client import AsyncClient

from supabase_client import cliente_para_usuario
from youtube_preview import buscar_candidatos

router = APIRouter(prefix="/charts")

_TABLA = "charts_tracks"
_TABLA_UNIF = "genero_unificaciones"

# Cache en memoria del proceso: {"slug:beatport_id": [candidatos...]}. Se
# pierde en cada redeploy/reinicio (aceptable para V1 — yt-dlp solo se
# vuelve a llamar la primera vez que se pide un track en ese proceso, no en
# cada request del modo radio de Charts).
_cache_candidatos: dict[str, list[dict]] = {}


def _slug(s: str) -> str:
    """Misma normalización que `asistente_dj/unificaciones.py` (fuente única
    del mapeo, pero ese módulo vive en el repo de escritorio: acá se
    reimplementa solo la función de slug para poder cruzar `valor` de
    `genero_unificaciones` contra el `genero_slug` de Beatport)."""
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    out = "".join(c if c.isalnum() else "-" for c in s)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


@router.get("/generos")
async def generos_disponibles(cliente: AsyncClient = Depends(cliente_para_usuario)):
    resp = await cliente.table(_TABLA).select("genero_slug, genero_nombre, fecha_scrape").execute()
    agregados: dict[str, dict] = {}
    for r in resp.data or []:
        slug = r["genero_slug"]
        agg = agregados.setdefault(
            slug, {"genero_slug": slug, "nombre": r.get("genero_nombre") or slug, "ultima": None}
        )
        if r.get("genero_nombre"):
            agg["nombre"] = r["genero_nombre"]
        if r.get("fecha_scrape") and (agg["ultima"] is None or r["fecha_scrape"] > agg["ultima"]):
            agg["ultima"] = r["fecha_scrape"]

    unif_resp = await (
        cliente.table(_TABLA_UNIF).select("umbrella, valor").eq("activo", True).execute()
    )
    slug_a_umbrella = {_slug(u["valor"]): u["umbrella"] for u in (unif_resp.data or [])}
    for slug, agg in agregados.items():
        agg["umbrella"] = slug_a_umbrella.get(slug)
    return list(agregados.values())


@router.get("/{slug}")
async def obtener_chart(slug: str, top: int = 100,
                        cliente: AsyncClient = Depends(cliente_para_usuario)):
    resp = await (
        cliente.table(_TABLA).select("*")
        .eq("genero_slug", slug).order("posicion").limit(top).execute()
    )
    return resp.data


@router.get("/{slug}/preview/{posicion}")
async def candidatos_youtube(slug: str, posicion: int,
                             cliente: AsyncClient = Depends(cliente_para_usuario)):
    """Candidatos de YouTube para el track en `posicion` del chart `slug`
    (reusa `youtube_preview.buscar_candidatos`, portado del escritorio). El
    teléfono no puede correr yt-dlp — esto se resuelve acá.

    yt-dlp bloquea, así que corre en threadpool (`asyncio.to_thread`) para
    no trabar el event loop de FastAPI mientras busca. Cacheado en memoria
    por `beatport_id` (no por posición: la posición cambia de scrape a
    scrape, el track no)."""
    resp = await (
        cliente.table(_TABLA).select("beatport_id, nombre, mix_name, artistas")
        .eq("genero_slug", slug).eq("posicion", posicion).limit(1).execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Track no encontrado en ese chart/posición")
    track = resp.data[0]
    clave = f"{slug}:{track['beatport_id']}"
    if clave in _cache_candidatos:
        return _cache_candidatos[clave]

    candidatos = await asyncio.to_thread(
        buscar_candidatos, track.get("artistas") or [], track.get("nombre") or "", track.get("mix_name"),
    )
    resultado = [
        {"video_id": c.video_id, "titulo": c.titulo, "duracion_seg": c.duracion_seg,
         "es_extended": c.es_extended}
        for c in candidatos
    ]
    _cache_candidatos[clave] = resultado
    return resultado


@router.get("/{slug}/novedades")
async def obtener_novedades(slug: str,
                            cliente: AsyncClient = Depends(cliente_para_usuario)):
    ultima_resp = await (
        cliente.table(_TABLA).select("fecha_scrape")
        .eq("genero_slug", slug).order("fecha_scrape", desc=True).limit(1).execute()
    )
    if not ultima_resp.data:
        return []
    ultima = ultima_resp.data[0]["fecha_scrape"]
    resp = await (
        cliente.table(_TABLA).select("*")
        .eq("genero_slug", slug).eq("fecha_scrape", ultima).eq("primera_vez", ultima)
        .order("posicion").execute()
    )
    return resp.data
