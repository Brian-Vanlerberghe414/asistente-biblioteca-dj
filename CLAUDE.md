# Asistente de Biblioteca DJ — contexto del proyecto

> Archivo de memoria para Claude Code. Resume QUÉ es el proyecto, su estado,
> cómo correrlo, la arquitectura y las decisiones tomadas, para continuar sin
> perder contexto. El detalle exhaustivo (historia y decisiones) está en
> `Concepto - Asistente de Biblioteca DJ.md` (mismo directorio). El uso de cada
> comando está en `asistente_dj/README.md`.

## Qué es

Herramienta para DJs de música electrónica (Brian + colegas) con dos módulos:
1. **Organizador** (Módulo 1): escanea la biblioteca, clasifica/archiva por
   género, analiza BPM/key/energía, detecta duplicados, importa datos de
   software DJ, crea playlists inteligentes y las exporta a Rekordbox.
2. **Descubrimiento** (Módulo 2, PENDIENTE): charts de Beatport, seguimiento
   de novedades, preview de YouTube, lista de "para conseguir".

Audiencia: no solo Brian; pensado para que lo usen otros DJs (cada uno con su
biblioteca y su modelo de energía aprendido).

## Estado actual

**Módulo 1: motor (CLI) + GUI en PySide6 ya funcionando, ambos probados contra
la biblioteca real de Brian (~1.950 tracks).** La GUI ([asistente_dj/gui/](asistente_dj/gui/),
arranca con `python app.py`) ya tiene: grilla de tracks editable, árbol de
géneros navegable, reproductor con cola y shuffle inteligente (BPM/armónico),
panel de detalle, filtros (texto/BPM/key/energía), selector de energía manual,
import de carpetas, export de playlists a Rekordbox. Quedan sin conectar a la
GUI (aunque el motor ya existe y funciona por CLI): tab de Artistas
(`artistas_widget.py`), import de Serato, borrado asistido de duplicados, y
sugerencia automática de género para "_Por revisar" (hoy es CLI-only vía
`analyze`/`resuggest`). El Módulo 2 (Descubrimiento) no está empezado.

## Cómo correrlo

Requisitos: Python 3.10+, `pip install -r asistente_dj/requirements.txt`
(numpy, mutagen). Externos opcionales: **ffmpeg** (análisis de audio, comando
`analyze`/`calibrate`) y **fpcalc** de Chromaprint (duplicados). En Windows,
dejar `fpcalc.exe` dentro de `asistente_dj/`.

