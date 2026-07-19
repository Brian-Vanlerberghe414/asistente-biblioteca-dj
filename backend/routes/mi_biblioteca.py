"""Sincronización de la biblioteca PERSONAL de cada DJ (género/subgénero
como él la organizó, y sus playlists) — base para que, más adelante,
Android/web/iOS puedan editar y que el cambio se vea en todos lados.

Distinto de `biblioteca.py` (conocimiento compartido entre DJs) y de
`audio.py` (solo los archivos subidos): esto es 100% privado por usuario,
ni la lectura es abierta.

Resolución de conflictos: "gana el cambio más reciente" — se aplica del
lado del servidor, comparando `actualizado_en`, para no confiar en que el
cliente nunca mande algo viejo por error."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase._async.client import AsyncClient

from auth import UsuarioActual, obtener_usuario_actual
from supabase_client import cliente_para_usuario

router = APIRouter(prefix="/mi-biblioteca")

_TABLA = "mi_biblioteca"
_TABLA_PLAYLISTS = "mis_playlists"


def _norm(texto: str) -> str:
    if not texto:
        return ""
    s = texto.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_dt(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


class TrackSync(BaseModel):
    artista: str
    titulo: str
    sello: Optional[str] = None
    anio: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    camelot: Optional[str] = None
    duracion_seg: Optional[float] = None
    genero: Optional[str] = None
    subgenero: Optional[str] = None
    energia: Optional[float] = None
    r2_key: Optional[str] = None
    actualizado_en: str


@router.post("/sync")
async def sincronizar(tracks: list[TrackSync],
                      usuario: UsuarioActual = Depends(obtener_usuario_actual),
                      cliente: AsyncClient = Depends(cliente_para_usuario)):
    resultados = []
    for t in tracks:
        art_norm, tit_norm = _norm(t.artista), _norm(t.titulo)
        existente = await (
            cliente.table(_TABLA).select("actualizado_en")
            .eq("artista_norm", art_norm).eq("titulo_norm", tit_norm)
            .limit(1).execute()
        )
        if existente.data and _parse_dt(existente.data[0]["actualizado_en"]) >= _parse_dt(t.actualizado_en):
            resultados.append({"artista": t.artista, "titulo": t.titulo, "aplicado": False})
            continue
        data = {
            "usuario_id": usuario.id, "artista_norm": art_norm, "titulo_norm": tit_norm,
            "artista": t.artista, "titulo": t.titulo, "sello": t.sello, "anio": t.anio,
            "bpm": t.bpm, "key": t.key, "camelot": t.camelot, "duracion_seg": t.duracion_seg,
            "genero": t.genero, "subgenero": t.subgenero, "energia": t.energia,
            "r2_key": t.r2_key, "actualizado_en": t.actualizado_en,
        }
        await cliente.table(_TABLA).upsert(data, on_conflict="usuario_id,artista_norm,titulo_norm").execute()
        resultados.append({"artista": t.artista, "titulo": t.titulo, "aplicado": True})
    return {"resultados": resultados}


@router.get("")
async def mi_biblioteca(since: Optional[str] = None, solo_ids: bool = False,
                        after_id: Optional[int] = None, limit: Optional[int] = None,
                        cliente: AsyncClient = Depends(cliente_para_usuario)):
    """`since` (ISO 8601, opcional): si se manda, solo devuelve filas con
    `actualizado_en` posterior — permite sincronizaciones incrementales en
    vez de bajar toda la biblioteca personal en cada corrida.

    `solo_ids`: para cuando lo único que hace falta es traducir ids de
    playlist a artista/título (push/pull de playlists) — evita bajar todas
    las columnas (bpm, key, género, etc.) cuando no hacen falta.

    `after_id` + `limit` (ambos opcionales, keyset): para clientes con miles
    de tracks (ej. la app) que quieren traer la biblioteca de a páginas en
    vez de un array gigante. Orden estable por `id`; para la página
    siguiente, `after_id` = el `id` de la última fila recibida. Sin estos
    parámetros el comportamiento es el de siempre (todo de una)."""
    campos = "id, artista_norm, titulo_norm" if solo_ids else "*"
    q = cliente.table(_TABLA).select(campos).order("id")
    if since:
        q = q.gt("actualizado_en", since)
    if after_id is not None:
        q = q.gt("id", after_id)
    if limit is not None:
        q = q.limit(limit)
    resp = await q.execute()
    return resp.data


class PlaylistSync(BaseModel):
    nombre: str
    ids: list[int]
    actualizado_en: str


@router.post("/playlists")
async def sincronizar_playlist(playlist: PlaylistSync,
                               usuario: UsuarioActual = Depends(obtener_usuario_actual),
                               cliente: AsyncClient = Depends(cliente_para_usuario)):
    existente = await (
        cliente.table(_TABLA_PLAYLISTS).select("actualizado_en")
        .eq("nombre", playlist.nombre).limit(1).execute()
    )
    if existente.data and _parse_dt(existente.data[0]["actualizado_en"]) >= _parse_dt(playlist.actualizado_en):
        return {"aplicado": False}
    data = {
        "usuario_id": usuario.id, "nombre": playlist.nombre,
        "reglas": {"ids": playlist.ids}, "actualizado_en": playlist.actualizado_en,
    }
    await cliente.table(_TABLA_PLAYLISTS).upsert(data, on_conflict="usuario_id,nombre").execute()
    return {"aplicado": True}


@router.get("/playlists")
async def mis_playlists(since: Optional[str] = None,
                        cliente: AsyncClient = Depends(cliente_para_usuario)):
    """Mismo `since` incremental que `GET /mi-biblioteca`."""
    q = cliente.table(_TABLA_PLAYLISTS).select("*")
    if since:
        q = q.gt("actualizado_en", since)
    resp = await q.execute()
    return resp.data


class PlaylistRename(BaseModel):
    nombre_nuevo: str


@router.patch("/playlists/{nombre}")
async def renombrar_playlist(nombre: str, cambio: PlaylistRename,
                             cliente: AsyncClient = Depends(cliente_para_usuario)):
    """Renombra sin duplicar (a diferencia de subir de nuevo con `POST
    /playlists`, que haría upsert por nombre nuevo y dejaría la vieja
    huérfana). RLS (`cliente_para_usuario`) ya garantiza que solo se pueda
    tocar una playlist propia."""
    resp = await (
        cliente.table(_TABLA_PLAYLISTS)
        .update({"nombre": cambio.nombre_nuevo, "actualizado_en": datetime.now(timezone.utc).isoformat()})
        .eq("nombre", nombre).execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Playlist no encontrada")
    return resp.data[0]


@router.delete("/playlists/{nombre}")
async def borrar_playlist(nombre: str, cliente: AsyncClient = Depends(cliente_para_usuario)):
    resp = await cliente.table(_TABLA_PLAYLISTS).delete().eq("nombre", nombre).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Playlist no encontrada")
    return {"borrado": True}
