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
python cli.py biblioteca estado|agregar|listar|caratulas   # Biblioteca Confiable (Supabase) — fuente prioritaria de género; caratulas: completa cover_url faltantes vía iTunes
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
- `itunes_cover.py` — cliente de la API pública de búsqueda de iTunes/Apple
  Music (sin API key) para carátulas (cover art): `obtener_caratula(artista,
  titulo, size=600)` y `obtener_caratulas_lote(tracks)`. Caché en memoria
  por (artista, título) + throttle configurable (~20 req/min, el límite
  documentado de Apple) para procesar lotes sin pasarse. Conectado a la
  Biblioteca Confiable vía `biblioteca_confiable.completar_caratulas()`
  (ver más abajo); todavía no está conectado a la GUI (panel de detalle,
  charts) para MOSTRAR la imagen, solo para completarla en Supabase.
- `serato_db.py` — parser binario de la base de datos de Serato (database V2).
- `cloud_backup.py` — Módulo 3 Fase 2: backup de audio personal a Cloudflare
  R2 vía el backend (`backend/`); usa la cuenta personal del DJ
  (`mi_email`/`mi_password`), no la cuenta de servicio.
- `cloud_sync.py` — sincronización de género/subgénero/playlists con
  `mi_biblioteca`/`mis_playlists` en la nube (base para Fase 3, apps
  cliente); mismo patrón de auth que `cloud_backup.py`.
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
- `gui/` — interfaz gráfica: `main_window.py` (ventana principal, pestañas en
  horizontal **Biblioteca - Playlist - Charts**), `organizador.py`
  (grilla + reproductor con cola/shuffle inteligente; el árbol de géneros ya
  NO tiene nodo de playlists, se movió a su propia pestaña), `playlists_widget.py`
  (pestaña Playlist: lista de playlists con renombrar/borrar/exportar a
  Rekordbox + grilla de solo lectura de sus tracks; la creación de playlists
  sigue siendo desde Biblioteca con selección de tracks + botón "➕ Playlist"),
  `track_model.py` (modelo de tabla editable), `detalle_panel.py` (panel de
  detalle), `track_table_view.py`, `waveform_widget.py`, `theme.py`, delegates
  de edición inline (género, BPM, artista). `artistas_widget.py` y sus
  workers existen pero todavía no están conectados a la ventana principal.
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
- **Carátulas (cover art) en la Biblioteca Confiable (sesión 2026-06-22)**:
  columna `cover_url` en `biblioteca_tracks` (migración
  `supabase_setup_cover_url.sql`). Decisión clave: se guarda **solo la URL**
  (al CDN de Apple/mzstatic.com vía `itunes_cover.py`), nunca se descarga ni
  se aloja la imagen — costo de storage despreciable (~150 bytes/fila) y
  sin depender de infraestructura propia. `biblioteca_confiable.completar_caratulas(limite)`
  busca tracks con `cover_url` vacío y los completa vía iTunes Search API;
  comando `python cli.py biblioteca caratulas --limit N`. `agregar()` solo
  pisa `cover_url` si se le pasa explícitamente (no se borra una carátula ya
  encontrada en cada upsert de género/BPM, que es un flujo separado).
  Validado contra la Biblioteca Confiable real (2.310 tracks): 5/5 carátulas
  encontradas en la primera corrida de prueba.
- **Escritura directa a la Biblioteca Confiable — SOLO mientras la app está en
  desarrollo.** Hoy (sesión 2026-06-19) tanto el scraper de charts como las
  ediciones manuales del DJ en la GUI escriben *directo* a `biblioteca_tracks`
  (`biblioteca_confiable.agregar()`), con una corrida manual marcada
  `fuente='manual'` protegida de que la pise cualquier subida automática
  después. **Esto es un atajo temporal, no el diseño final.** Para la beta V1,
  el flujo cambia (ver roadmap más abajo): el escaneo seguirá leyendo de la
  Biblioteca Confiable como hoy, pero los cambios manuales de los usuarios ya
  NO van a escribir ahí directo — van a pasar antes por una tabla intermedia
  ("Feedback DJ") y un análisis/validación, y solo después de aprobarse pasan
  a la Biblioteca Confiable. El código actual de escritura directa manual
  (`gui/track_model.py:guardar_ids`, la protección por `fuente='manual'` en
  `biblioteca_confiable.agregar()`) hay que reemplazarlo en ese momento, no
  solo extenderlo.
