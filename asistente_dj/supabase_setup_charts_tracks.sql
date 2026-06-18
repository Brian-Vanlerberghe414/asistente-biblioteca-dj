-- Tabla en la nube para los charts Top 100 de Beatport (Módulo 2).
-- Espejo de la tabla local `charts_tracks` (ver db.py), pero accesible desde
-- cualquier lado (agente en la nube + app local), no solo desde la PC que
-- corrió el scrape. Mismo enfoque que biblioteca_tracks: clave anon, RLS
-- abierta porque es una herramienta personal de un solo usuario.

CREATE TABLE IF NOT EXISTS charts_tracks (
  id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  beatport_id     TEXT NOT NULL,
  genero_slug     TEXT NOT NULL,    -- 'global' o el slug del género/subgénero
  genero_nombre   TEXT,
  posicion        INTEGER,
  nombre          TEXT,
  mix_name        TEXT,
  artistas        JSONB,            -- lista de nombres
  remixers        JSONB,            -- lista de nombres
  release         TEXT,
  sello           TEXT,
  bpm             REAL,
  key             TEXT,
  genero_pista    TEXT,
  duracion_ms     INTEGER,
  publish_date    TEXT,
  image_url       TEXT,
  primera_vez     TEXT,             -- fecha (YYYY-MM-DD) en que se vio por primera vez
  fecha_scrape    TEXT,             -- fecha (YYYY-MM-DD) del último scrape que lo confirmó
  actualizado_en  TIMESTAMPTZ DEFAULT now(),
  UNIQUE (beatport_id, genero_slug)
);

CREATE INDEX IF NOT EXISTS idx_charts_genero ON charts_tracks(genero_slug);
CREATE INDEX IF NOT EXISTS idx_charts_fecha ON charts_tracks(genero_slug, fecha_scrape);

ALTER TABLE charts_tracks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "DJs pueden leer y escribir charts_tracks"
  ON charts_tracks FOR ALL
  TO PUBLIC
  USING (true)
  WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON TABLE public.charts_tracks TO anon;
GRANT ALL ON TABLE public.charts_tracks TO service_role;

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'charts_tracks';
