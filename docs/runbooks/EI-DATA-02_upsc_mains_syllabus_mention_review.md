# EI-DATA-02 — UPSC CSE Mains syllabus mention review

**Type:** Operator / data-review task (SME judgment + live backend). Not a code change.
**Goal:** Every one of the 393 `syllabus_topic_mentions` on the UPSC CSE Mains syllabus
document carries a real reviewer decision, and the document itself is promoted or rejected
on the strength of that review.

**Why a runbook and not a bulk UPDATE:** `CLAUDE.md` locks verified-only reads — user-facing
exam intelligence reads filter on `reviewer_status='verified'`. A bulk
`UPDATE ... SET reviewer_status='verified'` would fabricate review for 393 rows and put
unreviewed claims about the official syllabus in front of aspirants. Same prohibition as
EI-DATA-01.

---

## What is actually being reviewed

Each mention asserts: *this topic is present in this syllabus document*. There are two
distinct claims here and they need different scrutiny.

| Rows | `mention_type` | The claim | Review question |
|---|---|---|---|
| 30 | `explicit` | The macro topic's text **is** an official UPSC syllabus line | Does `raw_text` match the official syllabus verbatim? |
| 363 | `derived` | This micro-theme falls **within** that macro topic's scope | Is this genuinely in scope, and under the right macro topic? |

The 30 explicit rows are a fidelity check against the published UPSC syllabus — objective,
and the gate for everything else. If the macro lines are wrong, the micro-themes under them
are wrong too and no amount of micro review saves them.

The 363 derived rows are a scope judgement. They are a curator's decomposition, not UPSC
text, and were never claimed otherwise (`mention_type='derived'`, and the ingest deliberately
did not label them `explicit`). Reviewing one is a yes/no on scope, not a research task.

**A caution on `confidence_score`.** Every row carries `1.0`. That records that the JSON→DB
extraction was exact — it says nothing about whether the JSON faithfully represents UPSC's
syllabus. Do not read it as evidence of correctness.

---

## Reusable IDs

- `exam_id` (UPSC CSE) = `5466e62f-7382-4a38-ba96-2fe5fbfeaba2`
- `exam_phase_id` (Mains **template** phase, `exam_cycle_id` null) = `626ec667-4bbf-4420-8715-48c5b83e0d11`
- `syllabus_document_id` (this ingest) = `3419ba7c-e910-4886-8b5b-7b059fedb4fa`
- Source file: `docs/reference/syllabus/upsc_cse_mains_gs_micro_themes_v2026.3.json`

---

## API surface

Global prefix `/api`.

| Action | Method + path | Permission | Body |
|---|---|---|---|
| List mentions | `GET /api/admin/exam-intelligence-cms/syllabus-topic-mentions` | `exam_intelligence.cms` | — |
| Review one mention | `PATCH /api/admin/exam-intelligence/items/syllabus_topic_mention/{id}/review` | `exam_intelligence.review` | `{"reviewer_status": "verified"\|"rejected"\|"needs_correction"\|"pending", "reviewer_notes": "…"}` |
| Edit a mention's text | `PATCH /api/admin/exam-intelligence-cms/syllabus-topic-mentions/{id}` | `exam_intelligence.cms` | `WriteEnvelope` |
| Review the document | `POST /api/admin/exam-intelligence-cms/syllabus-documents/{id}/review` | `exam_intelligence.review` | `{"status": "verified"\|"rejected", "reason": "8–500 chars"}` |

`syllabus_documents` transitions: `pending → verified\|rejected`, `verified → rejected\|superseded\|pending`.

---

## Phase 0 — Fix the document's provenance first

The document row currently has **no `source_url`**. Its only anchor is a file in the repo,
which means a reviewer cannot check the mentions against anything official.

Promoting the document to `verified` in this state records that someone verified an
unanchored claim. Set the URL first:

```
PATCH /api/admin/exam-intelligence-cms/syllabus-documents/3419ba7c-…
{"reason": "…", "payload": {"source_url": "<official UPSC CSE syllabus URL>"}}
```

Do not proceed to Phase 1 until a reviewer can open the official syllabus and read along.

---

## Phase 1 — The 30 explicit macro lines (blocking gate)

Export the worksheet:

```
python scripts/syllabus_mention_review.py export \
  --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 \
  --document-id 3419ba7c-e910-4886-8b5b-7b059fedb4fa \
  --out mains_syllabus_review.csv
```

