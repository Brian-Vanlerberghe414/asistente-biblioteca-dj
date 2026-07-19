import { Ionicons } from '@expo/vector-icons';
import { FlashList } from '@shopify/flash-list';
import { useRouter } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';

import { traerBibliotecaCompleta, type TrackBiblioteca } from '../../../api/mibiblioteca';
import { cargarUnificaciones, mostrar } from '../../../api/unificaciones';
import { ModalAgregarAPlaylist } from '../../../components/ModalAgregarAPlaylist';
import { useEsSonando } from '../../../context/PlayerContext';
import { colorParaGenero, colors, radius, spacing, typography } from '../../../theme';

const TODOS = 'Todos';

const DIACRITICOS = new RegExp('[̀-ͯ]', 'g');

function normalizar(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(DIACRITICOS, '');
}

export default function Biblioteca() {
  const router = useRouter();
  const [tracks, setTracks] = useState<TrackBiblioteca[] | null>(null);
  const [cantidadCargada, setCantidadCargada] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [generoActivo, setGeneroActivo] = useState(TODOS);
  const [, forzarRender] = useState(0);
  const [trackParaAgregar, setTrackParaAgregar] = useState<number | null>(null);

  useEffect(() => {
    let vivo = true;
    cargarUnificaciones().then(() => vivo && forzarRender(n => n + 1));
    traerBibliotecaCompleta(n => vivo && setCantidadCargada(n))
      .then(datos => vivo && setTracks(datos))
      .catch(e => vivo && setError(String(e)));
    return () => { vivo = false; };
  }, []);

  const generosDisponibles = useMemo(() => {
    if (!tracks) return [TODOS];
    const vistos = new Set<string>();
    for (const t of tracks) {
      const display = mostrar(t.genero, t.subgenero);
      if (display) vistos.add(display);
    }
    return [TODOS, ...Array.from(vistos).sort((a, b) => a.localeCompare(b))];
  }, [tracks]);

  const tracksFiltrados = useMemo(() => {
    if (!tracks) return [];
    const q = normalizar(busqueda.trim());
    return tracks.filter(t => {
      if (generoActivo !== TODOS && mostrar(t.genero, t.subgenero) !== generoActivo) return false;
      if (!q) return true;
      const texto = normalizar(`${t.artista ?? ''} ${t.titulo ?? ''}`);
      return texto.includes(q);
    });
  }, [tracks, busqueda, generoActivo]);

  const onPressTrack = useCallback((t: TrackBiblioteca) => {
    router.push(`/biblioteca/${t.id}`);
  }, [router]);

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudo cargar tu biblioteca.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
      </View>
    );
  }

  if (!tracks) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
        <Text style={styles.cargandoTexto}>
          {cantidadCargada > 0 ? `Cargando… ${cantidadCargada} tracks` : 'Cargando…'}
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.contenedor}>
      <View style={styles.buscador}>
        <TextInput
          style={styles.buscadorInput}
          placeholder="Buscar artista o título…"
          placeholderTextColor={colors.textMuted}
          value={busqueda}
          onChangeText={setBusqueda}
          autoCapitalize="none"
        />
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chips} contentContainerStyle={{ gap: spacing.xs }}>
        {generosDisponibles.map(g => (
          <TouchableOpacity
            key={g}
            style={[styles.chip, generoActivo === g && styles.chipActivo]}
            onPress={() => setGeneroActivo(g)}
          >
            <Text style={[styles.chipTexto, generoActivo === g && styles.chipTextoActivo]}>{g}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <Text style={styles.contador}>{tracksFiltrados.length} de {tracks.length} tracks</Text>

      <FlashList
        data={tracksFiltrados}
        keyExtractor={item => String(item.id)}
        renderItem={({ item }) => (
          <FilaTrack
            track={item}
            onPress={() => onPressTrack(item)}
            onAgregarAPlaylist={() => setTrackParaAgregar(item.id)}
          />
        )}
      />

      <ModalAgregarAPlaylist
        visible={trackParaAgregar !== null}
        trackId={trackParaAgregar}
        onCerrar={() => setTrackParaAgregar(null)}
      />
    </View>
  );
}

function FilaTrack({
  track, onPress, onAgregarAPlaylist,
}: { track: TrackBiblioteca; onPress: () => void; onAgregarAPlaylist: () => void }) {
  // Mismo id que usa Mi Música al activar esta fuente (Sesión 9): si el
  // track ya se subió a R2 (`r2_key`), es la clave estable entre tabs; si
  // no, cae al id de `mi_biblioteca` (nunca va a matchear sin r2_key, pero
  // mantiene el tipo consistente).
  const sonando = useEsSonando('local', track.r2_key ?? String(track.id));
  const display = mostrar(track.genero, track.subgenero);
  const colorGenero = colorParaGenero(track.genero);

  return (
    <TouchableOpacity style={styles.fila} onPress={onPress}>
      <View style={[styles.indicadorGenero, { backgroundColor: colorGenero }]} />
      <View style={styles.info}>
        <Text style={[styles.titulo, sonando && styles.tituloSonando]} numberOfLines={1}>
          {track.titulo || '(sin título)'}
        </Text>
        <Text style={styles.artista} numberOfLines={1}>{track.artista || '(sin artista)'}</Text>
      </View>
      {display ? (
        <View style={[styles.badge, { borderColor: colorGenero }]}>
          <Text style={[styles.badgeTexto, { color: colorGenero }]} numberOfLines={1}>{display}</Text>
        </View>
      ) : null}
      <View style={styles.metadata}>
        {track.bpm ? <Text style={styles.metadataTexto}>{Math.round(track.bpm)}</Text> : null}
        {track.camelot ? <Text style={styles.metadataTexto}>{track.camelot}</Text> : null}
      </View>
      <TouchableOpacity style={styles.botonAgregar} onPress={onAgregarAPlaylist} hitSlop={8}>
        <Ionicons name="add-circle-outline" size={20} color={colors.textMuted} />
      </TouchableOpacity>
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
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  buscadorInput: {
    backgroundColor: '#1A1A1C',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.09)',
    borderRadius: radius.sm,
    color: colors.textPrimary,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.size.sm,
  },
  chips: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    flexGrow: 0,
  },
  chip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: colors.bgElevated,
    borderWidth: 1,
    borderColor: colors.line,
  },
  chipActivo: {
    backgroundColor: 'rgba(0,229,255,0.14)',
    borderColor: colors.cyan,
  },
  chipTexto: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    fontWeight: '600',
  },
  chipTextoActivo: {
    color: colors.cyan,
  },
  contador: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xs,
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
    height: 32,
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
  tituloSonando: {
    color: colors.cyan,
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    marginTop: 1,
  },
  badge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    maxWidth: 110,
  },
  badgeTexto: {
    fontSize: 10,
    fontWeight: '700',
  },
  metadata: {
    alignItems: 'flex-end',
    minWidth: 34,
  },
  metadataTexto: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
  },
  botonAgregar: {
    paddingLeft: spacing.xs,
  },
});
