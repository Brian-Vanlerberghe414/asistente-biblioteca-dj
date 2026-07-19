import Constants from 'expo-constants';
import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import { api } from '../api/http';
import { useAuth } from '../context/AuthContext';
import { colors, radius, spacing, typography } from '../theme';

interface Me {
  id: string;
  email: string | null;
}

export default function Perfil() {
  const { session, cerrarSesion } = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Me>('/me').then(setMe).catch(e => setError(String(e)));
  }, []);

  return (
    <View style={styles.contenedor}>
      <View style={styles.avatar}>
        <Text style={styles.avatarTexto}>
          {(session?.user.email ?? '?').charAt(0).toUpperCase()}
        </Text>
      </View>

      <Text style={styles.email}>{me?.email ?? session?.user.email ?? '—'}</Text>
      {error ? <Text style={styles.error}>No se pudo confirmar con el servidor: {error}</Text> : null}

      <View style={styles.filaInfo}>
        <Text style={styles.etiqueta}>Versión</Text>
        <Text style={styles.valor}>{Constants.expoConfig?.version ?? '—'}</Text>
      </View>

      <TouchableOpacity style={styles.boton} onPress={cerrarSesion}>
        <Text style={styles.botonTexto}>Cerrar sesión</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flex: 1,
    backgroundColor: colors.bgElevated,
    alignItems: 'center',
    padding: spacing.xl,
  },
  avatar: {
    width: 72, height: 72, borderRadius: 36,
    backgroundColor: colors.bgPanel, borderWidth: 1, borderColor: colors.line,
    alignItems: 'center', justifyContent: 'center',
    marginTop: spacing.lg, marginBottom: spacing.md,
  },
  avatarTexto: {
    color: colors.cyan, fontSize: typography.size.xl, fontWeight: '700',
  },
  email: {
    color: colors.textPrimary,
    fontSize: typography.size.lg,
    fontWeight: '600',
    marginBottom: spacing.lg,
  },
  error: {
    color: '#FF6A6A',
    fontSize: typography.size.sm,
    marginBottom: spacing.md,
    textAlign: 'center',
  },
  filaInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    marginBottom: spacing.xl,
  },
  etiqueta: { color: colors.textSecondary, fontSize: typography.size.sm },
  valor: { color: colors.textPrimary, fontSize: typography.size.sm },
  boton: {
    borderWidth: 1,
    borderColor: 'rgba(255,106,106,0.4)',
    borderRadius: radius.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    marginTop: 'auto',
    marginBottom: spacing.lg,
  },
  botonTexto: {
    color: '#FF6A6A',
    fontWeight: '600',
    fontSize: typography.size.md,
  },
});
