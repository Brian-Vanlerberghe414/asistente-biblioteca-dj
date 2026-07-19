import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import React, { useCallback, useLayoutEffect, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { cacheBiblioteca, traerBibliotecaCompleta, type TrackBiblioteca } from '../../../api/mibiblioteca';
import { guardarPlaylist, obtenerMisPlaylists } from '../../../api/playlists';
import { useEsSonando } from '../../../context/PlayerContext';
import { colorParaGenero, colors, radius, spacing, typography } from '../../../theme';

export default function DetallePlaylistPropia() {
  const { nombre } = useLocalSearchParams<{ nombre: string }>();
  const navigation = useNavigation();
  const router = useRouter();
  const [ids, setIds] = useState<number[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useLayoutEffect(() => {
    navigation.setOptions({ title: nombre ?? 'Playlist' });
  }, [navigation, nombre]);

  const cargar = useCallback(async () => {
    if (!nombre) return;
    try {
      const [playlists] = await Promise.all([
        obtenerMisPlaylists(),
        cacheBiblioteca.porId.size === 0 ? traerBibliotecaCompleta() : Promise.resolve(),
      ]);
      const playlist = playlists.find(p => p.nombre === nombre);
      if (!playlist) {
        setError('Esta playlist ya no existe.');
        return;
      }
      setIds(playlist.reglas.ids);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, [nombre]);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function persistir(nuevosIds: number[]) {
    setIds(nuevosIds);
    setGuardando(true);
    try {
      await guardarPlaylist(nombre!, nuevosIds);
    } catch (e) {
      Alert.alert('No se pudo guardar el cambio', String(e));
    } finally {
      setGuardando(false);
    }
  }

  function quitar(id: number) {
    if (!ids) return;
    persistir(ids.filter(i => i !== id));
  }

  function mover(index: number, delta: number) {
    if (!ids) return;
    const destino = index + delta;
    if (destino < 0 || destino >= ids.length) return;
    const copia = [...ids];
    [copia[index], copia[destino]] = [copia[destino], copia[index]];
    persistir(copia);
  }

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>{error}</Text>
      </View>
    );
  }

  if (!ids) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  const tracks = ids.map(id => cacheBiblioteca.porId.get(id)).filter((t): t is TrackBiblioteca => !!t);

  return (
    <View style={styles.contenedor}>
      <TouchableOpacity
        style={styles.botonAgregar}
        onPress={() => router.push(`/playlists/agregar/${encodeURIComponent(nombre!)}`)}
      >
        <Ionicons name="add" size={20} color={colors.cyan} />
        <Text style={styles.botonAgregarTexto}>Agregar tracks</Text>
      </TouchableOpacity>

      {guardando ? <Text style={styles.guardando}>Guardando…</Text> : null}

      <FlatList
        data={tracks}
        keyExtractor={t => String(t.id)}
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text style={styles.error}>Todavía no tiene tracks.</Text>
          </View>
        }
        renderItem={({ item, index }) => (
          <FilaTrack
            track={item}
            onQuitar={() => quitar(item.id)}
            onSubir={index > 0 ? () => mover(index, -1) : undefined}
            onBajar={index < tracks.length - 1 ? () => mover(index, 1) : undefined}
          />
        )}
      />
    </View>
  );
}

function FilaTrack({
  track, onQuitar, onSubir, onBajar,
}: { track: TrackBiblioteca; onQuitar: () => void; onSubir?: () => void; onBajar?: () => void }) {
  const sonando = useEsSonando('local', track.r2_key ?? String(track.id));
  return (
    <View style={styles.fila}>
      <View style={[styles.indicadorGenero, { backgroundColor: colorParaGenero(track.genero) }]} />
      <View style={styles.info}>
        <Text style={[styles.titulo, sonando && styles.tituloSonando]} numberOfLines={1}>
          {track.titulo || '(sin título)'}
        </Text>
        <Text style={styles.artista} numberOfLines={1}>{track.artista || '(sin artista)'}</Text>
      </View>
      <TouchableOpacity style={styles.botonFila} onPress={onSubir} disabled={!onSubir}>
        <Ionicons name="chevron-up" size={18} color={onSubir ? colors.textSecondary : colors.line} />
      </TouchableOpacity>
      <TouchableOpacity style={styles.botonFila} onPress={onBajar} disabled={!onBajar}>
        <Ionicons name="chevron-down" size={18} color={onBajar ? colors.textSecondary : colors.line} />
      </TouchableOpacity>
      <TouchableOpacity style={styles.botonFila} onPress={onQuitar}>
        <Ionicons name="close" size={18} color={colors.textMuted} />
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
    padding: spacing.xl,
  },
  error: {
    color: colors.textSecondary,
    fontSize: typography.size.md,
    textAlign: 'center',
  },
  botonAgregar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    margin: spacing.lg,
    alignSelf: 'flex-start',
    backgroundColor: colors.bgElevated,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.line,
  },
  botonAgregarTexto: {
    color: colors.cyan,
    fontWeight: '600',
    fontSize: typography.size.sm,
  },
  guardando: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.xs,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.xs,
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
    marginRight: spacing.xs,
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
  botonFila: {
    padding: 4,
  },
});
