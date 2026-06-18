# Asistente de Biblioteca DJ — Documento de Concepto

> Documento de diseño conceptual. Define qué hará el programa y cómo, para retomarlo cuando arranquemos a construirlo. Todavía no es una especificación técnica final.

**Usuario:** Brian — DJ de música electrónica
**Software de DJ:** Rekordbox (Pioneer)
**Tamaño de biblioteca:** 2.000 – 10.000 tracks
**Fecha del concepto:** Junio 2026

---

## Visión general

Una **app de escritorio con interfaz gráfica** para uso cotidiano, con dos grandes módulos:

1. **Organizador** — mantiene la biblioteca limpia, ordenada y archivada por género, con organización dinámica sin mover archivos.
2. **Descubrimiento** — monitorea charts de Beatport, avisa novedades, deja escuchar desde YouTube Music dentro del programa y exporta listas de tracks de interés.

Principio rector: **el almacenamiento físico es uno solo y estable; la organización en pantalla es flexible e ilimitada.**

---

## Módulo 1 — Organizador

### 1.1 Almacenamiento físico (por género)

- El programa **copia** la biblioteca y la archiva en estructura jerárquica `Género/Subgénero`.
- Cada track vive en **una sola carpeta** → sin duplicados ni archivos sueltos.
- **Género dudoso o desconocido:** el programa **pregunta en el momento** antes de archivar (máximo control, decisión de Brian track por track).
- El árbol de géneros/subgéneros se define al inicio y se puede ajustar con el tiempo.

#### Árbol de géneros definitivo (basado en taxonomía Beatport)

```
Techno/
  Peak Time - Driving
  Melodic Techno
  Minimal - Deep Tech

House/
  Progressive House
  Tech House
  Bass House
  Afro House        (agregado tras ver la biblioteca real)
  Organic House     (agregado)
  Electro House     (agregado)

Trance/
  Main Floor
  Tech Trance
  Progressive Trance
  Psy-Trance

Indie Dance/
  (Nu Disco — opcional, a definir más adelante)

Big Room/           (Big Room / Mainstage — agregado)

_Ingreso/        → música nueva descargada; el programa la clasifica y archiva sola
_Por revisar/    → género dudoso, pendiente de decisión manual
```

> **Nota técnica:** Beatport escribe varios nombres con barra (`Raw / Deep / Hypnotic`). La barra `/` no se puede usar en nombres de carpeta (crea subcarpetas falsas), por eso en disco se reemplaza por guion (`Raw - Deep - Hypnotic`). El programa puede mostrar el nombre original de Beatport en pantalla y usar el nombre "seguro" en el sistema de archivos.

### 1.2 Carpeta de ingreso automático

- Hay una **carpeta destinada al ingreso** de música nueva descargada.
- El programa detecta el archivo nuevo, lo **analiza por audio** para determinar el género (criterio elegido: siempre analizar audio, ignorando el tag para mayor consistencia) y lo archiva en la carpeta correcta.
- Si hay duda, consulta antes de archivar.

### 1.3 Organización dinámica (vistas, sin mover archivos)

- Sobre la misma biblioteca física, Brian reorganiza la vista **todo el tiempo** según:
  - Género
  - BPM
  - Artista
  - Sello
  - Intensidad / energía
  - Valoración personal
- **Combinaciones libres.** Ejemplo: *Melodic Techno + 122–124 BPM + valoración ≥ 4 + sello X.*
- Estas vistas son filtros y ordenamientos; **no mueven ni duplican archivos**.

### 1.4 Metadatos y calidad

- Completado de metadatos faltantes: género, BPM, key, artista, sello, año.
- Detección de **duplicados** por huella de audio (no solo por nombre).
- Detección de archivos de **baja calidad** (ej. mp3 de bitrate bajo).
- **Análisis de energía / vibe**: automático con **ajuste manual** (el programa sugiere, Brian confirma o corrige al escuchar).

### 1.5 Playlists inteligentes

- Se crean por **reglas**, ej: *"todo Deep House entre 120–124 BPM con energía media-alta y valoración ≥ 4"*.
- La playlist se **llena sola** según las reglas y se mantiene actualizada.
- **Exportación automática a Rekordbox** vía XML.

