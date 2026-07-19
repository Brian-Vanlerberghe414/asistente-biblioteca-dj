import { api } from './http';

export interface PlaylistPropia {
  id: number;
  usuario_id: string;
  nombre: string;
  reglas: { ids: number[] };
  actualizado_en: string;
}

export function obtenerMisPlaylists(): Promise<PlaylistPropia[]> {
  return api.get<PlaylistPropia[]>('/mi-biblioteca/playlists');
}

/** Upsert por nombre — pisa la lista COMPLETA de ids (ver plan: estrategia
 * "última escritura gana", igual que el resto de la sincronización
 * personal — no hay merge). */
export function guardarPlaylist(nombre: string, ids: number[]): Promise<{ aplicado: boolean }> {
  return api.post<{ aplicado: boolean }>('/mi-biblioteca/playlists', {
    nombre, ids, actualizado_en: new Date().toISOString(),
  });
}

export function renombrarPlaylist(nombre: string, nombreNuevo: string): Promise<PlaylistPropia> {
  return api.patch<PlaylistPropia>(`/mi-biblioteca/playlists/${encodeURIComponent(nombre)}`, {
    nombre_nuevo: nombreNuevo,
  });
}

export function borrarPlaylist(nombre: string): Promise<{ borrado: boolean }> {
  return api.delete<{ borrado: boolean }>(`/mi-biblioteca/playlists/${encodeURIComponent(nombre)}`);
}
