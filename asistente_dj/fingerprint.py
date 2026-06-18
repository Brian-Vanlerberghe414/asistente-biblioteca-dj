"""Huella acústica con Chromaprint (fpcalc) y comparación de duplicados.

fpcalc es la herramienta de línea de comandos de Chromaprint. En Windows se
baja un solo binario (fpcalc.exe) de https://acoustid.org/chromaprint y se
deja en el PATH (o junto al programa). No es un paquete de pip.

La huella reconoce el MISMO track aunque cambie el formato o el bitrate: dos
codificaciones del mismo tema dan huellas casi idénticas (pocos bits distintos).
"""
from __future__ import annotations

import os
import shutil
import subprocess

import numpy as np


def _fpcalc():
    """Ubica el ejecutable fpcalc: 1) junto a este archivo, 2) en el PATH.
    Así alcanza con dejar fpcalc.exe en la carpeta del programa."""
    aqui = os.path.dirname(os.path.abspath(__file__))
    for nombre in ("fpcalc.exe", "fpcalc"):
        local = os.path.join(aqui, nombre)
        if os.path.isfile(local):
            return local
    return shutil.which("fpcalc")


def disponible() -> bool:
    exe = _fpcalc()
    if not exe:
        return False
    try:
        subprocess.run([exe, "-version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


def calcular(path, length=120):
    """Devuelve (duracion_seg, huella_str) o (None, None).
    huella_str = enteros separados por coma (formato -raw de fpcalc)."""
    exe = _fpcalc()
    if not exe:
        return None, None
    try:
        out = subprocess.run(
            [exe, "-raw", "-length", str(length), path],
            capture_output=True, text=True, timeout=180).stdout
    except Exception:
        return None, None
    dur, fp = None, None
    for line in out.splitlines():
        if line.startswith("DURATION="):
            try:
                dur = float(line.split("=", 1)[1])
            except Exception:
                pass
        elif line.startswith("FINGERPRINT="):
            fp = line.split("=", 1)[1].strip()
    if not fp:
        return None, None
    return dur, fp


def calcular_worker(path):
    """Worker para multiprocessing: devuelve (path, dur, huella_str)."""
    dur, fp = calcular(path)
    return (path, dur, fp)


def a_array(huella_str):
    """Convierte la huella de texto a array de uint32."""
    if not huella_str:
        return np.empty(0, dtype=np.uint32)
    try:
        return np.array([int(x) for x in huella_str.split(",") if x],
                        dtype=np.uint32)
    except Exception:
        return np.empty(0, dtype=np.uint32)


def bit_error_rate(a, b):
    """Fracción de bits distintos sobre el tramo solapado (0 = idéntico)."""
    n = min(len(a), len(b))
    if n == 0:
        return 1.0
    x = np.bitwise_xor(a[:n], b[:n])
    bits = int(np.unpackbits(x.view(np.uint8)).sum())
    return bits / (n * 32)


def son_duplicados(a, b, umbral=0.15):
    return bit_error_rate(a, b) < umbral