Rows are grouped so each macro topic appears immediately above the micro-themes claimed to
sit under it, ordered by paper (GS I–IV).

Filter to `mention_type = explicit` (30 rows) and compare each `text` against the official
UPSC syllabus for that paper, **word for word**. UPSC's syllabus lines are terse and specific;
a dropped clause changes scope.

Decisions:

- `verified` — matches the official line
- `needs_correction` — right topic, wrong or incomplete text. Fix via the CMS edit endpoint, then re-review
- `rejected` — not an official syllabus line at all

**Gate: if more than a handful of the 30 need correction, stop.** That indicates the source
JSON is not faithful and the fix belongs upstream in the file, followed by a re-ingest — not
393 individual corrections. Re-ingest is cheap and idempotent
(`scripts/ingest_upsc_gs_syllabus.py`); 393 hand-corrections are not.

---

## Phase 2 — The 363 derived micro-themes

Work **one macro topic at a time** — the worksheet is already grouped that way. Reading ~12
micro-themes against one official line is far faster and more consistent than reviewing rows
in isolation.

For each micro-theme ask only:

1. Does this fall within the scope of the macro topic above it?
2. Is it under the *right* macro topic? (Some themes plausibly sit under two — pick the
   better fit and note the alternative.)
3. Is it a real study unit, or a fragment of a longer list that lost its meaning?

Decisions:

- `verified` — in scope, correctly placed
- `needs_correction` — in scope but misplaced or badly worded. Note where it belongs
- `rejected` — out of scope, duplicated, or meaningless standalone

Reject freely. A rejected micro-theme costs nothing — it simply never becomes a coverage row.
A wrongly-verified one becomes a study task an aspirant works through for no reason.

Apply decisions in sittings; blanks stay pending:

```
python scripts/syllabus_mention_review.py apply --in mains_syllabus_review.csv --dry-run
python scripts/syllabus_mention_review.py apply --in mains_syllabus_review.csv
```

Re-export at any time to pick up what is still pending (`--status pending`).

---

## Phase 3 — Promote the document

Only after Phases 1–2, and only if Phase 1 passed cleanly:

```
POST /api/admin/exam-intelligence-cms/syllabus-documents/3419ba7c-…/review
{"status": "verified", "reason": "<what was checked, against which official source>"}
```

The `reason` is the audit record. State what was compared and against what — not "reviewed".

---

## Phase 4 — Confirm the downstream effect

```
python scripts/diagnose_scoring_chain.py \
  --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 \
  --exam-phase-id 626ec667-4bbf-4420-8715-48c5b83e0d11
```

Expect the mention blocker to clear. Then derive coverage **at the Mains phase scope** —
exam-wide derivation reads `exam_phase_id IS NULL` and will not see these mentions:

```
POST /api/admin/exam-intelligence/exams/5466e62f-…/coverage/derive
{"exam_phase_id": "626ec667-…", …}
```

Permission: `exam_intelligence.manage`.

### Expect flat priority — this is not a bug

With no locked score snapshots at the Mains phase, every derived row lands as:

- `coverage_depth = 'mentioned'`
- `derivation_basis = 'syllabus_only'`
- `exam_priority_score = 0`, `confidence_score = 0`, `is_high_yield = false`

The planner will have the full Mains syllabus tree but no ranking signal, so it orders topics
by syllabus sequence rather than by yield. That is the accepted trade — see the sequencing
note below.

Derivation is fingerprint-guarded and idempotent, and only ever writes rows it owns
(`source_basis='evidence_derived'`). Re-running it after PYQ scoring lands **upgrades the same
rows in place**. Nothing done here has to be redone.

---

## Sequencing note

Ranking requires locked `exam_topic_score_snapshots` at this phase, which requires verified
primary topic tags on verified Mains PYQ questions — **1,131 questions across 2013–2025**, each
needing one SME tagging decision.

The chosen sequence is to land the syllabus tree first at flat priority, then tag PYQ years
incrementally (newest first, since recency dominates frequency signal) and re-derive after
each. See `claude/upsc-syllabus-ingest-notes.md` for the current state of that backlog.

---

## Do not

- Bulk-update `reviewer_status` on mentions or the document.
- Treat `confidence_score = 1.0` as evidence the mapping is correct.
- Promote the document before its `source_url` is set.
- Run exam-wide coverage derivation and expect these mentions to be included.
- Mark the operator-validation gate passed from this runbook alone — capture live evidence
  (counts before/after, the derivation summary) per the registry's evidence rules.
