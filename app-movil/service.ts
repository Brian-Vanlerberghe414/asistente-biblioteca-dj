import TrackPlayer, { Event } from 'react-native-track-player';

// `TrackPlayer.registerPlaybackService` espera recibir la función directo
// vía `require(...)` (patrón documentado de RNTP) — no vía `export default`
// (con interop ESM, `require` devolvería `{ default: fn }`, no `fn`).
declare const module: { exports: unknown };

/** Playback service de `react-native-track-player` — maneja los eventos
 * remotos (notificación/lockscreen) para que Mi Música siga controlable con
 * la pantalla bloqueada (ver plan, Tab 4). Registrado desde `app/_layout.tsx`
 * antes de que arranque cualquier componente. */
module.exports = async function () {
  TrackPlayer.addEventListener(Event.RemotePlay, () => TrackPlayer.play());
  TrackPlayer.addEventListener(Event.RemotePause, () => TrackPlayer.pause());
  TrackPlayer.addEventListener(Event.RemoteStop, () => TrackPlayer.stop());
  TrackPlayer.addEventListener(Event.RemoteNext, () => TrackPlayer.skipToNext().catch(() => {}));
  TrackPlayer.addEventListener(Event.RemotePrevious, () => TrackPlayer.skipToPrevious().catch(() => {}));
  TrackPlayer.addEventListener(Event.RemoteSeek, ({ position }) => TrackPlayer.seekTo(position));
};
