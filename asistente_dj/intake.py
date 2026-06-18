"""Procesamiento de música nueva que entra a la carpeta de ingreso.

Para cada archivo nuevo: lee el tag, decide el género (cascada segura:
tag reconocido -> sugerencia por audio -> _Por revisar), lo archiva en
Género/Subgénero (mueve o copia) y lo registra en la base.
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime

import db
import tags as tagreader
from classifier import classify
from config import FOLDER_REVIEW, LOSSLESS_EXTENSIONS, LOW_QUALITY_BITRATE_KBPS
from archiver import _safe_name


def _parse_bpm(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return None


def procesar(conn, path, dest_root, analizar=True, mover=True, pedir_genero=None):
    """Procesa un archivo. Devuelve (destino_relativo, motivo).
    motivo: 'tag' | 'manual' | 'audio' | 'revisar' | 'ya_existe' | 'error' | 'saltado'.
    pedir_genero(label, ruta): callback opcional que, si el género no se reconoce,
    le pregunta al usuario. Devuelve (genero, subgenero), None (=_Por revisar) o 'SKIP'."""
    ext = os.path.splitext(path)[1].lower()
    t = tagreader.read_tags(path)
    c = classify(t.genero_raw)

    bpm, key, camelot = t.bpm, t.key, ""
    energia_raw = f_loud = f_bright = f_low = f_busy = None
    gsug = ssug = None
    feat = None
    if analizar:
        import analyzer
        feat = analyzer.analyze(path)
        if feat.ok:
            if not (_parse_bpm(bpm) and _parse_bpm(bpm) > 0):
                bpm = str(feat.bpm) if feat.bpm else bpm
            key = key or feat.key
            camelot = feat.camelot
            energia_raw = feat.energia_raw
            f_loud, f_bright = feat.f_loud, feat.f_bright
            f_low, f_busy = feat.f_low, feat.f_busy

    # cascada de género
    if c.genero is not None:
        destino_rel, motivo = c.carpeta_relativa, "tag"
        genero, subgenero = c.genero, c.subgenero
    elif pedir_genero is not None:
        # no reconocido: le preguntamos al usuario (elige de la lista)
        label = f"{t.artista or '?'} - {t.titulo or os.path.basename(path)}"
        res = pedir_genero(label, path)
        if res == "SKIP":
            return None, "saltado"
        if isinstance(res, tuple):
            genero, subgenero = res
            destino_rel = f"{genero}/{subgenero}" if subgenero else genero
            motivo = "manual"
        else:
            genero = subgenero = None
            destino_rel, motivo = FOLDER_REVIEW, "revisar"
    else:
        genero = subgenero = None
        destino_rel, motivo = FOLDER_REVIEW, "revisar"
        if feat and feat.ok:
            import analyzer
            bpm_ef = _parse_bpm(bpm) or feat.bpm
            g, s, _nota = analyzer.suggest_genre(
                bpm_ef, None, feat.f_low, feat.f_bright, feat.f_busy)
            if g:
                destino_rel = f"{g}/{s}" if s else g
                motivo = "audio"
                gsug, ssug = g, s

    # archivar
    carpeta = os.path.join(dest_root, *destino_rel.split("/"))
    artista = t.artista or "Unknown"
    titulo = t.titulo or os.path.splitext(os.path.basename(path))[0]
    nombre = _safe_name(f"{artista} - {titulo}{ext}")
    destino_full = os.path.normpath(os.path.join(carpeta, nombre))
    if os.path.exists(destino_full):
        return destino_rel, "ya_existe"
    try:
        os.makedirs(carpeta, exist_ok=True)
        if mover:
            shutil.move(path, destino_full)
        else:
            shutil.copy2(path, destino_full)
    except Exception:
        return destino_rel, "error"

    baja = 0
    if ext not in LOSSLESS_EXTENSIONS and t.bitrate_kbps:
        baja = 1 if t.bitrate_kbps < LOW_QUALITY_BITRATE_KBPS else 0

    db.upsert_track(conn, {
        "ruta_origen": destino_full,
        "ruta_destino": destino_full,
        "titulo": titulo, "artista": t.artista, "sello": t.sello, "anio": t.anio,
        "bpm": bpm, "key": key, "camelot": camelot,
        "duracion_seg": t.duracion_seg, "genero_raw": t.genero_raw,
        "genero": genero, "subgenero": subgenero,
        "genero_sugerido": gsug, "subgenero_sugerido": ssug,
        "energia_raw": energia_raw, "f_loud": f_loud, "f_bright": f_bright,
        "f_low": f_low, "f_busy": f_busy,
        "bitrate_kbps": t.bitrate_kbps, "formato": ext.lstrip("."),
        "baja_calidad": baja,
        "estado": "por_revisar" if genero is None else "archivado",
        "analizado": 1 if (feat and feat.ok) else 0,
        "fecha_ingreso": datetime.now().isoformat(timespec="seconds"),
    })
    conn.commit()
    return destino_rel, motivo
