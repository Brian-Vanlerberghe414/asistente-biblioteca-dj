import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { Image, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { usePlayer } from '../context/PlayerContext';
import { colors, radius, spacing, typography } from '../theme';

/** Mini-player persistente (encima de los tabs) — vive acá, a nivel raíz de
 * `(tabs)/_layout.tsx`, para seguir sonando y visible al navegar entre
 * tabs. Se alimenta 100% de `PlayerContext`: no sabe ni le importa si la
 * fuente activa es YouTube o audio local, solo refleja `nowPlaying`. */
export function MiniPlayer() {
  const { nowPlaying, pausar, reanudar, detener } = usePlayer();

  if (!nowPlaying) return null;

  const progresoPct = nowPlaying.duracionSeg
    ? Math.min(100, (nowPlaying.progresoSeg / nowPlaying.duracionSeg) * 100)
    : 0;

  return (
    <View style={styles.contenedor}>
      <View style={styles.barraProgreso}>
        <View style={[styles.barraProgresoRelleno, { width: `${progresoPct}%` }]} />
      </View>
      <View style={styles.fila}>
        {nowPlaying.coverUrl ? (
          <Image source={{ uri: nowPlaying.coverUrl }} style={styles.caratula} />
        ) : (
          <View style={[styles.caratula, styles.caratulaVacia]} />
        )}
        <View style={styles.info}>
          <Text style={styles.titulo} numberOfLines={1}>{nowPlaying.titulo}</Text>
          {nowPlaying.artista ? (
            <Text style={styles.artista} numberOfLines={1}>{nowPlaying.artista}</Text>
          ) : null}
        </View>
        <TouchableOpacity
          style={styles.boton}
          onPress={() => (nowPlaying.reproduciendo ? pausar() : reanudar())}
        >
          <Ionicons
            name={nowPlaying.reproduciendo ? 'pause' : 'play'}
            size={22}
            color={colors.textPrimary}
          />
        </TouchableOpacity>
        <TouchableOpacity style={styles.boton} onPress={detener}>
          <Ionicons name="close" size={20} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const ALTO_CARATULA = 40;

const styles = StyleSheet.create({
  contenedor: {
    backgroundColor: colors.bgElevated,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
  barraProgreso: {
    height: 2,
    backgroundColor: 'rgba(255,255,255,0.08)',
  },
  barraProgresoRelleno: {
    height: 2,
    backgroundColor: colors.cyan,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
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
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.sm,
    fontWeight: '600',
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
  },
  boton: {
    padding: spacing.xs,
  },
});
