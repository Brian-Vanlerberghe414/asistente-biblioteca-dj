import { useRouter } from 'expo-router';
import React from 'react';
import { Text, TouchableOpacity } from 'react-native';

import { useAuth } from '../context/AuthContext';
import { colors } from '../theme';

/** Avatar en el header que lleva a Perfil — presente en las 4 pantallas de
 * tabs (ver "Navegación" del plan: header con avatar → Perfil). */
export function BotonPerfil() {
  const router = useRouter();
  const { session } = useAuth();
  const inicial = (session?.user.email ?? '?').charAt(0).toUpperCase();
  return (
    <TouchableOpacity
      onPress={() => router.push('/perfil')}
      style={{
        width: 30, height: 30, borderRadius: 15, marginRight: 12,
        backgroundColor: colors.bgPanel, borderWidth: 1, borderColor: colors.line,
        alignItems: 'center', justifyContent: 'center',
      }}
    >
      <Text style={{ color: colors.cyan, fontWeight: '700', fontSize: 13 }}>{inicial}</Text>
    </TouchableOpacity>
  );
}
