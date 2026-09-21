# UPSC CSE Mains GS corpus — fabrication audit

Status as of 2026-09-14. Suggested repo path:
`docs/status/2026-09-14-gs-corpus-fabrication-audit.md`

**Read this before using any UPSC CSE Mains GS PYQ data, any predictability
score, or any coverage row on `exam_id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2`.**

---

## Finding

A large share of the UPSC CSE Mains GS question corpus is **not the official
papers**. The questions are plausible, correctly formatted, numbered into the
right slots, and in the early years carry a Hindi column and an official
instruction block. They were never asked.

2013 and 2014 are fabricated at scale. 2015 is fabricated in GS1 and GS2.
2019–2022 are largely authentic. Four years cannot be judged at all because no
raw paper exists for them.

---

## Verdict by year

Counts are source-JSON rows scored against the official paper. Questions appear
in both a per-paper file and an `…ALL.json` aggregate, so distinct-question
counts are roughly half the row counts.

| year | exact | variant | orphan | unverifiable | verdict |
|---|---:|---:|---:|---:|---|
| 2013 | 2 | 0 | 184 | 0 | **fabricated** — 2 genuine questions in 4 papers |
| 2014 | 0 | 0 | 116 | 40 | **fabricated** — zero matches, max score 82.8 |
| 2015 | — | — | — | — | **fabricated in part** (see below) |
| 2016 | 0 | 0 | 0 | 118 | unknown — no raw paper |
| 2017 | 0 | 0 | 0 | 175 | unknown — no raw paper |
| 2018 | 0 | 0 | 0 | 79 | unknown — no raw paper |
| 2019 | 31 | 2 | 6 | 40 | largely authentic (GS3/GS4 scored) |
| 2020 | 21 | 7 | 11 | 40 | largely authentic (GS2/GS4 scored) |
| 2021 | 8 | 5 | 6 | 60 | largely authentic (GS4 only scorable) |
| 2022 | 56+20 | 2 | 1 | 0 | **clean** — text layer, no OCR needed |
| 2023 | 0 | 0 | 0 | 72 | unknown — no raw paper |
| 2024 | — | — | — | — | not yet checked (source rows outside glob) |
| 2025 | — | — | — | — | not yet checked (source rows outside glob) |

**2015 detail:** GS1 4 of 20 authentic (Q1/Q2/Q3/Q5 at 92/98/100/93), 16 orphan.
GS2 20 of 20 orphan — official Q1 is uniform civil code / directive principles,
the source JSON's Q1 is Governor/ordinances. GS3 19 of 20 authentic, 1 orphan.
GS4 has no raw paper and is unverifiable; its 18 rows include case studies
confirmed fabricated by manual check against the official paper.

**Orphans in 2018–2025: 24.** This is a floor, not a total — see the gate caveat
below.

---

## Where the defect entered

Traced end to end.

1. **The DB is a faithful mirror.** All 43 sampled 2013 DB rows match
   `UPSCCSEMains2013ALL.json` byte for byte, 43/43. The import script did
   exactly what it was given.
2. **The source JSONs already contained the fabrications.** They were written
   before anything was POSTed.
3. **Import timing confirms it.** 2013's 93 GS rows were written between
   06:46:11 and 06:46:35 on 2026-08-22 — 93 POSTs in 24 seconds, one
   uninterrupted sequence, genuine and fabricated rows interleaved. There is no
   write window that separates them.

So no amount of DB-side forensics could have found this, and no import fix
prevents a recurrence. The defect is upstream, in whatever produced the JSONs.

### Hypotheses tested and rejected

- **"APPEND files are the fabricated ones."** False. `…2016APPENDGS1GS2.json`
  contains the genuine 2016 GS1 paper in order. The Essay APPEND files contain
  the real 2013–2017 essay topics. APPEND is a format step — flattening
  structured bilingual JSON into flat import rows.
