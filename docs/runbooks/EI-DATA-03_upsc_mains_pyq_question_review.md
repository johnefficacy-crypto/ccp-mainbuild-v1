# EI-DATA-03 — UPSC CSE Mains PYQ question + tag review

**Type:** Operator / data-review task (SME judgment + live backend). Not a code change.
**Goal:** Every UPSC CSE Mains PYQ question (GS I–IV + Essay, 2013–2025, ~1,031 + 100
Essay = ~1,131 rows) and its topic tags carries a real reviewer decision, so verified
questions and their verified primary tags can feed PYQ frequency scoring
(`verified_pyq_topic_counts`) and score-snapshot ranking. This is the PYQ half of the
sequencing note in `EI-DATA-02` (syllabus-mention review is the other half).

**Why a tool and not a bulk UPDATE:** `CLAUDE.md` locks verified-only reads and forbids
new AI-authored DB writes. A bulk `UPDATE ... SET reviewer_status='verified'` would
fabricate review for ~1,131 questions and every tag, leaking unreviewed content into
aspirant-facing exam intelligence. Same prohibition as `EI-DATA-01`/`EI-DATA-02`.

The tool is `scripts/pyq_question_review.py`. It makes **zero** live writes on its own —
`export` and `sweep` never write to the API, and `apply` writes nothing without both
`--apply` and `--confirm`. Nothing auto-promotes: a row reaches `verified` only via a
human `decision` typed into the worksheet.

---

## The audit-trail problem — read this first

The review endpoint **does not persist `reviewer_notes`** for either kind:

- `pyq_question` review routes through the `update_pyq_question_review_atomic` RPC, whose
  signature has no notes parameter (it cascades `reviewer_status` to the question's
  `pyq_options` rows and nothing else). Notes are dropped.
- `pyq_question_topic_tag` review is a plain table update with `supports_notes=False`.
  Notes are dropped.

So the promoted DB row carries **no record of why** it was verified. **The completed
worksheet CSV is the audit trail.** Fill in the `notes` column as you review, and
**archive the finished CSV** — do not discard it after `apply`. The tool sends
`reviewer_notes` anyway (harmless, forward-compatible if the API ever gains the column),
but it does not claim they were stored.

---

## Reusable IDs

- `exam_id` (UPSC CSE) = `5466e62f-7382-4a38-ba96-2fe5fbfeaba2`
- Mains `exam_phase_id` (shared / null-cycle) = `626ec667-4bbf-4420-8715-48c5b83e0d11`
  — a paper is treated as Mains **iff** its `exam_phase_id` equals this. Prelims/CSAT
  papers sit on other phases and are never touched by this pass.
- Section IDs (shared across years): Essay `ea24354e-0aa6-4102-a273-36773e3f52d6`,
  GS1 `daca2e9f-012e-46fc-8b10-b6df340b4200`, GS2 `d332fcad-6750-4542-af0a-3f203f819096`,
  GS3 `b5cbb735-b687-4de5-90cb-3978f48a71a1`, GS4 `dee30326-920a-40cf-bee0-a5b4c76760f7`

See `docs/pyqfrontloadnotes.md` for import state and known API bugs.

---

## API surface

Global prefix `/api`.

| Action | Method + path | Permission |
|---|---|---|
| List pending items | `GET /api/admin/exam-intelligence/exams/{exam_id}/items?kind=…&status=pending` | `exam_intelligence.review` |
| Question text (per paper) | `GET /api/admin/exam-intelligence-cms/pyq-questions?pyq_paper_id=…` | `exam_intelligence.cms` |
| Papers (Mains scoping) | `GET /api/admin/exam-intelligence-cms/pyq-papers?exam_id=…` | `exam_intelligence.cms` |
| Section labels | `GET /api/admin/exam-intelligence-cms/exam-phase-sections?exam_phase_id=…` | `exam_intelligence.cms` |
| Review one item | `PATCH /api/admin/exam-intelligence/items/{kind}/{row_id}/review` | `exam_intelligence.review` |

`kind` ∈ `{pyq_question, pyq_question_topic_tag}`. Review body is a **flat**
`{"reviewer_status": "verified\|rejected\|needs_correction\|pending", "reviewer_notes": "…"}`
— **not** the `{reason, payload}` CMS envelope. `reviewer_status` transitions: any of the
four allowed values; `pyq_question` cascades to its `pyq_options` automatically.

---

## What is being reviewed, and what the deterministic checks do

Two claims, reviewed separately:

- **Question** — is this a faithful, usable Mains PYQ stem for that paper/year/section?
- **Topic tag** — is this `topic_id` a valid catalog topic, and correctly a `primary` tag
  for that question?

`sweep` runs **deterministic checks that only ever FLAG a row — never a verdict.** No flag,
and no absence of a flag, promotes anything. Flags sort rows into *clean* vs *flagged* and
pick a spread spot-check sample from the clean set:

| Flag | Row | Meaning |
|---|---|---|
| `empty_or_short` | question | text empty or < 15 chars after stripping |
| `non_ascii_suspect` | question | non-ASCII text in a year **not** declared a legitimate bilingual/Hindi year (`--hindi-year`) — catches mojibake / extraction artefacts |
| `duplicate_text` | question | normalized text byte-identical to another question **in the same paper** (identical text in *different* papers does not flag) |
| `suspicious_repeat_char` | question | 4+ identical non-whitespace chars in a row (leftover extraction artefacts) |
| `unknown_topic` | tag | `topic_id` absent from the supplied `--topic-catalog` |
| `orphaned_topic` | tag | `topic_id` present but the catalog explicitly marks it a pre-split orphan (only fires if the catalog carries that distinction) |
| `non_primary` | tag | `tag_role != primary` (the workflow only ever created primary tags; a non-primary row is itself worth a look) |

