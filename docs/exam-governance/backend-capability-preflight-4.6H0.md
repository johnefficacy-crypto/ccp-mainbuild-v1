# Exam Governance — Backend Capability Preflight (Wave 4.6H0)

Status: investigation / preflight only. No backend, frontend, schema, or migration changes in this PR.
Generated: 2026-06-17. All claims verified against `main` after PR #700 (file:function + line anchors inline).
Scope: prove the backend read shape required for (1) 4.6H list-level work queue and (2) 4.6I per-exam action console, before any code is written.

Grounding labels used throughout (per PR discipline):
- **[derivable]** — already returned by, or trivially selectable from, an existing read (named).
- **[needs-join]** — computable by aggregating existing reads (named) + the join described; no new column.
- **[needs-column]** — NOT truthfully computable without a new DB column/migration. Flagged as a RISK; this is 4.6H schema work, not a thin read.

---

## 1. Executive verdict

**What exists now.** The console list (4.6G) runs on `GET /api/admin/exam-intelligence/exams` (`admin_exam_intelligence.py:235 list_exams`), which already returns per-row syllabus/coverage counts and a derived `readiness_level`, paginated with an exact `total_count`. Per-exam truth (readiness verdict, locked coverage, verified PYQ depth, competition, policy updates, evidence) all exist as **separate** reads, each grounded below. A universal evidence read (`evidence.py:135 get_evidence`, `GET /evidence/{kind}/{row_id}`) already deep-links 8 reviewable kinds.

**What is missing.**
- `/exams` has **no `sort` param** (always `ORDER BY name` — `admin_exam_intelligence.py:281`) and **no workflow filters** (`needs_action`, `blocked`, `missing_pyq`, …).
- `/exams` returns **no list-level aggregate counts** (blocked/ready/pending/stale).
- `/exams` returns **no real PYQ counts**; its `pyq_coverage_status` is a **misnomer** derived purely from coverage row presence (`admin_exam_intelligence.py:386`), not from `pyq_*` tables.
- No per-exam "action console" read exists; today the console mounts the full workspace (`ExamGovernanceConsole.jsx` → `ExamWorkspace variant="console"`).
- No exam-level `state`/`jurisdiction` column anywhere (confirmed absent in `exams`, `organizations` select, `competition_context.py`).

**FE-safe vs needs-backend.**
- **FE-safe, already shipped (4.6G):** search, the 6 existing filters, pagination, name-first rows, readiness badge (no %). See §9.
- **Needs extending the list read (4.6H):** every workflow chip, every aggregate count, `sort=blockers_first|recent_activity|management_lane`, per-row `blocker_count`/`first_blocker_text`/real PYQ counts/`locked_coverage_count`/`stale`/`last_touched`. All are **[needs-join]** (computable from existing reads) **except** `state`/`jurisdiction` (**[needs-column]**) and a cheap single-field `last_touched` (**[needs-join]** via audit log, or **[needs-column]** if a single `exams.updated_at`-style field is wanted).
- **Needs a new per-exam console read (4.6I):** verdict, action queue, activation checks, stages, evidence refs.

**Blunt rules carried forward.** No fake counts in the FE. No client-side "blocker-first" sort — the FE holds **one** server-paginated page (`ExamListShell.jsx`), so honest blocker-first ordering MUST be server-side. No confidence percentage in the evidence drawer, even though some evidence rows physically carry `confidence_score`.

---

## 2. Current `/exams` contract (exact, by inspection)

Source: `app/backend/app/api/admin_exam_intelligence.py:235-397` (`list_exams`).

- **Path:** `GET /api/admin/exam-intelligence/exams`
- **Params (the ONLY supported set):**
  - `limit` (int, 1–200, default 100), `offset` (int, ≥0, default 0) — `:237-238`
  - `q` — name/slug `ilike` via `or_(name.ilike.%q%,slug.ilike.%q%)` after `_sanitize_q` — `:254-256`
  - `exam_type` — `eq` — `:257-258`
  - `active_state` ∈ {`active`,`inactive`,`all`} (422 otherwise) — `:247-262`
  - `management_mode` — `eq`, plus `__null__` sentinel → `is null`; **default excludes `archive`** (`management_mode.is.null,management_mode.neq.archive`) — `:264-271`
  - `cadence` — `eq` — `:272-273`
  - `exam_family_id` — `eq` — `:274-275`
