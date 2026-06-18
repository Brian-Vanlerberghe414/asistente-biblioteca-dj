"""Diagnóstico: prueba tus tracks reales contra GetSongBPM con el buscador nuevo
(que limpia los nombres). Uso:  python diag.py TU_API_KEY
"""
import sys
import sqlite3
import getsongbpm

if len(sys.argv) < 2:
    print("Uso: python diag.py TU_API_KEY [ruta.db]")
    sys.exit(1)

api_key = sys.argv[1]
dbpath = sys.argv[2] if len(sys.argv) > 2 else "asistente_dj.db"

conn = sqlite3.connect(dbpath)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT artista, titulo FROM tracks "
    "WHERE bpm_fuente IS NULL OR bpm_fuente='audio' LIMIT 12").fetchall()

print(f"Probando {len(rows)} tracks reales (con limpieza de nombres):\n")
ok = 0
for r in rows:
    art = (r["artista"] or "").strip()
    tit = (r["titulo"] or "").strip()
    tl = getsongbpm.limpiar_titulo(tit)
    al = getsongbpm.limpiar_artista(art)
    d = getsongbpm.buscar(api_key, art, tit)
    if d.ok:
        ok += 1
        print(f"  OK   '{al}' - '{tl}'  ->  BPM={d.bpm}  key={d.key} ({d.camelot})")
    else:
        print(f"  {d.error:14} '{al}' - '{tl}'")
print(f"\nEncontrados: {ok}/{len(rows)}")