- **"Real head, generic tail within each paper."** False. Drawn from 2013 GS1,
  where Q1–Q8 read as verbatim-real. Against the OCR'd official papers, only 2
  questions across all four 2013 papers match. Those familiar-looking questions
  are real UPSC questions from *other years*. The generator drew on the real
  corpus, so per-file reading cannot detect it.
- **"`question_index` schema seam marks the contaminated files."** False. One
  stray field in each of two files. The confirmed fabrications are on the
  `question_number` schema. Schema does not separate clean from dirty.
- **"Hindi/English length ratio detects machine translation."** False. Flags 8
  of 25 rows in 2013 GS1 where ~17 are fabricated, and flags rows in files with
  no other sign of trouble. Devanagari is legitimately compact; 0.80–0.95 is
  normal for authentic text.
- **"2015 GS2's low scores are an artefact of un-stripped Hindi."** False.
  The scanned papers render Hindi as legacy-font ASCII (`jkds'k` = Rakesh),
  which survives a `[\x20-\x7E]+` filter. Stripping it removes 15–19% of 2015
  text and 7–10% of 2022 text and moves **zero** verdicts across 80 re-scored
  rows. The substituted-paper finding is genuine.

---

## Method, and why the verdicts are trustworthy

Full-text fuzzy match (rapidfuzz `partial_ratio`) of each source-JSON question
against the official paper for its own year+paper, and against every other raw
paper in the corpus. Verdicts: `exact` ≥95, `variant` 80–94, `wrong_year` <80
own year but ≥90 elsewhere, `orphan` <80 everywhere, `unverifiable` no readable
raw. Single 85 cut, calibrated on labelled data, not chosen.

Scanned papers were rasterized at 300 DPI and OCR'd with tesseract (eng only),
then passed through `strip_legacy_font`. OCR quality is not a limiting factor:
2013 GS4 extracted 2,456 English words at 1.3% noise.

**Separation is bimodal with no ambiguous band:**

| length class | authentic (n, min) | orphan (n, max) | gap |
|---|---|---|---:|
| long (>900 chars) | 6, 95.2 | 6, 47.9 | 47 pts |
| short (<400 chars) | 96, 92.0 | 73, 74.3 | 18 pts |

Across the full run, 180 rows sit at 50–59 and 62 at 95–100.

The long-form orphan population is the six confirmed-fabricated 2013 GS4 case
studies (`UPSCCSEMains2013ALL.json` qno 88–93), scored against the OCR'd real
2013 GS4 paper. **The strongest single result in the audit:** qno 88 is a
fabricated case study about a flyover engineer, and the real 2013 paper contains
a genuine flyover-engineer case study. Same theme, same page, and the fabricated
text still scores only 47.9. The matcher detects text, not topic — which is
exactly what a fabrication hunt requires.

### Known limitation — the confidence gate

A `<1500 raw token` gate flagged 7 short papers as low-confidence and left them
unscored: 2014 GS1, 2019 GS1/GS2, 2020 GS1/GS3, 2021 GS2/GS3. These are
legitimately short papers (670–880 clean English words), not failed extractions —
2022 GS1 scored cleanly at 854 tokens. The gate counts raw bilingual tokens, so
it penalises papers with *less* Devanagari noise. 220 rows were never scored;
orphans among them are not in the 24. Fix is to re-base the gate on English word
count and re-score from the warm cache — no re-OCR needed.

---

## Downstream — everything below was computed over this corpus

Treat all of it as suspect until recomputed over the surviving years.

- **Predictability** — computed over 13 years, three of which are fabricated.
  290 of 456 GS topics carry a score; 30 are banded `near_certain` (GS1 10,
  GS2 6, GS3 9, GS4 5). Every band inherits the fabricated years.
- **Coverage derivation** — `written=456, errors=0, derivation_version=v1.0` on
  phase `626ec667-4bbf-4420-8715-48c5b83e0d11`. Same values mirrored to the 2026
  cycle phase `f42ffb84-082e-49db-9154-9fd973e8b6e5`.
- **1,031 GS question→topic tags**, all `reviewer_status=pending`. Roughly 460
  sit in the fabricated years.
