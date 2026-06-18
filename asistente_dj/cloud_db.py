"""Integración con la BD musical compartida Overcome Harmony (Supabase).

Tablas en Supabase:
  contribuciones  — staging: todas las correcciones de los DJs, para revisión
  tracks_canonical — BD final curada por Brian tras analizar contribuciones

Flujo:
  push_contribucion()   → DJ guarda corrección → sube a contribuciones
  pull_track()          → consulta tracks_canonical por huella → sugiere valores
  encolar_pendiente()   → si no hay red, guarda cloud_status='pendiente' en BD local
  enviar_pendientes()   → al arrancar o analizar, reintenta los pendientes
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import settings

_PROJ = os.path.dirname(os.path.abspath(__file__))

APP_VERSION = "0.1-beta"


def _config() -> tuple[str, str]:
    """Devuelve (supabase_url, supabase_key). Lanza ValueError si no están configurados."""
    url = settings.get("supabase_url", "")
    key = settings.get("supabase_key", "")
    if not url or not key:
        raise ValueError(
            "Supabase no configurado. Ingresá la URL y la API key en Configuración."
        )
    return url.rstrip("/"), key


def _headers() -> dict:
    _, key = _config()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def dj_uid() -> str:
    """UUID anónimo de esta instalación. Se genera una vez y persiste en settings."""
    uid = settings.get("dj_uid", "")
    if not uid:
        import uuid
        uid = str(uuid.uuid4())
        settings.set_("dj_uid", uid)
    return uid


def fp_hash(huella_str: str) -> str:
    """SHA256 del string de huella Chromaprint → clave única para BD compartida."""
    return hashlib.sha256(huella_str.encode()).hexdigest()


# ─────────────────────────────────────────────── push ───────────────────────

def push_contribucion(conn, track_id: int, comentario: str = "") -> bool:
    """Sube los datos del track a la tabla `contribuciones` en Supabase.
    Devuelve True si tuvo éxito, False si falló (sin red, config inválida, etc.)."""
    try:
        import requests as req
    except ImportError:
        return False

    row = conn.execute(
        "SELECT artista, titulo, bpm, key, camelot, genero, subgenero, "
        "COALESCE(energia_manual, energia) AS energia, bpm_fuente, "
        "f_loud, f_bright, f_low, f_busy, waveform_data, huella, huella_dur "
        "FROM tracks WHERE id=?", (track_id,)
    ).fetchone()
    if not row or not row["huella"]:
        return False

    url, _ = _config()
    payload = {
        "fp_hash":      fp_hash(row["huella"]),
        "fp_dur":       row["huella_dur"],
        "artista":      row["artista"],
        "titulo":       row["titulo"],
        "bpm":          _to_float(row["bpm"]),
        "key_nota":     row["key"],
        "camelot":      row["camelot"],
        "genero":       row["genero"],
        "subgenero":    row["subgenero"],
        "energia":      row["energia"],
        "bpm_fuente":   row["bpm_fuente"],
        "f_loud":       row["f_loud"],
        "f_bright":     row["f_bright"],
        "f_low":        row["f_low"],
        "f_busy":       row["f_busy"],
        "waveform_data": row["waveform_data"],
        "comentario":   comentario or None,
        "dj_uid":       dj_uid(),
        "version_app":  APP_VERSION,
    }

    try:
        r = req.post(
            f"{url}/rest/v1/contribuciones",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        if r.status_code in (200, 201):
            conn.execute(
                "UPDATE tracks SET cloud_status='enviado' WHERE id=?", (track_id,)
            )
            conn.commit()
            return True
        return False
    except Exception:
        return False


def encolar_pendiente(conn, track_id: int):
    """Marca el track como pendiente de envío (cuando no hay red)."""
    conn.execute(
        "UPDATE tracks SET cloud_status='pendiente' WHERE id=?", (track_id,)
    )
    conn.commit()


def enviar_pendientes(conn, progreso_cb=None) -> int:
    """Reintenta enviar todos los tracks marcados como 'pendiente'. Devuelve n enviados."""
    rows = conn.execute(
        "SELECT id FROM tracks WHERE cloud_status='pendiente' AND huella IS NOT NULL"
    ).fetchall()
    enviados = 0
    for r in rows:
        if push_contribucion(conn, r["id"]):
            enviados += 1
            if progreso_cb:
                progreso_cb(f"Enviado pendiente {enviados}/{len(rows)}…")
    return enviados


# ─────────────────────────────────────────────── pull ───────────────────────

def pull_track(fp_hash_str: str) -> dict | None:
    """Consulta tracks_canonical por SHA256 de huella. Devuelve dict o None."""
    try:
        import requests as req
    except ImportError:
        return None

    try:
        url, _ = _config()
    except ValueError:
        return None

    try:
        r = req.get(
            f"{url}/rest/v1/tracks_canonical",
            headers={**_headers(), "Prefer": ""},
            params={"fp_hash": f"eq.{fp_hash_str}", "select": "*", "limit": "1"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            return data[0] if data else None
        return None
    except Exception:
        return None


def pull_tracks_batch(fp_hashes: list[str]) -> dict[str, dict]:
    """Consulta varios fp_hash de una vez. Devuelve {fp_hash: row}."""
    if not fp_hashes:
        return {}
    try:
        import requests as req
        url, _ = _config()
    except Exception:
        return {}

    try:
        in_clause = "(" + ",".join(fp_hashes) + ")"
        r = req.get(
            f"{url}/rest/v1/tracks_canonical",
            headers={**_headers(), "Prefer": ""},
            params={"fp_hash": f"in.{in_clause}", "select": "*"},
            timeout=15,
        )
        if r.status_code == 200:
            return {row["fp_hash"]: row for row in r.json()}
        return {}
    except Exception:
        return {}


# ─────────────────────────────────────────────── helpers ────────────────────

def _to_float(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def configurado() -> bool:
    """Devuelve True si Supabase está configurado (URL + key presentes)."""
    return bool(settings.get("supabase_url")) and bool(settings.get("supabase_key"))