- **Charts de Beatport (Módulo 2):** lee páginas públicas con Playwright (sin
  credenciales); migrar a la API oficial v4 (OAuth) cuando lleguen. Ver detalle
  en el roadmap más abajo.
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

**Beta V1 — "Feedback DJ" (rediseño del flujo de escritura a la Biblioteca
Confiable, PENDIENTE de diseñar a fondo, decidido en sesión 2026-06-19):**
- Hoy, en desarrollo, los cambios manuales del DJ en la GUI se suben *directo*
  a `biblioteca_tracks` (con protección `fuente='manual'`). Esto es un atajo
  de desarrollo, no el diseño final — confiar a ciegas en la corrección de
  cualquier usuario de la beta (no solo Brian) sin revisión es riesgoso una
  vez que esto salga de un entorno controlado.
- **Diseño futuro:** nueva tabla/proyecto en Supabase, **"Feedback DJ"**,
  separada de `biblioteca_tracks`. Los cambios manuales de los usuarios van
  ahí primero (no a la Biblioteca Confiable directo).
- Esos registros de Feedback DJ pasan por un **análisis previo** (un prompt/
  pipeline de validación — todavía sin diseñar, queda pendiente de trabajar
  más adelante) antes de promoverse a `biblioteca_tracks`. La idea es filtrar
  errores, trolling o correcciones de baja confianza antes de que afecten a
  *todos* los DJs que comparten la Biblioteca Confiable.
- El **escaneo** (`scanner.scan()`) sigue leyendo de la Biblioteca Confiable
  igual que ahora — eso no cambia. Lo que cambia es de dónde vienen las
  escrituras manuales.
- Implica reemplazar (no solo extender) el código actual de escritura manual
  directa: `gui/track_model.py:guardar_ids` (hoy llama a
  `biblioteca_confiable.agregar(..., fuente="manual")` directo) y la
  protección por `fuente='manual'` en `biblioteca_confiable.agregar()`.
