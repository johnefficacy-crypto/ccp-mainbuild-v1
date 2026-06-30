# English Writing Practice — Architecture Contract

**Status:** Design-locked. Do not implement without reading this document in full.
**Checklist:** `docs/status/career-copilot-checklist.md` § English Writing Practice
**PR plan:** `docs/status/career-copilot-pr-plan.md` § English Writing Practice PRs (EWP-1 … EWP-7)

---

## 1. Product intent

The English Writing Coach is an embedded mode inside Study OS, not a standalone destination. It surfaces from planner tasks, runs inside `StudyShell`, and feeds the same mastery/planner pipeline that governs every other subject.

The loop:

```
Exam writing requirement
→ progressively difficult writing task
→ aspirant writes
→ deterministic checks + structured evaluation
→ mistake explanation
→ aspirant rewrites
→ evidence recorded
→ English mastery updated
→ planner schedules the next drill
```

### No-surface rule

The no-new-top-level-surface rule from `AGENTS.md` applies. The English practice route is mounted under `StudyShell`:

```
/app/study/practice/english/:sessionId
```

It does not appear in the primary navigation. Entry is always via a planner task with a typed launch target.

---

## 2. Dual-runtime boundary

| Runtime | What it covers | Tables | Frontend shell |
|---|---|---|---|
| **Practice runtime** | Sentence construction, grammar correction, vocabulary, paragraph building, mandatory rewrites | `writing_*` tables (see §4) | `EnglishPracticeShell` |
| **Descriptive mock runtime** | Timed essay, précis, letter, report, full exam simulation | Existing `mock_attempt_responses` descriptive columns (M176/M177) | Future `descriptive` mode in `AttemptShellRouter` |

These runtimes share: prompts, rubrics, taxonomy, mastery evidence. They do not share attempt tables or frontend shells.

Sentence/grammar/paragraph drills must never create mock attempts. Creating mock attempts for drills would distort mock analytics and inflate attempt counts.

---

## 3. English taxonomy

Extend the existing subject/topic/microtopic hierarchy. Do not create an independent writing taxonomy.

```
English Language  (subject)
├── Sentence Construction
│   ├── Simple sentences
│   ├── Compound sentences
│   ├── Complex sentences
│   └── Sentence transformation
├── Grammar
│   ├── Subject–verb agreement
│   ├── Tense
│   ├── Articles
│   ├── Prepositions
│   ├── Pronoun reference
│   ├── Modifiers
│   └── Punctuation
├── Vocabulary in Context
│   ├── Word choice
│   ├── Collocations
│   ├── Formal vocabulary
│   └── Redundancy
├── Paragraph Writing
│   ├── Topic sentence
│   ├── Cohesion
│   ├── Logical order
│   └── Conclusion
├── Précis Writing
├── Essay Writing
├── Letter and Report Writing
└── Comprehension and Summary
```

Each leaf node is a row in the `topics` table with `level = 'microtopic'`. Every `writing_issue_events` row references a `topic_id` at microtopic level (`topics.level = 'microtopic'`). The planner reads `user_topic_error_patterns` at microtopic granularity and can generate "Articles drill" tasks rather than a generic "English weak" signal.

The repo has no separate `microtopics` table. All subject/topic/microtopic rows live in `public.topics` distinguished by `topics.level` and `parent_topic_id` (migration 029).

---

## 4. Practice data model

### 4.1 `writing_prompts`

Reviewed exercise content. Prompts are not created by the aspirant or the planner. They are authored in the Exam Workspace CMS and flow through the existing review lifecycle.

```sql
id                      uuid primary key
exam_id                 uuid not null references exams(id)
exam_cycle_id           uuid references exam_cycles(id)
exam_phase_id           uuid references exam_phases(id)
subject_id              uuid not null references subjects(id)
topic_id                uuid not null references topics(id)
microtopic_id           uuid references topics(id)      -- level='microtopic'
exercise_type           text not null   -- see §4.1a
prompt_text             text not null
source_text             text            -- for précis/comprehension
required_words          jsonb           -- array of strings, session-level
required_sentence_count int
difficulty_level        int not null    -- 1..10
min_words               int
max_words               int
max_rewrite_attempts    int not null default 3
rubric_id               uuid references writing_rubrics(id)
reviewer_status         text not null default 'pending'
is_active               boolean not null default false
source_document_id      uuid references document_assets(id)
metadata                jsonb not null default '{}'
created_at              timestamptz not null default now()
updated_at              timestamptz not null default now()
```

#### 4.1a Exercise types

```
sentence_construction
sentence_correction
vocabulary_in_context
sentence_rewrite
sentence_reconstruction
paragraph_writing
summary_writing
precis_practice
essay_practice
letter_practice
```

#### 4.1b Reviewer lifecycle

Prompts use the repo's existing Exam Intelligence item-review contract — not `draft → published`:

```
pending → verified | rejected | needs_correction
needs_correction → verified | rejected | pending
verified → rejected | needs_correction
```

A prompt is aspirant-visible only when:

```
reviewer_status = 'verified'
AND is_active = true
```

There is no separate `published` state. This matches the CMS pattern established by `admin_exam_intel_cms.py`, which forces created content to `pending`.

---

### 4.2 `exam_descriptive_requirements`

Ties prompts to official exam requirements. Different exams, cycles, phases and streams have different paper types, marks, word limits and timing.

```sql
id                              uuid primary key
exam_id                         uuid not null references exams(id)
exam_cycle_id                   uuid references exam_cycles(id)
exam_phase_id                   uuid references exam_phases(id)
stream_key                      text            -- e.g. 'general', 'legal', 'it'
language                        text not null default 'english'
exercise_type                   text not null
paper_name                      text
marks                           numeric
duration_minutes                int
minimum_words                   int
maximum_words                   int
required_sections               jsonb
format_rules                    jsonb
evaluation_dimensions           jsonb
feedback_release_policy         text not null   -- see §9.3
feedback_release_delay_seconds  int             -- required when policy=scheduled_after_submit
syllabus_document_id            uuid references document_assets(id)
notification_document_id        uuid references document_assets(id)
source_url                      text
source_locator                  jsonb
reviewer_status                 text not null default 'pending'
reviewed_by                     uuid references auth.users(id)
reviewed_at                     timestamptz
reviewer_notes                  text
is_active                       boolean not null default false
created_at                      timestamptz not null default now()
updated_at                      timestamptz not null default now()
```

