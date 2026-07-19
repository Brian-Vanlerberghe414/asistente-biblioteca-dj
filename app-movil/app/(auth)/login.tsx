import React, { useState } from 'react';
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';

import { useAuth } from '../../context/AuthContext';
import { colors, radius, spacing, typography } from '../../theme';

export default function Login() {
  const { iniciarSesion } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  async function onSubmit() {
    setError(null);
    if (!email.trim() || !password) {
      setError('Completá email y contraseña.');
      return;
    }
    setCargando(true);
    const { error: err } = await iniciarSesion(email.trim(), password);
    setCargando(false);
    if (err) setError(err);
    // Si no hay error, RootNavigator reacciona solo al cambio de sesión.
  }

  return (
    <KeyboardAvoidingView
      style={styles.contenedor}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <Text style={styles.titulo}>Asistente DJ</Text>
      <Text style={styles.subtitulo}>Iniciá sesión con tu cuenta</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        placeholderTextColor={colors.textMuted}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Contraseña"
        placeholderTextColor={colors.textMuted}
        secureTextEntry
        autoCapitalize="none"
        value={password}
        onChangeText={setPassword}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity style={styles.boton} onPress={onSubmit} disabled={cargando}>
        {cargando ? <ActivityIndicator color={colors.bgBase} /> : <Text style={styles.botonTexto}>Entrar</Text>}
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  contenedor: {
    flex: 1,
    backgroundColor: colors.bgBase,
    justifyContent: 'center',
    padding: spacing.xl,
  },
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.xl,
    fontWeight: '700',
    marginBottom: spacing.xs,
  },
  subtitulo: {
    color: colors.textSecondary,
    fontSize: typography.size.md,
    marginBottom: spacing.xl,
  },
  input: {
    backgroundColor: '#1A1A1C',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.09)',
    borderRadius: radius.sm,
    color: colors.textPrimary,
    padding: spacing.md,
    fontSize: typography.size.md,
    marginBottom: spacing.md,
  },
  error: {
    color: '#FF6A6A',
    fontSize: typography.size.sm,
    marginBottom: spacing.md,
  },
  boton: {
    backgroundColor: colors.cyan,
    borderRadius: radius.sm,
    padding: spacing.md,
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  botonTexto: {
    color: colors.bgBase,
    fontSize: typography.size.md,
    fontWeight: '700',
  },
});
