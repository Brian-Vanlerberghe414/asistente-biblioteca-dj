-- Fase 1 del Módulo 3 (backend multi-usuario): tabla de perfiles, uno por
-- cada DJ que se registra vía Supabase Auth. La fila se crea automáticamente
-- al firmar un usuario nuevo (trigger), así el backend no tiene que acordarse
-- de crearla a mano.
--
-- Requiere que Authentication esté habilitado en el proyecto de Supabase
-- (Authentication → Providers → Email, ya viene habilitado por defecto).

CREATE TABLE IF NOT EXISTS perfiles (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  nombre_dj   TEXT,
  creado_en   TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE perfiles ENABLE ROW LEVEL SECURITY;

-- Cada usuario ve y edita solo su propio perfil.
CREATE POLICY "Los DJs leen su propio perfil"
  ON perfiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Los DJs editan su propio perfil"
  ON perfiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

GRANT SELECT, UPDATE ON TABLE public.perfiles TO authenticated;
GRANT ALL ON TABLE public.perfiles TO service_role;

-- Trigger: crea la fila en perfiles automáticamente cuando alguien se
-- registra (auth.users es manejada por Supabase, no se puede hacer un
-- INSERT normal ahí desde afuera).
CREATE OR REPLACE FUNCTION public.crear_perfil_nuevo_usuario()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.perfiles (id, nombre_dj)
  VALUES (NEW.id, NEW.raw_user_meta_data->>'nombre_dj');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.crear_perfil_nuevo_usuario();

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'perfiles';
