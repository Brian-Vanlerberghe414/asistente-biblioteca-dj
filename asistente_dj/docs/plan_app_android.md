# Plan — Asistente DJ en Android (V1) — SOLO PLANIFICACIÓN

> Revisado por Fable 5 (2026-07-04); correcciones incorporadas: secuencia del
> development build, gaps de backend faltantes (playlists), capítulo YouTube
> re-dimensionado, sección "Cómo retomar" para sesiones frías.
>
> **Rediseñado 2026-07-19** tras terminar el reproductor unificado del
> escritorio (carátula real, avance real con YouTube, "sonando" resaltado en
> cyan en toda grilla): se profundiza el contrato del contexto global de
> player en la Sesión 2 (antes era solo un esqueleto) para no repetir en
> Android la reescritura por capas que hizo falta en escritorio — ver
> "Player global" más abajo. Las demás sesiones y el orden general no
> cambian: los otros 7 cambios de esa sesión de escritorio son de UI/flujo
> local, sin superficie de backend, y no tienen eco acá.

## Context

Brian pidió empezar a planear el asistente en Android. **Decisión explícita: en esta
sesión no se escribe código** — el entregable es este plan, que al aprobarse se guarda
como `asistente_dj/docs/plan_app_android.md` (junto al plan macro
`plan_multiplataforma_escalado.md`, Fase 3 del Módulo 3) y se referencia desde
`docs/modulo3_nube_backend.md`.

Base ya decidida (2026-07-01, no se re-debate): **React Native + Expo, TypeScript,
Expo Router** (Android → Web → iOS); consumo + edición liviana (el trabajo pesado
queda en escritorio); el backend FastAPI (Render) + Supabase + R2 se extiende, no se
reescribe; migración async (A1+A3) hecha en código, sin commitear.

**Alcance V1 (elegido por Brian):**
1. **Biblioteca + edición** (ver biblioteca sincronizada, editar género/subgénero)
2. **Charts + previews** (Top 100 Beatport, preview YouTube, autoplay tipo radio)
3. **Streaming de su audio** (lo subido a R2 con "Backup en la nube")
4. **Playlists propias** (crear/modificar `mis_playlists`, sync con escritorio)
5. **Playlists colaborativas** (unirse por código, aportar, tiempo real)

Fuera de V1: tiers/pagos, push, FeelBack móvil, iOS/Web.

**Idea diferida para la app "final" (post-V1, no para el APK de uso personal,
anotado 2026-07-19):** cuando se distribuya por Play Store en vez de APK directo,
retomar la idea original de Brian de un instalador liviano que baja componentes
después de instalado, vía **Play Feature Delivery** (módulos dinámicos de Google
Play — instalación diferida/condicional de partes de la app). Para el V1 actual
(uso personal, instalación directa por APK, sin Play Store) esto no aplica — ver
Sesión 10, que en cambio achica el APK con técnicas que no dependen de Play
Store (build por arquitectura, Hermes, recorte de código).
**Decisión de producto**: V1 es **100% online** — sin red muestra un estado "sin
conexión" claro y no cachea nada (el cacheo offline es mejora futura).

**Regla de trabajo**: la app NO se escribe de un tirón — se implementa en **sesiones
separadas** (ver abajo), cada una autocontenida y con cierre verificable, para
administrar tokens/contexto entre sesiones.

---

## La app — diseño de producto

### Identidad y usuarios
- V1 es para Brian (beta personal) con login real (Supabase Auth) desde el día 1;
  para colaborativas, otros DJs pueden crearse cuenta (el registro ya existe).
- Estética: heredar el tema oscuro de la GUI (acentos cyan, `GENRE_COLORS`).
- Nombre de la app: pendiente (no bloquea).

### Navegación (Expo Router: login + 4 tabs)

