# Exam Governance — Backend Capability Preflight (Wave 4.6H0)

Status: investigation / preflight only. No backend, frontend, schema, or migration changes in this PR.
Generated: 2026-06-17. All claims verified against `main` after PR #700 (file:function + line anchors inline). Revised in a correction pass: workspace-readiness vs mock-readiness shapes were previously conflated; evidence normalization, stale semantics, route family, and summary scoping are now grounded against source.
Scope: prove the backend read shape required for (1) 4.6H list-level work queue and (2) 4.6I per-exam action console, before any code is written.

Grounding labels:
- **[derivable]** — already returned by, or trivially selectable from, an existing read (named).
- **[needs-join]** — computable by aggregating/joining existing reads (named) + the join described; no new column.
- **[needs-column]** — NOT truthfully computable without a new DB column/migration. RISK; this is 4.6H schema work, not a thin read.

---

## 1. Executive verdict

**What exists now.** The console list (4.6G) runs on `GET /api/admin/exam-intelligence/exams` (`admin_exam_intelligence.py:235 list_exams`), returning per-row syllabus/coverage counts + a derived `readiness_level`, paginated with an exact `total_count`. Per-exam truth lives in **two distinct readiness reads that must not be conflated**:

- **Workspace readiness** — `GET /workspace/{exam_id}/readiness` → `exam_intelligence/readiness.py:426 compute_exam_workspace_readiness`. Section-based **activation** readiness with `overall.status ∈ {empty,partial,ready,locked}`, `overall.ready_to_activate`, `overall.blockers[]`, and a `score_percent` (0–100). This is the primary input to "can this exam reach aspirants?".
- **Mock readiness** — `GET /exams/{exam_id}/mock-readiness` → `exam_intelligence/diagnostics.py:759 assemble_mock_readiness_report`. **Phase-level mock/template bank** sufficiency only, with `summary{ready,thin_bank,blocked}` against `thresholds`. It is **advisory**, not the activation verdict.

A universal evidence read exists (`evidence.py:135 get_evidence`, `GET /evidence/{kind}/{row_id}`) but returns a **raw row + a thin trust envelope**, not a normalized evidence object.

**What is missing.**
- `/exams` has **no `sort` param** (always `ORDER BY name` — `admin_exam_intelligence.py:281`) and **no workflow filters**.
- No list-level aggregate counts shaped for console chips.
- `/exams` returns **no real PYQ counts**; its `pyq_coverage_status` is a **misnomer** derived purely from coverage-row presence (`:386`), reading no `pyq_*` table.
- No per-exam "action console" read; today the console mounts the full workspace (`ExamGovernanceConsole.jsx` → `ExamWorkspace variant="console"`).
- No exam-level `state`/`jurisdiction` column anywhere.

**FE-safe vs needs-backend.**
- **Shipped, FE-safe (4.6G):** search, the six existing filters, pagination, name-first rows, readiness badge (no %). See §9.
- **Needs the 4.6H list read + summary:** canonical activation status, workflow filters, server-side sort, per-row aggregates (blocker text/count, real PYQ counts, locked-coverage count, flags).
- **Needs the 4.6I-BE per-exam read:** activation verdict, action queue, activation checks, advisory mock-readiness, normalized evidence refs.

**Blunt rules.** No fake counts in the FE. No client-side blocker-first sort — `ExamListShell.jsx` holds exactly one server-paginated page, so blocker-first ordering MUST be server-side. **`confidence_score` must be stripped server-side** from any proposed console/evidence response (not merely hidden in the FE). A thin mock bank must **not** force an exam to global `blocked`.

---

## 2. Current `/exams` contract (exact)

Source: `app/backend/app/api/admin_exam_intelligence.py:235-397` (`list_exams`).

