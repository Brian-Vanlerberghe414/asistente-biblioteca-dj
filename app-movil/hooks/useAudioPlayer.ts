import { useCallback, useEffect, useRef } from 'react';
import TrackPlayer, {
  AppKilledPlaybackBehavior, Capability, Event, State,
} from 'react-native-track-player';

import { type AudioPersonal, pedirUrlDescarga } from '../api/audio';
import { usePlayer } from '../context/PlayerContext';

let inicializado: Promise<void> | null = null;

/** `setupPlayer` solo puede llamarse una vez por vida del proceso (y solo
 * con la app en foreground, ver docs de RNTP) — se hace lazy, en el primer
 * play, no al arrancar la app (Mi Música puede no usarse nunca en una
 * sesión). */
function asegurarPlayer(): Promise<void> {
  if (!inicializado) {
    inicializado = TrackPlayer.setupPlayer().then(() =>
      TrackPlayer.updateOptions({
        android: { appKilledPlaybackBehavior: AppKilledPlaybackBehavior.StopPlaybackAndRemoveNotification },
        capabilities: [
          Capability.Play, Capability.Pause, Capability.Stop,
          Capability.SkipToNext, Capability.SkipToPrevious, Capability.SeekTo,
        ],
        compactCapabilities: [Capability.Play, Capability.Pause, Capability.SkipToNext],
      })
    );
  }
  return inicializado;
}

/** Conecta `react-native-track-player` (streaming de R2, background +
 * lockscreen) como fuente 'local' del `PlayerContext` ya definido en la
 * Sesión 2 — no arma su propio mini-player ni resaltado, ver Tab 4 del
 * plan. URLs firmadas resueltas JUST-IN-TIME (nunca toda la cola junta). */
export function useAudioPlayer(cola: AudioPersonal[]) {
  const player = usePlayer();
  const colaRef = useRef(cola);
  colaRef.current = cola;
  const indiceActualRef = useRef<number>(-1);

  const reproducirIndice = useCallback(async (indice: number) => {
    const lista = colaRef.current;
    const track = lista[indice];
    if (!track) return;
    indiceActualRef.current = indice;

    await asegurarPlayer();
    const { download_url } = await pedirUrlDescarga(track.r2_key);

    await TrackPlayer.reset();
    await TrackPlayer.add({
      id: track.r2_key,
      url: download_url,
      title: track.titulo ?? '(sin título)',
      artist: track.artista ?? undefined,
    });
    await TrackPlayer.play();

    player.activarFuente(
      {
        tipo: 'local', id: track.r2_key, titulo: track.titulo ?? '(sin título)',
        artista: track.artista, coverUrl: null, duracionSeg: null,
      },
      {
        pausar: () => TrackPlayer.pause(),
        reanudar: () => TrackPlayer.play(),
        detener: () => TrackPlayer.reset(),
      },
    );
  }, [player]);

  const siguiente = useCallback(() => {
    if (indiceActualRef.current + 1 < colaRef.current.length) reproducirIndice(indiceActualRef.current + 1);
  }, [reproducirIndice]);

  const anterior = useCallback(() => {
    if (indiceActualRef.current > 0) reproducirIndice(indiceActualRef.current - 1);
  }, [reproducirIndice]);

  // Progreso real (mismo contrato que YouTube — la barra del mini-player se
  // alimenta de la fuente que sea, nunca de un timer separado).
  useEffect(() => {
    const id = setInterval(async () => {
      if (indiceActualRef.current < 0) return;
      try {
        const estado = await TrackPlayer.getPlaybackState();
        if (estado.state !== State.Playing && estado.state !== State.Buffering) return;
        const progreso = await TrackPlayer.getProgress();
        player.reportarProgreso(progreso.position, progreso.duration || undefined);
      } catch {
        // El player puede no estar inicializado todavía.
      }
    }, 1000);
    return () => clearInterval(id);
  }, [player]);

  useEffect(() => {
    const subs = [
      TrackPlayer.addEventListener(Event.PlaybackState, ({ state }) => {
        if (indiceActualRef.current < 0) return;
        player.reportarReproduciendo(state === State.Playing || state === State.Buffering);
      }),
      TrackPlayer.addEventListener(Event.PlaybackQueueEnded, () => {
        if (indiceActualRef.current < 0) return;
        siguiente();
      }),
    ];
    return () => subs.forEach(s => s.remove());
  }, [player, siguiente]);

  return { reproducirIndice, siguiente, anterior };
}
