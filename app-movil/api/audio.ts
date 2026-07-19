import { api } from './http';

export interface AudioPersonal {
  id: number;
  usuario_id: string;
  r2_key: string;
  titulo: string | null;
  artista: string | null;
  tamano_bytes: number;
  ruta_local: string | null;
  subido_en: string;
}

const TAMANO_PAGINA = 500;

export async function traerColeccionCompleta(onProgreso?: (n: number) => void): Promise<AudioPersonal[]> {
  const resultado: AudioPersonal[] = [];
  let beforeId: number | undefined;
  for (;;) {
    const pagina = await api.get<AudioPersonal[]>('/audio/mios', { before_id: beforeId, limit: TAMANO_PAGINA });
    resultado.push(...pagina);
    onProgreso?.(resultado.length);
    if (pagina.length < TAMANO_PAGINA) break;
    beforeId = pagina[pagina.length - 1].id;
  }
  return resultado;
}

/** URLs firmadas de R2 vencen en 1 hora — se resuelven JUST-IN-TIME al
 * cargar cada track (nunca se pre-resuelve la cola completa). */
export function pedirUrlDescarga(r2Key: string): Promise<{ download_url: string }> {
  return api.get<{ download_url: string }>(`/audio/${encodeURIComponent(r2Key)}/download-url`);
}
