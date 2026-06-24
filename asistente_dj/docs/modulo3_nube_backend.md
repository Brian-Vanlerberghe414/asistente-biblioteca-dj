# Módulo 3 — Nube + backend + multiplataforma

> Doc de módulo. Ver `CLAUDE.md` (raíz) para la tabla de ruteo completa y
> el contexto general del proyecto.

Backend FastAPI (`backend/`, deployado en Render:
https://asistente-biblioteca-dj.onrender.com) + Supabase (Auth, RLS,
Biblioteca Confiable compartida, biblioteca personal por usuario, storage
de audio). Fase 1, 2 y la sincronización personal ya hechas; Fase 3 (apps
cliente) sin arrancar.

## Comandos CLI relacionados (corren desde `asistente_dj/`)

```
python cli.py biblioteca estado|agregar|listar|caratulas   # Biblioteca Confiable (Supabase) — fuente prioritaria de género; caratulas: completa cover_url faltantes vía iTunes
python cli.py config --supabase-url URL --supabase-key KEY   # credenciales de Supabase
```

## Arquitectura

- `cloud_backup.py` — backup de audio personal a Cloudflare R2 vía el
  backend; usa la cuenta personal del DJ (`mi_email`/`mi_password`), no
  la cuenta de servicio.
- `cloud_sync.py` — sincronización de género/subgénero/playlists con
  `mi_biblioteca`/`mis_playlists` en la nube (base para Fase 3, apps
  cliente); mismo patrón de auth que `cloud_backup.py`. Funciones:
  `flush_pendientes(conn)` (push agrupado, ver abajo), `pull_biblioteca(conn)`,
  `push_playlist(nombre, ids, conn)`, `pull_playlists(conn)`.
- `biblioteca_confiable.py` — cliente de Supabase ("Biblioteca Confiable");
  fuente prioritaria de género. Opcional y a prueba de fallos: si no hay
  credenciales o falla la red, no rompe nada y el flujo sigue por tags.
  `agregar()` (una fila), `agregar_lote(filas)` (upsert en lote, ver
  abajo), `completar_caratulas(limite)`, `actualizar_cover_url()`.
- `backend/main.py`, `backend/auth.py` (verifica el JWT de Supabase Auth
  contra su JWKS público — ES256/asimétrico, no hace falta secreto
  compartido), `backend/supabase_client.py` (cliente de Supabase *por
  request*, actuando como el usuario del JWT, para que el RLS de Postgres
  haga el trabajo de permisos solo), `backend/routes/` (`biblioteca.py`,
  `artistas.py`, `charts.py`, `me.py`, `audio.py`, `mi_biblioteca.py`),
  `backend/storage.py` (cliente boto3 S3-compatible para R2).

**Sin documentar / legacy**: `cloud_db.py`, `admin_merge.py`.

## Decisiones de diseño

- **Biblioteca Confiable (Supabase)**: opcional, configurable con
  `python cli.py config --supabase-url URL --supabase-key KEY`. Si no está
  configurada o falla la red, el lookup devuelve `None` sin romper nada y el
  flujo sigue por el clasificador de tags normalmente.
- **Carátulas (cover art) en la Biblioteca Confiable (sesión 2026-06-22)**:
  columna `cover_url` en `biblioteca_tracks` (migración
  `supabase_setup_cover_url.sql`). Decisión clave: se guarda **solo la URL**
  (al CDN de Apple/mzstatic.com vía `itunes_cover.py`, ver
  `docs/modulo1_organizador.md`), nunca se descarga ni se aloja la imagen —
  costo de storage despreciable (~150 bytes/fila) y sin depender de
  infraestructura propia. `biblioteca_confiable.completar_caratulas(limite)`
  busca tracks con `cover_url` vacío y los completa vía iTunes Search API;
  comando `python cli.py biblioteca caratulas --limit N`. `agregar()` solo
  pisa `cover_url` si se le pasa explícitamente (no se borra una carátula ya
  encontrada en cada upsert de género/BPM, que es un flujo separado).
  Validado contra la Biblioteca Confiable real (2.310 tracks): 5/5 carátulas
  encontradas en la primera corrida de prueba. Para la parte GUI (cómo
  aparecen en vivo en la grilla durante el escaneo), ver `docs/gui.md`.
