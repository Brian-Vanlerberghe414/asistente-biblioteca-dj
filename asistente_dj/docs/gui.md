# GUI (PySide6)

> Doc de módulo. Ver `CLAUDE.md` (raíz) para la tabla de ruteo completa y
> el contexto general del proyecto.

Arranca con `python app.py` (desde `asistente_dj/`).

## Estado actual

GUI ya tiene: grilla de tracks editable, árbol de géneros navegable
(acordeón — un color por género, sin flechitas/recuadros, alineado a la
izquierda), reproductor con cola y shuffle inteligente (BPM/armónico),
panel de detalle, filtros (texto/BPM/key/energía), selector de energía
manual, import de carpetas, export de playlists a Rekordbox, pestañas en
horizontal **Biblioteca - Playlist - Charts**.

## Arquitectura

- `app.py` — punto de entrada de la GUI.
- `gui/main_window.py` — ventana principal, toolbar, pestañas.
- `gui/organizador.py` — grilla + reproductor con cola/shuffle inteligente;
  el árbol de géneros ya NO tiene nodo de playlists (se movió a su propia
  pestaña).
- `gui/playlists_widget.py` — pestaña Playlist: lista de playlists con
  renombrar/borrar/exportar a Rekordbox + grilla de solo lectura de sus
  tracks; la creación de playlists sigue siendo desde Biblioteca con
  selección de tracks + botón "➕ Playlist".
- `gui/track_model.py` — modelo de tabla editable.
- `gui/detalle_panel.py` — panel de detalle.
- `gui/track_table_view.py`, `gui/waveform_widget.py`, `gui/theme.py` —
  soporte visual.
- Delegates de edición inline (género, BPM, artista): `gui/genero_delegate.py`,
  `gui/bpm_delegate.py`, `gui/delegate_artista.py`. Delegates de
  visualización (lectura): `gui/visual_delegates.py`
  (`BpmDelegate`/`CamelotDelegate`/`EnergyDelegate`/`StatusDelegate`/
  `PlayButtonDelegate`/`CoverDelegate`).
- `gui/workers.py` — todos los `QThread` (Scan/Analyze/Archive/DjImport/
  CoverFill/Sync/BackupNube/etc.).
- `gui/cover_loader.py` (`CoverLoader`, singleton) — descarga asíncrona de
  carátulas (`QNetworkAccessManager`, sin bloquear la UI), caché en
  memoria compartida entre la grilla de Biblioteca y la de Playlist.
- `gui/artistas_widget.py` y sus workers existen pero todavía no están
  conectados a `main_window.py`.
- `gui/charts_widget.py` — pestaña Charts: barra lateral de charts +
  precarga del track #1 + reproducción continua en YouTube (sesión
  2026-06-23, detalle completo en `docs/modulo2_descubrimiento.md`).

## Carátulas en vivo durante el escaneo (sesión 2026-06-22)

Columna local `cover_url` en `tracks` (migración suave en `db.py`).
`scanner.scan()` trae `cover_url` de la Biblioteca Confiable en el mismo
lookup que ya hacía para género — si no está ahí, queda `NULL` y lo
resuelve `CoverFillWorker` (`gui/workers.py`): corre automático en
background apenas termina el análisis que sigue a un escaneo (no pasa por
`MainWindow._lanzar`, así no bloquea la toolbar mientras busca). Por cada
track sin `cover_url`: primero pregunta a la Biblioteca Confiable (puede
que otro DJ ya la subió), si no está ahí busca en iTunes (`itunes_cover.py`,
ver `docs/modulo1_organizador.md`) y lo que encuentra lo sube de vuelta a
la nube (parte backend en `docs/modulo3_nube_backend.md`). Las carátulas
aparecen en vivo en la grilla (columna nueva, primera tras el play/check)
a medida que se encuentran, sin recargar todo el modelo:
`TrackModel.actualizar_cover(track_id, url)` actualiza solo esa celda.
`gui/visual_delegates.py:CoverDelegate` pinta la miniatura cuando ya está
en caché, y no pinta nada mientras se descarga (aparece sola).

