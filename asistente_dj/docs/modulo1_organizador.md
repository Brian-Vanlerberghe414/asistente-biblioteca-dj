# Módulo 1 — Organizador (motor)

> Doc de módulo. Ver `CLAUDE.md` (raíz) para la tabla de ruteo completa y
> el contexto general del proyecto.

Escanea la biblioteca, clasifica/archiva por género, analiza BPM/key/energía,
detecta duplicados, importa datos de software DJ, crea playlists inteligentes
y las exporta a Rekordbox. Motor (CLI) + GUI ya funcionando, probados contra
la biblioteca real de Brian (~1.950 tracks).

## Comandos CLI (corren desde `asistente_dj/`)

```
python cli.py scan "<carpeta de música>"      # escanear + clasificar por género
python cli.py analyze [--reset]                # BPM/key/energía (multinúcleo, ventana ~75s)
python cli.py show --limit 40                  # ver lo analizado
python cli.py resuggest                        # recalcular energía/sugerencias (rápido, sin re-analizar)
python cli.py rate "<texto>" <1-10>            # fijar energía manual (manda sobre la auto)
python cli.py calibrate [--genero G]           # aprender el oído del DJ (escucha + califica)
python cli.py generos                          # géneros del tag no reconocidos
python cli.py clean-tags [--apply]             # limpiar URLs basura de los tags
python cli.py config --biblioteca "<ruta>"     # fijar la raíz de la biblioteca del asistente
python cli.py import "<carpeta origen>"        # importar música (copia + elige género + ofrece borrar originales)
python cli.py import-rekordbox "<rekordbox.xml>"   # BPM/key exactos desde Rekordbox
python cli.py import-traktor "<collection.nml>"    # BPM/key exactos desde Traktor
python cli.py import-getsongbpm --api-key <KEY>    # BPM/key desde GetSongBPM (cobertura pobre p/ underground)
python cli.py fingerprint                      # huella acústica (Chromaprint)
python cli.py duplicates                       # detectar duplicados, sugiere cuál conservar
python cli.py playlist-create "<nombre>" --genero ... --bpm-min ...   # playlist inteligente
python cli.py playlist-list
python cli.py playlist-export "<salida.xml>" --nombre "<playlist>"    # exportar a Rekordbox
python cli.py plan / archive "<destino>" [--apply]    # plan/archivado por género
python cli.py review                           # tracks sin género (_Por revisar)
python cli.py import-serato "<carpeta Serato>"      # BPM/key/género desde la base binaria de Serato
```

## Arquitectura (archivos en `asistente_dj/`)

- `cli.py` — punto de entrada; todos los comandos (argparse).
- `config.py` — árbol de géneros + alias de Beatport + umbrales.
- `db.py` — esquema SQLite, migración suave de columnas, limpieza de basura (._*).
- `scanner.py` — recorrido de carpetas, lectura de tags, clasificación, archivado.
- `tags.py` — lectura de tags (Mutagen; respaldo lector ID3 interno).
- `classifier.py` — mapea el género del tag al árbol.
- `analyzer.py` — análisis de audio (BPM, key, energía, rasgos) con ffmpeg+numpy;
  ventana parcial, multinúcleo; sugerencia de género; energía combinada.
- `archiver.py` — plan y copia por género.
- `intake.py` — procesar un archivo nuevo (usado por `import`).
- `settings.py` — ajustes persistentes (raíz de la biblioteca) en `asistente_config.json`.
- `tagclean.py` — limpieza de URLs basura en tags.
- `fingerprint.py` — huella Chromaprint (fpcalc) + comparación por bit-error-rate.
- `calibration_model.py` — regresión que aprende la energía del oído del DJ.
- `rekordbox_xml.py` / `traktor_nml.py` — parsers de import de software DJ.
- `rekordbox_export.py` — escribe XML de Rekordbox con playlists.
- `getsongbpm.py` — cliente de la API pública GetSongBPM.
- `serato_db.py` — parser binario de la base de datos de Serato (database V2).
- `genre_profiles.py` — perfiles de ~30 géneros de la taxonomía Beatport
  (`data/generos_electronicos_beatport.json`); motor de sugerencia de género por
  BPM + rasgos acústicos (graves/brillo/densidad), usado como fallback en
  `analyzer.suggest_genre` cuando no hay tag ni match en la Biblioteca Confiable.

**Sin documentar / legacy** (no descriptos en ningún lado todavía, no asumir
su propósito sin leerlos primero): `artist_db.py`, `lookup_genre.py`.

## Stack y por qué

- **Python** de punta a punta (donde viven las librerías de audio).
- **Interfaz: PySide6 (Qt)** — ver `docs/gui.md`.
- **Audio: ffmpeg + numpy** (NO Essentia: imposible de instalar fácil en Windows;
  ffmpeg+numpy se instala sin dolor y rinde igual para BPM/key/energía).
- **SQLite** local. **Mutagen** para tags. **Chromaprint/fpcalc** para duplicados.

## Decisiones de diseño clave

- **Almacenamiento físico por Género/Subgénero**; un track = una carpeta. La
  organización "dinámica" (filtros por BPM/key/energía/etc.) son vistas, no mueven archivos.
- **Árbol de géneros** (en `config.py`): Techno (Peak Time - Driving, Hard
  Techno, Raw - Deep - Hypnotic, Industrial, Minimal - Deep Tech), House
  (Progressive, Deep, Tech, Jackin, Bass, Afro, Organic, Electro), Trance
  (Main Floor, Tech, Progressive, Psy-Trance), Indie Dance, Big Room,
  Melodic House & Techno (género propio, sin subgéneros).
