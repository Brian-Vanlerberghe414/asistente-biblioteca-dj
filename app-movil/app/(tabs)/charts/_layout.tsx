import { Stack } from 'expo-router';
import React from 'react';

import { BotonPerfil } from '../../../components/BotonPerfil';
import { colors } from '../../../theme';

export default function ChartsLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgHeader },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Charts', headerRight: () => <BotonPerfil /> }} />
      <Stack.Screen name="[slug]" options={{ title: 'Top 100' }} />
    </Stack>
  );
}
