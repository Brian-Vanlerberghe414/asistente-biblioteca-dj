"""Playlists compartidas / colaborativas — función del plan VIP.

Varios DJs colaboran en UNA misma playlist uniéndose con un código. Cada uno
aporta tracks, pero solo viajan los DATOS del track (artista + título +
metadata), nunca el audio: el otro DJ, si tiene ese tema local, lo escucha de su
archivo; si no, por el reproductor de YouTube/Spotify de la app.

Distinto de mi_biblioteca.py (privado por usuario): acá la escritura la hace el
backend con service_role (bypassa RLS) DESPUÉS de validar rol/modo en código —
el cliente nunca decide permisos. Las LECTURAS con RLS (que usa Supabase
Realtime) las cubre supabase_setup_playlists_compartidas.sql; este backend, como
además ya autentica al usuario, valida membresía explícitamente en cada ruta.

Async (A1+A3): el cliente de servicio es un singleton compartido async
(`await cliente_servicio()`), así todas estas rutas reusan sus conexiones HTTP.
Los helpers que consultan la base son `async` y se esperan con `await`.
"""
from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase._async.client import AsyncClient

from auth import UsuarioActual, obtener_usuario_actual
from supabase_client import cliente_servicio

router = APIRouter(prefix="/playlists-compartidas")

_T_PLAYLIST = "playlists_compartidas"
_T_MIEMBROS = "playlists_compartidas_miembros"
_T_TRACKS = "playlists_compartidas_tracks"

# Alfabeto del código de adhesión sin caracteres ambiguos (sin O/0/I/1/L) para
# que sea fácil de dictar/tipear.
_ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_LARGO_CODIGO = 8


# ─────────────────────────────────────────────────────── enganche VIP (stub)
def requiere_shared_playlists(
    usuario: UsuarioActual = Depends(obtener_usuario_actual),
) -> UsuarioActual:
    """Punto único donde se gateará esta función al plan VIP.

    TODO(tiers): cuando exista el sistema de tiers (ver plan
    polymorphic-rolling-wolf.md), reemplazar el cuerpo por el chequeo de
    capability `canSharedPlaylists` (True para vip/oro/diamante, False para
    general) — p. ej. `capabilities.requiere("canSharedPlaylists")`. HOY deja
    pasar a cualquier usuario autenticado a propósito (los tiers se implementan
    al final), pero todas las rutas ya cuelgan de acá para prender el candado en
    un solo lugar."""
    return usuario


def _norm(texto: str) -> str:
    if not texto:
        return ""
    s = texto.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _generar_codigo(svc: AsyncClient) -> str:
    """Código único. Reintenta si (muy improbablemente) choca con uno existente."""
    for _ in range(10):
        codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_LARGO_CODIGO))
        existe = await svc.table(_T_PLAYLIST).select("id").eq("codigo", codigo).limit(1).execute()
        if not existe.data:
            return codigo
    raise HTTPException(status_code=500, detail="No se pudo generar un código único.")


async def _get_playlist(svc: AsyncClient, playlist_id: str) -> dict:
    resp = await svc.table(_T_PLAYLIST).select("*").eq("id", playlist_id).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Playlist compartida no encontrada.")
    return resp.data[0]


async def _get_miembro(svc: AsyncClient, playlist_id: str, usuario_id: str) -> dict | None:
    resp = await (
        svc.table(_T_MIEMBROS).select("*")
        .eq("playlist_id", playlist_id).eq("usuario_id", usuario_id)
        .limit(1).execute()
    )
    return resp.data[0] if resp.data else None


async def _exigir_miembro(svc: AsyncClient, playlist_id: str, usuario_id: str) -> dict:
    miembro = await _get_miembro(svc, playlist_id, usuario_id)
    if not miembro:
        raise HTTPException(status_code=403, detail="No sos miembro de esta playlist.")
    return miembro


def _es_dueno(playlist: dict, usuario_id: str) -> bool:
    return playlist["dueno_id"] == usuario_id


