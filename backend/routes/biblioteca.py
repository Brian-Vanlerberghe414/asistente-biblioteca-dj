"""Biblioteca Confiable — mismas queries que
`asistente_dj/biblioteca_confiable.py`, pero con el cliente de Supabase del
usuario autenticado en cada request (ver `supabase_client.py`), en vez de
una credencial estática local."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import UsuarioActual, obtener_usuario_actual
from supabase_client import cliente_para_usuario

router = APIRouter(prefix="/biblioteca")

_TABLA = "biblioteca_tracks"

_RE_MIX_SUFFIX = re.compile(
    r"\s*[\(\[](original mix|extended mix|club mix|radio mix|"
    r"original|extended|mix|edit|version)[\)\]]\s*$",
    flags=re.I,
)
_RE_FEAT = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s+.+$", flags=re.I)


def _norm(texto: str) -> str:
    if not texto:
        return ""
    s = texto.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = _RE_FEAT.sub("", s)
    s = _RE_MIX_SUFFIX.sub("", s)
    return s.strip()


@router.get("/buscar")
def buscar(artista: str, titulo: str, duracion_seg: float,
           usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    art, tit = _norm(artista), _norm(titulo)
    resp = (
        cliente.table(_TABLA)
        .select("genero, subgenero, bpm, camelot")
        .ilike("artista_norm", art)
        .ilike("titulo_norm", tit)
        .gte("duracion_seg", round(duracion_seg - 2, 2))
        .lte("duracion_seg", round(duracion_seg + 2, 2))
        .eq("confirmado", True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


@router.get("/listar")
def listar(genero: Optional[str] = None, limit: int = 50,
           usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    q = (
        cliente.table(_TABLA)
        .select("artista, titulo, duracion_seg, genero, subgenero, fuente")
        .eq("confirmado", True)
        .order("artista")
        .limit(limit)
    )
    if genero:
        q = q.eq("genero", genero)
    return q.execute().data


class TrackManual(BaseModel):
    artista: str
    titulo: str
    duracion_seg: float
    genero: Optional[str] = None
    subgenero: Optional[str] = None
    sello: Optional[str] = None
    bpm: Optional[float] = None
    camelot: Optional[str] = None


@router.post("/tracks")
def agregar_manual(track: TrackManual,
                    usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    """Corrección manual de un DJ. `fuente` y `creado_por` los pone el
    servidor siempre — un cliente nunca puede declarar que su corrección
    viene de otro lado (ej. 'beatport_chart') para saltarse la protección
    de fuentes de alta confianza."""
    cliente = cliente_para_usuario(usuario.jwt)
    data = {
        "artista": track.artista.strip(),
        "titulo": track.titulo.strip(),
        "artista_norm": _norm(track.artista),
        "titulo_norm": _norm(track.titulo),
        "duracion_seg": round(track.duracion_seg, 2),
        "genero": track.genero,
        "subgenero": track.subgenero,
        "sello": track.sello,
        "bpm": round(track.bpm, 2) if track.bpm else None,
        "camelot": track.camelot,
        "fuente": "manual",
        "creado_por": usuario.id,
        "confirmado": True,
    }
    try:
        cliente.table(_TABLA).upsert(data, on_conflict="artista_norm,titulo_norm").execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}
