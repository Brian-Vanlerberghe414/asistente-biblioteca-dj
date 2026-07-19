import { API_URL } from '../config';
import { supabase } from './supabase';

type Metodo = 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT';

interface Opciones {
  metodo?: Metodo;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

/** Se dispara cuando ni el request ni el refresh de sesión funcionaron —
 * `AuthContext` se suscribe acá para forzar logout + volver a Login, en vez
 * de que cada pantalla tenga que manejar sesión vencida por su cuenta. */
let onSesionExpirada: (() => void) | null = null;
export function registrarSesionExpirada(cb: () => void): void {
  onSesionExpirada = cb;
}

async function peticion<T>(path: string, opciones: Opciones = {}, reintentando = false): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) {
    onSesionExpirada?.();
    throw new Error('No hay sesión activa');
  }

  const url = new URL(path.replace(/^\//, ''), API_URL.endsWith('/') ? API_URL : `${API_URL}/`);
  if (opciones.params) {
    for (const [clave, valor] of Object.entries(opciones.params)) {
      if (valor !== undefined) url.searchParams.set(clave, String(valor));
    }
  }

  const resp = await fetch(url.toString(), {
    method: opciones.metodo ?? 'GET',
    headers: {
      Authorization: `Bearer ${session.access_token}`,
      ...(opciones.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: opciones.body !== undefined ? JSON.stringify(opciones.body) : undefined,
  });

  if (resp.status === 401 && !reintentando) {
    const { data, error } = await supabase.auth.refreshSession();
    if (error || !data.session) {
      onSesionExpirada?.();
      throw new Error('Sesión expirada');
    }
    return peticion<T>(path, opciones, true);
  }

  if (!resp.ok) {
    const texto = await resp.text().catch(() => '');
    throw new Error(`${resp.status} ${resp.statusText}${texto ? `: ${texto}` : ''}`);
  }

  if (resp.status === 204) return undefined as T;
  const texto = await resp.text();
  return (texto ? JSON.parse(texto) : undefined) as T;
}

export const api = {
  get: <T>(path: string, params?: Opciones['params']) => peticion<T>(path, { metodo: 'GET', params }),
  post: <T>(path: string, body?: unknown) => peticion<T>(path, { metodo: 'POST', body }),
  patch: <T>(path: string, body?: unknown) => peticion<T>(path, { metodo: 'PATCH', body }),
  delete: <T>(path: string) => peticion<T>(path, { metodo: 'DELETE' }),
};
