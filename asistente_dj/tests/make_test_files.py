"""Genera MP3 de prueba con tags ID3v2.3 reales (incluye un frame MPEG
para que el bitrate sea detectable). Solo para probar el motor sin música real.
"""
import os
import struct
import sys

# bitrate index MPEG1 L3: 9=128, 13=256, 14=320
_BR_INDEX = {128: 9, 192: 11, 256: 13, 320: 14}


def _frame(frame_id: bytes, text: str) -> bytes:
    data = b"\x00" + text.encode("latin-1", "ignore")  # enc 0 = latin1
    return frame_id + struct.pack(">I", len(data)) + b"\x00\x00" + data


def _synchsafe(n: int) -> bytes:
    return bytes([(n >> 21) & 0x7F, (n >> 14) & 0x7F, (n >> 7) & 0x7F, n & 0x7F])


def _id3(tags: dict) -> bytes:
    frames = b""
    mapping = {"titulo": b"TIT2", "artista": b"TPE1", "album": b"TALB",
               "genero": b"TCON", "bpm": b"TBPM", "key": b"TKEY",
               "anio": b"TYER", "sello": b"TPUB"}
    for k, fid in mapping.items():
        if tags.get(k):
            frames += _frame(fid, str(tags[k]))
    header = b"ID3" + bytes([3, 0]) + b"\x00" + _synchsafe(len(frames))
    return header + frames


def _mpeg_frame(bitrate: int) -> bytes:
    br = _BR_INDEX.get(bitrate, 14)
    b2 = (br << 4) | 0x00  # samplerate 44100 -> 00, no padding
    return bytes([0xFF, 0xFB, b2, 0x00]) + b"\x00" * 400


TRACKS = [
    dict(artista="Tale Of Us", titulo="Nova", sello="Afterlife",
         genero="Melodic Techno", bpm="122", key="Am", anio="2023", bitrate=320),
    dict(artista="Mathame", titulo="Nibiru", sello="Afterlife",
         genero="Melodic House & Techno", bpm="123", key="Fm", anio="2022", bitrate=320),
    dict(artista="Charlotte de Witte", titulo="Doppler", sello="KNTXT",
         genero="Techno (Peak Time / Driving)", bpm="132", key="Gm", anio="2024", bitrate=320),
    dict(artista="Boris Brejcha", titulo="Gravity", sello="Ultra",
         genero="Minimal / Deep Tech", bpm="126", key="Cm", anio="2021", bitrate=256),
    dict(artista="Fisher", titulo="Losing It", sello="Catch & Release",
         genero="Tech House", bpm="125", key="Bm", anio="2018", bitrate=320),
    dict(artista="Eelke Kleijn", titulo="Lonely Heart", sello="DAYS like NIGHTS",
         genero="Progressive House", bpm="122", key="Dm", anio="2023", bitrate=320),
    dict(artista="Joel Corry", titulo="Sorry", sello="Asylum",
         genero="Bass House", bpm="126", key="Am", anio="2019", bitrate=128),  # baja calidad
    dict(artista="Armin van Buuren", titulo="Blah Blah Blah", sello="Armada",
         genero="Trance", bpm="135", key="Em", anio="2018", bitrate=320),
    dict(artista="Vini Vici", titulo="Great Spirit", sello="Iboga",
         genero="Psy-Trance", bpm="140", key="Fm", anio="2017", bitrate=320),
    dict(artista="Some Artist", titulo="Mystery Track", sello="White Label",
         genero="Future Bass", bpm="150", key="Gm", anio="2020", bitrate=320),  # no reconocido
    dict(artista="Unknown DJ", titulo="Untagged Promo", sello="",
         genero="", bpm="", key="", anio="", bitrate=256),  # sin género
]


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for i, t in enumerate(TRACKS, 1):
        fname = f"{i:02d}_{t['artista']} - {t['titulo']}.mp3".replace("/", "_")
        path = os.path.join(out_dir, fname)
        with open(path, "wb") as f:
            f.write(_id3(t))
            f.write(_mpeg_frame(t["bitrate"]))
    print(f"Generados {len(TRACKS)} archivos de prueba en {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "test_audio")