**Constraints:**

```sql
check (minimum_words >= 0)
check (maximum_words >= minimum_words)
check (duration_minutes > 0)
check (
  feedback_release_policy in (
    'immediate', 'on_submit', 'on_evaluation_terminal', 'scheduled_after_submit'
  )
)
check (
  (feedback_release_policy = 'scheduled_after_submit' and feedback_release_delay_seconds > 0)
  or
  (feedback_release_policy != 'scheduled_after_submit' and feedback_release_delay_seconds is null)
)
```

**Idempotency key:** `(exam_id, exam_cycle_id, exam_phase_id, stream_key, language, exercise_type)`. Null-safe uniqueness via a generated key or `coalesce`-based partial index.

**Never hardcode exam-specific timings in application code.** Read from this table. Different IBPS PO cycles, SEBI streams, UPSC papers, and PSC phases all configure differently.

---

### 4.3 `writing_sessions`

One planner task or user-initiated session.

```sql
id                              uuid primary key
user_id                         uuid not null references auth.users(id)
study_task_id                   uuid references study_tasks(id)
prompt_id                       uuid not null references writing_prompts(id)
mode                            text not null   -- 'learning' | 'exam'
status                          text not null default 'active'
projection_revision             int not null    -- pinned at creation
feedback_release_policy         text not null   -- copied from exam_descriptive_requirements or 'immediate'
feedback_release_delay_seconds  int
feedback_released_at            timestamptz
evaluation_outcome              text            -- nullable until evaluation terminal
started_at                      timestamptz not null default now()
submitted_at                    timestamptz
completed_at                    timestamptz
```

`projection_revision` is pinned at session creation from the current code-defined integer. It cannot change after the session starts. Later sessions use the current revision; existing sessions keep their original.

`feedback_release_policy` and `feedback_release_delay_seconds` are copied from the requirement snapshot at creation and are immutable thereafter. Later edits to `exam_descriptive_requirements` do not alter in-progress sessions.

#### 4.3a Session states

```
active
evaluation_pending
rewrite_required
submitted          (exam mode only: answers locked, evaluation running)
completed
abandoned
```

#### 4.3b Session state rollup rules (priority order, first match wins)

```
1. any unit in (not_started, draft)
   → session: active

2. all units have submitted versions
   AND no unit in (not_started, draft)
   AND any unit in evaluation_pending
   → session: evaluation_pending

3. no unit in (not_started, draft, evaluation_pending)
   AND (any unit in rewrite_required OR current session check failed)
   → session: rewrite_required

4. all gates pass (see §4.6c)
   → session: completed
```

The `finalize_writing_session` function (§8) is the single owner of session rollup transitions.

#### 4.3c `evaluation_outcome` allowed values

```
fully_evaluated         -- rubric and language evaluation completed
deterministic_only      -- deterministic checks completed; language evaluation failed after retries
unscored                -- even required deterministic evaluation could not complete
```

Nullable while evaluation is non-terminal. Improves monotonically:
`unscored → deterministic_only → fully_evaluated`. Never downgrades. Enforcement: the finalizer writes only if the new outcome is strictly higher in this ordering.

---

### 4.4 `writing_session_units`

One independently evaluated response within a session. For the five-sentence exercise, one session has five units.

```sql
id                   uuid primary key
session_id           uuid not null references writing_sessions(id)
unit_number          int not null         -- 1-indexed
practice_microtopic_id uuid references topics(id)        -- intended exercise skill; level='microtopic'
unit_constraints     jsonb not null default '{}'         -- see §4.4a
status               text not null default 'not_started'

unique (session_id, unit_number)
```

`practice_microtopic_id` identifies the intended exercise skill. It is not the detected error topic. Both reference `topics(id)` at `level='microtopic'`. Detected errors go in `writing_issue_events` and carry their own `microtopic_id`.

#### 4.4a `unit_constraints` schema

Version-tagged. Backend validates with Pydantic `extra="forbid"` — unknown keys are rejected.

```json
{
  "schema_version": 1,
  "hint_words": ["despite"],
  "target_structures": ["compound_sentence"],
  "min_words": 5,
  "max_words": 20
}
```

All fields optional except `schema_version`. `max_words >= min_words` enforced at validation. Hint words are suggestions for exercises that deliberately assign a word to a unit. They do not impose a one-word-per-unit constraint. Session-level `required_words` on `writing_prompts` governs coverage validation.

#### 4.4b Unit states

```
not_started
draft
evaluation_pending
evaluation_failed
rewrite_required
ready
completed
```

**Transitions (learning mode):**

```
not_started → draft
draft → evaluation_pending
evaluation_pending → rewrite_required  (must_fix issues found)
evaluation_pending → ready             (no blocking issues)
evaluation_pending → evaluation_failed (no usable terminal result, recovery needed)
evaluation_failed → evaluation_pending (retry/recovery)
rewrite_required → evaluation_pending  (rewrite submitted)
ready → draft                          (explicit reopen, see §7)
ready → completed                      (session finalizer, all gates pass)
```

**Exam mode:** `rewrite_required` is forbidden. Units follow:

```
not_started → draft → evaluation_pending → ready → completed
evaluation_pending → evaluation_failed → evaluation_pending  (retry)
```

A language-stage failure after retry exhaustion does not leave the unit in `evaluation_failed` when deterministic results exist. The unit becomes `ready` with a `deterministic_only` evaluation outcome.

**`completed` is terminal.** Regression after completion belongs to a new session.

---

### 4.5 `writing_unit_versions`

Original response and subsequent rewrites. Every submitted version is immutable.

```sql
id                uuid primary key
unit_id           uuid not null references writing_session_units(id)
version_number    int not null    -- 1 = original, 2+ = rewrites
answer_text       text not null
client_word_count int
server_word_count int             -- computed at submit, authoritative
submission_kind   text not null default 'user'   -- 'user' | 'blank'
content_hash      text not null   -- see §4.5a
submitted_at      timestamptz not null default now()

unique (unit_id, version_number)
```

**`content_hash`** is computed as `SHA-256(answer_text).hexdigest()` (lowercase hex). It cannot change after version insertion.

