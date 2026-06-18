"""Lectura del export NML de Traktor (Native Instruments).

Traktor: File → Export... o el archivo collection.nml. Es XML.
Estructura relevante:
  <NML VERSION="19">
    <COLLECTION ENTRIES="N">
      <ENTRY ARTIST="..." TITLE="...">
        <LOCATION DIR="/:Users/:Brian/:Music/:" FILE="track.mp3" VOLUME="C:"/>
        <INFO GENRE="..." KEY="Am" .../>
        <TEMPO BPM="128.000000" .../>
        <MUSICAL_KEY VALUE="21"/>
      </ENTRY>
    </COLLECTION>
  </NML>

Extraemos: ruta, artista, título, BPM (exacto), key, género.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

# MUSICAL_KEY VALUE (0-23) de Traktor -> nombre. Best-effort (0-11 mayor, 12-23 menor).
_NOTAS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


@dataclass
class TraktorTrack:
    location: str = ""
    artista: str = ""
    titulo: str = ""
    bpm: str = ""
    key: str = ""
    genero: str = ""


def _location_a_ruta(loc_el) -> str:
    """Reconstruye la ruta desde <LOCATION VOLUME DIR FILE>.
    Traktor separa con '/:'. Ej: VOLUME='C:' DIR='/:Users/:Brian/:Music/:' FILE='x.mp3'."""
    if loc_el is None:
        return ""
    volume = loc_el.get("VOLUME", "") or ""
    dir_ = loc_el.get("DIR", "") or ""
    file_ = loc_el.get("FILE", "") or ""
    dir_norm = dir_.replace("/:", "/")
    ruta = f"{volume}{dir_norm}{file_}"
    return ruta


def _key_desde_musical(value: str) -> str:
    try:
        v = int(value)
    except Exception:
        return ""
    if 0 <= v <= 11:
        return _NOTAS[v]
    if 12 <= v <= 23:
        return _NOTAS[v - 12] + "m"
    return ""


def parse(nml_path: str):
    """Devuelve (lista de TraktorTrack, version)."""
    tree = ET.parse(nml_path)
    root = tree.getroot()
    version = root.get("VERSION", "")
    tracks = []
    coll = root.find("COLLECTION")
    if coll is None:
        return tracks, version
    for e in coll.findall("ENTRY"):
        info = e.find("INFO")
        tempo = e.find("TEMPO")
        mkey = e.find("MUSICAL_KEY")
        bpm = ""
        if tempo is not None and tempo.get("BPM"):
            # Traktor escribe "128.000000"; lo dejamos con 1-2 decimales
            try:
                bpm = f"{float(tempo.get('BPM')):.2f}".rstrip("0").rstrip(".")
            except Exception:
                bpm = tempo.get("BPM")
        key = (info.get("KEY") if info is not None else "") or ""
        if not key and mkey is not None:
            key = _key_desde_musical(mkey.get("VALUE", ""))
        tracks.append(TraktorTrack(
            location=_location_a_ruta(e.find("LOCATION")),
            artista=e.get("ARTIST", ""),
            titulo=e.get("TITLE", ""),
            bpm=bpm,
            key=key,
            genero=(info.get("GENRE") if info is not None else "") or "",
        ))
    return tracks, version
