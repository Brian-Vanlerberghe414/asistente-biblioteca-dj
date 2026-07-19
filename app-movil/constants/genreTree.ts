/**
 * Árbol de géneros — portado de `asistente_dj/config.py:GENRE_TREE`.
 * Única fuente de verdad para la EDICIÓN de género/subgénero (géneros
 * reales, nunca paraguas — el paraguas es solo capa de vista, ver
 * `constants/unificaciones` en el cliente API).
 */
export const GENRE_TREE: Record<string, string[]> = {
  'Techno': [
    'Peak Time - Driving',
    'Hard Techno',
    'Raw - Deep - Hypnotic',
    'Industrial',
    'Minimal - Deep Tech',
  ],
  'House': [
    'Progressive House',
    'Deep House',
    'Tech House',
    'Jackin House',
    'Bass House',
    'Afro House',
    'Organic House',
    'Electro House',
  ],
  'Trance': [
    'Main Floor',
    'Vocal Trance',
    'Progressive Trance',
    'Tech Trance',
    'Hard Trance',
    'Psy-Trance',
    'Goa',
    'Raw - Deep - Hypnotic',
  ],
  'Melodic House & Techno': [],
  'Breaks': [
    'Breakbeat',
    'Electro Breaks',
    'UK Bass',
    'Jungle',
  ],
  'Drum & Bass': [
    'Liquid',
    'Neurofunk',
    'Jump Up',
    'Jungle',
    'Dancefloor',
    'Minimal DnB',
  ],
  'UK Garage': [
    'Speed Garage',
    '2-Step',
    'Bassline',
  ],
  'Electro': [
    'Classic Electro',
    'Detroit Electro',
    'Modern Electro',
  ],
  'Indie Dance': [
    'Nu Disco',
  ],
  'Electronica': [
    'IDM',
    'Ambient Techno',
    'Experimental',
  ],
  'Ambient': [
    'Downtempo',
    'Chillout',
  ],
  'Afro': [
    'Amapiano',
    'Afrobeats',
    'Gqom',
  ],
  'Hard Dance': [
    'Hardcore',
    'Hardstyle',
  ],
  'Big Room': [],
  'Funk & Soul': [
    'Funk',
    'Soul',
    'R&B',
  ],
  'Hip-Hop': [
    'Trap',
    'Phonk',
    'Rap',
  ],
  'Latin': [
    'Reggaeton',
    'Dembow',
    'Brazilian Funk',
  ],
};

export const GENEROS = Object.keys(GENRE_TREE);
