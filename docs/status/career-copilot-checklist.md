---
owner: ops
status: live
last_modified: 2026-06-21
source_of_truth: code
review_cadence: per-sprint
---

# Career Copilot — Exam Intelligence UX Cleanup Checklist

Tracks operator-facing UX cleanup items identified in the H3 audit batch.

## Legend

| Status | Meaning |
|--------|---------|
| `CLEANUP PENDING` | Issue identified, no code change yet |
| `CODE-FIXED, VALIDATION PENDING` | Fix implemented in code, awaiting QA sign-off |
| `VALIDATED` | Fix confirmed in staging/production |

---

## UX-EI-1: Remove raw UUIDs from operator-facing surfaces

| ID | Surface | Location | Status |
|----|---------|----------|--------|
| I1 | ReviewQueueTable — Row id column | `app/frontend/src/features/admin/exam-intelligence/ReviewQueueTable.jsx` | `CODE-FIXED, VALIDATION PENDING` |
| I2 | SetupPanel — phase error message phaseId | `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | `CODE-FIXED, VALIDATION PENDING` |

**Fix:** `humanizeToken(r.id)` via `operatorChrome.js` replaces raw UUIDs with `#<first-8-chars>` prefix. Non-UUID identifiers pass through unchanged.

---

## UX-EI-3: Remove duplicate exam identity fields from OverviewPanel

| ID | Surface | Location | Status |
|----|---------|----------|--------|
| D1 | OverviewPanel — exam name / slug / type / family duplicates SmartHeader | `app/frontend/src/pages/admin/exam-workspace/panels/OverviewPanel.jsx` | `CODE-FIXED, VALIDATION PENDING` |

**Fix:** OverviewPanel created without the identity fields (name, slug, exam_type, family) that `SmartHeader` in `ExamWorkspace.jsx` already renders. Panel retains non-duplicate fields (cadence, management_mode, is_active) and the readiness sections summary.

---

## UX-EI-5: Add cycle context to "Phases needing dates" section

| ID | Surface | Location | Status |
|----|---------|----------|--------|
| D3 | SetupPanel — Phases needing dates — no cycle shown | `app/frontend/src/pages/admin/exam-workspace/panels/SetupPanel.jsx` | `CODE-FIXED, VALIDATION PENDING` |

**Fix:** Each phase row in the worklist now resolves its `exam_cycle_id` against the `cycles` array from context and displays the cycle name + year (e.g. "2026 Cycle (2026)"). Phases with no matching cycle gracefully omit the label.

---

## Validation checklist (manual)

- [ ] Open ReviewQueueTable with real UUID-based rows — confirm no raw UUIDs visible
- [ ] Open OverviewPanel — confirm name/slug/type/family are absent; cadence/management_mode/is_active present
- [ ] Open OverviewPanel — confirm readiness sections summary renders
- [ ] Open SetupPanel with multi-cycle exam having undated phases — confirm each row shows its cycle name + year
- [ ] Open SetupPanel with phase having unknown cycle_id — confirm no crash, no spurious cycle label
