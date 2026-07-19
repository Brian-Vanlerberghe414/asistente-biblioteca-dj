import 'react-native-get-random-values';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import * as aesjs from 'aes-js';

/**
 * SecureStore de Android/iOS solo acepta valores de hasta 2048 bytes — la
 * sesión completa de Supabase (access_token + refresh_token + metadata del
 * usuario) suele superarlo. Patrón documentado por Supabase para Expo: la
 * clave de cifrado (chica) va en SecureStore; la sesión, cifrada con esa
 * clave, va en AsyncStorage (sin límite de tamaño relevante acá).
 */
export class LargeSecureStore {
  private async encriptar(clave: string, valor: string): Promise<string> {
    const claveCifrado = crypto.getRandomValues(new Uint8Array(256 / 8));
    const cifrador = new aesjs.ModeOfOperation.ctr(claveCifrado, new aesjs.Counter(1));
    const bytesCifrados = cifrador.encrypt(aesjs.utils.utf8.toBytes(valor));

    await SecureStore.setItemAsync(clave, aesjs.utils.hex.fromBytes(claveCifrado));

    return aesjs.utils.hex.fromBytes(bytesCifrados);
  }

  private async desencriptar(clave: string, valor: string): Promise<string | null> {
    const claveHex = await SecureStore.getItemAsync(clave);
    if (!claveHex) return null;

    const cifrador = new aesjs.ModeOfOperation.ctr(
      aesjs.utils.hex.toBytes(claveHex), new aesjs.Counter(1)
    );
    const bytesDescifrados = cifrador.decrypt(aesjs.utils.hex.toBytes(valor));

    return aesjs.utils.utf8.fromBytes(bytesDescifrados);
  }

  async getItem(clave: string): Promise<string | null> {
    const valorCifrado = await AsyncStorage.getItem(clave);
    if (!valorCifrado) return null;
    return this.desencriptar(clave, valorCifrado);
  }

  async removeItem(clave: string): Promise<void> {
    await AsyncStorage.removeItem(clave);
    await SecureStore.deleteItemAsync(clave);
  }

  async setItem(clave: string, valor: string): Promise<void> {
    const valorCifrado = await this.encriptar(clave, valor);
    await AsyncStorage.setItem(clave, valorCifrado);
  }
}