**`server_word_count`** is computed synchronously by the submission handler (Stage 1 deterministic checks) and included in the initial INSERT. It is not updated after insert. No UPDATE or DELETE is permitted on this table from any client or service role.

**Blank exam versions** are created server-side for unanswered exam units at session submission:

```
answer_text = ''
submission_kind = 'blank'
content_hash = SHA-256('') = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

`content_hash` is a version-content verifier, not a global dedup key. Two blank versions in different sessions produce the same hash — this is expected and harmless.

#### 4.5a `version_set_hash` algorithm

Used by `writing_session_checks` to detect stale check results. Computed by one shared backend helper only — clients consume it but never generate it. Architecture tests must include a fixed-input fixture and expected digest.

```python
def compute_version_set_hash(units: list[UnitRow]) -> str:
    """
    units: rows sorted by unit_number ascending
    Each row: unit_number (int), id (UUID), version_id (UUID), content_hash (hex str)
    """
    payload = b"WPS_VERSION_SET_V1\x00"
    payload += struct.pack(">I", len(units))   # uint32 big-endian count

    for unit in sorted(units, key=lambda r: r.unit_number):
        payload += struct.pack(">I", unit.unit_number)
        payload += uuid.UUID(str(unit.id)).bytes          # 16 bytes RFC 4122
        payload += uuid.UUID(str(unit.version_id)).bytes  # 16 bytes RFC 4122
        payload += bytes.fromhex(unit.content_hash)       # 32 bytes

    return hashlib.sha256(payload).hexdigest()
```

**Contracts:**
- `unit_number`: unsigned 32-bit big-endian
- UUID bytes: RFC 4122 network-order 16-byte representation
- `content_hash` input: lowercase 64-character SHA-256 hex string
- Output: lowercase 64-character SHA-256 hex string
- Domain separator `WPS_VERSION_SET_V1\x00` prevents digest confusion with other SHA-256 uses in the codebase

#### 4.5b Text span offset contract

Issue spans use UTF-16 code unit offsets to match JavaScript string indexing.

```
span_start_utf16  int    -- inclusive
span_end_utf16    int    -- exclusive
quoted_text       text   -- the exact substring for verification
```

The backend encodes offsets in UTF-16 units when writing issue events. The frontend verifies `answer_text.slice(span_start_utf16, span_end_utf16) === quoted_text` before rendering highlights. This prevents misalignment for emoji, non-BMP characters and certain punctuation.

---

### 4.6 `writing_evaluations`

One logical evaluation envelope per version. Recovery retries resume the same envelope rather than inserting a new row.

```sql
id                              uuid primary key
unit_version_id                 uuid not null references writing_unit_versions(id)
evaluation_revision             int not null default 1
deterministic_evaluator_version text
language_evaluator_version      text
deterministic_status            text not null default 'pending'
language_status                 text not null default 'not_requested'
human_review_status             text not null default 'not_required'
overall_status                  text not null default 'pending'
deterministic_result            jsonb
language_result                 jsonb
dimension_scores                jsonb
created_at                      timestamptz not null default now()
updated_at                      timestamptz not null default now()

unique (unit_version_id, evaluation_revision)
```

#### 4.6a Stage-specific status values

```
overall_status:
  pending | partial | completed | failed

deterministic_status:
  pending | completed | failed

language_status:
  not_requested | queued | running | completed | failed | needs_review

human_review_status:
  not_required | pending | in_review | completed
```

A re-evaluation under new evaluator logic requires `evaluation_revision = previous + 1`. That is a new evaluation envelope, not a retry.

#### 4.6b Typical learning-mode flow

```
submission
→ deterministic_status=completed, overall_status=partial
→ language_status=queued
→ language_status=running
→ language_status=completed, overall_status=completed
```

A failed async stage can be retried without rerunning deterministic checks.

#### 4.6c Session completion conditions (learning mode)

A unit is `ready` when:
- latest evaluation `overall_status` is terminal (not pending/partial)
- no latest active issue has `severity = 'must_fix'` without a resolution event with `outcome = 'resolved'`
- unit-level deterministic requirements pass

A session is `completed` when:
- all units are `ready`
- required-word coverage session check passes (see §4.7)
- no unresolved `must_fix` issue exists

`advisory` and `should_fix` severity issues do not block completion.

---

### 4.7 `writing_session_checks`

Append-only. Each check row is valid only when its `version_set_hash` matches the current session state and no unit is in `draft` or `not_started`.

```sql
id               uuid primary key
session_id       uuid not null references writing_sessions(id)
check_type       text not null    -- 'required_word_coverage' | ...
version_set_hash text not null
passed           boolean not null
details          jsonb not null default '{}'
checker_version  text not null
created_at       timestamptz not null default now()
```

#### 4.7a Required-word coverage

Check type: `required_word_coverage`

Required-word coverage is **session-level**, not per-unit. One sentence may satisfy multiple required words.

**Validation:** Case-normalised token presence. Stage 1 validates only deterministic presence: `lower(required_word)` appears as a word-boundary token in at least one non-empty submitted sentence.

**Stage 2** (language evaluation) validates correct syntactic integration, part of speech, and contextual meaning. The session check for coverage runs on answer texts independently of whether language evaluation has completed — it depends only on submitted text.

**Eligibility:** the coverage check may run when every required unit satisfies all of:
- latest submitted version exists
- `latest evaluation.deterministic_status = 'completed'`
- `unit.status in ('evaluation_pending', 'rewrite_required', 'ready')`

`not_started`, `draft`, `evaluation_failed`, and `completed` exclude a unit from a new active-session check.

**Timing:** runs after all eligible units satisfy the above conditions. After any rewrite, the `version_set_hash` changes; the prior check row remains as historical record and a new check is required.

**Dispatch:** the coverage checker calls `finalize_writing_session` after committing its check row.

**Authoritativeness:** a prior check is authoritative only when:
```
check.version_set_hash = current_version_set_hash
AND no relevant unit is in draft or not_started
AND checker_version is supported
```

Immediately after a unit is reopened (`ready → draft`), the prior check is no longer authoritative even though the hash has not yet changed, because a unit is in `draft`.

---

### 4.8 `writing_issue_events`

Raw language findings. Append-only. Never mutated after insert.

```sql
id                         uuid primary key
evaluation_id              uuid not null references writing_evaluations(id)
issue_type                 text not null   -- see §5.1
microtopic_id              uuid references topics(id)    -- level='microtopic'
lineage_id                 uuid not null   -- see §4.8a
predecessor_issue_event_id uuid references writing_issue_events(id)
span_start_utf16           int
span_end_utf16             int
quoted_text                text
original_text              text
suggested_text             text
explanation                text
severity                   text not null   -- 'advisory' | 'should_fix' | 'must_fix'
affects_current_state      boolean not null default true
created_at                 timestamptz not null default now()
```

`affects_current_state = false` marks stale evaluation findings (evaluations for non-latest versions). They are available for audit but excluded from Error Lab counts and mastery evidence.

#### 4.8a Issue lineage

Lineage links related issues across rewrite versions within one session.

```
New issue appearing for the first time:
  lineage_id = new uuid
  predecessor_issue_event_id = null

