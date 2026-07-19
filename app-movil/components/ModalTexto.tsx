import React, { useEffect, useState } from 'react';
import { Modal, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

import { colors, radius, spacing, typography } from '../theme';

interface Props {
  visible: boolean;
  titulo: string;
  valorInicial?: string;
  placeholder?: string;
  textoConfirmar?: string;
  onCancelar: () => void;
  onConfirmar: (valor: string) => void;
}

/** Diálogo de texto simple (crear/renombrar playlist) — `Alert.prompt` de
 * React Native solo existe en iOS, así que hace falta uno propio para
 * Android. */
export function ModalTexto({
  visible, titulo, valorInicial = '', placeholder, textoConfirmar = 'Guardar', onCancelar, onConfirmar,
}: Props) {
  const [valor, setValor] = useState(valorInicial);

  useEffect(() => {
    if (visible) setValor(valorInicial);
  }, [visible, valorInicial]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancelar}>
      <View style={styles.fondo}>
        <View style={styles.caja}>
          <Text style={styles.titulo}>{titulo}</Text>
          <TextInput
            style={styles.input}
            value={valor}
            onChangeText={setValor}
            placeholder={placeholder}
            placeholderTextColor={colors.textMuted}
            autoFocus
          />
          <View style={styles.botones}>
            <TouchableOpacity style={styles.boton} onPress={onCancelar}>
              <Text style={styles.botonTextoCancelar}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.boton}
              disabled={!valor.trim()}
              onPress={() => onConfirmar(valor.trim())}
            >
              <Text style={[styles.botonTexto, !valor.trim() && styles.botonTextoDeshabilitado]}>
                {textoConfirmar}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  fondo: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.xl,
  },
  caja: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.lg,
    padding: spacing.lg,
    width: '100%',
    borderWidth: 1,
    borderColor: colors.line,
  },
  titulo: {
    color: colors.textPrimary,
    fontSize: typography.size.md,
    fontWeight: '700',
    marginBottom: spacing.md,
  },
  input: {
    backgroundColor: '#1A1A1C',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.09)',
    borderRadius: radius.sm,
    color: colors.textPrimary,
    padding: spacing.md,
    fontSize: typography.size.md,
  },
  botones: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: spacing.lg,
    marginTop: spacing.lg,
  },
  boton: {
    paddingVertical: spacing.xs,
  },
  botonTextoCancelar: {
    color: colors.textSecondary,
    fontSize: typography.size.md,
  },
  botonTexto: {
    color: colors.cyan,
    fontSize: typography.size.md,
    fontWeight: '700',
  },
  botonTextoDeshabilitado: {
    color: colors.textMuted,
  },
});
