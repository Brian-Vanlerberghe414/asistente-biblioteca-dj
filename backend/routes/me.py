"""GET /me — chequeo de cordura: confirma que el JWT se verificó bien y
devuelve quién es el usuario autenticado."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import UsuarioActual, obtener_usuario_actual

router = APIRouter()


@router.get("/me")
def me(usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    return {"id": usuario.id, "email": usuario.email}
