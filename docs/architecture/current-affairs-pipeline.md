---
owner: exam-intelligence / study-os
status: architecture decision (contract-first; PLANNED) — GATES the LLM pipeline PR
last_verified_against_code: 2026-07-11
source_of_truth: code
related_code:
  - app/backend/app/scraping/fetcher.py
  - app/backend/app/scraping/sources.py
  - app/backend/app/scraping/runner.py
  - app/backend/app/notifications/scheduler.py
  - app/backend/app/study_os/mock_blueprint_selection.py
  - app/backend/app/study_os/writing_practice/evaluation_worker.py
  - app/backend/app/study_os/attempt_evidence.py
related_migrations:
  - app/supabase/migrations/056_exam_policy_updates.sql
  - app/supabase/migrations/135_mock_engine_core.sql
  - app/supabase/migrations/159_mock_question_provenance.sql
  - app/supabase/migrations/161_mock_pipeline_gate.sql
related_adr:
  - docs/adr/0006-human-gate-before-automation.md
  - docs/adr/0007-aggregators-discovery-only.md
related_docs:
  - docs/architecture/subject-practice-framework.md
  - docs/architecture/english-writing-practice.md   # LLM-adapter runtime contract to reuse
  - docs/architecture/ewp-semantic-evaluator-adapter.md  # precedent: gated real LLM adapter
  - docs/scraping/aggregator-strategy.md
review_cadence: per-sprint
---

# General Awareness — Current-Affairs Pipeline

**Status:** CONTRACT-FIRST / PLANNED. This document is a **required gate** for the LLM pipeline PR
(GQR-G3). Per the locked invariant "No new AI writes … add an LLM adapter only when explicitly
justified in an architecture doc," no current-affairs generation code may land until this contract
is approved. Precedent: the EWP real semantic evaluator is still gated/unapproved for the same
reason (`ewp-semantic-evaluator-adapter.md`).

GA v1 = **current-affairs practice only** (`weekly_current_affairs`, `monthly_current_affairs`).
Cross-subject scope and product locks live in `docs/architecture/subject-practice-framework.md` §1.1.

---

## 1. Operating model
```text
Allowlisted official sources
→ scheduled fetching (new APScheduler jobs — see §9)
→ immutable document snapshots
→ claim extraction (LLM, shadow)
→ evidence verification
→ MCQ candidate generation (LLM, shadow)
→ deterministic validation
→ operator review (human gate — ADR 0006)
→ promotion to the objective question bank (reusing existing current_event isolation — §7)
→ reviewed weekly/monthly bundle
→ frozen learner attempt (own CA attempts table — §8)
```
The operator is a **curator and publisher**, not a manual question author. A manually uploaded
digest is supported only as an event-priority input, a gap-filling source, an editorial grouping, or
a request to regenerate — it never bypasses evidence collection or review.

---

## 2. Source authority (do NOT reuse `source_registry`)
`source_registry` is schema-generic, but **every active row is consumed by the recruitment runner**
(`scraping/runner.py::run_scraping_pass` → recruitment classify / extract / promote into
`recruitments`/`posts`/`vacancies`). Adding current-affairs rows there would drag them into the
recruitment pipeline. Create a separate authority:

```text
current_affairs_sources
- id, name
- authority_level          # primary_official | official_secondary | discovery_only
- publisher_type
- adapter_type
- official_url, crawl_url, rss_url, api_url, pdf_bulletin_url
- adapter_config, parser_config
- default_category, default_language
- crawl_schedule           # config consumed by the new ca:ingest job (§9), NOT an APScheduler cron by itself
- is_active
- created_at, updated_at
```

`authority_level` maps directly onto ADR 0007 (aggregators discovery-only): **a `discovery_only`
source may never be the sole evidence for a promoted question.** The LLM cannot assign or alter
`authority_level`.

**Reuse, don't rebuild:** the fetch layer is directly reusable — `scraping/fetcher.py` already does
ETag / Last-Modified conditional fetch and returns a dedicated `not_modified` (304) result across
HTML/RSS/API/PDF/sitemap; `scraping/sources.py::ScrapeSource` is a domain-neutral adapter-config
dataclass. Reuse both (optionally extract a shared adapter-config type), but **do not** route
current-affairs rows through the recruitment runner.

Initial scope: PIB, RBI, a small set of high-value Union ministries, major statutory/constitutional
bodies, official gazette/circular sources where retrieval is reliable. State/international/specialised
sources are added only after the first sources pass operational quality gates.

---

## 3. Evidence and event model (separate factual vs editorial lifecycles)
```text
current_affairs_documents      # immutable evidence snapshots; changed docs create new rows
- source_id, source_url, final_url, title, document_type
- published_at, fetched_at
- content_hash, etag, last_modified
- raw_text, metadata
- supersedes_document_id, ingestion_status

current_affairs_events
- canonical_title, event_date, category
- primary_topic_id
- event_fingerprint, editorial_importance
- relevance_from, relevance_until, status

current_affairs_claims
- event_id, claim_text, claim_fingerprint
- factual_status
- valid_from, superseded_at, superseded_by_claim_id
- reviewer_status

current_affairs_claim_evidence
- claim_id, document_id, evidence_text
- start_offset, end_offset, evidence_role
```

