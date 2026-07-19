import React, { createContext, useCallback, useContext, useRef, useState } from 'react';

/**
 * Contrato completo del player global — decidido en la Sesión 2 para no
 * repetir en Android la reescritura por capas que hizo falta en el
 * reproductor unificado del escritorio (`gui/organizador.py:PlayerWidget`):
 * ahí primero hubo un esqueleto por pantalla, después waveform congelado con
 * YouTube, carátula duplicada en Charts, "sonando" sin resaltar hasta
 * agregarlo aparte en cada grilla. Acá se define TODO desde el arranque:
 *
 * - Una sola fuente de reproducción a la vez ('local' — Biblioteca/
 *   Playlists/Mi Música vía R2 — o 'youtube' — Charts). Activar una fuente
 *   nueva corta/pausa la anterior sola (equivalente RN de
 *   activar_motor_externo/volver_a_motor_local del escritorio).
 * - "Cambió la fuente activa": NO hace falta un evento aparte (a diferencia
 *   de Qt/desktop) — al vivir `nowPlaying` en contexto de React, cualquier
 *   pantalla que lo lea (`usePlayer().nowPlaying`) ya se re-renderiza sola
 *   cuando cambia, y puede apagar su propio resaltado comparando
 *   `nowPlaying?.id`/`tipo` contra lo suyo. El contexto ES el mecanismo de
 *   notificación.
 * - `nowPlaying` expuesto para que Biblioteca/Charts/Playlists (Sesiones 3,
 *   5, 7, 8) resalten la fila que suena en cyan sin reimplementar nada.
 * - Carátula real siempre (nunca placeholder): quien active una fuente
 *   manda su propia `coverUrl` (local: la del track; YouTube:
 *   `hqdefault.jpg` del video_id).
 * - Progreso real aunque la fuente sea YouTube: el motor de reproducción
 *   activo (YoutubePlayer en Sesión 4, TrackPlayer en Sesión 9) es quien
 *   reporta progreso/duración vía `reportarProgreso` — la barra del
 *   mini-player nunca depende de un timer propio que se desincroniza (el
 *   bug exacto que hubo que parchear en el escritorio).
 *
 * El contexto es agnóstico al motor real: cada fuente, al activarse,
 * registra sus propios `Controles` (pausar/reanudar/detener/buscar) — así
 * el mini-player puede controlar "lo que sea que esté sonando" sin saber
 * si es un iframe de YouTube o un audio nativo de R2.
 */

export type TipoFuente = 'local' | 'youtube';

export interface InfoFuente {
  tipo: TipoFuente;
  /** Identificador estable para que una lista sepa "esta es mi fila":
   * local → id de `mi_biblioteca`/r2_key; youtube → `${slug}:${posicion}`. */
  id: string;
  titulo: string;
  artista: string | null;
  coverUrl: string | null;
  duracionSeg: number | null;
}

export interface Controles {
  pausar: () => void;
  reanudar: () => void;
  detener: () => void;
  buscar?: (seg: number) => void;
}

export interface NowPlaying extends InfoFuente {
  progresoSeg: number;
  reproduciendo: boolean;
}

interface PlayerContextValue {
  nowPlaying: NowPlaying | null;

  /** La pantalla que INICIA una fuente la registra acá (con sus propios
   * controles reales) — corta/reemplaza silenciosamente lo que sonaba
   * antes, sea cual sea su tipo. */
  activarFuente: (info: InfoFuente, controles: Controles) => void;

  /** El motor activo reporta su progreso real en cada tick — nunca lo
   * calcula el contexto ni un timer aparte. */
  reportarProgreso: (seg: number, duracionSeg?: number) => void;
  reportarReproduciendo: (val: boolean) => void;

  pausar: () => void;
  reanudar: () => void;
  detener: () => void;
  buscar: (seg: number) => void;
}

const PlayerContext = createContext<PlayerContextValue | null>(null);

export function PlayerProvider({ children }: { children: React.ReactNode }) {
  const [nowPlaying, setNowPlaying] = useState<NowPlaying | null>(null);
  const controlesRef = useRef<Controles | null>(null);

  const activarFuente = useCallback((info: InfoFuente, controles: Controles) => {
    // Cortar la fuente anterior (si había una distinta) antes de tomar el
    // control — nunca conviven dos fuentes sonando a la vez.
    if (controlesRef.current) {
      controlesRef.current.detener();
    }
    controlesRef.current = controles;
    setNowPlaying({ ...info, progresoSeg: 0, reproduciendo: true });
  }, []);

  const reportarProgreso = useCallback((seg: number, duracionSeg?: number) => {
    setNowPlaying(prev => {
      if (!prev) return prev;
      return { ...prev, progresoSeg: seg, duracionSeg: duracionSeg ?? prev.duracionSeg };
    });
  }, []);

  const reportarReproduciendo = useCallback((val: boolean) => {
    setNowPlaying(prev => (prev ? { ...prev, reproduciendo: val } : prev));
  }, []);

  const pausar = useCallback(() => controlesRef.current?.pausar(), []);
  const reanudar = useCallback(() => controlesRef.current?.reanudar(), []);
  const buscar = useCallback((seg: number) => controlesRef.current?.buscar?.(seg), []);

  const detener = useCallback(() => {
    controlesRef.current?.detener();
    controlesRef.current = null;
    setNowPlaying(null);
  }, []);

  return (
    <PlayerContext.Provider
      value={{ nowPlaying, activarFuente, reportarProgreso, reportarReproduciendo, pausar, reanudar, detener, buscar }}
    >
      {children}
    </PlayerContext.Provider>
  );
}

export function usePlayer(): PlayerContextValue {
  const ctx = useContext(PlayerContext);
  if (!ctx) throw new Error('usePlayer debe usarse dentro de <PlayerProvider>');
  return ctx;
}

/** Atajo para que una fila de lista sepa si ES la que está sonando (para
 * resaltarla en cyan) sin repetir la comparación de tipo+id en cada
 * pantalla. */
export function useEsSonando(tipo: TipoFuente, id: string): boolean {
  const { nowPlaying } = usePlayer();
  return nowPlaying?.tipo === tipo && nowPlaying?.id === id;
}

/** URL de carátula real de YouTube a partir del video_id — nunca
 * placeholder (ver contrato de "Player global" arriba). */
export function coverUrlYoutube(videoId: string): string {
  return `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
}
