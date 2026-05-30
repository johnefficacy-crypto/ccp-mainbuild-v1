-- Migration 154: add official_archive and sme_authored to document_source_kind.
--
-- PR #501 (migration 153) shipped with official_scan and crowd_sourced.
-- The corpus contract specifies official_archive (UPSC's published archive,
-- ~1-year delay) and sme_authored (SME-authored test content) as the intended
-- values. Both are added here following the forward-reserved ENUM policy:
-- old values official_scan and crowd_sourced are retained but removed from
-- ELIGIBLE_SOURCE_KINDS_V1 in dispatch.py (official_scan → use official_archive
-- instead; crowd_sourced remains ineligible).
--
-- Forward-reserved: NEVER remove ENUM values. Add new values only.

ALTER TYPE document_source_kind ADD VALUE IF NOT EXISTS 'official_archive';
ALTER TYPE document_source_kind ADD VALUE IF NOT EXISTS 'sme_authored';

COMMENT ON COLUMN document_assets.source_kind IS
    'Drives extractor eligibility. v1 accepts official_archive, '
    'sanitized_coaching, sme_authored. official_scan (legacy alias for '
    'official_archive) is also accepted for backwards compatibility. '
    'Raw coaching PDFs must be sanitized via SOP before extraction. '
    'See docs/engineering/sanitization-sop-v1.md and corpus contract.';