```
[Login] → (con sesión guardada va directo a tabs)

┌──────────────────────────────────────────────────┐
│ ♪ Biblioteca  ⚡ Charts  ▶ Playlists  ☁ Mi Música │  ← tabs abajo
└──────────────────────────────────────────────────┘
+ header con avatar → Perfil (email, logout, versión)
+ mini-player persistente (encima de los tabs) cuando algo suena
```

**Decisión de arquitectura (tomar en Sesión 2, no después):** el player vive en un
**contexto global a nivel raíz** (no dentro de una pantalla), para que siga sonando
al navegar entre tabs. Contrato completo (no solo el esqueleto) — ver "Player
global" a continuación.

### Player global y "sonando" (patrón heredado del escritorio)

El reproductor unificado del escritorio (`gui/organizador.py:PlayerWidget`) llegó
a su forma final recién después de varias rondas: primero un esqueleto por
pantalla, después waveform congelado con YouTube, carátula duplicada en Charts,
"sonando" sin resaltar hasta agregarlo aparte en cada grilla. Android arranca
directo con el contrato completo en la Sesión 2, para no repetir esa historia:

- **Una sola fuente de reproducción a la vez**: cola local (Biblioteca/Playlists,
  streaming R2) o una fuente externa activa (YouTube de Charts) — nunca las dos
  juntas. Activar una fuente nueva siempre corta/pausa la anterior (equivalente
  RN de `activar_motor_externo`/`volver_a_motor_local` del escritorio).
- **Evento "cambió la fuente activa"** (equivalente a la señal
  `motor_externo_changed` que se sumó en escritorio): cualquier pantalla que
  muestre su propio "esto está sonando" (ej. Charts) se suscribe y se apaga sola
  si otra pantalla tomó el control — sin tener que adivinarlo comparando ids a
  mano (ese fue justamente el gap que hizo falta parchear en escritorio).
- **Estado compartido `nowPlaying`** (id o posición de chart + carátula +
  progreso), expuesto por el contexto para que Biblioteca, Charts y Playlists
  (Sesiones 3, 5, 7, 8) resalten la fila que suena sin reimplementar el
  mecanismo cada una — mismo lenguaje visual que el escritorio: **texto del
  track en cyan (`theme.cyan`)** en la fila que suena, en las tres listas.
- **Carátula real siempre**, nunca placeholder: local (R2) y externa (YouTube,
  `hqdefault.jpg` del video_id) exponen ambas una `coverUrl` al contexto.
- **Progreso real aunque la fuente sea YouTube**: la barra del mini-player se
  alimenta del progreso de CUALQUIER fuente activa, no solo del player nativo
  — el escritorio tuvo el bug exacto de un progreso congelado con YouTube hasta
  corregirlo; acá se define el contrato así desde el arranque, no como parche.

Con esto ya fijado en Sesión 2, las Sesiones 4 (Charts player) y 9 (Mi Música)
solo conectan su fuente al contexto — no vuelven a decidir arquitectura de
reproductor ni reinventan el resaltado "sonando".

### Tab 1 — ♪ Biblioteca
- Fuente: `mi_biblioteca` (espejo personal del SQLite) vía `GET /mi-biblioteca`; el
  sync del escritorio (cada 20 min) la mantiene.
