# Calidad / roadmap transversal

> Doc de módulo. Ver `CLAUDE.md` (raíz) para la tabla de ruteo completa y
> el contexto general del proyecto.

Cosas que no pertenecen a un solo módulo de dominio: tests, empaquetado,
y el resumen histórico de "ya migrado del roadmap a hecho".

## Tests automatizados (arrancado sesión 2026-06-23)

`pip install -r asistente_dj/requirements-dev.txt` (solo `pytest`, no hace
falta para correr la app). Corren desde `asistente_dj/`:

```
python -m pytest tests/ -v
```

24 tests, todos unitarios/sin red (~0.5s en total) — cubren
`classifier.py` (incluye un test de consistencia que recorre TODO
`GENRE_ALIASES` contra `GENRE_TREE`, así una reorganización del árbol que
deje un alias roto se detecta sola, como hubiera pasado con el bug de
"Melodic House/Techno" de esta misma sesión), `getsongbpm.py` (Camelot,
limpieza de título/artista), `rekordbox_export.py` (preferencia de
`ruta_destino`, no duplicar tracks entre playlists, orden preservado), y
`scanner.scan()` de punta a punta contra una SQLite temporal con los MP3
de prueba de `tests/make_test_files.py` (monkeypatcheando
`biblioteca_confiable.buscar` para no tocar la Biblioteca Confiable real
ni depender de red). `tests/conftest.py` agrega `asistente_dj/` al
`sys.path` para poder importar los módulos del proyecto directo.

**Todavía sin cubrir** (próximos candidatos): mocks de red para
`biblioteca_confiable.py`/`itunes_cover.py`, tests de `archiver.py`/`db.py`
migraciones, y cualquier test de GUI (más caro, queda para después).

**Legacy/sin clasificar** (archivos .py sin documentar en ningún módulo,
no asumir su propósito sin leerlos): `diag.py`, `test_api.py`,
`tmp_show_knn.py`, `genre_model.py`.

## Empaquetado / instalador

**No empezado.** Falta: empaquetado/instalador + asistente de primer
arranque (elegir la biblioteca). Relacionado con el plan diferido de
Tiers/PyInstaller (ver abajo) — cuando se ataque el empaquetado real,
conviene coordinarlo con ese plan en vez de armar dos soluciones de
packaging distintas.

## Planes diferidos (NO implementados, diseño completo en otro archivo)

Viven en `C:\Users\Brian Vanlerberghe\.claude\plans\polymorphic-rolling-wolf.md`,
no en esta carpeta de docs — son planes de implementación futura, no
documentación de lo ya construido:

1. **Tiers de usuario + Capabilities + Build Flags + Pagos (Stripe)** —
   4 niveles de membresía (General/VIP/Oro/Diamante), gating por
   capabilities explícitas, exclusión física de charts/streaming del
   build público vía PyInstaller, login obligatorio con modo offline.
   Diferido a último paso del desarrollo (decisión explícita del dueño
   del producto).
2. **Charts propios** — reemplazo futuro de los charts de Beatport (tier
   Oro) por un chart basado en uso real de los clientes (scores "hot"/
   "rising", local-first + agregado de comunidad). Diferido hasta tener
   usuarios reales.

## Hecho (ya no es roadmap, resumen histórico)

Interfaz gráfica PySide6 (`app.py` + `gui/`, con reproductor + cola +
shuffle inteligente por BPM/armónico), Biblioteca Confiable en Supabase
como fuente prioritaria de género, motor de sugerencia de género por
audio basado en la taxonomía Beatport (`genre_profiles.py`).
