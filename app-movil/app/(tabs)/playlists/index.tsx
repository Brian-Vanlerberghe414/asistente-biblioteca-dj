import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useRouter } from 'expo-router';
import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';

import {
  borrarPlaylist, guardarPlaylist, obtenerMisPlaylists, type PlaylistPropia, renombrarPlaylist,
} from '../../../api/playlists';
import {
  crearPlaylistCompartida, listarPlaylistsCompartidas, type PlaylistCompartida, unirseAPlaylist,
} from '../../../api/playlistsCompartidas';
import { ModalTexto } from '../../../components/ModalTexto';
import { colors, radius, spacing, typography } from '../../../theme';

type Seccion = 'propias' | 'compartidas';

export default function Playlists() {
  const [seccion, setSeccion] = useState<Seccion>('propias');

  return (
    <View style={styles.contenedor}>
      <View style={styles.segmentado}>
        <TouchableOpacity
          style={[styles.segmento, seccion === 'propias' && styles.segmentoActivo]}
          onPress={() => setSeccion('propias')}
        >
          <Text style={[styles.segmentoTexto, seccion === 'propias' && styles.segmentoTextoActivo]}>Propias</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.segmento, seccion === 'compartidas' && styles.segmentoActivo]}
          onPress={() => setSeccion('compartidas')}
        >
          <Text style={[styles.segmentoTexto, seccion === 'compartidas' && styles.segmentoTextoActivo]}>Compartidas</Text>
        </TouchableOpacity>
      </View>

      {seccion === 'propias' ? <SeccionPropias /> : <SeccionCompartidas />}
    </View>
  );
}

function SeccionPropias() {
  const router = useRouter();
  const [playlists, setPlaylists] = useState<PlaylistPropia[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalNuevaVisible, setModalNuevaVisible] = useState(false);
  const [modalRenombrar, setModalRenombrar] = useState<PlaylistPropia | null>(null);

  const cargar = useCallback(() => {
    obtenerMisPlaylists().then(setPlaylists).catch(e => setError(String(e)));
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function crear(nombre: string) {
    setModalNuevaVisible(false);
    try {
      await guardarPlaylist(nombre, []);
      cargar();
      router.push(`/playlists/${encodeURIComponent(nombre)}`);
    } catch (e) {
      Alert.alert('No se pudo crear la playlist', String(e));
    }
  }

  async function renombrar(nombreNuevo: string) {
    const playlist = modalRenombrar;
    setModalRenombrar(null);
    if (!playlist) return;
    try {
      await renombrarPlaylist(playlist.nombre, nombreNuevo);
      cargar();
    } catch (e) {
      Alert.alert('No se pudo renombrar', String(e));
    }
  }

  function onLongPress(playlist: PlaylistPropia) {
    Alert.alert(playlist.nombre, undefined, [
      { text: 'Renombrar', onPress: () => setModalRenombrar(playlist) },
      {
        text: 'Borrar', style: 'destructive', onPress: () => {
          Alert.alert('¿Borrar esta playlist?', 'No se puede deshacer.', [
            { text: 'Cancelar', style: 'cancel' },
            {
              text: 'Borrar', style: 'destructive', onPress: async () => {
                try {
                  await borrarPlaylist(playlist.nombre);
                  cargar();
                } catch (e) {
                  Alert.alert('No se pudo borrar', String(e));
                }
              },
            },
          ]);
        },
      },
      { text: 'Cancelar', style: 'cancel' },
    ]);
  }

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudieron cargar tus playlists.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
      </View>
    );
  }

  if (!playlists) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  return (
    <>
      <TouchableOpacity style={styles.botonNueva} onPress={() => setModalNuevaVisible(true)}>
        <Ionicons name="add" size={20} color={colors.cyan} />
        <Text style={styles.botonNuevaTexto}>Nueva playlist</Text>
      </TouchableOpacity>

      <FlatList
        data={playlists}
        keyExtractor={item => String(item.id)}
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text style={styles.error}>Todavía no creaste ninguna playlist.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.fila}
            onPress={() => router.push(`/playlists/${encodeURIComponent(item.nombre)}`)}
            onLongPress={() => onLongPress(item)}
          >
            <View style={styles.info}>
              <Text style={styles.nombre}>{item.nombre}</Text>
              <Text style={styles.cantidad}>{item.reglas.ids.length} tracks</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
          </TouchableOpacity>
        )}
      />

      <ModalTexto
        visible={modalNuevaVisible}
        titulo="Nueva playlist"
        placeholder="Nombre de la playlist"
        textoConfirmar="Crear"
        onCancelar={() => setModalNuevaVisible(false)}
        onConfirmar={crear}
      />
      <ModalTexto
        visible={!!modalRenombrar}
        titulo="Renombrar playlist"
        valorInicial={modalRenombrar?.nombre}
        textoConfirmar="Renombrar"
        onCancelar={() => setModalRenombrar(null)}
        onConfirmar={renombrar}
      />
    </>
  );
}

