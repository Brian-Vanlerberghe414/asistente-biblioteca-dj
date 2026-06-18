"""Aprendizaje de la energía según el oído del DJ.

A partir de las calificaciones manuales del DJ (energia_manual 1-10) y los
rasgos de cada track (graves, brillo, densidad, volumen, BPM, tonalidad),
ajusta por mínimos cuadrados un modelo que reproduce su percepción, y lo
aplica al resto de la biblioteca.

No reemplaza las calificaciones manuales: esas quedan como verdad.
"""
from __future__ import annotations

import json

import numpy as np

import analyzer

# Mínimo de calificaciones para entrenar con cierta confianza.
MIN_MUESTRAS = 12


def vector_features(row) -> list[float]:
    """Construye el vector de entrada del modelo desde una fila de tracks.
    row debe tener: f_loud, f_bright, f_low, f_busy, bpm, camelot, key."""
    return [
        float(row["f_loud"] or 0.0),
        float(row["f_bright"] or 0.0),
        float(row["f_low"] or 0.0),
        float(row["f_busy"] or 0.0),
        analyzer.factor_bpm(row["bpm"]),
        analyzer.factor_modo(row["camelot"], row["key"]),
    ]


def entrenar(vectores, etiquetas):
    """Ajusta coeficientes (con sesgo) por mínimos cuadrados.
    Devuelve lista de coeficientes (len = n_features + 1)."""
    A = np.array(vectores, dtype=float)
    b = np.array(etiquetas, dtype=float)
    A1 = np.hstack([A, np.ones((A.shape[0], 1))])   # término de sesgo
    coef, *_ = np.linalg.lstsq(A1, b, rcond=None)
    return [float(c) for c in coef]


def predecir(coef, vector) -> int:
    """Predice energía 1-10 a partir del vector de features."""
    v = np.array(list(vector) + [1.0], dtype=float)
    val = float(np.dot(np.array(coef, dtype=float), v))
    return int(np.clip(round(val), 1, 10))


def serializar(coef) -> str:
    return json.dumps(coef)


def deserializar(texto: str):
    try:
        return json.loads(texto)
    except Exception:
        return None
