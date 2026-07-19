"""Búsqueda de previews en YouTube para los tracks de los charts.

Copia self-contenida de `asistente_dj/youtube_preview.py` (el repo de
escritorio no está disponible en el runtime de este backend — build/deploy
separado, ver `Dockerfile`). Mantener ambos en sync a mano si cambia la
lógica de matching.

Sin API key — usa yt-dlp en modo búsqueda (`ytsearchN:...`). Los charts de
Beatport casi siempre traen la versión "Extended Mix"; YouTube en cambio
suele tener la versión corta/radio. Por eso esta búsqueda prioriza
encontrar la extended, y si no aparece una coincidencia razonable, cae
automáticamente a la versión corta en vez de no devolver nada.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

_N_RESULTADOS = 10
_UMBRAL_MINIMO = 1.5   # score mínimo para aceptar un resultado como válido


@dataclass
class ResultadoYoutube:
    video_id: str
    titulo: str
    duracion_seg: Optional[float]
    es_extended: bool   # True si el video encontrado es la versión extended


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _score(titulo_video_norm: str, artistas: list[str], titulo: str, quiere_extended: bool) -> float:
    score = 0.0
    tit_norm = _norm(titulo)
    if tit_norm and tit_norm in titulo_video_norm:
        score += 3.0
    elif tit_norm:
        palabras = tit_norm.split()
        score += 3.0 * sum(1 for p in palabras if p in titulo_video_norm) / len(palabras)
    if any(_norm(a) in titulo_video_norm for a in artistas if a):
        score += 1.5
    es_extended_video = "extended" in titulo_video_norm
    if quiere_extended and es_extended_video:
        score += 2.0
    elif not quiere_extended and not es_extended_video:
        score += 0.5
    return score


def _buscar_crudo(query: str) -> list[dict]:
    import yt_dlp
    opts = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "extract_flat": "in_playlist", "default_search": f"ytsearch{_N_RESULTADOS}",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
    return info.get("entries") or []


def buscar_candidatos(
    artistas: list[str], titulo: str, mix_name: Optional[str] = None, n: int = 6
) -> list[ResultadoYoutube]:
    """Busca hasta `n` candidatos en YouTube para `titulo` de `artistas`,
    ordenados de mejor a peor match.

    Si `mix_name` indica Extended Mix, prioriza encontrar esa versión; si no
    hay una coincidencia razonable, cae a la versión corta/original. Devolver
    varios candidatos (no solo el mejor) permite que el cliente pruebe el
    siguiente si el primero resulta no disponible para embeber (restricción
    del dueño del video en YouTube, ajena a esta búsqueda).
    Nunca lanza excepción: devuelve [] si yt-dlp no está instalado, no hay
    red, o no se encuentra nada con confianza suficiente. Es SINCRÓNICA
    (yt-dlp bloquea) — quien la llame desde código async debe correrla en
    threadpool (`asyncio.to_thread`), nunca directo en el event loop."""
    if not titulo:
        return []
    quiere_extended = bool(mix_name) and "extended" in mix_name.lower()
    artistas_str = " ".join((artistas or [])[:2])

    consultas = []
    if quiere_extended:
        consultas.append(f"{artistas_str} {titulo} extended mix")
    consultas.append(f"{artistas_str} {titulo}")

    candidatos: dict[str, tuple[float, dict, bool]] = {}
    try:
        for query in consultas:
            mejor_de_esta_consulta = 0.0
            for e in _buscar_crudo(query):
                if not e or not e.get("id"):
                    continue
                tit_norm = _norm(e.get("title") or "")
                s = _score(tit_norm, artistas or [], titulo, quiere_extended)
                es_ext = "extended" in tit_norm
                mejor_de_esta_consulta = max(mejor_de_esta_consulta, s)
                previo = candidatos.get(e["id"])
                if previo is None or s > previo[0]:
                    candidatos[e["id"]] = (s, e, es_ext)
            if quiere_extended and mejor_de_esta_consulta >= 4.0:
                break  # ya encontramos una extended sólida, no hace falta el fallback
    except Exception:
        return []

    ordenados = sorted(candidatos.values(), key=lambda t: t[0], reverse=True)
    resultado = [
        ResultadoYoutube(video_id=e["id"], titulo=e.get("title") or titulo,
                          duracion_seg=e.get("duration"), es_extended=es_ext)
        for s, e, es_ext in ordenados if s >= _UMBRAL_MINIMO
    ]
    return resultado[:n]
