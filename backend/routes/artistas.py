"""Registro de qué género produce cada artista — mismas queries que
`asistente_dj/biblioteca_confiable.py:generos_de_artista`."""
from __future__ import annotations

import re
import unicodedata

from fastapi import APIRouter, Depends

from auth import UsuarioActual, obtener_usuario_actual
from supabase_client import cliente_para_usuario

router = APIRouter(prefix="/artistas")

_TABLA = "artistas_generos"


def _norm(texto: str) -> str:
    if not texto:
        return ""
    s = texto.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@router.get("/{nombre}/generos")
def generos_de_artista(nombre: str,
                        usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    resp = (
        cliente.table(_TABLA)
        .select("artista, genero, subgenero")
        .ilike("artista_norm", f"%{_norm(nombre)}%")
        .execute()
    )
    return resp.data
