-- ─────────────────────────────────────────────────────────────
-- Axis 1: structural format. Drives extractor dispatch.
-- Slow-growing enum; one value per processing strategy.
-- ─────────────────────────────────────────────────────────────

CREATE TYPE document_structural_format AS ENUM (
    'mcq_bilingual_two_column',     -- UPSC Prelims, banking prelims; v1 eligible
    'mcq_monolingual_single',       -- single-language MCQ; future v1.5
    'essay_long_form',              -- Mains GS, essay, non-technical optionals; Tier 2
    'mixed_objective_subjective',   -- exams blending MCQ + short answer; Tier 2
    'technical_with_figures',       -- math/physics/eng optionals; Tier 3 vision
    'vernacular_non_devanagari',    -- Tamil, Manipuri, Bengali papers; Tier 3
    'unknown'                       -- not yet classified; NEVER extract
);

-- ─────────────────────────────────────────────────────────────
-- Axis 2: domain identity. Drives downstream UX and metadata.
-- Larger enum, expected to grow as new exams are added.
-- Does NOT affect extractor logic directly.
-- ─────────────────────────────────────────────────────────────

CREATE TYPE document_exam_identity AS ENUM (
    'upsc_cse_prelims_gs1',
    'upsc_cse_prelims_csat',
    'upsc_cse_mains_essay',
    'upsc_cse_mains_gs1',
    'upsc_cse_mains_gs2',
    'upsc_cse_mains_gs3',
    'upsc_cse_mains_gs4',
    'upsc_cse_mains_optional_sociology',
    'upsc_cse_mains_optional_psir',
    'upsc_cse_mains_optional_history',
    'upsc_cse_mains_optional_anthropology',
    'upsc_cse_mains_optional_technical',  -- collective bucket for v3
    'upsc_other',                          -- IFoS, IES, etc.
    'state_psc_other',                     -- v3+
    'banking_other',                       -- v3+
    'unknown'
);

-- ─────────────────────────────────────────────────────────────
-- Columns on document_assets
-- ─────────────────────────────────────────────────────────────

ALTER TABLE document_assets
    ADD COLUMN structural_format document_structural_format
        NOT NULL DEFAULT 'unknown',
    ADD COLUMN exam_identity document_exam_identity
        NOT NULL DEFAULT 'unknown';

-- ─────────────────────────────────────────────────────────────
-- Backfill the two known fixture/smoke documents.
-- They predate this convention; grandfathered based on
-- empirical acceptance-gate behavior at 0.815 recall.
-- ─────────────────────────────────────────────────────────────

UPDATE document_assets
SET
    structural_format = 'mcq_bilingual_two_column',
    exam_identity = 'upsc_cse_prelims_gs1'
WHERE id IN (
    '83722a86-610b-471d-8b6b-4a8397aa1791',   -- 2026 fixture
    'afc8e285-0ea1-41a1-a524-83b8b3121154'    -- 2025 smoke
);

-- ─────────────────────────────────────────────────────────────
-- Index for the dispatcher query pattern
-- ─────────────────────────────────────────────────────────────

CREATE INDEX idx_document_assets_structural_format
    ON document_assets(structural_format)
    WHERE structural_format != 'unknown';

-- ─────────────────────────────────────────────────────────────
-- Comment for future maintainers
-- ─────────────────────────────────────────────────────────────

COMMENT ON COLUMN document_assets.structural_format IS
    'Drives extractor dispatch. v1 handles only mcq_bilingual_two_column. '
    'See docs/engineering/exam-intelligence-extraction-v1-corpus.md '
    'for tier roadmap.';

COMMENT ON COLUMN document_assets.exam_identity IS
    'Domain identity for downstream UX, syllabus mapping, planner. '
    'Does not affect extractor logic. Larger enum that grows as new '
    'exams are added.';