Issue that persists from version N-1:
  lineage_id = predecessor.lineage_id
  predecessor_issue_event_id = matched active issue id

Issue that regresses (was resolved, reappears):
  lineage_id = resolved issue's lineage_id
  predecessor_issue_event_id = latest resolved issue in that lineage
```

Lineage IDs are backend-assigned. The browser has no insert, update or delete permission on `writing_issue_events`.

**Evaluator inputs for version N:**

```
active_prior_issues:
  unresolved effective issues from version N-1
  (issues without a 'resolved' resolution event)

resolved_prior_lineages:
  issues whose lineage was resolved in any prior version
  of the current unit in the current session
  (regardless of session status)
```

Invalidated issues (see §4.10) are excluded from both sets.

The evaluator response may reference only issue IDs supplied in those sets. The backend validates every referenced ID before assigning lineage. Regression detection requires both sets — loading only active issues from N-1 cannot detect a recurrence of a previously resolved issue.

---

### 4.9 `writing_issue_resolution_events`

Append-only. Created by the backend evaluation pipeline only.

```sql
id                       uuid primary key
issue_event_id           uuid not null references writing_issue_events(id)
resolving_version_id     uuid not null references writing_unit_versions(id)
resolving_evaluation_id  uuid not null references writing_evaluations(id)
successor_issue_event_id uuid references writing_issue_events(id)
outcome                  text not null   -- see §4.9a
evaluator_version        text not null
confidence               numeric
rationale                text
created_at               timestamptz not null default now()

unique (issue_event_id, resolving_version_id, evaluator_version)
```

#### 4.9a Resolution outcomes

| Outcome | Meaning |
|---|---|
| `resolved` | The prior issue is absent from the rewrite. `successor_issue_event_id` is null. |
| `persisted` | The same issue remains. `successor_issue_event_id` references the new issue. |
| `regressed` | An issue resolved in a prior version of this session has reappeared. `successor_issue_event_id` references the new issue. |
| `uncertain` | The evaluator cannot confidently map the prior issue to the rewritten text. |

`not_applicable` does not exist as an outcome. Evaluator false positives are handled by `writing_issue_review_events` (§4.10), not by resolution events.

**Creation rule:** when evaluating version N, the backend creates exactly one resolution event per prior active issue (from version N-1) and per prior resolved lineage that reappears. No issue row is mutated.

---

### 4.10 `writing_issue_review_events`

False positive invalidation. Service-role and backend accessible only.

```sql
id                    uuid primary key
issue_event_id        uuid not null references writing_issue_events(id)
decision              text not null   -- 'confirmed' | 'invalidated' | 'reclassified'
corrected_issue_type  text
reviewer_type         text not null   -- 'human' | 'system'
reviewer_id           uuid references auth.users(id)
evaluator_version     text
reason                text
created_at            timestamptz not null default now()
```

An `invalidated` issue must never generate mastery evidence. An `invalidated` issue is excluded from both `active_prior_issues` and `resolved_prior_lineages` evaluator input sets.

**User-facing API:** returns a derived issue state only:
- `active` — no review event, or confirmed
- `resolved` — resolved resolution event exists
- `withdrawn` — invalidated

If invalidated before feedback release: omit entirely from user-facing output.
If invalidated after feedback release: return `withdrawn` marker without reviewer identity or private notes. The aspirant sees "This feedback item was withdrawn after review."

Aspirants have no SELECT access to this table.

---

### 4.11 `writing_issue_projections`

Versioned canonical classification. Separates raw language findings from mastery classification.

```sql
id                     uuid primary key
issue_event_id         uuid not null references writing_issue_events(id)
projection_revision    int not null   -- matches writing_sessions.projection_revision
canonical_error_type   text           -- maps to correction_policy.CANONICAL_CATEGORIES
projection_confidence  numeric
prior_occurrence_count int            -- occurrences of this issue_type for this user+microtopic
rationale              text
created_at             timestamptz not null default now()

unique (issue_event_id, projection_revision)
```

Consumers read the projection pinned to the session's `projection_revision`. They never select `ORDER BY projection_revision DESC`. The planner and mastery writer consume already-created mastery evidence that references the precise projection row, so they never ask "what is the latest projection for this issue."

Re-evaluation under new projection logic inserts a new row at a higher `projection_revision`. Old rows are immutable and auditable.

**Projection computation is race-safe.** A plain read-then-insert in a default-isolation transaction does not prevent two concurrent evaluations for the same user and microtopic from observing the same `prior_occurrence_count`. The implementation must use one of:

- A PostgreSQL advisory transaction lock keyed on `hashtext(user_id || microtopic_id || issue_type)` acquired before reading the count, OR
- `ISOLATION LEVEL SERIALIZABLE` for the projection insert transaction.

The lock/isolation must be acquired before reading `prior_occurrence_count` and held until the INSERT commits.

---

### 4.12 `user_topic_mastery_evidence`

Source-neutral learning evidence. Does not directly mutate `user_topic_mastery`.

```sql
id                    uuid primary key
user_id               uuid not null references auth.users(id)
exam_id               uuid references exams(id)
exam_phase_id         uuid references exam_phases(id)
topic_id              uuid not null references topics(id)
microtopic_id         uuid references topics(id)    -- level='microtopic'
source_type           text not null   -- see §4.12a
source_entity_id      uuid not null
evidence_tier         text not null   -- 'recognition' | 'correction' | 'production' | 'retention'
score                 numeric
confidence            numeric
issue_projection_id   uuid references writing_issue_projections(id)
observed_at           timestamptz not null
metadata              jsonb not null default '{}'
```

#### 4.12a Source types

```
objective_mock
descriptive_mock
sentence_drill
paragraph_drill
human_review
mentor_review
```

**Evidence tiers:**
- `recognition`: aspirant selected correct MCQ option
- `correction`: aspirant corrected a supplied incorrect sentence
- `production`: aspirant constructed an original correct sentence
- `retention`: aspirant used the rule correctly after ≥7 days since last `production` evidence

`production` evidence carries the highest mastery weight. A successful rewrite advances tier from `correction` toward `production`, not the first draft.

**Mastery aggregator:** a separate process reads `user_topic_mastery_evidence` and computes `user_topic_mastery`. Evidence must not directly mutate `user_topic_mastery`. The existing mastery recomputation from `mock_topic_breakdowns` must not be overwritten by a parallel writing update.

---

### 4.13 `writing_rubrics`

Configurable rubric definitions. Referenced by `writing_prompts.rubric_id`.

```sql
id                uuid primary key
name              text not null
version           int not null
dimensions        jsonb not null   -- array of {key, label, weight, max_score}
created_at        timestamptz not null default now()

