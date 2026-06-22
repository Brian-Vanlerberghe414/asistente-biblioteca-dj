"""Backend del Asistente de Biblioteca DJ — Fase 1 del Módulo 3.

Los clientes (Android más adelante, web después) inician sesión directo
contra Supabase Auth (con la clave anon, vía su SDK) y mandan el JWT
resultante a esta API. Esta API nunca usa una clave compartida para hablar
con Supabase en nombre de un usuario — cada request arma un cliente con el
JWT de quien pidió, así las políticas RLS de Postgres hacen el trabajo de
permisos (ver `supabase_client.py` / `auth.py`).

Correr local:  uvicorn main:app --reload
Variables de entorno requeridas: SUPABASE_URL, SUPABASE_ANON_KEY
"""
from __future__ import annotations

from fastapi import FastAPI

from routes import artistas, audio, biblioteca, charts, me, mi_biblioteca

app = FastAPI(title="Asistente Biblioteca DJ — API")

app.include_router(me.router)
app.include_router(biblioteca.router)
app.include_router(artistas.router)
app.include_router(charts.router)
app.include_router(audio.router)
app.include_router(mi_biblioteca.router)


@app.get("/health")
def health():
    return {"status": "ok"}
