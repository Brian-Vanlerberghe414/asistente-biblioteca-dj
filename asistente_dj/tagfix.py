"""Limpieza automática de tags: separar artista, limpiar basura, redondear BPM.

Se ejecuta sin excepción después de cada escaneo y al arrancar la app.
"""
from __future__ import annotations

import re


def limpiar_todo(conn) -> dict:
    """Aplica todas las correcciones y devuelve contadores."""
    sep   = _separar_artista(conn)
    tags  = _limpiar_tags(conn)
    bpm   = _redondear_bpm(conn)
    conn.commit()
    return {"artistas_separados": sep, "tags_limpiados": tags, "bpm_redondeados": bpm}


# ──────────────────────────────────────────────────────────────────────────────

def _separar_artista(conn) -> int:
    """Tracks con artista vacío y titulo = 'Artista - Título': separa los campos."""
    rows = conn.execute(
        "SELECT id, titulo FROM tracks "
        "WHERE (artista IS NULL OR artista = '') AND titulo LIKE '% - %'"
    ).fetchall()
    ok = 0
    for r in rows:
        t = re.sub(r"\s*\[.*?\]\s*$", "", r["titulo"] or "").strip()
        t = re.sub(r"\s+\d{2,3}\s*$", "", t).strip()
        partes = t.split(" - ", 1)
        if len(partes) < 2:
            continue
        art = re.sub(r"^\d+[\.\)]\s*", "", partes[0]).strip()
        tit = partes[1].strip()
        if art and tit:
            conn.execute(
                "UPDATE tracks SET artista=?, titulo=? WHERE id=?",
                (art, tit, r["id"]),
            )
            ok += 1
    return ok


def _limpiar_tags(conn) -> int:
    """Limpia prefijos numéricos, sufijos YouTube, URLs y guiones bajos."""
    rows = conn.execute("SELECT id, artista, titulo FROM tracks").fetchall()
    cambios = []
    for r in rows:
        art = r["artista"] or ""
        tit = r["titulo"]  or ""
        art_orig, tit_orig = art, tit

        # Prefijo numérico del artista: "18. Fahlberg" → "Fahlberg"
        art = re.sub(r"^\d+\.\s*", "", art).strip()
        # Sufijo YouTube Auto-Generated: "Artist - Topic" → "Artist"
        art = re.sub(r"\s*-\s*Topic$", "", art, flags=re.IGNORECASE).strip()
        # URLs en el título
        tit = re.sub(r"\s*(https?://\S+|www\.\S+)", "", tit).strip()
        # Guiones bajos de filename (solo si no tiene espacios)
        if "_" in art and " " not in art:
            art = art.replace("_", " ").strip()
        if "_" in tit and " " not in tit:
            tit = tit.replace("_", " ").strip()
        # "- " inicial en título (artefacto de separación incorrecta)
        tit = re.sub(r"^-\s*", "", tit).strip()

        if art != art_orig or tit != tit_orig:
            cambios.append((art or None, tit or None, r["id"]))

    if cambios:
        conn.executemany(
            "UPDATE tracks SET artista=?, titulo=? WHERE id=?", cambios
        )
    return len(cambios)


def _redondear_bpm(conn) -> int:
    """Redondea todos los BPM a número entero."""
    cur = conn.execute(
        "UPDATE tracks SET bpm = ROUND(bpm) WHERE bpm IS NOT NULL AND bpm != ROUND(bpm)"
    )
    return cur.rowcount
