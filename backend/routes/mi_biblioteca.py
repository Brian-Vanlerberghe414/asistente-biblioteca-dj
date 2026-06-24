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
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

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
def sincronizar(tracks: list[TrackSync],
                 usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    resultados = []
    for t in tracks:
        art_norm, tit_norm = _norm(t.artista), _norm(t.titulo)
        existente = (
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
        cliente.table(_TABLA).upsert(data, on_conflict="usuario_id,artista_norm,titulo_norm").execute()
        resultados.append({"artista": t.artista, "titulo": t.titulo, "aplicado": True})
    return {"resultados": resultados}


@router.get("")
def mi_biblioteca(since: Optional[str] = None, solo_ids: bool = False,
                   usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    """`since` (ISO 8601, opcional): si se manda, solo devuelve filas con
    `actualizado_en` posterior — permite sincronizaciones incrementales en
    vez de bajar toda la biblioteca personal en cada corrida.

    `solo_ids`: para cuando lo único que hace falta es traducir ids de
    playlist a artista/título (push/pull de playlists) — evita bajar todas
    las columnas (bpm, key, género, etc.) cuando no hacen falta."""
    cliente = cliente_para_usuario(usuario.jwt)
    campos = "id, artista_norm, titulo_norm" if solo_ids else "*"
    q = cliente.table(_TABLA).select(campos)
    if since:
        q = q.gt("actualizado_en", since)
    resp = q.execute()
    return resp.data


class PlaylistSync(BaseModel):
    nombre: str
    ids: list[int]
    actualizado_en: str


@router.post("/playlists")
def sincronizar_playlist(playlist: PlaylistSync,
                          usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    existente = (
        cliente.table(_TABLA_PLAYLISTS).select("actualizado_en")
        .eq("nombre", playlist.nombre).limit(1).execute()
    )
    if existente.data and _parse_dt(existente.data[0]["actualizado_en"]) >= _parse_dt(playlist.actualizado_en):
        return {"aplicado": False}
    data = {
        "usuario_id": usuario.id, "nombre": playlist.nombre,
        "reglas": {"ids": playlist.ids}, "actualizado_en": playlist.actualizado_en,
    }
    cliente.table(_TABLA_PLAYLISTS).upsert(data, on_conflict="usuario_id,nombre").execute()
    return {"aplicado": True}


@router.get("/playlists")
def mis_playlists(since: Optional[str] = None,
                   usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    """Mismo `since` incremental que `GET /mi-biblioteca`."""
    cliente = cliente_para_usuario(usuario.jwt)
    q = cliente.table(_TABLA_PLAYLISTS).select("*")
    if since:
        q = q.gt("actualizado_en", since)
    resp = q.execute()
    return resp.data
