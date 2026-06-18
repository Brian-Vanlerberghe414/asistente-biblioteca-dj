"""Perfiles de género de música electrónica (taxonomía Beatport 2025-2026).

Carga `data/generos_electronicos_beatport.json` y ofrece un matcher que
puntúa cada perfil contra los rasgos de audio de un track (BPM, graves/
sub-bass, brillo espectral, densidad rítmica, energía) para sugerir
género/subgénero cuando no hay tag ni Biblioteca Confiable.

No reemplaza al tag ni a la Biblioteca Confiable: es la heurística de
"paso 4 — analizar audio", probabilística por diseño (las fronteras de
BPM/feel se superponen en el catálogo real; la corrección manual siempre
tiene la última palabra).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data",
                          "generos_electronicos_beatport.json")

# id del JSON -> (Género, Subgénero) en el árbol propio (config.GENRE_TREE).
# None = excluir del matching (no es un género musical real).
MAPEO_A_ARBOL = {
    "house":                       ("House", None),
    "deep_house":                  ("House", "Deep House"),
    "tech_house":                  ("House", "Tech House"),
    "progressive_house":           ("House", "Progressive House"),
    "melodic_house_techno":        ("Melodic House & Techno", None),
    "organic_house":                ("House", "Organic House"),
    "afro_house":                  ("House", "Afro House"),
    "amapiano":                    ("Afro", "Amapiano"),
    "funky_house":                 ("House", "Progressive House"),
    "jackin_house":                ("House", "Jackin House"),
    "bass_house":                  ("House", "Bass House"),
    "indie_dance":                 ("Indie Dance", None),
    "nu_disco_disco":              ("Indie Dance", "Nu Disco"),
    "minimal_deep_tech":           ("Techno", "Minimal - Deep Tech"),
    "techno_peak_time_driving":    ("Techno", "Peak Time - Driving"),
    "techno_raw_deep_hypnotic":    ("Techno", "Raw - Deep - Hypnotic"),
    "hard_techno":                 ("Techno", "Hard Techno"),
    "trance_main_floor":           ("Trance", "Main Floor"),
    "trance_raw_deep_hypnotic":    ("Trance", "Raw - Deep - Hypnotic"),
    "psy_trance":                  ("Trance", "Psy-Trance"),
    "drum_and_bass":               ("Drum & Bass", None),
    "dubstep":                     ("Breaks", "UK Bass"),
    "140_deep_dubstep_grime":      ("Breaks", "UK Bass"),
    "breaks_breakbeat_uk_bass":    ("Breaks", "Breakbeat"),
    "uk_garage_bassline":          ("UK Garage", None),
    "trap_wave":                   ("Hip-Hop", "Trap"),
    "electro":                     ("Electro", None),
    "electronica":                 ("Electronica", None),
    "downtempo":                   ("Ambient", "Downtempo"),
    "ambient_experimental":        ("Ambient", None),
    "hard_dance_hardcore_neo_rave": ("Hard Dance", None),
    "mainstage":                   ("Big Room", None),
    "dance_pop":                   ("Big Room", None),
    "brazilian_funk":              ("Latin", "Brazilian Funk"),
    "dj_tools":                    None,   # no es género: excluido del matching
}

# pesos relativos de cada feature en el score final (BPM domina, como pide
# la guía: "el tempo es necesario pero no suficiente").
PESO_BPM = 3.0
PESO_SUB_BASS = 1.5
PESO_BRILLO = 1.0
PESO_DANCEABILITY = 0.8
PESO_ENERGIA = 0.7


@dataclass
class Coincidencia:
    genero_id: str
    nombre_beatport: str
    genero: Optional[str]
    subgenero: Optional[str]
    score: float


_perfiles_cache: Optional[list[dict]] = None


def _cargar_perfiles() -> list[dict]:
    global _perfiles_cache
    if _perfiles_cache is None:
        with open(_DATA_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _perfiles_cache = [
            p for p in data["generos"] if p["id"] != "dj_tools"
        ]
    return _perfiles_cache


def _score_bpm(perfil_bpm: dict, bpm: float) -> float:
    bmin, bmax, btyp = perfil_bpm["min"], perfil_bpm["max"], perfil_bpm.get("tipico")
    if btyp is None:
        btyp = (bmin + bmax) / 2
    if bmin <= bpm <= bmax:
        mitad = max(btyp - bmin, bmax - btyp, 1)
        return max(0.7, 1.0 - 0.3 * abs(bpm - btyp) / mitad)
    dist = min(abs(bpm - bmin), abs(bpm - bmax))
    return max(0.0, 1.0 - dist / 6.0)  # decae rápido: a 6 BPM del rango, score 0


def _score_escala(valor_perfil_1_5: float, feature_0_1: Optional[float]) -> Optional[float]:
    if feature_0_1 is None or valor_perfil_1_5 <= 0:
        return None
    objetivo = valor_perfil_1_5 / 5.0
    return max(0.0, 1.0 - abs(feature_0_1 - objetivo))


def mejores_coincidencias(bpm: Optional[float], energia: Optional[float] = None,
                          f_low: Optional[float] = None, f_bright: Optional[float] = None,
                          f_busy: Optional[float] = None, top: int = 3) -> list[Coincidencia]:
    """Puntúa todos los perfiles contra los rasgos del track y devuelve el
    top-N ordenado por score descendente. bpm es obligatorio (sin BPM no hay
    carril); el resto de features son opcionales y se ignoran si faltan."""
    if bpm is None:
        return []
    energia_0_1 = (energia / 10.0) if energia is not None else None

    resultados = []
    for perfil in _cargar_perfiles():
        peso_total = PESO_BPM
        score = PESO_BPM * _score_bpm(perfil["bpm"], bpm)

        for peso, valor_perfil, feature in (
            (PESO_SUB_BASS, perfil["sub_bass"], f_low),
            (PESO_BRILLO, perfil["brillo_espectral"], f_bright),
            (PESO_DANCEABILITY, perfil["danceability"], f_busy),
            (PESO_ENERGIA, perfil["energia"], energia_0_1),
        ):
            s = _score_escala(valor_perfil, feature)
            if s is not None:
                score += peso * s
                peso_total += peso

        score_final = score / peso_total
        mapeo = MAPEO_A_ARBOL.get(perfil["id"])
        genero, subgenero = mapeo if mapeo else (None, None)
        resultados.append(Coincidencia(
            genero_id=perfil["id"], nombre_beatport=perfil["nombre_beatport"],
            genero=genero, subgenero=subgenero, score=score_final,
        ))

    resultados.sort(key=lambda c: -c.score)
    return resultados[:top]


def suggest_genre(bpm: Optional[float], energia: Optional[float] = None,
                  f_low: Optional[float] = None, f_bright: Optional[float] = None,
                  f_busy: Optional[float] = None):
    """Devuelve (genero, subgenero, nota) — la mejor coincidencia + top-3
    como referencia probabilística en la nota."""
    if bpm is None:
        return (None, None, "sin BPM")
    top = mejores_coincidencias(bpm, energia, f_low, f_bright, f_busy, top=3)
    if not top:
        return (None, None, "sin coincidencias")
    mejor = top[0]
    resumen = " | ".join(f"{c.nombre_beatport} {c.score:.2f}" for c in top)
    nota = f"perfil:{mejor.nombre_beatport} ({mejor.score:.2f}) — top3: {resumen}"
    return (mejor.genero, mejor.subgenero, nota)
