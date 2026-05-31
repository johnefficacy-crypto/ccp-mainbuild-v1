-- Migration 153: source_kind enum + column + sanitized_from FK
--
-- Adds a document_source_kind ENUM to classify the provenance of uploaded PDFs.
-- The v1 extractor is gated on ELIGIBLE_SOURCE_KINDS_V1 = {'sanitized_coaching',
-- 'official_scan'}. Raw coaching material (watermarks, promotional overlays) is
-- blocked at extraction time with a loud error rather than silently producing
-- garbage rows.
--
-- Forward-reserved: NEVER remove enum values. Add new values in future
-- migrations (ALTER TYPE … ADD VALUE 'new_value').

-- ── 1. Create the ENUM ─────────────────────────────────────────────────────

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_source_kind') THEN
    CREATE TYPE document_source_kind AS ENUM (
      'official_scan',         -- directly from UPSC/government press
      'sanitized_coaching',    -- coaching PDF watermarks/overlays removed; clean input
      'raw_coaching',          -- coaching PDF as-is; watermarks/overlays present
      'crowd_sourced',         -- community-contributed; provenance unclear
      'unknown'                -- not yet classified
    );
  END IF;
END $$;

-- ── 2. Add source_kind column ──────────────────────────────────────────────

ALTER TABLE document_assets
  ADD COLUMN IF NOT EXISTS source_kind document_source_kind NOT NULL DEFAULT 'unknown';

-- ── 3. Add sanitized_from_document_id FK (optional; filled for sanitized docs) ─

ALTER TABLE document_assets
  ADD COLUMN IF NOT EXISTS sanitized_from_document_id uuid
    REFERENCES document_assets(id) ON DELETE SET NULL;

COMMENT ON COLUMN document_assets.sanitized_from_document_id IS
  'If source_kind=sanitized_coaching, the UUID of the raw_coaching document this was cleaned from. NULL for official_scan and other kinds.';

-- ── 4. Index for FK lookups ────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_document_assets_sanitized_from
  ON document_assets (sanitized_from_document_id)
  WHERE sanitized_from_document_id IS NOT NULL;

-- ── 5. Partial index for fast eligibility checks ───────────────────────────

CREATE INDEX IF NOT EXISTS idx_document_assets_source_kind_eligible
  ON document_assets (source_kind)
  WHERE source_kind IN ('official_scan', 'sanitized_coaching');

-- ── 6. Backfill the two known fixture / acceptance-gate documents ──────────
--
-- These predate migration 153. Both are sanitized UPSC coaching PDFs (the
-- canonical UPSC press PDFs are not watermarked, but these were sourced via
-- coaching aggregators and have been verified clean). Backfill to
-- 'sanitized_coaching' so the acceptance gate continues to pass.

UPDATE document_assets
SET source_kind = 'sanitized_coaching'
WHERE id IN (
  '83722a86-610b-471d-8b6b-4a8397aa1791',   -- 2026 GS-I
  'afc8e285-0ea1-41a1-a524-83b8b3121154'    -- 2025 GS-I
);
