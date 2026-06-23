"""Tests de rekordbox_export.py: preferencia de ruta_destino sobre
ruta_origen, y que escribir_playlists no duplique tracks compartidos entre
playlists (regresión de la sesión de "rutas correctas tras archivar")."""
import xml.etree.ElementTree as ET

import rekordbox_export as rb


def test_ruta_track_prefiere_destino():
    t = {"ruta_origen": "C:/Musica/a.mp3", "ruta_destino": "C:/Biblioteca/Techno/a.mp3"}
    assert rb._ruta_track(t) == "C:/Biblioteca/Techno/a.mp3"


def test_ruta_track_cae_a_origen_si_no_esta_archivado():
    t = {"ruta_origen": "C:/Musica/a.mp3", "ruta_destino": None}
    assert rb._ruta_track(t) == "C:/Musica/a.mp3"


def test_escribir_playlist_un_track(tmp_path):
    tracks = [{"ruta_origen": "C:/Musica/a.mp3", "ruta_destino": None,
               "artista": "A", "titulo": "T", "bpm": "120", "key": "Am",
               "genero": "Techno", "sello": ""}]
    salida = tmp_path / "out.xml"
    n = rb.escribir_playlist(tracks, "Mi Playlist", str(salida))
    assert n == 1
    assert salida.exists()


def test_escribir_playlists_no_duplica_tracks_compartidos(tmp_path):
    """Si el mismo track aparece en dos playlists, la <COLLECTION> debe
    tener una sola entrada para él (no duplicarlo)."""
    track_a = {"ruta_origen": "C:/Musica/a.mp3", "ruta_destino": None,
               "artista": "A", "titulo": "T", "bpm": "120", "key": "Am",
               "genero": "Techno", "sello": ""}
    track_b = {"ruta_origen": "C:/Musica/b.mp3", "ruta_destino": None,
               "artista": "B", "titulo": "U", "bpm": "124", "key": "Gm",
               "genero": "House", "sello": ""}
    salida = tmp_path / "out.xml"
    total = rb.escribir_playlists(
        {"Playlist 1": [track_a, track_b], "Playlist 2": [track_b, track_a]},
        str(salida),
    )
    assert total == 2  # 2 tracks únicos, no 4

    root = ET.parse(salida).getroot()
    assert len(root.find("COLLECTION").findall("TRACK")) == 2
    nodos = root.find("PLAYLISTS").find("NODE").findall("NODE")
    assert len(nodos) == 2
    for nodo in nodos:
        assert len(nodo.findall("TRACK")) == 2


def test_escribir_playlists_orden_se_preserva(tmp_path):
    track_a = {"ruta_origen": "C:/a.mp3", "ruta_destino": None, "artista": "A",
               "titulo": "A", "bpm": "120", "key": "", "genero": "", "sello": ""}
    track_b = {"ruta_origen": "C:/b.mp3", "ruta_destino": None, "artista": "B",
               "titulo": "B", "bpm": "120", "key": "", "genero": "", "sello": ""}
    salida = tmp_path / "out.xml"
    rb.escribir_playlists({"P": [track_b, track_a]}, str(salida))

    root = ET.parse(salida).getroot()
    id_por_nombre = {
        t.get("Name"): t.get("TrackID") for t in root.find("COLLECTION").findall("TRACK")
    }
    nodo = root.find("PLAYLISTS").find("NODE").find("NODE")
    keys_en_orden = [tr.get("Key") for tr in nodo.findall("TRACK")]
    assert keys_en_orden == [id_por_nombre["B"], id_por_nombre["A"]]