- El scraper de charts de Beatport (`cli.py:cmd_charts_scrape`) probablemente
  sigue escribiendo directo a `biblioteca_tracks` como hoy (es una fuente
  automática/pública, no la corrección de un usuario) — a confirmar cuando se
  diseñe esto a fondo.

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
- Preview de YouTube y Spotify: **hecho** (sesión 2026-06-19) — tab de Charts
  en la GUI (`gui/charts_widget.py`) con dos botones independientes ("▶
  YouTube", "♪ Spotify") arriba del reproductor embebido; el DJ elige cuál
  usar para cada track, **no hay fallback automático entre servicios** (se
  probó así primero y Brian pidió explícitamente que fuera elección manual,
  no algo automático). `youtube_preview.py` busca sin API key vía yt-dlp,
  prioriza Extended Mix con fallback a versión corta, y dentro del propio
  YouTube cicla entre varios candidatos si uno no permite embeberse
  (restricción del dueño por Content ID) — eso sí es automático, porque es
  "seguir buscando dentro de la opción YouTube", no cruzar a otro servicio.
  `spotify_preview.py` busca vía Client Credentials (credenciales en
  `asistente_config.json` con `python cli.py config --spotify-client-id ID
  --spotify-client-secret SECRET`, gratis en developer.spotify.com/dashboard);
  el embed de Spotify es más permisivo que YouTube pero sin login del
  usuario solo reproduce 30s de preview, no el track completo. Ver
  `gui/local_preview_server.py` para el detalle técnico de por qué hace
  falta un mini servidor HTTP local para que YouTube acepte el embed.
  **Caso de uso real validado:** "Disco Cherry" de Purple Disco Machine
  (sello Sweat It Out/Sony) tiene TODOS sus candidatos de YouTube con embed
  deshabilitado por Content ID — ahí el botón de Spotify es la única opción
  con preview, y funciona bien.

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
  ingreso/salida, lista de pendientes, exportar a texto.
- **Creador de DJ Sets** + chequeo de derechos para YouTube (semáforo por sello).
- **Empaquetado/instalador** + asistente de primer arranque (elegir la biblioteca).
- **Beatport API**: pedir credenciales OAuth (uso no comercial) para género/
  subgénero oficial (hoy solo está GetSongBPM, de cobertura pobre).

**Módulo 3 — Biblioteca en la nube + multiplataforma (pedido por Brian en
sesión 2026-06-19; Fase 1 hecha en sesión 2026-06-21, resto sin arrancar):**

- **Fase 1 — Backend + Auth + RLS multi-usuario: HECHA y deployada.**
  Decisiones: Auth = Supabase Auth, Backend = Python + FastAPI, Hosting =
  Render. Cambios:
  - `asistente_dj/supabase_setup_perfiles.sql` — tabla `perfiles` (uno por
    DJ autenticado) + trigger que la crea sola al registrarse.
  - `asistente_dj/supabase_setup_rls_v2.sql` — `biblioteca_tracks` y
    `artistas_generos` pasan de "anon escribe todo" a "lectura abierta,
    escritura solo `authenticated`"; se agregó columna `creado_por` a
    `biblioteca_tracks` para saber qué usuario hizo cada corrección manual.
  - Cuenta de servicio en Supabase Auth (credenciales en
    `asistente_config.json` como `supabase_service_email`/
    `supabase_service_password`, NUNCA en texto plano en ningún log/print)
    para que `biblioteca_confiable.py` (la app de escritorio y las rutinas
    de charts en la nube) puedan seguir escribiendo tras el RLS nuevo —
    `_get_cliente()` hace `sign_in_with_password` antes de devolver el
    cliente si hay cuenta de servicio configurada. Las 2 rutinas
    programadas de charts ya tienen estas credenciales en su prompt.
  - **Backend nuevo en `backend/`** (FastAPI, deployado en
    https://asistente-biblioteca-dj.onrender.com): `main.py`, `auth.py`
    (verifica el JWT de Supabase Auth contra su JWKS público — las claves
    nuevas de Supabase firman con ES256/asimétrico, no hace falta ningún
    secreto compartido), `supabase_client.py` (arma un cliente de Supabase
    *por request*, actuando como el usuario del JWT, para que el RLS de
    Postgres haga el trabajo de permisos solo), `routes/` (`biblioteca.py`,
    `artistas.py`, `charts.py`, `me.py`). Los clientes futuros (Android,
    web) inician sesión directo contra Supabase Auth con la clave anon (eso
    sí es seguro) y mandan ese JWT a esta API en cada request — nunca
    hablan directo con Supabase con una clave compartida.
  - **Gotcha de Supabase repetido dos veces en esta fase**: correr un SQL
    de `GRANT`/`ALTER TABLE ... ADD COLUMN` sin error visible en el SQL
    Editor NO garantiza que se haya aplicado — pasó con los permisos de
    `authenticated` en `biblioteca_tracks`/`charts_tracks` y con la columna
    `creado_por`. Verificar siempre con
    `SELECT grantee, privilege_type FROM information_schema.role_table_grants
    WHERE table_name='X'` (para permisos) o
    `SELECT column_name FROM information_schema.columns WHERE table_name='X'`
    (para columnas) después de cualquier cambio, y si falta algo, re-correr
    el `GRANT`/`ALTER` suelto + `NOTIFY pgrst, 'reload schema';`.
  - **Gotcha de Render**: el campo "Start Command" no quedó guardado en el
    primer intento (corrió el placeholder genérico `gunicorn
    your_application.wsgi` en vez de `uvicorn main:app --host 0.0.0.0
    --port $PORT`) — hay que entrar a Settings del servicio y confirmar que
    quedó el comando real, no el de ejemplo.

- **Fase 2 — Storage de audio real: HECHA (sesión 2026-06-21).** Proveedor
  elegido: **Cloudflare R2** (sin costo de egress — con muchos usuarios
  escuchando/descargando, eso es lo que de verdad importa; S3/GCS cobran
  $0.09–0.12/GB de egress y se vuelven inviables a esa escala). Cambios:
  - **Cuenta personal de Brian en Supabase Auth** (su email real, separada
    de la cuenta de servicio del scraper) — los archivos de audio son
    privados por usuario, no van a la Biblioteca Confiable compartida.
  - `asistente_dj/supabase_setup_audio_personal.sql` — tabla
    `audio_personal` (usuario_id, r2_key, titulo, artista, tamano_bytes,
    ruta_local), RLS `FOR ALL TO authenticated USING (auth.uid() =
    usuario_id)` — a diferencia de `biblioteca_tracks`, ni la lectura es
    abierta acá.
  - **Backend**: `backend/storage.py` (cliente `boto3` S3-compatible
    apuntando al endpoint de R2) + `backend/routes/audio.py`
    (`POST /audio/upload-url`, `GET /audio/mios`,
    `GET /audio/{r2_key}/download-url`) — el archivo nunca pasa por el
    backend, sube/baja *directo* a R2 con URLs firmadas.
  - **GUI**: botón **"☁ Backup en la nube"** en la toolbar principal
    (`gui/main_window.py:_on_backup_nube`), con `BackupNubeWorker`
    (`gui/workers.py`) y la lógica de subida en `asistente_dj/cloud_backup.py`
    (usa la cuenta personal de Brian, pide URL firmada al backend, hace el
    PUT directo a R2). Opera sobre los tracks marcados con "Seleccionar"
    (mismo mecanismo que "Eliminar"/"Playlist").
  - Validado end-to-end (local y en producción): subido un track real de la
    biblioteca de Brian, descargado de vuelta, hash SHA-256 idéntico —
    sin corrupción.
  - **Costo estimado** (sesión 2026-06-21, ver detalle en el chat): solo
    Brian con 50GB ≈ $0.60/mes; a 1000 usuarios con 100TB en total ≈
    $1.500–1.650/mes (~$1,60/usuario/mes), dominado casi enteramente por el
    storage — el egress es $0 siempre con R2.
  - **Pendiente, fuera de esta etapa**: Brian todavía no subió su
    biblioteca completa (~2000 tracks, 50GB) — lo decide él manualmente
    cuando quiera, track por track o seleccionando todo, con el mismo botón
    ya construido. No hay pantalla de login multi-usuario (si en el futuro
    hace falta soportar más DJs en la misma PC, hay que construirla).

- **Sincronización de biblioteca personal — HECHA (sesión 2026-06-22),
  base para la Fase 3.** Brian pidió que, cuando exista un cliente
  Android/web/iOS, el DJ pueda editar género o crear playlists *desde ese
  dispositivo* y que se vea en todos lados (incluida la app de escritorio).
  Como `genero`/`subgenero`/`playlists` vivían solo en el SQLite local
  (`biblioteca_tracks` es conocimiento *compartido* entre DJs, no la
  organización personal de cada uno), se armó esta base:
  - Tablas nuevas en Supabase: `mi_biblioteca` (espejo personal de
    género/subgénero/bpm/key por usuario, clave de sync = artista+título
    normalizados, igual que `biblioteca_confiable.py`) y `mis_playlists`
    (igual patrón). Privadas por usuario (RLS ni con lectura abierta, como
    `audio_personal`). `asistente_dj/supabase_setup_mi_biblioteca.sql`.
  - Backend: `backend/routes/mi_biblioteca.py`
    (`POST/GET /mi-biblioteca`, `POST/GET /mi-biblioteca/playlists`) —
    resolución de conflictos **"gana el cambio más reciente"** aplicada del
    lado del servidor (compara `actualizado_en`, no confía en que el
    cliente nunca mande algo viejo).
  - Local: columna `actualizado_en` nueva en `tracks` (migración suave en
    `db.py`), se pisa solo en ediciones manuales.
  - `asistente_dj/cloud_sync.py` (`push_track`/`pull_biblioteca`/
    `push_playlist`/`pull_playlists`) — mismo patrón de auth que
    `cloud_backup.py` (cuenta PERSONAL del DJ).
  - Conectado a las ediciones existentes: `gui/track_model.py:guardar_ids`
    y `gui/main_window.py:_on_crear_playlist` ahora también empujan el
    cambio a la nube. Botón nuevo **"🔄 Sincronizar"** en la toolbar para
    traer cambios hechos desde otro dispositivo.
  - Validado end-to-end simulando una edición "desde Android" (POST directo
    a `/mi-biblioteca/sync` sin pasar por la GUI, con género distinto): al
    apretar "Sincronizar", el género local cambió al valor mandado por la
    API — funciona en ambas direcciones, tracks y playlists.

- **Fase 3 (sin arrancar) — Apps cliente.** Android primero (prioridad
  elegida por Brian), después web/iOS. Ya van a poder pegarle al backend de
  `backend/` en vez de hablar directo con Supabase, y ya tienen
  `mi_biblioteca`/`mis_playlists` de dónde leer/escribir (ver arriba).
  Falta decidir el stack (no asumir nativo/Flutter/React Native hasta
  hablarlo con Brian).

- Relacionado con [[project-punch-list-calidad]] y el plan de "Feedback DJ"
  ([[project-feedback-dj-beta]]): la Fase 1 ya resuelve el problema más
  urgente (escritura sin control de ningún usuario con la clave anon), pero
  el pipeline de moderación de Feedback DJ en sí sigue sin diseñar.

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
