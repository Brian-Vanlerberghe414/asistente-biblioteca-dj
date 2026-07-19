import NetInfo from '@react-native-community/netinfo';
import React, { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { colors, typography } from '../theme';

/** V1 es 100% online (decisión de producto del plan): sin red no se cachea
 * nada, solo se avisa con claridad. Overlay absoluto para no reacomodar el
 * layout de navegación en cada cambio de conectividad. */
export function OfflineBanner() {
  const [sinConexion, setSinConexion] = useState(false);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    return NetInfo.addEventListener(estado => {
      setSinConexion(estado.isConnected === false || estado.isInternetReachable === false);
    });
  }, []);

  if (!sinConexion) return null;

  return (
    <Text style={[styles.banner, { paddingTop: insets.top + 6 }]}>
      Sin conexión — Asistente DJ funciona 100% online
    </Text>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    backgroundColor: '#7A1F1F',
    color: colors.textPrimary,
    fontSize: typography.size.xs,
    fontWeight: '600',
    textAlign: 'center',
    paddingBottom: 6,
    zIndex: 1000,
  },
});
