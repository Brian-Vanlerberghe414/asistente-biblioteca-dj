"""Lectura de tags y propiedades de audio.

Estrategia resiliente:
  1. Si Mutagen está instalado (recomendado en producción), se usa para leer
     tags de todos los formatos (MP3, FLAC, M4A, AIFF, WAV...).
  2. Si no, se usa un lector ID3v2 propio y mínimo, suficiente para MP3.
     Esto permite probar el motor sin dependencias externas.
"""
from __future__ import annotations

import os
import struct
from dataclasses import dataclass

try:
    import mutagen  # type: ignore
    _HAS_MUTAGEN = True
except Exception:
    _HAS_MUTAGEN = False


@dataclass
class TrackTags:
    titulo: str = ""
    artista: str = ""
    sello: str = ""
    album: str = ""
    genero_raw: str = ""
    bpm: str = ""
    key: str = ""
    anio: str = ""
    bitrate_kbps: int | None = None      # None = desconocido
    duracion_seg: float | None = None
    ilegible: bool = False               # True = archivo dañado/no se pudo leer


def read_tags(path: str) -> TrackTags:
    """Devuelve los tags de un archivo de audio (motor que esté disponible).

    Nunca lanza excepciones: un archivo dañado o con cabecera rara no debe
    frenar el escaneo de toda la biblioteca. Si Mutagen falla, se intenta el
    lector interno; si también falla, se devuelven tags vacíos y el track
    queda marcado como ilegible (el escáner lo manda a revisión).
    """
    if _HAS_MUTAGEN:
        try:
            return _read_with_mutagen(path)
        except Exception:
            pass  # archivo dañado/raro: probamos el lector interno
    try:
        return _read_id3_minimal(path)
    except Exception:
        t = TrackTags()
        t.ilegible = True
        return t


def using_mutagen() -> bool:
    return _HAS_MUTAGEN


# ---------------------------------------------------------------------------
# Motor 1: Mutagen (producción)
# ---------------------------------------------------------------------------
def _read_with_mutagen(path: str) -> TrackTags:
    from mutagen import File as MutagenFile  # type: ignore

    audio = MutagenFile(path, easy=True)
    t = TrackTags()
    if audio is None:
        return t

    def first(key: str) -> str:
        try:
            v = audio.get(key)
            return str(v[0]) if v else ""
        except Exception:
            return ""

    t.titulo = first("title")
    t.artista = first("artist")
    t.album = first("album")
    # El sello suele venir en "organization"/"label"/"publisher" según formato
    t.sello = first("organization") or first("label") or first("publisher")
    t.genero_raw = first("genre")
    t.bpm = first("bpm")
    t.key = first("initialkey") or first("key")
    t.anio = (first("date") or first("year"))[:4]

    info = getattr(audio, "info", None)
    if info is not None:
        br = getattr(info, "bitrate", None)
        if br:
            t.bitrate_kbps = int(round(br / 1000))
        length = getattr(info, "length", None)
        if length:
            t.duracion_seg = float(length)
    return t


# ---------------------------------------------------------------------------
# Motor 2: lector ID3v2 mínimo (respaldo, solo MP3)
# ---------------------------------------------------------------------------
_TEXT_FRAMES = {
    "TIT2": "titulo",
    "TPE1": "artista",
    "TALB": "album",
    "TCON": "genero_raw",
    "TBPM": "bpm",
    "TKEY": "key",
    "TYER": "anio",
    "TDRC": "anio",
    "TPUB": "sello",
}


def _decode_text(data: bytes) -> str:
    if not data:
        return ""
    enc = data[0]
    payload = data[1:]
    try:
        if enc == 0:
            return payload.decode("latin-1").strip("\x00").strip()
        if enc == 1:
            return payload.decode("utf-16").strip("\x00").strip()
        if enc == 2:
            return payload.decode("utf-16-be").strip("\x00").strip()
        return payload.decode("utf-8").strip("\x00").strip()
    except Exception:
        return payload.decode("latin-1", "ignore").strip("\x00").strip()


def _synchsafe(b: bytes) -> int:
    return (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]


def _read_id3_minimal(path: str) -> TrackTags:
    t = TrackTags()
    try:
        with open(path, "rb") as f:
            header = f.read(10)
            if header[:3] != b"ID3":
                # Sin tag ID3: igual intentamos el bitrate
                t.bitrate_kbps = _mp3_bitrate(path)
                return t
            version_major = header[3]
            tag_size = _synchsafe(header[6:10])
            body = f.read(tag_size)

        i = 0
        while i + 10 <= len(body):
            frame_id = body[i:i + 4]
            if frame_id == b"\x00\x00\x00\x00" or not frame_id.strip():
                break
            raw_size = body[i + 4:i + 8]
            if version_major == 4:
                size = _synchsafe(raw_size)
            else:
                size = struct.unpack(">I", raw_size)[0]
            data = body[i + 10:i + 10 + size]
            fid = frame_id.decode("latin-1", "ignore")
            if fid in _TEXT_FRAMES:
                setattr(t, _TEXT_FRAMES[fid], _decode_text(data))
            i += 10 + size

        # Normalizar TCON tipo "(18)" o "Techno\x00"
        if t.genero_raw:
            t.genero_raw = t.genero_raw.replace("\x00", " ").strip()
        if t.anio:
            t.anio = t.anio[:4]
    except Exception:
        pass

    t.bitrate_kbps = _mp3_bitrate(path)
    return t


_BITRATE_TABLE = {  # MPEG1 Layer III
    1: 32, 2: 40, 3: 48, 4: 56, 5: 64, 6: 80, 7: 96, 8: 112,
    9: 128, 10: 160, 11: 192, 12: 224, 13: 256, 14: 320,
}


def _mp3_bitrate(path: str) -> int | None:
    """Lee el bitrate del primer frame MPEG-1 Layer III. Best-effort."""
    try:
        with open(path, "rb") as f:
            buf = f.read(200000)
        # Saltar tag ID3v2 si está
        start = 0
        if buf[:3] == b"ID3":
            start = 10 + _synchsafe(buf[6:10])
        j = start
        while j + 4 <= len(buf):
            if buf[j] == 0xFF and (buf[j + 1] & 0xE0) == 0xE0:
                b2 = buf[j + 2]
                br_index = (b2 >> 4) & 0x0F
                if br_index in _BITRATE_TABLE:
                    return _BITRATE_TABLE[br_index]
            j += 1
    except Exception:
        pass
    return None
