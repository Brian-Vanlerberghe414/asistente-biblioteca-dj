-- Carátulas (cover art) en la Biblioteca Confiable: se guarda solo la URL
-- (apunta al CDN de Apple/mzstatic.com), nunca la imagen — costo de storage
-- despreciable (~150 bytes/fila) y sin necesidad de alojar nada nosotros.

ALTER TABLE biblioteca_tracks ADD COLUMN IF NOT EXISTS cover_url TEXT;

NOTIFY pgrst, 'reload schema';

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'biblioteca_tracks' AND column_name = 'cover_url';