- **"Melodic House" y "Melodic Techno" eliminados como subgéneros propios
  (sesión 2026-06-22)**: vivían como subgénero de House y de Techno
  respectivamente, pero en la práctica sonaban igual y se confundían entre
  sí todo el tiempo. Se fusionaron en el género ya existente "Melodic House
  & Techno" (sin subgénero) — los alias en `config.GENRE_ALIASES` que antes
  apuntaban a `("Techno","Melodic Techno")`/`("House","Melodic House")`
  ahora apuntan a `("Melodic House & Techno", None)`. Se migraron los datos
  ya clasificados (local: 6 tracks de Brian con el subgénero viejo, ahora
  en "Melodic House & Techno"); la Biblioteca Confiable en Supabase
  (`biblioteca_tracks`/`mi_biblioteca`/`artistas_generos`) ya estaba limpia
  — Beatport nunca tuvo esa división como subgénero separado, así que solo
  afectaba a la clasificación local de Brian (tag/audio).
- **Fuente de BPM/key, prioridad:** Rekordbox/Traktor (exacto) > Beatport API
  (cuando haya credenciales) > GetSongBPM > análisis de audio propio (fallback,
  con errores de octava). El BPM del tag se ignora si es "0" o no numérico.
- **Energía** = automático + ajuste manual + aprendizaje:
  - Auto por defecto: **90% acústica + 10% tonalidad + 10% BPM** (pesos relativos),
    rankeado por percentiles 1-10 sobre la biblioteca.
  - `rate` fija energía manual (manda siempre).
  - `calibrate` ("Calibrar Energía"): el DJ escucha el momento más intenso y
    califica 1-10 dentro de un mismo género; una regresión aprende su percepción
    (rasgos: graves/brillo/densidad/volumen + BPM + tonalidad) y la aplica a todo.
    Mínimo 12 calificaciones. Modelo en tabla `modelo_energia`.
- **Importar música** (reemplaza la vigilancia automática): `import` copia desde
  una carpeta (recursivo) a la biblioteca; si no reconoce el género, lo PREGUNTA
  con lista numerada (reproduce el pico); al final ofrece borrar originales.
- **Identificación de género — orden real del flujo** (en `scanner.scan()`):
  1. Leer tag → 2. Clasificar por tag (`classifier.classify_con_filtro`) →
  2.5. **Biblioteca Confiable (Supabase)**: si hay match por artista+título+
  duración (±2s), tiene prioridad sobre el tag (ver `docs/modulo3_nube_backend.md`)
  → 3. Analizar audio (comando `analyze`, separado) → 4. Si sigue sin género:
  sugerencia por audio (`analyzer.suggest_genre` → `genre_profiles.py`, ver
  abajo) → 5. Revisión manual (GUI/CLI) → 6. Guardar en SQLite. Las
  clasificaciones con `confianza in ("manual", "supabase")` nunca se
  sobreescriben en escaneos futuros (protección de fuentes de alta confianza).
- **Sugerencia de género por audio (`genre_profiles.py`)**: heurística
  probabilística (no determinista) que puntúa ~30 perfiles de la taxonomía
  Beatport (`data/generos_electronicos_beatport.json`) contra BPM + rasgos
  acústicos (graves/sub-bass, brillo espectral, densidad rítmica, energía).
  El BPM pesa más que el resto; fuera del rango de un perfil el score decae
  rápido (6 BPM de tolerancia). Los rasgos acústicos crudos se normalizan por
  PERCENTILES dentro de la propia biblioteca antes de comparar contra la
  escala 1-5 del JSON (si no, sesga sistemáticamente hacia los géneros de
  energía baja). Es solo un fallback de orden, no reemplaza al tag; la
  corrección manual siempre tiene la última palabra.
- **Rekordbox:** import (BPM/key + verificación) y export de playlists. Nunca
  modifica la base de Rekordbox; solo lee XML y escribe un XML nuevo.
- **Rutas correctas tras archivar (sesión 2026-06-22):** `archiver.py` solo
  COPIA los archivos (nunca borra el original), así que mientras el DJ no
  borre los originales a mano, sus playlists de Rekordbox no se rompen. El
  problema aparece cuando el DJ borra los originales para no duplicar
  espacio. Solución: `import-rekordbox` ahora también lee `<PLAYLISTS>`
  del XML (`rekordbox_xml.parse_playlists()`) y crea esas playlists
  localmente (`reglas={"ids":[...]}`, mismo formato que usa la GUI),
  matcheando cada track por el mismo criterio ya usado para BPM/key (ruta
  exacta → nombre de archivo → artista+título). `rekordbox_export.py`
  ahora prefiere `ruta_destino` (la ruta ya archivada) sobre `ruta_origen`
  al exportar — antes siempre usaba `ruta_origen`, lo cual rompía
  cualquier playlist exportada después de archivar. `playlist-export
  --todas` exporta todas las playlists guardadas a un solo XML (una sola
  `<COLLECTION>` compartida, sin duplicar tracks repetidos entre
  playlists). Flujo completo: el DJ exporta su colección+playlists desde
  Rekordbox → `import-rekordbox` (trae BPM/key Y crea las playlists) →
  el DJ archiva su biblioteca como siempre → `playlist-export --todas` →
  arrastra esa vista a su colección real en Rekordbox, ya con las rutas
  nuevas. `_tracks_por_reglas` (en `cli.py`) ahora soporta tanto
  `reglas={"ids":[...]}` (preservando el orden) como el formato de
  filtros de siempre.

## Pendiente de conectar a la GUI

El motor de Serato, borrado de duplicados, y sugerencia automática de género
ya funcionan por CLI pero les falta UI — el detalle completo (qué falta
exactamente en cada caso) vive en `docs/gui.md` (no se duplica acá).

## Esquema de base de datos

Ver `docs/base_de_datos.md` (transversal a los 3 módulos).
