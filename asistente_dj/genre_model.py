"""Clasificador KNN de género por audio.

Usa los tracks ya clasificados en la BD como conjunto de entrenamiento.
Features: bpm_norm, f_bright, f_low, f_busy (4 dimensiones).
f_loud excluido: es ~1.0 en toda música electrónica masterizada (no discrimina).

Pesos calibrados sobre estadísticas reales de la biblioteca:
  bpm=2.5  (discriminador más fuerte, rangos p10-p90 distintos por subgénero)
  f_low=1.5 (Psy-Trance 0.298 vs Big Room 0.198)
  f_busy=1.3 (Tech House 0.353 vs Big Room 0.268)
  f_bright=1.2 (Psy-Trance 0.455 vs Trance Main Floor 0.561)
"""
from __future__ import annotations

import numpy as np
from collections import Counter

BPM_MIN = 110.0
BPM_MAX = 165.0
PESOS   = np.array([2.5, 1.2, 1.5, 1.3])   # bpm_n, f_bright, f_low, f_busy


def _bpm_norm(bpm) -> float | None:
    """Normaliza BPM a [0,1] en rango 110-165. Devuelve None si es outlier."""
    try:
        b = float(bpm)
        if not (BPM_MIN <= b <= BPM_MAX):
            return None
        return (b - BPM_MIN) / (BPM_MAX - BPM_MIN)
    except (TypeError, ValueError):
        return None


def vector_features(row: dict) -> np.ndarray | None:
    """Construye vector de 4 features. Devuelve None si BPM es outlier/inválido."""
    bpm_n = _bpm_norm(row.get("bpm"))
    if bpm_n is None:
        return None
    return np.array([
        bpm_n,
        float(row.get("f_bright") or 0.5),
        float(row.get("f_low")    or 0.5),
        float(row.get("f_busy")   or 0.5),
    ], dtype=float)


def _cargar_entrenamiento(conn) -> tuple:
    """Carga tracks clasificados+analizados con BPM válido como training set.

    Retorna (X, labels, mean, std) o (None, None, None, None) si no hay datos.
    """
    rows = conn.execute(
        "SELECT bpm, f_bright, f_low, f_busy, genero, subgenero "
        "FROM tracks "
        "WHERE genero IS NOT NULL AND f_low IS NOT NULL AND analizado=1"
    ).fetchall()
    vecs, labels = [], []
    for r in rows:
        v = vector_features(dict(r))
        if v is not None:
            vecs.append(v)
            labels.append(f"{r['genero']}/{r['subgenero'] or ''}")
    if not vecs:
        return None, None, None, None
    X    = np.array(vecs, dtype=float)
    mean = X.mean(axis=0)
    std  = X.std(axis=0)
    std[std == 0] = 1.0
    return X, labels, mean, std


def predecir(conn, row: dict, k: int = 7) -> tuple[str | None, str | None, float]:
    """Predice (genero, subgenero, confianza) para un track usando KNN ponderado.

    confianza = fracción de k vecinos que votan por la clase ganadora (0-1).
    Retorna (None, None, 0.0) si BPM es inválido o no hay suficiente entrenamiento.
    """
    X, y, mean, std = _cargar_entrenamiento(conn)
    if X is None or len(X) < k:
        return None, None, 0.0
    vec = vector_features(row)
    if vec is None:
        return None, None, 0.0
    Xn = (X   - mean) / std * PESOS
    vn = (vec - mean) / std * PESOS
    dists     = np.linalg.norm(Xn - vn, axis=1)
    nn_labels = [y[i] for i in np.argsort(dists)[:k]]
    label, votos = Counter(nn_labels).most_common(1)[0]
    partes    = label.split("/", 1)
    genero    = partes[0] or None
    subgenero = (partes[1] if len(partes) > 1 and partes[1] else None)
    return genero, subgenero, votos / k


def stats_entrenamiento(conn) -> dict[str, int]:
    """Contadores de tracks por clase en el conjunto de entrenamiento."""
    rows = conn.execute(
        "SELECT genero, subgenero, COUNT(*) n FROM tracks "
        "WHERE genero IS NOT NULL AND f_low IS NOT NULL AND analizado=1 "
        "GROUP BY genero, subgenero ORDER BY n DESC"
    ).fetchall()
    return {f"{r['genero']}/{r['subgenero'] or ''}": r['n'] for r in rows}
