import { Stack } from 'expo-router';
import React from 'react';

import { BotonPerfil } from '../../../components/BotonPerfil';
import { colors } from '../../../theme';

export default function BibliotecaLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgHeader },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Biblioteca', headerRight: () => <BotonPerfil /> }} />
      <Stack.Screen name="[id]" options={{ title: 'Editar track' }} />
    </Stack>
  );
}