### 1.6 Creador de DJ sets + chequeo de derechos de autor (YouTube)

- Brian arma el **orden del set** dentro del programa.
- El programa hace una **verificación track por track**, cruzando cada uno con información conocida de sellos / Content ID.
- Devuelve un **semáforo de riesgo** (alto / medio / bajo) con el motivo, para decidir antes de subir la mezcla a YouTube.

> **Aclaración importante:** ningún sistema externo puede predecir con certeza qué hará el Content ID de YouTube — solo YouTube lo determina al procesar el video. Esta función es una **estimación orientativa** basada en patrones conocidos (qué sellos reclaman, qué tracks suelen marcarse), que reduce sorpresas pero no garantiza el resultado.

### 1.7 Integración con Rekordbox

- Modo **solo lectura + exportación XML**: el programa lee la colección y genera un XML que Brian importa en Rekordbox.
- **Cero riesgo** para la base de datos de Rekordbox (no la modifica directamente).

---

## Módulo 2 — Descubrimiento de música nueva

### 2.1 Charts de Beatport — explorador dentro de la app

- La app muestra los charts **en su propio diseño limpio** (lista propia con datos), no la web de Beatport embebida.
- **Charts soportados:** Top 100 por género y Hype 100 por género.
- **Navegación "fijos + explorar":**
  - **Mis charts** → favoritos fijados por Brian, siempre listos al abrir (cada uno con contador de novedades).
  - **Explorar** → árbol completo de géneros de Beatport para entrar a cualquier Top 100 / Hype y fijarlo con un pin.
- **Cruza cada novedad con la biblioteca** y marca: *"ya lo tenés"*, *"encaja con tu estilo (BPM/key/sello)"*, *"no es lo tuyo"*.
- Uso legítimo de información pública de charts (sin compras).

> **Cómo se obtienen los datos de los charts (decisión de Brian): empezar público, migrar a API.**
> Los charts (Top 100 / Hype) son **públicos** en beatport.com — no requieren credenciales para verse. Plan en dos fases con diseño intercambiable (misma interfaz interna, distinto backend abajo):
> 1. **Fase 1 — lectura de páginas públicas:** funciona ya, sin esperar credenciales. Contras: más frágil (se rompe si Beatport cambia la web), la web es muy dinámica (puede requerir render de JavaScript), y es zona gris respecto a los términos de uso.
> 2. **Fase 2 — API oficial v4 (OAuth):** cuando lleguen las credenciales. Datos limpios, estables y permitidos. Se cambia solo el backend, sin tocar el resto.

### 2.2 Seguimiento en el tiempo (nuevo ingreso / salida)

- El programa guarda una "foto" del chart en cada revisión y la compara con la anterior.
- Estados de cada track:
  - **Nuevo ingreso** → apareció desde la última revisión. Avisa para escucharlo.
  - **Escuchado** → Brian lo marca; deja de aparecer como pendiente.
  - **Salió sin escuchar** → si desaparece del chart y nunca se marcó como escuchado, pasa **automáticamente a la lista de pendientes**.

### 2.3 Preview con YouTube Music integrado

- Para cada track que no esté en la biblioteca, el programa busca la coincidencia en YouTube y permite **escucharlo en un panel embebido**, sin salir de la app.
- Permite evaluar el chart completo de corrido sin saltar entre pestañas.

### 2.4 Selección y exportación a texto

- Brian marca con un **check** los tracks que le gustan (en charts o en pendientes).
- Botón **"Exportar"** → genera una **lista de texto limpia**, una entrada por línea (ej. `Artista - Título (Mix)`), lista para copiar y pegar.
- Formato configurable: estilo del nombre y si se incluye sello / BPM / key.

---

## Límites y consideraciones

- **Muzrec:** no se integrará descarga automática ni asistida desde Muzrec. Es un servicio que redistribuye música sin autorización de los sellos (la membresía es a Muzrec, no a los dueños de la música). El programa cubre todo el trabajo tedioso —filtrar, escuchar, decidir, armar la lista curada—; el paso final de conseguir cada track queda por fuera del programa.
- **Beatport:** solo se usan sus charts (lectura). No hay función de compra.
- **Chequeo de derechos:** orientativo, no garantía (ver 1.6).

