import { Ionicons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import React from 'react';
import { Text, TouchableOpacity, View } from 'react-native';

import { BotonPerfil } from '../../components/BotonPerfil';
import { MiniPlayer } from '../../components/MiniPlayer';
import { colors } from '../../theme';

/** Tab bar propia (en vez de la de React Navigation tal cual) para poder
 * meter el `MiniPlayer` persistente arriba de los tabs sin pelear con los
 * internals vendorizados de expo-router. Recibe las props estándar de un
 * `tabBar` custom de React Navigation (state/descriptors/navigation). */
function TabBarPersonalizada({ state, descriptors, navigation }: any) {
  return (
    <View>
      <MiniPlayer />
      <View
        style={{
          flexDirection: 'row',
          borderTopWidth: 1,
          borderTopColor: colors.line,
          backgroundColor: colors.bgElevated,
          paddingBottom: 4,
        }}
      >
        {state.routes.map((route: any, index: number) => {
          const { options } = descriptors[route.key];
          const enfocado = state.index === index;
          const color = enfocado ? colors.cyan : colors.textMuted;
          const etiqueta = options.title ?? route.name;

          return (
            <TouchableOpacity
              key={route.key}
              accessibilityRole="button"
              accessibilityState={enfocado ? { selected: true } : {}}
              onPress={() => {
                const evento = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
                if (!enfocado && !evento.defaultPrevented) navigation.navigate(route.name);
              }}
              style={{ flex: 1, alignItems: 'center', paddingTop: 8, paddingBottom: 4 }}
            >
              {options.tabBarIcon?.({ focused: enfocado, color, size: 22 })}
              <Text style={{ color, fontSize: 10, marginTop: 2, fontWeight: '600' }}>{etiqueta}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      tabBar={TabBarPersonalizada}
      screenOptions={{
        headerStyle: { backgroundColor: colors.bgHeader },
        headerTintColor: colors.textPrimary,
        headerShadowVisible: false,
      }}
    >
      {/* biblioteca/charts/playlists tienen su propio Stack interno (con su
      propio header + avatar en la pantalla índice) — acá se oculta el
      header del Tabs para no duplicarlo. */}
      <Tabs.Screen
        name="biblioteca"
        options={{
          title: 'Biblioteca',
          headerShown: false,
          tabBarIcon: ({ color, size }) => <Ionicons name="musical-notes" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="charts"
        options={{
          title: 'Charts',
          headerShown: false,
          tabBarIcon: ({ color, size }) => <Ionicons name="flash" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="playlists"
        options={{
          title: 'Playlists',
          headerShown: false,
          tabBarIcon: ({ color, size }) => <Ionicons name="play" size={size} color={color} />,
        }}
      />
      <Tabs.Screen
        name="musica"
        options={{
          title: 'Mi Música',
          headerRight: () => <BotonPerfil />,
          tabBarIcon: ({ color, size }) => <Ionicons name="cloud" size={size} color={color} />,
        }}
      />
    </Tabs>
  );
}
