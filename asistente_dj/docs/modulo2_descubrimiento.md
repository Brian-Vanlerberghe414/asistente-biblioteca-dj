# Módulo 2 — Descubrimiento (charts)

> Doc de módulo. Ver `CLAUDE.md` (raíz) para la tabla de ruteo completa y
> el contexto general del proyecto.

Charts de Beatport, seguimiento de novedades, preview de YouTube/Spotify,
lista de "para conseguir". En progreso (la primera pieza, charts de
Beatport, funciona; el resto del módulo no está terminado).

## Comandos CLI (corren desde `asistente_dj/`)

```
python cli.py charts-generos                        # slugs de género disponibles en Beatport
python cli.py charts-scrape [--genero SLUG]          # scrapear Top 100 (global y/o por género)
python cli.py charts-show [--genero SLUG] [--top N]  # ver el chart guardado
python cli.py charts-novedades [--genero SLUG]       # tracks nuevos desde el último scrape
python cli.py conseguir agregar|listar|marcar|quitar # lista de "para conseguir"
```

## Arquitectura

- `charts_beatport.py` — scraper con Playwright de los charts Top 100 de
  Beatport (global y por género), sin credenciales. Diseño con backend
  intercambiable: cuando haya OAuth de la API oficial, se reemplaza sin
  tocar `cli.py` (mismo contrato de salida: listas de dicts).
- `youtube_preview.py` / `spotify_preview.py` / `gui/local_preview_server.py`
  — preview de tracks de charts en la GUI (ver detalle abajo).

**Sin documentar / legacy**: `charts_confiable.py`.

## Decisión de diseño

- **Charts de Beatport:** lee páginas públicas con Playwright (sin
  credenciales); migrar a la API oficial v4 (OAuth) cuando lleguen.
  **Riesgo legal activo** (scraping evadiendo Cloudflare) — ver crítica de
  arquitectura de sesión anterior; migrar a la API oficial es la salida,
  no solo una mejora.

## Roadmap

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
- **Barra lateral, precarga del track #1 y reproducción continua (sesión
  2026-06-23)**: la pestaña Charts pasó de un `QComboBox` arriba a una
  barra lateral izquierda (`QListWidget`, igual look and feel que la
  navegación de Biblioteca) — un ítem por chart/slug, sin jerarquía
  artificial porque los slugs de Beatport hoy son una lista plana.
  - **Precarga del track #1**: nueva preferencia en Configuración
    ("Reproductor preferido", YouTube o Spotify, clave
    `reproductor_preferido` en `settings.py`) — cada vez que el DJ entra a
    un chart, se busca en background (silencioso, sin tocar el preview)
    el track #1 con ese servicio y se guarda en
    `ChartsWidget._cache_track1` (clave=`genero_slug`). Si el DJ después
    clickea el botón de ESE servicio sobre la fila #1, sale del cache
    (instantáneo, sin el texto "Buscando…"); cualquier otra combinación
    (otra fila, otro servicio, cache todavía no listo) busca como antes.
  - **Reproducción continua — solo YouTube**: el embed de YouTube ya
    usaba la API real del reproductor (`YT.Player`/`loadVideoById`, para
    probar candidatos si uno no permite embeber); se le agregó
    `onStateChange` + un puente `QWebChannel` (`_PuenteYoutube`, clase
    nueva en `charts_widget.py`) que avisa a Python cuándo un track
    empieza (`PLAYING`) y cuándo termina (`ENDED`). Al empezar, Python
    precarga en background los candidatos del SIGUIENTE track del chart
    (`_cache_siguiente`, un solo slot); al terminar, si ya están listos,
    llama `player.loadVideoById(...)` vía `runJavaScript` — continúa sin
    recargar el iframe — y si no, espera a que la búsqueda en curso
    responda. La fila seleccionada en la tabla sigue al track que está
    sonando. Si no hay siguiente track (fin del chart), no rompe nada,
    solo deja de avanzar.
  - **Por qué Spotify no tiene continuidad**: su embed hoy es un
    `<iframe>` de oEmbed plano, sin ninguna API de eventos — conseguir lo
    mismo ahí requeriría migrar a la API de iframe propia de Spotify
    (tarea aparte, no hecha). Sin Premium logueado el preview de Spotify
    dura 30s por track de todas formas. La precarga del track #1 SÍ
    funciona para Spotify si es el preferido, pero ahí termina — sin
    auto-avance al track siguiente.
- **Módulo 2 completo:** charts Beatport (público→API), seguimiento nuevo
  ingreso/salida, lista de pendientes, exportar a texto. No empezado.
- **Beatport API**: pedir credenciales OAuth (uso no comercial) para género/
  subgénero oficial (hoy solo está GetSongBPM, de cobertura pobre). No
  empezado.
- **Creador de DJ Sets** + chequeo de derechos para YouTube (semáforo por
  sello). No empezado.

## Plan diferido relacionado

La app va a reemplazar, con el tiempo, los charts de Beatport (en el tier
Oro del futuro sistema de membresías) por un chart propio basado en uso
real de los clientes — diseño completo en
`C:\Users\Brian Vanlerberghe\.claude\plans\polymorphic-rolling-wolf.md`
("Charts propios"), diferido hasta tener usuarios reales. No nombrar nada
nuevo de este módulo de forma que quede atado permanentemente a "Beatport"
(ver nota de naming en ese plan).

## Esquema de base de datos

Tablas `charts_tracks`/`para_conseguir` — ver `docs/base_de_datos.md`.
