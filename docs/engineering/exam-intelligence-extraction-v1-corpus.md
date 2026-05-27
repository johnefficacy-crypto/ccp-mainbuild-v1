# Exam Intelligence Extraction v1 — Corpus Contract

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

## Out of scope (explicit non-goals for v1)
- Topic taxonomy seeding for UPSC.
- Options extraction.
- Topic tagging.
- LLM use of any kind.
- OCR / scanned papers.
- Notification, corrigendum, or answer-key extraction.
- Auto-verification at any confidence threshold.
- Bulk approval before sample review of new run.
