import { api } from './http';

export type ModoColaboracion = 'dueno_manda' | 'abierto';
export type RolMiembro = 'dueno' | 'miembro';

export interface PlaylistCompartida {
  id: string;
  codigo: string;
  nombre: string;
  dueno_id: string;
  modo_colaboracion: ModoColaboracion;
  creado_en: string;
  actualizado_en: string;
  mi_rol?: RolMiembro;
}

export interface TrackCompartido {
  id: string;
  playlist_id: string;
  aportado_por: string;
  artista_norm: string;
  titulo_norm: string;
  artista: string | null;
  titulo: string | null;
  sello: string | null;
  anio: string | null;
  bpm: number | null;
  key: string | null;
  camelot: string | null;
  duracion_seg: number | null;
  genero: string | null;
  subgenero: string | null;
  cover_url: string | null;
  mix_name: string | null;
  agregado_en: string;
}

export interface MiembroCompartida {
  playlist_id: string;
  usuario_id: string;
  rol: RolMiembro;
  unido_en: string;
}

export interface DetallePlaylistCompartida extends PlaylistCompartida {
  tracks: TrackCompartido[];
  miembros: MiembroCompartida[];
}

export interface TrackAporte {
  artista: string;
  titulo: string;
  sello?: string | null;
  anio?: string | null;
  bpm?: number | null;
  key?: string | null;
  camelot?: string | null;
  duracion_seg?: number | null;
  genero?: string | null;
  subgenero?: string | null;
  cover_url?: string | null;
  mix_name?: string | null;
}

export function crearPlaylistCompartida(nombre: string, modo: ModoColaboracion = 'dueno_manda'): Promise<PlaylistCompartida> {
  return api.post<PlaylistCompartida>('/playlists-compartidas', { nombre, modo_colaboracion: modo });
}

export function unirseAPlaylist(codigo: string): Promise<PlaylistCompartida> {
  return api.post<PlaylistCompartida>('/playlists-compartidas/unirse', { codigo: codigo.trim().toUpperCase() });
}

export function listarPlaylistsCompartidas(): Promise<PlaylistCompartida[]> {
  return api.get<PlaylistCompartida[]>('/playlists-compartidas');
}

export function detallePlaylistCompartida(id: string): Promise<DetallePlaylistCompartida> {
  return api.get<DetallePlaylistCompartida>(`/playlists-compartidas/${id}`);
}

export function aportarTracks(id: string, tracks: TrackAporte[]): Promise<{ agregados: number }> {
  return api.post<{ agregados: number }>(`/playlists-compartidas/${id}/tracks`, tracks);
}

export function quitarTrackCompartido(id: string, trackId: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/playlists-compartidas/${id}/tracks/${trackId}`);
}

export function renombrarPlaylistCompartida(id: string, nombre: string): Promise<{ ok: boolean }> {
  return api.patch<{ ok: boolean }>(`/playlists-compartidas/${id}`, { nombre });
}

export function salirDePlaylist(id: string): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>(`/playlists-compartidas/${id}/salir`);
}

export function borrarPlaylistCompartida(id: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/playlists-compartidas/${id}`);
}

export function expulsarMiembro(id: string, uid: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/playlists-compartidas/${id}/miembros/${uid}`);
}