- **Escritura directa a la Biblioteca Confiable — SOLO mientras la app está en
  desarrollo.** Hoy (sesión 2026-06-19) tanto el scraper de charts como las
  ediciones manuales del DJ en la GUI escriben *directo* a `biblioteca_tracks`
  (`biblioteca_confiable.agregar()`/`agregar_lote()`), con una corrida manual
  marcada `fuente='manual'` protegida de que la pise cualquier subida
  automática después. **Esto es un atajo temporal, no el diseño final.**
  Ver "Beta V1 — Feedback DJ" abajo para el plan.

## Roadmap

### Beta V1 — "Feedback DJ" (rediseño del flujo de escritura, PENDIENTE de diseñar a fondo, decidido en sesión 2026-06-19)

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
  directa: `gui/track_model.py:guardar_ids` y la protección por
  `fuente='manual'` en `biblioteca_confiable.agregar()`.
- El scraper de charts de Beatport probablemente sigue escribiendo directo a
  `biblioteca_tracks` como hoy (es una fuente automática/pública, no la
  corrección de un usuario) — a confirmar cuando se diseñe esto a fondo.
- Relacionado: la Fase 1 (abajo) ya resuelve el problema más urgente
  (escritura sin control de ningún usuario con la clave anon), pero el
  pipeline de moderación de Feedback DJ en sí sigue sin diseñar.

### Fase 1 — Backend + Auth + RLS multi-usuario: HECHA y deployada

Decisiones: Auth = Supabase Auth, Backend = Python + FastAPI, Hosting =
Render.

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
- Los clientes futuros (Android, web) inician sesión directo contra
  Supabase Auth con la clave anon (eso sí es seguro) y mandan ese JWT a
  esta API en cada request — nunca hablan directo con Supabase con una
  clave compartida.
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
- **Gotcha de deploy repetido en esta sesión**: un `git push` al backend
  NO siempre dispara el auto-deploy de Render — verificar con
  `curl .../openapi.json` qué rutas están realmente live antes de asumir
  que un push tomó efecto, y hacer "Manual Deploy → Deploy latest commit"
  si no.

### Fase 2 — Storage de audio real: HECHA

Proveedor elegido: **Cloudflare R2** (sin costo de egress — con muchos
usuarios escuchando/descargando, eso es lo que de verdad importa; S3/GCS
cobran $0.09–0.12/GB de egress y se vuelven inviables a esa escala).

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
- **Costo estimado**: solo Brian con 50GB ≈ $0.60/mes; a 1000 usuarios
  con 100TB en total ≈ $1.500–1.650/mes (~$1,60/usuario/mes), dominado
  casi enteramente por el storage — el egress es $0 siempre con R2.
- **Pendiente, fuera de esta etapa**: Brian todavía no subió su
  biblioteca completa (~2000 tracks, 50GB) — lo decide él manualmente
  cuando quiera. No hay pantalla de login multi-usuario (si en el futuro
  hace falta soportar más DJs en la misma PC, hay que construirla).

### Sincronización de biblioteca personal — HECHA, base para la Fase 3

Brian pidió que, cuando exista un cliente Android/web/iOS, el DJ pueda
editar género o crear playlists *desde ese dispositivo* y que se vea en
todos lados (incluida la app de escritorio). Como `genero`/`subgenero`/
`playlists` vivían solo en el SQLite local, se armó esta base:

- Tablas nuevas en Supabase: `mi_biblioteca` (espejo personal de
  género/subgénero/bpm/key por usuario, clave de sync = artista+título
  normalizados, igual que `biblioteca_confiable.py`) y `mis_playlists`
  (igual patrón). Privadas por usuario (RLS ni con lectura abierta, como
  `audio_personal`). `asistente_dj/supabase_setup_mi_biblioteca.sql`.
- Backend: `backend/routes/mi_biblioteca.py` (`POST/GET /mi-biblioteca`,
  `POST/GET /mi-biblioteca/playlists`) — resolución de conflictos **"gana
  el cambio más reciente"** aplicada del lado del servidor (compara
  `actualizado_en`, no confía en que el cliente nunca mande algo viejo).
- Local: columna `actualizado_en` nueva en `tracks` (migración suave en
  `db.py`), se pisa solo en ediciones manuales.
