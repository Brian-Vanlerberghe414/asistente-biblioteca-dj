import { useLocalSearchParams } from 'expo-router';
import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { cacheBiblioteca, sincronizarTracks, type TrackBiblioteca } from '../../../api/mibiblioteca';
import { GENEROS, GENRE_TREE } from '../../../constants/genreTree';
import { colorParaGenero, colors, radius, spacing, typography } from '../../../theme';

type Estado = 'idle' | 'guardando' | 'guardado' | 'error';

export default function EditarTrack() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const original = useMemo(() => cacheBiblioteca.porId.get(Number(id)), [id]);

  const [genero, setGenero] = useState(original?.genero ?? null);
  const [subgenero, setSubgenero] = useState(original?.subgenero ?? null);
  const [estado, setEstado] = useState<Estado>('idle');
  const [errorTexto, setErrorTexto] = useState<string | null>(null);

  if (!original) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>
          No encontramos este track (volvé a Biblioteca e intentá de nuevo).
        </Text>
      </View>
    );
  }

  const subgenerosDisponibles = genero ? GENRE_TREE[genero] ?? [] : [];

  async function guardar(nuevoGenero: string | null, nuevoSubgenero: string | null) {
    const generoAnterior = genero;
    const subgeneroAnterior = subgenero;
    setGenero(nuevoGenero);
    setSubgenero(nuevoSubgenero);
    setEstado('guardando');
    setErrorTexto(null);

    const track = original as TrackBiblioteca;
    try {
      const resp = await sincronizarTracks([{
        artista: track.artista ?? '',
        titulo: track.titulo ?? '',
        sello: track.sello,
        anio: track.anio,
        bpm: track.bpm,
        key: track.key,
        camelot: track.camelot,
        duracion_seg: track.duracion_seg,
        genero: nuevoGenero,
        subgenero: nuevoSubgenero,
        energia: track.energia,
        r2_key: track.r2_key,
        actualizado_en: new Date().toISOString(),
      }]);
      const aplicado = resp.resultados[0]?.aplicado;
      if (!aplicado) {
        // El backend descartó el cambio (llegó un cambio más nuevo de otro
        // lado antes, o el reloj del teléfono está atrasado) — revertir y avisar,
        // no alcanza con mirar el status HTTP (esto fue 200 igual).
        setGenero(generoAnterior);
        setSubgenero(subgeneroAnterior);
        setEstado('error');
        setErrorTexto('No se guardó: había un cambio más nuevo en la nube. Refrescá la Biblioteca.');
        return;
      }
      // Reflejar el cambio en la cache local para que la lista lo muestre
      // actualizado sin tener que recargar toda la biblioteca.
      cacheBiblioteca.porId.set(track.id, { ...track, genero: nuevoGenero, subgenero: nuevoSubgenero });
      setEstado('guardado');
    } catch (e) {
      setGenero(generoAnterior);
      setSubgenero(subgeneroAnterior);
      setEstado('error');
      setErrorTexto(String(e));
    }
  }

  return (
    <ScrollView style={styles.contenedor} contentContainerStyle={{ paddingBottom: spacing.xl }}>
      <View style={styles.cabecera}>
        <Text style={styles.titulo} numberOfLines={2}>{original.titulo || '(sin título)'}</Text>
        <Text style={styles.artista} numberOfLines={1}>{original.artista || '(sin artista)'}</Text>
        <View style={styles.metadataFila}>
          {original.bpm ? <Text style={styles.metadataTexto}>{Math.round(original.bpm)} BPM</Text> : null}
          {original.camelot ? <Text style={styles.metadataTexto}>{original.camelot}</Text> : null}
          {original.sello ? <Text style={styles.metadataTexto}>{original.sello}</Text> : null}
        </View>
      </View>

      <View style={styles.estadoFila}>
        {estado === 'guardando' ? <Text style={styles.estadoTexto}>Guardando…</Text> : null}
        {estado === 'guardado' ? <Text style={[styles.estadoTexto, { color: colors.cyan }]}>Guardado ✓</Text> : null}
        {estado === 'error' ? <Text style={[styles.estadoTexto, { color: '#FF6A6A' }]}>{errorTexto}</Text> : null}
      </View>

      <Text style={styles.seccionTitulo}>Género</Text>
      <View style={styles.chipsWrap}>
        {GENEROS.map(g => (
          <TouchableOpacity
            key={g}
            style={[
              styles.chip,
              { borderColor: colorParaGenero(g) },
              genero === g && { backgroundColor: `${colorParaGenero(g)}22` },
            ]}
            onPress={() => guardar(g, GENRE_TREE[g]?.includes(subgenero ?? '') ? subgenero : null)}
          >
            <Text style={[styles.chipTexto, { color: genero === g ? colorParaGenero(g) : colors.textSecondary }]}>
              {g}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {subgenerosDisponibles.length > 0 ? (
        <>
          <Text style={styles.seccionTitulo}>Subgénero</Text>
          <View style={styles.chipsWrap}>
            <TouchableOpacity
              style={[styles.chip, subgenero === null && styles.chipActivoNeutro]}
              onPress={() => guardar(genero, null)}
            >
              <Text style={[styles.chipTexto, subgenero === null && { color: colors.textPrimary }]}>(ninguno)</Text>
            </TouchableOpacity>
            {subgenerosDisponibles.map(sg => (
              <TouchableOpacity
                key={sg}
                style={[styles.chip, subgenero === sg && styles.chipActivoNeutro]}
                onPress={() => guardar(genero, sg)}
              >
                <Text style={[styles.chipTexto, subgenero === sg && { color: colors.textPrimary }]}>{sg}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </>
      ) : null}
    </ScrollView>
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
  cabecera: {
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.lg,
    fontWeight: '700',
  },
  artista: {
    color: colors.textSecondary,
    fontSize: typography.size.md,
    marginTop: 2,
  },
  metadataFila: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  metadataTexto: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
  },
  estadoFila: {
    minHeight: 28,
    paddingHorizontal: spacing.lg,
    justifyContent: 'center',
  },
  estadoTexto: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
  },
  seccionTitulo: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  chipsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    paddingHorizontal: spacing.lg,
  },
  chip: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 999,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
  },
  chipActivoNeutro: {
    backgroundColor: colors.bgElevated,
    borderColor: colors.cyan,
  },
  chipTexto: {
    color: colors.textSecondary,
    fontSize: typography.size.xs,
    fontWeight: '600',
  },
});
