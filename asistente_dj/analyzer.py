"""Análisis de audio con ffmpeg + numpy (sin Essentia).

Calcula BPM, key (con notación Camelot) y energía (1-10).
Decodifica cualquier formato vía ffmpeg, así que soporta mp3/wav/flac/m4a/aiff.

Requisitos en el sistema:
  - numpy            (pip install numpy)
  - ffmpeg en el PATH (https://ffmpeg.org/download.html)
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

import numpy as np

SR = 22050  # samplerate de análisis


@dataclass
class AudioFeatures:
    bpm: float | None = None
    key: str = ""          # ej. "A min"
    camelot: str = ""      # ej. "8A"
    energia: int | None = None       # 1..10 (se asigna por percentiles luego)
    energia_raw: float | None = None  # valor crudo de intensidad
    # rasgos acústicos individuales (inputs del aprendizaje de energía)
    f_loud: float | None = None
    f_bright: float | None = None
    f_low: float | None = None
    f_busy: float | None = None
    ok: bool = False


def decode(path: str, sr: int = SR, inicio: float | None = None,
           dur: float | None = None):
    """Devuelve audio mono float32 en [-1,1] usando ffmpeg, o None si falla.

    Si se pasan inicio/dur, decodifica solo ese tramo (en segundos) — mucho
    más rápido que el track completo.
    """
    cmd = ["ffmpeg", "-v", "quiet"]
    if inicio is not None:
        cmd += ["-ss", str(inicio)]            # seek de entrada (rápido)
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    try:
        raw = subprocess.run(cmd, capture_output=True, timeout=120).stdout
        if not raw:
            return None
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return y if y.size > sr else None  # al menos 1 segundo
    except Exception:
        return None


# Ventana por defecto para el análisis: del segundo 45 al 120 (el "cuerpo"
# del track, donde el groove es estable). Mucho más rápido que el track entero.
VENTANA_INICIO = 45.0
VENTANA_DUR = 75.0


def pico_intensidad(path, sr=11025, ventana=4.0, hop=2.0):
    """Devuelve el segundo donde el track es más intenso (mayor energía RMS).
    Decodifica todo el track a baja resolución (rápido) y busca el pico.
    Sirve para reproducir el momento más fuerte durante la calibración."""
    y = decode(path, sr=sr)
    if y is None or len(y) < sr * 8:
        return VENTANA_INICIO
    w, h = int(ventana * sr), int(hop * sr)
    mejor_e, mejor_off = -1.0, 0
    i = 0
    while i + w <= len(y):
        e = float(np.mean(y[i:i + w] ** 2))
        if e > mejor_e:
            mejor_e, mejor_off = e, i
        i += h
    pico = mejor_off / sr
    return max(0.0, pico - 4.0)   # arranca un poco antes para entrar al pico


# ----------------------------------------------------------------- STFT
def _stft_mag(y, n_fft=2048, hop=512):
    win = np.hanning(n_fft).astype(np.float32)
    n = 1 + (len(y) - n_fft) // hop
    if n < 2:
        return np.zeros((n_fft // 2 + 1, 1))
    frames = np.lib.stride_tricks.as_strided(
        y, shape=(n, n_fft),
        strides=(y.strides[0] * hop, y.strides[0])).copy()
    frames *= win
    spec = np.fft.rfft(frames, axis=1)
    return np.abs(spec).T  # (freqs, frames)


# ----------------------------------------------------------------- BPM
def estimate_bpm(y, sr=SR):
    hop = 512
    mag = _stft_mag(y, 2048, hop)
    flux = np.diff(mag, axis=1)          # flujo espectral = onset envelope
    flux[flux < 0] = 0
    onset = flux.sum(axis=0)
    if onset.size < 4 or onset.max() == 0:
        return None
    onset = onset - onset.mean()
    corr = np.correlate(onset, onset, mode="full")[onset.size - 1:]
    fps = sr / hop
    bpm_min, bpm_max = 70, 200
    lag_min = int(fps * 60 / bpm_max)
    lag_max = min(int(fps * 60 / bpm_min), corr.size - 1)
    if lag_max <= lag_min:
        return None
    seg = corr[lag_min:lag_max]
    k = int(np.argmax(seg))
    best_lag = lag_min + k
    # interpolación parabólica para precisión sub-muestra
    if 0 < k < len(seg) - 1:
        a, b, c = seg[k - 1], seg[k], seg[k + 1]
        denom = (a - 2 * b + c)
        if denom != 0:
            best_lag = best_lag + 0.5 * (a - c) / denom
    bpm = 60.0 * fps / best_lag
    while bpm < 110:   # plegar al rango típico DJ
        bpm *= 2
    while bpm > 180:
        bpm /= 2
    return round(float(bpm), 1)


# ----------------------------------------------------------------- KEY
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
_CAMELOT = {
    ("C", "maj"): "8B", ("G", "maj"): "9B", ("D", "maj"): "10B", ("A", "maj"): "11B",
    ("E", "maj"): "12B", ("B", "maj"): "1B", ("F#", "maj"): "2B", ("C#", "maj"): "3B",
    ("G#", "maj"): "4B", ("D#", "maj"): "5B", ("A#", "maj"): "6B", ("F", "maj"): "7B",
    ("A", "min"): "8A", ("E", "min"): "9A", ("B", "min"): "10A", ("F#", "min"): "11A",
    ("C#", "min"): "12A", ("G#", "min"): "1A", ("D#", "min"): "2A", ("A#", "min"): "3A",
    ("F", "min"): "4A", ("C", "min"): "5A", ("G", "min"): "6A", ("D", "min"): "7A",
}


def estimate_key(y, sr=SR):
    mag = _stft_mag(y, 4096, 2048)
    freqs = np.fft.rfftfreq(4096, 1.0 / sr)
    chroma = np.zeros(12)
    for i, f in enumerate(freqs):
        if f < 55 or f > 2000:
            continue
        midi = 69 + 12 * np.log2(f / 440.0)
        pc = int(round(midi)) % 12
        chroma[pc] += mag[i].sum()
    if chroma.sum() == 0:
        return "", ""
    chroma /= chroma.sum()
    best = None
    for shift in range(12):
        maj = np.corrcoef(np.roll(_MAJ, shift), chroma)[0, 1]
        minr = np.corrcoef(np.roll(_MIN, shift), chroma)[0, 1]
        for mode, score in (("maj", maj), ("min", minr)):
            if best is None or score > best[0]:
                best = (score, _NOTES[shift], mode)
    _, note, mode = best
    label = f"{note} {'maj' if mode == 'maj' else 'min'}"
    return label, _CAMELOT.get((note, mode), "")


# ----------------------------------------------------------------- ENERGY
def estimate_energy_raw(y, sr=SR):
    """Valor CRUDO de intensidad (0-1 aprox). Combina cuatro factores, cada uno
    normalizado a una escala comparable para que ninguno domine:
      - volumen (RMS)             -> qué tan fuerte/comprimido
      - brillo (centroide)        -> presencia de agudos/hats
      - graves (kick/bajo)        -> peso de la parte baja
      - densidad rítmica (onsets) -> qué tan 'movido'
    La escala 1-10 se asigna después por percentiles sobre toda la colección,
    así no satura y refleja la energía RELATIVA dentro de tu biblioteca."""
    hop = 512
    mag = _stft_mag(y, 2048, hop)
    freqs = np.fft.rfftfreq(2048, 1.0 / sr)
    spec = mag.mean(axis=1)
    total = spec.sum() + 1e-9

    f = features_acusticas_de_mag(mag, freqs, spec, total, y)
    # La energía DJ es más "drive" (kick + densidad rítmica) que brillo/volumen.
    return (0.20 * f["loud"] + 0.05 * f["bright"]
            + 0.35 * f["low"] + 0.40 * f["busy"])


def features_acusticas(y, sr=SR):
    """Devuelve los 4 rasgos acústicos individuales (0-1) que alimentan el
    cálculo de energía y el aprendizaje: loud, bright, low, busy."""
    mag = _stft_mag(y, 2048, 512)
    freqs = np.fft.rfftfreq(2048, 1.0 / sr)
    spec = mag.mean(axis=1)
    total = spec.sum() + 1e-9
    return features_acusticas_de_mag(mag, freqs, spec, total, y)


def features_acusticas_de_mag(mag, freqs, spec, total, y):
    rms = float(np.sqrt(np.mean(y ** 2)))
    loud = float(np.clip(rms * 4, 0, 1))
    centroid = float((freqs * spec).sum() / total)
    bright = float(np.clip(centroid / 5000.0, 0, 1))
    low = float(np.clip(spec[freqs < 200].sum() / total, 0, 1))
    flux = np.diff(mag, axis=1)
    flux[flux < 0] = 0
    frame_sum = mag[:, :-1].sum(axis=0) + 1e-9
    busy = float(np.clip(np.mean(flux.sum(axis=0) / frame_sum), 0, 1))
    return {"loud": loud, "bright": bright, "low": low, "busy": busy}


def estimate_energy(y, sr=SR):
    """Compatibilidad: estimación absoluta rápida (se prefiere energia_raw)."""
    return estimate_energy_raw(y, sr)


# --- Energía combinada: acústica + tonalidad + BPM (idea de Brian) ---
# La acústica domina fuerte; la tonalidad complementa; el BPM influye poco
# (es el menos confiable hasta importar Rekordbox). Son pesos relativos:
# el ranking final por percentiles sólo usa sus proporciones.
PESO_ACUSTICA = 0.90
PESO_MODO = 0.10
PESO_BPM = 0.10


def factor_bpm(bpm):
    """0-1 según el BPM: más rápido = más energía. Neutral (0.5) si no hay dato."""
    try:
        b = float(str(bpm).replace(",", "."))
    except Exception:
        return 0.5
    if b <= 0:
        return 0.5
    # rango típico de música electrónica de club: ~118 a ~145 BPM
    return min(max((b - 118.0) / (145.0 - 118.0), 0.0), 1.0)


def factor_modo(camelot, key):
    """Mayor (feliz) = más energía; menor (triste/oscuro) = menos.
    Camelot: 'B' = mayor, 'A' = menor. Neutral si se desconoce."""
    c = (camelot or "").strip().upper()
    if c.endswith("B"):
        return 0.7
    if c.endswith("A"):
        return 0.3
    k = (key or "").lower()
    if "maj" in k:
        return 0.7
    if "min" in k or k.endswith("m"):
        return 0.3
    return 0.5


def energia_combinada(acustica, bpm, camelot, key):
    """Combina la energía acústica (0-1) con BPM y tonalidad en un valor crudo."""
    a = acustica if acustica is not None else 0.0
    return (PESO_ACUSTICA * a
            + PESO_BPM * factor_bpm(bpm)
            + PESO_MODO * factor_modo(camelot, key))


def energia_por_percentiles(valores):
    """Dada una lista de energia_raw, devuelve dict idx->energia(1-10) por ranking."""
    pares = [(i, v) for i, v in enumerate(valores) if v is not None]
    if not pares:
        return {}
    pares.sort(key=lambda p: p[1])
    n = len(pares)
    out = {}
    for rank, (i, _v) in enumerate(pares):
        out[i] = 1 + int(round(9 * rank / max(n - 1, 1)))
    return out


def analyze(path: str, completo: bool = False) -> AudioFeatures:
    """Analiza un track. Por defecto usa una ventana de ~75s (rápido);
    con completo=True decodifica todo el archivo."""
    f = AudioFeatures()
    if completo:
        y = decode(path)
    else:
        y = decode(path, inicio=VENTANA_INICIO, dur=VENTANA_DUR)
        if y is None:                       # track corto o seek falló: probar entero
            y = decode(path)
    if y is None:
        return f
    try:
        f.bpm = estimate_bpm(y)
        f.key, f.camelot = estimate_key(y)
        feats = features_acusticas(y)
        f.f_loud, f.f_bright = feats["loud"], feats["bright"]
        f.f_low, f.f_busy = feats["low"], feats["busy"]
        f.energia_raw = (0.20 * feats["loud"] + 0.05 * feats["bright"]
                         + 0.35 * feats["low"] + 0.40 * feats["busy"])
        f.ok = True
    except Exception:
        pass
    return f


def compute_waveform(path: str, n_cols: int = 500) -> str | None:
    """Calcula la waveform coloreada tipo Beatport para el track completo.

    Decodifica el audio a baja resolución (11025 Hz), divide en n_cols segmentos
    y calcula amplitud + color (bajo=azul, medio=verde, alto=naranja) por segmento.
    Devuelve un JSON comprimido con base64+zlib, o None si falla.
    """
    import base64, json, zlib

    SR_WF = 11025
    y = decode(path, sr=SR_WF)
    if y is None or len(y) < SR_WF:
        return None

    seg_len = max(len(y) // n_cols, 1)
    freqs = np.fft.rfftfreq(seg_len, d=1.0 / SR_WF)
    win = np.hanning(seg_len).astype(np.float32)

    peaks  = np.zeros(n_cols, dtype=np.float32)
    colors = np.zeros((n_cols, 3), dtype=np.uint8)

    for i in range(n_cols):
        seg = y[i * seg_len: (i + 1) * seg_len]
        if len(seg) == 0:
            continue
        if len(seg) < seg_len:
            seg = np.pad(seg, (0, seg_len - len(seg)))
        peaks[i] = float(np.max(np.abs(seg)))
        fft = np.abs(np.fft.rfft(seg * win))
        low_e = float(np.sum(fft[freqs < 300]))
        mid_e = float(np.sum(fft[(freqs >= 300) & (freqs < 2000)]))
        hi_e  = float(np.sum(fft[freqs >= 2000]))
        total = low_e + mid_e + hi_e + 1e-9
        colors[i] = [
            min(int(200 * hi_e / total), 255),
            min(int(180 * mid_e / total), 255),
            min(int(80 + 175 * low_e / total), 255),
        ]

    max_peak = peaks.max()
    if max_peak > 0:
        peaks /= max_peak

    return json.dumps({
        "peaks":  base64.b64encode(zlib.compress(peaks.tobytes())).decode(),
        "colors": base64.b64encode(zlib.compress(colors.tobytes())).decode(),
        "n": n_cols,
    })


def waveform_file(path: str):
    """Worker para multiprocessing: solo calcula la waveform (sin BPM/key)."""
    return (path, compute_waveform(path))


def analyze_file(path: str):
    """Worker para multiprocessing: devuelve (path, dict de features)."""
    f = analyze(path)
    waveform = compute_waveform(path)
    return (path, {"bpm": f.bpm, "key": f.key, "camelot": f.camelot,
                   "energia_raw": f.energia_raw, "f_loud": f.f_loud,
                   "f_bright": f.f_bright, "f_low": f.f_low, "f_busy": f.f_busy,
                   "waveform_data": waveform,
                   "ok": f.ok})


# ------------------------------------------------- SUGERENCIA DE GÉNERO
# Heurística (orientativa, requiere confirmación manual). No reemplaza al
# tag: solo ayuda a ordenar tracks sin etiqueta. Delega en genre_profiles,
# que puntúa los ~30 perfiles de la taxonomía Beatport (BPM + graves/
# sub-bass + brillo espectral + densidad rítmica + energía) usando los
# rasgos acústicos ya calculados (f_low, f_bright, f_busy).
def suggest_genre(bpm, energia, f_low=None, f_bright=None, f_busy=None):
    import genre_profiles
    return genre_profiles.suggest_genre(bpm, energia, f_low, f_bright, f_busy)
