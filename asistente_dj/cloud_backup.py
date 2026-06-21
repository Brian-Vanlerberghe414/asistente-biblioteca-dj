"""Backup de audio personal al backend (Cloudflare R2) — Fase 2 del
Módulo 3. Usa la cuenta PERSONAL del DJ (`mi_email`/`mi_password` en
asistente_config.json), nunca la cuenta de servicio (esa es solo para la
automatización del scraper de charts).

El archivo nunca pasa por este módulo en sí: se pide al backend una URL
firmada y se sube *directo* a R2 con un PUT, evitando duplicar ancho de
banda."""
from __future__ import annotations

import os
from typing import Optional

import requests

import settings

BACKEND_URL = "https://asistente-biblioteca-dj.onrender.com"


def esta_configurado() -> bool:
    cfg = settings.cargar()
    return bool(cfg.get("mi_email") and cfg.get("mi_password"))


def crear_cuenta(email: str, password: str) -> tuple[bool, str]:
    """Crea la cuenta personal del DJ en Supabase Auth y la confirma (si hay
    `supabase_service_key` configurada — mismo patrón que la cuenta de
    servicio). Devuelve (ok, mensaje)."""
    from supabase import create_client
    cfg = settings.cargar()
    cliente = create_client(cfg["supabase_url"], cfg["supabase_key"])
    try:
        resp = cliente.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return False, f"No se pudo crear la cuenta: {e}"

    settings.set_("mi_email", email)
    settings.set_("mi_password", password)

    service_key = cfg.get("supabase_service_key", "").strip()
    if service_key and resp.user:
        try:
            admin = create_client(cfg["supabase_url"], service_key)
            admin.auth.admin.update_user_by_id(resp.user.id, {"email_confirm": True})
            return True, "Cuenta creada y confirmada. Ya podés subir tracks."
        except Exception:
            pass
    return True, "Cuenta creada. Revisá tu email para confirmarla antes de subir tracks."


def _obtener_jwt() -> Optional[str]:
    cfg = settings.cargar()
    email = cfg.get("mi_email", "").strip()
    password = cfg.get("mi_password", "").strip()
    if not email or not password:
        return None
    from supabase import create_client
    cliente = create_client(cfg["supabase_url"], cfg["supabase_key"])
    try:
        resp = cliente.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return None
    return resp.session.access_token


def subir_track(jwt: str, ruta_local: str, titulo: str, artista: str) -> tuple[bool, str]:
    """Sube un track al backup personal del DJ. Devuelve (ok, mensaje)."""
    if not ruta_local or not os.path.isfile(ruta_local):
        return False, "Archivo no encontrado en el disco"
    tamano = os.path.getsize(ruta_local)

    try:
        resp = requests.post(
            f"{BACKEND_URL}/audio/upload-url",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "titulo": titulo, "artista": artista,
                "tamano_bytes": tamano, "ruta_local": ruta_local,
            },
            timeout=15,
        )
        resp.raise_for_status()
        datos = resp.json()
    except Exception as e:
        return False, f"Error pidiendo URL de subida: {e}"

    try:
        with open(ruta_local, "rb") as f:
            put_resp = requests.put(datos["upload_url"], data=f, timeout=600)
        put_resp.raise_for_status()
    except Exception as e:
        return False, f"Error subiendo el archivo: {e}"
    return True, "OK"