unique (name, version)
```

---

### 4.14 `writing_evaluation_jobs`

Asynchronous job queue for language and rubric evaluation. The job queue owns retry accounting, not the evaluation row.

```sql
id             uuid primary key
evaluation_id  uuid not null references writing_evaluations(id)
job_kind       text not null   -- 'language_evaluation' | 'rubric_evaluation'
generation     int not null default 1
status         text not null default 'pending'   -- 'pending' | 'running' | 'done' | 'failed'
attempts       int not null default 0
max_attempts   int not null default 3
scheduled_for  timestamptz
locked_at      timestamptz
last_error     text
created_at     timestamptz not null default now()
updated_at     timestamptz not null default now()

unique (evaluation_id, job_kind, generation)
```

**Active-job uniqueness:**

```sql
unique (evaluation_id, job_kind) where status in ('pending', 'running')
```

**Recovery flow:** when `status = 'failed'` and `attempts = max_attempts`, a recovery operator or system creates a new row with `generation = previous + 1, attempts = 0`. The `compare-and-set` on `language_status: failed → queued` ensures the evaluation envelope is updated atomically. The failed job row remains for observability. The `unique (evaluation_id, job_kind, generation)` constraint prevents concurrent recovery workers from inserting duplicate generation rows.

A completed language result cannot be overwritten by recovery. Re-evaluation under changed evaluator logic requires a new `evaluation_revision` (new envelope row).

---

## 5. Evaluation pipeline

### 5.1 Writing issue taxonomy

These types live in `writing_issue_events.issue_type`. They are more granular than the existing mastery error taxonomy and must be projected before reaching `user_topic_mastery`.

```
sentence_fragment
run_on_sentence
subject_verb_agreement
tense
article
preposition
pronoun_reference
modifier
spelling
punctuation
word_choice
collocation
redundancy
informal_usage
cohesion
logical_order
off_topic
word_limit
format_violation
```

### 5.2 Stage 1 — Deterministic checks

Run synchronously at submission. No external calls. Returns in < 100ms.

- Required-word token presence (see §4.7)
- Server-authoritative word count (stored in `server_word_count`)
- Minimum/maximum word-limit compliance
- Sentence count
- Empty or extremely short answer
- Duplicate sentences across units
- Paragraph count
- Required format elements (from `exam_descriptive_requirements.format_rules`)
- Précis compression ratio

**Word count policy:** stored as `deterministic_evaluator_version` on `writing_evaluations`. Punctuation, hyphenated words and Unicode text can produce inconsistent counts; the version makes the counting rule auditable.

**`word_count_source`:** `'client'` during autosave, `'server'` after submit. The client displays a live count; the server recomputes on submit. Only `server_word_count` is authoritative for evaluation.

### 5.3 Stage 2 — Language issues

Async LLM call with structured output schema. Returns issue spans (§4.5b), explanations, severity, and lineage references. Returns `evaluator_version` for auditing.

Issue span format:

```json
{
  "issue_type": "subject_verb_agreement",
  "span_start_utf16": 4,
  "span_end_utf16": 25,
  "quoted_text": "The schemes is useful",
  "suggested_text": "The schemes are useful",
  "explanation": "Plural subject requires plural verb.",
  "severity": "must_fix",
  "microtopic_id": "<uuid>"
}
```

### 5.4 Stage 3 — Rubric evaluation

For paragraphs, essays and précis. Scores separate dimensions:

```
Grammar accuracy
Sentence construction
Vocabulary appropriateness
Clarity and conciseness
Coherence and cohesion
Content relevance
Organisation
Format compliance
Word-limit compliance
Précis fidelity and compression
```

Dimension keys are defined in `writing_rubrics.dimensions`. No hardcoded rubric labels in application code.

**Confidence gating:** `writing_evaluations.dimension_scores` includes per-dimension confidence. If confidence < 0.6 for a dimension, the API returns a score range (e.g. `{"min": 55, "max": 70}`) instead of a point estimate. Dimensions below 0.5 confidence are flagged for human review. Do not present rubric scores as official exam marks.

---

## 6. Error projection

Writing issue events must be projected into the canonical error categories before reaching the mastery pipeline. The canonical set (from `correction_policy.py`) is frozen:

```
concept_gap | memory_gap | careless | speed_issue | misread_question
option_trap | formula_confusion | time_management | unknown
```

Writing projection rules (frequency-dependent):

| Writing issue | First occurrence | Repeated occurrence |
|---|---|---|
| article, preposition, modifier, pronoun_reference | `careless` | `concept_gap` |
| subject_verb_agreement, tense, sentence_fragment, run_on_sentence, cohesion, logical_order | `concept_gap` | `concept_gap` |
| spelling | `careless` | `memory_gap` |
| word_choice, collocation, redundancy, informal_usage | `memory_gap` | `memory_gap` |
| punctuation | `careless` | `concept_gap` if systematic |
| off_topic | `misread_question` | `concept_gap` if repeated |
| word_limit | `time_management` | depends on timing evidence |
| format_violation | `concept_gap` | `concept_gap` |

**Unknown or low-confidence issues remain unprojected** (`canonical_error_type = null`). Never force a projection — unprojected issues are excluded from mastery evidence but are available in the Error Lab.

`prior_occurrence_count` is read transactionally at projection time. First occurrence = 0 prior occurrences.

---

## 7. Unit reopen

### 7.1 Endpoint

```http
POST /api/study/practice/english/sessions/{session_id}/units/{unit_id}/reopen
```

```json
{
  "expected_latest_version_id": "uuid",
  "reason": "session_check_failed"
}
```

### 7.2 Backend preconditions (evaluated before the transition)

```
session belongs to authenticated user
session.mode = 'learning'
session.status in ('rewrite_required', 'active')
unit.status = 'ready'
expected_latest_version_id matches current latest version (optimistic lock)
a current failed session-level check requires correction
```

The failed-check precondition is evaluated before the `ready → draft` transition. Once the transition commits, the prior check is superseded by the `draft` unit state — not by mutation of the check row.

### 7.3 Transaction

```
lock session row
lock unit row
validate expected_latest_version_id
transition unit: ready → draft
recompute session state via finalize_writing_session
commit
```

Multiple units may be reopened in separate requests. A failed required-word check may require changes to more than one sentence.

---

## 8. Stale evaluation contract

Evaluations belong to immutable versions. An evaluation of version 1 remains valid historical evidence even after version 2 exists.

### 8.1 Worker transaction sequence

```
1.  Load the requested unit version.
2.  Verify content hash:
      requested_content_hash = writing_unit_versions.content_hash
