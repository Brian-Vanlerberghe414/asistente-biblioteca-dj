import React, { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { FlashList } from '@shopify/flash-list';

import { type AudioPersonal, traerColeccionCompleta } from '../../api/audio';
import { useEsSonando } from '../../context/PlayerContext';
import { useAudioPlayer } from '../../hooks/useAudioPlayer';
import { colors, spacing, typography } from '../../theme';

export default function MiMusica() {
  const [coleccion, setColeccion] = useState<AudioPersonal[] | null>(null);
  const [cantidadCargada, setCantidadCargada] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');

  useEffect(() => {
    let vivo = true;
    traerColeccionCompleta(n => vivo && setCantidadCargada(n))
      .then(datos => vivo && setColeccion(datos))
      .catch(e => vivo && setError(String(e)));
    return () => { vivo = false; };
  }, []);

  const filtrada = useMemo(() => {
    if (!coleccion) return [];
    const q = busqueda.trim().toLowerCase();
    if (!q) return coleccion;
    return coleccion.filter(a => `${a.artista ?? ''} ${a.titulo ?? ''}`.toLowerCase().includes(q));
  }, [coleccion, busqueda]);

  const { reproducirIndice } = useAudioPlayer(filtrada);

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudo cargar tu música.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
      </View>
    );
  }

  if (!coleccion) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
        <Text style={styles.cargandoTexto}>
          {cantidadCargada > 0 ? `Cargando… ${cantidadCargada}` : 'Cargando…'}
        </Text>
      </View>
    );
  }

  if (coleccion.length === 0) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>Todavía no subiste música con "☁ Backup en la nube" desde el escritorio.</Text>
      </View>
    );
  }

  return (
    <View style={styles.contenedor}>
      <TextInput
        style={styles.buscador}
        placeholder="Buscar en tu música…"
        placeholderTextColor={colors.textMuted}
        value={busqueda}
        onChangeText={setBusqueda}
        autoCapitalize="none"
      />
      <FlashList
        data={filtrada}
        keyExtractor={item => item.r2_key}
        renderItem={({ item, index }) => (
          <FilaAudio track={item} onPress={() => reproducirIndice(index)} />
        )}
      />
    </View>
  );
}

function FilaAudio({ track, onPress }: { track: AudioPersonal; onPress: () => void }) {
  const sonando = useEsSonando('local', track.r2_key);
  return (
    <TouchableOpacity style={styles.fila} onPress={onPress}>
      <View style={styles.info}>
        <Text style={[styles.titulo, sonando && styles.tituloSonando]} numberOfLines={1}>
          {track.titulo || '(sin título)'}
        </Text>
        <Text style={styles.artista} numberOfLines={1}>{track.artista || '(sin artista)'}</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flex: 1,
    backgroundColor: colors.bgBase,
  },
  centrado: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
    gap: spacing.sm,
  },
  cargandoTexto: {
    color: colors.textMuted,
    fontSize: typography.size.sm,
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
  },
  buscador: {
    backgroundColor: '#1A1A1C',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.09)',
    borderRadius: 7,
    color: colors.textPrimary,
    margin: spacing.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.size.sm,
  },
  fila: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  info: {
    flex: 1,
  },
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.sm,
    fontWeight: '600',
  },
  tituloSonando: {
    color: colors.cyan,
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    marginTop: 1,
  },
});
