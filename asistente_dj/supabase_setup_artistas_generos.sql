-- Registro de qué género(s)/subgénero(s) produce cada artista, derivado de
-- los tracks que van pasando por la Biblioteca Confiable (charts de Beatport,
-- imports, etc.). Ej.: "Vegas produce Psy-Trance".
--
-- subgenero usa '' (no NULL) cuando no aplica, para que la restricción UNIQUE
-- funcione bien en upserts (NULL nunca matchea a NULL en Postgres).

CREATE TABLE IF NOT EXISTS artistas_generos (
  id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  artista        TEXT NOT NULL,
  artista_norm   TEXT NOT NULL,
  genero         TEXT NOT NULL,
  subgenero      TEXT NOT NULL DEFAULT '',
  creado_en      TIMESTAMPTZ DEFAULT now(),
  actualizado_en TIMESTAMPTZ DEFAULT now(),
  UNIQUE (artista_norm, genero, subgenero)
);

CREATE INDEX IF NOT EXISTS idx_artistas_generos_norm ON artistas_generos(artista_norm);

ALTER TABLE artistas_generos ENABLE ROW LEVEL SECURITY;

CREATE POLICY "DJs pueden leer y escribir artistas_generos"
  ON artistas_generos FOR ALL
  TO PUBLIC
  USING (true)
  WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON TABLE public.artistas_generos TO anon;
GRANT ALL ON TABLE public.artistas_generos TO service_role;

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'artistas_generos';
