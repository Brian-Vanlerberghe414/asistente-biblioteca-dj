"""Verificación del JWT de Supabase Auth.

Los clientes (Android más adelante, curl/Postman por ahora) inician sesión
*directo* contra Supabase Auth con la clave anon (eso es seguro, está
pensado para eso) y mandan el JWT resultante en cada request a esta API
como `Authorization: Bearer <jwt>`.

Las claves de Supabase nuevas firman con ES256 (asimétrico) — se verifica
contra la clave pública (JWKS) del proyecto, sin necesitar ningún secreto
compartido en el backend.
"""
from __future__ import annotations

import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwk_client = jwt.PyJWKClient(_JWKS_URL)

_security = HTTPBearer()


class UsuarioActual:
    """Identidad del DJ autenticado que hizo el request, más su propio JWT
    (se necesita para que `supabase_client.cliente_para_usuario` arme un
    cliente de Supabase que actúe como él, respetando RLS)."""

    def __init__(self, id: str, email: str | None, jwt_token: str):
        self.id = id
        self.email = email
        self.jwt = jwt_token


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(_security),
) -> UsuarioActual:
    token = credenciales.credentials
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["ES256"],
            audience="authenticated",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido o expirado: {exc}",
        )
    return UsuarioActual(id=payload["sub"], email=payload.get("email"), jwt_token=token)