- Conectado a las ediciones existentes: `gui/track_model.py:guardar_ids`
  y `gui/main_window.py:_on_crear_playlist`.
- Validado end-to-end simulando una edición "desde Android" (POST directo
  a `/mi-biblioteca/sync` sin pasar por la GUI, con género distinto): al
  sincronizar, el género local cambió al valor mandado por la API —
  funciona en ambas direcciones, tracks y playlists.

#### Sincronización automática, sin botón (sesión 2026-06-23)

Se sacó el botón "🔄 Sincronizar" de la toolbar — `SyncWorker`
(`gui/workers.py`) corre la misma lógica en background, sola, una vez al
arrancar la app, cada 20 minutos mientras está abierta
(`MainWindow._iniciar_sync`, `QTimer`), y al cerrar la app
(`MainWindow.closeEvent`, síncrono). Sin popups: si no hay cuenta personal
configurada o falla la red, no hace nada; solo actualiza la barra de
estado si trajo cambios reales.

**Incremental** para que correrla seguido sea liviano: el backend
(`GET /mi-biblioteca`, `GET /mi-biblioteca/playlists`) acepta
`?since=<ISO 8601>` y devuelve solo filas con `actualizado_en` más nuevo;
`cloud_sync.py` guarda la marca de la última corrida exitosa en
`asistente_config.json` (`sync_ultima_marca`/`sync_ultima_marca_playlists`/
`sync_ultima_marca_push`) y la manda en la siguiente. El lookup
id→artista/título que necesitan `push_playlist`/`pull_playlists` para
traducir ids de playlist sigue pidiendo la tabla completa (no puede ser
incremental, una playlist puede referenciar un track viejo), pero usa
`?solo_ids=true` para traer solo 3 columnas en vez de todas.

**Push también agrupado, no por track**: antes, cada track guardado
disparaba un request individual a `biblioteca_confiable.agregar()` Y otro
a `cloud_sync` (función ya eliminada, `push_track`) — guardar 20 tracks de
una (ej. con la edición masiva de género, ver `docs/gui.md`) hacía 20+20
requests. Ahora: `biblioteca_confiable.agregar_lote(filas)` sube todo el
lote guardado en un solo upsert (`gui/track_model.py:guardar_ids` ya no
llama a `agregar()` en loop). El push a `mi_biblioteca` se sacó por
completo de `guardar_ids` — alcanza con que quede el `actualizado_en`
puesto en la fila local; lo manda después `cloud_sync.flush_pendientes(conn)`,
que junta TODOS los tracks con `actualizado_en` más nuevo que la última
corrida exitosa y los manda en un solo `POST /mi-biblioteca/sync`.
`flush_pendientes` solo se llama desde `SyncWorker` (arranque + cada 20
min) y desde `MainWindow.closeEvent` — nunca desde un "Guardar"
individual. Resultado: 20 ediciones guardadas (en 1 clic o en 20) generan
como máximo 1 sincronización por ciclo, no una por track. Crear una
playlist sigue subiéndola al toque (acción puntual, no en loop) pero
ahora hace un `flush_pendientes` justo antes, para garantizar que sus
tracks ya estén en `mi_biblioteca` y se puedan traducir los ids.

### Fase 3 (sin arrancar) — Apps cliente

Android primero (prioridad elegida por Brian), después web/iOS. Ya van a
poder pegarle al backend de `backend/` en vez de hablar directo con
Supabase, y ya tienen `mi_biblioteca`/`mis_playlists` de dónde leer/
escribir (ver arriba). Falta decidir el stack (no asumir nativo/Flutter/
React Native hasta hablarlo con Brian).

## Plan diferido relacionado

Sistema completo de Tiers de usuario + Capabilities + Build Flags + Pagos
(Stripe) — diseño ya armado en
`C:\Users\Brian Vanlerberghe\.claude\plans\polymorphic-rolling-wolf.md`,
diferido a último paso del desarrollo. Toca directamente `backend/`
(`auth.py`, `main.py`, nuevos `capabilities.py`/`billing.py`/`routes/streaming.py`)
y la tabla `perfiles` (nueva columna `tier` + fix de seguridad de GRANT
por columna).

## Esquema de base de datos

Ver `docs/base_de_datos.md`.