- FlashList virtualizada: artista, título, género (con **paraguas Mainstage**), BPM,
  key. Búsqueda y filtro por género (paraguas incluidos, como el panel web). El
  track que suena se resalta en cyan vía `PlayerContext.nowPlaying` (ver "Player
  global").
- **Editar** género/subgénero (taxonomía `GENRE_TREE`, géneros reales, nunca
  paraguas). Guardado optimista → `POST /mi-biblioteca/sync`.
  - ⚠ El backend aplica **last-write-wins con el `actualizado_en` del cliente**: la
    respuesta puede ser 200 con `aplicado: false` (edición descartada por "vieja",
    p. ej. reloj del teléfono atrasado). La UI DEBE leer `aplicado` y avisar/revertir
    — no alcanza con manejar errores HTTP.
- Carátulas: `mi_biblioteca` no tiene `cover_url` y `GET /biblioteca/buscar` hoy
  **no devuelve `cover_url`** (selecciona solo genero/subgenero/bpm/camelot) y es
  1 request por track. V1 sale **sin carátulas en Biblioteca**; si se quieren, es un
  gap de backend (agregar `cover_url` + endpoint de lote), anotado como mejora.

### Tab 2 — ⚡ Charts
- Selector de género (agrupado por paraguas), Top 100 con novedades resaltadas.
- **Preview YouTube**: `react-native-youtube-iframe` (WebView). **Autoplay al entrar
  y reproducción continua** (paridad con escritorio).
- ⚠ **Expectativa fijada**: el modo radio de Charts funciona **con la pantalla
  encendida**. Al bloquear el teléfono, Android pausa el WebView — no hay solución
  limpia (y reproducir YouTube en background viola sus términos). Audio con pantalla
  bloqueada = solo Tab 4 (tu música desde R2).
- Embeds bloqueados por sellos (error 150): fallback → abrir en la app de YouTube
  (deep link). Patrón candidatos+fallback ya resuelto en escritorio.
- Los candidatos los da el **backend** (endpoint nuevo — ver gaps: es la pieza más
  **riesgosa**, no "chica": yt-dlp desde IPs de Render puede sufrir el bloqueo
  anti-bot de YouTube).
- "Para conseguir" desde el móvil: diferido (la tabla es local del escritorio).

### Tab 3 — ▶ Playlists (dos secciones)
- **Propias** (`mis_playlists`): listar, crear, **renombrar, borrar**, agregar desde
  Biblioteca (picker con "crear nueva" inline), quitar, reordenar.
  - ⚠ El backend hoy SOLO tiene `POST` (upsert **por nombre**) y `GET`: renombrar
    crearía una duplicada y borrar es imposible → **gap de backend** (rename/delete),
    ver tabla.
  - ⚠ **Contrato de ids a fijar** (gap): `reglas.ids` debe definirse como *ids de la
    tabla `mi_biblioteca` en la nube*, y confirmar que `cloud_sync.pull_playlists`
    del escritorio los traduce igual (hoy asume que los ids que él subió son sus ids
    locales). Sin esto, playlists creadas en el teléfono pueden llegar mal al
    escritorio. También: el POST pisa la lista completa de ids → un reorder móvil
    puede aplastar tracks agregados desde el escritorio entre syncs; decidir
    estrategia (merge o "última escritura gana" asumida y avisada).
- **Colaborativas** (backend completo: crear/unirse por código/aportar/quitar/
  renombrar/salir/expulsar/borrar — los 10 endpoints verificados contra el código):
  - Unirse con código o crear; ver aportes con autor; aportar desde Biblioteca.
    El track que suena se resalta en cyan igual que en Propias (mismo
    `PlayerContext`).
  - **Realtime** con supabase-js directo (suscribir al entrar, desuscribir al salir;
    fallback botón actualizar). RLS de lectura ya en SQL.
  - Detalle a manejar: si te **expulsan en vivo**, el refetch da 403/vacío — la UI
    sale de la pantalla con un aviso, sin crashear.
  - Escuchar un aporte: preview YouTube (mismo player global).
- Tiers: el stub actual deja pasar a cualquier autenticado — OK para V1; el candado
  real es A8 (futuro).

### Tab 4 — ☁ Mi Música
- Lista de `audio_personal` (`GET /audio/mios`), búsqueda.
- Streaming por **URL firmada** (`GET /audio/{r2_key}/download-url`) directo de R2.
  - ⚠ Las URLs firmadas vencen en **1 hora**: resolver la URL **just-in-time** al
    cargar cada track (no pre-resolver toda la cola), y manejar el error re-firmando.
- Player `react-native-track-player`: background + pantalla de bloqueo.
  - ⚠ **No corre en Expo Go** (código nativo): requiere **development build**
    (expo-dev-client vía EAS) — por eso el dev build se crea ANTES (ver Sesión 8a).
- Prerrequisito de datos: Brian debe subir su biblioteca (~2000 tracks, 50GB,
  ~$0.60/mes) con "☁ Backup en la nube" del escritorio. Acción suya, no de código.

### Perfil
- `GET /me` (devuelve id+email — la "última sincronización" NO existe en la API:
  queda fuera de V1 o se agrega endpoint después), logout, versión de la app.

---

## Qué necesita el backend para esta V1 (gaps)

| Gap | Por qué | Tamaño/riesgo |
|---|---|---|
| Commitear/deployar la migración async ya hecha | La app pega a producción | pendiente 2026-07-01 |
| **Render sin sleep** | Cold start ~1 min mata la UX móvil | config, no código |
| Paginación keyset en `GET /mi-biblioteca` y `/audio/mios` | Miles de tracks | A7, mediano |
| Verificar **Range** en URLs firmadas de R2 | Sin Range no hay seek | A4, chico |
| **Rename + delete de `mis_playlists`** (hoy solo upsert-por-nombre y GET) | Sesión 6 | nuevo, chico |
| **Contrato de `reglas.ids`** (ids de `mi_biblioteca` nube) + verificación de `cloud_sync.pull_playlists` en escritorio | Integridad de playlists tel↔PC | nuevo, mediano |
| Endpoint **unificaciones** (o `umbrella` en `GET /charts/generos` — ojo: el de géneros existente es ese, NO `/biblioteca/generos`) | Filtro Mainstage | nuevo, chico |
| Endpoint **candidatos YouTube** (`GET /charts/{slug}/preview/{posicion}`, reusa `youtube_preview.buscar_candidatos`) | El teléfono no corre yt-dlp | nuevo, **RIESGOSO**: correr en threadpool (no bloquear el event loop async), cache por track, y **probar yt-dlp desde Render** temprano; plan B si YouTube bloquea la IP: precalcular video_ids en la rutina de scrape |

No bloquean V1: A2/A8 tiers, A5 cache charts, A6 rate limit, A9 Sentry, CORS (solo
importa para B10 web — anotado), carátulas en Biblioteca.

---

## Cómo retomar (sesiones frías) — se completa en Sesión 2 y no cambia más

> Una sesión de implementación arranca leyendo SOLO este plan + este bloque + el
> Registro de avance. Nada de releer chats.

- URL backend producción: `https://asistente-biblioteca-dj.onrender.com`
- Proyecto app: `Blioteca Musical/app-movil/` — correr con `npx expo start`
- Env vars de la app (SUPABASE_URL / anon key / API_URL): _(definir en Sesión 2:
  `.env` + `app.config.ts`)_
- Cuenta de prueba: _(definir en Sesión 2)_
- **SDK de Expo pineada**: _(anotar en Sesión 2; ojo: Expo Go se auto-actualiza — si
  pasan meses entre sesiones puede hacer falta subir la SDK)_
- Sesión guardada: decidir en Sesión 2 el patrón para el límite de **2048 bytes de
  SecureStore** (clave de cifrado en SecureStore + sesión cifrada en AsyncStorage).

---

## Sesiones de implementación (para CUANDO se decida arrancar)

Reglas: una sesión = un objetivo cerrado y verificable; al cerrar se actualiza el
Registro de avance y se commitea; si se acaba el contexto, se corta en punto
compilable y se anota; si sobra contexto NO se arranca la siguiente "de yapa".

### Sesión 0 — Prerrequisitos (mayormente Brian)
Node LTS + cuenta Expo + cuenta EAS; Expo Go en el teléfono. Commit+push del backend
async + deploy; Render sin sleep.
*Cierre: `/health` responde rápido dos veces seguidas; Expo Go abre un hello-world.*

### Sesión 1 — Backend para la app (solo backend)
Todos los gaps de la tabla: paginación keyset, Range, rename/delete playlists,
contrato de ids (+ ajuste de `cloud_sync.pull_playlists` si hace falta),
unificaciones, candidatos YouTube (threadpool + cache).
*Cierre: endpoints probados con curl contra producción, **incluida una búsqueda
yt-dlp real desde Render** (si YouTube bloquea, activar plan B antes de seguir).*

### Sesión 2 — Esqueleto de la app + contrato completo del player
Proyecto Expo + TS + Router, tema oscuro (`theme.ts` desde `gui/theme.py`, incluye
el cyan de "sonando"), **cliente HTTP base con JWT + interceptor
401→refresh→retry→login**, login Supabase (patrón SecureStore+AsyncStorage),
navegación 4 tabs vacíos, Perfil con `/me` y logout, **`PlayerContext` completo**
(no solo esqueleto — fuente única, evento de cambio de fuente, `nowPlaying`
compartido, carátula y progreso reales; ver "Player global" arriba). Completar el
bloque "Cómo retomar".
*Cierre: Brian entra con su cuenta en Expo Go, ve tabs y su email.*

### Sesión 3 — Charts: lista y navegación
Selector de género con paraguas, Top 100 con novedades. Sin player todavía.
*Cierre: Brian navega los charts reales desde el teléfono.*

### Sesión 4 — Charts: player YouTube + radio
Charts conecta YouTube como fuente del `PlayerContext` ya definido en Sesión 2
(no arma su propio mini-player ni su propio resaltado): autoplay al entrar,
reproducción continua, fallback deep link (error 150), reporta `coverUrl` y
progreso al contexto. *Cierre: Brian escucha un chart tipo radio (pantalla
encendida) desde el teléfono, y ve la fila resaltada en cyan mientras suena.*

### Sesión 5 — Biblioteca: lista + búsqueda + filtro
FlashList paginada (keyset), búsqueda, filtro con unificaciones. Solo lectura.
*Cierre: navega/busca sus ~2000 tracks fluido.*

### Sesión 6 — Biblioteca: edición + guardado
Detalle/edición (géneros reales), guardado optimista → sync, manejo de
`aplicado: false` (avisar + revertir) además de errores HTTP.
*Cierre: edita un género en el teléfono y lo ve cambiado en el escritorio tras el
próximo sync (~20 min).*

### Sesión 7 — Playlists propias
Sección Propias: listar/crear/renombrar/borrar (endpoints de Sesión 1), picker
"agregar a playlist" desde Biblioteca (con crear inline), quitar, reordenar.
*Cierre: playlist creada en el teléfono aparece bien en el escritorio y viceversa
(verificación del contrato de ids en ambas direcciones).*

### Sesión 8 — Playlists colaborativas
Crear/unirse por código, aportar/quitar, roles, Realtime (suscribir al entrar/
desuscribir al salir) + fallback actualizar, manejo de expulsión en vivo, preview
YouTube de aportes.
*Cierre: dos cuentas ven en vivo lo que aporta la otra.*

### Sesión 8a — Development build (previa a Mi Música)
`expo-dev-client` + EAS Build → instalar el dev build en el teléfono (reemplaza a
Expo Go de acá en más). Sesión corta pero separada: la cola de EAS y la instalación
tienen fricción propia. *Cierre: la app corre desde el dev build con todo lo anterior
funcionando.*

### Sesión 9 — Mi Música (R2)
(Antes: Brian sube su biblioteca con Backup en la nube.) Lista `audio_personal`,
conecta `react-native-track-player` como fuente local del `PlayerContext` (URLs
firmadas **just-in-time**), background + lockscreen. El mini-player persistente
ya existe desde la Sesión 2 — acá solo se activa con esta fuente, no se
reconstruye.
*Cierre: escucha SU música con la pantalla bloqueada; mini-player y resaltado
cyan reflejan el track real.*

### Sesión 10 — Pulido + APK liviano
Estados vacíos/offline, ajustes de tema, EAS Build de producción → APK instalado
(Play Store no hace falta para uso personal).
- **APK lo más liviano posible** (pedido explícito de Brian, 2026-07-19) con las
  técnicas reales disponibles sin Play Store — sin Play Store **no existe**
  descarga de componentes/código nativo después de instalado (eso es "Play
  Feature Delivery", exclusivo de distribución por Play Store; se evaluó y se
  descarta, sigue la decisión de instalación directa para uso personal):
  - Build **por arquitectura** (`arm64-v8a` — cualquier teléfono de los últimos
    ~6 años) en vez de un APK universal con las 4 ABIs adentro.
  - **Hermes** (default de Expo) + recorte de código no usado (R8/ProGuard) en
    el build de producción.
  - Sin assets pesados embebidos: carátulas y demás gráficos siguen sirviéndose
    por URL (V1 ya lo hace así), no empaquetados en el APK.
  - **EAS Update** (OTA) para cambios de JS después de esta sesión, para no
    tener que reinstalar el APK entero por cada ajuste que no sea nativo.
*Cierre: la app corre instalada, sin dev server, y el APK final pesa lo mínimo
posible con estas técnicas (anotar el tamaño final en el Registro de avance).*

Orden 3–9 reordenable si Brian prioriza distinto (adelantar colaborativas, etc.).

---

## Estructura prevista del código

`Blioteca Musical/app-movil/` (mismo repo git):
```
app-movil/
  app/            # rutas: (auth)/login, (tabs)/biblioteca|charts|playlists|musica
  api/            # cliente HTTP (JWT + interceptor 401), supabase auth + realtime
  context/        # PlayerContext (fuente única, nowPlaying, mini-player) — Sesión 2
  components/     # lista de tracks (resaltado cyan), badges de género, mini-player
  features/       # lógica por feature
  theme.ts        # tema oscuro heredado de gui/theme.py (incluye cyan de "sonando")
```

## Lo que la app NO hace (V1, a propósito)
- No escanea ni analiza audio. No escribe en la Biblioteca Confiable (ediciones →
  `mi_biblioteca`; FeelBack móvil = futuro). No tiers/pagos, push, iOS/Web, offline.

## Verificación (del plan, no de código)
Al aprobarse: guardar como `asistente_dj/docs/plan_app_android.md`, referenciar en
`docs/modulo3_nube_backend.md` (Fase 3) y actualizar la memoria. **Sin código.**

## Registro de avance
- 2026-07-04: plan creado, revisado por Fable 5 y corregido. Sin sesiones ejecutadas.
- 2026-07-19: rediseño de etapas tras el reproductor unificado del escritorio —
  Sesión 2 pasa a definir el contrato completo de `PlayerContext` (fuente única,
  evento de cambio de fuente, `nowPlaying`, carátula y progreso reales) en vez de
  un esqueleto; Sesiones 4 y 9 se simplifican a solo conectar su fuente. Orden
  general de sesiones sin cambios (justificación: el resto de los cambios del
  escritorio en esa fecha no tocan backend ni afectan este plan). Sin sesiones
  ejecutadas todavía.
- 2026-07-19: Brian pidió APK lo más liviano posible con descarga de
  "complementos" post-instalación — se aclaró que sin Play Store no existe
  descarga de código nativo después de instalado (Play Feature Delivery es
  exclusivo de Play Store, descartado para mantener instalación directa de uso
  personal). Se acordó en cambio achicar el APK con técnicas reales: build por
  arquitectura (arm64-v8a), Hermes, recorte de código (R8/ProGuard), sin assets
  pesados embebidos, EAS Update para JS post-lanzamiento. Sesión 10 actualizada.
- 2026-07-19: **Sesión 0 arrancada (parcial)**. Hecho: (1) migración async del
  backend (`main.py` lifespan + `supabase_client.py` cliente singleton async +
  router `playlists_compartidas`) commiteada acotada a `backend/` (commit
  `ce55cf6`, sin arrastrar el resto de cambios sueltos del repo) y pusheada a
  `origin/master`; deploy en Render confirmado con el código nuevo (`openapi.json`
  ya expone `/playlists-compartidas`); `/health` responde rápido dos veces
  seguidas en producción (0.56s y 0.34s) — ya estaba corriendo sin problema de
  sleep en este momento, pero **no se configuró "Render sin sleep" de forma
  permanente** (es config del dashboard/plan pago, tarea de Brian, no de
  código). (2) Proyecto Expo creado en `app-movil/` (`create-expo-app
  blank-typescript`, sin repo git anidado): Expo SDK **57.0.7**, React Native
  **0.86.0**, React **19.2.3**, TypeScript **~6.0.3** — anotar como SDK pineada
  para la Sesión 2. `npx expo start` probado en modo LAN (IP de esta PC:
  `192.168.1.9:8081`), Metro respondió OK; se cortó el proceso para que Brian lo
  corra él mismo y vea el QR (el QR no se renderiza en un shell no interactivo).
  **Pendiente para cerrar Sesión 0** (tareas de Brian): Node instalado es v24
  (no es la LTS actual, v22 — probablemente funciona igual con Expo SDK 57 pero
  no se verificó una instalación LTS limpia); crear cuenta Expo + cuenta EAS;
  instalar Expo Go en el teléfono y escanear el QR de `npx expo start` corrido
  desde `app-movil/` (misma red WiFi que esta PC); decidir y configurar "Render
  sin sleep" en el dashboard de Render.
- 2026-07-19: **Sesiones 1 a 10 ejecutadas de corrido** (a pedido explícito de
  Brian, sin pausar entre sesiones). Verificación en cada paso: `tsc --noEmit`
  y `npx expo export --platform android` (bundle real de Metro, 1300+ módulos)
  sin errores; el backend además se verificó con imports reales + `uvicorn`
  local + `openapi.json` en producción. **No se pudo probar nada en un
  teléfono/emulador real** (sin dispositivo disponible en esta sesión) — es la
  verificación que falta y la más importante antes de dar por buena la app.
  - **Sesión 1 (backend)**: paginación keyset (`after_id`/`limit` en
    `/mi-biblioteca`, `before_id`/`limit` en `/audio/mios`), rename/delete de
    `/mi-biblioteca/playlists/{nombre}`, `umbrella` sumado a `/charts/generos`,
    `/charts/{slug}/preview/{posicion}` (yt-dlp en threadpool + cache en
    memoria) y **`/youtube/buscar`** (gap nuevo, no estaba en la tabla
    original: hace falta para "escuchar un aporte" en Playlists, que no tiene
    slug/posición de chart). El contrato de `reglas.ids` ya estaba bien
    resuelto en `cloud_sync.py` sin cambios. Commits `ce55cf6` (async) y
    `58193dd` (gaps Sesión 1) ya pusheados y deployados — **ojo**: `58193dd`
    quedó con `asistente_dj/biblioteca_feedback.py` mezclado por un error mío
    de alcance del commit (Brian decidió dejarlo así, no se corrigió con
    amend/force-push). Falta commitear/pushear `backend/routes/youtube.py`
    (Sesión 8) — ver más abajo. **No se pudo verificar una búsqueda yt-dlp
    real desde Render** (necesita un JWT de sesión real; Brian prefirió no
    completar ese paso ahora) — sigue pendiente confirmar que YouTube no
    bloquee la IP de Render.
  - **Sesión 2**: esqueleto completo en `app-movil/` — Expo Router, `theme.ts`
    (colores de `gui/theme.py`), cliente HTTP con JWT + interceptor
    401→refresh→retry→logout (`api/http.ts`), login Supabase con el patrón
    `LargeSecureStore` (SecureStore para la clave + AsyncStorage cifrado para
    la sesión, por el límite de 2048 bytes), 4 tabs + Perfil, `PlayerContext`
    completo (fuente única, `nowPlaying`, progreso/carátula reales — sin
    evento aparte de "cambió la fuente": al vivir en contexto de React, el
    re-render de los suscriptores ES la notificación).
  - **Sesión 3**: selector de géneros agrupado por paraguas + Top 100 con
    novedades resaltadas (`app/(tabs)/charts/`).
  - **Sesión 4**: `YoutubeRadioPlayer` — autoplay + reproducción continua,
    candidatos+fallback (siguiente candidato → deep link a la app de YouTube
    si ninguno embebe), progreso real vía polling de `getCurrentTime`.
  - **Sesión 5**: `FlashList` (v2, sin `estimatedItemSize`) con búsqueda y
    filtro por paraguas (`api/unificaciones.ts`, leído directo de Supabase con
    RLS abierta, igual que Realtime).
  - **Sesión 6**: edición género/subgénero (chips desde `GENRE_TREE`),
    guardado optimista → `/mi-biblioteca/sync`, manejo de `aplicado: false`
    (revierte y avisa, no solo mira el status HTTP).
  - **Sesión 7**: Propias — listar/crear/renombrar/borrar, picker "agregar a
    playlist" con crear inline (`ModalAgregarAPlaylist`, ida desde Biblioteca),
    quitar, reordenar (con botones arriba/abajo, no drag-and-drop — se evitó
    sumar una librería de gestos solo para esto).
  - **Sesión 8**: Compartidas — crear/unirse por código, aportar/quitar,
    roles, Realtime (suscripción a las 3 tablas, fallback pull-to-refresh),
    expulsión en vivo (403 → alerta + `router.back()`, sin crashear), "escuchar
    un aporte" vía el nuevo `/youtube/buscar` + `YoutubeTrackPreview`.
  - **Sesión 8a**: `expo-dev-client` + `eas.json` (perfiles
    development/preview/production, production en `apk` no `app-bundle` — sin
    Play Store). **No se corrió ningún build real** (necesita `eas login` con
    la cuenta de Brian). Falta que Brian corra `eas init` (vincula el
    project id en `app.json`) y `eas build --profile development --platform
    android`.
  - **Sesión 9**: `react-native-track-player` conectado como fuente `local` del
    `PlayerContext`, URLs firmadas resueltas just-in-time (`api/audio.ts`),
    background/lockscreen vía `service.ts` + capabilities. **Riesgo real
    detectado por `expo-doctor`**: react-native-track-player 4.1.2 (última
    estable; la 5.0.0 que sí anuncia New Architecture está en alpha) figura
    como "Unsupported on New Architecture" en React Native Directory, y Expo
    SDK 57 usa New Architecture por default. No se desactivó New Architecture
    para acomodarlo (rompería `@shopify/flash-list` v2, que sí la requiere) —
    queda **sin verificar si el audio realmente reproduce** en un dev build
    real; es la primera cosa a probar en el teléfono. Si falla: alternativas
    son esperar react-native-track-player 5 estable, o migrar a `expo-audio`
    + notificación manual (perdiendo algo de sofisticación de lockscreen).
  - **Sesión 10**: banner "sin conexión" (`@react-native-community/netinfo`,
    overlay global, sin cachear nada — V1 100% online), `expo-build-properties`
    (build por `arm64-v8a` únicamente, R8/ProGuard + shrink resources,
    compresión del bundle JS), `expo-updates` instalado + `runtimeVersion`
    fijada (`policy: appVersion`) para EAS Update — falta que Brian corra `eas
    update:configure` (necesita el project id de `eas init`). **No se generó
    ningún APK real** (necesita EAS, cuenta de Brian) — no hay tamaño final
    para anotar todavía.
  - **Pendiente de Brian** (ninguno es de código): probar el hello-world y
    todo lo demás en un teléfono real; `eas login` + `eas init` + `eas build
    --profile development`; instalar el dev build y recién ahí probar Mi
    Música (el riesgo de New Architecture de arriba); `eas update:configure`;
    decidir "Render sin sleep"; y — el más importante — el yt-dlp real desde
    Render (Sesión 1) sigue sin confirmarse.
