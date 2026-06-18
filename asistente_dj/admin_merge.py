"""Script de administración: analiza contribuciones en Supabase y mergea a tracks_canonical.

Uso:
  python admin_merge.py --preview              # ver qué se va a mergear
  python admin_merge.py --min-votos 2 --apply  # mergear tracks con ≥2 contribuciones
  python admin_merge.py --stats                # estadísticas de la BD compartida

Requiere: SUPABASE_URL y SUPABASE_KEY configurados (en settings o variables de entorno).
La service_role_key es necesaria para escribir en tracks_canonical.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

try:
    import requests as req
except ImportError:
    print("Error: instalá requests con  pip install requests")
    sys.exit(1)

_PROJ = os.path.dirname(os.path.abspath(__file__))
if _PROJ not in sys.path:
    sys.path.insert(0, _PROJ)

import settings


def _get_config():
    url = os.environ.get("SUPABASE_URL") or settings.get("supabase_url", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or settings.get("supabase_service_key", "")
    if not url or not key:
        print("Configurá SUPABASE_URL y SUPABASE_SERVICE_KEY en el entorno o en settings.")
        print("  python cli.py config --supabase-url <URL> --supabase-service-key <KEY>")
        sys.exit(1)
    return url.rstrip("/"), key


def _headers(key):
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _fetch_contribuciones(url, key, limit=10000) -> list[dict]:
    r = req.get(
        f"{url}/rest/v1/contribuciones",
        headers={**_headers(key), "Prefer": ""},
        params={"select": "*", "limit": str(limit), "order": "fecha.asc"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def _mayoria(valores: list) -> tuple:
    """Devuelve (valor_mas_frecuente, votos_dict)."""
    limpios = [v for v in valores if v is not None and str(v).strip()]
    if not limpios:
        return None, {}
    cnt = Counter(str(v).strip() for v in limpios)
    ganador = cnt.most_common(1)[0][0]
    return ganador, dict(cnt)


def _analizar(contribuciones: list[dict], min_votos: int) -> list[dict]:
    """Agrupa por fp_hash y calcula el valor ganador por mayoría para cada campo."""
    grupos: dict[str, list[dict]] = {}
    for c in contribuciones:
        fh = c.get("fp_hash")
        if fh:
            grupos.setdefault(fh, []).append(c)

    resultados = []
    for fh, rows in grupos.items():
        if len(rows) < min_votos:
            continue
        def m(campo):
            return _mayoria([r.get(campo) for r in rows])

        g_genero,   v_genero   = m("genero")
        g_sub,      v_sub      = m("subgenero")
        g_camelot,  v_camelot  = m("camelot")
        g_key,      v_key      = m("key_nota")
        g_bpm_s,    v_bpm      = m("bpm")
        g_energia,  v_energia  = m("energia")

        try:
            bpm_f = float(g_bpm_s) if g_bpm_s else None
        except (TypeError, ValueError):
            bpm_f = None

        # Tomar artista/titulo del más reciente (más completo)
        reciente = sorted(rows, key=lambda r: r.get("fecha", ""), reverse=True)[0]

        resultados.append({
            "fp_hash":     fh,
            "artista":     reciente.get("artista"),
            "titulo":      reciente.get("titulo"),
            "bpm":         bpm_f,
            "key_nota":    g_key,
            "camelot":     g_camelot,
            "genero":      g_genero,
            "subgenero":   g_sub,
            "energia":     int(g_energia) if g_energia else None,
            "n_contribuciones": len(rows),
            "votos": json.dumps({
                "genero":   v_genero,
                "subgenero": v_sub,
                "camelot":  v_camelot,
                "bpm":      v_bpm,
                "energia":  v_energia,
            }),
        })
    return resultados


def cmd_stats(url, key):
    contribs = _fetch_contribuciones(url, key)
    print(f"Total contribuciones : {len(contribs)}")
    fps = {c["fp_hash"] for c in contribs if c.get("fp_hash")}
    print(f"Tracks únicos        : {len(fps)}")
    djs = {c.get("dj_uid") for c in contribs if c.get("dj_uid")}
    print(f"DJs contribuyendo    : {len(djs)}")

    from collections import Counter
    por_dj = Counter(c.get("dj_uid") for c in contribs)
    print("\nContribuciones por DJ (anónimo):")
    for uid, n in por_dj.most_common():
        print(f"  {(uid or '?')[:16]}…  {n}")

    por_fp = Counter(c["fp_hash"] for c in contribs if c.get("fp_hash"))
    print(f"\nTracks con ≥2 contribuciones: {sum(1 for n in por_fp.values() if n>=2)}")
    print(f"Tracks con ≥3 contribuciones: {sum(1 for n in por_fp.values() if n>=3)}")


def cmd_merge(url, key, min_votos: int, apply: bool, preview_limit: int = 50):
    contribs = _fetch_contribuciones(url, key)
    candidatos = _analizar(contribs, min_votos)

    print(f"Contribuciones totales : {len(contribs)}")
    print(f"Tracks candidatos      : {len(candidatos)}  (min {min_votos} votos)")
    print()

    for i, c in enumerate(candidatos[:preview_limit]):
        estado = "→ mergeará" if apply else "(preview)"
        print(f"  [{i+1}] {estado}  {c['artista'] or '?'} — {c['titulo'] or '?'}")
        print(f"       Género: {c['genero']}/{c['subgenero']}  "
              f"Key: {c['camelot']}  BPM: {c['bpm']}  E: {c['energia']}  "
              f"[{c['n_contribuciones']} votos]")

    if len(candidatos) > preview_limit:
        print(f"  … y {len(candidatos) - preview_limit} más")

    if not apply:
        print("\n(Modo preview. Agregá --apply para escribir en tracks_canonical.)")
        return

    print(f"\nEscribiendo {len(candidatos)} tracks en tracks_canonical…")
    ok = err = 0
    for c in candidatos:
        r = req.post(
            f"{url}/rest/v1/tracks_canonical",
            headers={**_headers(key), "Prefer": "resolution=merge-duplicates"},
            json=c,
            timeout=15,
        )
        if r.status_code in (200, 201):
            ok += 1
        else:
            err += 1
            print(f"  ERROR {r.status_code}: {r.text[:120]}")
    print(f"\nMergeados: {ok}  |  Errores: {err}")


def main():
    p = argparse.ArgumentParser(description="Admin: merge contribuciones → tracks_canonical")
    p.add_argument("--stats",  action="store_true", help="Ver estadísticas de contribuciones")
    p.add_argument("--preview", action="store_true", help="Ver qué se va a mergear (sin escribir)")
    p.add_argument("--apply",  action="store_true", help="Ejecutar el merge")
    p.add_argument("--min-votos", type=int, default=2, dest="min_votos",
                   help="Mínimo de contribuciones para mergear (default: 2)")
    args = p.parse_args()

    url, key = _get_config()

    if args.stats:
        cmd_stats(url, key)
    elif args.apply or args.preview:
        cmd_merge(url, key, args.min_votos, apply=args.apply)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
