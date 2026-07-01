# Topic Prerequisite Semantics and Planner Authority Gate — J2-A′

- Document type: J2-A′ implementation contract — topic prerequisite semantics, trust lifecycle, and planner authority
- Status: **DRAFT — OPERATOR APPROVAL REQUIRED** (no implementation PR may be dispatched until OPERATOR APPROVED)
- Date: 2026-07-01
- Parent track: `J2 — missing operational editors in Manage Exam` (J2-A′ sub-slice, blocked in `Manage-Exam-Operational-Editors-Gate-2026-07-01.md` OD-9 / rule 6)
- Authority: `Manage-Exam-Operational-Editors-Gate-2026-07-01.md` §D (permission tiers, rules 3–5); `docs/architecture/domain-model.md`
- Prerequisite gates cleared: J2-A merged (PR #826 `822f874`)
- Blocks: J2-A′ implementation. Does NOT block J2-B/J2-C gate work sequencing, but the operator has directed J2-B/J2-C implementation must not begin until this gate is settled.

---

## How to use this document

This gate **reconciles the existing implementation** — it does not design from scratch. Every section states a LOCKED decision or an exact specification. Items marked **OPERATOR DECISION REQUIRED** must be resolved by operator approval and not guessed.

**No implementation PR may be dispatched until this document is OPERATOR APPROVED.**

**Serial delivery rule (locked):** J2-A′ touches the planner (`study_os/planner.py`) and the Manage Exam surface — one owner's sequential work, no fan-out.

---

## Section 0 — Actual implementation baseline

### 0.1 Table (`topic_prerequisites`, migration 029)

```sql
create table public.topic_prerequisites (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid not null references public.topics(id) on delete cascade,
  prerequisite_topic_id uuid not null references public.topics(id) on delete cascade,
  relation_type text not null default 'requires'
    check (relation_type in ('requires','recommended_before','supports','foundation_for')),
  strength numeric(4,3) not null default 1.0 check (strength >= 0 and strength <= 1),
  source_basis text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(topic_id, prerequisite_topic_id),
  check (topic_id <> prerequisite_topic_id)
);
```

- **No lifecycle column** (`reviewer_status` etc.) and **no reviewer/author columns** exist today.
- Edge direction: `topic_id` → `prerequisite_topic_id`. RLS: authenticated read (migration 035).

### 0.2 CMS endpoints (`admin_exam_intel_cms.py`, `exam_intelligence.cms`)

- `GET/POST/DELETE /topic-prerequisites`. POST validates both topics resolve, relation is in the 4-value set, and rejects **only the direct reverse edge** (`B→A` when `A→B` exists). No transitive cycle detection.

### 0.3 Planner consumption (`study_os/planner.py`)

- `_ORDERING_RELATIONS = {"requires", "recommended_before"}` (`supports`/`foundation_for` ignored for ordering).
- `_load_prerequisites` reads `topic_prerequisites` **with no review-status filter** — every matching row is consumed.
- `strength` is **not read** by the planner.
- `_order_by_priority_with_prereqs` limits ordering to prerequisites **inside the candidate set**, and falls back to plain priority order when blocked (cycle or out-of-set prerequisite). Plan generation never blocks on prerequisites.

---

## Section A — Gaps J2-A′ closes

| # | Gap | Consequence |
|---|---|---|
| G-1 | No trust lifecycle on edges | A `manage`-tier edit changes planner behavior immediately — contradicts the locked "editing must not imply approval" rule (J2-A gate rule 3). |
| G-2 | Planner reads unreviewed edges | Draft/unreviewed edges affect real user plans. |
| G-3 | Only direct-reverse cycle detection | `A→B→C→A` is accepted; ordering silently falls back, hiding a data error. |
| G-4 | `strength` semantics undefined | Stored but unused; ambiguous authority. |
| G-5 | No Manage-Exam prerequisite editor | Prerequisite editing only via Advanced Repair (cms). |

---

## Section B — Semantic decisions (LOCKED)

| ID | Decision |
|---|---|
| PD-1 | **Scope.** Prerequisite edges stay **globally canonical** (the table has no `exam_id`; the planner reads them globally). Manage Exam may create/edit an edge **only when BOTH topics belong to the current exam's resolved subject set** (coverage path, reusing J2-A `_exam_subject_ids`). |
| PD-2 | **Direction (LOCKED meaning).** `topic_id` **depends on** `prerequisite_topic_id` (i.e. `prerequisite_topic_id` must come first). |
| PD-3 | **Planner relations.** Only `requires` and `recommended_before` affect ordering (unchanged). `supports` and `foundation_for` remain **descriptive, Advanced-Repair-only** until a consumer is defined. |
| PD-4 | **Strength.** Stored and displayed; **does NOT affect planner scoring or ordering** in J2-A′. Advisory metadata until a separate deterministic algorithm is approved in its own gate. |
| PD-5 | **Planner out-of-set behavior (unchanged).** A prerequisite outside the selected candidate set is informational and must not block plan generation. Current fallback behavior is preserved. |

---

## Section C — Trust lifecycle (LOCKED)

### C.1 States and transitions

```
draft → pending_review → reviewed → locked
                       ↘ rejected
```

- `exam_intelligence.manage`: **creates and edits** edges in `draft` or `rejected` state; may submit `draft → pending_review`. Cannot review.
- `exam_intelligence.review`: performs lifecycle transitions (`pending_review → reviewed`, `reviewed → locked`, `pending_review → rejected`, `reviewed → rejected`, `locked → reviewed` reopen-with-notes). Cannot create canonical content.
- `super_admin`: bypass.

### C.2 Transition matrix (LOCKED)

| From \ To | draft | pending_review | reviewed | locked | rejected |
|---|---|---|---|---|---|
| draft | — | manage/review | — | — | review |
| pending_review | — | — | review | — | review |
| reviewed | — | — | — | review | review |
| locked | — | — | review (reopen; notes required) | — | — |
| rejected | manage (edit back to draft) | — | — | — | — |

Any transition not in the matrix → 409. Reopen (`locked → reviewed`) requires `review_notes` (mirrors the score-snapshot reopen precedent).

### C.3 Editing/deletion under lock (LOCKED — J2-A gate rules 4/5)

- `manage` may edit an edge only while `draft`/`rejected`. A `locked`/`reviewed`/`pending_review` edge must be reopened by `review` first.
- Deleting a `locked` edge is blocked; it must be reopened first. Forced cleanup remains Advanced Repair / `exam_intelligence.cms`.

---

## Section D — Migration decision (LOCKED shape; one item OPERATOR DECISION)

A forward migration adds to `topic_prerequisites`:

```sql
reviewer_status text not null default 'draft'
  check (reviewer_status in ('draft','pending_review','reviewed','locked','rejected')),
reviewed_by uuid references public.profiles(id) on delete set null,
reviewed_at timestamptz,
review_notes text,
created_by uuid references public.profiles(id) on delete set null,
updated_at timestamptz not null default now()
```

Plus an index on `(reviewer_status)` for the planner's locked-only read.

**OPERATOR DECISION REQUIRED — backfill of existing rows:** the planner will switch to reading **only `locked`** edges (Section G). Existing edges predate the lifecycle and were effectively live. Options:
- **PD-D-opt-1 (RECOMMENDED):** backfill existing rows to `locked` — grandfathers already-live curated edges so planner output does not silently change on deploy.
- PD-D-opt-2: backfill to `draft` — forces re-review of every existing edge; planner ordering loses all current prerequisite influence until re-locked (behavior regression until review sweep completes).

RLS/grants updated per migration discipline; verify with `pg_policies` before marking complete.

---

## Section E — Recursive cycle-validation contract (LOCKED)

- Cycle detection must reject **all transitive cycles** (`A→B→…→A`), not just the direct reverse edge.
- The check must be **transactional and race-safe**: two concurrent inserts must not be able to jointly form a cycle. Implement as a **`SECURITY DEFINER` RPC** (e.g. `cms_add_topic_prerequisite`) that, inside one transaction, takes the appropriate row/advisory lock, runs a **recursive CTE** reachability test from `prerequisite_topic_id` back to `topic_id`, and inserts only if no path exists. This mirrors the existing review-RPC pattern (migrations 185/201).
- The unique `(topic_id, prerequisite_topic_id)` constraint and `topic_id <> prerequisite_topic_id` check remain.
- Cycle detection considers only ordering relations (`requires`, `recommended_before`) — `supports`/`foundation_for` do not form ordering cycles (PD-3).

---

## Section F — Endpoint shapes (LOCKED)

Under the J2 `manage` router (`/admin/exam-intelligence-manage`), all mutations single-token `require_permission("exam_intelligence.manage")`; reviews single-token `require_permission("exam_intelligence.review")`; reason + audit on every write; PD-1 scope enforced on both endpoints of an edge.

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/topic-prerequisites?exam_id&topic_id` | manage | list edges for a topic (both directions), with `reviewer_status` |
| POST | `/topic-prerequisites?exam_id` | manage | create `draft` via the cycle-safe RPC (Section E); both topics ∈ exam subjects (PD-1); never sets a review state |
| PATCH | `/topic-prerequisites/{id}?exam_id` | manage | edit only while `draft`/`rejected`; relation/strength/source_basis; re-run cycle check if endpoints change |
| POST | `/topic-prerequisites/{id}/submit?exam_id` | manage | `draft → pending_review` |
| POST | `/topic-prerequisites/{id}/review?exam_id` | review | lifecycle transitions per C.2; reopen requires notes |
| DELETE | `/topic-prerequisites/{id}?exam_id` | manage | blocked while `locked` (reopen first); reason required |

Frontend: the prerequisite editor is added to the Manage Exam Syllabus panel (reusing the J2-A `canManage`/fail-closed pattern and shared `studyos/editors/` module), showing `reviewer_status`, relation, and advisory `strength`. Review transitions surface only to `exam_intelligence.review` holders.

---

## Section G — Planner authority change (LOCKED)

`study_os/planner.py::_load_prerequisites` MUST filter to `reviewer_status = 'locked'`:

```python
supabase.table("topic_prerequisites")
    .select("topic_id, prerequisite_topic_id, relation_type")
    .in_("topic_id", topic_ids)
    .eq("reviewer_status", "locked")
    .limit(5000)
```

Everything else in planner ordering is unchanged (candidate-set limiting, safe fallback, `strength` still ignored per PD-4). The read remains defensive (`_safe`, degrades to no-ordering on failure).

---

## Section H — Acceptance tests

### H.1 Scope (PD-1)
```
[ ] create rejected (422) when either endpoint topic is outside the exam's resolved subjects
[ ] create allowed when both topics ∈ exam subjects
```
### H.2 Cycle integrity (Section E)
```
[ ] direct reverse (B→A when A→B) rejected
[ ] transitive cycle (A→B→C→A) rejected by the recursive check
[ ] concurrent inserts cannot jointly form a cycle (RPC lock/serializable test)
[ ] self-edge rejected (existing check)
```
### H.3 Lifecycle + permission separation (Section C)
```
[ ] manage creates edges as draft; cannot transition beyond submit→pending_review
[ ] review performs pending_review→reviewed→locked and the reject branch
[ ] locked→reviewed reopen requires review_notes
[ ] manage cannot review (403); review cannot create (403); super_admin bypass
[ ] every write has a reason + audit row; create never sets a review state (rule 3)
```
### H.4 Edit/delete under lock (C.3)
```
[ ] manage edit blocked on locked/reviewed/pending_review edge (reopen first)
[ ] delete blocked on locked edge; allowed on draft/rejected with reason
```
### H.5 Planner authority (Section G)
```
[ ] planner consumes only locked edges (draft/pending/reviewed/rejected ignored)
[ ] strength does not affect ordering or scoring (PD-4)
[ ] out-of-candidate-set prerequisite stays informational; plan still generates (PD-5)
[ ] backfill (per PD-D decision) produces the intended planner behavior on existing edges
```

---

## Section I — Files to change (on approval)

| File | Change |
|---|---|
| `app/supabase/migrations/<next>_topic_prerequisite_lifecycle.sql` | Lifecycle columns + index + cycle-safe RPC + backfill (per PD-D) + RLS/grants |
| `app/backend/app/api/admin_exam_intel_manage.py` | manage prerequisite endpoints (create via RPC, edit/submit/delete) |
| `app/backend/app/api/…review…` | `review` transition endpoint (or extend the manage router with review-gated routes) |
| `app/backend/app/study_os/planner.py` | `_load_prerequisites` locked-only filter |
| `app/frontend/.../syllabus-mapper/` + `studyos/editors/` | prerequisite editor UI (manage) + review controls (review) |
| backend + frontend tests | Section H |
| `docs/status/career-copilot-checklist.md` | J2-A′ row |

---

## Appendix A — Code evidence index

- `app/supabase/migrations/029_exam_intelligence_taxonomy.sql:56–99` — `topic_prerequisites` schema, unique key, direct indexes; no lifecycle column.
- `app/supabase/migrations/035_…:64` — authenticated-read RLS.
- `app/backend/app/api/admin_exam_intel_cms.py` (`/topic-prerequisites`) — direct-reverse-only cycle check.
- `app/backend/app/study_os/planner.py:104–105, 294–322, 576–601, 1050` — `_ORDERING_RELATIONS`, `_load_prerequisites` (no status filter, strength unread), candidate-set ordering with safe fallback.

---

*Status: DRAFT — OPERATOR APPROVAL REQUIRED. Open decision: PD-D (backfill of existing edges; PD-D-opt-1 grandfather-to-`locked` recommended). All other decisions reconcile the existing implementation per operator direction. On approval: J2-A′ implementation (migration + endpoints + planner locked-only read + editor UI + tests).*
