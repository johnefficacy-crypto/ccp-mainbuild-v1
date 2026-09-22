---
owner: exam-intelligence / study-os
status: architecture decision — APPROVED 2026-07-12 (johnefficacy-crypto); GATES the LLM pipeline PR (gate CLEARED)
last_verified_against_code: 2026-07-11
source_of_truth: code
related_code:
  - app/backend/app/current_affairs/ingestion.py
  - app/backend/app/current_affairs/sources.py
  - app/backend/app/scraping/fetcher.py
  - app/backend/app/scraping/sources.py
  - app/backend/app/scraping/runner.py
  - app/backend/app/notifications/scheduler.py
  - app/backend/app/study_os/mock_blueprint_selection.py
  - app/backend/app/study_os/writing_practice/evaluation_worker.py
  - app/backend/app/study_os/attempt_evidence.py
related_migrations:
  - app/supabase/migrations/296_ca_sebi_path_allowlist_backfill.sql
  - app/supabase/migrations/294_ca_rss_item_level_ingestion.sql
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

**Status:** APPROVED 2026-07-12 (johnefficacy-crypto). This document was a **required gate** for the
LLM pipeline PR (GQR-G3); the gate is now CLEARED, so GQR-G3 generation code may land per this
contract (shadow / no-authority; no promotion or publication until GQR-G4/G5). Per the locked
invariant "No new AI writes … add an LLM adapter only when explicitly justified in an architecture
doc," this approved contract is that justification, scoped to current-affairs generation only.

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
`authority_level`. At ingest (CA-RSS-03, §4.8) a `discovery_only` source stores title + link + feed
summary only — no page fetch, no article text, no generation job.

**Reuse, don't rebuild:** the fetch layer is directly reusable — `scraping/fetcher.py` already does
ETag / Last-Modified conditional fetch and returns a dedicated `not_modified` (304) result across
HTML/RSS/API/PDF/sitemap; `scraping/sources.py::ScrapeSource` is a domain-neutral adapter-config
dataclass. Reuse both (optionally extract a shared adapter-config type), but **do not** route
current-affairs rows through the recruitment runner.

Initial scope: PIB, RBI, a small set of high-value Union ministries, major statutory/constitutional
bodies, official gazette/circular sources where retrieval is reliable. State/international/specialised
sources are added only after the first sources pass operational quality gates.

Seeded sources (migrations 241, 294, 299):

| Source | authority_level | publisher marker | cadence |
|---|---|---|---|
| PIB (Regid=3, Hindi feed → English follow) | primary_official | `PIB` | 12h |
| RBI press releases | primary_official | `RBI` | 24h |
| RBI notifications | primary_official | `RBI`, `feed=notifications` | 24h |
| RBI speeches | primary_official | `RBI`, `feed=speeches` | 48h |
| SEBI | primary_official | `SEBI` | 24h |
| UNESCO World Heritage Centre | primary_official (`international_body`) | `UNESCO_WHC` | 48h |
| The Hindu — National | discovery_only (`news_media`) | `THE_HINDU` | 12h |

Several sources may share a publisher marker (three RBI feeds). The marker selects per-publisher
behaviour (document typing, allow/deny lists, page-date shape, language follow); every identity and
dedup lookup is by `source_id`.

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

### 4.1 RSS sources are split per item (CA-RSS-01, migration 294)
A feed body is a **listing, not evidence**. For `adapter_type='rss'` the ingest writes one
`current_affairs_documents` row per feed ENTRY:

- `title` = entry title, `source_url` = entry link, `published_at` = the parsed entry date
  (see §4.6 for the accepted shapes). **Unparseable → NULL, never `now()`** — a fabricated
  publication date would silently corrupt the relevance window (§3).
- `raw_text` = the readable text of the entry's OWN page (`fetcher.strip_html`), not feed XML.
- `canonical_item_url` = the entry link normalised (scheme/host lowercased, `www.`, fragment and
  tracking params dropped, trailing slash stripped). This is the item identity, enforced by the
  partial unique index `uq_cad_source_canonical_item (source_id, canonical_item_url)` — app-level
  dedup is not the only guard. An already-seen link is skipped **without fetching its page**.
- Content-hash dedup (`uq_cad_source_content_hash`) still applies on top.
- The feed-level 304 short-circuit stays, but its validators now live on the source
  (`current_affairs_sources.feed_etag` / `feed_last_modified`) — a document row's `etag` belongs to
  that item's page, not to the feed.
- New items per source per pass are capped (`crawl_schedule.max_items_per_pass`, default 30). The
  remainder is picked up next pass; nothing is lost, because identity is the item link.
