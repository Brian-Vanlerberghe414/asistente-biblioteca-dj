import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';

import { cacheBiblioteca, traerBibliotecaCompleta, type TrackBiblioteca } from '../../../../api/mibiblioteca';
import { guardarPlaylist, obtenerMisPlaylists } from '../../../../api/playlists';
import { colorParaGenero, colors, radius, spacing, typography } from '../../../../theme';

export default function AgregarTracks() {
  const { nombre } = useLocalSearchParams<{ nombre: string }>();
  const router = useRouter();
  const [tracks, setTracks] = useState<TrackBiblioteca[] | null>(null);
  const [idsExistentes, setIdsExistentes] = useState<Set<number>>(new Set());
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set());
  const [busqueda, setBusqueda] = useState('');
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let vivo = true;
    Promise.all([
      cacheBiblioteca.porId.size === 0 ? traerBibliotecaCompleta() : Promise.resolve(Array.from(cacheBiblioteca.porId.values())),
      obtenerMisPlaylists(),
    ]).then(([datos, playlists]) => {
      if (!vivo) return;
      setTracks(datos.length ? datos : Array.from(cacheBiblioteca.porId.values()));
      const actual = playlists.find(p => p.nombre === nombre);
      setIdsExistentes(new Set(actual?.reglas.ids ?? []));
    });
    return () => { vivo = false; };
  }, [nombre]);

  const filtrados = useMemo(() => {
    if (!tracks) return [];
    const q = busqueda.trim().toLowerCase();
    if (!q) return tracks;
    return tracks.filter(t => `${t.artista ?? ''} ${t.titulo ?? ''}`.toLowerCase().includes(q));
  }, [tracks, busqueda]);

  function toggle(id: number) {
    setSeleccionados(prev => {
      const copia = new Set(prev);
      if (copia.has(id)) copia.delete(id); else copia.add(id);
      return copia;
    });
  }

  async function confirmar() {
    if (seleccionados.size === 0) {
      router.back();
      return;
    }
    setGuardando(true);
    try {
      const nuevos = [...idsExistentes, ...Array.from(seleccionados).filter(id => !idsExistentes.has(id))];
      await guardarPlaylist(nombre!, nuevos);
      router.back();
    } catch (e) {
      Alert.alert('No se pudo agregar', String(e));
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
        placeholder="Buscar artista o título…"
        placeholderTextColor={colors.textMuted}
        value={busqueda}
        onChangeText={setBusqueda}
        autoCapitalize="none"
      />

      <FlatList
        data={filtrados}
        keyExtractor={t => String(t.id)}
        renderItem={({ item }) => {
          const yaEsta = idsExistentes.has(item.id);
          const marcado = seleccionados.has(item.id);
          return (
            <TouchableOpacity
              style={styles.fila}
              disabled={yaEsta}
              onPress={() => toggle(item.id)}
            >
              <View style={[styles.indicadorGenero, { backgroundColor: colorParaGenero(item.genero) }]} />
              <View style={styles.info}>
                <Text style={styles.titulo} numberOfLines={1}>{item.titulo || '(sin título)'}</Text>
                <Text style={styles.artista} numberOfLines={1}>{item.artista || '(sin artista)'}</Text>
              </View>
              {yaEsta ? (
                <Text style={styles.yaAgregado}>Ya está</Text>
              ) : (
                <Ionicons
                  name={marcado ? 'checkmark-circle' : 'ellipse-outline'}
                  size={22}
                  color={marcado ? colors.cyan : colors.textMuted}
                />
              )}
            </TouchableOpacity>
          );
        }}
      />

      <TouchableOpacity style={styles.botonConfirmar} onPress={confirmar} disabled={guardando}>
        {guardando ? (
          <ActivityIndicator color={colors.bgBase} />
        ) : (
          <Text style={styles.botonConfirmarTexto}>
            {seleccionados.size > 0 ? `Agregar (${seleccionados.size})` : 'Cerrar'}
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
  yaAgregado: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
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
