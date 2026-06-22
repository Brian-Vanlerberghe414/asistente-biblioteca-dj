"""Configuración del Asistente de Biblioteca DJ.

Define el árbol de géneros de Brian, el mapeo de nombres de género
(tal como vienen en los tags / Beatport) hacia ese árbol, las extensiones
de audio soportadas y los umbrales de calidad.
"""

# ---------------------------------------------------------------------------
# Árbol de géneros — basado en la taxonomía oficial de Beatport 2024-2025
# (Género -> [Subgéneros])
# ---------------------------------------------------------------------------
GENRE_TREE = {
    # ------------------------------------------------------------------ TECHNO
    "Techno": [
        "Peak Time - Driving",      # Beatport: Techno (Peak Time/Driving)  — energético, oscuro, festival
        "Hard Techno",              # 140+ BPM, agresivo, distorsionado
        "Raw - Deep - Hypnotic",    # Beatport nueva cat. — underground, hipnótico, intelectual
        "Industrial",               # EBM, noise, dark industrial
        "Minimal - Deep Tech",      # Minimalista, stripped-down, groovy
    ],
    # ------------------------------------------------------------------- HOUSE
    "House": [
        "Progressive House",        # Melódico, buildups largos, emotional
        "Deep House",               # Soulful, jazzy, groovy, vocal samples
        "Tech House",               # Percusivo, bass-driven, club
        "Jackin House",             # Funky, Chicago, swingy
        "Bass House",               # Bass-heavy, festival, filthy
        "Afro House",               # Africano, percusivo, espiritual
        "Organic House",            # Natural sounds, downbeat, world
        "Electro House",            # Electro-influenced, synths agresivos
    ],
    # ------------------------------------------------------------------ TRANCE
    "Trance": [
        "Main Floor",               # Uplifting, comercial, anthems
        "Vocal Trance",             # Voz melódica, épico
        "Progressive Trance",       # Melódico, buildups lentos
        "Tech Trance",              # Más oscuro, techno-influenced
        "Hard Trance",              # Agresivo, 140+ BPM
        "Psy-Trance",               # 138-145 BPM, psicadélico, complejo
        "Goa",                      # Goa Trance original, espiritual
        "Raw - Deep - Hypnotic",    # Beatport nueva cat. — underground, instrumental
    ],
    # ----------------------------------------------- MELODIC HOUSE & TECHNO
    # Categoría propia de Beatport — crossover entre House y Techno melódico.
    # (sesión 2026-06-22) Eliminados "Melodic House" y "Melodic Techno" como
    # subgéneros propios de House/Techno: en la práctica eran el mismo sonido
    # y se confundían entre sí. Todo lo que antes caía en cualquiera de los
    # dos ahora es directamente "Melodic House & Techno" (sin subgénero).
    "Melodic House & Techno": [],
    # ----------------------------------------------------------------- BREAKS
    "Breaks": [
        "Breakbeat",                # Break clásico, sampleado
        "Electro Breaks",           # Electro-influenced breaks
        "UK Bass",                  # Sub-bass, grime-adjacent
        "Jungle",                   # Hardcore Jungle, amen breaks
    ],
    # -------------------------------------------------------------- DRUM & BASS
    "Drum & Bass": [
        "Liquid",                   # Melódico, rollers suaves
        "Neurofunk",                # Técnico, sci-fi, distorsionado
        "Jump Up",                  # Party, bouncy, vocal chops
        "Jungle",                   # Roots DnB, ragga
        "Dancefloor",               # Rollers, peak time DnB
        "Minimal DnB",              # Stripped-down, atmosférico
    ],
    # -------------------------------------------------------------- UK GARAGE
    "UK Garage": [
        "Speed Garage",             # Sub-bass wurlitzer, 130 BPM
        "2-Step",                   # Syncopado, UK underground
        "Bassline",                 # Sheffield Bassline House
    ],
    # ------------------------------------------------------------------ ELECTRO
    "Electro": [
        "Classic Electro",          # 808, Kraftwerk-influenced
        "Detroit Electro",          # Underground Resistance, Detroit
        "Modern Electro",           # Electro contemporáneo
    ],
    # -------------------------------------------------------------- INDIE DANCE
    "Indie Dance": [
        "Nu Disco",                 # Disco moderno, filter house
    ],
    # --------------------------------------------------------------- ELECTRONICA
    "Electronica": [
        "IDM",                      # Intelligent Dance Music — Aphex Twin, Autechre
        "Ambient Techno",           # Ambient electrónico, The Orb
        "Experimental",             # Avant-garde, no-genre
    ],
    # ------------------------------------------------------------------ AMBIENT
    "Ambient": [
        "Downtempo",                # Beats lentos, trip-hop adjacent
        "Chillout",                 # Lounge, relajado
    ],
    # --------------------------------------------------------------------- AFRO
    "Afro": [
        "Amapiano",                 # Sudáfrica, log drums, jazz
        "Afrobeats",                # Nigeria/Ghana, pop-adjacent
        "Gqom",                     # Durban, minimalista, oscuro
    ],
    # --------------------------------------------------------------- HARD DANCE
    "Hard Dance": [
        "Hardcore",                 # 160+ BPM, gabber, rave
        "Hardstyle",                # 150 BPM, kick oscuro, melódico
    ],
    # ---------------------------------------------------------------- BIG ROOM
    "Big Room": [],                 # Festival EDM, mainstage
    # --------------------------------------------------------------- FUNK/SOUL
    "Funk & Soul": [
        "Funk",
        "Soul",
        "R&B",
    ],
    # -------------------------------------------------- HIP-HOP (open format)
    "Hip-Hop": [
        "Trap",
        "Phonk",
        "Rap",
    ],
    # ---------------------------------------------------- LATIN (open format)
    "Latin": [
        "Reggaeton",
        "Dembow",
        "Brazilian Funk",
    ],
}

