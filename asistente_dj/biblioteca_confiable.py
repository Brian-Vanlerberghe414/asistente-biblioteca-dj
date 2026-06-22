"""Lookup en la Biblioteca Confiable (Supabase) — Overcome Harmony.

Fuente prioritaria para determinar género/subgénero de un track.
Si Supabase no está configurado o no responde, retorna None y el flujo
continúa con el clasificador de tags normalmente.

Credenciales: guardadas en asistente_config.json via settings.py
  python cli.py config --supabase-url URL --supabase-key KEY
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

import settings

# supabase-py es opcional; si no está instalado el lookup se omite
try:
    from supabase import create_client, Client as _Client
    _SUPABASE_DISPONIBLE = True
except ImportError:
    _SUPABASE_DISPONIBLE = False

_TABLA = "biblioteca_tracks"
_cliente: Optional["_Client"] = None


# ──────────────────────────────────────────────────── cliente singleton ──────

def _get_cliente() -> Optional["_Client"]:
    """Cliente de Supabase. Si hay una cuenta de servicio configurada
    (`supabase_service_email`/`supabase_service_password` — ver Fase 1 del
    Módulo 3, backend multi-usuario), inicia sesión con ella: desde que se
    endurecieron las políticas RLS de `biblioteca_tracks`/`artistas_generos`
    (escritura solo para `authenticated`, ya no `anon`), escribir sin esa
    sesión falla con permission denied. Si no hay cuenta de servicio
    configurada, sigue funcionando solo para lectura (que sigue abierta)."""
    global _cliente
    if not _SUPABASE_DISPONIBLE:
        return None
    if _cliente is not None:
        return _cliente
    cfg = settings.cargar()
    url = cfg.get("supabase_url", "").strip()
    key = cfg.get("supabase_key", "").strip()
    if not url or not key:
        return None
    try:
        cliente = create_client(url, key)
        email = cfg.get("supabase_service_email", "").strip()
        password = cfg.get("supabase_service_password", "").strip()
        if email and password:
            cliente.auth.sign_in_with_password({"email": email, "password": password})
        _cliente = cliente
    except Exception as e:
        print(f"  [biblioteca] No se pudo conectar a Supabase: {e}")
        _cliente = None
    return _cliente


def esta_configurado() -> bool:
    cfg = settings.cargar()
    return bool(cfg.get("supabase_url") and cfg.get("supabase_key"))


# ──────────────────────────────────────────────────── normalización ──────────

_RE_MIX_SUFFIX = re.compile(
    r"\s*[\(\[](original mix|extended mix|club mix|radio mix|"
    r"original|extended|mix|edit|version)[\)\]]\s*$",
    flags=re.I,
)
_RE_FEAT = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s+.+$", flags=re.I)


def _norm(texto: str) -> str:
    """Minúsculas, sin acentos, sin sufijos de mix, sin feat en título."""
    if not texto:
        return ""
    s = texto.lower().strip()
    # quitar acentos
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # quitar feat. del título (los artistas colaboradores varían entre fuentes)
    s = _RE_FEAT.sub("", s)
    # quitar sufijo de mix del título
    s = _RE_MIX_SUFFIX.sub("", s)
    return s.strip()


# ──────────────────────────────────────────────────── resultado ──────────────

@dataclass
class ResultadoBiblioteca:
    genero: str
    subgenero: Optional[str]
    bpm: Optional[float] = None
    camelot: Optional[str] = None
    cover_url: Optional[str] = None


# ──────────────────────────────────────────────────── API pública ────────────

def buscar(artista: str, titulo: str,
           duracion_seg: float) -> Optional[ResultadoBiblioteca]:
    """Busca el track en Supabase por artista + título + duración (±2 s).

    Devuelve ResultadoBiblioteca si hay coincidencia confirmada, None si no.
    Nunca lanza excepción: cualquier error de red/config devuelve None.
    """
    cliente = _get_cliente()
    if cliente is None:
        return None

    art = _norm(artista)
    tit = _norm(titulo)
    if not art or not tit:
        return None

    try:
        resp = (
            cliente.table(_TABLA)
            .select("genero, subgenero, bpm, camelot, cover_url")
            .ilike("artista_norm", art)
            .ilike("titulo_norm", tit)
            .gte("duracion_seg", round(duracion_seg - 2, 2))
            .lte("duracion_seg", round(duracion_seg + 2, 2))
            .eq("confirmado", True)
            .limit(1)
            .execute()
        )
        if resp.data:
            r = resp.data[0]
            return ResultadoBiblioteca(
                genero=r["genero"],
                subgenero=r.get("subgenero"),
                bpm=r.get("bpm"),
                camelot=r.get("camelot"),
                cover_url=r.get("cover_url"),
            )
    except Exception as e:
        print(f"  [biblioteca] Error consultando Supabase: {e}")
    return None


def agregar(artista: str, titulo: str, duracion_seg: float,
            genero: Optional[str] = None, subgenero: Optional[str] = None,
            sello: Optional[str] = None, bpm: Optional[float] = None,
            camelot: Optional[str] = None, cover_url: Optional[str] = None,
            fuente: str = "manual") -> bool:
    """Agrega o actualiza un track en la Biblioteca Confiable.

    Usa upsert por artista_norm + titulo_norm: si ya existe, actualiza.
    Devuelve True si tuvo éxito.
    """
    cliente = _get_cliente()
    if cliente is None:
        if not _SUPABASE_DISPONIBLE:
            print("  [biblioteca] Instalá supabase-py: pip install supabase")
        else:
            print("  [biblioteca] Configurá las credenciales:")
            print("    python cli.py config --supabase-url URL --supabase-key KEY")
        return False

    art_norm, tit_norm = _norm(artista), _norm(titulo)
    if fuente != "manual":
        # Una corrección manual del DJ (la propia o la de otro, vía la misma
        # Biblioteca Confiable) es la verdad final — nada automático (charts,
        # scans) la puede pisar después.
        try:
            existe = (
                cliente.table(_TABLA).select("fuente")
                .eq("artista_norm", art_norm).eq("titulo_norm", tit_norm)
                .limit(1).execute()
            )
            if existe.data and existe.data[0].get("fuente") == "manual":
                return True
        except Exception:
            pass  # si falla la consulta de protección, seguimos con el upsert normal

    data = {
        "artista":      artista.strip(),
        "titulo":       titulo.strip(),
        "artista_norm": art_norm,
        "titulo_norm":  tit_norm,
        "duracion_seg": round(duracion_seg, 2),
        "genero":       genero,
        "subgenero":    subgenero,
        "sello":        sello,
        "bpm":          round(bpm, 2) if bpm else None,
        "camelot":      camelot,
        "fuente":       fuente,
        "confirmado":   True,
    }
    # cover_url se completa por separado (lookup en iTunes, ver
    # completar_caratulas) — solo se manda acá si este llamado YA la trae,
    # para no pisarla a None en cada agregar() que no sabe de carátulas.
    if cover_url:
        data["cover_url"] = cover_url
    try:
        (
            cliente.table(_TABLA)
            .upsert(data, on_conflict="artista_norm,titulo_norm")
            .execute()
        )
        return True
    except Exception as e:
        print(f"  [biblioteca] Error guardando en Supabase: {e}")
        return False


def completar_caratulas(limite: int = 50) -> dict:
    """Busca carátula (vía iTunes Search API, ver itunes_cover.py) para los
    tracks de la Biblioteca Confiable que todavía no la tienen, y la guarda
    (solo la URL, no la imagen — ver decisión de diseño en CLAUDE.md).
    Devuelve {"completadas", "sin_caratula", "revisados"}."""
    cliente = _get_cliente()
    if cliente is None:
        return {"completadas": 0, "sin_caratula": 0, "revisados": 0}

    import itunes_cover
    try:
        resp = (
            cliente.table(_TABLA)
            .select("artista_norm, titulo_norm, artista, titulo")
            .is_("cover_url", "null")
            .limit(limite)
            .execute()
        )
        filas = resp.data or []
    except Exception as e:
        print(f"  [biblioteca] Error consultando tracks sin carátula: {e}")
        return {"completadas": 0, "sin_caratula": 0, "revisados": 0}

    completadas = sin_caratula = 0
    for f in filas:
        url = itunes_cover.obtener_caratula(f["artista"], f["titulo"])
        if not url:
            sin_caratula += 1
            continue
        try:
            (
                cliente.table(_TABLA)
                .update({"cover_url": url})
                .eq("artista_norm", f["artista_norm"])
                .eq("titulo_norm", f["titulo_norm"])
                .execute()
            )
            completadas += 1
        except Exception as e:
            print(f"  [biblioteca] Error guardando carátula de "
                  f"'{f['artista']} - {f['titulo']}': {e}")
            sin_caratula += 1

    return {
        "completadas": completadas,
        "sin_caratula": sin_caratula,
        "revisados": len(filas),
    }


def listar(genero: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Lista tracks de la Biblioteca Confiable (para diagnóstico/CLI)."""
    cliente = _get_cliente()
    if cliente is None:
        return []
    try:
        q = (
            cliente.table(_TABLA)
            .select("artista, titulo, duracion_seg, genero, subgenero, fuente")
            .eq("confirmado", True)
            .order("artista")
            .limit(limit)
        )
        if genero:
            q = q.eq("genero", genero)
        return q.execute().data or []
    except Exception:
        return []


