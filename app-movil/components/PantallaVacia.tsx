import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, typography } from '../theme';

/** Placeholder genérico para tabs todavía no implementados en esta sesión. */
export function PantallaVacia({ titulo }: { titulo: string }) {
  return (
    <View style={styles.contenedor}>
      <Text style={styles.texto}>{titulo}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flex: 1,
    backgroundColor: colors.bgBase,
    alignItems: 'center',
    justifyContent: 'center',
  },
  texto: {
    color: colors.textMuted,
    fontSize: typography.size.md,
  },
});
