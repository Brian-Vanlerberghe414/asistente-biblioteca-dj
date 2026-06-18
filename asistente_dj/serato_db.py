"""Lectura de la base de datos de Serato (database V2).

Serato almacena su colección en '<raíz de música>/_Serato_/database V2'.
Windows típico: C:\\Users\\<usuario>\\Music\\_Serato_\\database V2

Formato binario propietario (big-endian):
  [4 bytes tipo ASCII][4 bytes longitud BE][N bytes de datos]

Chunks de nivel superior:
  vrsn  → versión del programa (string UTF-16BE)
  otrk  → un track; contiene sub-chunks con los metadatos

Sub-chunks dentro de 'otrk':
  ptrk  → ruta del archivo (string UTF-16BE)
  tart  → artista          (string UTF-16BE)
  tsng  → título           (string UTF-16BE)
  tbpm  → BPM              (float 32-bit BE; o string UTF-16BE en versiones viejas)
  tkey  → tonalidad        (string UTF-16BE, ej. "Am", "C")
  tgen  → género           (string UTF-16BE)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class SeratoTrack:
    location: str = ""
    artista:  str = ""
    titulo:   str = ""
    bpm:      str = ""
    key:      str = ""
    genero:   str = ""


def _chunks(data: bytes) -> list[tuple[str, bytes]]:
    """Parsea una secuencia de chunks [tipo 4B][longitud 4B BE][datos]."""
    result = []
    pos = 0
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4].decode("ascii", errors="replace")
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        end = pos + 8 + length
        result.append((tag, data[pos + 8:end]))
        pos = end
    return result


def _utf16(data: bytes) -> str:
    """Decodifica string UTF-16 big-endian (formato estándar de Serato)."""
    try:
        return data.decode("utf-16-be", errors="replace").rstrip("\x00")
    except Exception:
        return ""


def _parse_bpm(data: bytes) -> str:
    """BPM puede venir como float IEEE 754 4B BE o como string UTF-16BE."""
    if len(data) == 4:
        try:
            val = struct.unpack(">f", data)[0]
            if 0 < val < 500:
                return f"{val:.2f}".rstrip("0").rstrip(".")
        except Exception:
            pass
    # Versiones antiguas lo guardan como string
    s = _utf16(data).strip()
    try:
        val = float(s)
        if 0 < val < 500:
            return f"{val:.2f}".rstrip("0").rstrip(".")
    except (ValueError, TypeError):
        pass
    return s


def _parse_track(otrk_data: bytes) -> SeratoTrack:
    t = SeratoTrack()
    for tag, val in _chunks(otrk_data):
        if tag == "ptrk":
            t.location = _utf16(val)
        elif tag == "tart":
            t.artista = _utf16(val)
        elif tag == "tsng":
            t.titulo = _utf16(val)
        elif tag == "tbpm":
            t.bpm = _parse_bpm(val)
        elif tag == "tkey":
            t.key = _utf16(val)
        elif tag == "tgen":
            t.genero = _utf16(val)
    return t


def parse(db_path: str) -> tuple[list[SeratoTrack], str]:
    """Lee el archivo 'database V2' de Serato.
    Devuelve (lista de SeratoTrack, version_string)."""
    with open(db_path, "rb") as f:
        data = f.read()

    version = ""
    tracks = []
    for tag, val in _chunks(data):
        if tag == "vrsn":
            version = _utf16(val).strip()
        elif tag == "otrk":
            t = _parse_track(val)
            if t.location:
                tracks.append(t)
    return tracks, version