- **Ordering:** `.order("name")` ascending — `:281`. **No sort param exists.**
- **Pagination:** PostgREST `count="exact"` → `total_count`; `has_next = offset + len(items) < total_count` — `:280-396`. (Test stub emulates range/count manually — `:295-298`.)
- **Base columns selected** (`:280`): `id, slug, name, exam_type, is_active, exam_family_id, management_mode, cadence`.
- **Derived per-row fields** (two batched child reads over the *page's* `exam_ids`, each `.limit(20000)`):
  - From `syllabus_topic_mentions(exam_id, reviewer_status)` — `:311-321` → `syllabus_verified` (status=`verified`), `syllabus_pending` (status∈{`pending`,`needs_correction`}) — `:339-347`.
  - From `exam_topic_coverage(exam_id, reviewer_status, is_high_yield)` — `:325-335` → `coverage_total`, `verified_topic_count` (status∈{`locked`,`reviewed`}), `high_yield_topic_count` — `:351-362`.
  - `pyq_coverage_status` = `"covered"` iff `coverage_total>0` else `"none"` — `:386`. **RISK: this is NOT PYQ data** — it never reads any `pyq_*` table; it is a relabel of coverage presence.
  - `readiness_level` — `:372-377`: `ready` if `verified_topic_count>0`; else `partial` if `syllabus_verified>0`; else `not_ready`. **Note:** "ready" here counts `locked`+`reviewed`, which is **looser** than planner-consumable (planner requires `locked` only — see §3/§7).
- **Fields NOT returned:** `state`/`jurisdiction`/`organization`; any `last_touched`/`updated_at`; real verified/total PYQ counts; locked-only coverage count; blocker count or text; `stale` flag; competition or policy-update signals.

---

## 3. Current workspace / readiness / context reads

| Read | Source (file:function:line) | Provides | Reuse class for 4.6I |
|---|---|---|---|
| Workspace context | `admin_exam_intelligence.py:1575 exam_workspace_context` | `exam(*)`, `cycles`, `phases`, `organization{id,name,type,trust_tier}` (via `exams.conducting_organization_id`), `family{id,name,slug}`, `readiness:null` | **Reusable** for identity/org/family |
| Workspace readiness | `admin_exam_intelligence.py:1761 exam_workspace_readiness` → `exam_intelligence/readiness.py:compute_exam_workspace_readiness` | `thresholds`, `summary{ready,thin_bank,blocked}`, `phases[]`, `generated_at` | **Reusable** for verdict inputs |
| Mock-readiness (verdict, **no %**) | `admin_exam_intelligence.py:1778 exam_mock_readiness` → `exam_intelligence/diagnostics.py:759 assemble_mock_readiness_report` | per-section `verdict ∈ {ready,thin_bank,blocked}` + `reasons ∈ {missing_structure,no_locked_coverage,thin_mcq_pool}`, `summary{ready,thin_bank,blocked}` | **Reusable** — primary verdict source; carries NO score_percent |
| Topic coverage (locked) | `exam_intelligence/coverage.py: locked_topic_coverage_summary / locked_topic_coverage` | locked rows w/ topic/subject, `is_high_yield`, `exam_priority_score`, `confidence_score`, `reviewer_status` | Useful but **per-topic**; needs aggregation for counts |
| Verified PYQ depth | `exam_intelligence/coverage.py: verified_pyq_topic_counts` | `{topic_id: verified_pyq_count}` (joins `pyq_papers`+`pyq_questions`+`pyq_question_topic_tags`, all `verified`) | Useful; **sum needed** for a row count |
| Documents | `admin_exam_intel_documents.py:407 list_documents` (+ `_shape/_extraction_status/_pages_count`) | admin document assets, extraction status, page count | **Reusable** for documents activation check |
| Syllabus | `/exams/{exam_id}/items?kind=syllabus_topic_mention` (`admin_exam_intelligence.py:401`) + `syllabus_topic_mentions` | per-mention reviewer_status | **Reusable** |
| PYQ | `pyq_papers.py: verified_pyq_papers / difficulty_heatmap`; `exam_intelligence/status.py:106 exam_intelligence_summary` | papers, verified counts, heatmap | Useful; insufficient for total-vs-verified row counts (see §12) |
| Updates | `study_os/update_context.py:85 policy_update_context` | `official_updates[]` w/ `published_at,effective_from,created_at`, `affects_*` flags | **Reusable** for stale + updates check |
| Competition | `study_os/competition_context.py:110 competition_context` | per-exam vacancy/applicant/pressure + `trust{source_basis,reviewer_status,confidence_score,evidence_count}` | **Reusable** for competition check |
| Review/activate | `admin_exam_intelligence.py: review_* PATCH handlers` (mutations, out of scope) | lifecycle transitions | Read only the resulting statuses |
| Evidence (universal) | `app/api/evidence.py:135 get_evidence` `GET /evidence/{kind}/{row_id}` | per-row source/trust envelope for 8 kinds | **Reusable** — drawer deep-links here |
| Planner consumability | `study_os/planner.py: _compute_plan` (`reason="no_locked_coverage"`) / `_load_locked_coverage` | definitive "planner-ready iff ≥1 `locked` coverage row" | **Reusable** for verdict |

Grouping:
- **Already reusable for 4.6I:** workspace context, mock-readiness verdict, documents, updates, competition, evidence, planner locked-coverage gate.
- **Useful but insufficient (need aggregation):** `verified_pyq_topic_counts` (per-topic, not summed), `locked_topic_coverage*` (per-topic), workspace readiness `phases[]`.
- **Unsafe to expose directly:** evidence `confidence_score` to the operator drawer (see §6/§8); any slug-derived `state` (see §12).
- **Would need aggregation:** all list-level counts (§5), per-row PYQ totals and locked-coverage counts (§4/§7).

---

## 4. Prototype feature matrix

Source column gives the named read; Label is the grounding verdict.

### Landing / list-level

| Feature | Prototype needs | Current support | Source file:function | Label | Decision | Wave |
|---|---|---|---|---|---|---|
| Blocked count | # exams with a `blocked` verdict | none | `diagnostics.py:assemble_mock_readiness_report` (per-exam) | [needs-join] | aggregate server-side | 4.6H |
| Needs-action count | # exams with any open blocker | none | mock-readiness + `coverage`/`syllabus` statuses | [needs-join] | aggregate server-side | 4.6H |
| Ready count | # exams planner-consumable | none | `planner.py:_compute_plan` locked gate / `exam_topic_coverage` locked | [needs-join] | aggregate server-side | 4.6H |
| Pending-review count | # exams w/ pending rows | none | `syllabus_topic_mentions` + `exam_topic_coverage` `reviewer_status` | [needs-join] | aggregate server-side | 4.6H |
| Stale-updates count | # exams w/ stale updates | none | `update_context.py:policy_update_context` (`published_at`) | [needs-join] | define threshold + aggregate | 4.6H |
| Workflow chips (Needs action, Blocked, Missing PYQ, Missing coverage, Stale, Ready) | filter list by signal | none | as the rows above (each chip = a count + a filter) | [needs-join] | server-side filter+count | 4.6H |
| Blocker-first sort | order by blocker severity | none (only `ORDER BY name`) | mock-readiness verdict per exam | [needs-join] | **server-side only** (FE holds 1 page) | 4.6H |
| Management-lane sort | order by lane | column exists, no sort param | `exams.management_mode` (`list_exams:280`) | [derivable] | add `sort` value | 4.6H |
| Recent-activity sort | order by last touched | none | see `last_touched` (§12) | [needs-join] / [needs-column] | resolve `last_touched` first | 4.6H |
| Row `blocker_count` | # blockers on the exam | none | mock-readiness `reasons` + missing-area checks | [needs-join] | compute in list read | 4.6H |
| Row `first_blocker_text` | top blocker label | none | mock-readiness `reasons` / area gaps | [needs-join] | compute in list read | 4.6H |
| Row `verified_pyq_count` | verified PYQ on exam | none (misnamed `pyq_coverage_status`) | `coverage.py:verified_pyq_topic_counts` (sum) | [needs-join] | compute in list read | 4.6H |
| Row `total_pyq_count` | total PYQ on exam | none | `pyq_questions` count per exam | [needs-join] | compute in list read | 4.6H |
| Row `locked_coverage_count` | locked coverage rows | partial (`verified_topic_count` = locked+reviewed) | `exam_topic_coverage` `reviewer_status='locked'` | [needs-join] | split locked-only count | 4.6H |
| Row `stale` flag | updates gone stale | none | `update_context.py` `published_at` vs now | [needs-join] | threshold + compute | 4.6H |
| Row `last_touched` | last edit time | none | audit log / child `*_at` (see §12) | [needs-join] / [needs-column] | resolve in §12 | 4.6H |
| State / jurisdiction / organization | display origin | org only via context, no state | org: `exam_workspace_context` (`organizations.name`); state: **none** | org=[needs-join]; **state=[needs-column]** | org now; state = migration | 4.6H |

### Per-exam console (4.6I)

| Feature | Prototype needs | Current support | Source file:function | Label | Decision | Wave |
|---|---|---|---|---|---|---|
| Verdict ("can this exam reach aspirants?") | one-line readiness verdict | mock-readiness verdict + locked gate | `diagnostics.py:assemble_mock_readiness_report`; `planner.py:_compute_plan` | [needs-join] | assemble in console read | 4.6I |
| Action-queue item | severity/title/why/CTA/entity/evidence | none | readiness `reasons` + per-area reads (below) | [needs-join] | assemble in console read | 4.6I |
| Activation: setup | exam/cycle/phase present | yes | `exam_workspace_context` (cycles, phases) | [derivable] | check presence | 4.6I |
| Activation: documents | docs uploaded/extracted | yes | `admin_exam_intel_documents.py:list_documents` | [derivable] | check presence | 4.6I |
| Activation: syllabus | mentions verified | yes | `syllabus_topic_mentions` reviewer_status | [derivable] | check counts | 4.6I |
| Activation: topic coverage | locked coverage exists | yes | `coverage.py:locked_topic_coverage*` / `exam_topic_coverage` | [needs-join] | count locked | 4.6I |
| Activation: PYQ | verified PYQ depth | yes | `coverage.py:verified_pyq_topic_counts` | [needs-join] | sum | 4.6I |
| Activation: updates | official updates current | yes | `update_context.py:policy_update_context` | [derivable] | check + stale | 4.6I |
| Activation: competition | metrics reviewed | yes | `competition_context.py:competition_context` | [derivable] | check presence/status | 4.6I |
| Activation: publish | ready_to_activate gate | yes | `exam_workspace_readiness` summary / planner gate | [needs-join] | derive gate | 4.6I |
| Stages (setup, evidence, review, activation) | grouping | n/a (UI grouping) | grouping over activation checks | [derivable] | UI-side grouping | 4.6I |
| Evidence object | source/basis/status/updated_at | yes | `evidence.py:get_evidence` (8 kinds) | [derivable] | reference, don't inline | 4.6I |
| Evidence drawer **NO %** | hide confidence | rows carry `confidence_score` | `evidence.py:_KIND_MAP` (`confidence_field`) | [derivable] | **never render %** | 4.6I |

---

## 5. Proposed minimal backend read shape — LIST (4.6H)

**Options.**
- **A. Extend `GET /api/admin/exam-intelligence/exams`** with `sort` + workflow filters + counts.
- **B. Add `GET /api/admin/exam-intelligence/console/exams`** — a console-shaped sibling.
- **C. Add `GET /api/admin/exam-intelligence/console/summary`** — counts only, separate from rows.

**Recommendation: B + C.** Keep `/exams` as the stable Registry read (4.6G already binds `ExamListShell` to it, and `ExamListTable` Registry also uses it). Add **B** for the console's work-queue rows (it can carry the heavier per-row aggregates without changing the Registry contract) and **C** for the landing chips (aggregate counts have a different, catalogue-wide cost profile — see §12). This avoids overloading `/exams` and avoids two callers fighting over one response shape.

**B — `GET /console/exams` response (concrete shape):**
```json
{
  "items": [
    {
      "id": "…", "slug": "ssc-cgl", "name": "SSC CGL",
      "exam_type": "recruitment", "management_mode": "core", "cadence": "annual",
      "exam_family_id": "…", "organization_name": "Staff Selection Commission",
      "readiness": "blocked",
      "blocker_count": 3,
      "first_blocker_text": "No locked topic coverage",
      "locked_coverage_count": 0,
      "verified_pyq_count": 0,
      "total_pyq_count": 42,
      "stale": true,
      "last_touched": "2026-05-30T12:00:00Z"
    }
  ],
  "count": 25, "total_count": 130, "limit": 25, "offset": 0, "has_next": true
}
```
- **Supported filters:** existing six (`q`, `exam_type`, `active_state`, `management_mode`, `cadence`, `exam_family_id`) **[derivable]** + workflow filters `needs_action`, `blocked`, `missing_pyq`, `missing_coverage`, `stale`, `ready` — each **[needs-join]** (§4 rows).
- **Supported sort values:** `management_lane` **[derivable]**; `blockers_first` **[needs-join]**; `recent_activity` **[needs-join]/[needs-column]** (gated on `last_touched`, §12).
- **No raw DB leakage:** expose `organization_name`, not `conducting_organization_id`; expose `readiness` token, not `reviewer_status` soup; no UUIDs in labels.

**C — `GET /console/summary` response:**
```json
{ "blocked": 12, "needs_action": 31, "ready": 64, "pending_review": 19, "stale": 8, "generated_at": "…" }
```
All six counts are **[needs-join]** (mock-readiness verdict + coverage/syllabus statuses + updates recency), computed server-side, never in the FE.

---

## 6. Proposed minimal backend read shape — PER-EXAM CONSOLE (4.6I)

**Candidate:** `GET /api/admin/exam-intelligence/console/{exam_id}` (mirrors the existing `/workspace/{exam_id}/...` convention; `:exam_id` is already the URL source of truth — `useSelectedExamId`).

```json
{
  "exam": { "id": "…", "slug": "ssc-cgl", "name": "SSC CGL", "organization_name": "…", "family_name": "…" },
  "verdict": { "status": "blocked", "headline": "Not ready for aspirants", "reason": "No locked topic coverage" },
  "action_queue": [
    {
      "id": "coverage-locked",
      "severity": "blocker",
      "area": "topic_coverage",
      "title": "Lock topic coverage",
      "why": "Planner reads only locked coverage rows; none exist yet.",
      "cta_label": "Open topic coverage",
      "cta_route": "/admin/exam-intelligence/workspace/<exam_id>",
      "entity_kind": "exam_topic_coverage",
      "entity_id": null,
      "evidence": [ { "kind": "exam_topic_coverage", "row_id": "…" } ],
      "status": "open"
    }
  ],
  "activation_checks": [
    { "area": "setup",         "state": "done",    "detail": "1 cycle · 2 phases" },
    { "area": "documents",     "state": "done",    "detail": "3 documents extracted" },
    { "area": "syllabus",      "state": "partial", "detail": "12 verified · 4 pending" },
    { "area": "topic_coverage","state": "blocked", "detail": "0 locked" },
    { "area": "pyq",           "state": "blocked", "detail": "0 verified PYQ" },
    { "area": "updates",       "state": "stale",   "detail": "no official update in 90d" },
    { "area": "competition",   "state": "done",    "detail": "reviewed" },
    { "area": "publish",       "state": "blocked", "detail": "blocked by coverage + pyq" }
  ],
  "stages": [
    { "id": "setup",      "label": "Setup",      "areas": ["setup","documents"] },
    { "id": "evidence",   "label": "Evidence",   "areas": ["syllabus","topic_coverage","pyq"] },
    { "id": "review",     "label": "Review",     "areas": ["updates","competition"] },
    { "id": "activation", "label": "Activation", "areas": ["publish"] }
  ],
  "evidence_refs": [ { "kind": "exam_topic_coverage", "row_id": "…" } ],
  "generated_at": "…",
  "stale": true
}
```

**Grounding for every assembled part:**
- `verdict` — `diagnostics.py:assemble_mock_readiness_report` summary + `planner.py:_compute_plan` locked gate. **[needs-join]**.
- `action_queue[].area` and `activation_checks[].area` — each maps to a named read: `setup`→`exam_workspace_context`; `documents`→`list_documents`; `syllabus`→`syllabus_topic_mentions`; `topic_coverage`→`exam_topic_coverage`/`coverage.py:locked_topic_coverage*`; `pyq`→`coverage.py:verified_pyq_topic_counts`; `updates`→`update_context.py:policy_update_context`; `competition`→`competition_context.py:competition_context`; `publish`→`exam_workspace_readiness`. `setup/documents/updates/competition` are **[derivable]**; `topic_coverage/pyq/publish` are **[needs-join]** (aggregation).
- `cta_route` — existing workspace routes. **[derivable]**.
- `evidence` / `evidence_refs` — **references** to `evidence.py:get_evidence` `GET /evidence/{kind}/{row_id}`; the console read returns `{kind,row_id}` pairs, the drawer fetches them. **[derivable]**.

**HARD RULE:** no `confidence_score`/`confidence_percent` anywhere in the action queue, activation checks, verdict, or evidence drawer — even though `evidence.py:_KIND_MAP` carries `confidence_field` for several kinds. The console read must **omit** that field from its projection.

---

## 7. Existing-read reuse plan (per proposed field)

| Proposed field | Source read | Label |
|---|---|---|
| existing six filters | `/exams` `list_exams` params | [derivable] |
| `management_lane` sort | `exams.management_mode` | [derivable] |
| `organization_name` | `exam_workspace_context` → `organizations.name` (via `conducting_organization_id`) | [needs-join] |
| `family_name` | `exam_workspace_context` → `exam_families.name` | [needs-join] |
| `readiness` token / `verdict` | `diagnostics.py:assemble_mock_readiness_report` + `planner.py:_compute_plan` | [needs-join] |
| `blocker_count`, `first_blocker_text` | mock-readiness `reasons` + per-area gaps | [needs-join] |
| `locked_coverage_count` | `exam_topic_coverage` `reviewer_status='locked'` (`coverage.py:locked_topic_coverage`) | [needs-join] |
| `verified_pyq_count` | `coverage.py:verified_pyq_topic_counts` (sum) | [needs-join] |
| `total_pyq_count` | `pyq_questions` per-exam count | [needs-join] |
| `stale` | `update_context.py:policy_update_context` `published_at` vs now | [needs-join] |
| `last_touched` | `admin_audit_logs` (entity) / child `*_at` (§12) | [needs-join] / [needs-column] |
| list aggregate counts | mock-readiness + coverage/syllabus statuses + updates recency, catalogue-wide | [needs-join] |
| activation: setup/documents/updates/competition | context / `list_documents` / `policy_update_context` / `competition_context` | [derivable] |
| activation: topic_coverage/pyq/publish | coverage + verified PYQ + readiness gate | [needs-join] |
| evidence objects | `evidence.py:get_evidence` (referenced) | [derivable] |
| `state` / `jurisdiction` | no existing read | [needs-column] |

---

## 8. Fields that MUST NOT be faked in the FE

Each requires a server value; the FE must render only what the backend returns (empty/unknown otherwise):
- blocked count, needs-action count, ready count, pending-review count, stale count
- per-row: `missing_pyq` flag, `missing_coverage` flag, `stale` flag, `blocker_count`, `first_blocker_text`, `verified_pyq_count`, `total_pyq_count`, `locked_coverage_count`, `last_touched`
- `blockers_first` / `recent_activity` sort ordering (cannot be reconstructed from one page)
- per-exam: `verdict`, activation-check completion count, evidence count

The FE has exactly **one** server-paginated page in hand (`ExamListShell.jsx` state `{items,total_count,has_next,offset}`); none of the above can be honestly synthesized client-side.

---

## 9. 4.6G safe subset already shipped (record)

Confirmed live on `main` (`ExamGovernanceConsole.jsx` → `ExamListShell.jsx`, PR #700):
- search (`q`) · the existing filters (`exam_type`, `active_state`, `management_mode`+`__null__`, `cadence`, `exam_family_id`) · `limit`/`offset` pagination
- name-first rows · slug as secondary text · readiness badge from `readiness_level` (**no %**)
- console primary action → `/console/:exam_id` · advanced-workspace secondary → `/workspace/:exam_id`
- **no** workflow chips · **no** aggregate/fake counts · **no** blocker-first sort · empty/error states render no seed data

These stay; 4.6H/4.6I add to them, they do not replace them.

---

## 10. 4.6H implementation recommendation (next code PR)

- **Endpoints:** add `GET /api/admin/exam-intelligence/console/exams` (work-queue rows: existing filters + `sort` + workflow filters + per-row aggregates) and `GET /api/admin/exam-intelligence/console/summary` (the six counts). Leave `/exams` unchanged.
- **Service module:** a new aggregation helper, e.g. `app/backend/app/exam_intelligence/work_queue.py`, that composes existing reads (`diagnostics.assemble_mock_readiness_report`, `coverage.verified_pyq_topic_counts`/`locked_topic_coverage`, `update_context.policy_update_context`) into per-exam row signals and catalogue counts. Keep it read-only; reuse, don't re-query ad hoc.
- **Tests:** unit tests for the helper (verdict→`readiness` token, locked-only count, verified-PYQ sum, stale threshold), endpoint tests for each `sort` value + each workflow filter + counts, and a guard test that the response carries **no** `confidence_score` and **no** raw `conducting_organization_id`.
- **Schema:** ONLY if `state`/`jurisdiction` is required for 4.6H (it is **[needs-column]** — see §12); and optionally a denormalized `last_touched` if the audit-log join proves too costly. Call these out explicitly in that PR; do not silently assume them.
- **UI:** none beyond wiring the chips/counts/sort once the backend exists.

## 11. 4.6I implementation recommendation (later PR)

- Add `GET /api/admin/exam-intelligence/console/{exam_id}` returning the §6 shape; render a per-exam action console: verdict strip → blocker-first action queue → activation checks → stages.
- Evidence drawer references `GET /evidence/{kind}/{row_id}`; render source/basis/reviewer_status/updated_at, **never** `confidence_score`.
- Reuse existing workspace panels where they fit; **do not fork the PYQ Workbench**; no workspace redesign; no mutation/route changes beyond the new read.

---

## 12. Computability verdicts (concrete)

- **`stale`** → **[needs-join].** Compute from `update_context.py:policy_update_context` `official_updates[].published_at` (and `created_at` fallback) vs `now` against a defined window (e.g. 90d), optionally gated on unreviewed `affects_*` rows. No new column; needs a threshold decision.
- **`last_touched`** → **[needs-join]** (preferred) **/ [needs-column]** (fallback). Truthful value = `max` of the relevant child timestamps: `exam_topic_coverage.reviewed_at/created_at`, `exam_policy_updates.published_at`, `syllabus_topic_mentions.reviewed_at`, plus `admin_audit_logs.created_at` filtered by `entity_id` (`admin_community_governance.py:_audit` writes `entity_type/entity_id`). That cross-table `max` is a join, not a column. If that proves too costly per request, denormalize a single `exams.last_touched`-style column → **[needs-column]** (RISK, 4.6H schema work).
- **`state` / `jurisdiction`** → **[needs-column] + UNSAFE to derive.** No `state` field on `exams`, on the `organizations` projection (`id,name,type,trust_tier`), or in `competition_context.py`. Only the slug encodes state-like prefixes; **parsing the slug is explicitly disallowed** (the audit's "DB key doing a State column's job"). Recommend a real `exams.state`/`jurisdiction` column (or an `organizations.state` join if added) before any State display.
- **`evidence`** → **reference, don't inline.** Use the existing `GET /evidence/{kind}/{row_id}` (`evidence.py:135`, 8 kinds in `_KIND_MAP`). The console read returns `{kind,row_id}` refs; the drawer fetches the trust envelope on demand. Avoids duplicating projections and keeps the `confidence_score` omission enforced in one place. **[derivable].**
- **List aggregate counts** → **[needs-join], compute-live with a cost caveat.** `/exams` today does two batched child reads capped at 20000 rows **for one page's `exam_ids` only** (`:316,:331`). Landing counts span the **whole catalogue**, so naive per-exam `assemble_mock_readiness_report` calls would be O(#exams) round-trips. Recommend a single set-based aggregation in the `work_queue.py` helper (group-by over `exam_topic_coverage`/`syllabus_topic_mentions`/`exam_policy_updates`), and cache the `/console/summary` result briefly if needed. Live is feasible; do not precompute into a column unless profiling demands it. **[needs-join].**
