# Base de datos (SQLite local)

> Doc transversal. Ver `CLAUDE.md` (raíz) para la tabla de ruteo completa.
> El esquema lo tocan los Módulos 1, 2 y 3 por igual; está separado de
> esos docs para no forzar a cargar uno entero solo para consultarlo.

Tabla `tracks` (núcleo): ruta_origen/destino, titulo, artista, sello, anio, bpm,
key, camelot, duracion_seg, genero_raw, genero, subgenero, confianza (tag/manual/
supabase — protege de re-escaneos), genero_sugerido, subgenero_sugerido,
nota_sugerencia (texto, incluye el top-3 de `genre_profiles`), energia,
energia_manual, energia_raw, f_loud/f_bright/f_low/f_busy (rasgos), waveform_data,
bpm_fuente, huella, huella_dur, bitrate_kbps, formato, baja_calidad, estado,
analizado, fecha_ingreso, cover_url (Módulo 1/3 — carátula, ver
`docs/modulo3_nube_backend.md`), actualizado_en (Módulo 3 — sincronización
personal, ver `docs/modulo3_nube_backend.md`).

Tablas: `playlists` (reglas JSON), `modelo_energia` (coef del aprendizaje,
Módulo 1).

Tablas del Módulo 2: `charts_tracks` (charts de Beatport scrapeados:
beatport_id, genero_slug, posicion, nombre, artistas/remixers en JSON,
sello, bpm, key, primera_vez/fecha_scrape para detectar novedades) y
`para_conseguir` (lista manual de tracks a comprar/bajar, con `conseguido` 0/1).

Las columnas nuevas se agregan por migración suave en `db.connect()`
(`asistente_dj/db.py`).