3.  Evaluate the version (LLM call or deterministic computation).
4.  Lock the parent writing_session_units row.
5.  Read the unit's current latest version.
6.  Persist the evaluation against the requested version (always).
7.  Insert writing_issue_events for this version.
      Set affects_current_state = (requested_version_id == latest_version_id).
      Issue events are always inserted — they are the permanent record of what the
      evaluator found. The staleness flag is stored on the row itself.
8.  If requested version != latest version (stale path):
      skip steps 9–12 and go to step 13 (commit only evaluation + issue events).
9.  Insert writing_issue_resolution_events for every prior active issue.
10. Insert writing_issue_projections.
11. Commit a writing_mastery_outbox job row (see §8.2).
      The outbox job is committed atomically with steps 9–10 so it cannot be lost.
12. Recompute unit and session state via finalize_writing_session.
13. Commit.
14. (Post-commit) Process mastery outbox job from step 11 — derive and write
      user_topic_mastery_evidence. If this step fails it is retried via the outbox
      job; the evaluation transaction is not affected.
```

**Insertion order within the transaction:**
- Issue events (step 7) are inserted before resolution events (step 9).
- `successor_issue_event_id` on resolution events references rows inserted in step 7.
- No deferred FK verification needed when inserts are sequenced correctly.

**Stale path summary:** evaluation row + issue events are always persisted (steps 6–7). Resolution events, projections, outbox jobs, and finalizer are skipped for stale versions. The `affects_current_state = false` flag on issue events gates downstream consumers (Error Lab, mastery, planner).

**Rewrite submission** must lock the same unit row before creating the next version. This removes the race between rewrite creation and evaluator completion.

**Evaluation idempotency key:**

```sql
unique (unit_version_id, evaluation_revision)
```

### 8.2 Mastery evidence emission (durable outbox, post-commit processing)

`user_topic_mastery_evidence` inserts must not be inside the main evaluation transaction. Lock contention or flag-read failures on mastery tables must not roll back the evaluation, issue, or resolution inserts.

**Required pattern — transactional outbox:**

A `writing_mastery_outbox` job row is inserted inside the evaluation transaction (step 11). The job row is committed atomically with the evaluation; it cannot be lost even if the post-commit processing step fails. After commit, a worker reads the outbox, derives mastery evidence, and writes `user_topic_mastery_evidence`. If evidence writing fails, the outbox job retries without re-running evaluation steps 1–10.

An optional "invoke-after-commit" callback without a committed outbox record is not permitted — it loses evidence on process crash between commit and callback execution.

**`writing_mastery_outbox` table (added in EWP-1 migration):**

```sql
id                uuid primary key
evaluation_id     uuid not null references writing_evaluations(id)
user_id           uuid not null references auth.users(id)
idempotency_key   text not null  -- SHA-256(evaluation_id || user_id || projection_revision)
status            text not null default 'pending'  -- 'pending' | 'processing' | 'done' | 'failed'
attempts          int not null default 0
max_attempts      int not null default 5
last_error        text
created_at        timestamptz not null default now()
processed_at      timestamptz

unique (idempotency_key)
```

### 8.3 Job claiming

Evaluation jobs use row-level locking (`SELECT ... FOR UPDATE SKIP LOCKED`) before transitioning to `running`. This prevents two workers from processing the same job.

---

## 9. Session finalizer

### 9.1 `finalize_writing_session(session_id)`

Single owner of session/unit state rollup. Executes transactionally or via atomic database RPC.

**Invoked after:**
- Session submission
- Deterministic evaluation completion
- Language evaluation completion
- Permanent job failure
- Recovery completion
- Session-check completion (coverage checker calls it after committing the check row)

**Locks:**
- `writing_sessions` row
- all required `writing_session_units` rows
- latest `writing_evaluations`
- current `writing_session_checks`

**The finalizer is idempotent.** Running it twice with the same inputs produces the same result.

**`evaluation_outcome` update:** conditional write to ensure monotonic improvement:

```sql
UPDATE writing_sessions
SET evaluation_outcome = $new_outcome
WHERE id = $session_id
  AND (
    evaluation_outcome IS NULL
    OR (
      evaluation_outcome = 'unscored' AND $new_outcome IN ('deterministic_only', 'fully_evaluated')
      OR evaluation_outcome = 'deterministic_only' AND $new_outcome = 'fully_evaluated'
    )
  )
