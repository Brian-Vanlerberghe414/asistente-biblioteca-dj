-- Sincronización de biblioteca personal (base para Fase 3 — apps cliente).
-- A diferencia de biblioteca_tracks (conocimiento COMPARTIDO entre DJs) y de
-- audio_personal (solo registra archivos subidos), esto es la organización
-- PERSONAL de cada DJ: género/subgénero como él los clasificó, y sus
-- playlists. Privado por usuario, mismo patrón de RLS que audio_personal.
--
-- Clave de sincronización: artista_norm + titulo_norm (igual que
-- biblioteca_confiable.py) — un id de SQLite local no es estable entre
-- dispositivos/reinstalaciones, pero "es la misma canción" sí se puede
-- identificar por artista+título normalizados.

CREATE TABLE IF NOT EXISTS mi_biblioteca (
  id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  usuario_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  artista_norm   TEXT NOT NULL,
  titulo_norm    TEXT NOT NULL,
  artista        TEXT,
  titulo         TEXT,
  sello          TEXT,
  anio           TEXT,
  bpm            REAL,
  key            TEXT,
  camelot        TEXT,
  duracion_seg   REAL,
  genero         TEXT,
  subgenero      TEXT,
  energia        REAL,
  r2_key         TEXT,             -- referencia a audio_personal, si ya se subió el archivo
  actualizado_en TIMESTAMPTZ DEFAULT now(),
  UNIQUE (usuario_id, artista_norm, titulo_norm)
);

CREATE INDEX IF NOT EXISTS idx_mi_biblioteca_usuario ON mi_biblioteca(usuario_id);

CREATE TABLE IF NOT EXISTS mis_playlists (
  id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  usuario_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  nombre         TEXT NOT NULL,
  reglas         JSONB NOT NULL,   -- {"ids": [mi_biblioteca.id, ...]}
  actualizado_en TIMESTAMPTZ DEFAULT now(),
  UNIQUE (usuario_id, nombre)
);

ALTER TABLE mi_biblioteca ENABLE ROW LEVEL SECURITY;
ALTER TABLE mis_playlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Cada DJ ve y maneja solo su propia biblioteca"
  ON mi_biblioteca FOR ALL
  TO authenticated
  USING (auth.uid() = usuario_id)
  WITH CHECK (auth.uid() = usuario_id);

CREATE POLICY "Cada DJ ve y maneja solo sus propias playlists"
  ON mis_playlists FOR ALL
  TO authenticated
  USING (auth.uid() = usuario_id)
  WITH CHECK (auth.uid() = usuario_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.mi_biblioteca TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.mis_playlists TO authenticated;
GRANT ALL ON TABLE public.mi_biblioteca TO service_role;
GRANT ALL ON TABLE public.mis_playlists TO service_role;

NOTIFY pgrst, 'reload schema';

-- Verificación (correr después para confirmar que todo quedó bien):
SELECT table_name, column_name FROM information_schema.columns
WHERE table_name IN ('mi_biblioteca', 'mis_playlists') ORDER BY table_name, column_name;

SELECT grantee, privilege_type, table_name
FROM information_schema.role_table_grants
WHERE table_name IN ('mi_biblioteca', 'mis_playlists')
ORDER BY table_name, grantee, privilege_type;