---

## Stack técnico definitivo

Decisión clave: **Python de punta a punta**. El análisis de audio (lo más pesado) vive en el ecosistema Python, así que usar Python también para la interfaz evita tener dos lenguajes comunicándose entre sí.

| Pieza | Elección | Por qué |
|---|---|---|
| Lenguaje | **Python** | Un solo lenguaje; donde viven las librerías de audio |
| Interfaz (GUI) | **PySide6 (Qt)** | Tablas grandes y rápidas (miles de tracks), reproductor de audio nativo (QtMultimedia), embed de YouTube (QWebEngineView) |
| Análisis de audio | **Essentia** (+ librosa de apoyo) | BPM, key e intensidad/energía confiables |
| Detección de duplicados | **Chromaprint (fpcalc)** | Huella acústica: detecta repetidos aunque cambie el nombre |
| Tags / metadatos | **Mutagen** | Lectura y escritura de etiquetas |
| Charts de Beatport | **API oficial Beatport v4 (OAuth2)** | Datos limpios y permitidos para uso no comercial; respaldo: lectura de páginas públicas |
| Base de datos local | **SQLite** | Local, sin servidor |
| Exportar a Rekordbox | **Generación de XML** | Cero riesgo para la base de Rekordbox |

### Nota sobre el acceso a la API de Beatport

- La API de Beatport (v4, OAuth2) incluye charts, Top 100, metadatos y previews.
- Es de **uso no comercial** → compatible con el uso personal de Brian.
- Requiere **solicitar credenciales** describiendo el uso (contacto: equipo de ingeniería de Beatport).
- **Plan:** solicitar credenciales oficiales; si no se obtuvieran, usar lectura de páginas públicas como respaldo.

---

## Diseño de pantallas (bocetos)

La app tiene una barra superior con tres pestañas: **Organizador · Descubrimiento · DJ Sets**. Layout de escritorio, ~680 px de ancho de referencia.

### Pantalla 1 — Organizador

- **Barra lateral izquierda:** árbol de géneros (`Techno`, `House`, `Trance`, `Indie Dance`) desplegable a subgéneros, con contador de tracks. Abajo, carpetas de sistema `_Ingreso` (con badge de archivos nuevos detectados) y `_Por revisar`.
- **Barra de filtros (arriba):** chips combinables, cada uno una condición que se suma (ej. `BPM 120–124` + `Intensidad ≥ 7` + `★ ≥ 4`). Botón "Guardar como playlist" convierte los filtros activos en una playlist inteligente.
- **Tabla central:** título, sello, BPM, key, valoración (★) e intensidad. Botón play por fila para preview.
- **Reproductor inferior:** track actual, barra de progreso, y acceso a "Exportar XML Rekordbox".

### Pantalla 2 — Descubrimiento

- **Selector de chart** (ej. "Beatport · Melodic Techno Top 100") + resumen de estado: cuántos nuevos, cuántos pendientes, última revisión.
- **Lista central:** cada track con checkbox de selección, estado con color (verde = nuevo ingreso, ámbar = pendiente/salió sin escuchar, gris = ya escuchado) y columna "en biblioteca" (si ya lo tenés).
- **Panel derecho:** preview de YouTube Music embebido con controles; abajo, contador de seleccionados y botón "Exportar a lista de texto".

### Pantalla 3 — Creador de DJ Sets

- **Cabecera del set:** nombre, cantidad de tracks, duración, botón "Revisar derechos YouTube".
- **Resumen tipo semáforo:** tarjetas con conteo de riesgo bajo / medio / alto.
- **Lista ordenable** (arrastrar para reordenar): cada track con su sello y su semáforo de riesgo de derechos. Los sellos *major* (Universal, Sony, Warner y subsellos) tienden a riesgo alto por reclamos vía Content ID; sellos independientes, riesgo más bajo.
- **Pie:** recordatorio de que la estimación es orientativa y no garantiza el resultado real de YouTube.

---

## Esquema de base de datos (SQLite)