## Pendiente de conectar a la GUI (el motor ya funciona por CLI)

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

## Sincronización con la nube (sin botón, automática)

Ver el detalle técnico completo en `docs/modulo3_nube_backend.md`
(sección "Sincronización de biblioteca personal") — desde la GUI no hay
botón "Sincronizar": corre sola al arrancar, cada 20 minutos, y al cerrar
la app (`gui/workers.py:SyncWorker`, `MainWindow._iniciar_sync`/`closeEvent`).

## Bugs/fixes de UI resueltos (sesión 2026-06-23)

- **Botón "Seleccionar" no dejaba tildar los checkboxes**: el delegate
  genérico (`QStyledItemDelegate`) usado para pintar el checkbox en modo
  selección tiene su propio manejo nativo de click-para-tildar en
  `editorEvent`, que solo se activa una vez que la celda ya es la "actual"
  (no en el primer click, que solo la enfoca) — esto competía con el
  toggle explícito agregado en `OrganizadorWidget._on_click`, generando un
  doble-toggle que anulaba el segundo click en adelante. Fix:
  `_SoloPintarCheckboxDelegate` (en `gui/organizador.py`) con
  `editorEvent` inerte (`return False`) — el único que togglea ahora es
  `_on_click`, un solo toggle por click real, siempre.
- **Árbol de géneros**: acordeón (un solo género desplegado a la vez,
  `_on_genero_expandido`), un color distinto por género (incluso sin
  subgéneros, `theme.GENRE_COLORS`), sin flechitas/recuadros de expandir
  (`setItemsExpandable(False)` + QSS `QTreeWidget::branch{image:none}`),
  alineado a la izquierda.
- **BPM/Key**: BPM al mismo tamaño de fuente que el resto de la grilla
  (antes usaba tamaño en puntos en vez de píxeles); badges de Key con
  ancho fijo (antes "8A" quedaba más chico que "11A").

## Edición masiva / botón Seleccionar = Acción masiva (sesión 2026-06-23)

El botón **"☐ Seleccionar"** (en `filtros_bar`, dentro de `OrganizadorWidget`)
ya no es un simple toggle — es una máquina de estados de 3 textos
(`_on_click_btn_seleccionar`/`_actualizar_texto_btn_seleccionar` en
`gui/organizador.py`, `self._modo_seleccion: bool`, NO usa
`setCheckable(True)` de Qt — se maneja a mano para poder distinguir el
3er caso):

1. **Apagado**: "☐ Seleccionar". Click → prende modo selección.
2. **Prendido, 0 tildados**: "✓ Seleccionando". Click → apaga modo
   selección (toggle simple, igual que antes).
3. **Prendido, ≥1 tildado**: "⚡ Acción masiva (N)" — el texto se
   actualiza en vivo a medida que se tilda/destilda. Click → NO apaga el
   modo selección, abre un `QMenu` (`_abrir_menu_acciones_masivas`) anclado
   al botón con las acciones disponibles (hoy solo "🏷 Cambiar género…",
   pensado para sumar más entradas sin tocar la interacción). Al cerrarse
   el menú — se elija una acción, se cancele el diálogo, o se cierre sin
   elegir nada — el modo selección se apaga siempre.

Se sacó el botón separado "🏷 Género en lote" de la toolbar principal
(`gui/main_window.py`) — la única forma de llegar a "Cambiar género" ahora
es por este menú. `OrganizadorWidget.editar_genero_en_lote()` (la lógica
del diálogo de género/subgénero en sí) no cambió — sigue marcando el
cambio como **pendiente** vía `TrackModel.marcar_genero_lote(ids, genero, subgenero)`
(reutiliza `setData`/`_pendientes`, fila en amarillo + barra
Guardar/Cancelar, no escribe directo), y al guardar sube todo en un solo
lote (ver `docs/modulo3_nube_backend.md`, "Push también agrupado").
