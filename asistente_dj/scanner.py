"""Escaneo de la biblioteca: recorre una carpeta, lee tags, clasifica y guarda."""
from __future__ import annotations

import os
from datetime import datetime

from config import (AUDIO_EXTENSIONS, LOSSLESS_EXTENSIONS,
                    LOW_QUALITY_BITRATE_KBPS)
import db
import tags as tagreader
from classifier import classify, classify_con_filtro
import biblioteca_confiable


def es_basura(name: str) -> bool:
    """Archivos que no son música real y hay que ignorar:
    resource forks de macOS (._algo), .DS_Store, archivos ocultos."""
    base = os.path.basename(name)
    return base.startswith("._") or base in (".DS_Store", "Thumbs.db")


def iter_audio_files(root: str):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if es_basura(name):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext in AUDIO_EXTENSIONS:
                # normpath: si `root` viene con barras mezcladas ("/" vs "\"),
                # el mismo archivo puede terminar guardado con dos strings de
                # ruta distintos en escaneos sucesivos, y como ruta_origen es
                # la clave de upsert, eso duplica el track entero en la base
                # (visto en producción: toda la biblioteca x2, sesión 2026-06-18).
                yield os.path.normpath(os.path.join(dirpath, name))


def _is_low_quality(ext: str, bitrate_kbps) -> bool:
    if ext in LOSSLESS_EXTENSIONS:
        return False
    if bitrate_kbps is None:
        return False  # desconocido: no lo marcamos como malo
    return bitrate_kbps < LOW_QUALITY_BITRATE_KBPS


def scan(root: str, conn) -> dict:
    """Escanea root, llena la tabla tracks y devuelve un resumen."""
    resumen = {
        "total": 0, "clasificados": 0, "por_revisar": 0,
        "baja_calidad": 0, "por_genero": {}, "ilegibles": [], "basura_limpiada": 0,
    }

    # Limpiar de la base archivos basura (._*, .DS_Store) que entraron antes
    junk_rows = conn.execute(
        "SELECT id, ruta_origen FROM tracks").fetchall()
    for jr in junk_rows:
        from os.path import basename
        b = basename(jr["ruta_origen"])
        if b.startswith("._") or b in (".DS_Store", "Thumbs.db"):
            conn.execute("DELETE FROM tracks WHERE id=?", (jr["id"],))
            resumen["basura_limpiada"] += 1

    for path in iter_audio_files(root):
        ext = os.path.splitext(path)[1].lower()
        t = tagreader.read_tags(path)
        if t.ilegible:
            resumen["ilegibles"].append(path)
        baja = _is_low_quality(ext, t.bitrate_kbps)

        # Proteger clasificaciones manuales y confirmadas por Supabase:
        # nunca sobreescribir fuentes de alta confianza.
        existente = conn.execute(
            "SELECT genero, subgenero, confianza FROM tracks WHERE ruta_origen=?",
            (path,),
        ).fetchone()
        cover_url = None
        if existente and existente["confianza"] in ("manual", "supabase"):
            c_genero    = existente["genero"]
            c_subgenero = existente["subgenero"]
            c_confianza = existente["confianza"]
        else:
            # Paso 2: clasificar por tag
            c = classify_con_filtro(t.genero_raw, t.artista or "", conn)
            c_genero    = c.genero
            c_subgenero = c.subgenero
            c_confianza = c.confianza

            # Paso 2.5: consultar la Biblioteca Confiable (Supabase)
            # Tiene prioridad sobre el clasificador de tags. De paso, si
            # tiene carátula ya cargada por otro DJ/escaneo, la traemos
            # (los tracks que no estén ahí los completa CoverFillWorker
            # en background, ver gui/workers.py).
            if t.duracion_seg:
                hit = biblioteca_confiable.buscar(
                    t.artista or "", t.titulo or "", t.duracion_seg
                )
                if hit:
                    c_genero    = hit.genero
                    c_subgenero = hit.subgenero
                    c_confianza = "supabase"
                    if hit.cover_url:
                        cover_url = hit.cover_url

        estado = "por_revisar" if c_genero is None else "escaneado"

        data = {
            "ruta_origen": path,
            "ruta_destino": None,
            "titulo": t.titulo or os.path.splitext(os.path.basename(path))[0],
            "artista": t.artista,
            "sello": t.sello,
            "anio": t.anio,
            "bpm": t.bpm,
            "key": t.key,
            "duracion_seg": t.duracion_seg,
            "genero_raw": t.genero_raw,
            "genero": c_genero,
            "subgenero": c_subgenero,
            "confianza": c_confianza,
            "bitrate_kbps": t.bitrate_kbps,
            "formato": ext.lstrip("."),
            "baja_calidad": 1 if baja else 0,
            "estado": estado,
            "fecha_ingreso": datetime.now().isoformat(timespec="seconds"),
        }
        # Solo se manda si se encontró: así no se pisa con NULL un cover_url
        # que ya hubiera completado CoverFillWorker en un escaneo anterior.
        if cover_url:
            data["cover_url"] = cover_url
        db.upsert_track(conn, data)

        resumen["total"] += 1
        if c_genero is None:
            resumen["por_revisar"] += 1
        else:
            resumen["clasificados"] += 1
            carpeta_rel = f"{c_genero}/{c_subgenero}" if c_subgenero else c_genero
            resumen["por_genero"][carpeta_rel] = (
                resumen["por_genero"].get(carpeta_rel, 0) + 1)
        if baja:
            resumen["baja_calidad"] += 1

    conn.commit()
    return resumen
