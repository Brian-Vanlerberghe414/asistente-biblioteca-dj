"""Biblioteca FeelBack (Feedback DJ) — motor de consenso hacia la Confiable.

Segunda biblioteca en Supabase (`biblioteca_feedback`) que junta las
correcciones/clasificaciones MANUALES de los usuarios (no del admin). Este
módulo:
  1. Recibe aportes (`registrar_aporte`) — lo usan los clientes cuando un
     usuario corrige un género a mano.
  2. Los evalúa por consenso y promueve a la Biblioteca Confiable
     (`evaluar`) — lo corre la rutina de nube cada 3 h y también el panel.
  3. Da vistas para el panel (`resumen_pendientes`, `listar_alertas`) y
     acciones manuales del admin (`aprobar`, `descartar`, `marcar_alerta_vista`).

Reutiliza el cliente de Supabase autenticado de `biblioteca_confiable.py`
(la cuenta de servicio es admin: ve todos los aportes y escribe la Confiable).

REGLAS (constantes abajo, fáciles de tunear):
  · Track NUEVO (no está en la Confiable):
      - 2 usuarios coinciden en género+subgénero  -> migra
      - 3 usuarios coinciden solo en género        -> migra (subgénero más votado)
  · Track en la Confiable por Beatport/auto:
      - 5 usuarios proponen un género distinto      -> migra y pisa
  · Track en la Confiable MANUAL (de Brian):
      - 5 usuarios proponen un género distinto      -> migra y pisa + ALERTA
  · Propuesta que coincide con lo que ya hay        -> se marca resuelta, sin tocar nada
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

import biblioteca_confiable as bc  # reutiliza cliente Supabase + normalización

# ── Config por defecto ────────────────────────────────────────────────────────
# Valores reales viven en la tabla `feedback_config` de Supabase (editable desde
# el panel), para que el panel local y la rutina de nube usen los MISMOS. Esto
# es solo el respaldo por si la tabla no existe o no responde.
_CONFIG_DEFAULT = {
    "umbral_genero_subgenero": 2,   # track nuevo: coinciden género+subgénero -> migra
    "umbral_solo_genero": 3,        # track nuevo: coinciden solo género        -> migra
    "umbral_contradice": 5,         # contradicen la Confiable (auto o manual)
    "accion_contradice_beatport": "migrar",         # 'migrar' | 'alertar'
    "accion_contradice_manual": "migrar_alertar",   # 'migrar_alertar' | 'alertar'
}

_TABLA_FB      = "biblioteca_feedback"
_TABLA_ALERTAS = "biblioteca_feedback_alertas"
_TABLA_CONFIG  = "feedback_config"
_TABLA_CONF    = "biblioteca_tracks"


def cargar_config() -> dict:
    """Lee la config de acciones automatizadas desde Supabase (fila id=1).
    Si la tabla no existe o falla, devuelve los valores por defecto."""
    cfg = dict(_CONFIG_DEFAULT)
    try:
        r = bc._get_cliente().table(_TABLA_CONFIG).select("*").eq("id", 1).limit(1).execute()
        if r.data:
            for k in _CONFIG_DEFAULT:
                if r.data[0].get(k) is not None:
                    cfg[k] = r.data[0][k]
    except Exception:
        pass
    return cfg


def guardar_config(campos: dict) -> bool:
    """Guarda cambios de config (solo las claves conocidas). Admin only (RLS)."""
    datos = {k: campos[k] for k in _CONFIG_DEFAULT if k in campos}
    if not datos:
        return False
    datos["id"] = 1
    datos["actualizado_en"] = _ahora()
    try:
        _cli().table(_TABLA_CONFIG).upsert(datos, on_conflict="id").execute()
        return True
    except Exception as e:
        print(f"  [feedback] Error guardando config: {e}")
        return False


def _cli():
    c = bc._get_cliente()
    if c is None:
        raise RuntimeError("No hay conexión con Supabase (revisá asistente_config.json).")
    return c


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────── recibir aportes (clientes) ──────

def registrar_aporte(usuario_id: str, artista: str, titulo: str,
                     duracion_seg: float, genero: Optional[str],
                     subgenero: Optional[str] = None, bpm: Optional[float] = None,
                     camelot: Optional[str] = None, sello: Optional[str] = None) -> bool:
    """Guarda (o pisa) la propuesta manual de un usuario para un track.
    Un usuario tiene una sola propuesta vigente por track (upsert por
    usuario_id + artista_norm + titulo_norm)."""
    cli = _cli()
    art_norm, tit_norm = bc._norm(artista), bc._norm(titulo)
    if not art_norm or not tit_norm or not genero:
        return False
    fila = {
        "usuario_id": usuario_id,
        "artista_norm": art_norm, "titulo_norm": tit_norm,
        "artista": artista.strip(), "titulo": titulo.strip(),
        "duracion_seg": round(duracion_seg, 2) if duracion_seg else None,
        "genero": genero, "subgenero": subgenero,
        "bpm": round(bpm, 2) if bpm else None,
        "camelot": camelot, "sello": sello,
        "estado": "pendiente", "actualizado_en": _ahora(),
    }
    try:
        cli.table(_TABLA_FB).upsert(fila, on_conflict="usuario_id,artista_norm,titulo_norm").execute()
        return True
    except Exception as e:
        print(f"  [feedback] Error guardando aporte: {e}")
        return False


# ──────────────────────────────────────────── helpers de lectura ──────────────

def _traer_pendientes() -> list[dict]:
    """Todos los aportes en estado 'pendiente' (paginado). Admin only (RLS)."""
    cli = _cli()
    out, off = [], 0
    while True:
        r = cli.table(_TABLA_FB).select("*").eq("estado", "pendiente").range(off, off + 999).execute()
        out += r.data or []
        if not r.data or len(r.data) < 1000:
            break
        off += 1000
    return out


def _confiable_de(art_norm: str, tit_norm: str) -> Optional[dict]:
    """Fila actual de la Confiable para ese track, o None."""
    cli = _cli()
    r = (cli.table(_TABLA_CONF)
         .select("id,genero,subgenero,fuente")
         .eq("artista_norm", art_norm).eq("titulo_norm", tit_norm).limit(1).execute())
    return r.data[0] if r.data else None


def _agrupar(pendientes: list[dict]) -> dict:
    """Agrupa aportes por track (artista_norm, titulo_norm)."""
    grupos: dict[tuple, list] = {}
    for a in pendientes:
        grupos.setdefault((a["artista_norm"], a["titulo_norm"]), []).append(a)
    return grupos


def _mas_comun(valores) -> Optional[str]:
    vals = [v for v in valores if v]
    return Counter(vals).most_common(1)[0][0] if vals else None


def _decidir(aportes: list[dict], conf: Optional[dict], cfg: dict) -> Optional[dict]:
    """Decide qué hacer con un grupo de aportes de un track.

    Devuelve None si no hay consenso todavía, o un dict con:
      genero, subgenero, cantidad, accion ('migrar' | 'alertar'),
      contradice_manual (bool).
    'migrar'  = hay que promoverlo a la Confiable.
    'alertar' = hay consenso para contradecir, pero la config dice avisar y
                que el admin decida (no migrar solo).
    Cada aporte es de un usuario distinto (UNIQUE por usuario/track)."""
    por_gsg = Counter((a.get("genero"), a.get("subgenero")) for a in aportes)
    por_g   = Counter(a.get("genero") for a in aportes)

    if conf is None:
        # Track NUEVO: siempre migra (agregar conocimiento nuevo no pisa nada).
        for (g, sg), n in por_gsg.most_common():
            if g and n >= cfg["umbral_genero_subgenero"]:
                return {"genero": g, "subgenero": sg, "cantidad": n,
                        "accion": "migrar", "contradice_manual": False}
        for g, n in por_g.most_common():
            if g and n >= cfg["umbral_solo_genero"]:
                sg = _mas_comun([a.get("subgenero") for a in aportes if a.get("genero") == g])
                return {"genero": g, "subgenero": sg, "cantidad": n,
                        "accion": "migrar", "contradice_manual": False}
        return None

    # Track YA en la Confiable: solo cuentan las CONTRADICCIONES (género distinto)
    # con >= umbral_contradice usuarios. La acción depende de la config.
    conf_g = (conf.get("genero") or "").strip().lower()
    es_manual = (conf.get("fuente") == "manual")
    for g, n in por_g.most_common():
        if g and g.strip().lower() != conf_g and n >= cfg["umbral_contradice"]:
            sg = _mas_comun([a.get("subgenero") for a in aportes if a.get("genero") == g])
            if es_manual:
                accion = "migrar" if cfg["accion_contradice_manual"] == "migrar_alertar" else "alertar"
            else:
                accion = "migrar" if cfg["accion_contradice_beatport"] == "migrar" else "alertar"
            return {"genero": g, "subgenero": sg, "cantidad": n,
                    "accion": accion, "contradice_manual": es_manual}
    return None


# ──────────────────────────────────────────── el motor ────────────────────────

def _alerta_abierta_existe(art_norm: str, tit_norm: str) -> bool:
    """¿Ya hay una alerta sin ver para ese track? (para no duplicar alertas en
    cada corrida cuando la acción es 'solo alertar')."""
    try:
        r = (_cli().table(_TABLA_ALERTAS).select("id")
             .eq("artista_norm", art_norm).eq("titulo_norm", tit_norm)
             .eq("vista", False).limit(1).execute())
        return bool(r.data)
    except Exception:
        return False


def _crear_alerta(cli, art_norm, tit_norm, rep, conf, decision, motivo):
    if _alerta_abierta_existe(art_norm, tit_norm):
        return
    try:
        cli.table(_TABLA_ALERTAS).insert({
            "artista_norm": art_norm, "titulo_norm": tit_norm,
            "artista": rep.get("artista"), "titulo": rep.get("titulo"),
            "genero_anterior": (conf or {}).get("genero"),
            "subgenero_anterior": (conf or {}).get("subgenero"),
            "genero_nuevo": decision["genero"], "subgenero_nuevo": decision["subgenero"],
            "cantidad_usuarios": decision["cantidad"], "motivo": motivo,
        }).execute()
    except Exception as e:
        print(f"  [feedback] Error creando alerta: {e}")


def evaluar(dry_run: bool = False) -> dict:
    """Corre el motor de consenso sobre todos los aportes pendientes, según la
    config de `feedback_config`.

    Migra a la Confiable lo que alcanzó consenso, genera alertas (cuando pisa un
    dato manual, o cuando la config dice 'solo alertar'), y marca resueltos los
    aportes migrados. Con dry_run=True solo calcula qué haría, sin escribir.
    Devuelve {'migrados':[...], 'alertas':[...], 'revisados':n}."""
    cli = _cli()
    cfg = cargar_config()
    grupos = _agrupar(_traer_pendientes())
    migrados, alertas = [], []

    for (art_norm, tit_norm), aportes in grupos.items():
        conf = _confiable_de(art_norm, tit_norm)
        decision = _decidir(aportes, conf, cfg)
        if not decision:
            continue

        rep = aportes[0]  # representante para artista/titulo/duracion
        info = {
            "artista": rep.get("artista"), "titulo": rep.get("titulo"),
            "genero": decision["genero"], "subgenero": decision["subgenero"],
            "cantidad_usuarios": decision["cantidad"], "accion": decision["accion"],
            "contradice_manual": decision["contradice_manual"],
            "genero_anterior": (conf or {}).get("genero"),
        }

        # Caso "solo alertar": hay consenso para contradecir, pero la config pide
        # que decidas vos. No migra ni resuelve los aportes; deja una alerta.
        if decision["accion"] == "alertar":
            alertas.append(info)
            if not dry_run:
                motivo = "contradice_manual" if decision["contradice_manual"] else "contradice_beatport"
                _crear_alerta(cli, art_norm, tit_norm, rep, conf, decision, motivo)
            continue

        # Caso "migrar".
        migrados.append(info)
        if decision["contradice_manual"]:
            alertas.append(info)
        if dry_run:
            continue

        # 1) upsert a la Confiable (pisa lo que haya, incluido manual: es la decisión del consenso)
        fila = {
            "artista_norm": art_norm, "titulo_norm": tit_norm,
            "artista": rep.get("artista"), "titulo": rep.get("titulo"),
            "duracion_seg": rep.get("duracion_seg"),
            "genero": decision["genero"], "subgenero": decision["subgenero"],
            "bpm": _mas_comun([a.get("bpm") for a in aportes]),
            "camelot": _mas_comun([a.get("camelot") for a in aportes]),
            "sello": _mas_comun([a.get("sello") for a in aportes]),
            "fuente": "feedback", "confirmado": True, "actualizado_en": _ahora(),
        }
        try:
            cli.table(_TABLA_CONF).upsert(fila, on_conflict="artista_norm,titulo_norm").execute()
        except Exception as e:
            print(f"  [feedback] Error migrando {art_norm}-{tit_norm}: {e}")
            continue

        # 2) alerta si pisó un dato manual tuyo
        if decision["contradice_manual"]:
            _crear_alerta(cli, art_norm, tit_norm, rep, conf, decision, "contradice_manual")

        # 3) marcar como resueltos los aportes cuyo género quedó reflejado en la Confiable
        ids_resueltos = [a["id"] for a in aportes
                         if (a.get("genero") or "").strip().lower() == decision["genero"].strip().lower()]
        if ids_resueltos:
            try:
                cli.table(_TABLA_FB).update({"estado": "migrado", "actualizado_en": _ahora()}) \
                   .in_("id", ids_resueltos).execute()
            except Exception as e:
                print(f"  [feedback] Error marcando resueltos: {e}")

    return {"migrados": migrados, "alertas": alertas, "revisados": len(grupos)}


# ──────────────────────────────────────────── vistas para el panel ────────────

def resumen_pendientes(limite_tracks: int = 200) -> list[dict]:
    """Para el panel: agrupa los aportes pendientes por track, con el conteo de
    propuestas, el dato actual de la Confiable y qué acción sugiere el motor."""
    cfg = cargar_config()
    grupos = _agrupar(_traer_pendientes())
    salida = []
    for (art_norm, tit_norm), aportes in list(grupos.items())[:limite_tracks]:
        conf = _confiable_de(art_norm, tit_norm)
        decision = _decidir(aportes, conf, cfg)
        propuestas = [{"genero": g, "subgenero": sg, "usuarios": n}
                      for (g, sg), n in Counter((a.get("genero"), a.get("subgenero")) for a in aportes).most_common()]
        salida.append({
            "artista_norm": art_norm, "titulo_norm": tit_norm,
            "artista": aportes[0].get("artista"), "titulo": aportes[0].get("titulo"),
            "total_usuarios": len(aportes),
            "propuestas": propuestas,
            "confiable": conf,   # None si es track nuevo
            "listo_para_migrar": decision is not None,
            "sugerencia": decision,
        })
    # primero los que ya están listos para migrar
    salida.sort(key=lambda x: (not x["listo_para_migrar"], -x["total_usuarios"]))
    return salida


def aprobar(art_norm: str, tit_norm: str, genero: str, subgenero: Optional[str] = None) -> bool:
    """Migración manual desde el panel: el admin aprueba una propuesta y la
    fija en la Confiable como 'manual' (su verdad, protegida)."""
    cli = _cli()
    aportes = (cli.table(_TABLA_FB).select("*").eq("estado", "pendiente")
               .eq("artista_norm", art_norm).eq("titulo_norm", tit_norm).execute().data or [])
    rep = aportes[0] if aportes else {}
    fila = {
        "artista_norm": art_norm, "titulo_norm": tit_norm,
        "artista": rep.get("artista"), "titulo": rep.get("titulo"),
        "duracion_seg": rep.get("duracion_seg"),
        "genero": genero, "subgenero": subgenero,
        "fuente": "manual", "confirmado": True, "actualizado_en": _ahora(),
    }
    try:
        cli.table(_TABLA_CONF).upsert(fila, on_conflict="artista_norm,titulo_norm").execute()
        cli.table(_TABLA_FB).update({"estado": "migrado", "actualizado_en": _ahora()}) \
           .eq("artista_norm", art_norm).eq("titulo_norm", tit_norm).execute()
        return True
    except Exception as e:
        print(f"  [feedback] Error aprobando: {e}")
        return False


def descartar(art_norm: str, tit_norm: str) -> bool:
    """Marca todos los aportes pendientes de un track como 'descartado' (el
    admin decidió que esa propuesta de la comunidad no va)."""
    cli = _cli()
    try:
        cli.table(_TABLA_FB).update({"estado": "descartado", "actualizado_en": _ahora()}) \
           .eq("estado", "pendiente").eq("artista_norm", art_norm).eq("titulo_norm", tit_norm).execute()
        return True
    except Exception as e:
        print(f"  [feedback] Error descartando: {e}")
        return False


def listar_alertas(solo_no_vistas: bool = True) -> list[dict]:
    cli = _cli()
    q = cli.table(_TABLA_ALERTAS).select("*").order("creado_en", desc=True).limit(200)
    if solo_no_vistas:
        q = q.eq("vista", False)
    try:
        return q.execute().data or []
    except Exception:
        return []


def marcar_alerta_vista(alerta_id: int) -> bool:
    cli = _cli()
    try:
        cli.table(_TABLA_ALERTAS).update({"vista": True}).eq("id", alerta_id).execute()
        return True
    except Exception:
        return False
