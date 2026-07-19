import type { Session } from '@supabase/supabase-js';
import React, { createContext, useContext, useEffect, useRef, useState } from 'react';

import { registrarSesionExpirada } from '../api/http';
import { supabase } from '../api/supabase';

interface AuthContextValue {
  session: Session | null;
  cargando: boolean;
  iniciarSesion: (email: string, password: string) => Promise<{ error: string | null }>;
  cerrarSesion: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [cargando, setCargando] = useState(true);
  const montado = useRef(true);

  useEffect(() => {
    montado.current = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!montado.current) return;
      setSession(data.session);
      setCargando(false);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_evento, nuevaSesion) => {
      if (!montado.current) return;
      setSession(nuevaSesion);
    });

    // Si el interceptor HTTP no pudo refrescar la sesión (refresh_token
    // también vencido/inválido), forzar el logout acá — así todas las
    // pantallas vuelven solas a Login sin manejar esto cada una.
    registrarSesionExpirada(() => {
      if (!montado.current) return;
      supabase.auth.signOut();
    });

    return () => {
      montado.current = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  async function iniciarSesion(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error: error?.message ?? null };
  }

  async function cerrarSesion() {
    await supabase.auth.signOut();
  }

  return (
    <AuthContext.Provider value={{ session, cargando, iniciarSesion, cerrarSesion }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  return ctx;
}
