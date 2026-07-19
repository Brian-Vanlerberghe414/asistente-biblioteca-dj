import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, RefreshControl, SectionList, StyleSheet, Text, TouchableOpacity, View,
} from 'react-native';

import { type Genero, obtenerGeneros } from '../../../api/charts';
import { colors, radius, spacing, typography } from '../../../theme';

interface Seccion {
  title: string;
  data: Genero[];
}

const SIN_PARAGUAS = 'Géneros';

function agruparPorParaguas(generos: Genero[]): Seccion[] {
  const porUmbrella = new Map<string, Genero[]>();
  for (const g of generos) {
    const clave = g.umbrella ?? SIN_PARAGUAS;
    if (!porUmbrella.has(clave)) porUmbrella.set(clave, []);
    porUmbrella.get(clave)!.push(g);
  }
  const secciones = Array.from(porUmbrella.entries()).map(([title, data]) => ({
    title, data: data.sort((a, b) => a.nombre.localeCompare(b.nombre)),
  }));
  // Los paraguas primero (agrupan varios géneros), "Géneros" sueltos al final.
  secciones.sort((a, b) => {
    if (a.title === SIN_PARAGUAS) return 1;
    if (b.title === SIN_PARAGUAS) return -1;
    return a.title.localeCompare(b.title);
  });
  return secciones;
}

export default function SelectorGeneros() {
  const router = useRouter();
  const [generos, setGeneros] = useState<Genero[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refrescando, setRefrescando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const datos = await obtenerGeneros();
      setGeneros(datos);
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const secciones = useMemo(() => agruparPorParaguas(generos ?? []), [generos]);

  async function onRefrescar() {
    setRefrescando(true);
    await cargar();
    setRefrescando(false);
  }

  if (generos === null && !error) {
    return (
      <View style={styles.centrado}>
        <ActivityIndicator color={colors.cyan} size="large" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centrado}>
        <Text style={styles.error}>No se pudieron cargar los géneros.</Text>
        <Text style={styles.errorDetalle}>{error}</Text>
        <TouchableOpacity style={styles.botonReintentar} onPress={cargar}>
          <Text style={styles.botonReintentarTexto}>Reintentar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <SectionList
      style={styles.lista}
      sections={secciones}
      keyExtractor={item => item.genero_slug}
      stickySectionHeadersEnabled={false}
      refreshControl={
        <RefreshControl refreshing={refrescando} onRefresh={onRefrescar} tintColor={colors.cyan} />
      }
      renderSectionHeader={({ section }) => (
        <Text style={styles.encabezadoSeccion}>{section.title}</Text>
      )}
      renderItem={({ item }) => (
        <TouchableOpacity
          style={styles.fila}
          onPress={() => router.push(`/charts/${item.genero_slug}`)}
        >
          <View style={styles.filaInfo}>
            <Text style={styles.nombreGenero}>{item.nombre}</Text>
            {item.ultima ? <Text style={styles.fechaGenero}>Último scrape: {item.ultima}</Text> : null}
          </View>
          <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
        </TouchableOpacity>
      )}
      ListEmptyComponent={
        <View style={styles.centrado}>
          <Text style={styles.error}>Todavía no hay charts guardados.</Text>
        </View>
      }
    />
  );
}

const styles = StyleSheet.create({
  lista: {
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
  botonReintentar: {
    marginTop: spacing.lg,
    backgroundColor: colors.bgElevated,
    borderRadius: radius.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
  },
  botonReintentarTexto: {
    color: colors.cyan,
    fontWeight: '600',
  },
  encabezadoSeccion: {
    color: colors.cyan,
    fontSize: typography.size.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    backgroundColor: colors.bgBase,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xs,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  filaInfo: {
    flex: 1,
  },
  nombreGenero: {
    color: colors.textPrimary,
    fontSize: typography.size.md,
    fontWeight: '600',
  },
  fechaGenero: {
    color: colors.textMuted,
    fontSize: typography.size.xs,
    marginTop: 2,
  },
});