# ──────────────────────────────────────────── registro artista → género ──────
# Qué género(s)/subgénero(s) produce cada artista, derivado de los tracks que
# van pasando por la Biblioteca Confiable (charts de Beatport, imports, etc.).
# Ej.: "Vegas produce psytrance".

_TABLA_ARTISTAS = "artistas_generos"


def registrar_genero_artista(artista: str, genero: Optional[str],
                              subgenero: Optional[str] = None) -> bool:
    """Registra que `artista` produce `genero`/`subgenero`. Idempotente: no
    duplica la combinación artista+género+subgénero, solo actualiza la fecha.
    No hace nada si no hay género (no tiene sentido registrar "ninguno")."""
    if not genero:
        return False
    cliente = _get_cliente()
    if cliente is None:
        return False
    data = {
        "artista": artista.strip(),
        "artista_norm": _norm(artista),
        "genero": genero,
        "subgenero": subgenero or "",
    }
    try:
        (
            cliente.table(_TABLA_ARTISTAS)
            .upsert(data, on_conflict="artista_norm,genero,subgenero")
            .execute()
        )
        return True
    except Exception as e:
        print(f"  [biblioteca] Error registrando artista/género: {e}")
        return False


def generos_de_artista(nombre: str) -> list[dict]:
    """Géneros/subgéneros registrados para un artista (búsqueda parcial,
    sin distinguir mayúsculas/acentos)."""
    cliente = _get_cliente()
    if cliente is None:
        return []
    try:
        resp = (
            cliente.table(_TABLA_ARTISTAS)
            .select("artista, genero, subgenero")
            .ilike("artista_norm", f"%{_norm(nombre)}%")
            .execute()
        )
        return resp.data or []
    except Exception:
        return []
