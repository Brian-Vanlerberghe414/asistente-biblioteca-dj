import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useRef, useState } from 'react';
import { Linking, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import YoutubeIframe, { PLAYER_STATES, type YoutubeIframeRef } from 'react-native-youtube-iframe';

import { buscarCandidatosYoutube, type CandidatoYoutube } from '../api/charts';
import { coverUrlYoutube, usePlayer } from '../context/PlayerContext';
import { colors, radius, spacing, typography } from '../theme';

interface Props {
  id: string;
  artista: string;
  titulo: string;
  mixName?: string | null;
  onCerrar: () => void;
}

/** Preview de UN track suelto (no forma parte de un chart con posiciones) —
 * usado por Playlists ("escuchar un aporte", mismo player global que
 * Charts). A diferencia de `YoutubeRadioPlayer` no avanza solo al
 * siguiente: es solo play/pause/cerrar de ESTE track. */
export function YoutubeTrackPreview({ id, artista, titulo, mixName, onCerrar }: Props) {
  const player = usePlayer();
  const playerRef = useRef<YoutubeIframeRef>(null);
  const [candidatos, setCandidatos] = useState<CandidatoYoutube[]>([]);
  const [candidatoIdx, setCandidatoIdx] = useState(0);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [reproduciendo, setReproduciendo] = useState(true);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    setCargando(true);
    buscarCandidatosYoutube(artista, titulo, mixName)
      .then(c => {
        if (!vivo) return;
        setCandidatos(c);
        setVideoId(c[0]?.video_id ?? null);
      })
      .finally(() => vivo && setCargando(false));
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!videoId) return;
    player.activarFuente(
      { tipo: 'youtube', id, titulo: mixName ? `${titulo} (${mixName})` : titulo, artista, coverUrl: coverUrlYoutube(videoId), duracionSeg: null },
      {
        pausar: () => setReproduciendo(false),
        reanudar: () => setReproduciendo(true),
        detener: () => { setReproduciendo(false); onCerrar(); },
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]);

  useEffect(() => {
    if (!reproduciendo || !videoId) return;
    const t = setInterval(async () => {
      try {
        const [seg, dur] = await Promise.all([
          playerRef.current?.getCurrentTime() ?? Promise.resolve(0),
          playerRef.current?.getDuration() ?? Promise.resolve(0),
        ]);
        player.reportarProgreso(seg, dur || undefined);
      } catch { /* iframe todavía no listo */ }
    }, 1000);
    return () => clearInterval(t);
  }, [reproduciendo, videoId, player]);

  function onError() {
    setCandidatoIdx(i => {
      const siguiente = i + 1;
      if (siguiente < candidatos.length) {
        setVideoId(candidatos[siguiente].video_id);
        return siguiente;
      }
      setVideoId(null);
      return i;
    });
  }

  function abrirEnYoutube() {
    const candidato = candidatos[candidatoIdx];
    const url = candidato
      ? `https://www.youtube.com/watch?v=${candidato.video_id}`
      : `https://www.youtube.com/results?search_query=${encodeURIComponent(`${artista} ${titulo}`)}`;
    Linking.openURL(url);
  }

  return (
    <View style={styles.contenedor}>
      {videoId ? (
        <YoutubeIframe
          ref={playerRef}
          height={200}
          videoId={videoId}
          play={reproduciendo}
          onChangeState={(e: PLAYER_STATES) => {
            if (e === PLAYER_STATES.PLAYING) { setReproduciendo(true); player.reportarReproduciendo(true); }
            if (e === PLAYER_STATES.PAUSED || e === PLAYER_STATES.ENDED) { setReproduciendo(false); player.reportarReproduciendo(false); }
          }}
          onError={onError}
          forceAndroidAutoplay
        />
      ) : (
        <View style={[styles.sinVideo, { height: 200 }]}>
          <Text style={styles.sinVideoTexto}>
            {cargando ? 'Buscando preview…' : 'Sin preview disponible'}
          </Text>
          {!cargando ? (
            <TouchableOpacity style={styles.botonYoutube} onPress={abrirEnYoutube}>
              <Ionicons name="logo-youtube" size={16} color={colors.textPrimary} />
              <Text style={styles.botonYoutubeTexto}>Abrir en YouTube</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      )}
      <View style={styles.fila}>
        <Text style={styles.titulo} numberOfLines={1}>{mixName ? `${titulo} (${mixName})` : titulo}</Text>
        <TouchableOpacity onPress={onCerrar} hitSlop={8}>
          <Ionicons name="close" size={20} color={colors.textSecondary} />
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
  fila: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  titulo: {
    color: colors.cyan,
    fontSize: typography.size.sm,
    fontWeight: '700',
    flex: 1,
    marginRight: spacing.sm,
  },
});