### Biblioteca (Módulo 1)

- **`generos`** — `id`, `nombre`, `padre_id` (jerarquía Género→Subgénero), `nombre_beatport` (nombre lindo para pantalla), `nombre_carpeta` (nombre seguro en disco, sin `/`).
- **`tracks`** — núcleo del sistema:
  - Archivo: `id`, `ruta_archivo`, `genero_id`, `bitrate`, `formato`, `huella_acustica` (Chromaprint, para duplicados).
  - Metadatos: `titulo`, `artista`, `sello`, `año`, `bpm`, `key`, `duracion`.
  - Clasificación: `energia` (calculada por el programa) y `energia_confirmada` (ajuste manual de Brian, separada para no pisar su criterio); `valoracion` (★).
  - Gestión: `fecha_ingreso`, `origen`, `estado` (`archivado` / `por_revisar`).
- **`playlists`** — `id`, `nombre`, `tipo`, `reglas` (JSON), `exportar_rekordbox`. **Las playlists inteligentes guardan reglas, no tracks** → se evalúan al momento y se actualizan solas cuando entra música nueva.

### Descubrimiento (Módulo 2) — charts con memoria

- **`charts`** — `id`, `nombre`, `genero`, `tipo` (`top100` / `hype`), `fijado` (pin de "Mis charts").
- **`chart_snapshots`** — la "foto" del chart en cada revisión: `chart_id`, `fecha`, y las entradas (`posicion`, `track_beatport_id`). Comparar el último snapshot con el anterior es lo que detecta entradas y salidas.
- **`chart_tracks`** — estado vivo de cada track de chart: `track_beatport_id`, `titulo`, `artista`, `sello`, `estado` (`nuevo` / `escuchado` / `pendiente`), `seleccionado` (para exportar), `en_biblioteca_id` (cruce: si ya lo tenés, apunta al track de tu biblioteca).

### DJ Sets (Módulo 1)

- **`sets`** y **`set_tracks`** — `set_id`, `track_id`, `posicion` (orden del set).
- **`sellos_riesgo`** — alimenta el semáforo de YouTube: `sello`, `riesgo` (`bajo` / `medio` / `alto`), `motivo`.

---

## Decisiones tomadas (resumen)

- Software DJ objetivo: **Rekordbox**, vía **XML de solo lectura**.
- Almacenamiento físico: **Género/Subgénero (jerárquico)**, un track = una carpeta.
- Género dudoso: **preguntar en el momento**.
- Ingreso automático: **clasificar siempre por análisis de audio**.
- Energía/vibe: **automático + ajuste manual + aprendizaje**. Cálculo automático por defecto = **90% análisis acústico + 10% tonalidad + 10% BPM** (pesos relativos, ajustables; calibrados con Brian), rankeado por percentiles. Se recalcula sin re-analizar audio (mejora al traer el BPM exacto de Rekordbox). La energía manual (`rate`) siempre manda.

### Calibrar Energía (✅ construido) — el sistema aprende el oído del DJ

Idea de Brian. Comando `calibrate`: el programa reproduce un fragmento de ~30s (vía `ffplay`) de tracks **al azar**, el DJ los califica **1-10**, y con esas calificaciones **aprende su percepción**:
- Guarda los **rasgos acústicos individuales** de cada track (graves/kick, brillo, densidad rítmica, volumen) + BPM + tonalidad como entradas.
- Ajusta por **regresión (mínimos cuadrados)** un modelo personalizado que reproduce las calificaciones del DJ (validado: recupera los pesos con ~0 error).
- Aplica ese modelo a **toda la biblioteca** y a los análisis futuros, así la energía se parece cada vez más al criterio del DJ.
- Las calificaciones manuales quedan como verdad; cuantas más, mejor aprende (mínimo 12 para empezar).
- Cada DJ entrena su propio modelo (pensado para que el programa sirva a varios).
- **Reproduce el momento más intenso del track** (no un punto fijo): `pico_intensidad` decodifica el track a baja resolución y busca el pico de energía RMS, así el DJ califica el "drop" real (idea de Brian, validado).
- **Calibra dentro de un mismo género/subgénero** para que la comparación sea consistente: por defecto agarra el género con más tracks sin calificar; se puede fijar con `--genero` / `--subgenero` (idea de Brian).
- Charts: **Beatport** (lectura).
- Preview: **YouTube Music embebido**.
- Chequeo de derechos: **estimación por base de datos** (semáforo).
- Interfaz: **app de escritorio con GUI (PySide6 / Qt)**.
- Lenguaje: **Python** de punta a punta.
- Charts: **API oficial de Beatport v4 (OAuth2)**, uso no comercial; respaldo por páginas públicas.
- Orden de construcción: **motor primero, visual después** (opción A). Se construye y prueba la lógica (escaneo, archivado, base de datos) antes de invertir en la interfaz definitiva. Los bocetos de pantallas ya están definidos como guía.

