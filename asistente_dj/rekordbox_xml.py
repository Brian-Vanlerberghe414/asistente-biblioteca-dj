"""Lectura del export XML de Rekordbox (solo lectura, cero riesgo).

Rekordbox: menú File → "Export Collection in xml format".
El XML tiene un <COLLECTION> con un <TRACK> por canción, con atributos como:
  Name (título), Artist, AverageBpm, Tonality (key), Location (ruta del archivo),
  Genre, Label, etc.

Este módulo extrae lo que nos importa: ruta, artista, título, BPM exacto y key.
"""
from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class RBTrack:
    location: str = ""    # ruta de archivo ya decodificada
    artista: str = ""
    titulo: str = ""
    bpm: str = ""         # AverageBpm (ej. "124.00")
    key: str = ""         # Tonality (ej. "Am")
    genero: str = ""
    sello: str = ""
    track_id: str = ""    # TrackID de Rekordbox (clave usada en <PLAYLISTS>)


def _location_a_ruta(loc: str) -> str:
    """Convierte 'file://localhost/C:/.../x.mp3' en 'C:/.../x.mp3' (decodificada)."""
    if not loc:
        return ""
    s = loc
    for pre in ("file://localhost/", "file://localhost", "file://", "file:"):
        if s.startswith(pre):
            s = s[len(pre):]
            break
    s = urllib.parse.unquote(s)
    # En Windows queda como '/C:/...'; le sacamos la barra inicial
    if len(s) >= 3 and s[0] == "/" and s[2] == ":":
        s = s[1:]
    return s


def parse(xml_path: str):
    """Devuelve (lista de RBTrack, version_producto)."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    producto = root.find("PRODUCT")
    version = producto.get("Version", "") if producto is not None else ""
    tracks = []
    coll = root.find("COLLECTION")
    if coll is None:
        return tracks, version
    for t in coll.findall("TRACK"):
        # Preferir el BPM del beat grid (<TEMPO>) sobre AverageBpm
        tempo = t.find("TEMPO")
        bpm = (tempo.get("Bpm", "") if tempo is not None else "") or t.get("AverageBpm", "")
        tracks.append(RBTrack(
            location=_location_a_ruta(t.get("Location", "")),
            artista=t.get("Artist", ""),
            titulo=t.get("Name", ""),
            bpm=bpm,
            key=t.get("Tonality", ""),
            genero=t.get("Genre", ""),
            sello=t.get("Label", ""),
            track_id=t.get("TrackID", ""),
        ))
    return tracks, version


def parse_playlists(xml_path: str) -> list[dict]:
    """Devuelve las playlists del XML: [{"nombre": ..., "track_ids_rb": [...]},...].
    Ignora los nodos Type="0" (carpetas, solo sirven para anidar) y solo
    devuelve los nodos Type="1" (playlists reales), con el camino de
    carpetas en el nombre si están anidadas (ej. "Sets 2024/Warmup") para
    evitar colisiones de nombre."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    playlists_root = root.find("PLAYLISTS")
    if playlists_root is None:
        return []

    resultado = []

    def _recorrer(nodo, camino):
        for hijo in nodo.findall("NODE"):
            nombre = hijo.get("Name", "")
            if hijo.get("Type") == "0":
                _recorrer(hijo, camino + [nombre] if nombre and nombre != "ROOT" else camino)
            else:
                track_ids = [tr.get("Key", "") for tr in hijo.findall("TRACK")]
                nombre_completo = "/".join(camino + [nombre]) if camino else nombre
                resultado.append({"nombre": nombre_completo, "track_ids_rb": track_ids})

    raiz = playlists_root.find("NODE")
    if raiz is not None:
        _recorrer(raiz, [])
    return resultado
