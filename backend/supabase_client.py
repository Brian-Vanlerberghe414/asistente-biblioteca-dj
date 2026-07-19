"""Cliente de Supabase por request — versión ASÍNCRONA (A1+A3 del plan
`docs/plan_multiplataforma_escalado.md`).

Por qué async: este backend casi no hace cálculo; todo su tiempo lo pasa
ESPERANDO a PostgREST (la API REST de Supabase) por HTTP. Con rutas
sincrónicas, cada request ocupa un hilo del threadpool mientras espera, y con
muchos usuarios a la vez se hace fila. Con rutas async, mientras un request
espera la respuesta de la base, el mismo worker atiende otros — así aguantamos
muchos más usuarios concurrentes con el mismo servidor.

Dos clientes distintos:

- `cliente_para_usuario` (dependency de FastAPI): un cliente POR REQUEST que
  actúa como el usuario dueño del JWT, para que las políticas RLS de Postgres
  (`auth.uid()`) apliquen solas. Se CIERRA solo al terminar el request (bloque
  `finally`) para no acumular conexiones abiertas — clave con 1000 usuarios.
  Nota (A1, follow-up): por seguridad no se puede COMPARTIR un cliente
  autenticado entre usuarios (el token va en el header del cliente), así que
  este es por-request; el reuso de conexiones keep-alive por-usuario queda como
  micro-optimización futura. El salto grande de capacidad lo da el async, no el
  keep-alive.

- `cliente_servicio` (singleton compartido): UN solo cliente con service_role
  para todo el proceso — como su credencial es fija (no depende del usuario), sí
  se puede reusar, y así todas las rutas de playlists compartidas comparten sus
  conexiones HTTP (eso SÍ es el reuso de A1). Se cierra en el shutdown de la app
  (ver `main.py`).
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

from fastapi import Depends
from supabase import create_async_client
from supabase._async.client import AsyncClient

from auth import UsuarioActual, obtener_usuario_actual

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]


async def cliente_para_usuario(
    usuario: UsuarioActual = Depends(obtener_usuario_actual),
) -> AsyncGenerator[AsyncClient, None]:
    """Dependency: cliente de Supabase async que actúa como el usuario
    autenticado — sus queries respetan el RLS de ese usuario. Se cierra solo al
    terminar el request."""
    cliente = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    cliente.postgrest.auth(usuario.jwt)
    try:
        yield cliente
    finally:
        # Solo se usó PostgREST (.table()); el resto de sub-clientes nunca abrió
        # conexión. Cerrar postgrest libera las conexiones HTTP del request.
        await cliente.postgrest.aclose()


_cliente_servicio: AsyncClient | None = None
_lock_servicio = asyncio.Lock()


async def cliente_servicio() -> AsyncClient:
    """Cliente con service_role (bypassa RLS) — para las escrituras de las
    playlists COMPARTIDAS, donde el backend valida rol/modo en código y hace el
    DB op como servicio (ver routes/playlists_compartidas.py). NUNCA se expone a
    un cliente final ni se usa para datos personales (esos van con RLS por JWT).

    Singleton compartido y lazy: se crea una sola vez (con doble chequeo bajo
    lock para que dos requests simultáneos no creen dos). Los deploys que todavía
    no configuraron SUPABASE_SERVICE_ROLE_KEY siguen levantando; solo falla si de
    verdad se llama a una ruta que lo necesita."""
    global _cliente_servicio
    if _cliente_servicio is None:
        async with _lock_servicio:
            if _cliente_servicio is None:
                key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
                if not key:
                    raise RuntimeError(
                        "Falta SUPABASE_SERVICE_ROLE_KEY (necesaria para playlists compartidas)."
                    )
                _cliente_servicio = await create_async_client(SUPABASE_URL, key)
    return _cliente_servicio


async def cerrar_cliente_servicio() -> None:
    """Cierra el cliente de servicio compartido — se llama en el shutdown de la
    app (`main.py`) para liberar sus conexiones prolijamente."""
    global _cliente_servicio
    if _cliente_servicio is not None:
        await _cliente_servicio.postgrest.aclose()
        _cliente_servicio = None