- A failed item-page fetch is recorded per item and **no row is written**, so the next pass retries
  it. One unreachable item never fails the whole source.

Non-RSS adapters (html / api / pdf / sitemap) keep the whole-body snapshot: their fetch target
already IS one document.

### 4.2 Per-source identity
`adapter_config.user_agent` overrides the default bot User-Agent for that source only. PIB requires
it (42 consecutive `http_403` against the bot UA; a browser UA returns 200). The recruitment
scraper's identity is unchanged — the override is opt-in per row.

### 4.3 Publisher URL-path allow-list (CA-RSS-02, migration 296)
The coarsest filter, and the first one applied: an item whose canonical link sits outside its
publisher's allow-listed sections is structurally not general-awareness material, so its page is
**never fetched**. SEBI's allow-list:

```text
/media-and-notifications/press-releases/
/legal/circulars/
/legal/master-circulars/
/legal/regulations/
/reports-and-statistics/reports/
```

The excluded row is still written (pipeline §4) with `ingestion_status='deprioritised'` and
`metadata.prefilter_reason='publisher_path_excluded:/<seg1>/<seg2>'`, so an operator can see which
section was dropped. A publisher with **no** configured allow-list is unfiltered by path — absence
of config is never read as "deny all", which is why RBI and PIB are untouched until their page
structure is verified by a live pass.

Rationale (live, 2026-09-21): SEBI's first item-split pass snapshotted 15 documents, 14 of them
`/enforcement/orders/...` RTI appeals and interim orders with no examinable claim.