---

## Próximos pasos (cuando arranquemos)

1. ~~Definir el árbol completo de géneros/subgéneros de Brian.~~ ✅ **Hecho** (ver sección 1.1).
2. ~~Bocetar las pantallas (organizador, vistas dinámicas, descubrimiento, creador de sets).~~ ✅ **Hecho** (ver sección "Diseño de pantallas").
3. ~~Cerrar el stack técnico definitivo.~~ ✅ **Hecho** (ver sección "Stack técnico definitivo").
4. ~~Diseñar el esquema de la base de datos local.~~ ✅ **Hecho** (ver sección "Esquema de base de datos").
5. ~~Construir un primer prototipo del Módulo 1 (escaneo + archivado por género).~~ ✅ **Hecho** — ver carpeta `asistente_dj/` (escaneo, clasificación por género, _Por revisar, copia a Género/Subgénero, base SQLite, probado por consola).

### Siguientes etapas de construcción (post-prototipo)

6. ~~Análisis de audio (energía/intensidad, BPM y key calculados).~~ ✅ **Hecho** — implementado con **ffmpeg + numpy** (no Essentia: mucho más fácil de instalar en Windows y testeable). Comando `analyze`: BPM (±0.3 en pruebas), key con Camelot, energía 1-10, y sugerencia de género por rangos para tracks sin tag. **Hallazgo del escaneo real:** de 2.389 tracks, 1.026 se clasificaron por tag y 1.120 no tienen tag de género (de ahí la importancia del análisis de audio).
6b. ~~Integración con Rekordbox.~~ ✅ **Hecho.** Dos direcciones:
   - **Import (verificación):** `import-rekordbox` lee el export XML de Rekordbox y trae BPM/key, matcheando por ruta y, si difiere, por artista+título. Reutilizable como cross-check contra los datos de Beatport.
   - **Import Traktor (✅ hecho):** `import-traktor` lee el `collection.nml` (NML/XML) y trae BPM/key, reconstruyendo las rutas con formato Traktor (`/:`). Usa el mismo matching que Rekordbox (helper compartido). Marca fuente `traktor`.
   - **Export de playlists:** `playlist-create` (reglas por género/subgénero/BPM/key/energía, respeta la energía manual), `playlist-list`, `playlist-export` → escribe un `rekordbox.xml` con COLLECTION + PLAYLISTS que Rekordbox importa (validado por round-trip). Cero riesgo: solo escribe un archivo nuevo.
   - `rate` fija energía manual (tu valor manda sobre el automático).

**Estrategia de fuente de datos (BPM/key/género) — por identificación online:**

- **Beatport API v4** (fuente ideal): expone `bpm`, `key` con Camelot, `genre` y `sub_genre`. Identificación por tags (artista/título/mix). **Pendiente:** credenciales OAuth (uso no comercial), aprobación manual, tarda días.
- **GetSongBPM** (✅ construida, pero ⚠️ cobertura insuficiente para este catálogo): API pública gratuita (`api.getsong.co`), BPM + key. Funciona técnicamente (validado con tracks mainstream), pero su base está sesgada a música mainstream/antigua y **NO tiene el catálogo de Brian** (Afro/Organic/Melodic House underground y reciente): prueba de 12 tracks reales = 0 encontrados con nombres ya limpios. El buscador limpia títulos (saca Original/Extended Mix, feat., nº de pista) y artista principal, con reintento por título — pero el problema es ausencia de datos, no de formato. Queda como apoyo marginal.
- ⚠️ **Spotify quedó descartado:** deprecó los endpoints de audio-features/audio-analysis (BPM, key, energía) el 27/11/2024; las apps nuevas reciben 403, sin reemplazo.

