-- Fase 1 del Módulo 3 (backend multi-usuario): rediseño de RLS en las tablas
-- compartidas. Hasta ahora `biblioteca_tracks` y `artistas_generos` tenían
-- una sola política "FOR ALL TO PUBLIC USING (true)" — cualquiera con la
-- clave anon podía leer Y escribir lo que quisiera. Eso era aceptable con
-- un solo usuario (Brian) en desarrollo; deja de serlo apenas hay más
-- clientes/usuarios.
--
-- Nuevo esquema:
--   - LECTURA: sigue abierta a cualquiera (es una base de conocimiento
--     compartida, bajo riesgo dejarla legible).
--   - ESCRITURA (INSERT/UPDATE): solo usuarios autenticados (rol
--     `authenticated`, ya no `anon`/`PUBLIC`).
--
-- `charts_tracks` NO se toca acá: sigue escribiendo el scraper automático
-- con su credencial actual (no es un usuario final); los clientes solo
-- necesitan leerla, y su política de lectura abierta ya sirve para eso.

-- ──────────────────────────────────────────────────────── biblioteca_tracks
ALTER TABLE biblioteca_tracks
  ADD COLUMN IF NOT EXISTS creado_por UUID REFERENCES auth.users(id);

DROP POLICY IF EXISTS "DJs pueden leer y escribir biblioteca_tracks" ON biblioteca_tracks;

CREATE POLICY "Lectura abierta de biblioteca_tracks"
  ON biblioteca_tracks FOR SELECT
  TO PUBLIC
  USING (true);

CREATE POLICY "Escritura autenticada de biblioteca_tracks"
  ON biblioteca_tracks FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Actualizacion autenticada de biblioteca_tracks"
  ON biblioteca_tracks FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

REVOKE INSERT, UPDATE ON TABLE public.biblioteca_tracks FROM anon;
GRANT SELECT ON TABLE public.biblioteca_tracks TO anon;
GRANT SELECT, INSERT, UPDATE ON TABLE public.biblioteca_tracks TO authenticated;

-- ──────────────────────────────────────────────────────── artistas_generos
DROP POLICY IF EXISTS "DJs pueden leer y escribir artistas_generos" ON artistas_generos;

CREATE POLICY "Lectura abierta de artistas_generos"
  ON artistas_generos FOR SELECT
  TO PUBLIC
  USING (true);

CREATE POLICY "Escritura autenticada de artistas_generos"
  ON artistas_generos FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Actualizacion autenticada de artistas_generos"
  ON artistas_generos FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

REVOKE INSERT, UPDATE ON TABLE public.artistas_generos FROM anon;
GRANT SELECT ON TABLE public.artistas_generos TO anon;
GRANT SELECT, INSERT, UPDATE ON TABLE public.artistas_generos TO authenticated;

SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE tablename IN ('biblioteca_tracks', 'artistas_generos')
ORDER BY tablename, cmd;
