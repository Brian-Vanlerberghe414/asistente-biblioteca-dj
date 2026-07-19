import { api } from './http';

export interface TrackBiblioteca {
  id: number;
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
  energia: number | null;
  r2_key: string | null;
  actualizado_en: string;
}

const TAMANO_PAGINA = 500;

/** Cache en memoria del último `traerBibliotecaCompleta()` — la pantalla de
 * edición (`biblioteca/[id].tsx`) la lee por id en vez de pedir de nuevo un
 * solo track (no hay endpoint para eso; siempre se navega ahí DESDE la
 * lista, que ya tiene todo cargado). */
export const cacheBiblioteca = {
  porId: new Map<number, TrackBiblioteca>(),
};

/** Trae TODA la biblioteca personal paginando por keyset (`after_id`) —
 * pensado para ~2000 tracks (unas pocas páginas), no para bibliotecas
 * ilimitadas. `onProgreso` opcional para mostrar "cargando X de..." mientras
 * arma la primera lista completa. */
export async function traerBibliotecaCompleta(
  onProgreso?: (cantidad: number) => void
): Promise<TrackBiblioteca[]> {
  const resultado: TrackBiblioteca[] = [];
  let afterId: number | undefined;

  for (;;) {
    const pagina = await api.get<TrackBiblioteca[]>('/mi-biblioteca', {
      after_id: afterId, limit: TAMANO_PAGINA,
    });
    resultado.push(...pagina);
    onProgreso?.(resultado.length);
    if (pagina.length < TAMANO_PAGINA) break;
    afterId = pagina[pagina.length - 1].id;
  }
  cacheBiblioteca.porId = new Map(resultado.map(t => [t.id, t]));
  return resultado;
}

export interface CambioTrack {
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
  energia?: number | null;
  r2_key?: string | null;
  actualizado_en: string;
}

export interface ResultadoSync {
  resultados: { artista: string; titulo: string; aplicado: boolean }[];
}

export function sincronizarTracks(cambios: CambioTrack[]): Promise<ResultadoSync> {
  return api.post<ResultadoSync>('/mi-biblioteca/sync', cambios);
}
