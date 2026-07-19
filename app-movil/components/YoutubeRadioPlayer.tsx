import { Ionicons } from '@expo/vector-icons';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Linking, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import YoutubeIframe, { PLAYER_STATES, type YoutubeIframeRef } from 'react-native-youtube-iframe';

import { type CandidatoYoutube, type ChartTrack, obtenerCandidatosYoutube } from '../api/charts';
import { coverUrlYoutube, usePlayer } from '../context/PlayerContext';
import { colors, radius, spacing, typography } from '../theme';

interface Props {
  slug: string;
  tracks: ChartTrack[];
  posicionInicial: number;
  onCerrar: () => void;
}

const ALTO_PLAYER = 220;

/**
 * Modo radio de Charts: autoplay al entrar + reproducción continua (pasa
 * sola al siguiente track del Top 100 cuando termina el video). Conecta
 * YouTube como fuente de `PlayerContext` (ya definido en la Sesión 2) — NO
 * arma su propio mini-player ni su propio resaltado, ver `usePlayer`.
 *
 * Requiere la pantalla ENCENDIDA (limitación conocida y aceptada del plan):
 * Android pausa el WebView al bloquear el teléfono, y reproducir YouTube en
 * background viola sus términos.
 */
export function YoutubeRadioPlayer({ slug, tracks, posicionInicial, onCerrar }: Props) {
  const player = usePlayer();
  const playerRef = useRef<YoutubeIframeRef>(null);
  const cacheCandidatos = useRef<Map<number, CandidatoYoutube[]>>(new Map());

  const [posicionIdx, setPosicionIdx] = useState(() => {
    const i = tracks.findIndex(t => t.posicion === posicionInicial);
    return i >= 0 ? i : 0;
  });
  const [candidatos, setCandidatos] = useState<CandidatoYoutube[]>([]);
  const [candidatoIdx, setCandidatoIdx] = useState(0);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [reproduciendo, setReproduciendo] = useState(true);
  const [cargando, setCargando] = useState(false);
  const [sinCandidatos, setSinCandidatos] = useState(false);

  const trackActual = tracks[posicionIdx];

  const irASiguiente = useCallback(() => {
    setPosicionIdx(i => (i + 1) % tracks.length);
  }, [tracks.length]);

  const irAAnterior = useCallback(() => {
    setPosicionIdx(i => (i - 1 + tracks.length) % tracks.length);
  }, [tracks.length]);

  // Candidatos del track actual (cacheados por posición: si el DJ vuelve
  // para atrás no vuelve a pegarle a yt-dlp).
  useEffect(() => {
    if (!trackActual) return;
    let vivo = true;
    setSinCandidatos(false);
    setCandidatoIdx(0);
    setVideoId(null);

    const enCache = cacheCandidatos.current.get(trackActual.posicion);
    if (enCache) {
      setCandidatos(enCache);
      setVideoId(enCache[0]?.video_id ?? null);
      setSinCandidatos(enCache.length === 0);
      return;
    }

    setCargando(true);
    obtenerCandidatosYoutube(slug, trackActual.posicion)
      .then(candidatosNuevos => {
        if (!vivo) return;
        cacheCandidatos.current.set(trackActual.posicion, candidatosNuevos);
        setCandidatos(candidatosNuevos);
        setVideoId(candidatosNuevos[0]?.video_id ?? null);
        setSinCandidatos(candidatosNuevos.length === 0);
      })
      .catch(() => { if (vivo) setSinCandidatos(true); })
      .finally(() => { if (vivo) setCargando(false); });

    return () => { vivo = false; };
  }, [slug, trackActual?.posicion]);

  // Fallback candidatos+fallback (mismo patrón que el escritorio): si el
  // candidato actual no embebe (error 150/101), probar el siguiente: si no
  // quedan más, ofrecer deep link a la app de YouTube.
  const probarSiguienteCandidato = useCallback(() => {
    setCandidatoIdx(i => {
      const siguiente = i + 1;
      if (siguiente < candidatos.length) {
        setVideoId(candidatos[siguiente].video_id);
        return siguiente;
      }
      setVideoId(null);
      return i;
    });
  }, [candidatos]);

  // Registrar/actualizar la fuente activa del PlayerContext cada vez que
  // arranca un video nuevo — nunca dos fuentes sonando a la vez, y el resto
  // de la app (mini-player, resaltado en la lista) se entera solo.
  useEffect(() => {
    if (!videoId || !trackActual) return;
    player.activarFuente(
      {
        tipo: 'youtube',
        id: `${slug}:${trackActual.posicion}`,
        titulo: trackActual.mix_name ? `${trackActual.nombre} (${trackActual.mix_name})` : trackActual.nombre,
        artista: (trackActual.artistas ?? []).join(', '),
        coverUrl: coverUrlYoutube(videoId),
        duracionSeg: null,
      },
      {
        pausar: () => setReproduciendo(false),
        reanudar: () => setReproduciendo(true),
        detener: () => { setReproduciendo(false); onCerrar(); },
      },
    );
    // Deliberado: solo re-registrar cuando cambia el video, no en cada
    // render (evitaría cortar/reactivar la fuente sin necesidad).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId, slug, trackActual?.posicion]);

  // Progreso REAL de YouTube (nunca placeholder ni timer propio — el
  // escritorio tuvo el bug exacto de progreso congelado con YouTube hasta
  // corregirlo; acá se define bien desde el arranque).
  useEffect(() => {
    if (!reproduciendo || !videoId) return;
    const id = setInterval(async () => {
      try {
        const [seg, dur] = await Promise.all([
          playerRef.current?.getCurrentTime() ?? Promise.resolve(0),
          playerRef.current?.getDuration() ?? Promise.resolve(0),
        ]);
        player.reportarProgreso(seg, dur || undefined);
      } catch {
        // El iframe puede no estar listo todavía — se reintenta en el próximo tick.
      }
    }, 1000);
    return () => clearInterval(id);
  }, [reproduciendo, videoId, player]);

  function onChangeState(estado: PLAYER_STATES) {
    if (estado === PLAYER_STATES.ENDED) {
      irASiguiente();
    } else if (estado === PLAYER_STATES.PLAYING) {
      setReproduciendo(true);
      player.reportarReproduciendo(true);
    } else if (estado === PLAYER_STATES.PAUSED) {
      setReproduciendo(false);
      player.reportarReproduciendo(false);
    }
  }

  function onError() {
    probarSiguienteCandidato();
  }

  function abrirEnYoutube() {
    const candidato = candidatos[candidatoIdx] ?? candidatos[0];
    const url = candidato
      ? `https://www.youtube.com/watch?v=${candidato.video_id}`
      : `https://www.youtube.com/results?search_query=${encodeURIComponent(
          `${(trackActual?.artistas ?? []).join(' ')} ${trackActual?.nombre ?? ''}`
        )}`;
    Linking.openURL(url);
  }

  if (!trackActual) return null;

  return (
    <View style={styles.contenedor}>
      {videoId ? (
        <YoutubeIframe
          ref={playerRef}
          height={ALTO_PLAYER}
          videoId={videoId}
          play={reproduciendo}
          onChangeState={onChangeState}
          onError={onError}
          forceAndroidAutoplay
        />
      ) : (
        <View style={[styles.sinVideo, { height: ALTO_PLAYER }]}>
          <Text style={styles.sinVideoTexto}>
            {cargando ? 'Buscando preview…' : sinCandidatos ? 'Sin preview disponible para este track' : 'No se pudo reproducir acá'}
          </Text>
          {!cargando ? (
            <TouchableOpacity style={styles.botonYoutube} onPress={abrirEnYoutube}>
              <Ionicons name="logo-youtube" size={16} color={colors.textPrimary} />
              <Text style={styles.botonYoutubeTexto}>Abrir en YouTube</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      )}

      <View style={styles.info}>
        <Text style={styles.titulo} numberOfLines={1}>
          {trackActual.mix_name ? `${trackActual.nombre} (${trackActual.mix_name})` : trackActual.nombre}
        </Text>
        <Text style={styles.artista} numberOfLines={1}>{(trackActual.artistas ?? []).join(', ')}</Text>
      </View>

      <View style={styles.controles}>
        <TouchableOpacity style={styles.boton} onPress={irAAnterior}>
          <Ionicons name="play-skip-back" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.boton}
          onPress={() => setReproduciendo(r => !r)}
          disabled={!videoId}
        >
          <Ionicons name={reproduciendo ? 'pause' : 'play'} size={26} color={videoId ? colors.cyan : colors.textMuted} />
        </TouchableOpacity>
        <TouchableOpacity style={styles.boton} onPress={irASiguiente}>
          <Ionicons name="play-skip-forward" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={{ flex: 1 }} />
        <TouchableOpacity style={styles.boton} onPress={onCerrar}>
          <Ionicons name="close" size={22} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    backgroundColor: colors.bgPanel,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  sinVideo: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    backgroundColor: '#000',
  },
  sinVideoTexto: {
    color: colors.textSecondary,
    fontSize: typography.size.sm,
  },
  botonYoutube: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.bgElevated,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  botonYoutubeTexto: {
    color: colors.textPrimary,
    fontSize: typography.size.sm,
    fontWeight: '600',
  },
  info: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
  },
  titulo: {
    color: colors.cyan,
    fontSize: typography.size.md,
    fontWeight: '700',
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.sm,
    marginTop: 2,
  },
  controles: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  boton: {
    padding: spacing.xs,
  },
});
