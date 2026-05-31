# Extraction Environment Pinning

## Problem

The extractor pipeline depends on Tesseract OCR for page rasterization and
text extraction. OCR output is not bit-for-bit identical across platforms:
word segmentation, confidence scores, and bbox coordinates vary with the
underlying Tesseract/Leptonica build and system JPEG/PNG codec.

This produces divergent results that are hard to reason about:

- Observed: CI (Ubuntu, Tesseract 5.x) extracted **84 questions** from the
  2026 GS-I paper. The same PDF run locally on Windows (Tesseract from the
  UB Mannheim installer) produced **79 questions** — a 5-question divergence
  (~6%) against the same fixture.
- Root cause: different Tesseract versions produce different line-split
  decisions, which shifts segmentation boundaries. The pipeline's
  column-split heuristic is sensitive to OCR word bboxes; small shifts
  cascade into missed or merged question segments.
- Impact: the acceptance gate (recall ≥ 0.815) and any locally-run dry
  runs cannot be trusted as equivalent unless the environment is pinned.

## Decision: TBD

Two viable strategies are on the table. The operator has not yet chosen one.

### Option A — CI dispatch only (no Dockerfile)

All paper-grade extraction runs are submitted as CI jobs (GitHub Actions).
Local dry runs are permitted but explicitly not equivalent; recall measurements
come only from CI artifacts.

**Pros**
- Zero new infrastructure. The existing `extractor-acceptance.yml` workflow
  already pins Ubuntu + a specific APT Tesseract build.
- No Docker dependency for developers.
- Fast to adopt: change is documentation only.

**Cons**
- Local dry runs are disconnected from the acceptance gate. Operators who run
  the extractor locally to preview output may see materially different
  question counts.
- CI turnaround is 3–5 minutes; no quick local feedback loop.
- Anyone who accidentally runs the acceptance evaluation locally will get a
  number that diverges silently.

### Option B — Dockerfile

A `Dockerfile` in `app/backend/` pins Python + Tesseract + all shared-library
versions. Local runs use `docker run`; CI uses the same image via a registry
pull or `docker build`.

**Pros**
- Full reproducibility: local and CI runs are identical.
- The acceptance gate number is trustworthy from any machine.
- Explicit, auditable: the Dockerfile is the single source of truth for
  the extraction environment.

**Cons**
- Docker required on every developer machine (can be an onboarding friction
  point on Windows without WSL2).
- Image rebuild required when Tesseract or system libs are upgraded.
- CI must pull or build the image; adds ~30–90s to the acceptance workflow
  unless the image is cached in a registry.

## How to run paper-grade extraction reproducibly (current state)

Until the decision above is made, **CI dispatch is the only reliable path**
for acceptance-gate measurements.

```bash
# Trigger the acceptance gate via CI by pushing to a branch that touches:
#   app/backend/app/exam_intelligence/extraction/**
# The extractor-acceptance.yml workflow runs automatically.

# For local dry runs (not equivalent to CI, but useful for development):
cd app/backend
PYTHONPATH=. python scripts/run_extractor_dry.py \
    --document-id <uuid> \
    --paper-id <uuid>
# Inspect output:
# SELECT metadata->'dry_run_rows' FROM extraction_runs WHERE id = '<run_id>';
```

To re-run the v2 acceptance gate:

```bash
# From a branch that touches extraction/**:
pytest tests/exam_intelligence/extraction/test_pipeline_against_fixture.py \
    -m integration -v -s
# Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, Tesseract binary
# See: docs/extraction/v2-acceptance-2026-gs1.md (once populated)
```

## What versions are pinned

Pinned in `app/backend/requirements.txt`:

| Package | Version |
|---------|---------|
| PyMuPDF | 1.24.11 |
| pytesseract | 0.3.13 |
| pypdf | 6.10.2 |
| Pillow | 12.2.0 |
| numpy | 2.4.4 |

**Tesseract binary is NOT pinned in requirements.txt.** It is installed via
`apt-get install tesseract-ocr tesseract-ocr-eng` in the CI workflow
(`extractor-acceptance.yml`). The exact version depends on the Ubuntu runner's
APT snapshot. This is the root cause of the CI/local divergence.

To lock Tesseract:
- Option A: document the APT-pinned version (`tesseract-ocr=5.x.y-z`) in the
  workflow file.
- Option B: bake a specific Tesseract build into the Dockerfile.

## How to rerun the v2 acceptance gate

See `docs/extraction/v2-acceptance-2026-gs1.md`. That file is populated by
the acceptance gate CI job and committed after each paper-grade run. The gate
must pass (stem recall ≥ 0.815) before paper #2 ingest.

## Related

- `extractor-acceptance.yml` — CI workflow
- `docs/engineering/exam-intelligence-extraction-v1-corpus.md` — corpus contract,
  acceptance thresholds, extractor stack
- Issue: "Choose extraction environment strategy" (TBD)