function SeccionCompartidas() {
  const router = useRouter();
  const [playlists, setPlaylists] = useState<PlaylistCompartida[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [modalCrear, setModalCrear] = useState(false);
  const [modalUnirse, setModalUnirse] = useState(false);

  const cargar = useCallback(() => {
    listarPlaylistsCompartidas().then(setPlaylists).catch(e => setError(String(e)));
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  async function crear(nombre: string) {
    setModalCrear(false);
    try {
      const pl = await crearPlaylistCompartida(nombre);
      cargar();
      router.push(`/playlists/compartida/${pl.id}`);
    } catch (e) {
      Alert.alert('No se pudo crear la playlist', String(e));
    }
  }

  async function unirse(codigo: string) {
    setModalUnirse(false);
    try {
      const pl = await unirseAPlaylist(codigo);
      cargar();
      router.push(`/playlists/compartida/${pl.id}`);
    } catch (e) {
      Alert.alert('No se pudo unir', 'Revisá el código e intentá de nuevo.');
    }
  }

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudieron cargar tus playlists compartidas.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
      </View>
    );
  }

  if (!playlists) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  return (
    <>
      <View style={styles.filaBotones}>
        <TouchableOpacity style={styles.botonNueva} onPress={() => setModalCrear(true)}>
          <Ionicons name="add" size={20} color={colors.cyan} />
          <Text style={styles.botonNuevaTexto}>Crear</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.botonNueva} onPress={() => setModalUnirse(true)}>
          <Ionicons name="enter-outline" size={18} color={colors.cyan} />
          <Text style={styles.botonNuevaTexto}>Unirse con código</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={playlists}
        keyExtractor={item => item.id}
        ListEmptyComponent={
          <View style={styles.centrado}>
            <Text style={styles.error}>Todavía no participás de ninguna playlist compartida.</Text>
          </View>
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.fila}
            onPress={() => router.push(`/playlists/compartida/${item.id}`)}
          >
            <View style={styles.info}>
              <Text style={styles.nombre}>{item.nombre}</Text>
              <Text style={styles.cantidad}>
                {item.mi_rol === 'dueno' ? 'Dueño' : 'Miembro'} · código {item.codigo}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
          </TouchableOpacity>
        )}
      />

      <ModalTexto
        visible={modalCrear}
        titulo="Nueva playlist compartida"
        placeholder="Nombre de la playlist"
        textoConfirmar="Crear"
        onCancelar={() => setModalCrear(false)}
        onConfirmar={crear}
      />
      <ModalTexto
        visible={modalUnirse}
        titulo="Unirse con código"
        placeholder="Código de 8 caracteres"
        textoConfirmar="Unirse"
        onCancelar={() => setModalUnirse(false)}
        onConfirmar={unirse}
      />
    </>
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
  segmentado: {
    flexDirection: 'row',
    margin: spacing.lg,
    backgroundColor: colors.bgElevated,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 3,
  },
  segmento: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderRadius: radius.sm - 2,
  },
  segmentoActivo: {
    backgroundColor: 'rgba(0,229,255,0.14)',
  },
  segmentoTexto: {
    color: colors.textSecondary,
    fontSize: typography.size.sm,
    fontWeight: '600',
  },
  segmentoTextoActivo: {
    color: colors.cyan,
  },
  filaBotones: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginHorizontal: spacing.lg,
  },
  botonNueva: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    marginBottom: spacing.lg,
    alignSelf: 'flex-start',
    backgroundColor: colors.bgElevated,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.line,
  },
  botonNuevaTexto: {
    color: colors.cyan,
    fontWeight: '600',
    fontSize: typography.size.sm,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  info: {
    flex: 1,
  },
  nombre: {
    color: colors.textPrimary,
    fontSize: typography.size.md,
    fontWeight: '600',
  },
  cantidad: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    marginTop: 2,
  },
});
