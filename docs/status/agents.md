---
owner: ops
last_modified: 2026-06-20
verified_against: main @ a2ded8c
---

# Agent dispatch table

Maps all open work items to suggested agent types, write scopes, and blocking
relationships. Cross-reference with `career-copilot-pr-plan.md` for full PR
specs and `career-copilot-checklist.md` for current status.

Status vocabulary matches the checklist: PLANNED, CLEANUP PENDING, BLOCKED,
OPERATOR PENDING, DESIGN QUESTION.

---

## Lane A — Mock Engine validation gate

| Work item | Agent type | Status | Blocks |
|---|---|---|---|
| A1 Scheduler evidence | Operator (live, docs-only) | OPERATOR PENDING | Unblocks A2 |
| A2 Repeat off/shadow validation | Operator (live, docs-only) | GATE FAILED — BLOCKED ON ALLOWLIST | Unblocks FF=live |
| A3 Live canary plan execution | Operator (live, docs-only) | BLOCKED | Needs A1+A2 clean + allowlist PR |
| Allowlist implementation PR | Backend agent | PLANNED | Hard prerequisite for A2/A3 |
| Migration 182 dry-run/apply | Operator (DB) | OPERATOR PENDING | Part of allowlist gate |
| `_apply_error_patterns` schema mismatch | Backend agent | PLANNED | Blocks A2 |

Do not dispatch A2/A3 until A1 passes and the allowlist implementation PR merges.

---

## Lane B — Exam Governance Console cleanup

| Work item | Agent type | Status | Depends on |
|---|---|---|---|
| B1 De-leak ExamActionConsole labels | Frontend agent | CODE PRESENT | — |
| B2 Remove orphaned console variant + ExamTaskRail | Frontend agent | CODE PRESENT | B1 (test coordination) |
| B3a Registry row expansion | Frontend agent | CODE PRESENT | — |
| B3b Remove CMS `+ New guided exam` CTA | Frontend agent | CODE PRESENT | — |
| B3c Collapsible lifecycle banner | Frontend agent | CODE PRESENT | — |
| B3d-2 ConsoleWorkQueue action hierarchy | Frontend agent | CODE PRESENT | — |
| B3d-3 GuidedExamWizard primary hierarchy | Frontend agent | CODE PRESENT | — |
| B3d-close CL-5 final cross-surface audit | Frontend audit agent (docs-only) | CLEANUP PENDING | B3d-2 + B3d-3 merged |
| B4/CL-6b Dormant console plumbing removal | Frontend agent | CODE PRESENT | — |

---

## Lane C — Exam workspace setup/timeline UX

| Work item | Agent type | Status | Depends on |
|---|---|---|---|
| C0 Design lock / component ownership preflight | Frontend architect (docs-only) | CLEANUP PENDING | — |
| C1 Phase timeline table extraction | Frontend agent | CLEANUP PENDING | C0 |
| C2 Merge template phases into timeline | Frontend agent | CLEANUP PENDING | C1 |
| C3 Fast date-entry mode | Frontend agent | CLEANUP PENDING | C1 or C2 |
| C4 Setup mutation governance | Frontend agent | CLEANUP PENDING | C1 (or parallel if scope split) |

---

## Lane D — Document readiness identity/status audit

| Work item | Agent type | Status | Depends on |
|---|---|---|---|
| D1 Read-only contract audit | Backend+frontend auditor (docs-only) | NEEDS TARGETED RECHECK | — |
| D2 Narrow fix (if D1 finds bug) | Backend or frontend agent | PLANNED | D1 |

**Note:** BUG-EI-2 (`console_detail::_documents()` querying wrong table) is now
confirmed as the specific D-lane bug. D2 = H2 in Lane H. If H2 is dispatched,
D1 can be marked complete.

---

## Lane E — Backend CI audit sequencing

| Work item | Agent type | Status | Depends on |
|---|---|---|---|
| E1 CI sequencing PR | CI/infra agent | STILL OPEN | — |

Write scope: `.github/workflows/ci.yml` only. `pip-audit` must not gate `pytest`.

---

## Lane F — Live-DB-only tails

