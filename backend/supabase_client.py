"""Cliente de Supabase por request.

A diferencia de `asistente_dj/biblioteca_confiable.py` (un singleton con UNA
credencial estática por proceso, pensado para la app de escritorio de un
solo DJ), este backend atiende a muchos usuarios a la vez — cada request
necesita su propio cliente, actuando como el usuario que hizo ese request
(vía su JWT), para que las políticas RLS de Postgres (`auth.uid()`) se
apliquen solas, sin reinventar la lógica de permisos en Python.
"""
from __future__ import annotations

import os

from supabase import Client, create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]


def cliente_para_usuario(jwt_token: str) -> Client:
    """Cliente de Supabase que actúa como el usuario autenticado dueño de
    `jwt_token` — las queries que haga respetan el RLS de ese usuario."""
    cliente = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    cliente.postgrest.auth(jwt_token)
    return cliente