Three distinct validity axes — do not collapse them:
- `factual_status` — whether the fact is still correct.
- `relevance_until` — whether the event should still be selected for current-affairs practice.
- bundle `available_until` — whether a learner may still start that bundle.
A fact can remain true after it is no longer editorially current.

---

## 4. Ingestion
Runs on the new `ca:ingest` job (§9), daily or more frequently per source capability:
`fetch → conditional 304 check → URL/content-hash dedup → document snapshot → relevance pre-filter →
extraction queue`. Before any LLM call, reject/deprioritise duplicates, routine/ceremonial/
promotional releases, narrow local notices, documents with no stable examinable claim, and
inaccessible/incomplete sources — each exclusion records a machine-readable reason.

---

## 5. LLM pipeline (shadow; reuse the EWP runtime contract)
AI is an assistant, not an authority (ADR 0006). **The generation/verification runtime MUST reuse
the EWP LLM-adapter contract** (`english-writing-practice.md` §5, `AGENTS.md` EWP-4), not a new
pattern: the LLM call runs with **no DB transaction open**; jobs use a **lease + fencing token**
(`locked_at` + `claim_token`, re-asserted `FOR UPDATE` in the final write txn); job acknowledgement
is atomic with side effects; an idempotency key dedupes retries; output is **shadow / no authority**.

- **Stage A — claim extraction.** Input: immutable document text + metadata + source authority +
  explicit exam/category taxonomy. Output: events → claims with `document_id` and exact
  `start/end` offsets. Hard rules: use only supplied evidence; no model-memory facts; no generated
  URLs; strict structured output; null/reject on insufficient evidence.
- **Stage B — MCQ generation.** Single-correct MCQs only (stem, four distinct options, one answer,
  concise explanation, per-distractor rationale, linked claim IDs, difficulty, style). No MSQ /
  native matching in this phase.
- **Stage C — independent verification.** A separate verifier receives the MCQ + linked claims +
  exact evidence and independently checks the supported answer, single-correctness, option safety,
  explanation support, and time-dependent/ambiguous wording. **Advisory only** — it does not
  approve publication.
- **Stage D — deterministic validation (code, not AI).** Enforce: exactly four options; exactly one
  correct; no duplicate options; non-empty explanation; evidence linked to the answer; supported
  dates/numbers/entities/titles; no unsupported distractor facts; no answer leakage; no unqualified
  "currently/recently/latest"; valid event & relevance dates; no duplicate question fingerprint; no
  superseded claim; **no inactive or `discovery_only` source as sole evidence** (ADR 0007).
- **Stage E — operator review (human gate).** Operator sees event summary, category/importance,
  source authority + links, exact evidence passages, question/options/answer, explanation,
  distractor rationales, verification result, duplicate/conflict warnings, relevance window, and the
  generation audit. Actions: approve / edit+approve / reject / regenerate / regenerate distractors /
  merge duplicate event / mark unsuitable / send back for evidence. **The model may write only to
  staging via validated code; it may never promote, publish, or mark its own output reviewed.**

---

## 6. Candidate + generation audit
```text
current_affairs_generation_runs
- action, provider, model, prompt_version
- input_hash, output_hash, token_usage, latency, status, error

current_affairs_question_candidates
- event_id, question_payload, question_fingerprint
- generator_run_id, verifier_run_id, validation_result
- status                 # generated -> validation_failed | review_ready -> approved | rejected -> promoted
- reviewed_by, reviewed_at
```

---

