/**
 * Tokens de diseño — portados de `asistente_dj/gui/theme.py` (escritorio).
 * Mismos colores base y acentos para que la app se sienta parte del mismo
 * producto; el cyan de "sonando" es el mismo en ambos lados.
 */

export const colors = {
  bgBase: '#0F0F10',
  bgPanel: '#0D0D0E',
  bgElevated: '#161617',
  bgToolbar: '#131314',
  bgHeader: '#141415',
  line: '#1F1F21',
  textPrimary: '#E9E9EC',
  textSecondary: '#9A9CA1',
  textMuted: '#75777B',

  cyan: '#00E5FF',
  orange: '#FF6B00',
  green: '#16D6A6',
  amber: '#FFB02E',
} as const;

// Escala de energía 1-10 (índice 0 = nivel 1)
export const energyColors = [
  '#2F6BFF', '#2F9BFF', '#18C5E0', '#16D6A6', '#4FD64F',
  '#B7D63A', '#FFD23A', '#FF9B2F', '#FF6A2A', '#FF3326',
];

// Camelot Wheel 1-12 (índice 0 = número 1)
export const camelotColors = [
  '#6AD5B0', '#7ED99A', '#A8DF7C', '#D4DD6F', '#F0CF6A',
  '#F5A85F', '#F07D6A', '#EE6A8F', '#D96EC0', '#A77CE0',
  '#7A8CE8', '#6AB4DC',
];

// Colores por género (mismo mapa que GENRE_COLORS del escritorio).
export const genreColors: Record<string, string> = {
  'Techno': '#00E5FF',
  'House': '#FF6B00',
  'Trance': '#A77CE0',
  'Melodic House & Techno': '#FF4FA3',
  'Breaks': '#5FE0C8',
  'Drum & Bass': '#FF4F4F',
  'UK Garage': '#4FA0FF',
  'Electro': '#C49A6C',
  'Indie Dance': '#4FD64F',
  'Electronica': '#BCBD3A',
  'Ambient': '#8FA8C9',
  'Afro': '#E0883D',
  'Hard Dance': '#FF2D78',
  'Big Room': '#FFD23A',
  'Funk & Soul': '#C77DFF',
  'Hip-Hop': '#B5654A',
  'Latin': '#FFA94D',
};

export function colorParaGenero(genero: string | null | undefined): string {
  if (!genero) return colors.textMuted;
  return genreColors[genero] ?? colors.textSecondary;
}

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
} as const;

export const radius = {
  sm: 7,
  md: 10,
  lg: 14,
} as const;

export const typography = {
  size: {
    xs: 11,
    sm: 12,
    md: 13,
    lg: 15,
    xl: 20,
  },
} as const;
