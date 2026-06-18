"""Clasificación de género: mapea el género del tag al árbol de Brian."""
from __future__ import annotations

import re
from dataclasses import dataclass

from config import GENRE_ALIASES, GENRE_TREE, FOLDER_REVIEW


@dataclass
class Classification:
    genero: str | None        # ej. "Techno"  (None => sin clasificar)
    subgenero: str | None     # ej. "Melodic Techno"
    confianza: str            # "exacta" | "parcial" | "ninguna"
    carpeta_relativa: str     # ruta destino relativa (ej. "Techno/Melodic Techno")
    nota: str = ""


def _normalize(s: str) -> str:
    """Minúsculas, sin acentos básicos ni símbolos, espacios colapsados."""
    s = s.lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"[\(\)\[\]/\-_,.|]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def classify(genero_raw: str) -> Classification:
    raw = (genero_raw or "").strip()
    if not raw:
        return Classification(None, None, "ninguna", FOLDER_REVIEW,
                              "Sin tag de género")

    key = _normalize(raw)

    # 1) Coincidencia exacta en el diccionario de alias
    if key in GENRE_ALIASES:
        genero, sub = GENRE_ALIASES[key]
        return _build(genero, sub, "exacta")

    # 2) Coincidencia parcial: el alias está contenido (o viceversa)
    best = None
    for alias, (genero, sub) in GENRE_ALIASES.items():
        if alias in key or key in alias:
            # preferimos el alias más largo (más específico)
            if best is None or len(alias) > len(best[0]):
                best = (alias, genero, sub)
    if best is not None:
        _, genero, sub = best
        return _build(genero, sub, "parcial",
                      nota=f"Coincidencia parcial con '{raw}'")

    # 3) Nada: a revisar
    return Classification(None, None, "ninguna", FOLDER_REVIEW,
                          f"Género no reconocido: '{raw}'")


def classify_con_filtro(genero_raw: str, artista_str: str, conn) -> Classification:
    """Como classify(), pero filtra géneros imposibles para el artista dado.

    Si el artista no está en la BD de artistas → sin restricción (idéntico a classify).
    Si el género detectado no está entre los permitidos → envía a _Por revisar.
    Las clasificaciones manuales deben protegerse en el llamador, no aquí.
    """
    import artist_db
    result = classify(genero_raw)
    if result.genero is None or conn is None:
        return result  # sin clasificar o sin BD → no hay qué filtrar

    permitidos = artist_db.generos_permitidos(conn, artista_str or "")
    if permitidos is None or not permitidos:
        return result  # artista no en BD o sin géneros → sin restricción

    clave = (result.genero, result.subgenero)
    clave_raiz = (result.genero, None)
    if clave in permitidos or clave_raiz in permitidos:
        return result  # género dentro de los permitidos → ok

    return Classification(
        None, None, "filtrado_artista", FOLDER_REVIEW,
        f"Género '{result.genero}' no producido por '{artista_str}'",
    )


def _build(genero: str, sub: str | None, confianza: str, nota: str = "") -> Classification:
    if sub and sub in GENRE_TREE.get(genero, []):
        carpeta = f"{genero}/{sub}"
    else:
        carpeta = genero
    return Classification(genero, sub, confianza, carpeta, nota)