```

### 9.2 Exam-mode session flow

```
active
→ submitted      (answers locked, editing forbidden, evaluation queued)
→ evaluation_pending
→ completed
```

At session submission:
1. All answer editing is locked.
2. A submitted immutable version is ensured for every required unit.
3. Any unanswered unit receives a server-created blank version (`submission_kind = 'blank'`).
4. Every unit moves to `evaluation_pending`.
5. Evaluation jobs are queued.

`submitted` separates the end of the exam interaction from the end of evaluation. The aspirant can leave; evaluation continues asynchronously.

### 9.3 `feedback_released_at` writer

The finalizer sets `feedback_released_at` based on the session's copied policy:

| Policy | `feedback_released_at` |
|---|---|
| `immediate` | `session.created_at` |
| `on_submit` | `session.submitted_at` |
| `scheduled_after_submit` | `submitted_at + feedback_release_delay_seconds` |
| `on_evaluation_terminal` | timestamp when all required unit evaluations become terminal (including `deterministic_only` and `unscored` — feedback must not remain hidden permanently because an external evaluator failed) |

For `on_evaluation_terminal`, "terminal" includes `fully_evaluated`, `deterministic_only`, and `unscored`.

---

## 10. Mastery and planner safety

### 10.1 Feature flag

Environment variables, matching the existing `FF_MOCK_MASTERY_WRITES` pattern:

```
FF_WRITING_MASTERY_WRITES=off|shadow|live
FF_WRITING_MASTERY_LIVE_USER_IDS=<comma-separated UUIDs>
```

**Fail-closed rules:**
```
invalid or missing value → off
live + empty allowlist → shadow
live + malformed allowlist → shadow
live + user absent from allowlist → shadow
```

**Behaviour by flag state:**

```
off:
  Persist writing_sessions, issue events, evaluations, and session checks only.
  No mastery evidence written.

shadow:
  Derive mastery deltas.
  Persist writing_mastery_shadow rows.
  Do not update user_topic_mastery.

live:
  Persist shadow row.
  Apply canonical mastery update.
  Only for allowlisted users.
```

### 10.1a `writing_mastery_shadow` table

Shadow rows record the mastery deltas that would be applied in `live` mode without touching `user_topic_mastery`. They must be idempotent — reprocessing the same evidence must not insert duplicate rows.

```sql
id                    uuid primary key
user_id               uuid not null references auth.users(id)
exam_id               uuid references exams(id)
topic_id              uuid not null references topics(id)
microtopic_id         uuid references topics(id)    -- level='microtopic'
source_type           text not null
source_entity_id      uuid not null
evaluation_id         uuid not null references writing_evaluations(id)
issue_projection_id   uuid references writing_issue_projections(id)
evidence_tier         text not null
score                 numeric
confidence            numeric
delta_json            jsonb not null default '{}'
idempotency_key       text not null   -- SHA-256(user_id || evaluation_id || topic_id || source_type)
processed_at          timestamptz not null default now()

unique (idempotency_key)
```

Insert uses `ON CONFLICT (idempotency_key) DO NOTHING` to guarantee at-most-once shadow rows for a given evidence event. No UPDATE or DELETE is permitted on this table.

### 10.2 Blocking constraint

Writing live mastery writes must not become a second independent writer racing the current mock mastery pipeline. Two options:

**Option A (preferred):** writing evidence enters the same unified mastery aggregator that processes mock evidence. The aggregator is the single writer of `user_topic_mastery`.

**Option B (fallback):** `FF_WRITING_MASTERY_WRITES=live` remains prohibited until `FF_MOCK_MASTERY_WRITES=live` is cleared and the unified aggregator is in place.

The current checklist marks canonical mock mastery live operation as blocked. Until that gate clears, writing evidence stays in shadow.

### 10.3 Shadow-to-live promotion gates

The flag must be changed by the deployment/operator owner. The checklist records operator approval and validation status. Promotion gates:

1. Exact replay produces byte-equivalent shadow decisions.
2. Reprocessing the same evidence creates no duplicate shadow rows.
3. No canonical mastery writes occur while in `shadow`.
4. Every mastery delta has traceable source evidence and projection version.
5. Projection agreement passes against a manually labelled writing-error benchmark.
6. No planner duplicate-retention tasks are generated.
7. Concurrent mock and writing evidence produces the same result regardless of processing order.
8. Failed evaluations create no mastery evidence.
9. A bounded per-user live canary passes.
10. Operator approval recorded in checklist.

Do not compare writing deltas to mock-derived deltas "within 5%." These are different evidence types with different scales.

---

## 11. Planner integration

### 11.1 Task launch target (not a stored URL)

`study_tasks` stores a typed launch target — not a frontend URL. The mission-control API computes the URL and label.

```sql
-- new columns on study_tasks
launch_type        text    -- 'english_writing_session' | null for non-english tasks
launch_entity_id   uuid    -- writing_sessions.id
launch_context     jsonb   -- {exercise_type, ...}
```

Mission-control response:

```json
{
  "launch_type": "english_writing_session",
  "launch_entity_id": "session-uuid",
  "action_url": "/app/study/practice/english/session-uuid",
  "action_label": "Start sentence practice"
}
```

When the front-end routing changes, only the mission-control URL-builder changes — no migration required.

### 11.2 Writing task types

`study_tasks.task_type` is an unconstrained text field. Valid writing task types:

```
sentence_construction
grammar_correction
vocabulary_in_context
sentence_rewrite
paragraph_writing
summary_writing
precis_practice
essay_practice
letter_practice
writing_revision
```

### 11.3 Scheduling logic

```
Repeated grammar error
→ sentence correction drill within 1 day

Error corrected successfully twice
→ delayed revision after 3–5 days (uses existing next_revision_at)

Strong sentence-level performance
→ progress to paragraph writing

Repeated essay word-limit failure
→ timed outline + constrained essay task