# ───────────────────────────────────────────────────────────── modelos
class CrearPlaylist(BaseModel):
    nombre: str
    modo_colaboracion: str = "dueno_manda"


class Unirse(BaseModel):
    codigo: str


class TrackAporte(BaseModel):
    artista: str
    titulo: str
    sello: str | None = None
    anio: str | None = None
    bpm: float | None = None
    key: str | None = None
    camelot: str | None = None
    duracion_seg: float | None = None
    genero: str | None = None
    subgenero: str | None = None
    cover_url: str | None = None
    mix_name: str | None = None


class Renombrar(BaseModel):
    nombre: str


# ───────────────────────────────────────────────────────────── rutas
@router.post("")
async def crear(datos: CrearPlaylist,
                usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    if datos.modo_colaboracion not in ("dueno_manda", "abierto"):
        raise HTTPException(status_code=400, detail="modo_colaboracion inválido.")
    svc = await cliente_servicio()
    codigo = await _generar_codigo(svc)
    pl = (await svc.table(_T_PLAYLIST).insert({
        "codigo": codigo, "nombre": datos.nombre, "dueno_id": usuario.id,
        "modo_colaboracion": datos.modo_colaboracion,
    }).execute()).data[0]
    await svc.table(_T_MIEMBROS).insert({
        "playlist_id": pl["id"], "usuario_id": usuario.id, "rol": "dueno",
    }).execute()
    return pl


@router.post("/unirse")
async def unirse(datos: Unirse,
                 usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    resp = await svc.table(_T_PLAYLIST).select("*").eq("codigo", datos.codigo.strip().upper()).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Código inválido.")
    pl = resp.data[0]
    if not await _get_miembro(svc, pl["id"], usuario.id):
        await svc.table(_T_MIEMBROS).insert({
            "playlist_id": pl["id"], "usuario_id": usuario.id, "rol": "miembro",
        }).execute()
    return pl


@router.get("")
async def listar(usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    """Las playlists compartidas donde el usuario es miembro (con su rol)."""
    svc = await cliente_servicio()
    mis = await svc.table(_T_MIEMBROS).select("playlist_id, rol").eq("usuario_id", usuario.id).execute()
    if not mis.data:
        return []
    por_id = {m["playlist_id"]: m["rol"] for m in mis.data}
    pls = await svc.table(_T_PLAYLIST).select("*").in_("id", list(por_id.keys())).execute()
    return [{**pl, "mi_rol": por_id.get(pl["id"])} for pl in pls.data]


@router.get("/{playlist_id}")
async def detalle(playlist_id: str,
                  usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    pl = await _get_playlist(svc, playlist_id)
    miembro = await _exigir_miembro(svc, playlist_id, usuario.id)
    tracks = await svc.table(_T_TRACKS).select("*").eq("playlist_id", playlist_id).order("agregado_en").execute()
    miembros = await svc.table(_T_MIEMBROS).select("*").eq("playlist_id", playlist_id).execute()
    return {**pl, "mi_rol": miembro["rol"], "tracks": tracks.data, "miembros": miembros.data}


@router.post("/{playlist_id}/tracks")
async def aportar(playlist_id: str, tracks: list[TrackAporte],
                  usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    """Aporta uno o varios tracks. Cualquier miembro puede aportar (en ambos
    modos). Upsert por (playlist_id, artista_norm, titulo_norm) — si el tema ya
    está, no se duplica."""
    svc = await cliente_servicio()
    await _get_playlist(svc, playlist_id)
    await _exigir_miembro(svc, playlist_id, usuario.id)
    filas = []
    for t in tracks:
        art_norm, tit_norm = _norm(t.artista), _norm(t.titulo)
        if not art_norm and not tit_norm:
            continue
        filas.append({
            "playlist_id": playlist_id, "aportado_por": usuario.id,
            "artista_norm": art_norm, "titulo_norm": tit_norm,
            "artista": t.artista, "titulo": t.titulo, "sello": t.sello, "anio": t.anio,
            "bpm": t.bpm, "key": t.key, "camelot": t.camelot,
            "duracion_seg": t.duracion_seg, "genero": t.genero, "subgenero": t.subgenero,
            "cover_url": t.cover_url, "mix_name": t.mix_name,
        })
    if not filas:
        return {"agregados": 0}
    await svc.table(_T_TRACKS).upsert(filas, on_conflict="playlist_id,artista_norm,titulo_norm").execute()
    await _tocar(svc, playlist_id)
    return {"agregados": len(filas)}


@router.delete("/{playlist_id}/tracks/{track_id}")
async def quitar_track(playlist_id: str, track_id: str,
                       usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    pl = await _get_playlist(svc, playlist_id)
    await _exigir_miembro(svc, playlist_id, usuario.id)
    resp = await svc.table(_T_TRACKS).select("aportado_por").eq("id", track_id).eq("playlist_id", playlist_id).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Track no encontrado en la playlist.")
    aportado_por = resp.data[0]["aportado_por"]
    # Dueño: siempre. Modo abierto: cualquier miembro. dueno_manda: solo lo suyo.
    permitido = (
        _es_dueno(pl, usuario.id)
        or pl["modo_colaboracion"] == "abierto"
        or aportado_por == usuario.id
    )
    if not permitido:
        raise HTTPException(status_code=403, detail="No podés quitar un track que aportó otro DJ.")
    await svc.table(_T_TRACKS).delete().eq("id", track_id).execute()
    await _tocar(svc, playlist_id)
    return {"ok": True}


@router.patch("/{playlist_id}")
async def renombrar(playlist_id: str, datos: Renombrar,
                    usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    pl = await _get_playlist(svc, playlist_id)
    await _exigir_miembro(svc, playlist_id, usuario.id)
    if not (_es_dueno(pl, usuario.id) or pl["modo_colaboracion"] == "abierto"):
        raise HTTPException(status_code=403, detail="Solo el dueño puede renombrar esta playlist.")
    await svc.table(_T_PLAYLIST).update({
        "nombre": datos.nombre, "actualizado_en": _ahora_iso(),
    }).eq("id", playlist_id).execute()
    return {"ok": True}


@router.post("/{playlist_id}/salir")
async def salir(playlist_id: str,
                usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    pl = await _get_playlist(svc, playlist_id)
    await _exigir_miembro(svc, playlist_id, usuario.id)
    if _es_dueno(pl, usuario.id):
        raise HTTPException(status_code=400, detail="El dueño no puede salir; borrá la playlist.")
    await svc.table(_T_MIEMBROS).delete().eq("playlist_id", playlist_id).eq("usuario_id", usuario.id).execute()
    return {"ok": True}


@router.delete("/{playlist_id}")
async def borrar(playlist_id: str,
                 usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    pl = await _get_playlist(svc, playlist_id)
    if not _es_dueno(pl, usuario.id):
        raise HTTPException(status_code=403, detail="Solo el dueño puede borrar la playlist.")
    # ON DELETE CASCADE limpia miembros y tracks.
    await svc.table(_T_PLAYLIST).delete().eq("id", playlist_id).execute()
    return {"ok": True}


@router.delete("/{playlist_id}/miembros/{uid}")
async def expulsar(playlist_id: str, uid: str,
                   usuario: UsuarioActual = Depends(requiere_shared_playlists)):
    svc = await cliente_servicio()
    pl = await _get_playlist(svc, playlist_id)
    if not _es_dueno(pl, usuario.id):
        raise HTTPException(status_code=403, detail="Solo el dueño puede expulsar miembros.")
    if uid == usuario.id:
        raise HTTPException(status_code=400, detail="El dueño no puede expulsarse a sí mismo.")
    await svc.table(_T_MIEMBROS).delete().eq("playlist_id", playlist_id).eq("usuario_id", uid).execute()
    return {"ok": True}


async def _tocar(svc: AsyncClient, playlist_id: str) -> None:
    """Actualiza `actualizado_en` de la playlist tras un cambio de tracks."""
    await svc.table(_T_PLAYLIST).update({"actualizado_en": _ahora_iso()}).eq("id", playlist_id).execute()
