import { supabase } from './supabase';

/**
 * Capa de unificaciones de género (paraguas) — mismo mapeo que
 * `asistente_dj/unificaciones.py`, pero leído directo de Supabase con la
 * sesión del usuario (RLS de `genero_unificaciones` es lectura abierta para
 * `authenticated`, no hace falta pasar por el backend para esto, igual que
 * Realtime de playlists compartidas).
 *
 * Regla de oro (igual que el escritorio): la edición y el filtrado real
 * siguen usando géneros REALES — el paraguas es solo una capa de vista.
 */

interface FilaUnificacion {
  umbrella: string;
  valor: string;
}

let cache: { valor2umbrella: Map<string, string>; umbrella2valores: Map<string, string[]> } | null = null;
let cargando: Promise<void> | null = null;

async function fetchYArmarCache(): Promise<void> {
  const { data, error } = await supabase
    .from('genero_unificaciones')
    .select('umbrella,valor')
    .eq('activo', true);

  const filas = (error ? [] : (data as FilaUnificacion[] | null)) ?? [];
  const valor2umbrella = new Map<string, string>();
  const umbrella2valores = new Map<string, string[]>();
  for (const fila of filas) {
    valor2umbrella.set(fila.valor, fila.umbrella);
    const lista = umbrella2valores.get(fila.umbrella) ?? [];
    lista.push(fila.valor);
    umbrella2valores.set(fila.umbrella, lista);
  }
  cache = { valor2umbrella, umbrella2valores };
}

async function asegurarCache(): Promise<void> {
  if (cache) return;
  if (!cargando) {
    cargando = fetchYArmarCache();
  }
  await cargando;
}

export async function cargarUnificaciones(): Promise<void> {
  await asegurarCache();
}

/** Nombre a MOSTRAR para un track: el paraguas de su subgénero, el de su
 * género, o el género crudo si no hay unificación. Requiere haber llamado
 * `cargarUnificaciones()` antes (si no, se comporta como si no hubiera
 * unificaciones — nunca lanza). */
export function mostrar(genero: string | null | undefined, subgenero?: string | null): string | null {
  if (!cache) return genero ?? null;
  return (subgenero && cache.valor2umbrella.get(subgenero))
    || (genero && cache.valor2umbrella.get(genero))
    || genero
    || null;
}

export function esUmbrella(nombre: string | null | undefined): boolean {
  if (!cache || !nombre) return false;
  return cache.umbrella2valores.has(nombre);
}
