import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';

import { cacheBiblioteca, traerBibliotecaCompleta, type TrackBiblioteca } from '../../../../../api/mibiblioteca';
import { aportarTracks } from '../../../../../api/playlistsCompartidas';
import { colorParaGenero, colors, radius, spacing, typography } from '../../../../../theme';

/** Aportar a una playlist compartida: solo viajan los DATOS del track (nunca
 * el audio) — el otro DJ lo escucha local si lo tiene, o por YouTube si no. */
export default function AportarTracks() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [tracks, setTracks] = useState<TrackBiblioteca[] | null>(null);
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set());
  const [busqueda, setBusqueda] = useState('');
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let vivo = true;
    const yaCargada = cacheBiblioteca.porId.size > 0
      ? Promise.resolve(Array.from(cacheBiblioteca.porId.values()))
      : traerBibliotecaCompleta();
    yaCargada.then(datos => vivo && setTracks(datos));
    return () => { vivo = false; };
  }, []);

  const filtrados = useMemo(() => {
    if (!tracks) return [];
    const q = busqueda.trim().toLowerCase();
    if (!q) return tracks;
    return tracks.filter(t => `${t.artista ?? ''} ${t.titulo ?? ''}`.toLowerCase().includes(q));
  }, [tracks, busqueda]);

  function toggle(idTrack: number) {
    setSeleccionados(prev => {
      const copia = new Set(prev);
      if (copia.has(idTrack)) copia.delete(idTrack); else copia.add(idTrack);
      return copia;
    });
  }

  async function confirmar() {
    if (seleccionados.size === 0 || !tracks) {
      router.back();
      return;
    }
    setGuardando(true);
    try {
      const elegidos = tracks.filter(t => seleccionados.has(t.id));
      await aportarTracks(id!, elegidos.map(t => ({
        artista: t.artista ?? '', titulo: t.titulo ?? '', sello: t.sello, anio: t.anio,
        bpm: t.bpm, key: t.key, camelot: t.camelot, duracion_seg: t.duracion_seg,
        genero: t.genero, subgenero: t.subgenero,
      })));
      router.back();
    } catch (e) {
      Alert.alert('No se pudo aportar', String(e));
    } finally {
      setGuardando(false);
    }
  }

  if (!tracks) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  return (
    <View style={styles.contenedor}>
      <TextInput
        style={styles.buscador}
        placeholder="Buscar en tu biblioteca…"
        placeholderTextColor={colors.textMuted}
        value={busqueda}
        onChangeText={setBusqueda}
        autoCapitalize="none"
      />

      <FlatList
        data={filtrados}
        keyExtractor={t => String(t.id)}
        renderItem={({ item }) => {
          const marcado = seleccionados.has(item.id);
          return (
            <TouchableOpacity style={styles.fila} onPress={() => toggle(item.id)}>
              <View style={[styles.indicadorGenero, { backgroundColor: colorParaGenero(item.genero) }]} />
              <View style={styles.info}>
                <Text style={styles.titulo} numberOfLines={1}>{item.titulo || '(sin título)'}</Text>
                <Text style={styles.artista} numberOfLines={1}>{item.artista || '(sin artista)'}</Text>
              </View>
              <Ionicons
                name={marcado ? 'checkmark-circle' : 'ellipse-outline'}
                size={22}
                color={marcado ? colors.cyan : colors.textMuted}
              />
            </TouchableOpacity>
          );
        }}
      />

      <TouchableOpacity style={styles.botonConfirmar} onPress={confirmar} disabled={guardando}>
        {guardando ? (
          <ActivityIndicator color={colors.bgBase} />
        ) : (
          <Text style={styles.botonConfirmarTexto}>
            {seleccionados.size > 0 ? `Aportar (${seleccionados.size})` : 'Cerrar'}
          </Text>
        )}
      </TouchableOpacity>
    </View>
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
  },
  buscador: {
    backgroundColor: '#1A1A1C',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.09)',
    borderRadius: radius.sm,
    color: colors.textPrimary,
    margin: spacing.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.size.sm,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  indicadorGenero: {
    width: 4,
    height: 28,
    borderRadius: 2,
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
    marginTop: 1,
  },
  botonConfirmar: {
    backgroundColor: colors.cyan,
    margin: spacing.lg,
    borderRadius: radius.sm,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  botonConfirmarTexto: {
    color: colors.bgBase,
    fontWeight: '700',
    fontSize: typography.size.md,
  },
});
