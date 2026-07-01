# English Writing Practice — Architecture Contract

**Status:** DESIGN-LOCKED (merged in PR #819, 2026-07-01). Implementation per Lane H (EWP-1 in review — PR #821, code present / review pending; EWP-2 onward not started).
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
submitted              (exam mode only: answers locked, evaluation running)
completed
evaluation_incomplete  (terminal, operator-visible: a unit's recovery is exhausted
                        with no usable deterministic result — see §4.3b rule 3)
abandoned
```

#### 4.3b Session state rollup rules (priority order, first match wins)

```
1. any unit in (not_started, draft)
   → session: active

2. all units have submitted versions
   AND no unit in (not_started, draft)
   AND any unit in (evaluation_pending, evaluation_failed) WHILE recovery is available
        (evaluation_failed unit has a recoverable job: attempts < max_attempts
         OR a new generation can be created)
   → session: evaluation_pending

3. no unit in (not_started, draft, evaluation_pending)
   AND any unit in evaluation_failed with recovery EXHAUSTED
        (no usable terminal result and no further recovery)
   → session: evaluation_incomplete   (terminal, operator-visible)

4. no unit in (not_started, draft, evaluation_pending, evaluation_failed)
   AND (any unit in rewrite_required OR current session check failed)
   → session: rewrite_required

5. all gates pass (see §4.6c)
   → session: completed
```

Rule 2 keeps the session in `evaluation_pending` while an `evaluation_failed` unit is still recoverable (mirrors the unit-level `evaluation_failed → evaluation_pending` retry path, §4.4b). Rule 3 is the terminal escape hatch: a unit whose recovery is exhausted with no usable deterministic result puts the session in `evaluation_incomplete`, surfaced to operators — it never silently matches no rule and never hangs in `evaluation_pending` forever. (A language-only failure that still has a deterministic result becomes `ready`/`deterministic_only` per §4.4b and does not reach rule 3.)

`evaluation_incomplete` is added to the §4.3a session-state list as a terminal, operator-visible state.

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
  pending | partial | terminal_partial | completed | failed

deterministic_status:
  pending | completed | failed

language_status:
  not_requested | queued | running | completed | failed | needs_review

human_review_status:
  not_required | pending | in_review | completed
```

A re-evaluation under new evaluator logic requires `evaluation_revision = previous + 1`. That is a new evaluation envelope, not a retry.

#### 4.6a-1 Terminality vs completeness (deterministic mapping)

An evaluation is **terminal** when no further automatic stage will run; it is **complete** when all requested stages succeeded. These are separate properties. The finalizer maps stage statuses to `overall_status` deterministically:

| deterministic_status | language_status | overall_status | terminal? | maps to outcome |
|---|---|---|---|---|
| pending | * | `pending` | no | — |
| completed | not_requested / queued / running | `partial` | no | — |
| completed | completed | `completed` | yes | `fully_evaluated` |
| completed | failed (retries exhausted) | `terminal_partial` | yes | `deterministic_only` |
| completed | needs_review | `partial` | no | — |
| failed | * | `failed` | yes | `unscored` |

`terminal_partial` is the explicit terminal state for "deterministic succeeded, language permanently failed." A unit may become `ready` on `terminal_partial` with a `deterministic_only` session outcome. The finalizer has exactly one mapping for the language-failed/deterministic-complete case — there is no ambiguity between `partial`, `completed`, and `failed`.

#### 4.6b Typical learning-mode flow

```
submission
→ deterministic_status=completed, overall_status=partial
→ language_status=queued
→ language_status=running
→ language_status=completed, overall_status=completed
```

A failed async stage can be retried without rerunning deterministic checks. If language fails after retry exhaustion: `overall_status=terminal_partial` (see §4.6a-1).

#### 4.6c Session completion conditions (learning mode)

A unit is `ready` when:
- latest evaluation `overall_status` is terminal (`completed`, `terminal_partial`, or `failed` per §4.6a-1) — never `pending` or `partial`
- no latest active issue has `severity = 'must_fix'` without a resolution event with `outcome = 'resolved'`
- unit-level deterministic requirements pass

A `failed` (`unscored`) evaluation does not make a unit `ready` in learning mode — deterministic requirements have not passed. In exam mode a unit still moves to `ready` so feedback is not withheld permanently (§4.4b).

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

#### 4.10a Effective decision and supersession

Multiple review events may target one `issue_event_id` (e.g. `invalidated` then later `confirmed`). The **effective decision** is the latest event by `(created_at, id)` ordering. Derivation:

- Effective `confirmed` (or no review event) → issue is `active`.
- Effective `invalidated` → issue is `withdrawn`; excluded from `active_prior_issues`, `resolved_prior_lineages`, mastery, and planner queries.
- Effective `reclassified` → issue uses the corrected classification via a review-override projection (§4.11a).

Review events for one issue are **serialized** (processed in `(created_at, id)` order, one at a time). Each event that **changes** the effective decision emits exactly one correction evidence row keyed on that `review_event_id`, superseding the currently-effective evidence event — see the full transition matrix in §4.12c (including reversals like `invalidated → confirmed` which re-assert the original, and `reclassified → confirmed` which removes the replacement). A review event that does not change the effective decision (e.g. a redundant `confirmed`) emits nothing. Superseded events remain in the append-only history but do not drive current state.

---

### 4.11 `writing_issue_projections`

Versioned canonical classification. Separates raw language findings from mastery classification.

```sql
id                     uuid primary key
issue_event_id         uuid not null references writing_issue_events(id)
projection_revision    int not null   -- matches writing_sessions.projection_revision
projection_kind        text not null default 'automatic'  -- 'automatic' | 'review_override'
override_review_event_id uuid references writing_issue_review_events(id)  -- set iff kind='review_override'
canonical_error_type   text           -- maps to correction_policy.CANONICAL_CATEGORIES
projection_confidence  numeric
prior_occurrence_count int            -- occurrences of this issue_type for this user+microtopic
rationale              text
created_at             timestamptz not null default now()

check (
  (projection_kind = 'automatic' and override_review_event_id is null)
  or
  (projection_kind = 'review_override' and override_review_event_id is not null)
)

-- one automatic projection per (issue, revision)
unique (issue_event_id, projection_revision) where projection_kind = 'automatic'
-- one override per review event (idempotent under retry)
unique (override_review_event_id) where projection_kind = 'review_override'
```

The original `unique (issue_event_id, projection_revision)` is now a **partial** unique index scoped to `projection_kind='automatic'`. A `reclassified` review inserts a `review_override` row at the **same** session-pinned `projection_revision` without conflicting with the automatic row, because the partial index does not cover override rows. The override is deduplicated by `unique (override_review_event_id)`.

Consumers read the projection pinned to the session's `projection_revision`. They never select `ORDER BY projection_revision DESC`. The planner and mastery writer consume already-created mastery evidence that references the precise projection row, so they never ask "what is the latest projection for this issue."

Re-evaluation under new projection logic inserts a new row at a higher `projection_revision`. Old rows are immutable and auditable.

**Projection computation is race-safe.** A plain read-then-insert in a default-isolation transaction does not prevent two concurrent evaluations for the same user and microtopic from observing the same `prior_occurrence_count`. The implementation must use one of:

- A PostgreSQL advisory transaction lock keyed on `hashtext(user_id || microtopic_id || issue_type)` acquired before reading the count, OR
- `ISOLATION LEVEL SERIALIZABLE` for the projection insert transaction.

The lock/isolation must be acquired before reading `prior_occurrence_count` and held until the INSERT commits.

#### 4.11a Review-override projections vs revision bumps

`projection_revision` represents the **global code-defined projection ruleset**. It is bumped only when the projection logic is redeployed — never as a side effect of a single human review correction.

A `reclassified` review event (§4.10a) produces a **review-override projection**: a `writing_issue_projections` row with `projection_kind='review_override'` and `override_review_event_id` set, carrying the corrected `canonical_error_type`, inserted at the **same** `projection_revision` the session is pinned to — not a higher revision. The partial unique indexes (above) make this insert legal alongside the original automatic row. This keeps a human correction distinct from a global ruleset deployment. Consumers that read "the projection for this issue at the session's revision" must prefer the `review_override` row over the `automatic` row when an effective `reclassified` decision exists.

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
evidence_op           text not null default 'assert'  -- 'assert' | 'retract' | 'replace'
review_event_id       uuid references writing_issue_review_events(id)  -- cause for retract/replace
supersedes_evidence_key text          -- the evidence_key this row corrects (retract/replace)
evidence_key          text not null   -- see §4.12b
observed_at           timestamptz not null
metadata              jsonb not null default '{}'

unique (evidence_key)
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

**Tier ordering is explicit, never lexical.** The rank is:

```
recognition (1) < correction (2) < production (3) < retention (4)
```

Implemented as a `tier_rank(tier text) returns int` SQL helper or a fixed lookup. Any "highest tier achieved" or "tier below production" comparison uses this rank — never `evidence_tier < 'production'` string comparison, which is lexically wrong (`'correction' < 'production'` is true but `'recognition' < 'production'` is also true while `'retention' > 'production'` lexically yet retention outranks production).

#### 4.12b `evidence_key` — end-to-end idempotency

`evidence_key` is the deterministic dedup key that makes outbox delivery idempotent end to end. It identifies the exact evidence unit produced by one evaluation:

```
evidence_key = SHA-256(
  evidence_op || '\x00' ||              -- 'assert' | 'retract' | 'replace'
  user_id || '\x00' ||
  evaluation_id || '\x00' ||
  coalesce(issue_projection_id::text, 'no_projection') || '\x00' ||
  coalesce(microtopic_id::text, 'no_microtopic') || '\x00' ||
  evidence_tier || '\x00' ||
  source_type || '\x00' ||
  coalesce(review_event_id::text, 'no_review')   -- causal identity for retract/replace
)
```

`evidence_op` and `review_event_id` are part of the key so a retraction or replacement for the same `(evaluation, projection, tier, source)` produces a **distinct** key from the original `assert` row — it is not rejected by `unique (evidence_key)`. The original `assert` row keys with `evidence_op='assert'` and `review_event_id=null`; a `retract`/`replace` keys with the new op and the causing `review_event_id`, so each review event contributes exactly one correction row and re-running the same review event is idempotent.

The `unique (evidence_key)` constraint means a worker that inserts evidence, crashes before marking the outbox done, then retries, produces `ON CONFLICT (evidence_key) DO NOTHING` — no duplicate. The evidence insert and the outbox-completion UPDATE must occur in **one transaction** so completion is only recorded when evidence is durably written.

The shadow idempotency key (§10.1a) uses the same identity components (including `evidence_op` and `review_event_id`) — it must not collapse multiple projections, microtopics, tiers, or corrections produced for one evaluation.

**Mastery aggregator:** a separate process reads `user_topic_mastery_evidence` and computes `user_topic_mastery`. Evidence must not directly mutate `user_topic_mastery`. The existing mastery recomputation from `mock_topic_breakdowns` must not be overwritten by a parallel writing update.

#### 4.12c Correction path (post-emission) — transition matrix

When a `writing_issue_review_events` row changes the **effective decision** (§4.10a) for an issue **after** evidence/shadow rows already exist, the existing rows are never mutated (append-only). A correction evidence row is appended. Review events for one `issue_event_id` are **serialized** (processed in `(created_at, id)` order, one at a time per issue) so the effective decision is well defined at each step.

`supersedes_evidence_key` always points to the **currently effective** evidence event for the issue — not always the original assertion. The correction supersedes whatever is effective now.

Transition matrix (previous effective decision → new effective decision):

| From → To | Emitted correction | `evidence_op` | supersedes |
|---|---|---|---|
| (none) → confirmed/active | original assertion | `assert` | — |
| active → invalidated | retract | `retract` | effective assert row |
| active → reclassified | replace (override projection §4.11a) | `replace` | effective assert row |
| invalidated → confirmed | re-assert (restores original classification) | `assert` | effective retract row |
| reclassified → confirmed | re-assert original (removes replacement) | `assert` | effective replace row |
| reclassified → invalidated | retract the replacement | `retract` | effective replace row |
| invalidated → reclassified | replace from withdrawn | `replace` | effective retract row |
| reclassified → reclassified (new) | replace superseding prior replacement | `replace` | effective replace row |

Each effective-decision change emits exactly **one** correction, keyed on the causing `review_event_id` (in `evidence_key`, §4.12b). A review event that does not change the effective decision (e.g. redundant `confirmed`) emits nothing. The aggregator folds `assert/retract/replace` in causal order and nets the result.

**Corrections are independent of the current feature flag.** A correction inherits the **channels/mode of the assertion it supersedes**, resolved from the superseded evidence row (or the outbox `mastery_flag_state` that produced it) — NOT re-resolved from the current `FF_WRITING_MASTERY_WRITES`. Rationale: an assertion emitted in `shadow`, then the flag flipped to `off`, then the issue invalidated, must still emit a `retract` so the planner stops seeing the withdrawn evidence. Flag changes may stop **new assertions**; they must never suppress retractions/replacements for already-persisted evidence. Therefore a correction outbox row is created whenever a superseded evidence row exists, regardless of the current flag; its `mastery_flag_state` is copied from the superseded row.

**Outbox for corrections:** enqueued as a `writing_mastery_outbox` row with `source_kind='review_correction'`, sourced by `review_event_id` (not `evaluation_id`). `idempotency_key` includes `review_event_id` + `evidence_op`, so each effective-decision change enqueues a distinct correction job. See §8.2.

The aggregator is the single point that nets corrections against prior effects. No writing-side code mutates `user_topic_mastery` directly.

#### 4.12d Effective-evidence fold (the only planner/level source)

`user_topic_mastery_evidence` is append-only: a `retract` or `replace` leaves the original `assert` row intact. Reading the raw table directly would let a retracted `production` assertion still advance level or generate tasks. Therefore neither the planner nor level derivation reads the raw table.

A single backend-owned view/RPC `effective_user_topic_mastery_evidence` is the only source for personalization and level:

- folds `assert / retract / replace` chains per `(user, issue lineage / supersedes chain)` in causal order,
- yields only the currently-effective row per chain (retracted chains yield nothing; replaced chains yield the replacement),
- honours the effective review decision (§4.10a) and excludes withdrawn/invalidated and stale (`affects_current_state=false`) projections,
- is the sole input to EWP-5 planner personalization and to `user_current_level` derivation (§15).

The unified mastery aggregator consumes the same fold, so canonical mastery, planner, and level all agree.

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
claim_token    uuid            -- set on claim; checked (fenced) in the final write txn (§8.3)
last_error     text
created_at     timestamptz not null default now()
updated_at     timestamptz not null default now()

unique (evaluation_id, job_kind, generation)
```

`locked_at` + `claim_token` implement the lease/fencing contract in §8.3: a stale worker whose lease expired cannot commit after another worker reclaims the job with a new token.

**Active-job uniqueness:**

```sql
unique (evaluation_id, job_kind) where status in ('pending', 'running')
```

**Recovery flow:** when `status = 'failed'` and `attempts = max_attempts`, a recovery operator or system creates a new row with `generation = previous + 1, attempts = 0`. The `compare-and-set` on `language_status: failed → queued` ensures the evaluation envelope is updated atomically. The failed job row remains for observability. The `unique (evaluation_id, job_kind, generation)` constraint prevents concurrent recovery workers from inserting duplicate generation rows.

A completed language result cannot be overwritten by recovery. Re-evaluation under changed evaluator logic requires a new `evaluation_revision` (new envelope row).

---

### 4.15 `writing_issue_type_microtopic_map`

Backend-owned mapping from `issue_type` (§5.1) to the canonical English microtopic. The evaluator returns `issue_type` only; the backend resolves the microtopic through this table (§5.3). The model never supplies taxonomy IDs.

```sql
id              uuid primary key
issue_type      text not null   -- from the §5.1 enum
microtopic_id   uuid not null references topics(id)   -- must be English subject, level='microtopic'
map_version     int not null default 1
is_active       boolean not null default true
created_at      timestamptz not null default now()

-- exactly one active mapping per issue_type
unique (issue_type) where is_active = true
unique (issue_type, map_version)
```

**Validation at seed and at resolve time:** the referenced `topics` row must be inside the English subject tree, `level='microtopic'`, and active. Seeded in EWP-1 with stable UUIDs (same determinism rule as the taxonomy seed). Versioned: a remap inserts a new `map_version` and flips `is_active`; history is retained.

**RLS / writes:** service-role-only writes. Read policy: readable by authenticated users (it is non-sensitive reference data) OR service-role-only if the frontend never needs it — EWP-1 records the deliberate choice. It is not append-only (active flag flips), so it gets no immutability trigger.

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
  "severity": "must_fix"
}
```

**The evaluator does NOT supply taxonomy IDs.** The model returns only `issue_type` (from the §5.1 enum). The backend owns the mapping from `issue_type` to the canonical `topics(id)` microtopic. JSON-schema validation only proves UUID *shape* — it cannot prove a model-supplied ID belongs to English, is `level='microtopic'`, is active, or matches the issue type. Letting the model choose arbitrary repository taxonomy IDs is forbidden.

Backend resolution before any `writing_issue_events` insert:
- map `issue_type` → canonical microtopic via a backend-owned lookup table seeded in EWP-1,
- assert the resolved `topics` row is in the English subject tree, `level='microtopic'`, and active,
- reject the issue (or fall back to topic-level with `microtopic_id=null`) if no valid mapping exists.

Any future schema field that carries a taxonomy ID from the model is validated against subject + level + active state + allowed issue-type mapping before insert.

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

Follows the canonical lock order (§8.0): session row first, then ALL required units ascending.

```
lock session row                        (canonical order step 1)
lock ALL required units, ascending      (canonical order step 2 — not just the target)
validate expected_latest_version_id
transition target unit: ready → draft
recompute session state via finalize_writing_session
commit
```

Multiple units may be reopened in separate requests. A failed required-word check may require changes to more than one sentence.

---

## 8. Stale evaluation contract

Evaluations belong to immutable versions. An evaluation of version 1 remains valid historical evidence even after version 2 exists.

### 8.0 Canonical lock order (global, deadlock-free)

Every path that locks more than one row acquires locks in exactly this order:

```
1. writing_sessions (the session row)
2. writing_session_units — ALL required units of the session, ascending unit_number
     (not just the target unit — because finalize_writing_session locks them all)
3. writing_evaluations / writing_session_checks
4. writing_evaluation_jobs / writing_mastery_outbox
```

**Lock all required units, ascending, up front.** A path that touches only one unit still locks the full required-unit set in ascending `unit_number` immediately after the session row, before operating on the target unit or entering `finalize_writing_session`. Locking only unit 5 and then letting the finalizer lock units 1–4 produces the order `session → unit5 → unit1..4`, which deadlocks against a worker holding unit 1 and waiting for unit 5. Acquiring `session → unit1..N (asc)` up front makes every path request unit locks in the same order.

No path may hold a unit lock and then acquire the session lock — that inversion is forbidden. This ascending-all-units rule applies to the evaluator completion, reopen (§7.3), session submission, and recovery paths. This single order eliminates both the session↔unit and the unit↔unit deadlock.

### 8.1 Worker transaction sequence

```
1.  Load the requested unit version (answer_text + stored content_hash).
2.  Verify content hash by RECOMPUTING from the stored text:
      sha256(stored_answer_text) == stored_content_hash == requested_content_hash
      All three must be equal. Recomputation (not field equality) is what
      detects corrupted or mutated text; the requested_content_hash check
      only proves the caller carried the stored value.
      If they differ → abort as corrupt; do not evaluate.
3.  Evaluate the version (LLM call or deterministic computation).
      NO database transaction is open during the external/LLM call.
      The locking/write transaction (steps 4–14) begins only after the
      evaluator returns.
4.  Lock rows in canonical order (§8.0): writing_sessions row FIRST,
      then ALL required writing_session_units rows ascending by unit_number
      (not just the target unit — the finalizer will lock them all).
      Never unit-before-session; never target-unit-before-lower-numbered-units.
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
11. Insert a writing_mastery_outbox job row (see §8.2).
      Committed atomically with steps 6–10 so it cannot be lost.
12. Recompute unit and session state via finalize_writing_session.
13. Set the claimed writing_evaluation_jobs row status = 'done' (SAME transaction).
14. Commit. — steps 4–13 are ONE transaction. Job acknowledgement and all
      side effects commit together; there is no window where side effects are
      durable but the job is still claimable.
15. (Post-commit) Process mastery outbox job from step 11 — derive and write
      user_topic_mastery_evidence. If this step fails it is retried via the outbox
      job; the evaluation transaction is not affected.
```

**Atomic job acknowledgement (no replay duplication):** the claimed job's `status='done'` UPDATE is part of the same transaction as steps 6–13. A crash after side effects commit but before acknowledgement is impossible — both commit together. If the worker crashes *before* the commit, the whole transaction rolls back and the job is re-claimable with no partial side effects.

**Replay guard (defense in depth):** before re-running, the worker checks whether the evaluation envelope (`unique(unit_version_id, evaluation_revision)`) is already in a terminal `overall_status`. An already-terminal evaluation is not re-processed; the job is acknowledged. This protects against any path that re-delivers a job whose side effects already landed. A crash-after-commit/before-ack regression test is required in EWP-2B.

**Insertion order within the transaction:**
- Issue events (step 7) are inserted before resolution events (step 9).
- `successor_issue_event_id` on resolution events references rows inserted in step 7.
- No deferred FK verification needed when inserts are sequenced correctly.

**Stale path summary:** evaluation row + issue events are always persisted (steps 6–7), and the job is still acknowledged (step 13). Resolution events, projections, outbox jobs, and finalizer are skipped for stale versions. The `affects_current_state = false` flag on issue events gates downstream consumers (Error Lab, mastery, planner).

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
id                  uuid primary key
source_kind         text not null  -- 'evaluation' | 'review_correction'
evaluation_id       uuid references writing_evaluations(id)            -- set when source_kind='evaluation'
review_event_id     uuid references writing_issue_review_events(id)    -- set when source_kind='review_correction'
evidence_op         text not null default 'assert'  -- 'assert' | 'retract' | 'replace'
user_id             uuid not null references auth.users(id)
mastery_flag_state  text not null  -- pinned 'shadow' | 'live' at row creation; see below
idempotency_key     text not null  -- see below
status              text not null default 'pending'  -- 'pending' | 'processing' | 'done' | 'failed'
attempts            int not null default 0
max_attempts        int not null default 5
locked_at           timestamptz
last_error          text
created_at          timestamptz not null default now()
processed_at        timestamptz

check (
  (source_kind = 'evaluation' and evaluation_id is not null and review_event_id is null)
  or
  (source_kind = 'review_correction' and review_event_id is not null)
)
unique (idempotency_key)
```

**Idempotency key:**
- `evaluation` source: `SHA-256('eval' || evaluation_id || user_id || projection_revision)`
- `review_correction` source: `SHA-256('review' || review_event_id || evidence_op || user_id)`

A later invalidation/reclassification therefore enqueues a **distinct** correction job for the same evaluation — the original evaluation-sourced row does not block it.

**Mode pinning (mirrors the mock pinned-mode regression contract):** the effective `off|shadow|live` mode — including the per-user allowlist resolution — is resolved **once**, when the outbox row is created (inside the evaluation transaction), and stored in `mastery_flag_state`. The worker reads `mastery_flag_state` from the row and never re-reads the environment or allowlist. Retries and recovery reuse the pinned mode. This prevents an in-flight job from being processed under a later environment/allowlist value.

For `source_kind='evaluation'` (new assertions), the mode comes from the current flag at creation time:
- `off`: **no outbox row is created.** No mastery side effects exist to track.
- `shadow`: outbox row with `mastery_flag_state = 'shadow'`; worker writes source-neutral `user_topic_mastery_evidence` + `writing_mastery_shadow` delta rows; canonical aggregation stays disabled.
- `live`: outbox row with `mastery_flag_state = 'live'`; worker writes evidence + shadow row and publishes to the unified aggregator (see §10.2). `live` is prohibited until Lane A clears (§10.2).

For `source_kind='review_correction'` (retract/replace/re-assert), the mode is **copied from the superseded evidence row**, NOT re-resolved from the current flag (§4.12c). A correction outbox row is created whenever a superseded evidence row exists — even if the current flag is `off` — so retractions are never suppressed by a later flag change.

**Worker transaction contents (shadow and live).** The evidence insert, the shadow-row insert, and the outbox `done` update must all be in **one** transaction:

```
1. insert effective user_topic_mastery_evidence  (ON CONFLICT (evidence_key) DO NOTHING)
2. insert writing_mastery_shadow                 (ON CONFLICT (evidence_key) DO NOTHING)
3. [live only] publish to unified aggregator
4. update writing_mastery_outbox: status='done'
```

Committing all together prevents evidence/shadow drift (evidence committed but shadow lost, or the outbox acknowledged while a row is missing). A crash before commit rolls back all four and the outbox row is re-claimable (lease, §8.3).

### 8.3 Job claiming and recovery

**Evaluation jobs** (`writing_evaluation_jobs`) use row-level locking (`SELECT ... FOR UPDATE SKIP LOCKED`) before transitioning to `running`. This prevents two workers from claiming the same job simultaneously. But because the LLM call runs **outside** the write transaction (§8.1 step 3), a worker can claim a job, set `running`, and crash mid-call — leaving it stuck. Evaluation jobs therefore need the same lease + fencing contract as the outbox:

- **Lease:** claiming stamps `locked_at` and a `claim_token` (uuid). A sweeper resets `running` rows whose `locked_at` is older than the lease back to `pending`, increments `attempts`, and clears `claim_token`.
- **Max attempts:** a job reaching `max_attempts` transitions to `failed` (permanent-failure handling, §4.6a-1); it never loops forever.
- **Fencing:** the final write transaction (§8.1 steps 4–14) re-reads the job row `FOR UPDATE` and asserts its `claim_token` still matches the token the worker holds. If a slow worker's lease expired and another worker reclaimed the job (new token), the stale worker's assertion fails and its transaction aborts — it cannot commit side effects for a job it no longer owns. Combined with the `unique(unit_version_id, evaluation_revision)` envelope and the already-terminal replay guard, this prevents double application.
- **Tests (EWP-2B):** crash during LLM call → job reclaimed and completes once; lease-expiry double-worker → only the current owner commits, the stale worker aborts.

`claim_token uuid` and `max_attempts` already exist on the table; add the sweeper and the fencing re-check.

**Mastery outbox jobs** (`writing_mastery_outbox`) use the same claiming protocol: a worker claims a `pending` row with `SELECT ... FOR UPDATE SKIP LOCKED`, sets `status='processing'` and stamps `locked_at`, then performs the evidence write + completion in one transaction (§4.12b). A `processing` row whose `locked_at` is older than a configured lease (stuck/crashed worker) is reclaimable: a sweeper resets `processing` rows past the lease back to `pending` and increments `attempts`. Because the evidence write is keyed on `evidence_key` with `ON CONFLICT DO NOTHING`, reclaiming a row that already wrote its evidence is safe — the re-run inserts nothing and simply marks the row `done`. A row reaching `max_attempts` is set `failed` and surfaced for operator attention; it never silently drops.

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

#### 9.1a Session-level outcome aggregation (deterministic)

Per-evaluation outcome is mapped in §4.6a-1. A session has many units with possibly mixed outcomes. The finalizer computes the session `evaluation_outcome` by this fixed rule over the latest evaluation of each **required** unit (first match wins):

```
1. any required unit's latest evaluation is non-terminal
     → session outcome not yet computed (stay pending/active)
2. any required unit deterministic failure (overall_status = 'failed' / unscored)
     → session: unscored
3. else any required unit terminal language failure (overall_status = 'terminal_partial' / deterministic_only)
     → session: deterministic_only
4. else all required units fully_evaluated
     → session: fully_evaluated
```

Blank exam units (`submission_kind='blank'`) are required units and participate in this rule.

**`evaluation_outcome` update:** conditional write to ensure monotonic improvement. The aggregate from §9.1a is the `$new_outcome`:

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

**Monotonic recovery on a completed session:** if a previously language-failed unit is later recovered (new `generation`) and reaches `fully_evaluated`, the finalizer recomputes §9.1a and the conditional UPDATE upgrades `deterministic_only → fully_evaluated`. This improves the recorded outcome **without** reopening interaction state: `completed` units stay `completed`, no version is created, no unit returns to `draft`. Recovery only ever upgrades the outcome; it never downgrades and never reopens the session.

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
  No user_topic_mastery_evidence and no shadow rows written.

shadow:
  Write source-neutral user_topic_mastery_evidence (raw evidence).
  Derive and persist writing_mastery_shadow delta rows.
  Do NOT run canonical aggregation into user_topic_mastery.

live:
  Write source-neutral user_topic_mastery_evidence.
  Persist shadow delta row.
  Publish validated evidence to the unified mastery aggregator
    (which is then enabled to update user_topic_mastery).
  Never write user_topic_mastery directly (see locked rule 19).
  Only for allowlisted users.
```

**Locked contract (resolves the shadow/planner question):** `shadow` **does** write source-neutral `user_topic_mastery_evidence`. Only canonical aggregation into `user_topic_mastery` is disabled in shadow. This is deliberate so the EWP-5 planner can read writing evidence at microtopic granularity throughout the shadow period and generate drills — without any canonical mastery mutation. `writing_mastery_shadow` records the *delta decision* the aggregator would apply; the evidence table records the *raw observation*.

`live` does **not** apply a direct canonical mastery update from writing code. Per locked rule 19, the unified aggregator is the single writer of `user_topic_mastery`. `live` publishes validated evidence to that aggregator and enables aggregation. Until the aggregator exists and Lane A clears (§10.2), `live` is prohibited.

**Planner safety in shadow:** because evidence exists but canonical mastery is not mutated, the planner personalizes from `user_topic_mastery_evidence` directly during shadow. It must not read `user_topic_mastery` deltas attributable to writing until `live`.

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
evidence_key          text not null   -- same identity as user_topic_mastery_evidence.evidence_key (§4.12b)
processed_at          timestamptz not null default now()

unique (evidence_key)
```

The shadow key is the same `evidence_key` defined in §4.12b: it includes `issue_projection_id`, `microtopic_id`, and `evidence_tier`, so multiple projections/microtopics/tiers from one evaluation produce distinct rows and are not collapsed. Insert uses `ON CONFLICT (evidence_key) DO NOTHING` to guarantee at-most-once shadow rows. No UPDATE or DELETE is permitted on this table.

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

Every owner-readable table gets an explicit SELECT policy. The exact policy per table:

| Table | Owner SELECT policy (`USING`) |
|---|---|
| `writing_sessions` | `user_id = auth.uid()` |
| `writing_session_units` | owner via join: `exists (select 1 from writing_sessions s where s.id = session_id and s.user_id = auth.uid())` |
| `writing_unit_versions` | owner via join through `writing_session_units` → `writing_sessions` to `auth.uid()` |
| `writing_session_checks` | owner via join: `exists (select 1 from writing_sessions s where s.id = session_id and s.user_id = auth.uid())` — required so the learning UI can render failed-coverage feedback |
| `writing_prompts` | `reviewer_status = 'verified' AND is_active = true` (catalog read; not user-scoped) |
| `exam_descriptive_requirements` | `reviewer_status = 'verified' AND is_active = true` |
| `writing_rubrics` | readable (referenced by verified prompts) |
| `writing_evaluations` | owner via join + feedback gate (below) |
| `writing_issue_events` | owner via join + feedback gate; invalidated issues filtered (§4.10) |
| `writing_issue_resolution_events` | owner via join + feedback gate |
| `writing_issue_projections` | owner via join + feedback gate |

The feedback-gated owner policy (evaluations and the issue tables):

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

Equivalent join-based feedback-gated policies apply to `writing_issue_events`, `writing_issue_resolution_events`, `writing_issue_projections`. `writing_sessions`, `writing_session_units`, `writing_unit_versions`, and `writing_session_checks` use the plain owner policies above (no feedback gate — they carry no released-feedback content, and the UI needs session/coverage state to render progress).

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

### 12.4 Append-only enforced at the database, not just by convention

RLS does not constrain the `service_role` — it bypasses row policies. Append-only tables therefore need **database-level immutability triggers** (or equivalent privilege fencing) so that even backend/service-role code cannot UPDATE or DELETE history rows. EWP-1 must install a `BEFORE UPDATE OR DELETE` trigger that raises an exception on:

```
writing_unit_versions          (entire row immutable after insert)
writing_issue_events
writing_issue_resolution_events
writing_issue_projections
writing_issue_review_events
user_topic_mastery_evidence
writing_mastery_shadow
```

Tables that legitimately mutate (`writing_sessions`, `writing_session_units`, `writing_evaluations`, `writing_evaluation_jobs`, `writing_mastery_outbox`) are excluded — their state columns are designed to change.

EWP-1 tests must prove a `service_role` UPDATE and a `service_role` DELETE both fail on each immutable table.

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

`writing_prompts.difficulty_level` maps to this scale. The practice session API enforces `difficulty_level ≤ user_current_level`. `user_current_level` is derived from the effective-evidence fold `effective_user_topic_mastery_evidence` (§4.12d) — highest `evidence_tier = 'production'` (by `tier_rank`) achieved per topic cluster. It must NOT read the raw append-only table, or a retracted `production` assertion could inflate level.

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
