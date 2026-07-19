import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { guardarPlaylist, obtenerMisPlaylists, type PlaylistPropia } from '../api/playlists';
import { colors, radius, spacing, typography } from '../theme';
import { ModalTexto } from './ModalTexto';

interface Props {
  visible: boolean;
  trackId: number | null;
  onCerrar: () => void;
}

/** Picker "agregar a playlist" desde Biblioteca — con "crear nueva" inline
 * (ver plan, Tab 3 Playlists: "picker con 'crear nueva' inline"). Agrega UN
 * track a la playlist elegida (o a una nueva). */
export function ModalAgregarAPlaylist({ visible, trackId, onCerrar }: Props) {
  const [playlists, setPlaylists] = useState<PlaylistPropia[] | null>(null);
  const [modalNuevaVisible, setModalNuevaVisible] = useState(false);
  const [guardandoEn, setGuardandoEn] = useState<string | null>(null);

  useEffect(() => {
    if (visible) {
      setPlaylists(null);
      obtenerMisPlaylists().then(setPlaylists);
    }
  }, [visible]);

  async function agregarA(playlist: PlaylistPropia) {
    if (trackId === null) return;
    setGuardandoEn(playlist.nombre);
    const ids = playlist.reglas.ids.includes(trackId)
      ? playlist.reglas.ids
      : [...playlist.reglas.ids, trackId];
    try {
      await guardarPlaylist(playlist.nombre, ids);
    } finally {
      setGuardandoEn(null);
      onCerrar();
    }
  }

  async function crearYAgregar(nombre: string) {
    setModalNuevaVisible(false);
    if (trackId === null) return;
    setGuardandoEn(nombre);
    try {
      await guardarPlaylist(nombre, [trackId]);
    } finally {
      setGuardandoEn(null);
      onCerrar();
    }
  }

  return (
    <>
      <Modal visible={visible && !modalNuevaVisible} transparent animationType="slide" onRequestClose={onCerrar}>
        <TouchableOpacity style={styles.fondo} activeOpacity={1} onPress={onCerrar}>
          <View style={styles.caja} onStartShouldSetResponder={() => true}>
            <Text style={styles.titulo}>Agregar a playlist</Text>

            <TouchableOpacity style={styles.opcionNueva} onPress={() => setModalNuevaVisible(true)}>
              <Ionicons name="add-circle-outline" size={20} color={colors.cyan} />
              <Text style={styles.opcionNuevaTexto}>Crear nueva…</Text>
            </TouchableOpacity>

            {!playlists ? (
              <ActivityIndicator color={colors.cyan} style={{ marginVertical: spacing.lg }} />
            ) : playlists.length === 0 ? (
              <Text style={styles.vacio}>Todavía no tenés playlists propias.</Text>
            ) : (
              playlists.map(p => (
                <TouchableOpacity key={p.id} style={styles.fila} onPress={() => agregarA(p)} disabled={!!guardandoEn}>
                  <Text style={styles.filaTexto}>{p.nombre}</Text>
                  {guardandoEn === p.nombre ? (
                    <ActivityIndicator color={colors.cyan} size="small" />
                  ) : (
                    <Text style={styles.filaCantidad}>{p.reglas.ids.length}</Text>
                  )}
                </TouchableOpacity>
              ))
            )}
          </View>
        </TouchableOpacity>
      </Modal>

      <ModalTexto
        visible={modalNuevaVisible}
        titulo="Nueva playlist"
        placeholder="Nombre de la playlist"
        textoConfirmar="Crear y agregar"
        onCancelar={() => setModalNuevaVisible(false)}
        onConfirmar={crearYAgregar}
      />
    </>
  );
}

const styles = StyleSheet.create({
  fondo: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  caja: {
    backgroundColor: colors.bgElevated,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    padding: spacing.lg,
    maxHeight: '70%',
  },
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.md,
    fontWeight: '700',
    marginBottom: spacing.md,
  },
  opcionNueva: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    marginBottom: spacing.xs,
  },
  opcionNuevaTexto: {
    color: colors.cyan,
    fontWeight: '600',
    fontSize: typography.size.sm,
  },
  vacio: {
    color: colors.textMuted,
    fontSize: typography.size.sm,
    paddingVertical: spacing.lg,
    textAlign: 'center',
  },
  fila: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  filaTexto: {
    color: colors.textPrimary,
    fontSize: typography.size.sm,
  },
  filaCantidad: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
  },
});
