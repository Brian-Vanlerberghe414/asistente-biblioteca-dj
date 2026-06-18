-- ============================================================
-- Overcome Harmony DB — setup de tablas en Supabase
-- Ejecutar en: Supabase Dashboard → SQL Editor → New query
-- ============================================================

-- ── Tabla staging: contribuciones de los DJs ─────────────────
CREATE TABLE IF NOT EXISTS contribuciones (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fp_hash       TEXT NOT NULL,
  fp_dur        REAL,
  artista       TEXT,
  titulo        TEXT,
  bpm           REAL,
  key_nota      TEXT,
  camelot       TEXT,
  genero        TEXT,
  subgenero     TEXT,
  energia       INTEGER,
  bpm_fuente    TEXT,
  f_loud        REAL,
  f_bright      REAL,
  f_low         REAL,
  f_busy        REAL,
  waveform_data TEXT,
  comentario    TEXT,
  dj_uid        TEXT,
  version_app   TEXT,
  fecha         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contrib_fp ON contribuciones(fp_hash);
CREATE INDEX IF NOT EXISTS idx_contrib_dj ON contribuciones(dj_uid);

-- ── Tabla final curada (solo Brian escribe acá) ──────────────
CREATE TABLE IF NOT EXISTS tracks_canonical (
  fp_hash              TEXT PRIMARY KEY,
  artista              TEXT,
  titulo               TEXT,
  bpm                  REAL,
  key_nota             TEXT,
  camelot              TEXT,
  genero               TEXT,
  subgenero            TEXT,
  energia              INTEGER,
  n_contribuciones     INTEGER DEFAULT 0,
  votos                JSONB,
  ultima_actualizacion TIMESTAMPTZ DEFAULT now()
);

-- ── Row Level Security (RLS) ─────────────────────────────────
-- Habilitar RLS en ambas tablas
ALTER TABLE contribuciones     ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracks_canonical   ENABLE ROW LEVEL SECURITY;

-- Política: todos los roles pueden operar en contribuciones (anon, authenticated, service_role)
CREATE POLICY "DJs pueden contribuir"
  ON contribuciones FOR ALL
  TO PUBLIC
  USING (true)
  WITH CHECK (true);

-- Política: cualquiera puede leer tracks_canonical
CREATE POLICY "DJs pueden leer canonical"
  ON tracks_canonical FOR SELECT
  TO anon
  USING (true);

-- La service_role_key (solo Brian) puede hacer todo (override RLS por defecto).

-- ── Permisos explícitos de tabla (necesarios además de las políticas RLS) ──
GRANT SELECT, INSERT ON TABLE public.contribuciones TO anon;
GRANT SELECT           ON TABLE public.tracks_canonical TO anon;
GRANT ALL              ON TABLE public.contribuciones TO service_role;
GRANT ALL              ON TABLE public.tracks_canonical TO service_role;

-- ── Verificar ────────────────────────────────────────────────
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('contribuciones', 'tracks_canonical');
