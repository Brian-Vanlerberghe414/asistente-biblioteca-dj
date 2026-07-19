import { Stack } from 'expo-router';
import React from 'react';

import { BotonPerfil } from '../../../components/BotonPerfil';
import { colors } from '../../../theme';

export default function PlaylistsLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgHeader },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="index" options={{ title: 'Playlists', headerRight: () => <BotonPerfil /> }} />
      <Stack.Screen name="[nombre]" options={{ title: 'Playlist' }} />
      <Stack.Screen name="agregar/[nombre]" options={{ title: 'Agregar tracks', presentation: 'modal' }} />
      <Stack.Screen name="compartida/[id]" options={{ title: 'Playlist compartida' }} />
      <Stack.Screen name="compartida/aportar/[id]" options={{ title: 'Aportar tracks', presentation: 'modal' }} />
    </Stack>
  );
}