### 4.4 Embedded-PDF body extraction
SEBI (and peers) render the item page as chrome around an embedded PDF viewer: the readable HTML is
a breadcrumb and the document is the PDF. After fetching an allow-listed page, the ingest takes the
PDF body when the readable HTML is below `crawl_schedule.pdf_fallback_below_chars` (default 800)
**and** the page embeds or links a PDF — found via a viewer `?file=` parameter, an
`iframe`/`embed`/`object` source, or an anchor, always resolved to a `.pdf` on the **same host** (an
off-host PDF is an unvetted third party, not this source's evidence).

Extraction reuses `fetcher.fetch_pdf` → `parse_pdf_bytes`, the same pypdf path `doc:text_extract`
runs on library uploads. No new dependency. The stored body is the page title plus the extracted
text; `metadata` records `body_source` (`html`|`pdf`), `pdf_url` and `extracted_chars`, and the
document's `content_hash` becomes the PDF's so dedup keys on the body actually stored. The PDF fetch
carries the same per-source User-Agent as the page and is capped at `crawl_schedule.max_pdf_bytes`
(default 10 MB).

**Minimum-body gate.** A final body below `crawl_schedule.min_body_chars` (default 400) writes **no
row** and records a per-item error, exactly like an item-page fetch failure. This is deliberate:
294's partial unique index on `(source_id, canonical_item_url)` means a written row permanently owns
that item's slot, so storing a chrome-only body would block any later, better extraction of the same
item.

A PDF that cannot be fetched (including over the size cap) is only fatal when the HTML body alone
does not clear the floor; otherwise the HTML body is kept and `metadata.pdf_error` records what
happened.

### 4.5 Publisher title deny-list
The second layer, inside an allow-listed section. `sources.py` carries per-publisher title patterns
for strictly administrative instruments (SEBI: recovery certificate, notice of attachment, release
order, general remittance order, general remittance advice, adjudication order, settlement order,
order for compliance, order of AA under the RTI Act, and `appeal no.` + `filed by` together).
Matching is deterministic, case-insensitive substring — **no LLM, no scoring**; a tuple pattern
requires every substring and reports itself joined by `+`. A match is evaluable from the feed entry
alone, so the item page is never fetched. The row is still snapshotted with
`ingestion_status='deprioritised'` and `metadata.prefilter_reason='publisher_denylist:<pattern>'`;
it is never silently dropped.

### 4.6 Publication dates
`metadata.raw_pub_date` always keeps the feed's verbatim value, parsed or not — when a publisher
changes its date shape, that string is what lets the parser be extended and the rows re-derived
without re-crawling. `parse_published_at` accepts RFC 2822 (shape-checked first, because
`email.utils` silently mis-parses `Sep 21, 2026 02:30 PM` as 02:30), ISO-8601, and the
day/month-name shapes Indian publishers use, with or without a time and with or without a trailing
`IST` / `+0530`. **A value carrying no timezone is read as Asia/Kolkata** (fixed +05:30 — India has
no DST), not UTC; reading it as UTC back-dated every item by 5.5 hours. Unparseable still means
`published_at` NULL, never `now()`.

**Page-printed dates (CA-RSS-03).** When the feed gives no parseable date, the date printed on the
stored item page is used, per publisher. PIB: the whitespace after `Posted On:` (English) or
`प्रविष्टि तिथि:` (Hindi) is collapsed and `DD MON YYYY h:mmAM/PM` is parsed as Asia/Kolkata — by a
dedicated `strptime`, not `parse_published_at`, whose RFC 2822 branch would accept the shape and drop
the PM. `metadata.date_source` records `feed` or `page`, and `metadata.raw_page_date` keeps the
matched string. No feed date and no page date still means NULL, never `now()`.

Only `snapshotted` documents are enqueued for generation (`_reconcile_pending_generation`), so
deprioritised items never reach the LLM queue.

### 4.7 PIB English-version follow (CA-RSS-03, migrations 299 + 300)
PIB's only non-empty feed is `RssMain.aspx?ModId=6&Lang=1&Regid=3`, and every item in it is Hindi
(Lang, Accept-Language and the other Regid values return empty or the same Hindi feed). Items carry
title + link only, and link `PressReleaseIframePage.aspx?PRID=<hi>`. For publisher `PIB`:

1. The feed link is rewritten to `PressReleasePage.aspx?PRID=<hi>` (the page with the language
   switcher) and fetched with the PIB User-Agent. The Iframe page is never fetched.
2. The anchor whose trimmed visible text is `English` gives the English PRID. The page holds several
   PRIDs (itself, its `lang=2` self-link, other languages, related releases) and the English one has
   no arithmetic relation to the Hindi one, so it is **only** selected by anchor text.
3. `PressReleasePage.aspx?PRID=<en>&lang=1` is fetched. The row stores the ENGLISH release: title from
   `h2#Titleh2`, `source_url` and `canonical_item_url` = the English URL, and
   `metadata.source_prid_hi` / `source_prid_en` / `source_url_hi` (the Hindi feed link).
4. Body trim: the release text is the HTML between the `#PrDateTime` block and `span#ReleaseId`.
   Everything else — header/nav, ministry and title block, Release ID, visitor counter, the "Read this
   release in" switcher, related-release tags/links, share widgets, the hidden print copy and the
   footer — is cut. If either marker is missing the whole-page text is kept (`metadata.body_trim`
   = `none`).

**Outcomes.** A failed fetch at either hop is a per-item error with no row, retried next pass
(§4.1). No `English` anchor, or an English body below `min_body_chars`, writes the Hindi page as
`deprioritised` / `language_mismatch` (`metadata.language_follow` = `no_english_link` |
`english_page_thin`), keyed on the Hindi **full-page** URL.

**Dedup and skip-without-fetch.** The English canonical URL is the row identity under 294's partial
unique index. "Already handled" is keyed on `metadata.source_url_hi` (expression index
`idx_cad_source_url_hi`, migration 299), so a Hindi item already resolved — to English or to a
mismatch row — is skipped on the next pass with **zero** fetches. No side table: the document row is
the resolution record.

**Pre-CA-RSS-03 Hindi rows.** Migration 300 moves the PIB Hindi snapshots to `deprioritised` /
`language_mismatch_pre_rss03` and fails their pending/running generation jobs. Those rows carry no
`source_url_hi` and their `canonical_item_url` is the Iframe link, so the next pass re-resolves each
item to English and writes a new row with a different canonical URL — no unique-index collision.
Apply 300 before deploying the code.

### 4.8 Language guard and discovery_only (CA-RSS-03)
**Language guard (every source).** The final stored body's dominant script is measured by a
Devanagari-vs-Latin character count (`sources.detect_language`; no dependency) and stored as
`metadata.detected_language` (`hi` | `en`, or `null` below 40 script characters). A body whose script
contradicts the source's `default_language` is written `deprioritised` / `language_mismatch`. The
guard abstains when nothing is detected or the declared language is neither `en` nor `hi`.

**discovery_only (ADR 0007).** A `discovery_only` RSS source's entry is written with
`ingestion_status='discovery_only'` (added to the CHECK by migration 299), `raw_text` NULL, the feed
summary in `metadata.feed_summary`, and `metadata.prefilter_reason='discovery_only'`. Its page is
never fetched. The status is not `snapshotted`, so the ingest pass never enqueues a job, and the
validator's `sole_evidence_discovery_only` check stays as the second line. A `discovery_only` source
on a whole-body adapter is not ingested (`skipped` / `discovery_only_non_rss`): a whole-body fetch is
article text and has no entry to take a title and link from.

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
