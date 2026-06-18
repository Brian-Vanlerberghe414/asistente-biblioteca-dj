# Asistente DJ — Módulo 1 (prototipo del motor)

Primer prototipo del organizador de biblioteca: escanea una carpeta de música,
lee los tags, clasifica cada track según el árbol de géneros de Brian y los
**copia** a una estructura `Género/Subgénero`. Por consola, sin interfaz todavía.

> Los archivos originales nunca se mueven ni se modifican: el programa **copia**.

## Instalación

Requiere Python 3.10+.

```bash
pip install -r requirements.txt
```

Mutagen es opcional pero recomendado (lectura de tags en todos los formatos).
Sin Mutagen, el motor usa un lector ID3 interno que funciona solo con MP3.

## Uso

```bash
# 1) Escanear una carpeta (guarda todo en la base SQLite)
python cli.py scan "C:\ruta\a\mi\musica"

# 2) Ver qué tracks quedaron a revisar (género no reconocido)
python cli.py review

# 3) Ver el plan de archivado SIN copiar nada (simulación)
python cli.py plan

# 4) Analizar el audio (BPM, key, energía) y sugerir género a los sin tag
python cli.py analyze
#    Probá primero con pocos:  python cli.py analyze --limit 20
#    Requiere numpy + ffmpeg instalados.

# 5) Ver los géneros del tag que no se reconocieron (por frecuencia)
python cli.py generos

# 5b) Importar BPM y key EXACTOS desde Rekordbox (la fuente precisa)
#     En Rekordbox: File > Export Collection in xml format (modo Export)
python cli.py import-rekordbox "C:\ruta\rekordbox.xml"
#     Traktor (archivo collection.nml):
python cli.py import-traktor "C:\ruta\collection.nml"

# 5b-bis) Traer BPM/key desde la API pública GetSongBPM (gratis, con API key)
#     Conseguí tu key en https://getsongbpm.com/api (requiere un backlink al sitio)
python cli.py import-getsongbpm --api-key TU_API_KEY --limit 20

# 5c) Corregir a mano la energía de un track (tu valor manda siempre)
python cli.py rate "Tell Me Why" 4

# 5d) Playlists inteligentes (por filtros) y export a Rekordbox
python cli.py playlist-create "Melodic 120-125" --genero Techno --subgenero "Melodic Techno" --bpm-min 120 --bpm-max 125 --energia-min 6
python cli.py playlist-list
python cli.py playlist-export "C:\ruta\mi_playlist.xml" --nombre "Melodic 120-125"
#   O export directo por filtros, sin guardar:
python cli.py playlist-export "C:\ruta\peaktime.xml" --como "Peak Time" --genero Techno --bpm-min 128

# 5e) Detectar duplicados por huella acústica (necesita fpcalc de Chromaprint)
#     Bajá fpcalc.exe de https://acoustid.org/chromaprint y dejalo en el PATH
python cli.py fingerprint        # calcula la huella de cada track (multinúcleo)
python cli.py duplicates         # agrupa repetidos y sugiere cuál conservar

# 5f) Configurar (una vez) la carpeta-biblioteca del asistente
python cli.py config --biblioteca "C:\ruta\Biblioteca del Asistente"

# 5f-bis) Limpiar tags basura (URLs de sitios de descarga en título/artista/sello/género)
python cli.py clean-tags                       # vista previa (no cambia nada)
python cli.py clean-tags --apply               # aplica en la base
python cli.py clean-tags --apply --escribir-archivos   # además reescribe los tags del archivo

# 5g) Importar música: copia desde una carpeta a la biblioteca, ordenada por género
#     (recursivo; pregunta el género cuando no lo reconoce; al final ofrece borrar originales)
python cli.py import "C:\ruta\carpeta con musica nueva"

# 6) Archivar de verdad (copia a la carpeta destino)
python cli.py archive "C:\ruta\Biblioteca Ordenada" --apply
#    Sin --apply es solo simulación.
```

La base de datos se guarda como `asistente_dj.db` (cambialo con `--db`).

## Qué hace hoy

- Recorre la carpeta (mp3, wav, aiff, flac, m4a, aac, ogg).
- Lee título, artista, sello, BPM, key, año, género y bitrate.
- Clasifica el género al árbol definido, entendiendo nombres de Beatport
  (ej. `Melodic House & Techno` → `Techno/Melodic Techno`,
  `Techno (Peak Time / Driving)` → `Techno/Peak Time - Driving`).
- Detecta baja calidad (bitrate < 256 kbps en formatos con pérdida).
- Manda a `_Por revisar` los de género dudoso o desconocido.
- Copia todo a `Género/Subgénero`, renombrando a `Artista - Título.ext`.
- **Analiza el audio** (`analyze`): calcula BPM (±0.3 en pruebas), key con
  notación Camelot y energía 1-10, usando ffmpeg + numpy (sin Essentia).
- Para tracks **sin tag de género**, sugiere un género por rangos de BPM/energía
  (orientativo, para confirmar manualmente).

## Todavía NO hace (próximas etapas)

- Detección de duplicados por huella acústica (Chromaprint).
- Carpeta de ingreso con vigilancia automática.
- Playlists inteligentes y exportación a Rekordbox (XML).
- Módulo de descubrimiento (charts de Beatport) y creador de sets.
- Interfaz gráfica (PySide6).

## Archivos

- `config.py` — árbol de géneros, alias de Beatport, umbrales de calidad.
- `tags.py` — lectura de tags (Mutagen o respaldo ID3 interno).
- `analyzer.py` — análisis de audio (BPM, key, energía) y sugerencia de género.
- `classifier.py` — mapeo de género del tag al árbol.
- `db.py` — esquema y acceso a SQLite.
- `scanner.py` — recorrido de la carpeta + guardado.
- `archiver.py` — plan y copia por género.
- `cli.py` — comandos de consola.
- `tests/make_test_files.py` — genera MP3 de prueba con tags.
