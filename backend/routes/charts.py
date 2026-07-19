"""Charts de Beatport guardados — mismas queries que
`asistente_dj/charts_confiable.py`. Esta tabla la escribe el scraper
automático (credencial propia, no un usuario final); los clientes solo
necesitan leerla."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase._async.client import AsyncClient

from supabase_client import cliente_para_usuario

router = APIRouter(prefix="/charts")

_TABLA = "charts_tracks"


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
    return list(agregados.values())


@router.get("/{slug}")
async def obtener_chart(slug: str, top: int = 100,
                        cliente: AsyncClient = Depends(cliente_para_usuario)):
    resp = await (
        cliente.table(_TABLA).select("*")
        .eq("genero_slug", slug).order("posicion").limit(top).execute()
    )
    return resp.data


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
