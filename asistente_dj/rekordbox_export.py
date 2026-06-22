"""Escritura de un export XML de Rekordbox con playlists.

Genera un archivo .xml con la estructura que Rekordbox importa:
  <DJ_PLAYLISTS>
    <PRODUCT/>
    <COLLECTION>   -> un <TRACK> por canción (con Location = ruta del archivo)
    <PLAYLISTS>    -> un <NODE> playlist que referencia los TrackID
  </DJ_PLAYLISTS>

En Rekordbox: Preferences > View > Layout: activar "rekordbox xml", y en
Preferences > Advanced > rekordbox xml apuntar a este archivo. Aparece una
vista "rekordbox xml" desde donde se arrastran las playlists a la colección.

Solo escribe un archivo nuevo: no toca la base de datos de Rekordbox.
"""
from __future__ import annotations

import urllib.parse
from xml.sax.saxutils import escape


def _ruta_a_location(ruta: str) -> str:
    """'C:/Users/.../x.mp3' -> 'file://localhost/C:/Users/.../x.mp3' (URL-encoded)."""
    p = (ruta or "").replace("\\", "/")
    # quote dejando intactos los separadores y los dos puntos de la unidad
    enc = urllib.parse.quote(p, safe="/:")
    return f"file://localhost/{enc}"


def _attr(s) -> str:
    return escape(str(s if s is not None else ""), {'"': "&quot;"})


def _ruta_track(t: dict) -> str:
    """Prefiere la ruta ya archivada (ruta_destino); si el track todavía no
    se archivó, cae a la ruta original."""
    return t.get("ruta_destino") or t.get("ruta_origen") or ""


def escribir_playlist(tracks: list[dict], nombre_playlist: str, out_path: str) -> int:
    """tracks: lista de dicts con ruta_origen/ruta_destino, artista, titulo,
    bpm, key, genero, sello. Devuelve cuántos tracks se escribieron."""
    return escribir_playlists({nombre_playlist: tracks}, out_path)


def escribir_playlists(playlists: dict[str, list[dict]], out_path: str) -> int:
    """playlists: {nombre_playlist: [tracks...]}. Todas comparten una sola
    <COLLECTION> (sin duplicar tracks repetidos entre playlists) y cada una
    es un <NODE> bajo ROOT. Devuelve el total de tracks en la colección."""
    # Colección única: un TrackID por ruta de archivo (evita duplicar el
    # mismo track si aparece en más de una playlist).
    track_id_por_ruta: dict[str, int] = {}
    todos_los_tracks: list[dict] = []
    for tracks in playlists.values():
        for t in tracks:
            ruta = _ruta_track(t)
            if ruta not in track_id_por_ruta:
                track_id_por_ruta[ruta] = len(todos_los_tracks) + 1
                todos_los_tracks.append(t)

    lineas = []
    lineas.append('<?xml version="1.0" encoding="UTF-8"?>')
    lineas.append('<DJ_PLAYLISTS Version="1.0.0">')
    lineas.append('  <PRODUCT Name="Asistente DJ" Version="1.0" Company="Brian"/>')
    lineas.append(f'  <COLLECTION Entries="{len(todos_los_tracks)}">')
    for t in todos_los_tracks:
        tid = track_id_por_ruta[_ruta_track(t)]
        loc = _ruta_a_location(_ruta_track(t))
        bpm = t.get("bpm") or ""
        key = t.get("key") or ""
        lineas.append(
            f'    <TRACK TrackID="{tid}" '
            f'Name="{_attr(t.get("titulo"))}" '
            f'Artist="{_attr(t.get("artista"))}" '
            f'Genre="{_attr(t.get("genero"))}" '
            f'Label="{_attr(t.get("sello"))}" '
            f'AverageBpm="{_attr(bpm)}" '
            f'Tonality="{_attr(key)}" '
            f'Location="{_attr(loc)}"/>'
        )
    lineas.append('  </COLLECTION>')
    lineas.append('  <PLAYLISTS>')
    lineas.append(f'    <NODE Type="0" Name="ROOT" Count="{len(playlists)}">')
    for nombre_playlist, tracks in playlists.items():
        lineas.append(
            f'      <NODE Name="{_attr(nombre_playlist)}" Type="1" '
            f'KeyType="0" Entries="{len(tracks)}">')
        for t in tracks:
            tid = track_id_por_ruta[_ruta_track(t)]
            lineas.append(f'        <TRACK Key="{tid}"/>')
        lineas.append('      </NODE>')
    lineas.append('    </NODE>')
    lineas.append('  </PLAYLISTS>')
    lineas.append('</DJ_PLAYLISTS>')

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    return len(todos_los_tracks)
