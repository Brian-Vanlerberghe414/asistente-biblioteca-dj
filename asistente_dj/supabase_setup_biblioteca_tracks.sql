-- ============================================================
-- Biblioteca Confiable — tabla `biblioteca_tracks`
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
--
-- Esta es la tabla que usa de verdad `biblioteca_confiable.py` (buscar/
-- agregar/listar). Las tablas `contribuciones`/`tracks_canonical` de
-- supabase_setup.sql son de un diseño anterior y no la reemplazan.
-- ============================================================

CREATE TABLE IF NOT EXISTS biblioteca_tracks (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  artista       TEXT NOT NULL,
  titulo        TEXT NOT NULL,
  artista_norm  TEXT NOT NULL,
  titulo_norm   TEXT NOT NULL,
  duracion_seg  REAL,
  genero        TEXT,
  subgenero     TEXT,
  sello         TEXT,
  bpm           REAL,
  camelot       TEXT,
  fuente        TEXT,            -- 'manual' | 'beatport_chart' | etc.
  confirmado    BOOLEAN DEFAULT TRUE,
  creado_en     TIMESTAMPTZ DEFAULT now(),
  actualizado_en TIMESTAMPTZ DEFAULT now(),
  UNIQUE (artista_norm, titulo_norm)
);

CREATE INDEX IF NOT EXISTS idx_biblioteca_genero ON biblioteca_tracks(genero);
CREATE INDEX IF NOT EXISTS idx_biblioteca_norm ON biblioteca_tracks(artista_norm, titulo_norm);

ALTER TABLE biblioteca_tracks ENABLE ROW LEVEL SECURITY;

-- biblioteca_confiable.py (buscar/agregar/listar) usa `supabase_key` (no la
-- service_role key) para leer Y escribir — igual que `contribuciones` en
-- supabase_setup.sql, esta tabla está pensada para que la app misma escriba.
CREATE POLICY "DJs pueden leer y escribir biblioteca_tracks"
  ON biblioteca_tracks FOR ALL
  TO PUBLIC
  USING (true)
  WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON TABLE public.biblioteca_tracks TO anon;
GRANT ALL ON TABLE public.biblioteca_tracks TO service_role;

-- ── Verificar ────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'biblioteca_tracks';