Retest scheduled for a microtopic
→ planner reads user_topic_mastery.next_revision_at as a hard trigger (priority band 1)
```

---

## 12. RLS contract

All schema writes are backend/service-role controlled. Aspirants receive only owner-select access.

### 12.1 Tables with owner-select RLS

```sql
-- writing_evaluations: owner-select gated by feedback_released_at
exists (
  select 1
  from writing_unit_versions v
  join writing_session_units u on u.id = v.unit_id
  join writing_sessions s on s.id = u.session_id
  where v.id = writing_evaluations.unit_version_id
    and s.user_id = auth.uid()
    and (
      s.mode = 'learning'
      or (
        s.feedback_released_at is not null
        and s.feedback_released_at <= now()
      )
    )
)
```

Equivalent join-based policies apply to `writing_issue_events`, `writing_issue_resolution_events`, `writing_issue_projections`.

### 12.2 Service-role-only tables (no client access)

```
writing_issue_review_events
user_topic_mastery_evidence
writing_evaluation_jobs
writing_mastery_shadow
writing_mastery_outbox
```

These tables intentionally have **no client allow policy**. An RLS policy of `USING (false)` or no policy at all is correct — there is no authenticated-user read path. A reviewer or implementer must not add a SELECT policy to any of these tables without an explicit architecture decision.

### 12.3 No-write from client rule

The browser has no INSERT, UPDATE, or DELETE permission on:

```
writing_issue_events
writing_issue_resolution_events
writing_issue_projections
writing_issue_review_events
user_topic_mastery_evidence
```

---

## 13. Frontend architecture

### 13.1 Route

```
/app/study/practice/english/:sessionId
```

Mounted under `StudyShell`. Wrapped in `RouteErrorBoundary`. Entry only via planner task launch target.

### 13.2 Shell hierarchy

```
EnglishPracticeShell
├── SentenceBuilder
├── SentenceCorrection
├── VocabularyUsage
├── GrammarDrill
├── ParagraphBuilder
└── ErrorReview
```

This shell does not go through `AttemptShellRouter`. That router fetches a mock attempt header and dispatches only between mock interface modes. Later, full descriptive mock exams will add `interface_mode = 'descriptive'` to the mock router — essays and précis conducted as timed examinations are real mock attempts and belong there.

### 13.3 Mandatory patterns

All frontend code follows AGENTS.md governance:

- Every route inside `RouteErrorBoundary`
- Every mutation via `useApiAction`
- Every data collection via `useApiCollection` (four-state: idle → loading → data | empty | error)

---

## 14. Locked implementation rules

The following rules are invariants. Violating them requires an architecture revision, not a local fix.

1. Practice sessions are not mock attempts.
2. Submitted `writing_unit_versions` and raw `writing_issue_events` are append-only and immutable.
3. Stale evaluations (non-latest version) are preserved as historical evidence but cannot change current unit or session state.
4. Rewrite submission and evaluator completion lock the same unit row.
5. Issue resolution events are backend-generated for every prior active issue.
6. False positives are invalidated through `writing_issue_review_events`, not by mutating issue rows.
7. Required-word coverage is a version-set-pinned session check, not a per-unit check.
8. `completed` units are terminal. `ready` units may be reopened. Regression after completion belongs to a new session.
9. Projection revisions are pinned per session at creation. Mixed projection rules within one session are forbidden.
10. Feature flags are deployment environment variables and fail closed.
11. Exam submission and evaluation completion are separate lifecycle stages.
12. Failed language evaluation emits no mastery evidence.
13. Feedback visibility is enforced by RLS using `feedback_released_at`, not suppressed in UI code only.
14. Retry accounting is owned by `writing_evaluation_jobs`, not embedded in evaluation rows.
15. All schema writes are backend/service-role controlled.
16. Study tasks persist typed launch targets (`launch_type`, `launch_entity_id`, `launch_context`), never frontend URLs.
17. Migration numbering comes from `select max(version)::int + 1 from schema_migrations`, not from filenames.
18. Mastery evidence emission is a post-commit step, not inside the evaluation transaction.
19. Mastery evidence must not directly mutate `user_topic_mastery`; a unified aggregator owns that write.
20. Only verified, active prompts and exam requirements reach aspirant or planner surfaces.
21. Issue lineage IDs are backend-assigned; the browser cannot set `lineage_id` or `predecessor_issue_event_id`.
22. Invalidated issues are excluded from every mastery and planner query.
23. `version_set_hash` is computed by one shared backend helper; clients consume it but never generate it.
24. UTF-16 span offsets plus `quoted_text` verification are the contract between the Python evaluator and the React frontend.

---

## 15. Learning progression

Do not start aspirants at essay level. Build evidence from sentences upward.

| Level | Exercise |
|---|---|
| 1 | Construct one correct simple sentence |
| 2 | Correct an incorrect sentence |
| 3 | Use a given word correctly in a sentence |
| 4 | Rewrite a sentence for clarity or conciseness |
| 5 | Reconstruct a scrambled sentence |
| 6 | Combine simple sentences into compound/complex |
| 7 | Write a coherent paragraph |
| 8 | Summarise a paragraph |
| 9 | Write a précis within a word limit |
| 10 | Complete a timed exam-specific descriptive paper |

`writing_prompts.difficulty_level` maps to this scale. The practice session API enforces `difficulty_level ≤ user_current_level`. `user_current_level` is derived from `user_topic_mastery_evidence` — highest `evidence_tier = 'production'` achieved per topic cluster.

Persona `writing_comfort_level` bootstraps cold-start:

| Persona answer | Starting level |
|---|---|
| "One sentence" | 3 |
| "A short paragraph" | 6 |
| "A précis" | 8 |
| "A full essay" | 9 |

After the first session, level is evidence-derived.

---

## 16. Release gates for advancing to paragraphs/essays

Move to paragraph or essay modes when these conditions pass — not after a fixed number of days:

1. No lost-answer incidents in autosave tests.
2. Idempotent version and rewrite submissions confirmed.
3. Deterministic word-count parity across all test vectors.
4. Issue-span accuracy validated on a curated benchmark (UTF-16 offset verification).
5. Acceptable false-positive rate for grammar feedback (human-labelled sample).
6. Mastery projection replay produces identical output.
7. Planner does not create duplicate retest tasks.
8. At least one exam configuration is officially sourced and reviewed (`exam_descriptive_requirements.reviewer_status = 'verified'`).
9. `FF_WRITING_MASTERY_WRITES` shadow gate passes (§10.3).
10. Operator approval recorded in checklist.

---

## 17. Prompt content ownership

Initial prompts are authored as embedded content in the existing Exam Workspace CMS. No new admin sidebar destination. The no-new-surface rule applies to admin surfaces too.

Minimum reviewed prompt bank before aspirant launch:

```
50 sentence-construction prompts
50 sentence-correction prompts
100 grammar-rule exercises
50 vocabulary-in-context prompts
20 scaffolded paragraph prompts
```

All prompts must pass the reviewer lifecycle (`reviewer_status = 'verified'`) before `is_active` can be set to `true`.
