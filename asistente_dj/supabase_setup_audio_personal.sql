-- Fase 2 del Módulo 3: registro de los archivos de audio que cada DJ sube
-- a Cloudflare R2. A diferencia de biblioteca_tracks (metadata COMPARTIDA
-- entre todos los DJs), esto es la colección PRIVADA de cada usuario — los
-- archivos de audio son suyos, nadie más los ve ni los puede tocar.

CREATE TABLE IF NOT EXISTS audio_personal (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  usuario_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  r2_key        TEXT NOT NULL UNIQUE,
  titulo        TEXT,
  artista       TEXT,
  tamano_bytes  BIGINT,
  ruta_local    TEXT,            -- solo referencia, no se usa para servir el archivo
  subido_en     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audio_personal_usuario ON audio_personal(usuario_id);

ALTER TABLE audio_personal ENABLE ROW LEVEL SECURITY;

-- A diferencia de biblioteca_tracks, ACÁ ni siquiera la lectura es abierta:
-- cada usuario únicamente ve y escribe sus propias filas.
CREATE POLICY "Cada DJ ve y maneja solo su propio audio"
  ON audio_personal FOR ALL
  TO authenticated
  USING (auth.uid() = usuario_id)
  WITH CHECK (auth.uid() = usuario_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.audio_personal TO authenticated;
GRANT ALL ON TABLE public.audio_personal TO service_role;

NOTIFY pgrst, 'reload schema';

-- Verificación (correr después para confirmar que todo quedó bien):
SELECT grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_name = 'audio_personal'
ORDER BY grantee, privilege_type;
