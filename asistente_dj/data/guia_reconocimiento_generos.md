# Guía de parámetros para reconocimiento de géneros de música electrónica

**Raíz taxonómica:** Beatport (catálogo electrónico ~36 géneros, estado 2025‑2026)
**Acompaña a:** `generos_electronicos_beatport.json`
**Uso:** referencia para un sistema de reconocimiento de géneros/subgéneros.

---

## 1. Idea central: el ritmo manda, no la armonía

El hallazgo más importante de toda la investigación, repetido por fuentes de producción y por la literatura de clasificación automática, es este: **el patrón de batería identifica el género mejor que la melodía o la armonía.** Dos temas con la misma progresión de acordes a 128 BPM pueden ser house, techno o trance según lo que haga el kick y dónde caigan snare e hi-hats. Los acordes son secundarios; la batería te dice qué estás escuchando en los primeros dos compases.

Para un clasificador esto implica priorizar features rítmicos y de bajo por encima de los armónicos.

## 2. El tempo es necesario pero NO suficiente

El BPM define el "carril", pero hay solapamiento masivo. A 140 BPM conviven dubstep, techno, trance, breakbeat y trap. Lo que los separa es el patrón rítmico y el diseño del bajo, no el número.

El gran obstáculo es el **half-time / double-time**: un tema a 140 BPM puede *percibirse* a 70 (dubstep, trap, parte del DnB) porque el snare cae a la mitad de la velocidad aparente, aunque hi-hats y demás percusión sigan al BPM completo. En el DAW el proyecto sigue a 140; el feel lento viene de dónde caen kick y snare. **Tu detector de tempo tiene que resolver explícitamente la ambigüedad half-time**, o vas a confundir dubstep (140) con house (~125) por estimación de tempo, y DnB (174) con su mitad (87).

## 3. Jerarquía de decisión recomendada

En vez de un único clasificador plano de 35 clases, conviene un enfoque jerárquico (primero familia, después subgénero). Orden sugerido de aplicación de parámetros:

1. **Tempo (BPM)** + resolución de half-time → acota a un grupo de candidatos.
2. **Base rítmica**: four-on-the-floor vs breakbeat vs half-time vs 2-step/shuffle. Es el discriminador más potente dentro de un mismo BPM.
3. **Perfil de graves y diseño de sub-bass**: energía en banda <120 Hz, sub continuo vs wobble vs reese vs rolling. Separa la familia bass (dubstep/DnB/bass house) del resto.
4. **Brillo espectral** (centroide, rolloff): separa lo brillante/agresivo (hard techno, trance, hardstyle) de lo cálido/oscuro (deep house, organic, deep dubstep).
5. **Armonía y tonalidad** (chroma, tendencia menor/mayor, densidad de acordes): desempate fino, menos fiable.
6. **Features de alto nivel** (danceability, energy, valence, instrumentalness, acousticness): para distinguir familias completas.

## 4. Features de audio a extraer

Set estándar de la literatura de MIR (todo extraíble con **librosa** en Python o **Essentia**):

| Categoría | Features | Para qué sirven |
|---|---|---|
| Rítmicos | tempo (multi-algoritmo), detección half-time, beat strength por banda, danceability (DFA), swing ratio | carril de tempo, patrón de batería, feel |
| Espectrales | spectral_centroid, spectral_rolloff, spectral_bandwidth, spectral_flux, spectral_entropy, zero_crossing_rate | brillo/timbre, distorsión, agresividad |
| Tímbricos | MFCC (1–13) + deltas, spectral_contrast | "huella" tímbrica del género |
| Armónicos | chroma_stft, tonnetz, tonalidad/escala (Camelot), key_strength | tendencia menor/mayor, densidad armónica |
| Energía | RMS total, RMS banda grave (<120 Hz), RMS banda aguda (>6 kHz) | dominancia de sub-bass, brillo |

El combo histórico que mejor funciona en datasets tipo GTZAN es **chroma + MFCC + centroide + rolloff + tempo + ZCR**. El centroide espectral indica el "centro de masa" de la frecuencia (brillo): géneros con más energía en agudos (hard techno, trance) dan centroide alto; los de foco grave (deep dubstep, organic) lo dan bajo.

## 5. Advertencia importante para el modelo

La taxonomía comercial de Beatport está, en términos acústicos, **sobre-especificada**. Investigación reciente encuentra que ~35 subgéneros prescritos convergen a ~23 clusters naturales: hay pares que el oído (y el clasificador) apenas distinguen por audio:

- **Tech House ↔ Minimal / Deep Tech** (casi idéntico BPM y groove)
- **Techno Peak Time ↔ Hard Techno** (diferencia gradual de tempo/distorsión)
- **Deep House ↔ Organic House** (separados sobre todo por instrumentación)
- **Trance Main Floor ↔ Progressive House** (frontera difusa)
- **House ↔ Funky House ↔ Jackin House** (matices de groove/sampling)

Recomendaciones:
- Aceptá **etiquetas blandas/probabilísticas** (top-3) en lugar de una única clase dura.
- Para los pares confusos, considerá fusionarlos en una clase "familia" si tu caso de uso lo permite.
- Cada género en el JSON trae un campo `confundible_con`: úsalo para construir la matriz de confusión esperada y para ponderar los límites de decisión.

## 6. Notas sobre el JSON adjunto

Cada género incluye: `bpm` (min/max/típico), `base_ritmica`, `feel`, `patron_kick`, `tonalidad`, y escalas cualitativas **1–5** orientativas para `sub_bass`, `brillo_espectral`, `energia` y `danceability`. Además `rasgos_distintivos`, `confundible_con` y `subgeneros_beatport`.

**Importante sobre las escalas 1–5:** son heurísticas de *feature engineering* derivadas de las descripciones de las fuentes, **no** son medias medidas sobre un dataset. Sirven para inicializar reglas o como priors; calibralas contra tu propia colección etiquetada antes de confiar en ellas.

### Casos especiales a tratar aparte
- **DJ Tools**: no es un género musical (acapellas, loops, FX). Excluilo del entrenamiento o tratalo como clase separada "no-musical".
- **Ambient / Experimental**: a menudo *sin tempo detectable* (beatless). Tu pipeline tiene que tolerar `tempo = null` y clasificar por textura/MFCC.
- **Dance/Pop, Mainstage, Electronica**: categorías amplias con alta varianza interna; esperá menor precisión en ellas.
- **Open-format** (Hip-Hop, R&B, Pop, Latin, Caribbean, African): Beatport los agregó en septiembre 2025 en una sección aparte y quedan fuera del Global Top 100 electrónico. Amapiano, Afro House y Brazilian Funk son cruces ya incluidos en el JSON; el resto del open-format quedó fuera por no ser electrónica de pista.

## 7. Fuentes

Taxonomía: lista oficial de géneros de Beatport y comunicados de 2025 (nuevos géneros Ambient/Experimental y Downtempo standalone; sección open-format; Brazilian Funk con espacio propio). Rangos de BPM y patrones rítmicos: guías de Ableton, DJ.Studio, ZIPDJ, chosic (datos de tempo sobre catálogo de Spotify), y guías de producción especializadas. Features de audio y solapamiento de subgéneros: literatura de clasificación automática de géneros (GTZAN, Essentia, estudios de taxonomía EDM).

Los rangos de BPM son de **consenso entre múltiples fuentes**; las fronteras exactas varían un poco según quién las publique. Tomalos como punto de partida, no como ley.
