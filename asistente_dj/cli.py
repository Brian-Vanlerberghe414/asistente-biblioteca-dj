"""Interfaz de consola del prototipo del Asistente DJ (Módulo 1).

Uso:
  python cli.py scan    <carpeta_origen> [--db ruta.db]
  python cli.py plan    [--db ruta.db]
  python cli.py archive <carpeta_destino> [--db ruta.db] [--apply]
  python cli.py review  [--db ruta.db]

Por defecto 'archive' es simulación (dry-run). Agregá --apply para copiar de verdad.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import db
import settings
import tags as tagreader
from scanner import scan
from archiver import build_plan, execute_plan

DEFAULT_DB = "asistente_dj.db"


def _lazy_analyzer():
    """Importa analyzer solo cuando se usa (requiere numpy + ffmpeg)."""
    import analyzer
    return analyzer


def _parse_bpm(valor):
    """Convierte un BPM del tag (texto, a veces '128.00' o '128,0') a float."""
    if not valor:
        return None
    try:
        return float(str(valor).replace(",", ".").strip())
    except Exception:
        return None


def _recalibrar_energia(conn):
    """Asigna energía 1-10. Si el DJ ya calibró (hay modelo aprendido), usa ese
    modelo personalizado; si no, usa el cálculo por percentiles (acústica+BPM+
    tonalidad)."""
    analyzer = _lazy_analyzer()
    import calibration_model as cm
    modelo = conn.execute("SELECT coef FROM modelo_energia WHERE id=1").fetchone()
    coef = cm.deserializar(modelo["coef"]) if modelo and modelo["coef"] else None
    rows = conn.execute(
        "SELECT id, energia_raw, bpm, camelot, key, f_loud, f_bright, f_low, f_busy "
        "FROM tracks WHERE energia_raw IS NOT NULL").fetchall()
    if not rows:
        return 0
    if coef:  # modelo aprendido del oído del DJ
        n = 0
        for r in rows:
            if r["f_low"] is None:
                continue
            e = cm.predecir(coef, cm.vector_features(r))
            conn.execute("UPDATE tracks SET energia=? WHERE id=?", (e, r["id"]))
            n += 1
        conn.commit()
        return n
    # default: percentiles de la energía combinada
    ids = [r["id"] for r in rows]
    vals = [analyzer.energia_combinada(r["energia_raw"], r["bpm"], r["camelot"], r["key"])
            for r in rows]
    mapping = analyzer.energia_por_percentiles(vals)
    for idx, e in mapping.items():
        conn.execute("UPDATE tracks SET energia=? WHERE id=?", (e, ids[idx]))
    conn.commit()
    return len(mapping)


def _resuggest(conn, analyzer):
    """Recalcula sugerencias de género (BPM del tag si existe, energía real).

    Los rasgos acústicos crudos (f_low/f_bright/f_busy) viven en una escala
    propia del análisis, distinta de la escala cualitativa 1-5 del JSON de
    perfiles de género. Para compararlos con los perfiles, se normalizan por
    PERCENTILES dentro de la propia biblioteca (igual que la energía): así
    "graves altos" significa "más graves que el resto de tu colección", no
    un valor absoluto que puede no calzar con la escala del JSON."""
    todos = conn.execute(
        "SELECT id, f_low, f_bright, f_busy FROM tracks "
        "WHERE analizado=1 AND f_low IS NOT NULL"
    ).fetchall()
    ids_todos = [r["id"] for r in todos]
    pct_low = analyzer.energia_por_percentiles([r["f_low"] for r in todos])
    pct_bright = analyzer.energia_por_percentiles([r["f_bright"] for r in todos])
    pct_busy = analyzer.energia_por_percentiles([r["f_busy"] for r in todos])
    id_to_idx = {tid: i for i, tid in enumerate(ids_todos)}

    def _pct(mapa, track_id):
        idx = id_to_idx.get(track_id)
        if idx is None or idx not in mapa:
            return None
        return mapa[idx] / 10.0  # 1-10 -> 0-1

    rows = conn.execute(
        "SELECT id, bpm, energia FROM tracks WHERE genero IS NULL AND analizado=1"
    ).fetchall()
    for r in rows:
        bpm = _parse_bpm(r["bpm"])
        f_low = _pct(pct_low, r["id"])
        f_bright = _pct(pct_bright, r["id"])
        f_busy = _pct(pct_busy, r["id"])
        g, s, nota = analyzer.suggest_genre(bpm, r["energia"], f_low, f_bright, f_busy)
        conn.execute(
            "UPDATE tracks SET genero_sugerido=?, subgenero_sugerido=?, "
            "nota_sugerencia=? WHERE id=?", (g, s, nota, r["id"]))
    conn.commit()
    return len(rows)


def _print_header():
    motor = "Mutagen" if tagreader.using_mutagen() else "lector ID3 interno (respaldo)"
    print(f"  Asistente DJ — Módulo 1 (prototipo)   [motor de tags: {motor}]")
    print("=" * 64)


def cmd_scan(args):
    _print_header()
    if not os.path.isdir(args.carpeta):
        print(f"No existe la carpeta: {args.carpeta}")
        return 1
    conn = db.connect(args.db)
    print(f"Escaneando: {args.carpeta}\n")
    r = scan(args.carpeta, conn)
    print(f"Archivos de audio encontrados : {r['total']}")
    print(f"  Clasificados                : {r['clasificados']}")
    print(f"  A revisar (género dudoso)   : {r['por_revisar']}")
    print(f"  Baja calidad detectada      : {r['baja_calidad']}")
    if r.get("basura_limpiada"):
        print(f"  Basura limpiada (._*, etc.) : {r['basura_limpiada']}")
    print("\nDistribución por género:")
    for carpeta, n in sorted(r["por_genero"].items()):
        print(f"  {carpeta:<32} {n}")
    if r.get("ilegibles"):
        print(f"\nArchivos que no se pudieron leer ({len(r['ilegibles'])}) — posiblemente dañados:")
        for p in r["ilegibles"][:20]:
            print(f"  ! {p}")
        if len(r["ilegibles"]) > 20:
            print(f"  ... y {len(r['ilegibles']) - 20} más")
    print(f"\nBase de datos: {args.db}")
    conn.close()
    return 0


def cmd_analyze(args):
    """Analiza el audio (BPM, key, energía) y sugiere género a los sin tag."""
    _print_header()
    analyzer = _lazy_analyzer()
    conn = db.connect(args.db)
    if getattr(args, "reset", False):
        n = conn.execute("UPDATE tracks SET analizado=0").rowcount
        conn.commit()
        print(f"(Reanalizando TODO: {n} tracks)\n")
    elif getattr(args, "reintentar", False):
        n = conn.execute(
            "UPDATE tracks SET analizado=0 "
            "WHERE nota_sugerencia LIKE 'error:%'").rowcount
        conn.commit()
        print(f"(Reintentando {n} tracks que habían fallado)\n")
    rows = conn.execute(
        "SELECT id, ruta_origen, genero, bpm, key FROM tracks "
        "WHERE analizado IS NULL OR analizado=0").fetchall()
    if args.limit:
        rows = rows[:args.limit]
    total = len(rows)
    if total == 0:
        # Antes de salir, verificar si hay waveforms pendientes
        pendientes_wf = conn.execute(
            "SELECT COUNT(*) FROM tracks WHERE waveform_data IS NULL AND analizado=1"
        ).fetchone()[0]
        if pendientes_wf == 0:
            print("Nada para analizar (todo está en cache). Usá --reset para rehacer.")
            conn.close()
            return 0
        print(f"BPM/key ya en cache. Calculando waveforms para {pendientes_wf} tracks...")
    info = {r["ruta_origen"]: r for r in rows}
    paths = list(info.keys())

    from multiprocessing import Pool, cpu_count
    procesos = args.procesos if args.procesos else max(1, cpu_count())
    if total > 0:
        print(f"Analizando {total} tracks con {procesos} núcleos "
              f"(ventana de ~{int(analyzer.VENTANA_DUR)}s)...\n")
    hechos = fallos = sugeridos = 0
    rutas_fallidas = []

    def aplicar(idx, path, feat):
        nonlocal hechos, fallos, sugeridos
        r = info[path]
        if not feat["ok"]:
            fallos += 1
            motivo = "archivo no existe" if not os.path.exists(path) else "no decodificable"
            rutas_fallidas.append((path, motivo))
            conn.execute("UPDATE tracks SET analizado=1, nota_sugerencia=? WHERE id=?",
                         (f"error: {motivo}", r["id"]))
        else:
            # BPM del tag SOLO si es un número positivo real (muchos traen "0"
            # o hasta URLs de sitios de descarga); si no, usamos el del audio.
            tag_bpm = _parse_bpm(r["bpm"])
            if tag_bpm and tag_bpm > 0:
                bpm = r["bpm"]
                bpm_ef = tag_bpm
            else:
                bpm = str(feat["bpm"]) if feat["bpm"] else ""
                bpm_ef = feat["bpm"]
            key = r["key"] or feat["key"]
            gsug = ssug = nota = None
            if r["genero"] is None:
                gsug, ssug, nota = analyzer.suggest_genre(
                    bpm_ef, None, feat.get("f_low"), feat.get("f_bright"),
                    feat.get("f_busy"))
                if gsug:
                    sugeridos += 1
            conn.execute(
                "UPDATE tracks SET bpm=?, key=?, camelot=?, energia_raw=?, "
                "f_loud=?, f_bright=?, f_low=?, f_busy=?, "
                "genero_sugerido=?, subgenero_sugerido=?, nota_sugerencia=?, "
                "waveform_data=?, analizado=1 WHERE id=?",
                (bpm, key, feat["camelot"], feat["energia_raw"],
                 feat.get("f_loud"), feat.get("f_bright"), feat.get("f_low"),
                 feat.get("f_busy"), gsug, ssug, nota,
                 feat.get("waveform_data"), r["id"]))
            hechos += 1

    if total > 0:
        if procesos > 1:
            with Pool(processes=procesos) as pool:
                for idx, (path, feat) in enumerate(
                        pool.imap_unordered(analyzer.analyze_file, paths, chunksize=4), 1):
                    aplicar(idx, path, feat)
                    if idx % 50 == 0 or idx == total:
                        print(f"  {idx}/{total}...")
                        conn.commit()
        else:
            for idx, path in enumerate(paths, 1):
                _, feat = analyzer.analyze_file(path)
                aplicar(idx, path, feat)
                if idx % 50 == 0 or idx == total:
                    print(f"  {idx}/{total}...")
                    conn.commit()
        conn.commit()

    # Pasada extra: waveforms para tracks ya analizados que no las tienen
    filas_wf = conn.execute(
        "SELECT id, ruta_origen FROM tracks WHERE waveform_data IS NULL AND analizado=1"
    ).fetchall()
    if filas_wf:
        total_wf = len(filas_wf)
        print(f"\nCalculando waveforms para {total_wf} tracks...")
        info_wf = {r["ruta_origen"]: r["id"] for r in filas_wf}
        paths_wf = list(info_wf.keys())

        def aplicar_wf(path, wf_data):
            tid = info_wf.get(path)
            if tid and wf_data:
                conn.execute("UPDATE tracks SET waveform_data=? WHERE id=?", (wf_data, tid))

        if procesos > 1:
            with Pool(processes=procesos) as pool:
                for idx_wf, (path, wf) in enumerate(
                        pool.imap_unordered(analyzer.waveform_file, paths_wf, chunksize=4), 1):
                    aplicar_wf(path, wf)
                    if idx_wf % 50 == 0 or idx_wf == total_wf:
                        print(f"  waveform {idx_wf}/{total_wf}...")
                        conn.commit()
        else:
            for idx_wf, path in enumerate(paths_wf, 1):
                _, wf = analyzer.waveform_file(path)
                aplicar_wf(path, wf)
                if idx_wf % 50 == 0 or idx_wf == total_wf:
                    conn.commit()
        conn.commit()

    # Recalibrar energía (percentiles) y refinar sugerencias con la energía real
    n_e = _recalibrar_energia(conn)
    _resuggest(conn, analyzer)
    print(f"\nAnalizados OK      : {hechos}")
    print(f"No decodificables  : {fallos}")
    print(f"Con género sugerido: {sugeridos}")
    print(f"Energía recalibrada: {n_e} tracks (escala relativa 1-10)")
    if rutas_fallidas:
        print(f"\nArchivos que fallaron ({len(rutas_fallidas)}):")
        for ruta, motivo in rutas_fallidas[:30]:
            print(f"  ! [{motivo}] {ruta}")
        if len(rutas_fallidas) > 30:
            print(f"  ... y {len(rutas_fallidas) - 30} más")
    print("\n(Las sugerencias son orientativas: revisá y confirmá antes de archivar.)")
    conn.close()
    return 0


def cmd_reclassify(args):
    """Re-clasifica tracks sin género usando los aliases actuales de config.py.
    Solo toca tracks con genero IS NULL; nunca sobreescribe géneros ya asignados."""
    _print_header()
    from classifier import classify
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT id, genero_raw FROM tracks "
        "WHERE genero IS NULL AND genero_raw IS NOT NULL AND genero_raw != ''"
    ).fetchall()
    actualizados = 0
    for r in rows:
        c = classify(r["genero_raw"])
        if c.genero is not None:
            conn.execute(
                "UPDATE tracks SET genero=?, subgenero=?, confianza=? WHERE id=?",
                (c.genero, c.subgenero, c.confianza, r["id"]),
            )
            actualizados += 1
    conn.commit()
    sin_genero_restantes = conn.execute(
        "SELECT COUNT(*) FROM tracks WHERE genero IS NULL"
    ).fetchone()[0]
    conn.close()
    print(f"Reclasificados: {actualizados} de {len(rows)} tracks sin género")
    print(f"Siguen sin género: {sin_genero_restantes} (revisar con 'review --resolver')")
    return 0


def cmd_predict_genre(args):
    """Clasifica tracks sin género usando KNN sobre los features acústicos de la BD."""
    import genre_model as gm
    _print_header()
    conn = db.connect(args.db)

    stats = gm.stats_entrenamiento(conn)
    total_ent = sum(stats.values())
    print(f"Entrenamiento: {total_ent} tracks ({len(stats)} clases)")
    for clase, n in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {n:4d}  {clase}")
    print()

    rows = conn.execute(
        "SELECT id, artista, titulo, bpm, f_bright, f_low, f_busy "
        "FROM tracks WHERE genero IS NULL AND f_low IS NOT NULL AND analizado=1 "
        "ORDER BY artista, titulo"
    ).fetchall()
    if args.limit:
        rows = rows[: args.limit]

    if not rows:
        print("No hay tracks analizados sin género.")
        conn.close()
        return 0

    print(f"Prediciendo género para {len(rows)} tracks...\n")
    aplicados = sin_conf = sin_bpm = sobre_umbral = 0

    for r in rows:
        g, sg, conf = gm.predecir(conn, dict(r), k=args.k)
        if g is None:
            sin_bpm += 1
            continue
        label = f"{r['artista'] or '?'} - {r['titulo'] or '?'}"
        label = label.encode("cp1252", errors="replace").decode("cp1252")[:65]
        pred  = f"{g}/{sg or ''}"
        print(f"  {conf * 100:3.0f}%  {pred:<32}  {label}")
        if conf >= args.min_confianza:
            sobre_umbral += 1
            if args.apply:
                conn.execute(
                    "UPDATE tracks SET genero=?, subgenero=?, confianza='audio-knn' WHERE id=?",
                    (g, sg, r["id"]),
                )
                aplicados += 1
        else:
            sin_conf += 1

    if args.apply:
        conn.commit()
        print(f"\nAplicados  : {aplicados}")
        print(f"Baja conf. : {sin_conf}  (umbral {args.min_confianza:.0%})")
        print(f"Sin BPM val: {sin_bpm}")
    else:
        total_pred = len(rows) - sin_bpm
        print(f"\nConf >= {args.min_confianza:.0%}: {sobre_umbral}/{total_pred}  — usar --apply para guardar")

    conn.close()
    return 0


def _extraer_artista_titulo(artista: str, titulo: str) -> tuple[str, str]:
    """Extrae artista y título limpios para la búsqueda online.

    Si artista está vacío intenta parsear 'Artista - Título' desde el titulo.
    Elimina prefijos numéricos tipo '03. ' y sufijos como '(Original Mix)'.
    """
    import re
    artista = (artista or "").strip()
    titulo  = (titulo  or "").strip()

    # Si artista vacío, intentar "Artista - Título" del campo titulo
    if not artista and " - " in titulo:
        partes = titulo.split(" - ", 1)
        artista = partes[0].strip()
        titulo  = partes[1].strip()

    # Limpiar prefijo numérico del artista: "03. Chris..." → "Chris..."
    artista = re.sub(r"^\d+[\.\-]\s*", "", artista).strip()

    # Eliminar sufijos de mix del título para mejor match
    titulo = re.sub(
        r"\s*[\(\[](original mix|extended mix|extended version|radio edit"
        r"|club mix|vip mix|remix)[^\)\]]*[\)\]]",
        "", titulo, flags=re.IGNORECASE
    ).strip()

    return artista, titulo


def cmd_lookup_genre(args):
    """Busca géneros online (MusicBrainz + Last.fm) para tracks sin género."""
    import time as _time
    import lookup_genre as lg

    _print_header()
    conn = db.connect(args.db)
    # Incluye tracks con artista vacío: los parseamos del titulo
    rows = conn.execute(
        "SELECT id, artista, titulo FROM tracks "
        "WHERE genero IS NULL "
        "ORDER BY artista, titulo"
    ).fetchall()

    if args.limit:
        rows = rows[: args.limit]

    total = len(rows)
    if total == 0:
        print("No hay tracks sin género.")
        conn.close()
        return 0

    print(f"Buscando género online para {total} tracks...\n")
    ok = sin_match = errores = 0

    for i, r in enumerate(rows, 1):
        artista, titulo = _extraer_artista_titulo(r["artista"], r["titulo"])
        if not artista:
            sin_match += 1
            continue
        label = f"{artista} - {titulo}".encode("cp1252", errors="replace").decode("cp1252")
        print(f"[{i}/{total}] {label[:70]} ", end="", flush=True)
        try:
            g, sg, fuente = lg.lookup(artista, titulo, args.lastfm_key or None)
            if g:
                conn.execute(
                    "UPDATE tracks SET genero=?, subgenero=?, confianza='online' WHERE id=?",
                    (g, sg, r["id"]),
                )
                conn.commit()
                print(f"-> {g}/{sg or ''}  [{fuente}]")
                ok += 1
            else:
                print("-> sin match")
                sin_match += 1
        except Exception as e:
            print(f"-> error: {e}")
            errores += 1
        if i < total:
            _time.sleep(1.1)   # respetar rate limit MusicBrainz (1 req/seg)

    sin_restantes = conn.execute(
        "SELECT COUNT(*) FROM tracks WHERE genero IS NULL"
    ).fetchone()[0]
    conn.close()
    print(f"\nClasificados: {ok}  Sin match: {sin_match}  Errores: {errores}")
    print(f"Tracks sin género restantes: {sin_restantes}")
    return 0


def cmd_resuggest(args):
    """Recalibra energía (percentiles) y recalcula sugerencias de género.
    Rápido: no vuelve a decodificar audio. Útil tras ajustar la heurística."""
    _print_header()
    analyzer = _lazy_analyzer()
    conn = db.connect(args.db)
    n_e = _recalibrar_energia(conn)
    cambios = _resuggest(conn, analyzer)
    print(f"Energía recalibrada     : {n_e} tracks")
    print(f"Sugerencias recalculadas: {cambios}")
    conn.close()
    return 0


def _norm(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _match_y_actualizar(conn, registros, fuente):
    """Matchea una lista de tracks de un software DJ con la base y trae BPM/key.
    Cada registro tiene: location, artista, titulo, bpm, key.
    Matching: ruta exacta -> nombre de archivo -> artista+título.
    Devuelve (actualizados, sin_match, sin_bpm)."""
    por_ruta, por_base, por_at = {}, {}, {}
    for r in conn.execute("SELECT id, ruta_origen, artista, titulo FROM tracks"):
        ruta = (r["ruta_origen"] or "").replace("\\", "/").lower()
        por_ruta[ruta] = r["id"]
        por_base.setdefault(ruta.rsplit("/", 1)[-1], r["id"])
        por_at.setdefault(_norm(r["artista"]) + _norm(r["titulo"]), r["id"])

    from getsongbpm import key_a_camelot
    actualizados = sin_match = sin_bpm = 0
    for reg in registros:
        loc = (reg.location or "").replace("\\", "/").lower()
        tid = (por_ruta.get(loc)
               or por_base.get(loc.rsplit("/", 1)[-1])
               or por_at.get(_norm(reg.artista) + _norm(reg.titulo)))
        if tid is None:
            sin_match += 1
            continue
        if not reg.bpm:
            sin_bpm += 1
            continue
        cam = key_a_camelot(reg.key) if reg.key else ""
        conn.execute(
            "UPDATE tracks SET bpm=?, bpm_fuente=?, "
            "key=COALESCE(NULLIF(?,''), key), "
            "camelot=COALESCE(NULLIF(?,''), camelot) "
            "WHERE id=?",
            (reg.bpm, fuente, reg.key, cam, tid))
        actualizados += 1
    conn.commit()
    return actualizados, sin_match, sin_bpm


def cmd_clean_tags(args):
    """Detecta y limpia tags basura (URLs de sitios de descarga) en los metadatos."""
    _print_header()
    import tagclean
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT id, ruta_origen, titulo, artista, sello, genero_raw FROM tracks").fetchall()
    cambios = []
    for r in rows:
        nuevos = {}
        for campo, permitir_vacio in tagclean.CAMPOS.items():
            actual = r[campo]
            if actual and tagclean.tiene_basura(actual):
                limpio = tagclean.limpiar_campo(actual, permitir_vacio)
                if limpio != actual:
                    nuevos[campo] = limpio
        if nuevos:
            cambios.append((r, nuevos))

    if not cambios:
        print("No se encontraron tags con basura. 🎉")
        conn.close()
        return 0

    print(f"Tracks con tags a limpiar: {len(cambios)}\n")
    for r, nuevos in cambios[:40]:
        for campo, val in nuevos.items():
            print(f"  {campo}: '{r[campo]}'")
            print(f"      -> '{val}'")
    if len(cambios) > 40:
        print(f"  ... y {len(cambios) - 40} tracks más")

    if not args.apply:
        print("\n(Vista previa. Para aplicar los cambios en la base: agregá --apply)")
        conn.close()
        return 0

    escritos = 0
    for r, nuevos in cambios:
        sets = ", ".join(f"{c}=?" for c in nuevos)
        conn.execute(f"UPDATE tracks SET {sets} WHERE id=?",
                     list(nuevos.values()) + [r["id"]])
        if args.escribir_archivos:
            escritos += _escribir_tags_archivo(r["ruta_origen"], nuevos)
    conn.commit()
    conn.close()
    print(f"\nTags limpiados en la base: {len(cambios)} tracks.")
    if args.escribir_archivos:
        print(f"Tags reescritos en los archivos: {escritos}")
    return 0


def _escribir_tags_archivo(path, nuevos):
    """Escribe los tags limpios de vuelta al archivo (Mutagen). Best-effort."""
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(path, easy=True)
        if audio is None:
            return 0
        mapa = {"titulo": "title", "artista": "artist", "genero_raw": "genre"}
        toco = False
        for campo, val in nuevos.items():
            if campo in mapa:
                audio[mapa[campo]] = [val] if val else [""]
                toco = True
        if toco:
            audio.save()
            return 1
    except Exception:
        pass
    return 0


def cmd_config(args):
    """Ver o fijar la configuración (ruta de la biblioteca + credenciales Supabase)."""
    _print_header()
    if args.biblioteca:
        settings.set_("biblioteca", args.biblioteca)
        print(f"Biblioteca del asistente fijada en:\n  {args.biblioteca}")
    if args.supabase_url:
        settings.set_("supabase_url", args.supabase_url)
        print(f"Supabase URL guardada.")
    if args.supabase_key:
        settings.set_("supabase_key", args.supabase_key)
        print(f"Supabase API key guardada.")
    if args.spotify_client_id:
        settings.set_("spotify_client_id", args.spotify_client_id)
        print("Spotify Client ID guardado.")
    if args.spotify_client_secret:
        settings.set_("spotify_client_secret", args.spotify_client_secret)
        print("Spotify Client Secret guardado.")

    bib = settings.get("biblioteca")
    cfg = settings.cargar()
    sb_url = cfg.get("supabase_url", "")
    sb_key = cfg.get("supabase_key", "")
    sp_id = cfg.get("spotify_client_id", "")
    sp_secret = cfg.get("spotify_client_secret", "")

    print(f"\nBiblioteca del asistente : {bib or '(sin configurar)'}")
    print(f"Supabase URL             : {sb_url or '(sin configurar)'}")
    print(f"Supabase API key         : {'✓ configurada' if sb_key else '(sin configurar)'}")
    print(f"Spotify Client ID/Secret : {'✓ configurados' if (sp_id and sp_secret) else '(sin configurar)'}")

    if not bib:
        print('\nFijá la biblioteca con:  python cli.py config --biblioteca "C:\\ruta"')
    if not sb_url or not sb_key:
        print("Configurá Supabase con:  python cli.py config --supabase-url URL --supabase-key KEY")
    if not sp_id or not sp_secret:
        print("Configurá Spotify con:  python cli.py config --spotify-client-id ID --spotify-client-secret SECRET")
    return 0


def cmd_biblioteca(args):
    """Gestionar la Biblioteca Confiable (Supabase)."""
    _print_header()
    import biblioteca_confiable

    if args.accion == "estado":
        if biblioteca_confiable.esta_configurado():
            print("Biblioteca Confiable: ✓ conectada a Supabase")
            tracks = biblioteca_confiable.listar(limit=5)
            print(f"Primeros {len(tracks)} registros:")
            for t in tracks:
                sub = f" / {t['subgenero']}" if t.get("subgenero") else ""
                print(f"  {t['artista']} — {t['titulo']}  [{t['genero']}{sub}]")
        else:
            print("Biblioteca Confiable: no configurada")
            print("Usá:  python cli.py config --supabase-url URL --supabase-key KEY")

    elif args.accion == "agregar":
        # Agrega el track con la ruta dada a la biblioteca confiable
        conn = db.connect(args.db)
        row = conn.execute(
            "SELECT artista, titulo, duracion_seg, genero, subgenero, sello, bpm, camelot "
            "FROM tracks WHERE ruta_origen=?", (args.ruta,)
        ).fetchone()
        if not row:
            print(f"Track no encontrado en la base local: {args.ruta}")
            return 1
        if not row["genero"]:
            print("El track no tiene género asignado — asignale uno primero.")
            return 1
        ok = biblioteca_confiable.agregar(
            artista=row["artista"] or "",
            titulo=row["titulo"] or "",
            duracion_seg=row["duracion_seg"] or 0,
            genero=row["genero"],
            subgenero=row["subgenero"],
            sello=row["sello"],
            bpm=row["bpm"],
            camelot=row["camelot"],
            fuente="scan",
        )
        if ok:
            print(f"✓ Agregado a Biblioteca Confiable: {row['artista']} — {row['titulo']}")
        return 0 if ok else 1

    elif args.accion == "listar":
        tracks = biblioteca_confiable.listar(genero=args.genero, limit=args.limit)
        if not tracks:
            print("Sin resultados.")
            return 0
        print(f"{'ARTISTA':<35} {'TITULO':<40} {'GENERO':<20} SUBGENERO")
        print("─" * 110)
        for t in tracks:
            sub = t.get("subgenero") or "—"
            print(f"{(t['artista'] or ''):<35.35} {(t['titulo'] or ''):<40.40} "
                  f"{t['genero']:<20} {sub}")

    elif args.accion == "artista":
        registros = biblioteca_confiable.generos_de_artista(args.nombre)
        if not registros:
            print(f"Sin géneros registrados para '{args.nombre}'.")
            return 0
        generos = sorted({
            f"{r['genero']} / {r['subgenero']}" if r.get("subgenero") else r["genero"]
            for r in registros
        })
        artista = registros[0]["artista"]
        print(f"{artista} produce: " + ", ".join(generos))
    return 0


def _hoy():
    from datetime import date
    return date.today().isoformat()


def cmd_charts_generos(args):
    """Lista los géneros/sub-géneros de Beatport disponibles para scrapear."""
    _print_header()
    import charts_beatport
    print("Consultando beatport.com/charts ...")
    try:
        generos = charts_beatport.listar_generos_disponibles()
    except ImportError:
        print("Falta Playwright. Instalá con:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return 1
    if not generos:
        print("No se encontraron géneros (Beatport puede haber cambiado su estructura).")
        return 1
    print(f"{len(generos)} géneros encontrados:\n")
    for g in generos:
        print(f"  {g['slug']:<28} {g['nombre']}")
    print("\nUsá el slug con:  python cli.py charts-scrape --genero <slug>")
    return 0


def cmd_charts_scrape(args):
    """Scrapea el Top 100 global y/o por género de Beatport, lo guarda en la
    base y sube automáticamente a la Biblioteca Confiable (Supabase) cada
    track del chart (nombre, artista, BPM, key) y registra qué género produce
    cada artista. Si el género de Beatport no tiene mapeo al árbol propio, se
    sube igual con el nombre de Beatport tal cual — nunca se pierde info por
    falta de mapeo. La info del chart siempre tiene prioridad: si el track ya
    estaba con un dato distinto, se actualiza con el del chart."""
    _print_header()
    import charts_beatport
    import biblioteca_confiable
    import charts_confiable
    import json as _json

    if args.solo_global:
        generos_filtro = []
        incluir_global = True
    else:
        generos_filtro = [args.genero] if args.genero else None
        incluir_global = (not args.genero or args.global_tambien) and not args.sin_global
    subir_biblioteca = biblioteca_confiable.esta_configurado()
    if not subir_biblioteca:
        print("(Biblioteca Confiable no configurada — los charts se guardan local "
              "pero no se suben a Supabase. Configurala con `cli.py config "
              "--supabase-url URL --supabase-key KEY`.)")
    print("Scrapeando Beatport (esto puede tardar varios minutos)...")
    try:
        resultado = charts_beatport.ejecutar(generos_filtro, incluir_global, args.delay_seg)
    except ImportError:
        print("Falta Playwright. Instalá con:")
        print("  pip install playwright")
        print("  playwright install chromium")
        return 1
    except RuntimeError as exc:
        print(f"Error al scrapear: {exc}")
        return 1

    conn = db.connect(args.db)
    fecha = _hoy()
    nuevos_total = 0
    subidos_total = 0

    def _subir_a_biblioteca(t, genero, subgenero):
        """Sube nombre/artista/bpm/key a la Biblioteca Confiable. `genero`
        puede venir del mapeo al árbol propio o, si no hay mapeo (género de
        Beatport sin equivalente todavía), del nombre crudo de Beatport —
        nunca se pierde la info por falta de mapeo. La info del chart manda
        siempre: agregar() hace upsert por artista+título, así que si ya
        había un dato distinto (ej. otro key) lo pisa con el del chart."""
        if not subir_biblioteca:
            return False
        artistas = t["artistas"] or []
        artista = ", ".join(artistas) if artistas else None
        if not artista or not t["nombre"] or not t["duracion_ms"]:
            return False
        titulo = t["nombre"]
        if t["mix_name"] and t["mix_name"].lower() not in ("original mix", "extended mix"):
            titulo = f"{titulo} ({t['mix_name']})"
        ok = biblioteca_confiable.agregar(
            artista=artista, titulo=titulo, duracion_seg=t["duracion_ms"] / 1000,
            genero=genero, subgenero=subgenero, sello=t["sello"], bpm=t["bpm"],
            camelot=charts_beatport.key_a_camelot(t["key"]), fuente="beatport_chart",
        )
        if ok and genero:
            for art in artistas:
                biblioteca_confiable.registrar_genero_artista(art, genero, subgenero)
        return ok

    subir_charts_cloud = charts_confiable.esta_configurado()

    def _guardar(slug, nombre_genero, tracks, es_global):
        nuevos = subidos = 0
        for t in tracks:
            data = {
                "beatport_id": t["beatport_id"], "genero_slug": slug,
                "genero_nombre": nombre_genero, "posicion": t["posicion"],
                "nombre": t["nombre"], "mix_name": t["mix_name"],
                "artistas": _json.dumps(t["artistas"], ensure_ascii=False),
                "remixers": _json.dumps(t["remixers"], ensure_ascii=False),
                "release": t["release"], "sello": t["sello"], "bpm": t["bpm"],
                "key": t["key"], "genero_pista": t.get("genero_pista"),
                "duracion_ms": t["duracion_ms"],
                "publish_date": t["publish_date"], "image_url": t["image_url"],
            }
            es_nuevo = db.upsert_chart_track(conn, data, fecha)
            if es_nuevo:
                nuevos += 1
            if es_global:
                genero, subgenero = charts_beatport.mapear_genero_por_nombre(t.get("genero_pista"))
                if not genero:
                    genero, subgenero = t.get("genero_pista"), None
            else:
                genero, subgenero = charts_beatport.mapear_genero_por_slug(slug)
                if not genero:
                    genero, subgenero = nombre_genero, None
            if _subir_a_biblioteca(t, genero, subgenero):
                subidos += 1
        conn.commit()
        if subir_charts_cloud:
            charts_confiable.upsert_tracks(tracks, slug, nombre_genero, fecha)
        extra = f", {subidos} subidos a Biblioteca Confiable" if subir_biblioteca else ""
        print(f"  [{nombre_genero}] {len(tracks)} tracks ({nuevos} nuevos{extra})")
        return nuevos, subidos

    if resultado.get("global"):
        n, s = _guardar("global", "Global Top 100", resultado["global"], es_global=True)
        nuevos_total += n
        subidos_total += s
    for slug, info in resultado.get("generos", {}).items():
        n, s = _guardar(slug, info["nombre"], info["tracks"], es_global=False)
        nuevos_total += n
        subidos_total += s

    if not resultado.get("global") and not resultado.get("generos"):
        print("No se pudo scrapear nada — revisá la conexión o si Beatport cambió su estructura.")
        return 1
    print(f"\nListo. {nuevos_total} tracks nuevos en total"
          + (f", {subidos_total} subidos a la Biblioteca Confiable" if subir_biblioteca else "")
          + " (ver novedades con: charts-novedades).")
    return 0


def _filas_chart_dict(rows) -> list[dict]:
    """Normaliza filas de SQLite (Row) o de Supabase (dict, artistas ya como
    lista) a una forma común: dict con 'artistas' siempre como lista."""
    out = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("artistas"), str):
            d["artistas"] = json.loads(d["artistas"] or "[]")
        out.append(d)
    return out


def cmd_charts_show(args):
    """Muestra el Top N guardado de un chart (global o de un género).
    Lee de Supabase si está configurado (ahí escribe también el agente en la
    nube); si no, cae al SQLite local."""
    _print_header()
    import charts_confiable
    slug = args.genero or "global"
    rows = []
    if charts_confiable.esta_configurado():
        rows = _filas_chart_dict(charts_confiable.obtener_chart(slug, args.top))
    if not rows:
        conn = db.connect(args.db)
        rows = _filas_chart_dict(conn.execute(
            "SELECT * FROM charts_tracks WHERE genero_slug=? ORDER BY posicion LIMIT ?",
            (slug, args.top),
        ).fetchall())
    if not rows:
        print(f"Sin datos para '{slug}'. Corré primero:  python cli.py charts-scrape"
              + (f" --genero {slug}" if slug != "global" else ""))
        return 1
    print(f"Top {len(rows)} — {rows[0]['genero_nombre'] or slug}  (scrape: {rows[0]['fecha_scrape']})\n")
    for r in rows:
        artistas = ", ".join(r["artistas"])
        bpm = f"{r['bpm']:.0f}" if r["bpm"] else "—"
        print(f"  {r['posicion']:>3}) {artistas:<30.30} {r['nombre']:<35.35} "
              f"[{bpm} BPM, {r['key'] or '—'}]  {r['sello'] or ''}")
    return 0


def cmd_charts_novedades(args):
    """Tracks que aparecieron por primera vez en el scrape más reciente.
    Lee de Supabase si está configurado; si no, cae al SQLite local."""
    _print_header()
    import charts_confiable
    slug = args.genero or "global"
    rows: list[dict] = []
    ultima = None
    if charts_confiable.esta_configurado():
        ultima = charts_confiable.ultima_fecha(slug)
        if ultima:
            rows = _filas_chart_dict(charts_confiable.obtener_novedades(slug))
    if ultima is None:
        conn = db.connect(args.db)
        fila_ultima = conn.execute(
            "SELECT MAX(fecha_scrape) AS f FROM charts_tracks WHERE genero_slug=?", (slug,)
        ).fetchone()
        ultima = fila_ultima["f"] if fila_ultima else None
        if ultima:
            rows = _filas_chart_dict(conn.execute(
                "SELECT * FROM charts_tracks WHERE genero_slug=? AND fecha_scrape=? "
                "AND primera_vez=? ORDER BY posicion", (slug, ultima, ultima),
            ).fetchall())
    if ultima is None:
        print(f"Sin datos para '{slug}'. Corré primero charts-scrape.")
        return 1
    if not rows:
        print(f"Sin novedades en '{slug}' desde el scrape del {ultima}.")
        return 0
    print(f"{len(rows)} novedades en '{slug}' (scrape del {ultima}):\n")
    for r in rows:
        artistas = ", ".join(r["artistas"])
        print(f"  {r['posicion']:>3}) {artistas:<30.30} {r['nombre']:<35.35} {r['sello'] or ''}")
    return 0


def cmd_conseguir(args):
    """Lista de 'para conseguir': tracks vistos en charts (u a mano) que el DJ quiere bajar/comprar."""
    _print_header()
    conn = db.connect(args.db)

    if args.accion == "agregar":
        conn.execute(
            "INSERT INTO para_conseguir (nombre, artistas, sello, notas, fecha_agregado, conseguido) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (args.nombre, args.artistas, args.sello, args.notas, _hoy()),
        )
        conn.commit()
        print(f"Agregado a 'para conseguir': {args.nombre}")
        return 0

    if args.accion == "listar":
        where = "" if args.todos else "WHERE conseguido=0"
        rows = conn.execute(
            f"SELECT * FROM para_conseguir {where} ORDER BY fecha_agregado DESC"
        ).fetchall()
        if not rows:
            print("Lista vacía.")
            return 0
        for r in rows:
            marca = "✓" if r["conseguido"] else " "
            print(f"  [{marca}] #{r['id']:<4} {r['nombre']:<40.40} "
                  f"{r['artistas'] or ''}  ({r['fecha_agregado']})")
        return 0

    if args.accion == "marcar":
        conn.execute("UPDATE para_conseguir SET conseguido=1 WHERE id=?", (args.id,))
        conn.commit()
        print(f"Marcado como conseguido: #{args.id}")
        return 0

    if args.accion == "quitar":
        conn.execute("DELETE FROM para_conseguir WHERE id=?", (args.id,))
        conn.commit()
        print(f"Quitado de la lista: #{args.id}")
        return 0
    return 0


def _opciones_genero():
    from config import GENRE_TREE
    ops = []
    for g, subs in GENRE_TREE.items():
        if subs:
            for s in subs:
                ops.append((g, s))
        else:
            ops.append((g, None))
    return ops


def _elegir_genero(label, ruta=None):
    """Pide al usuario el género de un track desde una lista numerada.
    Reproduce el momento más intenso para ayudar a decidir.
    Devuelve (genero, subgenero), None (=_Por revisar) o 'SKIP'."""
    ops = _opciones_genero()
    print(f"\n  Género no reconocido: {label}")
    proc = None
    if ruta:
        try:
            analyzer = _lazy_analyzer()
            proc = _reproducir(ruta, analyzer.pico_intensidad(ruta), 30)
        except Exception:
            proc = None
    for i, (g, s) in enumerate(ops, 1):
        print(f"    {i:>2}) {g + '/' + s if s else g}")
    print("     0) Dejar en _Por revisar      s) saltar (no importar)")
    try:
        val = input("  Elegí el género (número): ").strip().lower()
    finally:
        if proc:
            proc.terminate()
    if val == "s":
        return "SKIP"
    if val == "0" or not val:
        return None
    try:
        i = int(val)
        if 1 <= i <= len(ops):
            return ops[i - 1]
    except ValueError:
        pass
    print("  (opción inválida, lo dejo en _Por revisar)")
    return None


def cmd_import(args):
    """Importa música: copia desde una carpeta a la biblioteca del asistente,
    organizada por género; pregunta el género cuando no lo reconoce."""
    _print_header()
    import intake
    from config import AUDIO_EXTENSIONS
    from scanner import es_basura

    bib = args.destino or settings.get("biblioteca")
    if not bib:
        print("No hay biblioteca configurada. Fijala primero con:")
        print('  python cli.py config --biblioteca "C:\\ruta\\Biblioteca"')
        return 1
    if not os.path.isdir(args.origen):
        print(f"No existe la carpeta de origen: {args.origen}")
        return 1

    archivos = []
    for dp, _dirs, fs in os.walk(args.origen):
        for n in fs:
            if es_basura(n):
                continue
            if os.path.splitext(n)[1].lower() in AUDIO_EXTENSIONS:
                archivos.append(os.path.join(dp, n))
    if not archivos:
        print("No encontré archivos de audio en esa carpeta.")
        return 0

    print(f"Encontré {len(archivos)} tracks. Los copio a:\n  {bib}\n")
    conn = db.connect(args.db)
    picker = (lambda label, ruta: _elegir_genero(label, ruta))
    importados = []
    for path in archivos:
        try:
            rel, motivo = intake.procesar(
                conn, path, bib, analizar=not args.sin_analisis,
                mover=False, pedir_genero=picker)
        except Exception:
            rel, motivo = "?", "error"
        marca = {"tag": "tag", "manual": "elegido", "revisar": "a revisar",
                 "ya_existe": "ya existía", "error": "ERROR", "saltado": "saltado"}.get(motivo, motivo)
        print(f"  [{marca}] {os.path.basename(path)}  ->  {rel}")
        if motivo in ("tag", "manual", "revisar"):
            importados.append(path)
    _recalibrar_energia(conn)
    conn.close()

    print(f"\nImportados: {len(importados)} de {len(archivos)}")
    if importados:
        val = input(f"¿Borrar los {len(importados)} archivos originales ya copiados? (s/N): ").strip().lower()
        if val == "s":
            borrados = 0
            for p in importados:
                try:
                    os.remove(p)
                    borrados += 1
                except Exception:
                    pass
            print(f"Originales borrados: {borrados}")
        else:
            print("No borré nada; tus originales quedan intactos.")
    return 0


def cmd_watch(args):
    """Vigila la carpeta de ingreso y archiva la música nueva automáticamente."""
    _print_header()
    import time
    import intake
    from scanner import es_basura
    from config import AUDIO_EXTENSIONS
    if not os.path.isdir(args.ingreso):
        print(f"No existe la carpeta de ingreso: {args.ingreso}")
        return 1
    conn = db.connect(args.db)
    print(f"Vigilando: {args.ingreso}")
    print(f"Archivando en: {args.destino}")
    modo = "copia" if args.copiar else "mueve"
    print(f"(Revisa cada {args.intervalo}s · {modo} los archivos · Ctrl+C para parar)\n")
    etiquetas = {"tag": "[por tag]", "audio": "[por audio]", "revisar": "[a revisar]",
                 "ya_existe": "[ya existía]", "error": "[ERROR]"}
    estable = {}
    try:
        while True:
            try:
                nombres = os.listdir(args.ingreso)
            except Exception:
                nombres = []
            for name in nombres:
                path = os.path.join(args.ingreso, name)
                if not os.path.isfile(path) or es_basura(name):
                    continue
                if os.path.splitext(name)[1].lower() not in AUDIO_EXTENSIONS:
                    continue
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                sig = (st.st_size, int(st.st_mtime))
                if estable.get(path) != sig:
                    estable[path] = sig          # cambió: esperar a que se estabilice
                    continue
                try:
                    destino_rel, motivo = intake.procesar(
                        conn, path, args.destino,
                        analizar=not args.sin_analisis, mover=not args.copiar)
                except Exception as e:
                    destino_rel, motivo = "?", "error"
                print(f"  {etiquetas.get(motivo, motivo):13} {name}  ->  {destino_rel}")
                estable.pop(path, None)
            if args.una_vez:
                break
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nVigilancia detenida.")
    conn.close()
    return 0


def cmd_fingerprint(args):
    """Calcula la huella acústica (Chromaprint/fpcalc) de cada track."""
    _print_header()
    import fingerprint
    if not fingerprint.disponible():
        print("No encontré 'fpcalc' (Chromaprint). Bajá fpcalc.exe de")
        print("https://acoustid.org/chromaprint y dejalo en el PATH o junto al programa.")
        return 1
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT id, ruta_origen FROM tracks WHERE huella IS NULL").fetchall()
    if args.limit:
        rows = rows[:args.limit]
    total = len(rows)
    if total == 0:
        print("Todos los tracks ya tienen huella.")
        conn.close()
        return 0
    from multiprocessing import Pool, cpu_count
    procesos = args.procesos if args.procesos else max(1, cpu_count())
    print(f"Calculando huella de {total} tracks con {procesos} núcleos...\n")
    paths = [r["ruta_origen"] for r in rows]
    idporpath = {r["ruta_origen"]: r["id"] for r in rows}
    ok = fallo = 0
    with Pool(processes=procesos) as pool:
        for idx, (path, dur, fp) in enumerate(
                pool.imap_unordered(fingerprint.calcular_worker, paths, chunksize=4), 1):
            if fp:
                conn.execute("UPDATE tracks SET huella=?, huella_dur=? WHERE id=?",
                             (fp, dur, idporpath[path]))
                ok += 1
            else:
                fallo += 1
            if idx % 50 == 0 or idx == total:
                print(f"  {idx}/{total}...")
                conn.commit()
    conn.commit()
    print(f"\nHuellas calculadas: {ok} | fallidas: {fallo}")
    print("Ahora corré 'duplicates' para encontrar repetidos.")
    conn.close()
    return 0


def cmd_duplicates(args):
    """Detecta duplicados comparando huellas acústicas y sugiere cuál conservar."""
    _print_header()
    import fingerprint
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT id, ruta_origen, artista, titulo, huella, huella_dur, "
        "bitrate_kbps, formato FROM tracks WHERE huella IS NOT NULL "
        "ORDER BY huella_dur").fetchall()
    if len(rows) < 2:
        print("No hay suficientes huellas. Corré 'fingerprint' primero.")
        conn.close()
        return 0
    rows = list(rows)
    arrs = [fingerprint.a_array(r["huella"]) for r in rows]
    n = len(rows)
    padre = list(range(n))

    def find(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def union(a, b):
        padre[find(a)] = find(b)

    # comparar solo tracks de duración parecida (ventana de ±tol s)
    tol = args.tolerancia
    comparaciones = 0
    for i in range(n):
        di = rows[i]["huella_dur"] or 0
        j = i + 1
        while j < n and (rows[j]["huella_dur"] or 0) - di <= tol:
            if fingerprint.son_duplicados(arrs[i], arrs[j], args.umbral):
                union(i, j)
            comparaciones += 1
            j += 1

    grupos = {}
    for i in range(n):
        grupos.setdefault(find(i), []).append(i)
    dups = [g for g in grupos.values() if len(g) > 1]

    if not dups:
        print(f"No se encontraron duplicados ({comparaciones} comparaciones).")
        conn.close()
        return 0

    def calidad(r):
        loss = r["formato"] in ("wav", "aiff", "aif", "flac")
        return (10000 if loss else 0) + (r["bitrate_kbps"] or 0)

    total_dup = sum(len(g) - 1 for g in dups)
    print(f"Encontrados {len(dups)} grupos de duplicados ({total_dup} archivos sobrantes):\n")

    if not args.borrar:
        for g in dups:
            miembros = sorted((rows[i] for i in g), key=calidad, reverse=True)
            mejor = miembros[0]
            print(f"  ▸ {mejor['artista']} - {mejor['titulo']}")
            for k, r in enumerate(miembros):
                marca = "CONSERVAR" if k == 0 else "duplicado"
                cal = f"{r['formato']} {r['bitrate_kbps'] or '?'}kbps"
                print(f"      [{marca}] {cal:14} {r['ruta_origen']}")
            print()
        print("(Para borrar interactivamente: agregá --borrar)")
        conn.close()
        return 0

    # Modo borrado asistido: grupo por grupo
    borrados = saltados = errores = 0
    for idx, g in enumerate(dups, 1):
        miembros = sorted((rows[i] for i in g), key=calidad, reverse=True)
        mejor = miembros[0]
        print(f"\n[Grupo {idx}/{len(dups)}] {mejor['artista']} - {mejor['titulo']}")
        for k, r in enumerate(miembros, 1):
            marca = "CONSERVAR" if k == 1 else "duplicado "
            cal = f"{r['formato']} {r['bitrate_kbps'] or '?'}kbps"
            print(f"  {k}) [{marca}] {cal:14}  {r['ruta_origen']}")

        conservar_idx = 0
        val = input(
            "  [Enter=borrar duplicados / número=conservar ese / n=saltar / q=salir] > "
        ).strip().lower()

        if val == "q":
            print("Sesión interrumpida.")
            break
        if val == "n":
            saltados += 1
            continue
        if val.isdigit():
            i = int(val) - 1
            if 0 <= i < len(miembros):
                conservar_idx = i
            else:
                print("  (número fuera de rango, uso la sugerencia)")

        a_conservar = miembros[conservar_idx]
        a_borrar = [r for k, r in enumerate(miembros) if k != conservar_idx]

        for r in a_borrar:
            try:
                if os.path.exists(r["ruta_origen"]):
                    os.remove(r["ruta_origen"])
                conn.execute("DELETE FROM tracks WHERE id=?", (r["id"],))
                borrados += 1
            except Exception as e:
                print(f"  Error al borrar {r['ruta_origen']}: {e}")
                errores += 1
        conn.commit()
        etiq = f"{a_conservar['formato']} {a_conservar['bitrate_kbps'] or '?'}kbps"
        print(f"  -> Conservado: {etiq}  ({a_conservar['ruta_origen']})")

    print(f"\nBorrados: {borrados}  |  Saltados: {saltados}  |  Errores: {errores}")
    conn.close()
    return 0


def cmd_import_traktor(args):
    """Importa BPM/key exactos desde un export NML de Traktor."""
    _print_header()
    import traktor_nml
    if not os.path.exists(args.nml):
        print(f"No existe el archivo: {args.nml}")
        return 1
    try:
        tracks, version = traktor_nml.parse(args.nml)
    except Exception as e:
        print(f"No se pudo leer el NML: {e}")
        return 1
    print(f"Traktor NML v{version} — {len(tracks)} tracks en la colección\n")
    conn = db.connect(args.db)
    act, sin_match, sin_bpm = _match_y_actualizar(conn, tracks, "traktor")
    print(f"BPM/key actualizados desde Traktor : {act}")
    print(f"Tracks del NML sin match en tu base: {sin_match}")
    if sin_bpm:
        print(f"Tracks sin BPM en el NML           : {sin_bpm}")
    conn.close()
    return 0


def cmd_import_serato(args):
    """Importa BPM/key exactos desde la base de datos de Serato (database V2)."""
    _print_header()
    import serato_db
    if not os.path.exists(args.archivo):
        print(f"No existe el archivo: {args.archivo}")
        return 1
    try:
        tracks, version = serato_db.parse(args.archivo)
    except Exception as e:
        print(f"No se pudo leer la base de Serato: {e}")
        return 1
    print(f"Serato database V2 ({version}) — {len(tracks)} tracks en la colección\n")
    conn = db.connect(args.db)
    act, sin_match, sin_bpm = _match_y_actualizar(conn, tracks, "serato")
    print(f"BPM/key actualizados desde Serato    : {act}")
    print(f"Tracks de Serato sin match en tu base: {sin_match}")
    if sin_bpm:
        print(f"Tracks sin BPM en Serato             : {sin_bpm}")
    conn.close()
    return 0


def cmd_import_getsongbpm(args):
    """Trae BPM/key desde la API pública de GetSongBPM (por artista+título)."""
    _print_header()
    import time
    import getsongbpm
    conn = db.connect(args.db)
    # Tracks que aún no tienen una fuente confiable de BPM
    rows = conn.execute(
        "SELECT id, artista, titulo FROM tracks "
        "WHERE bpm_fuente IS NULL OR bpm_fuente='audio'").fetchall()
    if args.limit:
        rows = rows[:args.limit]
    total = len(rows)
    print(f"Consultando GetSongBPM para {total} tracks...\n")
    ok = sin = err = 0
    for idx, r in enumerate(rows, 1):
        data = getsongbpm.buscar(args.api_key, r["artista"], r["titulo"])
        if data.ok:
            conn.execute(
                "UPDATE tracks SET bpm=COALESCE(NULLIF(?,''), bpm), "
                "key=COALESCE(NULLIF(?,''), key), "
                "camelot=COALESCE(NULLIF(?,''), camelot), "
                "bpm_fuente='getsongbpm' WHERE id=?",
                (data.bpm, data.key, data.camelot, r["id"]))
            ok += 1
        elif data.error.startswith("red:"):
            err += 1
        else:
            sin += 1
        if idx % 20 == 0 or idx == total:
            print(f"  {idx}/{total}  (encontrados {ok}, sin match {sin}, errores {err})")
            conn.commit()
        time.sleep(args.pausa)   # cortesía con la API (límite 3000/hora)
    conn.commit()
    print(f"\nEncontrados en GetSongBPM : {ok}")
    print(f"Sin match                 : {sin}")
    if err:
        print(f"Errores de red            : {err}")
    print("\n(Recordá: GetSongBPM exige un backlink a getsongbpm.com en tu app.)")
    conn.close()
    return 0


def cmd_import_rekordbox(args):
    """Importa BPM y key EXACTOS desde un export XML de Rekordbox."""
    _print_header()
    import os
    import rekordbox_xml
    if not os.path.exists(args.xml):
        print(f"No existe el archivo: {args.xml}")
        return 1
    try:
        rbtracks, version = rekordbox_xml.parse(args.xml)
    except Exception as e:
        print(f"No se pudo leer el XML: {e}")
        return 1
    print(f"Rekordbox XML v{version} — {len(rbtracks)} tracks en la colección\n")

    conn = db.connect(args.db)
    actualizados, sin_match, sin_bpm = _match_y_actualizar(conn, rbtracks, "rekordbox")
    print(f"BPM/key actualizados desde Rekordbox : {actualizados}")
    print(f"Tracks del XML sin match en tu base  : {sin_match}")
    if sin_bpm:
        print(f"Tracks sin BPM en el XML             : {sin_bpm}")
    print("\n(Los BPM de Rekordbox son ahora la fuente exacta; el análisis de "
          "audio no los sobrescribe.)")
    conn.close()
    return 0


def _reproducir(path, inicio, seg):
    """Reproduce un fragmento con ffplay (viene con ffmpeg). Devuelve el proceso."""
    import subprocess
    try:
        return subprocess.Popen(
            ["ffplay", "-ss", str(inicio), "-t", str(seg), "-autoexit",
             "-nodisp", "-loglevel", "quiet", path])
    except FileNotFoundError:
        return None


def _camelot_compatibles(cam):
    """Keys compatibles con cam en la rueda de Camelot (±1 + paralela).
    Ej: '8A' → {'7A', '8A', '9A', '8B'}."""
    if not cam or len(cam) < 2:
        return set()
    try:
        num = int(cam[:-1])
        letra = cam[-1].upper()
    except ValueError:
        return set()
    compat = {f"{((num - 1 + d) % 12) + 1}{letra}" for d in (-1, 0, 1)}
    compat.add(f"{num}{'B' if letra == 'A' else 'A'}")
    return compat


def _siguiente_smart(pool, actual, args):
    """Elige el siguiente track del pool aplicando los filtros dinámicos activos.
    Devuelve un track elegido al azar entre los compatibles, o del pool completo
    si no hay candidatos."""
    import random
    if not pool:
        return None
    candidatos = list(pool)

    if getattr(args, "mismo_genero", False) and actual.get("genero"):
        candidatos = [r for r in candidatos if r["genero"] == actual["genero"]]

    if getattr(args, "misma_key", False) and actual.get("camelot"):
        compat = _camelot_compatibles(actual["camelot"])
        candidatos = [r for r in candidatos if r["camelot"] in compat]

    if getattr(args, "mismo_bpm", False) and actual.get("bpm"):
        try:
            bpm_ref = float(actual["bpm"])
            tol = args.tolerancia_bpm
            candidatos = [r for r in candidatos
                          if abs(float(r["bpm"] or 0) - bpm_ref) <= tol]
        except (ValueError, TypeError):
            pass

    if getattr(args, "misma_energia", False) and actual.get("energia_ef") is not None:
        tol = args.tolerancia_energia
        candidatos = [r for r in candidatos
                      if r["energia_ef"] is not None
                      and abs(r["energia_ef"] - actual["energia_ef"]) <= tol]

    if not candidatos:
        print("  (sin tracks compatibles — eligiendo al azar del pool restante)")
        candidatos = list(pool)

    return random.choice(candidatos)


def cmd_calibrate(args):
    """Calibrar Energía: el DJ escucha tracks al azar y los califica 1-10;
    el sistema aprende su percepción y la aplica a toda la biblioteca."""
    _print_header()
    import random
    from datetime import datetime
    import calibration_model as cm
    analyzer = _lazy_analyzer()
    conn = db.connect(args.db)

    # Calibrar dentro de UN género/subgénero = percepción más confiable.
    base = "energia_manual IS NULL AND f_low IS NOT NULL"
    if args.subgenero:
        genero_obj = args.subgenero
        where = base + " AND subgenero = ?"
        params = (args.subgenero,)
    elif args.genero:
        genero_obj = args.genero
        where = base + " AND COALESCE(genero, genero_sugerido) = ?"
        params = (args.genero,)
    else:
        # auto: el género (confirmado o sugerido) con más tracks sin calificar
        g = conn.execute(
            "SELECT COALESCE(genero, genero_sugerido) AS g, COUNT(*) AS n "
            f"FROM tracks WHERE {base} AND COALESCE(genero, genero_sugerido) IS NOT NULL "
            "GROUP BY g ORDER BY n DESC LIMIT 1").fetchone()
        genero_obj = g["g"] if g else None
        where = base + (" AND COALESCE(genero, genero_sugerido) = ?" if genero_obj else "")
        params = (genero_obj,) if genero_obj else ()

    rows = conn.execute(
        f"SELECT id, ruta_origen, artista, titulo, energia FROM tracks WHERE {where}",
        params).fetchall()
    if not rows:
        print("No hay tracks para calibrar con ese filtro. ¿Corriste 'analyze' "
              "(versión nueva que guarda los rasgos)? ¿O ya calificaste todo ese género?")
        conn.close()
        return 0
    rows = list(rows)
    random.shuffle(rows)
    seleccion = rows[:args.cantidad]

    if genero_obj:
        print(f"Calibrando dentro del género: {genero_obj}")
    print(f"Te voy a pasar {len(seleccion)} tracks. Reproduzco el momento más intenso;")
    print("escuchá y poné la energía de 1 a 10. (Enter = saltar · 'q' = terminar)\n")
    proc = None
    for i, r in enumerate(seleccion, 1):
        print(f"[{i}/{len(seleccion)}] {r['artista']} - {r['titulo']}   (auto actual: {r['energia']})")
        # reproducir el fragmento más intenso del track
        inicio = args.inicio if args.inicio is not None else analyzer.pico_intensidad(r["ruta_origen"])
        proc = _reproducir(r["ruta_origen"], inicio, args.seg)
        if proc is None:
            print("  (No encontré 'ffplay'. Instalá ffmpeg completo o calificá de memoria.)")
        try:
            val = input("   Energía 1-10: ").strip().lower()
        finally:
            if proc:
                proc.terminate()
        if val == "q":
            break
        if not val:
            continue
        try:
            e = int(val)
            if 1 <= e <= 10:
                conn.execute("UPDATE tracks SET energia_manual=? WHERE id=?", (e, r["id"]))
                conn.commit()
            else:
                print("   (fuera de 1-10, lo salteo)")
        except ValueError:
            print("   (no es un número, lo salteo)")

    labeled = conn.execute(
        "SELECT f_loud, f_bright, f_low, f_busy, bpm, camelot, key, energia_manual "
        "FROM tracks WHERE energia_manual IS NOT NULL AND f_low IS NOT NULL").fetchall()
    print(f"\nTracks calificados en total: {len(labeled)}")
    if len(labeled) < cm.MIN_MUESTRAS:
        faltan = cm.MIN_MUESTRAS - len(labeled)
        print(f"Calificá {faltan} más y el sistema va a poder aprender tu oído. "
              f"Volvé a correr 'calibrate' cuando quieras.")
        conn.close()
        return 0

    X = [cm.vector_features(r) for r in labeled]
    y = [r["energia_manual"] for r in labeled]
    coef = cm.entrenar(X, y)
    conn.execute(
        "INSERT INTO modelo_energia(id, coef, n_muestras, fecha) VALUES(1, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET coef=excluded.coef, "
        "n_muestras=excluded.n_muestras, fecha=excluded.fecha",
        (cm.serializar(coef), len(labeled), datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    n = _recalibrar_energia(conn)
    print(f"\n¡Aprendido! El sistema ajustó la energía de {n} tracks a tu oído")
    print(f"(modelo entrenado con {len(labeled)} calificaciones tuyas).")
    print("Cuantos más tracks califiques y vuelvas a correr 'calibrate', mejor aprende.")
    conn.close()
    return 0


def cmd_rate(args):
    """Fija manualmente la energía (1-10) de los tracks que matcheen un texto.
    Tu valor manual manda sobre el automático y nunca se sobrescribe."""
    _print_header()
    if not (1 <= args.energia <= 10):
        print("La energía debe estar entre 1 y 10.")
        return 1
    conn = db.connect(args.db)
    patron = f"%{args.buscar}%"
    rows = conn.execute(
        "SELECT id, artista, titulo FROM tracks "
        "WHERE titulo LIKE ? OR artista LIKE ?", (patron, patron)).fetchall()
    if not rows:
        print(f"Ningún track coincide con '{args.buscar}'.")
        conn.close()
        return 0
    if len(rows) > 1 and not args.todos:
        print(f"Coinciden {len(rows)} tracks con '{args.buscar}':")
        for r in rows:
            print(f"  • {r['artista']} - {r['titulo']}")
        print("\nAfiná la búsqueda, o repetí con --todos para aplicar a todos.")
        conn.close()
        return 0
    for r in rows:
        conn.execute("UPDATE tracks SET energia_manual=? WHERE id=?",
                     (args.energia, r["id"]))
        print(f"  energía {args.energia} → {r['artista']} - {r['titulo']}")
    conn.commit()
    conn.close()
    return 0


def cmd_show(args):
    """Muestra los tracks ya analizados con sus features."""
    _print_header()
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT artista, titulo, genero, subgenero, bpm, key, camelot, "
        "energia, energia_manual, "
        "genero_sugerido, subgenero_sugerido FROM tracks "
        "WHERE analizado=1 AND (nota_sugerencia IS NULL OR nota_sugerencia NOT LIKE 'error:%') "
        "ORDER BY CAST(bpm AS REAL)").fetchall()
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        print("Todavía no hay tracks analizados. Corré 'analyze' primero.")
        conn.close()
        return 0
    print(f"{'ARTISTA - TÍTULO':<42} {'BPM':>5} {'KEY':>7} {'CAM':>4} {'E':>2}  GÉNERO")
    print("-" * 96)
    for r in rows:
        nombre = f"{r['artista'] or '?'} - {r['titulo'] or '?'}"[:40]
        bpm = r["bpm"] or ""
        key = r["key"] or ""
        cam = r["camelot"] or ""
        # Energía manual (tu valor) manda sobre la automática; se marca con *
        if r["energia_manual"] is not None:
            ener = f"{r['energia_manual']}*"
        elif r["energia"] is not None:
            ener = str(r["energia"])
        else:
            ener = ""
        if r["genero"]:
            genero = f"{r['genero']}/{r['subgenero']}" if r["subgenero"] else r["genero"]
        else:
            g = r["genero_sugerido"] or "?"
            s = r["subgenero_sugerido"] or ""
            genero = f"~{g}/{s}" if s else f"~{g}"  # ~ = sugerido
        print(f"{nombre:<42} {bpm:>5} {key:>7} {cam:>4} {ener:>3}  {genero}")
    print("\n(E con * = tu energía manual. ~ en género = sugerido por audio.)")
    conn.close()
    return 0


# ----------------------------------------------------------- PLAYLISTS
def _reglas_desde_args(args) -> dict:
    reglas = {}
    for k in ("genero", "subgenero", "key", "bpm_min", "bpm_max",
              "energia_min", "energia_max"):
        v = getattr(args, k, None)
        if v not in (None, ""):
            reglas[k] = v
    return reglas


def _where_desde_reglas(reglas: dict):
    """Construye (WHERE, params) a partir de un dict de reglas."""
    cond, params = [], []
    if reglas.get("genero"):
        cond.append("genero = ?")
        params.append(reglas["genero"])
    if reglas.get("subgenero"):
        cond.append("subgenero = ?")
        params.append(reglas["subgenero"])
    if reglas.get("key"):
        cond.append("(key = ? OR camelot = ?)")
        params += [reglas["key"], reglas["key"]]
    if reglas.get("bpm_min") is not None:
        cond.append("CAST(NULLIF(bpm,'') AS REAL) >= ?")
        params.append(float(reglas["bpm_min"]))
    if reglas.get("bpm_max") is not None:
        cond.append("CAST(NULLIF(bpm,'') AS REAL) <= ?")
        params.append(float(reglas["bpm_max"]))
    if reglas.get("energia_min") is not None:
        cond.append("COALESCE(energia_manual, energia) >= ?")
        params.append(int(reglas["energia_min"]))
    if reglas.get("energia_max") is not None:
        cond.append("COALESCE(energia_manual, energia) <= ?")
        params.append(int(reglas["energia_max"]))
    where = " AND ".join(cond) if cond else "1=1"
    return where, params


def _tracks_por_reglas(conn, reglas: dict):
    where, params = _where_desde_reglas(reglas)
    sql = ("SELECT ruta_origen, artista, titulo, bpm, key, genero, sello "
           f"FROM tracks WHERE {where} ORDER BY CAST(NULLIF(bpm,'') AS REAL)")
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def cmd_playlist_create(args):
    _print_header()
    reglas = _reglas_desde_args(args)
    if not reglas:
        print("Definí al menos un filtro (ej. --genero Techno --bpm-min 120).")
        return 1
    conn = db.connect(args.db)
    conn.execute(
        "INSERT INTO playlists(nombre, reglas) VALUES(?, ?) "
        "ON CONFLICT(nombre) DO UPDATE SET reglas=excluded.reglas",
        (args.nombre, json.dumps(reglas)))
    conn.commit()
    n = len(_tracks_por_reglas(conn, reglas))
    print(f"Playlist '{args.nombre}' guardada.")
    print(f"  Reglas: {reglas}")
    print(f"  Coinciden ahora: {n} tracks")
    conn.close()
    return 0


def cmd_playlist_list(args):
    _print_header()
    conn = db.connect(args.db)
    rows = conn.execute("SELECT nombre, reglas FROM playlists ORDER BY nombre").fetchall()
    if not rows:
        print("No hay playlists. Creá una con 'playlist-create'.")
    else:
        for r in rows:
            reglas = json.loads(r["reglas"])
            n = len(_tracks_por_reglas(conn, reglas))
            print(f"  • {r['nombre']:<28} {n:>4} tracks   {reglas}")
    conn.close()
    return 0


def cmd_playlist_export(args):
    _print_header()
    import rekordbox_export
    conn = db.connect(args.db)
    if args.nombre:
        row = conn.execute(
            "SELECT reglas FROM playlists WHERE nombre=?", (args.nombre,)).fetchone()
        if not row:
            print(f"No existe la playlist '{args.nombre}'.")
            return 1
        reglas = json.loads(row["reglas"])
        nombre = args.nombre
    else:
        reglas = _reglas_desde_args(args)
        nombre = args.como or "Asistente DJ"
    tracks = _tracks_por_reglas(conn, reglas)
    if not tracks:
        print("Ningún track coincide con esos filtros; no se exporta nada.")
        return 0
    n = rekordbox_export.escribir_playlist(tracks, nombre, args.salida)
    print(f"Exportados {n} tracks a la playlist '{nombre}'.")
    print(f"Archivo: {args.salida}")
    print("\nEn Rekordbox: Preferences > View > Layout: activá 'rekordbox xml';")
    print("Preferences > Advanced > rekordbox xml: apuntá a este archivo.")
    print("Aparece la vista 'rekordbox xml' y arrastrás la playlist a tu colección.")
    conn.close()
    return 0


def cmd_plan(args):
    _print_header()
    conn = db.connect(args.db)
    plan = build_plan(conn)
    print(f"Plan de archivado ({len(plan)} tracks) — SIMULACIÓN, no copia nada:\n")
    for item in plan:
        marca = {"exacta": "OK ", "parcial": "~  ", "ninguna": "?? "}.get(
            item.confianza, "   ")
        print(f"  [{marca}] {item.destino_rel}/{item.nombre}")
    conn.close()
    return 0


def cmd_archive(args):
    _print_header()
    conn = db.connect(args.db)
    plan = build_plan(conn)
    dry = not args.apply
    modo = "SIMULACIÓN (dry-run)" if dry else "EJECUCIÓN REAL (copiando)"
    print(f"Archivando a: {args.destino}   [{modo}]\n")
    res = execute_plan(conn, plan, args.destino, dry_run=dry)
    print(f"  Copiados : {res['copiados']}")
    print(f"  Saltados : {res['saltados']}")
    print(f"  Errores  : {res['errores']}")
    if dry:
        print("\n(Para copiar de verdad, repetí el comando con --apply)")
    conn.close()
    return 0


def cmd_generos(args):
    """Lista los géneros NO reconocidos, ordenados por frecuencia.

    Sirve para descubrir qué alias hay que agregar a config.GENRE_ALIASES.
    """
    _print_header()
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT COALESCE(NULLIF(TRIM(genero_raw), ''), '(sin tag)') AS g, "
        "COUNT(*) AS n FROM tracks WHERE genero IS NULL "
        "GROUP BY g ORDER BY n DESC").fetchall()
    if not rows:
        print("No hay géneros sin reconocer. 🎉")
    else:
        total = sum(r["n"] for r in rows)
        print(f"Géneros no reconocidos ({total} tracks, {len(rows)} nombres distintos):\n")
        for r in rows:
            print(f"  {r['n']:>5}  {r['g']}")
    conn.close()
    return 0


def cmd_review(args):
    _print_header()
    conn = db.connect(args.db)
    rows = conn.execute(
        "SELECT id, titulo, artista, genero_raw, ruta_origen, "
        "genero_sugerido, subgenero_sugerido FROM tracks "
        "WHERE genero IS NULL ORDER BY artista, titulo"
    ).fetchall()

    if not rows:
        print("No hay tracks pendientes de revisión.")
        conn.close()
        return 0

    print(f"Tracks a revisar ({len(rows)}) — género no reconocido:\n")

    if not args.resolver:
        for r in rows:
            tag_g = r["genero_raw"] or "(sin tag)"
            sug = r["genero_sugerido"] or ""
            sug_sub = r["subgenero_sugerido"] or ""
            sug_str = ""
            if sug:
                sug_str = f"  [sugerido: {sug + '/' + sug_sub if sug_sub else sug}]"
            linea = f"  - {r['artista']} - {r['titulo']}   (tag: {tag_g}){sug_str}"
            print(linea.encode("cp1252", errors="replace").decode("cp1252"))
        print("\n(Para asignar géneros interactivamente: agregá --resolver)")
        conn.close()
        return 0

    # Modo resolver: asignación interactiva
    total = len(rows)
    if args.limit:
        rows = rows[:args.limit]
    resueltos = saltados = 0

    for idx, r in enumerate(rows, 1):
        print(f"\n[{idx}/{len(rows)}] {r['artista']} - {r['titulo']}")
        tag_g = r["genero_raw"] or "(sin tag)"
        print(f"  Tag de género : {tag_g}")
        sug = r["genero_sugerido"] or ""
        sug_sub = r["subgenero_sugerido"] or ""
        if sug:
            sug_str = f"{sug}/{sug_sub}" if sug_sub else sug
            print(f"  Análisis sugiere: {sug_str}")

        label = f"{r['artista']} - {r['titulo']} (tag: {tag_g})"
        eleccion = _elegir_genero(label, r["ruta_origen"])

        if eleccion == "SKIP":
            saltados += 1
            continue
        if eleccion is None:
            saltados += 1
            continue

        genero, subgenero = eleccion
        conn.execute(
            "UPDATE tracks SET genero=?, subgenero=?, estado='archivado' WHERE id=?",
            (genero, subgenero, r["id"]))
        conn.commit()
        resueltos += 1
        etiqueta = f"{genero}/{subgenero}" if subgenero else genero
        print(f"  -> Asignado: {etiqueta}")

    pendientes = total - resueltos
    print(f"\nResueltos: {resueltos}  |  Pendientes: {pendientes}")
    if resueltos:
        print("(Corré 'archive <destino> --apply' para mover los archivos a su carpeta.)")
    conn.close()
    return 0


def cmd_play(args):
    """Reproduce tracks de la biblioteca en cola con navegación simple y smart shuffle."""
    _print_header()
    import random as rand_mod
    import subprocess
    import time

    conn = db.connect(args.db)
    filtros = ["ruta_origen IS NOT NULL"]
    params = []
    if args.genero:
        filtros.append("genero = ?"); params.append(args.genero)
    if args.subgenero:
        filtros.append("subgenero = ?"); params.append(args.subgenero)
    if args.bpm_min:
        filtros.append("CAST(bpm AS REAL) >= ?"); params.append(args.bpm_min)
    if args.bpm_max:
        filtros.append("CAST(bpm AS REAL) <= ?"); params.append(args.bpm_max)
    if args.energia_min:
        filtros.append("COALESCE(energia_manual, energia) >= ?"); params.append(args.energia_min)
    if args.energia_max:
        filtros.append("COALESCE(energia_manual, energia) <= ?"); params.append(args.energia_max)

    filas = conn.execute(
        "SELECT id, ruta_origen, artista, titulo, bpm, key, camelot, "
        "COALESCE(energia_manual, energia) AS energia_ef, genero, subgenero "
        f"FROM tracks WHERE {' AND '.join(filtros)}", params).fetchall()
    conn.close()

    if not filas:
        print("No hay tracks que coincidan con los filtros.")
        return 0

    filas = [dict(r) for r in filas]
    orden = args.orden or "random"
    smart = any([args.mismo_genero, args.misma_key, args.mismo_bpm, args.misma_energia])

    if orden != "random":
        if orden == "bpm":
            filas.sort(key=lambda r: float(r["bpm"] or 0))
        elif orden == "energia":
            filas.sort(key=lambda r: r["energia_ef"] or 0, reverse=True)
        elif orden == "artista":
            filas.sort(key=lambda r: (r["artista"] or "").lower())
        if args.limit:
            filas = filas[:args.limit]
        cola = filas
        usar_pool = False
    else:
        if args.limit:
            rand_mod.shuffle(filas)
            filas = filas[:args.limit]
        pool = list(filas)
        rand_mod.shuffle(pool)
        usar_pool = True

    total = len(filas) if not usar_pool else len(pool)
    modo_str = orden + (" + smart shuffle" if smart and orden == "random" else "")
    print(f"Cola: {total} tracks  |  Orden: {modo_str}")
    if smart and orden == "random":
        fa = []
        if args.mismo_genero:  fa.append("género")
        if args.misma_key:     fa.append("key Camelot ±1")
        if args.mismo_bpm:     fa.append(f"BPM ±{args.tolerancia_bpm}")
        if args.misma_energia: fa.append(f"energía ±{args.tolerancia_energia}")
        print(f"Smart shuffle: {', '.join(fa)}")
    print("Controles: Enter/n = siguiente  |  a = anterior  |  q = salir\n")

    try:
        import msvcrt
        _msvcrt = True
    except ImportError:
        _msvcrt = False

    reproducidos = 0
    historial = []

    def _reproducir_track(r):
        nombre = f"{r['artista'] or '?'} - {r['titulo'] or '?'}"
        bpm_s  = r["bpm"] or "?"
        key_s  = r["key"] or "?"
        cam_s  = r["camelot"] or ""
        ener_s = str(r["energia_ef"]) if r["energia_ef"] is not None else "?"
        gen_s  = (f"{r['genero']}/{r['subgenero']}" if r["subgenero"]
                  else (r["genero"] or "sin género"))
        print(f"[{reproducidos + 1}/{total}] {nombre}")
        print(f"  BPM {bpm_s}  Key {key_s}  {cam_s}  E:{ener_s}  {gen_s}")
        try:
            return subprocess.Popen(
                ["ffplay", "-autoexit", "-nodisp", "-loglevel", "quiet",
                 r["ruta_origen"]])
        except FileNotFoundError:
            print("  (ffplay no encontrado — instalá ffmpeg)")
            return None

    def _esperar(proc):
        accion = "next"
        if _msvcrt:
            print("> ", end="", flush=True)
            while True:
                if proc and proc.poll() is not None:
                    print(); break
                if msvcrt.kbhit():
                    ch = msvcrt.getwch().lower()
                    print()
                    if ch in ("\r", "\n", " ", "n"): accion = "next"
                    elif ch == "a":                   accion = "prev"
                    elif ch == "q":                   accion = "quit"
                    if proc: proc.terminate()
                    break
                time.sleep(0.05)
        else:
            val = input("> ").strip().lower()
            if proc: proc.terminate()
            if val == "a":   accion = "prev"
            elif val == "q": accion = "quit"
        return accion

    if usar_pool:
        actual = pool.pop(rand_mod.randrange(len(pool)))
        while True:
            proc = _reproducir_track(actual)
            reproducidos += 1
            historial.append(actual)
            accion = _esperar(proc)
            print()
            if accion == "quit":
                print("Reproductor cerrado."); break
            elif accion == "prev" and len(historial) >= 2:
                pool.append(historial.pop())
                actual = historial.pop()
                reproducidos -= 2
            elif not pool:
                print("Fin de la cola."); break
            else:
                siguiente = (_siguiente_smart(pool, actual, args)
                             if smart else pool[rand_mod.randrange(len(pool))])
                if siguiente in pool:
                    pool.remove(siguiente)
                actual = siguiente
    else:
        idx = 0
        while 0 <= idx < len(cola):
            actual = cola[idx]
            proc = _reproducir_track(actual)
            reproducidos += 1
            accion = _esperar(proc)
            print()
            if accion == "quit":
                print("Reproductor cerrado."); break
            elif accion == "prev":
                idx = max(0, idx - 1)
                reproducidos -= 2
            else:
                idx += 1
        else:
            print("Fin de la cola.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Asistente DJ — Módulo 1 (prototipo)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scan", help="Escanear una carpeta")
    sp.add_argument("carpeta")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("plan", help="Ver el plan de archivado (simulación)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("archive", help="Archivar por género")
    sp.add_argument("destino")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.add_argument("--apply", action="store_true", help="Copiar de verdad")
    sp.set_defaults(func=cmd_archive)

    sp = sub.add_parser("review", help="Listar (y opcionalmente resolver) tracks sin género")
    sp.add_argument("--resolver", action="store_true",
                    help="Asignar género interactivamente a cada track sin clasificar")
    sp.add_argument("--limit", type=int, default=0,
                    help="Procesar solo N tracks (útil para sesiones cortas)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_review)

    sp = sub.add_parser("generos", help="Géneros no reconocidos (por frecuencia)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_generos)

    sp = sub.add_parser("analyze", help="Analizar audio (BPM/key/energía) y sugerir género")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.add_argument("--limit", type=int, default=0, help="Analizar solo N tracks (prueba)")
    sp.add_argument("--reintentar", action="store_true",
                    help="Volver a intentar los que fallaron antes")
    sp.add_argument("--reset", action="store_true",
                    help="Reanalizar TODOS los tracks desde cero")
    sp.add_argument("--procesos", type=int, default=0,
                    help="Núcleos a usar (0 = todos)")
    sp.set_defaults(func=cmd_analyze)

    sp = sub.add_parser("show", help="Ver tracks analizados (BPM/key/energía/género)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.add_argument("--limit", type=int, default=0)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("resuggest", help="Recalcular sugerencias de género (rápido, sin re-analizar)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_resuggest)

    sp = sub.add_parser("reclassify", help="Re-clasificar tracks sin género con los aliases actuales")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_reclassify)

    sp = sub.add_parser("lookup-genre", help="Buscar género online (MusicBrainz/Last.fm) para tracks sin género")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.add_argument("--lastfm-key", default="", metavar="KEY",
                    help="API key de Last.fm (gratis en last.fm/api) para mayor cobertura")
    sp.add_argument("--limit", type=int, default=0, metavar="N",
                    help="Procesar solo los primeros N tracks (prueba)")
    sp.set_defaults(func=cmd_lookup_genre)

    sp = sub.add_parser("predict-genre",
                        help="Clasificar tracks sin género por espectro acústico (KNN)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.add_argument("--apply", action="store_true",
                    help="Guardar predicciones en BD (por defecto solo muestra)")
    sp.add_argument("--min-confianza", type=float, default=0.6, metavar="0-1",
                    help="Confianza mínima para aplicar (default 0.6)")
    sp.add_argument("--k", type=int, default=7,
                    help="Vecinos en KNN (default 7)")
    sp.add_argument("--limit", type=int, default=0, metavar="N",
                    help="Procesar solo los primeros N tracks")
    sp.set_defaults(func=cmd_predict_genre)

    sp = sub.add_parser("rate", help="Fijar energía manual (1-10) de un track")
    sp.add_argument("buscar", help="Texto del título o artista")
    sp.add_argument("energia", type=int, help="Energía 1-10")
    sp.add_argument("--todos", action="store_true", help="Aplicar a todos los que coincidan")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_rate)

    sp = sub.add_parser("calibrate", help="Calibrar Energía: escuchás y calificás; el sistema aprende tu oído")
    sp.add_argument("--cantidad", type=int, default=15, help="Cuántos tracks calificar en esta sesión")
    sp.add_argument("--seg", type=float, default=30, help="Segundos de fragmento a reproducir")
    sp.add_argument("--inicio", type=float, default=None,
                    help="Forzar segundo de inicio (por defecto: el momento más intenso)")
    sp.add_argument("--genero", help="Calibrar solo este género")
    sp.add_argument("--subgenero", help="Calibrar solo este subgénero")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_calibrate)

    sp = sub.add_parser("import-rekordbox", help="Importar BPM/key exactos desde un XML de Rekordbox")
    sp.add_argument("xml", help="Ruta al archivo .xml exportado de Rekordbox")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_import_rekordbox)

    sp = sub.add_parser("clean-tags", help="Limpiar tags basura (URLs de sitios de descarga)")
    sp.add_argument("--apply", action="store_true", help="Aplicar los cambios (sin esto, solo muestra)")
    sp.add_argument("--escribir-archivos", dest="escribir_archivos", action="store_true",
                    help="Además, reescribir los tags limpios en los archivos")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_clean_tags)

    sp = sub.add_parser("config", help="Ver/fijar configuración (biblioteca + Supabase)")
    sp.add_argument("--biblioteca", help="Ruta donde el asistente organiza la música")
    sp.add_argument("--supabase-url", dest="supabase_url",
                    help="URL del proyecto Supabase (Settings → API → Project URL)")
    sp.add_argument("--supabase-key", dest="supabase_key",
                    help="API key anon/public de Supabase (Settings → API → anon key)")
    sp.add_argument("--spotify-client-id", dest="spotify_client_id",
                    help="Client ID de tu app en developer.spotify.com/dashboard")
    sp.add_argument("--spotify-client-secret", dest="spotify_client_secret",
                    help="Client Secret de tu app en developer.spotify.com/dashboard")
    sp.set_defaults(func=cmd_config)

    sp = sub.add_parser("biblioteca",
                        help="Gestionar la Biblioteca Confiable en Supabase")
    sp.add_argument("accion", choices=["estado", "agregar", "listar", "artista"],
                    help="estado: verificar conexión | agregar: subir track | "
                         "listar: ver registros | artista: ver géneros que produce")
    sp.add_argument("--ruta", help="Ruta del track a agregar (para accion=agregar)")
    sp.add_argument("--genero", help="Filtrar por género (para accion=listar)")
    sp.add_argument("--limit", type=int, default=50, help="Máximo de resultados (listar)")
    sp.add_argument("nombre", nargs="?", help="Nombre del artista (para accion=artista)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_biblioteca)

    sp = sub.add_parser("import", help="Importar música desde una carpeta a la biblioteca del asistente")
    sp.add_argument("origen", help="Carpeta de donde tomar la música (recursivo)")
    sp.add_argument("--destino", help="Raíz de la biblioteca (por defecto, la configurada)")
    sp.add_argument("--sin-analisis", dest="sin_analisis", action="store_true",
                    help="No analizar audio (más rápido)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("fingerprint", help="Calcular huella acústica (Chromaprint) de los tracks")
    sp.add_argument("--limit", type=int, default=0)
    sp.add_argument("--procesos", type=int, default=0, help="Núcleos (0 = todos)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_fingerprint)

    sp = sub.add_parser("duplicates", help="Detectar duplicados por huella acústica")
    sp.add_argument("--borrar", action="store_true",
                    help="Borrar duplicados interactivamente (pide confirmación por grupo)")
    sp.add_argument("--umbral", type=float, default=0.15, help="Tolerancia de diferencia (0-1)")
    sp.add_argument("--tolerancia", type=float, default=15.0, help="Diferencia máxima de duración (s) para comparar")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_duplicates)

    sp = sub.add_parser("import-traktor", help="Importar BPM/key exactos desde un NML de Traktor")
    sp.add_argument("nml", help="Ruta al archivo .nml exportado de Traktor")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_import_traktor)

    sp = sub.add_parser("import-serato", help="Importar BPM/key exactos desde la base de datos de Serato")
    sp.add_argument("archivo",
                    help="Ruta al archivo 'database V2' de Serato "
                         "(normalmente en <música>/_Serato_/database V2)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_import_serato)

    sp = sub.add_parser("import-getsongbpm", help="Traer BPM/key desde la API pública GetSongBPM")
    sp.add_argument("--api-key", dest="api_key", required=True, help="Tu API key de getsongbpm.com")
    sp.add_argument("--limit", type=int, default=0, help="Procesar solo N tracks (prueba)")
    sp.add_argument("--pausa", type=float, default=0.5, help="Segundos entre consultas")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_import_getsongbpm)

    def _add_filtros(parser):
        parser.add_argument("--genero")
        parser.add_argument("--subgenero")
        parser.add_argument("--key", help="Tonalidad o Camelot (ej. 8A)")
        parser.add_argument("--bpm-min", dest="bpm_min", type=float)
        parser.add_argument("--bpm-max", dest="bpm_max", type=float)
        parser.add_argument("--energia-min", dest="energia_min", type=int)
        parser.add_argument("--energia-max", dest="energia_max", type=int)

    sp = sub.add_parser("play", help="Reproducir tracks de la biblioteca en cola")
    _add_filtros(sp)
    sp.add_argument("--orden", choices=["random", "bpm", "energia", "artista"],
                    default="random", help="Orden de reproducción (default: aleatorio)")
    sp.add_argument("--mismo-genero",    dest="mismo_genero",    action="store_true",
                    help="Smart shuffle: siguiente track del mismo género")
    sp.add_argument("--misma-key",       dest="misma_key",       action="store_true",
                    help="Smart shuffle: siguiente track con key compatible (Camelot ±1 + paralela)")
    sp.add_argument("--mismo-bpm",       dest="mismo_bpm",       action="store_true",
                    help="Smart shuffle: siguiente track con BPM similar")
    sp.add_argument("--misma-energia",   dest="misma_energia",   action="store_true",
                    help="Smart shuffle: siguiente track con energía similar")
    sp.add_argument("--tolerancia-bpm",  dest="tolerancia_bpm",  type=float, default=3.0,
                    help="Tolerancia de BPM para --mismo-bpm (default: ±3)")
    sp.add_argument("--tolerancia-energia", dest="tolerancia_energia", type=float, default=2.0,
                    help="Tolerancia de energía para --misma-energia (default: ±2)")
    sp.add_argument("--limit", type=int, default=0, help="Máximo de tracks en la cola")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_play)

    sp = sub.add_parser("playlist-create", help="Crear/guardar una playlist inteligente por filtros")
    sp.add_argument("nombre")
    _add_filtros(sp)
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_playlist_create)

    sp = sub.add_parser("playlist-list", help="Listar playlists guardadas y su conteo")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_playlist_list)

    sp = sub.add_parser("playlist-export", help="Exportar una playlist a Rekordbox XML")
    sp.add_argument("salida", help="Ruta del .xml a generar")
    sp.add_argument("--nombre", help="Nombre de una playlist guardada")
    sp.add_argument("--como", help="Nombre de la playlist si usás filtros directos")
    _add_filtros(sp)
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_playlist_export)

    sp = sub.add_parser("charts-generos", help="Listar géneros/sub-géneros de Beatport disponibles para scrapear")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_charts_generos)

    sp = sub.add_parser("charts-scrape", help="Scrapear el Top 100 de Beatport (global y/o por género)")
    sp.add_argument("--genero", help="Slug del género (ver charts-generos); si se omite, scrapea global + todos")
    sp.add_argument("--global-tambien", action="store_true",
                     help="Si se pasa --genero, scrapear también el Top 100 global")
    sp.add_argument("--sin-global", action="store_true",
                     help="Si NO se pasa --genero (todos los géneros), saltear el Top 100 "
                          "global porque ya está hecho")
    sp.add_argument("--solo-global", action="store_true",
                     help="Scrapear únicamente el Top 100 global, sin tocar géneros "
                          "(no hace descubrimiento). Pensado para corridas puntuales, "
                          "ej. desde un cron.")
    sp.add_argument("--delay-seg", type=float, default=None,
                     help="Segundos entre cada pedido a Beatport dentro de esta corrida "
                          "(default: 1800 = 30 min). Bajalo solo si algo externo ya espacia "
                          "las invocaciones, ej. un cron horario que llama a este comando "
                          "una vez por hora.")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_charts_scrape)

    sp = sub.add_parser("charts-show", help="Ver el Top N guardado de un chart (global o de un género)")
    sp.add_argument("--genero", help="Slug del género (default: global)")
    sp.add_argument("--top", type=int, default=20)
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_charts_show)

    sp = sub.add_parser("charts-novedades", help="Tracks nuevos desde el último scrape de un chart")
    sp.add_argument("--genero", help="Slug del género (default: global)")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_charts_novedades)

    sp = sub.add_parser("conseguir", help="Lista de 'para conseguir' (tracks a comprar/bajar)")
    sp.add_argument("accion", choices=["agregar", "listar", "marcar", "quitar"])
    sp.add_argument("nombre", nargs="?", help="Nombre del track (para 'agregar')")
    sp.add_argument("--artistas", help="Artistas (para 'agregar')")
    sp.add_argument("--sello", help="Sello (para 'agregar')")
    sp.add_argument("--notas", help="Notas libres (para 'agregar')")
    sp.add_argument("--id", type=int, help="ID de la entrada (para 'marcar'/'quitar')")
    sp.add_argument("--todos", action="store_true", help="Incluir ya conseguidos (para 'listar')")
    sp.add_argument("--db", default=DEFAULT_DB)
    sp.set_defaults(func=cmd_conseguir)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
