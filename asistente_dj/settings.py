"""Ajustes persistentes del asistente (archivo JSON junto al programa).

Guarda, entre otras cosas, la RAÍZ de la biblioteca del asistente: la carpeta
donde el programa copia y organiza la música por género. El usuario la elige
una vez (al instalar) y queda registrada acá.
"""
from __future__ import annotations

import json
import os

_ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "asistente_config.json")


def cargar() -> dict:
    try:
        with open(_ARCHIVO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar(d: dict) -> None:
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def get(clave, default=None):
    return cargar().get(clave, default)


def set_(clave, valor) -> None:
    d = cargar()
    d[clave] = valor
    guardar(d)