**Flagged rows are never eligible for the clean-batch path** — they are always in the
worksheet for an individual human decision.

**The topic catalog is never derived.** `--topic-catalog` is required and must be a file
the operator supplies (a flat `[{id, subject_id, level, macro_topic, text}, …]` list of the
currently valid/reviewed topics). If no such file exists yet, produce one first; the tool
refuses to sweep without it rather than guessing a valid-id list.

**Sampling.** For each paper, from the clean set only, `min(8, ceil(20%))` rows are marked
`spot_check`, spread across the paper. These are the mandatory human eyeball before an
operator trusts a clean batch. Two verification paths to `verified`, and only these two:

1. **Passed checks AND a clean batch** — the row is clean, and its paper's spot-check
   sample was reviewed and found good, so the operator fills `verified` across that clean
   batch.
2. **Explicit human decision** — a flagged row (or any row) individually judged and
   decided in the worksheet.

---

## Phase 1 — Export (read-only)

Windows PowerShell 5.1. The tool reads `CCP_API_BASE` and `CCP_ADMIN_JWT` from the
environment. `export`/`sweep`/`apply` do not make live writes except `apply --apply
--confirm`.

```powershell
$env:CCP_API_BASE = "https://<host>"
$env:CCP_ADMIN_JWT = "<admin JWT>"

python scripts/pyq_question_review.py export `
  --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 `
  --out pyq_review_out --apply
```

Without `--apply`, `export` fetches and prints counts (Mains papers found, pending
questions/tags by year) but writes no files — a safe preview. With `--apply` it writes
`pyq_review_out/questions_export.json` and `pyq_review_out/tags_export.json`. Confirm the
per-year question counts look right (and that no Prelims/CSAT paper leaked in) before
sweeping.

If a direct API check is wanted, the same GETs run under PowerShell `Invoke-RestMethod`
(not `curl -H/-X`):

```powershell
$H = @{ Authorization = "Bearer $env:CCP_ADMIN_JWT" }
Invoke-RestMethod -Headers $H `
  -Uri "$env:CCP_API_BASE/api/admin/exam-intelligence-cms/pyq-papers?exam_id=5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
```

---

## Phase 2 — Sweep (offline; no network)

```powershell
python scripts/pyq_question_review.py sweep `
  --questions pyq_review_out/questions_export.json `
  --tags pyq_review_out/tags_export.json `
  --topic-catalog <path/to/topic_catalog.json> `
  --hindi-year 2023 `
  --out worksheet.csv --apply
```

`--hindi-year` is **not hardcoded**: confirm from the export which year(s), if any, store
non-ASCII (bilingual/Hindi) stems, and pass those. Without it every non-ASCII stem flags
`non_ascii_suspect` (safe — it only asks for a human look, never auto-verifies). Project
convention has pointed at 2023; verify against the actual export before trusting it.

Worksheet columns: `row_type`, `row_id`, `paper_year`, `question_number_or_topic_id`,
`text_preview`, `flags`, `sample_reason` (`spot_check` | `flagged` | blank), `decision`
(**blank — you fill in**), `notes` (**blank — you fill in; this is the audit trail**).

---

## Phase 3 — Review by hand

Open `worksheet.csv`. Fill `decision` (`verified` | `rejected` | `needs_correction`) for
every row you decide; leave it blank to decide later (blanks stay pending).

- **Clean batches** (blank `flags`) can be filled fast — but only after eyeballing that
  paper's `spot_check` rows and finding them sound. If a spot-check row is wrong, do not
  trust the batch; review that paper more closely.
- **Flagged rows** (`sample_reason=flagged`) need an actual look — that is the whole point
  of the flag. Reject freely: a rejected question/tag simply never feeds scoring; a wrongly
  verified one puts bad content in front of aspirants.

Fill `notes` as you go — it is the only durable record of *why*, since the DB drops it.

---

## Phase 4 — Apply

Dry-run first (default; no writes). It prints the planned counts per year per decision:

```powershell
python scripts/pyq_question_review.py apply --worksheet worksheet.csv `
  --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2
```

Then commit the decisions — **both** flags required:

```powershell
python scripts/pyq_question_review.py apply --worksheet worksheet.csv `
  --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 --apply --confirm
```

Rows with a blank `decision` are skipped and counted (they stay pending). Each year's batch
prints a summary line (verified / rejected / needs_correction / skipped) as it finishes, so
a bad batch is visible mid-run. `--sleep` (default 0.1s) spaces the calls. Re-run `export`
any time to pull whatever is still pending.

**Archive the completed `worksheet.csv`** — it is the audit trail the DB does not keep.

---

## Phase 5 — Downstream

Verified primary tags on verified Mains questions are what PYQ frequency
(`verified_pyq_topic_counts`, primary-only, conjunctive trust gates) and
`compute_exam_topic_scores` read. After a meaningful batch of years is verified, re-run
score-snapshot compute and re-derive Mains-phase coverage so ranking picks up the new
signal (see `EI-DATA-02` Phase 4 for the derivation commands and the flat-priority note).

---

## Do not

- Bulk-update `reviewer_status` on questions or tags.
- Treat a clean sweep as a verdict — a clean row is still pending until a human decides it.
- Auto-verify a flagged row "because the flag is probably fine."
- Fabricate a valid-topic-id list — supply `--topic-catalog`; the tool refuses without it.
- Touch Prelims/CSAT papers — this pass is Mains only.
- Claim `reviewer_notes` was stored, or discard the completed worksheet.
- Mark the operator-validation gate passed from this runbook alone — capture live evidence
  (counts before/after, batch summaries) per the registry's evidence rules.
```
