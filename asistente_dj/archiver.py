"""Archivado por género: copia cada track a la estructura Género/Subgénero.

Filosofía (del documento de concepto):
  - El programa COPIA la biblioteca (no mueve el original) -> cero riesgo.
  - Cada track vive en UNA sola carpeta.
  - Género dudoso -> carpeta _Por revisar (o se pregunta, ver interactivo en cli).
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from config import FOLDER_REVIEW
from classifier import classify


@dataclass
class PlanItem:
    track_id: int
    origen: str
    destino_rel: str   # carpeta relativa destino
    nombre: str
    confianza: str


def _safe_name(name: str) -> str:
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    return name.strip()


def build_plan(conn) -> list[PlanItem]:
    """Calcula a dónde iría cada track, sin tocar nada (dry-run)."""
    plan = []
    rows = conn.execute(
        "SELECT id, ruta_origen, titulo, artista, genero, subgenero, "
        "confianza, genero_raw FROM tracks").fetchall()
    for r in rows:
        if r["genero"] is None:
            destino = FOLDER_REVIEW
            conf = "ninguna"
        else:
            c = classify(r["genero_raw"])
            destino = c.carpeta_relativa
            conf = r["confianza"]
        ext = os.path.splitext(r["ruta_origen"])[1]
        artista = r["artista"] or "Unknown"
        titulo = r["titulo"] or "Untitled"
        nombre = _safe_name(f"{artista} - {titulo}{ext}")
        plan.append(PlanItem(r["id"], r["ruta_origen"], destino, nombre, conf))
    return plan


def execute_plan(conn, plan: list[PlanItem], dest_root: str,
                 dry_run: bool = True) -> dict:
    """Ejecuta (o simula) el archivado por copia."""
    res = {"copiados": 0, "saltados": 0, "errores": 0}
    for item in plan:
        carpeta = os.path.join(dest_root, *item.destino_rel.split("/"))
        destino_full = os.path.join(carpeta, item.nombre)
        if dry_run:
            res["copiados"] += 1
            continue
        try:
            os.makedirs(carpeta, exist_ok=True)
            if os.path.exists(destino_full):
                res["saltados"] += 1
            else:
                shutil.copy2(item.origen, destino_full)
                res["copiados"] += 1
            estado = "por_revisar" if item.destino_rel == FOLDER_REVIEW else "archivado"
            conn.execute(
                "UPDATE tracks SET ruta_destino=?, estado=? WHERE id=?",
                (destino_full, estado, item.track_id))
        except Exception:
            res["errores"] += 1
    if not dry_run:
        conn.commit()
    return res
