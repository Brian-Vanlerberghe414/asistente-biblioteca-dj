import db, re

conn = db.connect("asistente_dj.db")

# ── 1. Separar Artista: artista vacío y titulo tiene "Artista - Título" ──
rows_sep = conn.execute(
    "SELECT id, titulo FROM tracks "
    "WHERE (artista IS NULL OR artista = '') AND titulo LIKE '% - %'"
).fetchall()

sep_ok = 0
for r in rows_sep:
    titulo_raw = r["titulo"] or ""
    t = re.sub(r"\s*\[.*?\]\s*$", "", titulo_raw).strip()
    t = re.sub(r"\s+\d{2,3}\s*$", "", t).strip()
    partes = t.split(" - ", 1)
    if len(partes) < 2:
        continue
    art = re.sub(r"^\d+[\.\)]\s*", "", partes[0].strip())
    tit = partes[1].strip()
    if art and tit:
        conn.execute("UPDATE tracks SET artista=?, titulo=? WHERE id=?", (art, tit, r["id"]))
        sep_ok += 1

print(f"Separar artista: {sep_ok} tracks corregidos")

# ── 2. Limpiar Tags: prefijos, YouTube Topic, URLs, guiones bajos ──
rows_all = conn.execute("SELECT id, artista, titulo FROM tracks").fetchall()
cambios = []
for r in rows_all:
    art = r["artista"] or ""
    tit = r["titulo"]  or ""
    art_orig, tit_orig = art, tit

    art = re.sub(r"^\d+\.\s*", "", art).strip()
    art = re.sub(r"\s*-\s*Topic$", "", art, flags=re.IGNORECASE).strip()
    tit = re.sub(r"\s*(https?://\S+|www\.\S+)", "", tit).strip()
    if "_" in art and " " not in art:
        art = art.replace("_", " ").strip()
    if "_" in tit and " " not in tit:
        tit = tit.replace("_", " ").strip()
    tit = re.sub(r"^-\s*", "", tit).strip()

    if art != art_orig or tit != tit_orig:
        cambios.append((art or None, tit or None, r["id"]))

conn.executemany("UPDATE tracks SET artista=?, titulo=? WHERE id=?", cambios)
print(f"Limpiar tags:    {len(cambios)} tracks corregidos")

conn.commit()
conn.close()
print("Listo.")