Orden de prioridad de fuentes para BPM/key: Rekordbox (si se importa) > Beatport (cuando haya credenciales) > GetSongBPM > análisis de audio propio (fallback).

---

## Escalabilidad — primer arranque con biblioteca grande (~6.000 tracks)

Pensado para que el programa sirva también a otros DJs, no solo a Brian.

**Aclaración clave:** NO hay "ida y vuelta" con el software DJ. El usuario ya tiene su biblioteca analizada en Rekordbox/Serato/Traktor (parte de su prep normal); el programa solo **lee** ese export. Y de todo lo que calculamos, BPM y key vienen gratis del tag o del software DJ — lo único que realmente exige procesar audio es la **energía**.

**Cascada de datos (cada track toma el dato de la fuente más barata):**
1. Tag del archivo → instantáneo (muchos ya traen BPM/key de Beatport).
2. Export del software DJ (Rekordbox/Serato/Traktor) → rápido, solo parsear.
3. Análisis de audio propio → solo para los huecos. Lo único pesado.

La **energía** siempre necesita audio: se calcula en el análisis y se ajusta manual.

**Decisiones de Brian para el arranque:**
- Flujo: **analizar todo primero** (pasada completa antes de usar), pero con la cascada para no recalcular lo que ya tiene fuente.
- Profundidad: **tramo de ~75s** (no el track entero) — casi misma precisión, mucho más rápido.
- Software DJ a soportar: Rekordbox (✅ hecho), **Serato** y **Traktor** (a construir).

**Optimizaciones del análisis (✅ implementadas y validadas):**
- **Tramo parcial** (ventana de ~75s vía ffmpeg `-ss`/`-t`): ~2.4x más rápido, BPM/key igual de precisos.
- **Multinúcleo** (multiprocessing): ~Nx según núcleos.
- **Cache** (flag `analizado`): cada track se analiza una sola vez; reescaneos no recalculan.
- Medido: **4.1x** con solo 2 núcleos (tramo+paralelo); en una PC de 8 núcleos, ~10x. 6.000 tracks pasan de horas a ~15 min, una sola vez.
- Comando: `analyze --procesos N` (0 = todos los núcleos).
7. ~~Detección de duplicados por huella acústica (Chromaprint).~~ ✅ **Hecho** — `fingerprint` calcula la huella con fpcalc (multinúcleo); `duplicates` compara por bit-error-rate, agrupa con tolerancia de duración (union-find) y sugiere conservar el de mejor calidad (lossless > mayor bitrate). Validado: re-codificaciones del mismo tema se detectan (BER ~0.05) y temas distintos no (BER ~0.50), umbral 0.15. Requiere `fpcalc.exe` (Chromaprint) en el PATH.
8. ~~Ingreso de música nueva.~~ ✅ **Hecho** — rediseñado como **Importar música** (decisión de Brian, reemplaza la vigilancia automática): comando `import` que toma una carpeta de origen (recursivo), **copia** cada track a la biblioteca del asistente organizándolo por género, y cuando NO reconoce el género **le pregunta al usuario eligiendo de una lista numerada** (reproduce el momento más intenso para ayudar a decidir). Al final ofrece **borrar los originales** (una vez, para todos) para ahorrar espacio. La **raíz de la biblioteca es configurable** (`config --biblioteca`, se elige al instalar), guardada en `settings.py` (asistente_config.json). El módulo `intake.py` quedó con un callback de selección de género reutilizable para la tarea de "resolver tracks sin género". Validado de punta a punta (copia, elección manual, SKIP y _Por revisar).
9. Playlists inteligentes + exportación XML a Rekordbox.
10. Módulo 2 (charts de Beatport vía API) y creador de sets con chequeo de derechos.
11. Interfaz gráfica con PySide6 sobre el motor ya funcionando.
