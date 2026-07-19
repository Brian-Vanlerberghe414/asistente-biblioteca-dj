/**
 * Config de entorno — `EXPO_PUBLIC_*` se inlinean en el bundle de Metro
 * automáticamente desde `.env` (ver `.env.example`). No hace falta
 * `app.config.ts` para esto (soporte nativo de Expo desde SDK 49).
 */
function requerida(valor: string | undefined, nombre: string): string {
  if (!valor) {
    throw new Error(
      `Falta ${nombre} — copiá .env.example a .env y completá los valores.`
    );
  }
  return valor;
}

export const SUPABASE_URL = requerida(
  process.env.EXPO_PUBLIC_SUPABASE_URL, 'EXPO_PUBLIC_SUPABASE_URL'
);
export const SUPABASE_ANON_KEY = requerida(
  process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY, 'EXPO_PUBLIC_SUPABASE_ANON_KEY'
);
export const API_URL = requerida(
  process.env.EXPO_PUBLIC_API_URL, 'EXPO_PUBLIC_API_URL'
);