# Carpetas de sistema
FOLDER_INCOMING = "_Ingreso"
FOLDER_REVIEW = "_Por revisar"

# ---------------------------------------------------------------------------
# Mapeo de nombres de género → (Género, Subgénero)
# La clave YA está normalizada: minúsculas, & → and, /()-_,.|→espacio, espacios colapsados.
# Subgénero None => va a la raíz del género (igual queda clasificado).
# ---------------------------------------------------------------------------
GENRE_ALIASES = {

    # =====================================================================
    # TECHNO
    # =====================================================================

    # — genérico —
    "techno": ("Techno", None),
    "technoe": ("Techno", None),

    # — Peak Time / Driving —
    "techno peak time driving": ("Techno", "Peak Time - Driving"),
    "techno peak time driving hard": ("Techno", "Peak Time - Driving"),
    "peak time driving": ("Techno", "Peak Time - Driving"),
    "peak time": ("Techno", "Peak Time - Driving"),
    "driving techno": ("Techno", "Peak Time - Driving"),
    "dark techno": ("Techno", "Peak Time - Driving"),
    "acid techno": ("Techno", "Peak Time - Driving"),
    "rave techno": ("Techno", "Peak Time - Driving"),
    "festival techno": ("Techno", "Peak Time - Driving"),

    # — Hard Techno —
    "hard techno": ("Techno", "Hard Techno"),
    "industrial techno": ("Techno", "Hard Techno"),
    "schranz": ("Techno", "Hard Techno"),
    "terror techno": ("Techno", "Hard Techno"),
    "frenchcore": ("Techno", "Hard Techno"),

    # — Raw / Deep / Hypnotic —
    "techno raw deep hypnotic": ("Techno", "Raw - Deep - Hypnotic"),
    "raw deep hypnotic": ("Techno", "Raw - Deep - Hypnotic"),
    "raw techno": ("Techno", "Raw - Deep - Hypnotic"),
    "deep techno": ("Techno", "Raw - Deep - Hypnotic"),
    "hypnotic techno": ("Techno", "Raw - Deep - Hypnotic"),
    "dub techno": ("Techno", "Raw - Deep - Hypnotic"),
    "detroit techno": ("Techno", "Raw - Deep - Hypnotic"),
    "underground techno": ("Techno", "Raw - Deep - Hypnotic"),
    "atmospheric techno": ("Techno", "Raw - Deep - Hypnotic"),
    "groove techno": ("Techno", "Raw - Deep - Hypnotic"),
    "industrial dub": ("Techno", "Raw - Deep - Hypnotic"),

    # — Industrial —
    "industrial": ("Techno", "Industrial"),
    "ebm": ("Techno", "Industrial"),
    "body music": ("Techno", "Industrial"),
    "dark electro": ("Techno", "Industrial"),
    "aggrotech": ("Techno", "Industrial"),

    # — Minimal / Deep Tech —
    "minimal": ("Techno", "Minimal - Deep Tech"),
    "minimal techno": ("Techno", "Minimal - Deep Tech"),
    "minimal deep tech": ("Techno", "Minimal - Deep Tech"),
    "deep tech": ("Techno", "Minimal - Deep Tech"),
    "tech minimal": ("Techno", "Minimal - Deep Tech"),
    "microhouse": ("Techno", "Minimal - Deep Tech"),
    "glitch": ("Techno", "Minimal - Deep Tech"),

    # =====================================================================
    # MELODIC HOUSE & TECHNO  (Beatport género autónomo)
    # =====================================================================
    "melodic house and techno": ("Melodic House & Techno", None),
    "melodic and progressive": ("Melodic House & Techno", None),
    # "Melodic Techno" y "Melodic House" se fusionaron en este género único
    # (sesión 2026-06-22) — sonaban igual y se confundían entre sí.
    "melodic techno": ("Melodic House & Techno", None),
    "melodic house techno": ("Melodic House & Techno", None),
    "melodic progressive": ("Melodic House & Techno", None),
    "progressive melodic": ("Melodic House & Techno", None),
    "melodic": ("Melodic House & Techno", None),
    "melodic house": ("Melodic House & Techno", None),

    # =====================================================================
    # HOUSE
    # =====================================================================

    # — genérico —
    "house": ("House", None),
    "house music": ("House", None),
    "chicago house": ("House", None),

    # — Progressive House —
    "progressive house": ("House", "Progressive House"),
    "prog house": ("House", "Progressive House"),
    "progressive": ("House", "Progressive House"),
    "future house": ("House", "Progressive House"),
    "melodic progressive house": ("House", "Progressive House"),
    "bigroom progressive": ("House", "Progressive House"),
    "funky house": ("House", "Progressive House"),
    "filter house": ("House", "Progressive House"),
    "french house": ("House", "Progressive House"),

    # — Deep House —
    "deep house": ("House", "Deep House"),
    "deep": ("House", "Deep House"),
    "soulful house": ("House", "Deep House"),
    "vocal house": ("House", "Deep House"),
    "nudisco": ("House", "Deep House"),
    "lounge house": ("House", "Deep House"),
    "jazzy house": ("House", "Deep House"),
    "tropical house": ("House", "Deep House"),

    # — Tech House —
    "tech house": ("House", "Tech House"),
    "minimal tech house": ("House", "Tech House"),
    "bass tech house": ("House", "Tech House"),
    "vocal tech house": ("House", "Tech House"),
    "tech funk": ("House", "Tech House"),
    "groove house": ("House", "Tech House"),
    "tech": ("House", "Tech House"),

    # — Jackin House —
    "jackin house": ("House", "Jackin House"),
    "jackin": ("House", "Jackin House"),
    "club house": ("House", "Jackin House"),
    "jacking house": ("House", "Jackin House"),

    # — Bass House —
    "bass house": ("House", "Bass House"),
    "slap house": ("House", "Bass House"),
    "bounce": ("House", "Bass House"),
    "future bass": ("House", "Bass House"),
    "uk house": ("House", "Bass House"),

    # — Afro House —
    "afro house": ("House", "Afro House"),
    "afrohouse": ("House", "Afro House"),
    "afro tech": ("House", "Afro House"),
    "afro soul": ("House", "Afro House"),
    "tribal house": ("House", "Afro House"),
    "african house": ("House", "Afro House"),
    "afro": ("House", "Afro House"),

    # — Organic House —
    "organic house": ("House", "Organic House"),
    "organic house downtempo": ("House", "Organic House"),
    "organic house down tempo": ("House", "Organic House"),
    "organic": ("House", "Organic House"),
    "afro organic": ("House", "Organic House"),
    "world house": ("House", "Organic House"),

    # — Electro House —
    "electro house": ("House", "Electro House"),
    "complextro": ("House", "Electro House"),
    "dirty electro": ("House", "Electro House"),
    "electroclash": ("House", "Electro House"),

    # =====================================================================
    # TRANCE
    # =====================================================================

    # — genérico —
    "trance": ("Trance", "Main Floor"),
    "trance music": ("Trance", "Main Floor"),

    # — Main Floor —
    "trance main floor": ("Trance", "Main Floor"),
    "main floor": ("Trance", "Main Floor"),
    "uplifting trance": ("Trance", "Main Floor"),
    "uplifting": ("Trance", "Main Floor"),
    "eurotrance": ("Trance", "Main Floor"),
    "anthem trance": ("Trance", "Main Floor"),
    "epic trance": ("Trance", "Main Floor"),

    # — Vocal Trance —
    "vocal trance": ("Trance", "Vocal Trance"),
    "vocal": ("Trance", "Vocal Trance"),
    "trancepop": ("Trance", "Vocal Trance"),
    "trance pop": ("Trance", "Vocal Trance"),

    # — Progressive Trance —
    "progressive trance": ("Trance", "Progressive Trance"),
    "prog trance": ("Trance", "Progressive Trance"),

    # — Tech Trance —
    "tech trance": ("Trance", "Tech Trance"),
    "techno trance": ("Trance", "Tech Trance"),

    # — Hard Trance —
    "hard trance": ("Trance", "Hard Trance"),
    "hardtrance": ("Trance", "Hard Trance"),
    "acid trance": ("Trance", "Hard Trance"),

    # — Psy-Trance —
    "psy trance": ("Trance", "Psy-Trance"),
    "psytrance": ("Trance", "Psy-Trance"),
    "psychedelic trance": ("Trance", "Psy-Trance"),
    "psychedelic": ("Trance", "Psy-Trance"),
    "psychadelic": ("Trance", "Psy-Trance"),
    "dark psy": ("Trance", "Psy-Trance"),
    "dark psytrance": ("Trance", "Psy-Trance"),
    "full on": ("Trance", "Psy-Trance"),
    "fullon": ("Trance", "Psy-Trance"),
    "forest psy": ("Trance", "Psy-Trance"),
    "night psy": ("Trance", "Psy-Trance"),

    # — Goa —
    "goa": ("Trance", "Goa"),
    "goa trance": ("Trance", "Goa"),
    "goatrance": ("Trance", "Goa"),

    # — Raw / Deep / Hypnotic —
    "trance raw deep hypnotic": ("Trance", "Raw - Deep - Hypnotic"),
    "raw trance": ("Trance", "Raw - Deep - Hypnotic"),
    "deep trance": ("Trance", "Raw - Deep - Hypnotic"),
    "hypnotic trance": ("Trance", "Raw - Deep - Hypnotic"),
    "underground trance": ("Trance", "Raw - Deep - Hypnotic"),

    # =====================================================================
    # BREAKS
    # =====================================================================
    "breaks": ("Breaks", "Breakbeat"),
    "breakbeat": ("Breaks", "Breakbeat"),
    "breakbeats": ("Breaks", "Breakbeat"),
    "nu skool breaks": ("Breaks", "Breakbeat"),
    "electro breaks": ("Breaks", "Electro Breaks"),
    "uk bass": ("Breaks", "UK Bass"),
    "jungle": ("Breaks", "Jungle"),
    "raggajungle": ("Breaks", "Jungle"),
    "ragga jungle": ("Breaks", "Jungle"),

    # =====================================================================
    # DRUM & BASS
    # =====================================================================
    "drum and bass": ("Drum & Bass", None),
    "drum n bass": ("Drum & Bass", None),
    "dnb": ("Drum & Bass", None),
    "d and b": ("Drum & Bass", None),
    "d n b": ("Drum & Bass", None),
    "liquid": ("Drum & Bass", "Liquid"),
    "liquid dnb": ("Drum & Bass", "Liquid"),
    "liquid drum and bass": ("Drum & Bass", "Liquid"),
    "liquid funk": ("Drum & Bass", "Liquid"),
    "neurofunk": ("Drum & Bass", "Neurofunk"),
    "neuro": ("Drum & Bass", "Neurofunk"),
    "jump up": ("Drum & Bass", "Jump Up"),
    "jumpup": ("Drum & Bass", "Jump Up"),
    "dancefloor dnb": ("Drum & Bass", "Dancefloor"),
    "rollers": ("Drum & Bass", "Dancefloor"),
    "minimal dnb": ("Drum & Bass", "Minimal DnB"),

    # =====================================================================
    # UK GARAGE
    # =====================================================================
    "uk garage": ("UK Garage", None),
    "garage": ("UK Garage", None),
    "speed garage": ("UK Garage", "Speed Garage"),
    "2 step": ("UK Garage", "2-Step"),
    "2step": ("UK Garage", "2-Step"),
    "two step": ("UK Garage", "2-Step"),
    "bassline": ("UK Garage", "Bassline"),
    "bassline house": ("UK Garage", "Bassline"),
    "grime": ("UK Garage", None),
    "ukg": ("UK Garage", None),

    # =====================================================================
    # ELECTRO (Classic / Detroit / Modern)
    # =====================================================================
    "electro": ("Electro", None),
    "classic electro": ("Electro", "Classic Electro"),
    "detroit electro": ("Electro", "Detroit Electro"),
    "modern electro": ("Electro", "Modern Electro"),
    "electro funk": ("Electro", "Classic Electro"),
    "miami bass": ("Electro", "Classic Electro"),
    "ghetto tech": ("Electro", "Modern Electro"),
    "electro rap": ("Electro", "Classic Electro"),

    # =====================================================================
    # INDIE DANCE / NU DISCO
    # =====================================================================
    "indie dance": ("Indie Dance", None),
    "indie dance nu disco": ("Indie Dance", "Nu Disco"),
    "nu disco": ("Indie Dance", "Nu Disco"),
    "nu disco disco": ("Indie Dance", "Nu Disco"),
    "disco": ("Indie Dance", "Nu Disco"),
    "italo disco": ("Indie Dance", "Nu Disco"),
    "indie": ("Indie Dance", None),
    "indie pop": ("Indie Dance", None),
    "electropop": ("Indie Dance", None),
    "electro pop": ("Indie Dance", None),
    "synthpop": ("Indie Dance", None),
    "synth pop": ("Indie Dance", None),
    "new wave": ("Indie Dance", None),
    "post punk": ("Indie Dance", None),
    "dream pop": ("Indie Dance", None),

    # =====================================================================
    # ELECTRONICA / EXPERIMENTAL
    # =====================================================================
    "electronica": ("Electronica", None),
    "electronic": ("Electronica", None),
    "idm": ("Electronica", "IDM"),
    "intelligent dance music": ("Electronica", "IDM"),
    "experimental": ("Electronica", "Experimental"),
    "avant garde": ("Electronica", "Experimental"),
    "ambient techno": ("Electronica", "Ambient Techno"),
    "leftfield": ("Electronica", None),
    "braindance": ("Electronica", "IDM"),
    "glitchcore": ("Electronica", "Experimental"),

    # =====================================================================
    # AMBIENT / DOWNTEMPO
    # =====================================================================
    "ambient": ("Ambient", None),
    "ambient music": ("Ambient", None),
    "downtempo": ("Ambient", "Downtempo"),
    "down tempo": ("Ambient", "Downtempo"),
    "chillout": ("Ambient", "Chillout"),
    "chill out": ("Ambient", "Chillout"),
    "chillwave": ("Ambient", "Chillout"),
    "trip hop": ("Ambient", "Downtempo"),
    "triphop": ("Ambient", "Downtempo"),
    "lo fi": ("Ambient", "Downtempo"),
    "lofi": ("Ambient", "Downtempo"),
    "new age": ("Ambient", None),

    # =====================================================================
    # AFRO / AMAPIANO / GQOM
    # =====================================================================
    "afrobeats": ("Afro", "Afrobeats"),
    "afrobeat": ("Afro", "Afrobeats"),
    "afropop": ("Afro", "Afrobeats"),
    "amapiano": ("Afro", "Amapiano"),
    "gqom": ("Afro", "Gqom"),
    "afro pop": ("Afro", "Afrobeats"),

    # =====================================================================
    # HARD DANCE
    # =====================================================================
    "hardcore": ("Hard Dance", "Hardcore"),
    "hard dance": ("Hard Dance", None),
    "gabber": ("Hard Dance", "Hardcore"),
    "happy hardcore": ("Hard Dance", "Hardcore"),
    "terrorcore": ("Hard Dance", "Hardcore"),
    "hardstyle": ("Hard Dance", "Hardstyle"),
    "euphoric hardstyle": ("Hard Dance", "Hardstyle"),
    "rawstyle": ("Hard Dance", "Hardstyle"),
    "jumpstyle": ("Hard Dance", "Hardstyle"),

    # =====================================================================
    # BIG ROOM / MAINSTAGE / EDM
    # =====================================================================
    "big room": ("Big Room", None),
    "big room house": ("Big Room", None),
    "mainstage": ("Big Room", None),
    "main stage": ("Big Room", None),
    "edm": ("Big Room", None),
    "festival": ("Big Room", None),
    "dance": ("Big Room", None),
    "club": ("Big Room", None),
    "pop": ("Big Room", None),

    # =====================================================================
    # FUNK & SOUL / HIP-HOP / LATIN
    # =====================================================================
    "funk": ("Funk & Soul", "Funk"),
    "soul": ("Funk & Soul", "Soul"),
    "rnb": ("Funk & Soul", "R&B"),
    "r and b": ("Funk & Soul", "R&B"),
    "rhythm and blues": ("Funk & Soul", "R&B"),
    "neo soul": ("Funk & Soul", "Soul"),
    "hip hop": ("Hip-Hop", None),
    "hiphop": ("Hip-Hop", None),
    "rap": ("Hip-Hop", "Rap"),
    "trap": ("Hip-Hop", "Trap"),
    "phonk": ("Hip-Hop", "Phonk"),
    "latin": ("Latin", None),
    "reggaeton": ("Latin", "Reggaeton"),
    "dembow": ("Latin", "Dembow"),
    "brazilian funk": ("Latin", "Brazilian Funk"),
    "funk carioca": ("Latin", "Brazilian Funk"),
    "baile funk": ("Latin", "Brazilian Funk"),
}

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aiff", ".aif", ".flac", ".m4a", ".aac", ".ogg"}

# Calidad: bitrate (kbps) por debajo del cual un MP3/AAC se considera baja calidad.
LOW_QUALITY_BITRATE_KBPS = 256
# Formatos sin pérdida (siempre alta calidad)
LOSSLESS_EXTENSIONS = {".wav", ".aiff", ".aif", ".flac"}
