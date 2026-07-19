import { useLocalSearchParams, useNavigation } from 'expo-router';
import React, { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, FlatList, Image, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';

import { type ChartTrack, obtenerChart, obtenerNovedades } from '../../../api/charts';
import { YoutubeRadioPlayer } from '../../../components/YoutubeRadioPlayer';
import { useEsSonando } from '../../../context/PlayerContext';
import { colors, radius, spacing, typography } from '../../../theme';

export default function DetalleChart() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const navigation = useNavigation();
  const [tracks, setTracks] = useState<ChartTrack[] | null>(null);
  const [idsNuevos, setIdsNuevos] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [sesion, setSesion] = useState<{ posicionInicial: number; clave: number } | null>(null);

  useLayoutEffect(() => {
    navigation.setOptions({ title: slug ?? 'Top 100' });
  }, [navigation, slug]);

  useEffect(() => {
    if (!slug) return;
    let vivo = true;
    Promise.all([obtenerChart(slug, 100), obtenerNovedades(slug)])
      .then(([chart, novedades]) => {
        if (!vivo) return;
        setTracks(chart);
        setIdsNuevos(new Set(novedades.map(n => n.beatport_id)));
      })
      .catch(e => vivo && setError(String(e)));
    return () => { vivo = false; };
  }, [slug]);

  const total = tracks?.length ?? 0;
  const nuevos = idsNuevos.size;

  const encabezado = useMemo(() => {
    if (!tracks) return null;
    return (
      <View style={styles.resumen}>
        <Text style={styles.resumenTexto}>{total} tracks{nuevos > 0 ? ` · ${nuevos} nuevos` : ''}</Text>
      </View>
    );
  }, [tracks, total, nuevos]);

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudo cargar el chart.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
      </View>
    );
  }

  if (!tracks) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  return (
    <FlatList
      style={styles.lista}
      data={tracks}
      keyExtractor={item => `${item.beatport_id}-${item.genero_slug}`}
      ListHeaderComponent={
        <>
          {encabezado}
          {sesion && slug ? (
            <YoutubeRadioPlayer
              key={sesion.clave}
              slug={slug}
              tracks={tracks}
              posicionInicial={sesion.posicionInicial}
              onCerrar={() => setSesion(null)}
            />
          ) : null}
        </>
      }
      renderItem={({ item }) => (
        <FilaTrack
          track={item}
          esNuevo={idsNuevos.has(item.beatport_id)}
          onPress={() => setSesion(s => ({ posicionInicial: item.posicion, clave: (s?.clave ?? 0) + 1 }))}
          slug={slug ?? ''}
        />
      )}
    />
  );
}

function FilaTrack({
  track, esNuevo, onPress, slug,
}: { track: ChartTrack; esNuevo: boolean; onPress: () => void; slug: string }) {
  const artistas = (track.artistas ?? []).join(', ');
  const sonando = useEsSonando('youtube', `${slug}:${track.posicion}`);
  const duracion = track.duracion_ms
    ? `${Math.floor(track.duracion_ms / 60000)}:${String(Math.round((track.duracion_ms % 60000) / 1000)).padStart(2, '0')}`
    : null;

  return (
    <TouchableOpacity style={styles.fila} onPress={onPress}>
      <Text style={styles.posicion}>{track.posicion}</Text>
      {track.image_url ? (
        <Image source={{ uri: track.image_url }} style={styles.caratula} />
      ) : (
        <View style={[styles.caratula, styles.caratulaVacia]} />
      )}
      <View style={styles.info}>
        <View style={styles.filaTitulo}>
          <Text style={[styles.titulo, sonando && styles.tituloSonando]} numberOfLines={1}>
            {track.nombre}{track.mix_name ? ` (${track.mix_name})` : ''}
          </Text>
          {esNuevo ? <View style={styles.badgeNuevo}><Text style={styles.badgeNuevoTexto}>NUEVO</Text></View> : null}
        </View>
        <Text style={styles.artista} numberOfLines={1}>{artistas}</Text>
        <Text style={styles.metadata} numberOfLines={1}>
          {[track.sello, track.bpm ? `${track.bpm} BPM` : null, track.key, duracion].filter(Boolean).join(' · ')}
        </Text>
      </View>
    </TouchableOpacity>
  );
}

const ALTO_CARATULA = 48;

const styles = StyleSheet.create({
  lista: {
    flex: 1,
    backgroundColor: colors.bgBase,
  },
  centrado: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  error: {
    color: colors.textSecondary,
    fontSize: typography.size.md,
    textAlign: 'center',
  },
  errorDetalle: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
  resumen: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  resumenTexto: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  posicion: {
    width: 24,
    color: colors.textMuted,
    fontSize: typography.size.sm,
    fontWeight: '700',
    textAlign: 'center',
  },
  caratula: {
    width: ALTO_CARATULA,
    height: ALTO_CARATULA,
    borderRadius: radius.sm,
  },
  caratulaVacia: {
    backgroundColor: colors.bgPanel,
  },
  info: {
    flex: 1,
  },
  filaTitulo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.sm,
    fontWeight: '600',
    flexShrink: 1,
  },
  tituloSonando: {
    color: colors.cyan,
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    marginTop: 1,
  },
  metadata: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    marginTop: 1,
  },
  badgeNuevo: {
    backgroundColor: 'rgba(0,229,255,0.15)',
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  badgeNuevoTexto: {
    color: colors.cyan,
    fontSize: 9,
    fontWeight: '700',
  },
});
