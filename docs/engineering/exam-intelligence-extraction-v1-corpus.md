# Exam Intelligence Extraction v1 — Corpus Contract

## Scope (v1 and tier roadmap)

The extractor pipeline is explicitly scoped via two axes on
document_assets:

- **structural_format** drives extractor dispatch. Slow-growing
  enum; one value per processing strategy.
- **exam_identity** drives downstream domain logic (syllabus
  mapping, planner blast radius, reviewer UX). Larger enum that
  grows with each new exam added; does NOT affect extractor logic.

### Tier roadmap

| Tier | Structural formats | Status |
|------|-------------------|--------|
| 1 (v1) | mcq_bilingual_two_column | shipping; UPSC CSE Prelims |
| 1.5 | mcq_monolingual_single | planned; banking/state PSC MCQ |
| 2 | essay_long_form, mixed_objective_subjective | future; Mains GS, non-technical optionals |
| 3 | technical_with_figures, vernacular_non_devanagari | future; needs vision model + multilingual OCR |

### v1 eligibility

A document is extractable by v1 iff:
1. structural_format == 'mcq_bilingual_two_column'
2. source_kind is appropriate clean input (see PR #501)

Out-of-scope documents upload successfully with their format tagged
but are NEVER auto-extracted. The extractor raises a loud error
(ExtractionNotSupportedError) on dispatch attempts for unsupported
formats. No silent garbage is produced.

### Adding a new exam identity

1. Add the value to the `document_exam_identity` ENUM (forward
   migration; never remove ENUM values).
2. Add the value to `ExamIdentity` in `dispatch.py`.
3. Add a mapping in `EXAM_TO_FORMAT_DEFAULT`.
4. Add a test case in `test_dispatch.py` confirming the mapping.

The test `test_every_exam_identity_has_a_mapping` will fail
loudly if step 3 is skipped.

### Grandfather clause

The 2026 fixture (83722a86-...) and 2025 smoke document
(afc8e285-...) were uploaded before the source_kind convention
existed. They are grandfathered as 'sanitized_coaching' for v1
acceptance gate continuity. Future uploads MUST use the new
classification flow.

---

## Scope
- Exam: UPSC CSE
- Cycle context: UPSC CSE 2026
- Document type: pyq_paper
- Corpus size: max 5 PDFs
- First fixture: 1 full paper (~100 questions)
- Excluded from v1: notification, corrigendum, answer-key extraction,
  topic tagging, options tagging, LLM-based extraction, auto-verification,
  scanned-only papers (deferred until OCR pipeline lands).

## Trust model
- Extraction output is a SUGGESTION engine.
- Every extracted row lands as reviewer_status='pending' via existing CMS path.
- Confidence is a queue-priority signal only — never auto-verifies.
- Reviewer must approve before any planner-readable status is reached.
- The existing CMS lifecycle (pending → reviewed → locked/verified) is unchanged.

## Span model — bbox-first
- Authoritative representation: regions[] list of {page, bbox}.
- Coordinate system: top-left origin, normalized to page [0.0, 1.0].
- Bbox format: [x_min, y_min, x_max, y_max].
- Multi-region required to support cross-column and cross-page questions.
- text_excerpt field is convenience only. If text and bbox disagree, bbox wins.
- Do NOT include char_start/char_end. Reject char-offset spans entirely.

## Extractor stack constraint
- Digital PDFs: pymupdf (text + bbox per word/line).
- Scanned PDFs: deferred to v2. Tesseract hOCR path documented but not built.
- Existing text_extract queue produces page-level plain text — insufficient
  for bbox. Decision pending in PR0.75: extend text_extract or add second pass.

## Fixture split
- questions.json — segmentation + question_text + regions (v1)
- options.json — option text + is_correct (v2, after questions extractor lands)
- topic_tags.json — topic_id assignment (v3, after UPSC topic taxonomy seeded)

## Evaluation metrics (v1 acceptance)
Question segmentation:
  recall    = matched_questions / fixture_questions    >= 0.80
  precision = matched_questions / extracted_questions  reported, no threshold

Match definition (a fixture question counts as matched if):
  page_match           = exact
  IoU(bbox_extracted, bbox_fixture) >= 0.5
  centroid(bbox_extracted) lies inside bbox_fixture
  normalized_text_similarity >= 0.95 (Levenshtein ratio after whitespace normalize)
    OR question_number matches exactly

Aggregate v1 ship gate:
  question recall >= 0.80 across the full fixture
  zero false-positive question_numbers (extractor must not invent numbering)

## Idempotency and collision
idempotency_key = sha256(document_id || page || regions_hash || extractor_version)
content_hash    = sha256(normalize(question_text))

normalize(question_text): lowercase, collapse whitespace, strip punctuation
except internal "?" and ".", remove leading "Q." or "N." numbering.

Write rules:
- idempotency_key collision → reuse existing extracted row, do not insert.
- content_hash collision with any existing row (manual or auto) → do not
  insert; create extraction_provenance link to existing row and flag for
  reviewer confirmation.

## Label ownership
- Owner: <TODO — name internal SME or contract labeler>
- Tool: PR0.5 bbox labeler (PDF.js + canvas rectangle drawer).
- Target labeling time: ~6 hours for 100 questions including review.

## Source document characteristics (v1 corpus, observed)

- Format: scanned PDF (no text layer), 300 DPI JPEG per page.
  Confirmed across 2026 and 2025 GS-I papers — both produced by
  ScandAll PRO + Adobe PDF Scan Library.
- Bilingual layout: English on odd pages, Hindi translations on
  even pages. v1 extractor processes odd pages only.
- Two-column layout. Papers in this corpus (2025 and 2026 GS-I) have
  gutters consistently in the band x ∈ [0.44, 0.52] (normalized).
  Column-split is detected per-page by finding the lowest-density bin
  within this band; global bimodal search is forbidden for this corpus
  (failure mode: locks onto header/watermark bins far from the true
  gutter). The band [0.44, 0.52] is an explicit UPSC v1 corpus
  parameter, not a generic heuristic.
- Page size varies across papers:
  2026 paper: 538.56 × 761.76 pts (~7.5" × 10.6")
  2025 paper: 602.64 × 761.04 pts (~8.4" × 10.6")
  All geometric heuristics must operate in normalized [0,1] coords.
- 100 numbered questions per paper. Approximately 8-12 are
  matching/table-form questions tagged out_of_scope_v1 in fixtures.

## Extractor stack (v1, locked)

- pymupdf for page rasterization, dimensions, metadata
- Tesseract OCR (lang=eng) with --psm 6, word-level bbox output
- No LLM
- No Hindi processing
- No figure/table/matching-list extraction
- No options, no topic tags

## Out of scope (explicit non-goals for v1)
- Topic taxonomy seeding for UPSC.
- Options extraction.
- Topic tagging.
- LLM use of any kind.
- OCR / scanned papers.
- Notification, corrigendum, or answer-key extraction.
- Auto-verification at any confidence threshold.
- Bulk approval before sample review of new run.