Todos los comandos se corren desde `asistente_dj/`:

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
python cli.py biblioteca estado|agregar|listar      # Biblioteca Confiable (Supabase) — fuente prioritaria de género
python cli.py config --supabase-url URL --supabase-key KEY   # credenciales de Supabase
python cli.py charts-generos                        # Módulo 2: slugs de género disponibles en Beatport
python cli.py charts-scrape [--genero SLUG]          # Módulo 2: scrapear Top 100 (global y/o por género)
python cli.py charts-show [--genero SLUG] [--top N]  # Módulo 2: ver el chart guardado
python cli.py charts-novedades [--genero SLUG]       # Módulo 2: tracks nuevos desde el último scrape
python cli.py conseguir agregar|listar|marcar|quitar # Módulo 2: lista de "para conseguir"
```

Para la GUI (PySide6), desde `asistente_dj/`:

```
python app.py
```

## Arquitectura (carpeta `asistente_dj/`)

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
- `biblioteca_confiable.py` — cliente de Supabase ("Biblioteca Confiable"); fuente
  prioritaria de género (ver Decisiones de diseño). Opcional y a prueba de fallos:
  si no hay credenciales o falla la red, no rompe nada y el flujo sigue por tags.
- `charts_beatport.py` — Módulo 2: scraper con Playwright de los charts Top
  100 de Beatport (global y por género), sin credenciales. Diseño con
  backend intercambiable: cuando haya OAuth de la API oficial, se reemplaza
  sin tocar `cli.py` (mismo contrato de salida: listas de dicts).
- `genre_profiles.py` — perfiles de ~30 géneros de la taxonomía Beatport
  (`data/generos_electronicos_beatport.json`); motor de sugerencia de género por
  BPM + rasgos acústicos (graves/brillo/densidad), usado como fallback en
  `analyzer.suggest_genre` cuando no hay tag ni match en la Biblioteca Confiable.
- `app.py` — punto de entrada de la GUI (PySide6).
- `gui/` — interfaz gráfica: `main_window.py` (ventana principal), `organizador.py`
  (grilla + reproductor con cola/shuffle inteligente), `track_model.py` (modelo
  de tabla editable), `detalle_panel.py` (panel de detalle), `track_table_view.py`,
  `waveform_widget.py`, `theme.py`, delegates de edición inline (género, BPM,
  artista). `artistas_widget.py` y sus workers existen pero todavía no están
  conectados a la ventana principal.
- `tests/make_test_files.py` — genera MP3 de prueba.

## Stack y por qué

- **Python** de punta a punta (donde viven las librerías de audio).
- **Interfaz: PySide6 (Qt)** — ya construida y en uso (`app.py` + `gui/`).
- **Audio: ffmpeg + numpy** (NO Essentia: imposible de instalar fácil en Windows;
  ffmpeg+numpy se instala sin dolor y rinde igual para BPM/key/energía).
- **SQLite** local. **Mutagen** para tags. **Chromaprint/fpcalc** para duplicados.

## Decisiones de diseño clave

- **Almacenamiento físico por Género/Subgénero**; un track = una carpeta. La
  organización "dinámica" (filtros por BPM/key/energía/etc.) son vistas, no mueven archivos.
- **Árbol de géneros** (en `config.py`): Techno (Peak Time - Driving, Melodic
  Techno, Minimal - Deep Tech), House (Progressive, Tech, Bass, Afro, Organic,
  Electro), Trance (Main Floor, Tech, Progressive, Psy-Trance), Indie Dance, Big Room.
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
  duración (±2s), tiene prioridad sobre el tag → 3. Analizar audio (comando
  `analyze`, separado) → 4. Si sigue sin género: sugerencia por audio
  (`analyzer.suggest_genre` → `genre_profiles.py`, ver abajo) → 5. Revisión
  manual (GUI/CLI) → 6. Guardar en SQLite. Las clasificaciones con
  `confianza in ("manual", "supabase")` nunca se sobreescriben en escaneos
  futuros (protección de fuentes de alta confianza).
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
- **Biblioteca Confiable (Supabase)**: opcional, configurable con
  `python cli.py config --supabase-url URL --supabase-key KEY`. Si no está
  configurada o falla la red, el lookup devuelve `None` sin romper nada y el
  flujo sigue por el clasificador de tags normalmente.
- **Charts de Beatport (Módulo 2):** lee páginas públicas con Playwright (sin
  credenciales); migrar a la API oficial v4 (OAuth) cuando lleguen. Ver detalle
  en el roadmap más abajo.
- **Rekordbox:** import (BPM/key + verificación) y export de playlists. Nunca
  modifica la base de Rekordbox; solo lee XML y escribe un XML nuevo.

## Base de datos (SQLite)

Tabla `tracks` (núcleo): ruta_origen/destino, titulo, artista, sello, anio, bpm,
key, camelot, duracion_seg, genero_raw, genero, subgenero, confianza (tag/manual/
supabase — protege de re-escaneos), genero_sugerido, subgenero_sugerido,
nota_sugerencia (texto, incluye el top-3 de `genre_profiles`), energia,
energia_manual, energia_raw, f_loud/f_bright/f_low/f_busy (rasgos), waveform_data,
bpm_fuente, huella, huella_dur, bitrate_kbps, formato, baja_calidad, estado,
analizado, fecha_ingreso.
Tablas: `playlists` (reglas JSON), `modelo_energia` (coef del aprendizaje).
Tablas del Módulo 2: `charts_tracks` (charts de Beatport scrapeados: beatport_id,
genero_slug, posicion, nombre, artistas/remixers en JSON, sello, bpm, key,
primera_vez/fecha_scrape para detectar novedades) y `para_conseguir` (lista
manual de tracks a comprar/bajar, con `conseguido` 0/1).
Las columnas nuevas se agregan por migración suave en `db.connect()`.

## Lo que falta (roadmap)

**Módulo 2 — en progreso (primera pieza: charts de Beatport):**
- `charts_beatport.py` scrapea con Playwright (Beatport es una SPA en
  Next.js) el Top 100 global y por género/sub-género, sin credenciales.
  Comandos: `charts-generos` (lista slugs disponibles), `charts-scrape
  [--genero SLUG]`, `charts-show [--genero SLUG] [--top N]`,
  `charts-novedades [--genero SLUG]` (tracks nuevos desde el último scrape).
  Confirmado funcionando contra Beatport real (46 géneros descubiertos, Top
  100 de un género parseado correctamente).
  **Caveat importante**: Beatport tiene protección Cloudflare; varias
  corridas seguidas en poco tiempo (visto durante el desarrollo) hacen que
  devuelva una página de challenge ("Just a moment...") en vez de contenido;
  el comando lo detecta y falla con mensaje claro en vez de romperse, pero
  hay que espaciar los scrapes (idea original: una corrida diaria, no en
  loop ni con reintentos agresivos).
- Lista "para conseguir" (`conseguir agregar/listar/marcar/quitar`): existe
  y funciona, pero es 100% manual — no se llena automático desde los charts
  todavía (ej. "agregar todas las novedades de Techno a la lista").
  PENDIENTE.
- Seguimiento de novedades funciona por género individual
  (`charts-novedades --genero X`); no hay una vista agregada de "todo lo
  nuevo en mis géneros favoritos" en una sola corrida. PENDIENTE.
- Preview de YouTube: no empezado.

**Hecho, pendiente de conectar a la GUI** (el motor ya funciona por CLI):
- **Importador de Serato** — parser binario (`serato_db.py`) y comando
  `import-serato` funcionan; falta un botón en la GUI.
- **Borrado asistido de duplicados** — el CLI (`duplicates --borrar`) agrupa,
  sugiere la mejor calidad y borra interactivo; no existe equivalente en la GUI.
- **Sugerencia automática de género para "_Por revisar"** — el motor
  (`analyzer.suggest_genre` / `genre_profiles.py`) funciona vía `analyze`/
  `resuggest`; la GUI permite editar género a mano pero no tiene un botón que
  dispare la sugerencia automática.
- **Tab de Artistas** — `gui/artistas_widget.py` y los workers de
  enriquecimiento (Last.fm/Beatport) existen pero no están integrados en
  `main_window.py`.

**No empezado:**
- **Módulo 2 completo:** charts Beatport (público→API), seguimiento nuevo
  ingreso/salida, lista de pendientes, preview YouTube, exportar a texto.
- **Creador de DJ Sets** + chequeo de derechos para YouTube (semáforo por sello).
- **Empaquetado/instalador** + asistente de primer arranque (elegir la biblioteca).
- **Beatport API**: pedir credenciales OAuth (uso no comercial) para género/
  subgénero oficial (hoy solo está GetSongBPM, de cobertura pobre).

**Hecho** (ya no es roadmap, pero quedaba listado como pendiente antes):
interfaz gráfica PySide6 (`app.py` + `gui/`, con reproductor + cola + shuffle
inteligente por BPM/armónico), Biblioteca Confiable en Supabase como fuente
prioritaria de género, motor de sugerencia de género por audio basado en la
taxonomía Beatport (`genre_profiles.py`).

## Convenciones

- Idioma: español en mensajes de consola, comentarios y nombres de funciones.
- Cada track vive en una sola carpeta física (Género/Subgénero).
- El análisis cachea por flag `analizado`; nunca re-analiza salvo `--reset`.
- Las calificaciones manuales del DJ son verdad y nunca se sobrescriben.
- Multinúcleo: los workers (analyze_file, calcular_worker) son funciones de módulo
  (picklables); `main()` está guardado por `if __name__ == "__main__"`.

## Notas / gotchas

- El proyecto está en una carpeta de OneDrive. En Claude Code (que edita archivos
  locales directo) esto no da problema; el lag de sincronización que se vio antes
  era un artefacto del entorno anterior. Aun así, si OneDrive molesta en refactors
  grandes, considerá mover el proyecto a una ruta local (ej. `C:\Proyectos\asistente_dj`).
- `asistente_dj.db` (la base), `asistente_config.json` y `fpcalc.exe` son locales
  de cada máquina: NO versionar (ver `.gitignore`).
- GetSongBPM tiene cobertura pobre para el catálogo underground/reciente de Brian
  (validado: 0/12). Sirve poco; Beatport es la fuente correcta para este estilo.