## 7. Promotion + freshness isolation (reuse existing machinery)
The repo already has current-affairs isolation scaffolding — **reuse it, do not rebuild:**
- Migration 159 added `is_current_based`, `event_anchor_date`, `valid_from`, `valid_until`, and a
  soft `current_affairs_item_id` uuid on `mock_question_bank` (159 notes the target table "does not
  yet exist" — this pipeline creates it; wire the FK when `current_affairs_events` lands).
- Migration 161 made `source_kind = 'current_event'` a legal value.
- `mastery_engine/mastery_delta.py` already weights `current_event` at 0.8.
- **`mock_blueprint_selection.py::_exam_base_pool` already EXCLUDES `is_current` / `is_current_based`
  and expired (`valid_until`) questions** from generated sectional-mock selection, pinned to the
  readiness predicate.

Promote an approved candidate (via an audited service/RPC only) into the objective bank with
`source_kind='current_event'`, `is_current_based=true`, and `valid_until=<relevance window>`; the
blueprint selector then auto-keeps it out of permanent mocks.

```text
current_affairs_question_links
- candidate_id, event_id, claim_id, mock_question_id, promoted_at
```

**GQR-G0 PREREQUISITE (correctness, ship-blocking):** the `_exam_base_pool` exclusion holds only on
the **new** blueprint selector. The **legacy** template path
(`mock_engine._select_criteria_question_ids` / `select_questions_for_template`) uses a looser pool
with **no `is_current` exclusion** (documented "PARKED — TEMPLATE-PATH POOL DIVERGENCE" in
`mock_blueprint_selection.py`). A promoted `current_event` question could leak into a template-path
mock with a decaying answer. **Align the template pool predicate with `_exam_base_pool` BEFORE any
current-affairs question becomes promotable/attemptable (GQR-G5).** This is a latent mock-engine
correctness bug and is fixed as its own PR (GQR-G0), independent of the CA arc.

`source_type` note: the categorical value is `source_kind` (migration 161 CHECK), not `source_type`
(untyped text). Use `source_kind`. Do not use `source_type` as the behavioural switch for mastery —
attempt policy explicitly disables mastery for current-affairs (§8).

---

## 8. Learner runtime + CA attempts (own table, not `mock_attempts`)
```http
POST /api/study/subjects/{subject_id}/practice/start   { "mode": "weekly_current_affairs" }
```
Server resolves the learner's exam, the current eligible bundle, common + capped-personalised
questions, order, attempt context, and frozen evidence/version identifiers. The client never supplies
question IDs, source IDs, or bundle dates.

**Attempts model — decision (folded correction):** there is **no `attempt_kind` discriminator**
anywhere today, and trap drills deliberately use a **separate table** (`user_trap_drill_attempts`)
to avoid polluting mock analytics/attempt counts (mirroring the EWP rule "drills must never create
mock attempts"). Therefore current-affairs practice uses its **own attempts table**, not
`mock_attempts`:

```text
current_affairs_attempts
- id, user_id, exam_id
- bundle_id, cadence, period_start, period_end
- status, started_at, submitted_at
current_affairs_attempt_responses
- attempt_id, mock_question_id, selected_option_id, is_correct, time_spent_sec
```

Rationale: reusing `mock_attempts` with an `attempt_kind` flag would require auditing every mock
dashboard / leaderboard / attempt-count query to filter CA out; a dedicated table keeps mock
analytics clean by construction. Derive completion, attempted/correct counts, accuracy, category
breakdown, time spent, and weekly/monthly trend from these rows — **do not** create a duplicate
session-metrics authority.

---

## 9. Scheduling (new jobs — scraping is NOT scheduled today)
Recruitment scraping is **admin/API-triggered only**; `notifications/scheduler.py` (APScheduler)
wires `notif:*`, `elig:recompute`, `study:plan_regen`, `mock:sweeper`, `doc:text_extract`,
`writing:evaluate`, `writing:mastery_outbox` — **no crawl job exists**. The CA pipeline therefore
adds its **own** scheduler jobs, following the `writing:evaluate` / `writing:mastery_outbox`
worker+scheduler pattern:
- `ca:ingest` — fetch + snapshot + dedup + queue (consumes each source's `crawl_schedule`).
- `ca:generate` — drain the extraction/generation/verification queue (lease + fencing, §5).
- `ca:promote-sweep` — housekeeping: expire relevance windows, demote stale events.

---

## 10. Feedback, retry, and mastery bypass
After submission show: correct answer, concise explanation, event date, source publication date,
source link, and a "source updated" warning where a superseding claim exists. **Do not write** to
`user_topic_mastery`, long-term SRS, the permanent Mistake Book, or normal correction-task
generation. A dedicated short-lived retry queue handles weekly→monthly retries:

```text
current_affairs_retry_items
- user_id, question_id, source_attempt_id
- due_at, expires_at, status
```
Expiry stops future scheduling; it never deletes historical attempt analytics. At monthly-attempt
creation the server may append a **capped** personalised retry tail from the learner's still-relevant
weekly mistakes; the resulting list is frozen in the attempt. The monthly core bundle is editorial
and common to eligible users — it must not simply concatenate weekly bundles.

---

## 11. Bundles
```text
current_affairs_bundles
- cadence, period_start, period_end, exam_family_id (nullable)
- publish_at, available_until, reviewer_status, status, published_by, published_at
current_affairs_bundle_questions
- bundle_id, mock_question_id, display_order, importance_score, inclusion_reason
```
Weekly = newly relevant events, concise factual recall, statement-based single-answer, first
exposure. Monthly core = high-importance reviewed events, commonly-missed weekly concepts, confusion
pairs, corrected facts (latest approved claim), broader connections.

---

## 12. Admin placement
Embedded in **Content Studio** as an additional content type / work queue (Sources, Ingestion,
Events, Question Review, Bundles) via internal tabs or drill-in views. No new sidebar destination
(no-new-surface rule).
