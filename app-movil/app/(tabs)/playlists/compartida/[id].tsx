import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';

import { useAuth } from '../../../../context/AuthContext';
import {
  borrarPlaylistCompartida, type DetallePlaylistCompartida, detallePlaylistCompartida,
  expulsarMiembro, quitarTrackCompartido, renombrarPlaylistCompartida, salirDePlaylist,
  type TrackCompartido,
} from '../../../../api/playlistsCompartidas';
import { ModalTexto } from '../../../../components/ModalTexto';
import { YoutubeTrackPreview } from '../../../../components/YoutubeTrackPreview';
import { useEsSonando } from '../../../../context/PlayerContext';
import { supabase } from '../../../../api/supabase';
import { colorParaGenero, colors, radius, spacing, typography } from '../../../../theme';

export default function DetallePlaylistCompartidaScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const navigation = useNavigation();
  const router = useRouter();
  const { session } = useAuth();
  const [detalle, setDetalle] = useState<DetallePlaylistCompartida | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refrescando, setRefrescando] = useState(false);
  const [modalRenombrar, setModalRenombrar] = useState(false);
  const [previewActivo, setPreviewActivo] = useState<string | null>(null);
  const salioRef = useRef(false);

  const cargar = useCallback(async (silencioso = false) => {
    if (!id) return;
    if (!silencioso) setError(null);
    try {
      const d = await detallePlaylistCompartida(id);
      setDetalle(d);
    } catch (e) {
      const texto = String(e);
      if (texto.includes('403') && !salioRef.current) {
        salioRef.current = true;
        Alert.alert('Ya no formás parte de esta playlist', 'Puede que el dueño te haya sacado.');
        router.back();
        return;
      }
      setError(texto);
    }
  }, [id, router]);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  useLayoutEffect(() => {
    navigation.setOptions({ title: detalle?.nombre ?? 'Playlist compartida' });
  }, [navigation, detalle?.nombre]);

  // Realtime: cualquier cambio en tracks/miembros/la playlist misma
  // refresca el detalle — fallback manual: pull-to-refresh (RefreshControl
  // abajo) para cuando la conexión de Realtime se cae.
  useEffect(() => {
    if (!id) return;
    const canal = supabase
      .channel(`playlist-compartida-${id}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'playlists_compartidas_tracks', filter: `playlist_id=eq.${id}` }, () => cargar(true))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'playlists_compartidas_miembros', filter: `playlist_id=eq.${id}` }, () => cargar(true))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'playlists_compartidas', filter: `id=eq.${id}` }, () => cargar(true))
      .subscribe();
    return () => { supabase.removeChannel(canal); };
  }, [id, cargar]);

  async function onRefrescar() {
    setRefrescando(true);
    await cargar(true);
    setRefrescando(false);
  }

  async function renombrar(nombreNuevo: string) {
    setModalRenombrar(false);
    if (!id) return;
    try {
      await renombrarPlaylistCompartida(id, nombreNuevo);
      cargar(true);
    } catch (e) {
      Alert.alert('No se pudo renombrar', String(e));
    }
  }

  async function quitar(track: TrackCompartido) {
    if (!id) return;
    try {
      await quitarTrackCompartido(id, track.id);
      cargar(true);
    } catch (e) {
      Alert.alert('No se pudo quitar', 'No tenés permiso para quitar este track.');
    }
  }

  function salir() {
    Alert.alert('¿Salir de esta playlist?', undefined, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Salir', style: 'destructive', onPress: async () => {
          try {
            await salirDePlaylist(id!);
            router.back();
          } catch (e) {
            Alert.alert('No se pudo salir', String(e));
          }
        },
      },
    ]);
  }

  function borrar() {
    Alert.alert('¿Borrar esta playlist?', 'Se borra para todos los miembros. No se puede deshacer.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Borrar', style: 'destructive', onPress: async () => {
          try {
            await borrarPlaylistCompartida(id!);
            router.back();
          } catch (e) {
            Alert.alert('No se pudo borrar', String(e));
          }
        },
      },
    ]);
  }

  function expulsar(usuarioId: string) {
    Alert.alert('¿Sacar a este DJ de la playlist?', undefined, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Sacar', style: 'destructive', onPress: async () => {
          try {
            await expulsarMiembro(id!, usuarioId);
            cargar(true);
          } catch (e) {
            Alert.alert('No se pudo expulsar', String(e));
          }
        },
      },
    ]);
  }

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudo cargar la playlist.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
      </View>
    );
  }

  if (!detalle) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  const esDueno = detalle.mi_rol === 'dueno';
  const puedeRenombrar = esDueno || detalle.modo_colaboracion === 'abierto';

  return (
    <View style={styles.contenedor}>
      <View style={styles.cabecera}>
        <Text style={styles.codigo}>Código: {detalle.codigo} · {detalle.modo_colaboracion === 'abierto' ? 'Modo abierto' : 'Dueño manda'}</Text>
        <View style={styles.miembros}>
          {detalle.miembros.map(m => (
            <TouchableOpacity
              key={m.usuario_id}
              style={styles.miembroChip}
              disabled={!esDueno || m.usuario_id === session?.user.id}
              onLongPress={() => esDueno && m.usuario_id !== session?.user.id && expulsar(m.usuario_id)}
            >
              <Text style={styles.miembroTexto}>{m.rol === 'dueno' ? '👑' : ''} {m.usuario_id === session?.user.id ? 'Vos' : m.usuario_id.slice(0, 6)}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <View style={styles.accionesFila}>
          {puedeRenombrar ? (
            <TouchableOpacity style={styles.accionBoton} onPress={() => setModalRenombrar(true)}>
              <Ionicons name="pencil" size={14} color={colors.textSecondary} />
              <Text style={styles.accionTexto}>Renombrar</Text>
            </TouchableOpacity>
          ) : null}
          <TouchableOpacity
            style={styles.accionBoton}
            onPress={() => router.push(`/playlists/compartida/aportar/${id}`)}
          >
            <Ionicons name="add" size={16} color={colors.cyan} />
            <Text style={[styles.accionTexto, { color: colors.cyan }]}>Aportar</Text>
          </TouchableOpacity>
          {esDueno ? (
            <TouchableOpacity style={styles.accionBoton} onPress={borrar}>
              <Ionicons name="trash" size={14} color="#FF6A6A" />
              <Text style={[styles.accionTexto, { color: '#FF6A6A' }]}>Borrar</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={styles.accionBoton} onPress={salir}>
              <Ionicons name="exit-outline" size={16} color="#FF6A6A" />
              <Text style={[styles.accionTexto, { color: '#FF6A6A' }]}>Salir</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      <FlatList
        data={detalle.tracks}
        keyExtractor={t => t.id}
        refreshControl={<RefreshControl refreshing={refrescando} onRefresh={onRefrescar} tintColor={colors.cyan} />}
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text style={styles.error}>Todavía no hay tracks aportados.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <FilaTrackCompartido
            track={item}
            enPreview={previewActivo === item.id}
            onEscuchar={() => setPreviewActivo(p => (p === item.id ? null : item.id))}
            onQuitar={
              esDueno || detalle.modo_colaboracion === 'abierto' || item.aportado_por === session?.user.id
                ? () => quitar(item)
                : undefined
            }
          />
        )}
      />

      <ModalTexto
        visible={modalRenombrar}
        titulo="Renombrar playlist"
        valorInicial={detalle.nombre}
        textoConfirmar="Renombrar"
        onCancelar={() => setModalRenombrar(false)}
        onConfirmar={renombrar}
      />
    </View>
  );
}

function FilaTrackCompartido({
  track, enPreview, onEscuchar, onQuitar,
}: { track: TrackCompartido; enPreview: boolean; onEscuchar: () => void; onQuitar?: () => void }) {
  const sonando = useEsSonando('youtube', track.id);
  return (
    <View>
      <TouchableOpacity style={styles.fila} onPress={onEscuchar}>
        <View style={[styles.indicadorGenero, { backgroundColor: colorParaGenero(track.genero) }]} />
        <View style={styles.info}>
          <Text style={[styles.titulo, sonando && styles.tituloSonando]} numberOfLines={1}>
            {track.titulo || '(sin título)'}{track.mix_name ? ` (${track.mix_name})` : ''}
          </Text>
          <Text style={styles.artista} numberOfLines={1}>{track.artista || '(sin artista)'}</Text>
        </View>
        <Ionicons name={enPreview ? 'volume-high' : 'play-outline'} size={18} color={sonando ? colors.cyan : colors.textMuted} />
        {onQuitar ? (
          <TouchableOpacity onPress={onQuitar} hitSlop={8} style={{ marginLeft: spacing.sm }}>
            <Ionicons name="close" size={18} color={colors.textMuted} />
          </TouchableOpacity>
        ) : null}
      </TouchableOpacity>
      {enPreview ? (
        <YoutubeTrackPreview
          id={track.id}
          artista={track.artista ?? ''}
          titulo={track.titulo ?? ''}
          mixName={track.mix_name}
          onCerrar={onEscuchar}
        />
      ) : null}
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
  errorDetalle: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
  cabecera: {
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    gap: spacing.sm,
  },
  codigo: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
  },
  miembros: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
  },
  miembroChip: {
    backgroundColor: colors.bgElevated,
    borderRadius: 999,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
  },
  miembroTexto: {
    color: colors.textSecondary,
    fontSize: 10,
  },
  accionesFila: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  accionBoton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  accionTexto: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    fontWeight: '600',
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
  tituloSonando: {
    color: colors.cyan,
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    marginTop: 1,
  },
});
