"""Búsqueda genérica de candidatos de YouTube (artista+título sueltos, sin
depender de una posición de chart) — la necesita Playlists (propias y
compartidas, Sesión 7/8): "escuchar un aporte" no tiene slug/posición de
Beatport, a diferencia de Charts (que usa `/charts/{slug}/preview/{posicion}`,
ver `routes/charts.py`)."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends

from auth import UsuarioActual, obtener_usuario_actual
from youtube_preview import buscar_candidatos

router = APIRouter(prefix="/youtube")

# Mismo criterio de cache en memoria por proceso que charts.py.
_cache_candidatos: dict[str, list[dict]] = {}


@router.get("/buscar")
async def buscar(artista: str, titulo: str, mix_name: Optional[str] = None,
                 usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    clave = f"{artista.strip().lower()}::{titulo.strip().lower()}::{(mix_name or '').strip().lower()}"
    if clave in _cache_candidatos:
        return _cache_candidatos[clave]

    candidatos = await asyncio.to_thread(buscar_candidatos, [artista], titulo, mix_name)
    resultado = [
        {"video_id": c.video_id, "titulo": c.titulo, "duracion_seg": c.duracion_seg,
         "es_extended": c.es_extended}
        for c in candidatos
    ]
    _cache_candidatos[clave] = resultado
    return resultado