- **Planner scoring** — `0.50*coverage_priority + pyq_factor + high_yield_bonus`
  reads these coverage rows.
- **Six published blog posts** under `docs/blog/upsc-*-what-actually-gets-asked.md`
  state what UPSC asks, on this basis. They are public.
- **The study-artefact feature** (topic-level "what actually gets asked" pages)
  is blocked on this. Its entire claim is corpus fidelity.

### Not affected

- **Essay corpus.** The 2013–2017 essay topics in the source JSONs match the
  public record. 15 themes and 100 tagged essay PYQs are live and unaffected.
- **Optionals corpus.** Separate pipeline, separate provenance: English-only,
  `source_type: aggregator`, `trust_status: pending`,
  `verified_against_official: false`, `marks_source` distinguishing printed from
  inferred, structural anomalies counted (71 in PubAd) rather than smoothed.
  Not audited, but it declares its own limits — the opposite of the GS pipeline.
  Note that predictability and the six blog posts rest on it.

---

## Cannot be resolved without sourcing

**2016, 2017, 2018, 2023 have no classifiable raw paper.** They can be neither
cleared nor condemned. 372 rows.

Constraint discovered during the audit: official UPSC papers and coaching-site
copies alike are camera scans with no text layer. OCR works well on them, so
this is a sourcing problem, not an extraction problem.

Three readable PDFs remain unclassified — `02/03/04 UPSC GS Mains Paper_Final*.pdf`,
~1,900 English words of real questions, no year or paper in the filename. Opening
their cover pages by hand may cover one of the four blank years.

**Web lookups are not a substitute.** Summarised pages misreport the papers: a
check of 2022 GS4 returned an airport land-acquisition case study that does not
exist in that paper, and an Ashok/mining scenario with the specifics rewritten.
The DB was the accurate source in that comparison. Only the papers count.

---

## Other defects recorded

- `UPSCCSEMainsEssay2017-2013.json` — invalid JSON, concatenated objects with no
  wrapping array. Never parsed, so never the ingest source; something derived
  from it was.
- `MPSC-Rajyaseva-2026GS1.json` — truncated, missing the root closing brace.
  Different exam (Marathi, `text_mr`), out of scope for this audit.
- Both files carry one stray `question_index` field where every other row uses
  `question_number`. Recorded for completeness; not a contamination marker.
- 2025 GS rows in the DB have Hindi text belonging to a *different question* than
  their English (Agriculture q44, q54; Environment q47, q48). English is correct.
  Separate defect, not fabrication.
- `uq_pyq_question_one_primary_tag` exists in the live DB and in no migration.
  Unrelated to this audit, still unaddressed.

---

## Next steps

1. Re-score the 7 gated papers with an English-word-count gate. Mark rows
   `gate_relaxed=true` so the conservative count of 24 stays traceable.
2. Reconcile 2024 and 2025 against the raw DOCX (exact extraction, no OCR).
   Source rows are outside the `UPSCCSEMains*` glob.
3. Identify the three `Paper_Final*.pdf` files by cover page.
4. Decide: delete the fabricated rows and recompute predictability over the
   survivors, or source the four blank years first. Do not build on the corpus
   before this.

## Artefacts

- `scripts/reconcile_gs_sources.py` — text-layer reconciliation
- `scripts/ocr_reconcile_phase2.py` — OCR reconciliation, resumable
- `scripts/ocr_calibrate.py` — threshold calibration
- `scripts/legacy_font_validate.py` — legacy-font filter validation
- `workbench/audit/gs_source_verdict.csv` — 1,238 rows, dual question numbering
- `workbench/audit/ocr_phase2_verdict.csv` — 1,023 rows, `ocr_derived=true`
- `workbench/audit/ocr_calibration.md`, `legacy_font_filter.md`, `ocr_phase2.md`
- `workbench/audit/ocr_cache/` — 26 cached OCR texts; re-scoring needs no re-OCR

PR #1112 (topic artefact classifier) was closed against this: its verdicts were
computed over the contaminated corpus, and it committed a generated input file
without its builder.
