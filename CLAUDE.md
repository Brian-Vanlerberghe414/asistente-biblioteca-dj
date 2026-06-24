# Asistente de Biblioteca DJ — contexto del proyecto

> Archivo de memoria para Claude Code. Este archivo es deliberadamente
> CHICO: el detalle real vive partido por módulo en `asistente_dj/docs/`
> (ver tabla de ruteo abajo) — léase SOLO el doc del módulo en el que se
> va a trabajar, no todos. El detalle histórico exhaustivo está en
> `Concepto - Asistente de Biblioteca DJ.md` (mismo directorio). El uso de
> cada comando está en `asistente_dj/README.md`.

## Qué es

Herramienta para DJs de música electrónica (Brian + colegas) con dos módulos
de producto:
1. **Organizador** (Módulo 1): escanea la biblioteca, clasifica/archiva por
   género, analiza BPM/key/energía, detecta duplicados, importa datos de
   software DJ, crea playlists inteligentes y las exporta a Rekordbox.
2. **Descubrimiento** (Módulo 2, en progreso): charts de Beatport, seguimiento
   de novedades, preview de YouTube/Spotify, lista de "para conseguir".

Más un Módulo 3 (nube + multiplataforma, ver doc de módulo) y una GUI
PySide6 que cubre los Módulos 1 y 2.

Audiencia: no solo Brian; pensado para que lo usen otros DJs (cada uno con su
biblioteca y su modelo de energía aprendido).

## Dónde está cada cosa (leer SOLO el doc del módulo en el que se va a trabajar)

| Si se menciona...                                                                          | Leer                                          |
|---------------------------------------------------------------------------------------------|------------------------------------------------|
| "Módulo 1", organizador, escaneo, análisis de audio, BPM/key/energía, archivado, import Rekordbox/Traktor/Serato | `asistente_dj/docs/modulo1_organizador.md` |
| "Módulo 2", descubrimiento, charts, Beatport, para conseguir, novedades, preview YouTube/Spotify | `asistente_dj/docs/modulo2_descubrimiento.md` |
| GUI, interfaz, ventana, pestaña, widget, carátulas en vivo                                   | `asistente_dj/docs/gui.md` |
| "Módulo 3", nube, backend, Supabase, Feedback DJ, sync, backup, multiusuario                 | `asistente_dj/docs/modulo3_nube_backend.md` |
| tests, calidad, roadmap general, empaquetado                                                 | `asistente_dj/docs/calidad_y_roadmap.md` |
| base de datos, esquema, tabla, migración SQLite                                              | `asistente_dj/docs/base_de_datos.md` |

Si el módulo no es obvio por lo que se pide, preguntar antes de leer todo
— no cargar más de un doc de módulo a la vez salvo que la tarea cruce
módulos explícitamente (en ese caso, cada doc tiene referencias cruzadas
al resto). Hay además dos planes de implementación futura, diferidos,
en `C:\Users\Brian Vanlerberghe\.claude\plans\polymorphic-rolling-wolf.md`
(Tiers/Capabilities/Pagos, y Charts propios) — no viven en `docs/` porque
son diseño sin construir, no documentación de lo existente.

## Cómo correrlo

Requisitos: Python 3.10+, `pip install -r asistente_dj/requirements.txt`
(numpy, mutagen). Externos opcionales: **ffmpeg** (análisis de audio) y
**fpcalc** de Chromaprint (duplicados). En Windows, dejar `fpcalc.exe`
dentro de `asistente_dj/`.

GUI (PySide6), desde `asistente_dj/`:

```
python app.py
```

CLI: todos los comandos están documentados en su doc de módulo
correspondiente (ver tabla arriba) — no hay un listado único acá a
propósito, para no tener que leer comandos de los 3 módulos a la vez.

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