- **Path:** `GET /api/admin/exam-intelligence/exams`
- **Params (the ONLY supported set):** `limit` (1–200, def 100), `offset` (≥0); `q` (name/slug `ilike` after `_sanitize_q` — `:254-256`); `exam_type` (`eq`); `active_state ∈ {active,inactive,all}`, else 422 (`:247-262`); `management_mode` (`eq`, `__null__` sentinel → `is null`; **default excludes `archive`** — `:264-271`); `cadence` (`eq`); `exam_family_id` (`eq`).
- **Ordering:** `.order("name")` asc — `:281`. **No sort param.**
- **Pagination:** PostgREST `count="exact"` → `total_count`; `has_next = offset + len(items) < total_count`.
- **Base columns** (`:280`): `id, slug, name, exam_type, is_active, exam_family_id, management_mode, cadence`.
- **Derived per-row** (two batched child reads over the *page's* `exam_ids`, each `.limit(20000)`):
  - `syllabus_topic_mentions(exam_id,reviewer_status)` → `syllabus_verified` (verified), `syllabus_pending` (pending/needs_correction).
  - `exam_topic_coverage(exam_id,reviewer_status,is_high_yield)` → `coverage_total`, `verified_topic_count` (locked+reviewed), `high_yield_topic_count`.
  - `pyq_coverage_status` = `"covered"` iff `coverage_total>0` else `"none"` (`:386`). **RISK: not PYQ data** — relabels coverage presence; reads no `pyq_*` table.
  - `readiness_level` (`:372-377`): `ready` if `verified_topic_count>0`; else `partial` if `syllabus_verified>0`; else `not_ready`. **Looser than planner-consumable** (planner needs `locked` only — §7).
- **Not returned:** `state`/`jurisdiction`/`organization`; any `last_touched`/`updated_at`; real verified/total PYQ counts; locked-only coverage count; blocker count/text; stale flags; competition/update signals.

---

## 3. Current workspace / readiness / context reads (corrected shapes)

### 3a. Workspace readiness (activation) — exact shape
`GET /api/admin/exam-intelligence/workspace/{exam_id}/readiness` → `readiness.py:426 compute_exam_workspace_readiness`:
```json
{
  "exam_id": "…", "cycle_id": null, "generated_at": "…",
  "overall": { "status": "empty|partial|ready|locked", "score_percent": 0, "ready_to_activate": false, "blockers": [] },
  "sections": [ { "section": "setup", "label": "Setup", "status": "empty|partial|ready|locked", "score_percent": 0, "weight": 1, "blockers": [] } ],
  "topic_coverage": { } 
}
```
- Sections (`readiness.py:433-442`): `setup, documents, syllabus_mapper, pyq_workbench, updates, competition, review_activate`.
- `overall.status` derived from `score_percent` (`:456-463`): 0→`empty`, ≥80→`ready`, 100→`locked`, else `partial`. `ready_to_activate = review_activate.status ∈ {ready,locked}` (`:454`).
- **`overall.score_percent` and every section `score_percent` exist internally** (`_STATUS_SCORE`: empty=0, partial=50, ready=80, locked=100 — `:22-23`). **They must be omitted from the proposed console API and operator UI.**
- It does **not** return `thresholds`, `phases[]`, or `ready/thin_bank/blocked`. Those belong to mock readiness.

### 3b. Mock readiness (advisory, phase-level) — exact shape
`GET /api/admin/exam-intelligence/exams/{exam_id}/mock-readiness` → `diagnostics.py:759 assemble_mock_readiness_report` (wrapped by `admin_exam_intelligence.py:1778 exam_mock_readiness`):
```json
{
  "exam_id": "…", "exam_phase_id": null, "generated_at": "…",
  "thresholds": { "min_per_section": 30, "min_locked_coverage": 1 },
  "summary": { "ready": 0, "thin_bank": 0, "blocked": 0 },
  "phases": [ { "exam_phase_id": "…", "readiness_verdict": { "sections": [ { "verdict": "ready|thin_bank|blocked", "reasons": ["missing_structure","no_locked_coverage","thin_mcq_pool"] } ] } } ],
  "skipped": []
}
```
- Measures **mock/template content sufficiency per phase only**. Carries **no `score_percent`**. Its `ready/thin_bank/blocked` tokens describe the mock bank, **not** exam activation.

### 3c. Other reads

| Read | Source | Provides | Reuse for 4.6I |
|---|---|---|---|
| Workspace context | `admin_exam_intelligence.py:1575 exam_workspace_context` | `exam(*)`, `cycles`, `phases`, `organization{id,name,type,trust_tier}` (via `conducting_organization_id`), `family{id,name,slug}`, `readiness:null` | identity/org/family |
| Overview KPIs (catalogue) | `admin_exam_intelligence.py:124 overview` | global counts incl. `stale_review_items` (14-day; §12), locked-coverage status logic | stale-review grounding |
| Topic coverage (locked) | `coverage.py: locked_topic_coverage_summary / locked_topic_coverage` | locked rows w/ topic/subject, `is_high_yield`, `exam_priority_score`, `reviewer_status` (and `confidence_score` — to be dropped) | per-topic; aggregate for counts |
| Verified PYQ depth | `coverage.py: verified_pyq_topic_counts` | `{topic_id: verified_pyq_count}` (joins verified `pyq_papers/pyq_questions/pyq_question_topic_tags`) | sum for a row count |
| Documents | `admin_exam_intel_documents.py:407 list_documents` | document assets + extraction/page status | documents check |
| Updates | `update_context.py:85 policy_update_context` | `official_updates[]` w/ `published_at,effective_from,created_at`, `affects_*` | updates check + official-intelligence staleness |
| Competition | `competition_context.py:110 competition_context` | per-exam vacancy/applicant/pressure + `trust{…,confidence_score,…}` (to be dropped) | competition check |
| Evidence (raw) | `evidence.py:135 get_evidence` | raw row + thin trust envelope (see §3d) | reference; needs normalization |
| Planner consumability | `planner.py: _compute_plan` (`reason="no_locked_coverage"`) / `_load_locked_coverage` | "planner-ready iff ≥1 `locked` coverage row" | hard gate for verdict |

Grouping:
- **Already reusable:** workspace readiness, workspace context, documents, updates, competition, planner locked gate.
- **Advisory/separate:** mock readiness (do not use as activation verdict).
- **Useful but insufficient:** `verified_pyq_topic_counts` (per-topic), `locked_topic_coverage*` (per-topic), evidence (raw, not normalized).
- **Unsafe to expose:** `confidence_score` (strip server-side); slug-derived `state` (§12).

### 3d. Evidence — actual returned shape
`evidence.py:162-171 get_evidence` returns:
```json
{ "kind": "…", "id": "…", "row": { /* raw projected columns */ },
  "trust": { "status": "…", "confidence_score": 0.0, "reviewed_at": "…" } }
```
It does **not** universally normalize `source_label / source_url / source_kind / location|page|row / basis / reviewer_status / trust_status / updated_at`. Those fields live inconsistently inside `row` per `kind` (`_KIND_MAP`), or not at all.

---

## 4. Prototype feature matrix

### Landing / list-level

| Feature | Current support | Source | Label | Decision | Wave |
|---|---|---|---|---|---|
| Primary status `blocked`/`needs_action`/`ready` (mutually exclusive) | none | workspace readiness `overall` + planner locked gate (§3a,§3c) | [needs-join] | canonical model §5 | 4.6H |
| Blocked count | none | per-exam activation verdict | [needs-join] | summary §5 | 4.6H |
| Needs-action count | none | per-exam activation verdict | [needs-join] | summary §5 | 4.6H |
| Ready count | none | `planner._compute_plan` locked gate + `ready_to_activate` | [needs-join] | summary §5 | 4.6H |
| Pending-review count (flag) | none | `syllabus_topic_mentions`/`exam_topic_coverage` `reviewer_status` | [needs-join] | flag §5 | 4.6H |
| `stale_review_queue` (flag) | yes, 14-day, catalogue KPI | `admin_exam_intelligence.py:45 _STALE_REVIEW_DAYS=14`, `overview().stale_review_items` | [needs-join] | flag §5/§12 | 4.6H |
| `stale_official_intelligence` (flag) | partial (per-exam 30-day in readiness `_updates`) | `readiness.py:35 _STALE_DAYS=30` | [needs-join] (per-exam) / OPEN (catalogue) | OPEN DECISION §12 | 4.6H? |
| `thin_mock_bank` (flag, **not a blocker**) | advisory | mock-readiness `summary.thin_bank` (§3b) | [needs-join] | **DEFERRED** — an exam-total approximation is not equivalent to the section-attributed diagnostic; exact list aggregation is future work | 4.6I-BE+ |
| Workflow chips | none | the counts/flags above | [needs-join] | server-side filter+count | 4.6H |
| Blocker-first sort | none | activation verdict per exam | [needs-join] | **server-side only** | 4.6H |
| Management-lane sort | column exists, no sort | `exams.management_mode` | [derivable] | add `sort` value | 4.6H |
| Recent-activity sort | none | `last_touched` (§12) | [needs-join]/[needs-column] | resolve `last_touched` | 4.6H |
| Row `blocker_count`/`first_blocker_text` | none | workspace readiness `overall.blockers[]` / section blockers | [needs-join] | list read | 4.6H |
| Row `verified_pyq_count` | none (misnamed `pyq_coverage_status`) | `coverage.py:verified_pyq_topic_counts` (sum) | [needs-join] | list read | 4.6H |
| Row `total_pyq_count` | none | `pyq_questions` per-exam count | [needs-join] | list read | 4.6H |
| Row `locked_coverage_count` | partial (`verified_topic_count`=locked+reviewed) | `exam_topic_coverage reviewer_status='locked'` | [needs-join] | split locked-only | 4.6H |
| Row `missing_coverage`/`missing_pyq` (flags) | none | locked-coverage / verified-PYQ aggregates | [needs-join] | flags §5 | 4.6H |
| Row `last_touched` | none | audit log / child `*_at` (§12) | [needs-join]/[needs-column] | §12 | 4.6H |
| State/jurisdiction | none | — | **[needs-column]**; slug-parse UNSAFE | migration | 4.6H |
| Organization name | via context only | `exam_workspace_context` → `organizations.name` | [needs-join] | list read | 4.6H |

### Per-exam console (4.6I)

| Feature | Current support | Source | Label |
|---|---|---|---|
| `activation_verdict` ("can reach aspirants?") | none assembled | workspace readiness sections + `ready_to_activate` + planner locked gate + lifecycle checks | [needs-join] |
| `mock_readiness` (advisory) | yes | `diagnostics.py:assemble_mock_readiness_report` | [derivable] |
| action-queue item | none | readiness blockers + per-area reads | [needs-join] |
| Activation: setup | yes | `exam_workspace_context` (cycles/phases) | [derivable] |
| Activation: documents | yes | `list_documents` | [derivable] |
| Activation: syllabus | yes | `syllabus_topic_mentions` | [derivable] |
| Activation: topic_coverage (hard gate) | yes | `exam_topic_coverage` locked / `planner._compute_plan` | [needs-join] |
| Activation: pyq | yes | `coverage.py:verified_pyq_topic_counts` | [needs-join] |
| Activation: updates | yes | `update_context.py:policy_update_context` | [derivable] |
| Activation: competition | yes | `competition_context.py` | [derivable] |
| Activation: mock_readiness (advisory) | yes | mock-readiness | [derivable] |
| Activation: publish (hard gate) | yes | workspace readiness `ready_to_activate` | [needs-join] |
| Stages (setup/evidence/review/activation) | n/a | UI grouping over checks | [derivable] |
| Evidence (normalized) | raw only | `evidence.py` + joins (§3d, §6) | [needs-join]/extension |
| Evidence drawer **no %** | rows carry `confidence_score` | strip server-side | [derivable] |

---

## 5. Proposed minimal backend read shape — LIST (4.6H)

**Route family (static-first, consistent):**
```
GET /api/admin/exam-intelligence/console/exams
GET /api/admin/exam-intelligence/console/exams/{exam_id}
GET /api/admin/exam-intelligence/console/summary
```
Leave `/exams` unchanged (Registry + 4.6G `ExamListShell` depend on it). The console rows/detail/summary are a separate, console-shaped family — avoids overloading `/exams` and avoids static/dynamic path ambiguity.

### Canonical work-queue model (mutually exclusive primary status)
Exactly one of:
- **`blocked`** — one or more hard activation/planner gates fail (e.g. required setup missing, **no locked planner coverage**, no usable required evidence).
- **`needs_action`** — no hard blocker, but ≥1 pending/partial/stale-review/incomplete check remains.
- **`ready`** — all required activation gates pass; **must satisfy locked planner-consumable coverage** (`planner._compute_plan` would not return `no_locked_coverage`). "Reviewed coverage exists" alone is NOT ready.

**Orthogonal flags shipped in 4.6H** (may overlap with any non-`ready` status; may overlap each other): `pending_review`, `missing_pyq`, `missing_coverage`, `stale_review_queue`.

`thin_mock_bank` is **deferred from 4.6H**: a truthful flag needs the section-attributed, `question_type`/`valid_until`-aware diagnostic (`assemble_mock_readiness_report`, per-exam), not an exam-total count. It remains an advisory object for 4.6I-BE (one diagnostic call for the selected exam); a set-based catalogue/list aggregation is future work and is NOT automatically solved by 4.6I-BE. `stale_official_intelligence` likewise stays excluded (open threshold, §12).

Rules: the three primary statuses are **mutually exclusive** and their summary counts **do not overlap**. Flag counts **may** overlap.

### `GET /console/exams` row (concrete)
```json
{
  "items": [
    { "id": "…", "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment",
      "management_mode": "core", "cadence": "annual", "exam_family_id": "…",
      "organization_name": "Staff Selection Commission",
      "status": "blocked",
      "flags": ["missing_coverage","missing_pyq","stale_review_queue"],
      "blocker_count": 2, "first_blocker_text": "No locked topic coverage",
      "locked_coverage_count": 0, "verified_pyq_count": 0, "total_pyq_count": 42,
      "last_touched": "2026-05-30T12:00:00Z" }
  ],
  "count": 25, "total_count": 130, "limit": 25, "offset": 0, "has_next": true
}
```
- **Filters:** existing six [derivable] + workflow filters `needs_action|blocked|missing_pyq|missing_coverage|stale_review_queue|ready` — each [needs-join]. (`thin_mock_bank` deferred, above.)
- **Sort:** `management_lane` [derivable]; `blockers_first` [needs-join]; `recent_activity` [needs-join]/[needs-column] (gated on `last_touched`, §12).
- **No raw DB leakage:** `organization_name` not `conducting_organization_id`; `status`/`flags` tokens not raw `reviewer_status`; no UUIDs in labels; **no `score_percent`, no `confidence_score`.**

### `GET /console/summary`
Accepts the **same base filters** as the list (`exam_type, active_state, management_mode, cadence, exam_family_id`, and `q`). Counts always reflect the **same scope** as the filtered list so chips never disagree with rows.
- **`q` scoping decision: YES** — `q` scopes summary counts, for chip/list consistency during text search. (The FE must never show global counts beside a filtered list.)
```json
{ "blocked": 12, "needs_action": 31, "ready": 64,
  "pending_review": 19, "stale_review_queue": 8,
  "total_count": 107, "generated_at": "…" }
```
Five counts: three mutually-exclusive primaries (`blocked`,`needs_action`,`ready`) + two overlap-allowed flags (`pending_review`,`stale_review_queue`). **`thin_mock_bank` and `stale_official_intelligence` are intentionally excluded** — the former is deferred (not equivalent set-based), the latter pending a locked threshold (§12).

---

## 6. Proposed minimal backend read shape — PER-EXAM CONSOLE (4.6I-BE)

`GET /api/admin/exam-intelligence/console/exams/{exam_id}`:
```json
{
  "exam": { "id": "…", "slug": "ssc-cgl", "name": "SSC CGL", "organization_name": "…", "family_name": "…" },
  "activation_verdict": { "status": "blocked|needs_action|ready", "headline": "Not ready for aspirants",
                          "reasons": ["No locked topic coverage"] },
  "mock_readiness": { "status": "blocked|thin_bank|ready|unknown", "detail": "2 of 5 sections thin" },
  "action_queue": [
    { "id": "coverage-locked", "severity": "blocker", "area": "topic_coverage",
      "title": "Lock topic coverage", "why": "Planner reads only locked coverage rows; none exist yet.",
      "cta_label": "Open topic coverage", "cta_route": "/admin/exam-intelligence/workspace/<exam_id>",
      "entity_kind": "exam_topic_coverage", "entity_id": null,
      "evidence_refs": [ { "kind": "exam_topic_coverage", "row_id": "…" } ], "status": "open" }
  ],
  "activation_checks": [
    { "area": "setup",          "gate": "hard",     "state": "done",    "detail": "1 cycle · 2 phases", "reasons": [] },
    { "area": "documents",      "gate": "advisory", "state": "done",    "detail": "3 documents extracted", "reasons": [] },
    { "area": "syllabus",       "gate": "advisory", "state": "partial", "detail": "12 verified · 4 pending", "reasons": [] },
    { "area": "topic_coverage", "gate": "hard",     "state": "blocked", "detail": "0 locked", "reasons": ["no_locked_coverage"] },
    { "area": "pyq",            "gate": "advisory", "state": "blocked", "detail": "0 verified PYQ", "reasons": [] },
    { "area": "updates",        "gate": "advisory", "state": "needs_action", "detail": "2 pending review", "reasons": [] },
    { "area": "competition",    "gate": "advisory", "state": "done",    "detail": "reviewed", "reasons": [] },
    { "area": "mock_readiness", "gate": "advisory", "state": "thin_bank", "detail": "thin mock bank (advisory)", "reasons": ["thin_mcq_pool"] },
    { "area": "publish",        "gate": "hard",     "state": "blocked", "detail": "blocked by coverage", "reasons": [] }
  ],
  "stages": [
    { "id": "setup",      "label": "Setup",      "areas": ["setup","documents"] },
    { "id": "evidence",   "label": "Evidence",   "areas": ["syllabus","topic_coverage","pyq"] },
    { "id": "review",     "label": "Review",     "areas": ["updates","competition","mock_readiness"] },
    { "id": "activation", "label": "Activation", "areas": ["publish"] }
  ],
  "evidence_refs": [ { "kind": "exam_topic_coverage", "row_id": "…" } ],
  "generated_at": "…"
}
```

Rules:
- **`activation_verdict` is NOT a mock-readiness token.** It derives from workspace-readiness sections + `overall.ready_to_activate` + the planner locked-coverage gate + required lifecycle checks. `mock_readiness` is a **separate advisory** object; `thin_bank` there never forces `activation_verdict.status = blocked`.
- Each `activation_checks[]` entry declares `gate` (`hard` vs `advisory`), `source` read (per §3c), `state`, `detail`, and `reasons[]`. Hard gates: `setup`, `topic_coverage`, `publish`. `mock_readiness` and `pyq` are advisory (do not block activation by themselves).
- **No `score_percent` / `confidence_score` / any percentage** anywhere in this response.
- `cta_route` uses existing workspace routes [derivable].

---

## 7. Existing-read reuse plan (per proposed field)

| Proposed field | Source read | Label |
|---|---|---|
| existing six filters | `/exams` `list_exams` params | [derivable] |
| `management_lane` sort | `exams.management_mode` | [derivable] |
| `organization_name` / `family_name` | `exam_workspace_context` → `organizations.name` / `exam_families.name` | [needs-join] |
| primary `status` / `activation_verdict` | `readiness.py:compute_exam_workspace_readiness` (`overall`, sections) + `planner._compute_plan` locked gate | [needs-join] |
| `blocker_count`, `first_blocker_text` | `readiness.py` `overall.blockers[]` / section `blockers[]` | [needs-join] |
| `locked_coverage_count` | `exam_topic_coverage reviewer_status='locked'` (`coverage.py:locked_topic_coverage`) | [needs-join] |
| `verified_pyq_count` | `coverage.py:verified_pyq_topic_counts` (sum) | [needs-join] |
| `total_pyq_count` | `pyq_questions` per-exam count | [needs-join] |
| `mock_readiness` | `diagnostics.py:assemble_mock_readiness_report` | [derivable] |
| `pending_review` flag | `syllabus_topic_mentions`/`exam_topic_coverage` `reviewer_status` | [needs-join] |
| `stale_review_queue` flag | `admin_exam_intelligence.py:_STALE_REVIEW_DAYS=14` / `overview().stale_review_items` | [needs-join] |
| `stale_official_intelligence` flag | `readiness.py:_STALE_DAYS=30` (`_updates`) per-exam; catalogue threshold OPEN | [needs-join] / OPEN |
| `thin_mock_bank` flag | mock-readiness `summary.thin_bank` (per-exam diagnostic) | [needs-join] — **deferred from 4.6H** |
| activation checks (setup/documents/updates/competition) | context / `list_documents` / `policy_update_context` / `competition_context` | [derivable] |
| activation checks (topic_coverage/pyq/publish) | coverage + verified PYQ + `ready_to_activate` | [needs-join] |
| evidence (normalized) | `evidence.py:get_evidence` + joins to document assets/pages, source registry, PYQ paper/question, policy-update source, competition evidence | [needs-join]/extension |
| `last_touched` | audit log / child `*_at` (§12) | [needs-join] / [needs-column] |
| `state` / `jurisdiction` | no existing read | [needs-column] |
| **server-side strip** of `confidence_score` | omit in console/evidence projection | [derivable] |

---

## 8. Fields that MUST NOT be faked in the FE

blocked count · needs-action count · ready count · pending_review count · stale_review_queue count; per-row `missing_pyq`/`missing_coverage`/`stale_*` flags, `blocker_count`, `first_blocker_text`, `verified_pyq_count`, `total_pyq_count`, `locked_coverage_count`, `last_touched`; `blockers_first`/`recent_activity` ordering; per-exam `activation_verdict`, activation-check completion count, evidence count. The FE holds one server-paginated page (`ExamListShell.jsx`); none of these can be honestly synthesized client-side.

---

## 9. 4.6G safe subset already shipped (record)

Live on `main` (`ExamGovernanceConsole.jsx` → `ExamListShell.jsx`, PR #700): search (`q`); the six existing filters; `limit`/`offset` pagination; name-first rows; slug secondary; readiness badge from `readiness_level` (**no %**); console primary → `/console/:exam_id`; advanced-workspace secondary → `/workspace/:exam_id`; **no** workflow chips; **no** aggregate/fake counts; **no** blocker-first sort; empty/error states render no seed data. These stay; 4.6H/4.6I add to them.

---

## 10. 4.6H implementation recommendation (list + summary only)

- **Endpoints:** `GET /console/exams` (rows: existing filters + `sort` + workflow filters + per-row aggregates) and `GET /console/summary` (the five counts, same-scope filters incl. `q`). Leave `/exams` unchanged.
- **Canonical semantics:** implement the mutually-exclusive `blocked|needs_action|ready` model + orthogonal flags (§5).
- **Service module:** new read-only helper, e.g. `app/backend/app/exam_intelligence/work_queue.py`, composing existing reads set-based (group-by over `exam_topic_coverage`/`syllabus_topic_mentions`/`exam_policy_updates`/mock-readiness inputs) — **never N+1 per exam**.
- **Tests:** unit tests for status derivation (locked gate → `ready`; thin mock bank → flag, not `blocked`), each `sort`, each workflow filter, summary same-scope, and guards that responses carry **no** `confidence_score`, **no** `score_percent`, **no** raw `conducting_organization_id`.
- **Schema:** only if `state`/`jurisdiction` ([needs-column]) or a denormalized `last_touched` ([needs-column] fallback) is required — call out explicitly.
- **UI:** none beyond wiring chips/counts/sort once backend lands.

## 11. 4.6I implementation recommendation

- **4.6I-BE first:** add `GET /console/exams/{exam_id}` returning the §6 shape — `activation_verdict` (separate from `mock_readiness`), `action_queue`, `activation_checks` (hard vs advisory), `stages`, normalized `evidence_refs`, with **server-side confidence stripping**.
- **4.6I-FE after the contract lands:** render the prototype-aligned per-exam console — verdict strip → blocker-first action queue → activation checks → stages → evidence drawer (references `/evidence/{kind}/{row_id}`, renders **no** confidence %). Reuse existing workspace panels where they fit; **do not fork the PYQ Workbench**; no workspace redesign; no mutation/route changes beyond the new read. 4.6I is **backend-first**, not primarily FE work.

---

## 12. Computability verdicts (concrete)

- **`stale_review_queue`** → **[needs-join]**, threshold already defined: `admin_exam_intelligence.py:45 _STALE_REVIEW_DAYS = 14` ("A review row is 'stale' once it has sat un-actioned for this long"), used by `overview()` to compute `stale_review_items` (`:177-202`). Reuse this exact 14-day rule for the review-queue backlog flag.
- **`stale_official_intelligence`** → distinct product concept; **OPEN DECISION**. A 30-day threshold for stale *policy/official updates* exists per-exam in `readiness.py:35 _STALE_DAYS = 30` (`_updates`, `:300-306`), but a catalogue-level "official intelligence stale" semantics/threshold is **not locked**. **Do not invent 90 days**; do not claim catalogue support until source semantics + threshold are defined. (The 14-day `_STALE_REVIEW_DAYS` and the 30-day `_STALE_DAYS` are **different KPIs** — review-queue backlog vs policy-update freshness — and must not be merged.)
- **`last_touched`** → **[needs-join]** (preferred) **/ [needs-column]** (fallback). Truthful value = `max` of relevant child timestamps: `exam_topic_coverage.reviewed_at/created_at`, `exam_policy_updates.published_at`, `syllabus_topic_mentions.reviewed_at`, plus `admin_audit_logs.created_at` filtered by `entity_id` (`admin_community_governance.py:_audit`). That cross-table `max` is a join. If too costly per request, denormalize `exams.last_touched` → [needs-column] (RISK).
- **`state` / `jurisdiction`** → **[needs-column] + UNSAFE to derive.** No `state` field on `exams`, on the `organizations` projection (`id,name,type,trust_tier`), or in `competition_context.py`. Slug-parsing is explicitly disallowed. Recommend a real column before any State display.
- **`evidence` normalization** → **[needs-join]/endpoint-extension.** `evidence.py:get_evidence` returns `{kind,id,row,trust{status,confidence_score,reviewed_at}}` — raw, not normalized. A normalized object (`source_label/source_url/source_kind/location|page|row/basis/reviewer_status/trust_status/updated_at`) needs joins to document assets/pages, source registry, PYQ paper/question context, policy-update source, and competition evidence. Keep `{kind,row_id}` refs in the console read; do the normalization in an extended/new evidence read. **`confidence_score`/`confidence_percent` must be omitted server-side** from the console/evidence response — never return a percentage-shaped confidence field to the client.
- **List aggregate counts** → **[needs-join], set-based.** `/exams` today does two batched child reads capped at 20000 rows **for one page's `exam_ids` only**. Catalogue-wide counts must be computed with set-based group-by in `work_queue.py` (and may be briefly cached), **not** N+1 per-exam readiness calls.
