# Topic Prerequisite Semantics and Planner Authority Gate — J2-A′

- Document type: J2-A′ implementation contract — topic prerequisite semantics, trust lifecycle, and planner authority
- Status: **OPERATOR APPROVED (2026-07-01); IMPLEMENTED + MERGED (PR #835 `3e3d930`); MIGRATION 208 VERIFY DB — PARTIAL PASS (2026-07-02).** Gate merged via PR #830, confirmed approved by the operator. PD-D-opt-1 approved. Audit-atomicity acceptance amended — see §C.2a. Live-DB proofs completed for concurrent cycle prevention + lifecycle-state CAS + grandfather locked-state + reversible reopen + RLS/RPC hardening — see `docs/audits/2026-07-02-migration-208-operator-validation.md`. **Not yet independently captured:** PD-D pre-migration count + representative planner pre/post preservation, and the same-state `updated_at` lost-update race (unit-covered; DB isolation pending). Manage/review permission grants applied to the operator accounts.
- Date: 2026-07-01
- **PD-D — OPERATOR APPROVED (2026-07-01):** `PD-D-opt-1` — backfill every pre-migration `topic_prerequisites` row to `reviewer_status='locked'` in the same forward migration. Implementation validation must record: pre-migration edge count; post-migration grandfathered `locked` count; zero legacy rows left in another status; planner behavior preserved for a representative existing graph; grandfathered rows require the review reopen path before manage-tier edits/deletes.
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

- `exam_intelligence.manage`: **creates and edits** edges in `draft` or `rejected` state; may perform the **submit handoff** (`draft → pending_review`, `rejected → pending_review`) only. Cannot reject, review, lock, reopen, or `reviewed → draft`.
- `exam_intelligence.review`: performs all lifecycle transitions (`pending_review → reviewed`, `reviewed → locked`, `pending_review → rejected`, `reviewed → rejected`, `reviewed → draft`, `locked → reviewed` reopen-with-notes). Cannot create canonical content.
- `super_admin`: bypass.

### C.2 Transition matrix (LOCKED)

| From \ To | draft | pending_review | reviewed | locked | rejected |
|---|---|---|---|---|---|
| draft | — | **manage (submit)** | — | — | review |
| pending_review | — | — | review | — | review |
| reviewed | **review only** | — | — | review | review |
| locked | — | — | review (reopen; notes required) | — | — |
| rejected | — | **manage (submit)** | — | — | — |

Any transition not in the matrix → 409. Reopen (`locked → reviewed`) requires `review_notes` (mirrors the score-snapshot reopen precedent).

**Permission separation (LOCKED — parent gate rule):** `exam_intelligence.review` is exclusive to trust/lifecycle transitions. Therefore **all** state changes are review-only **except one documented exception:** the **submit handoff** `draft → pending_review` and `rejected → pending_review`, which `manage` may perform to hand its own work to review. `manage` can NEVER perform reject, review, lock, reopen, or `reviewed → draft`. In particular `reviewed → draft` is **review-only** (an earlier draft allowed manage — corrected).

**Rejected correction path (LOCKED — no lifecycle rewrite by manage):** a `rejected` edge is corrected by **editing in place while `rejected`** (manage, per C.3) and then the explicit **`rejected → pending_review` submit handoff** (manage). Manage does not move `rejected → draft`; there is no manage path that erases a review-assigned state.

**Reopen-to-edit path (LOCKED — closes the C.2 dead-end, permission-correct):** correcting a locked edge is `locked → reviewed` (review, notes) → `reviewed → draft` (**review only**) → edit as `draft` (manage) → `draft → pending_review` submit (manage) → re-review → re-lock.

### C.3 Editing/deletion under lock (LOCKED — J2-A gate rules 4/5)

- `manage` may **edit** an edge only while `draft`/`rejected`. A `pending_review`/`reviewed`/`locked` edge must be rolled back by `review` first.
- `manage` may **delete** an edge only while `draft`/`rejected`. `pending_review`, `reviewed`, and `locked` all require review-authority rollback (to `draft`/`rejected`) before a manage delete. Forced exceptional cleanup at any state remains Advanced Repair / `exam_intelligence.cms`, audited.

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

**PD-D — OPERATOR APPROVED: `PD-D-opt-1`** (backfill of existing rows). The planner switches to reading **only `locked`** edges (Section G); existing edges predate the lifecycle and were effectively live.
- **PD-D-opt-1 (APPROVED):** backfill existing rows to `locked` in the same forward migration — grandfathers already-live curated edges so planner output does not silently change on deploy. **Consequence:** grandfathered `locked` edges immediately fall under C.3 — `manage` can no longer edit or delete them without a `review` reopen (intended trust posture). **Implementation validation MUST record:** pre-migration existing-edge count; post-migration grandfathered `locked` count; zero legacy rows left in another status; planner behavior preserved for a representative existing graph; grandfathered rows require the review reopen path before manage edits/deletes.
- ~~PD-D-opt-2: backfill to `draft`~~ — rejected (would regress planner ordering until a re-review sweep completes).

RLS/grants updated per migration discipline; verify with `pg_policies` before marking complete.

---

## Section E — Recursive cycle-validation contract (LOCKED)

- Cycle detection must reject **all transitive cycles** (`A→B→…→A`), not just the direct reverse edge.
- **Single global lock (LOCKED — blocker 4).** A pair-scoped lock is insufficient: three concurrent writes `A→B`, `B→C`, `C→A` use different pair keys, each observe no path, and jointly commit a cycle. Every ordering-edge write MUST take **one shared, transaction-scoped advisory lock** (a single constant lock key for the whole `topic_prerequisites` ordering graph, e.g. `pg_advisory_xact_lock(<constant>)`) before running the recursive check, so all ordering writes serialize against each other. (An alternative algorithm is acceptable only with an equivalent concurrency proof.)
- The check runs inside a **`SECURITY DEFINER` RPC** (e.g. `cms_write_topic_prerequisite`) that, in one transaction: takes the global lock, runs a **recursive CTE** reachability test from `prerequisite_topic_id` back to `topic_id`, and writes only if no path exists. Reuse the lock-then-check pattern landing in the score-snapshot RPC (PR #828) for consistency.
- **Single write path for ALL writers (LOCKED — blocker 1).** Every application writer to `topic_prerequisites` — the Manage Exam `manage` endpoints **AND Advanced Repair (`admin_exam_intel_cms.py`, `exam_intelligence.cms`)** — MUST go through this same cycle-safe RPC. Advanced Repair keeps its own permission and exceptional-cleanup authority, but it must NOT bypass graph acyclicity and must NOT unrestrictedly promote lifecycle state via direct table insert. Equivalent-strength alternative: enforce acyclicity as a **database-level trigger/constraint** that any direct insert (including CMS) cannot bypass. The current CMS direct insert + direct-reverse-only check is removed/replaced.
- The unique `(topic_id, prerequisite_topic_id)` constraint and `topic_id <> prerequisite_topic_id` check remain.
- Cycle detection considers only ordering relations (`requires`, `recommended_before`) — `supports`/`foundation_for` do not form ordering cycles (PD-3). **A PATCH that changes endpoints OR promotes `relation_type` into the ordering set MUST run the same locked recursive check** (a non-ordering edge is never cycle-checked, so promotion is a create-equivalent for cycle purposes) — and takes the same single global lock.

---

## Section F — Endpoint shapes (LOCKED)

Under the J2 `manage` router (`/admin/exam-intelligence-manage`), all mutations single-token `require_permission("exam_intelligence.manage")`; reviews single-token `require_permission("exam_intelligence.review")`; reason + audit on every write; PD-1 scope enforced on both endpoints of an edge.

**§C.2a Audit atomicity (AMENDED 2026-07-01, operator-approved).** Every write emits an `admin_audit_logs` row via the shared `_audit()` helper, which is **best-effort** (logged-not-fatal on failure) — consistent with the entire CMS/admin surface, which uses the same helper. The gate does NOT require prerequisite writes to be transactionally atomic with their audit insert; making prerequisites uniquely transactional while the rest of the CMS is best-effort was rejected as disproportionate and inconsistent. Acceptance is "an audit row is emitted on every write path," not "the write is impossible without a committed audit row."

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/topic-prerequisites?exam_id&topic_id` | **read: existing admin/read access (manage OR review)** | list edges for a topic (both directions), with `reviewer_status`. Read-only under the parent gate's "View Manage Exam and operational data" access so a **review-only** operator can load the rows they must review (blocker 2). |
| POST | `/topic-prerequisites?exam_id` | manage | create `draft` via the cycle-safe RPC (Section E); both topics ∈ exam subjects (PD-1); never sets a review state |
| PATCH | `/topic-prerequisites/{id}?exam_id` | manage | edit only while `draft`/`rejected`; relation/strength/source_basis; **re-run the cycle check whenever endpoints change OR `relation_type` transitions into the ordering set** (`requires`/`recommended_before`) — a `supports`/`foundation_for` → `requires` promotion can close an ordering cycle that was never checked |
| POST | `/topic-prerequisites/{id}/submit?exam_id` | manage | submit handoff: `draft → pending_review` and `rejected → pending_review` (the sole manage lifecycle exception) |
| POST | `/topic-prerequisites/{id}/review?exam_id` | review | lifecycle transitions per C.2 (incl. `reviewed → draft`, reopen); reopen requires notes |
| DELETE | `/topic-prerequisites/{id}?exam_id` | manage | allowed only while `draft`/`rejected`; `pending_review`/`reviewed`/`locked` require review rollback first (C.3); reason required |

Frontend: the prerequisite editor is added to the Manage Exam Syllabus panel; the panel section mounts for **`canManage || canReview`**. Mutation controls (create/edit/delete/submit) render only for `canManage`; review-transition controls render only for `canReview`; a review-only operator sees the list + review controls but no manage mutations. Reuses the J2-A `canManage`/fail-closed pattern and the shared `studyos/editors/` module; shows `reviewer_status`, relation, and advisory `strength`.

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
[ ] concurrent inserts cannot jointly form a cycle (RPC lock test)
[ ] THREE concurrent writes A→B, B→C, C→A cannot jointly commit a cycle (single global lock serializes them; exactly one path-closing write is rejected)
[ ] self-edge rejected (existing check)
[ ] PATCH promoting relation_type supports→requires that would close a cycle is rejected
[ ] Advanced Repair (cms) create/promote goes through the same cycle-safe path — a cms write that would close a cycle is rejected (parity test)
```
### H.3 Lifecycle + permission separation (Section C)
```
[ ] manage creates edges as draft; cannot transition beyond submit→pending_review
[ ] review performs pending_review→reviewed→locked and the reject branch
[ ] locked→reviewed reopen requires review_notes
[ ] reopen-to-edit path works: locked→reviewed→draft makes the edge manage-editable again (no dead-end)
[ ] manage cannot review (403); review cannot create (403); super_admin bypass
[ ] manage CANNOT perform reject / review / lock / reopen / reviewed→draft (403 or 409)
[ ] manage submit handoff works for draft→pending_review AND rejected→pending_review
[ ] review-only operator can GET/list edges (read gate allows manage OR review)
[ ] every write has a reason + audit row; create never sets a review state (rule 3)
```
### H.4 Edit/delete under lock (C.3)
```
[ ] manage edit blocked on locked/reviewed/pending_review edge (rollback first)
[ ] manage delete allowed ONLY on draft/rejected; blocked on pending_review/reviewed/locked (review rollback first)
[ ] cms forced cleanup remains available and audited at any state
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
| `app/supabase/migrations/<next>_topic_prerequisite_lifecycle.sql` | Lifecycle columns + index + cycle-safe RPC + backfill (per PD-D) + RLS/grants. **Migration number:** pick the next free slot at implementation time (`206` is contended by PRs #828 and #823 → use ≥ `207`); do not hardcode from a stale branch. **RPC:** reuse the lock-then-check `SECURITY DEFINER` pattern landing in the score-snapshot RPC (PR #828) for consistent race-safety. |
| `app/backend/app/api/admin_exam_intel_manage.py` | manage prerequisite endpoints (create/edit/submit/delete via the cycle-safe RPC); GET readable by manage OR review; review-transition endpoint (review-gated, incl. reviewed→draft + reopen) |
| `app/backend/app/api/admin_exam_intel_cms.py` | **route the existing Advanced Repair `/topic-prerequisites` writes through the same cycle-safe RPC** (remove the direct insert + direct-reverse-only check) so cms cannot bypass acyclicity (blocker 1) |
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

*Status: OPERATOR APPROVED (2026-07-01) — gate merged (#830) and confirmed approved; PD-D-opt-1 approved; audit-atomicity amended to best-effort (§C.2a). Implementation in PR #835: migration 208 (lifecycle + backfill + cycle-safe RPC w/ single global advisory lock + CAS lifecycle & lost-update guards + RLS trust-boundary tightening), manage/review endpoints, Advanced-Repair reroute, planner locked-only read, editor UI. VERIFY DB — **PARTIAL PASS (2026-07-02)**: concurrent cycle prevention + lifecycle-state CAS + grandfather locked-state + reversible reopen + RLS/RPC hardening proven against live Supabase Postgres; PD-D pre/post planner-preservation and the same-state `updated_at` race not independently captured (unit-covered). Script `app/supabase/validation/validate_topic_prerequisite_concurrency.sql`; evidence `docs/audits/2026-07-02-migration-208-operator-validation.md`. #4 folded in: scoped searchable `GET /exams/{id}/candidate-topics` across all exam subjects, editor fetches candidates independently (search + paginate), single DB-filtered counted/ranged both-direction edge query, edge-list Prev/Next. Manage relations restricted to the ordering set (PD-3).*