| Work item | Agent type | Status | Depends on |
|---|---|---|---|
| F1 Verify/delete `e2e-workspace-exam` prod row | Operator (DB) | VERIFY DB | — |
| F2 Verify state PSC URL backfill | Operator (DB) | VERIFY DB | — |
| F3 Reconfirm SEBI Grade A | Operator (DB) | VERIFY DB | — |

These produce evidence docs only. No runtime code changes unless a real defect is found.

---

## Lane G — Later expansion (blocked)

Do not dispatch until Lane A exits clean.

| Work item | Agent type | Status |
|---|---|---|
| A-PR4 Exposure cooldown | Backend agent | BLOCKED |
| A-PR5 Mastery-informed mock selection | Backend+frontend agent | BLOCKED |
| Track C question-model v2 | Backend+frontend agent | BLOCKED |
| Wave 5 PYQ weighting | Backend agent | BLOCKED |

---

## Lane H — Exam Intelligence P0 bug fixes (NEW — 2026-06-20)

Source: operator screenshot audit `docs/audits/exam-intelligence-gaps-2026-06-20.md`.
Can run in parallel with Lanes B, C, D, E.

| Work item | Agent type | Status | Depends on |
|---|---|---|---|
| H1 Fix `syllabus/propose` 404 (BUG-EI-1) | Backend agent | PLANNED | Nothing — dispatch now |
| H2 Fix `console/exams/{id}` 500 (BUG-EI-2) | Backend agent | PLANNED — DESIGN GATE | Operator must choose Option A or B (see PR plan H2) |
| H3 EI UX cleanup batch (UX-EI-1/3/5) | Frontend agent | PLANNED | Nothing — dispatch now |
| UX-EI-2 Topics exam-scope filter | Backend + frontend agent | PLANNED | Design decision on filter contract |
| UX-EI-4 Bulk import JSON schema docs | Docs agent | PLANNED | Nothing — dispatch now |
| UX-EI-6 Competition metrics JSONB schema | Operator + backend agent | DESIGN QUESTION | Operator must define cutoff structure |

### H2 design gate — operator must decide before dispatch

Options:
- **Option A (recommended):** `_documents()` queries `syllabus_documents` by `exam_id`; uses `trust_status == "verified"` as readiness proxy. Simple, uses existing schema.
- **Option B:** `_documents()` queries a processing-job status table (e.g. `document_processing_jobs`) to get extraction status per document. More accurate but requires confirming that table structure.

Record the decision in the H2 PR description before any code is written.

---

## Open design questions (no agent can be dispatched without a decision)

| ID | Question | Needed for |
|---|---|---|
| DQ-1 | Exam-family hierarchy UI intent (KG value proposition) | Lane C or new UI lane |
| DQ-2 | Exam active/inactive toggle — operator workflow | H3 or new UX PR |
| DQ-3 | Business definition of core/managed-light/indexed in UI | CMS docs |
| DQ-4 | Cross-exam common-subject management strategy | Backend schema decision |
| DQ-5 | Error pattern taxonomy — time pressure vs. skipped distinction | Lane A / mastery writer |
| DQ-6 | PYQ bilingual/two-column PDF handling | PYQ import pipeline |
| DQ-7 | Historical cycle paper addition workflow | Operator runbook |
| H2-gate | console_detail._documents() redesign: Option A or B | H2 |

---

## Safe next dispatch batch (as of 2026-06-20)

| Priority | Agent | Work | Notes |
|---|---|---|---|
| P0 | Backend agent → H1 | Fix `syllabus/propose` 404 | Dispatch immediately; narrow scope |
| P0 | Backend agent → H2 | Fix console 500 | Requires design decision first |
| P1 | Frontend agent → H3 | EI UX cleanup (IDs, OverviewPanel, phases cycle label) | Can run parallel with H1 |
| P1 | Frontend agent → B1 | ExamActionConsole de-leak | Independent of H-lane |
| P1 | CI/infra agent → E1 | pip-audit / pytest sequencing | Independent of all other lanes |
| P2 | Docs agent → UX-EI-4 | Bulk import schema documentation | Docs-only, no code |
| P2 | Operator → A1 | Scheduler evidence | Operator-only, live env |
