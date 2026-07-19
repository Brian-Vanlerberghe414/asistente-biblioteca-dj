import { api } from './http';

export interface Genero {
  genero_slug: string;
  nombre: string;
  ultima: string | null;
  umbrella: string | null;
}

export interface ChartTrack {
  id: number;
  beatport_id: string;
  genero_slug: string;
  genero_nombre?: string | null;
  posicion: number;
  nombre: string;
  mix_name?: string | null;
  artistas: string[] | null;
  remixers?: string[] | null;
  release?: string | null;
  sello?: string | null;
  bpm?: number | null;
  key?: string | null;
  genero_pista?: string | null;
  duracion_ms?: number | null;
  publish_date?: string | null;
  image_url?: string | null;
  primera_vez?: string | null;
  fecha_scrape?: string | null;
}

export interface CandidatoYoutube {
  video_id: string;
  titulo: string;
  duracion_seg: number | null;
  es_extended: boolean;
}

export function obtenerGeneros(): Promise<Genero[]> {
  return api.get<Genero[]>('/charts/generos');
}

export function obtenerChart(slug: string, top = 100): Promise<ChartTrack[]> {
  return api.get<ChartTrack[]>(`/charts/${encodeURIComponent(slug)}`, { top });
}

export function obtenerNovedades(slug: string): Promise<ChartTrack[]> {
  return api.get<ChartTrack[]>(`/charts/${encodeURIComponent(slug)}/novedades`);
}

export function obtenerCandidatosYoutube(slug: string, posicion: number): Promise<CandidatoYoutube[]> {
  return api.get<CandidatoYoutube[]>(`/charts/${encodeURIComponent(slug)}/preview/${posicion}`);
}

/** Búsqueda genérica (Playlists — no depende de slug/posición de chart). */
export function buscarCandidatosYoutube(artista: string, titulo: string, mixName?: string | null): Promise<CandidatoYoutube[]> {
  return api.get<CandidatoYoutube[]>('/youtube/buscar', { artista, titulo, mix_name: mixName ?? undefined });
}
