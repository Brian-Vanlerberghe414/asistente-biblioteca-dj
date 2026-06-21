"""Backup de audio personal — cada DJ sube sus propios archivos a R2.
A diferencia de `biblioteca.py` (metadata compartida), esto es privado:
la tabla `audio_personal` tiene RLS que ni siquiera deja leer las filas de
otro usuario."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import UsuarioActual, obtener_usuario_actual
from storage import url_descarga, url_subida
from supabase_client import cliente_para_usuario

router = APIRouter(prefix="/audio")

_TABLA = "audio_personal"


class SolicitudSubida(BaseModel):
    titulo: str
    artista: str | None = None
    tamano_bytes: int
    ruta_local: str | None = None


@router.post("/upload-url")
def pedir_url_subida(solicitud: SolicitudSubida,
                      usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    r2_key = f"{usuario.id}/{uuid.uuid4().hex}"
    cliente = cliente_para_usuario(usuario.jwt)
    try:
        cliente.table(_TABLA).insert({
            "usuario_id": usuario.id,
            "r2_key": r2_key,
            "titulo": solicitud.titulo,
            "artista": solicitud.artista,
            "tamano_bytes": solicitud.tamano_bytes,
            "ruta_local": solicitud.ruta_local,
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"upload_url": url_subida(r2_key), "r2_key": r2_key}


@router.get("/mios")
def mi_coleccion(usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    resp = cliente.table(_TABLA).select("*").order("subido_en", desc=True).execute()
    return resp.data


@router.get("/{r2_key:path}/download-url")
def pedir_url_descarga(r2_key: str,
                        usuario: UsuarioActual = Depends(obtener_usuario_actual)):
    cliente = cliente_para_usuario(usuario.jwt)
    resp = cliente.table(_TABLA).select("id").eq("r2_key", r2_key).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="No encontrado (o no es tuyo)")
    return {"download_url": url_descarga(r2_key)}
