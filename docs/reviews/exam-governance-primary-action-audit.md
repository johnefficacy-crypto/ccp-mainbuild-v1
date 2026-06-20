# Exam Governance primary-action hierarchy audit

Date: 2026-06-20

Scope: B3d-close / CL-5 cross-surface audit. Runtime code was inspected read-only; this document records evidence only.

## Decision

**Pass.** All six audited surfaces satisfy the CL-5 one-primary-per-screen rule in this checkout, so CL-5 can move from `CLEANUP PENDING` to `CODE PRESENT IN THIS CHECKOUT`.

Rule applied: a screen may expose at most one screen-level primary CTA; pressed filters/selectors are not primary actions; repeated row actions are contextual; local form submission buttons are scoped to their form/card and are not automatically competing screen-level CTAs.

`SetupPanel` local transaction buttons are deferred to Lane C and are not screen-level navigation hierarchy for this B3d-close audit.

## Surface findings

### 1. Exam Registry — pass

- **Classification:** `Open console` is the sole **screen-level primary CTA** in the `PageHeader` right slot.
- **Evidence:** The header `right` slot renders `Open console` with `className="btn btn-primary text-xs"`, while `Create exam` is `btn btn-ghost` and `Advanced import / repair` is `btn btn-ghost ... text-amber-700 ...` rather than primary. `StatusDot` is status display, not an action. Evidence: `app/frontend/src/pages/admin/ExamIntelligence.jsx:143-168`.
- **Required result:** Registry has `Open console` as the sole screen-level primary. **Satisfied.**

### 2. Console Work Queue — pass

- **Classification:** The work queue has **no screen-level primary CTA**; workflow controls are **pressed selector/filter** controls; table links are **repeated row action** controls; pagination/empty-state controls are utility controls.
- **Evidence:** The summary strip is a filter group (`role="group"`, `aria-label="Work-queue summary filters"`) whose chips render as `className="btn ghost filter-chip"` with `aria-pressed={active}`. Evidence: `app/frontend/src/features/admin/exam-intelligence/ConsoleWorkQueue.jsx:215-247`.
- **Evidence:** The uncounted workflow buttons also render as `className="btn ghost filter-chip"` with `aria-pressed={active}`. Evidence: `app/frontend/src/features/admin/exam-intelligence/ConsoleWorkQueue.jsx:296-317`.
- **Evidence:** Per-row `Open console` and `Advanced workspace` links are repeated under the table `Actions` column, with `Open console` using `className="btn"` and `Advanced workspace` using `className="btn ghost"`. Evidence: `app/frontend/src/features/admin/exam-intelligence/ConsoleWorkQueue.jsx:347-420`.
- **Required result:** Work Queue has no screen-level primary; filters use pressed styling; row actions are contextual. **Satisfied.**

### 3. Per-exam ExamActionConsole — pass

- **Classification:** Header navigation links are **tertiary/advanced navigation** / secondary navigation, and queue CTAs are **contextual action-queue item** controls.
- **Evidence:** The header action area renders `Back to work queue` and `Advanced workspace` as `className="btn btn-ghost"`, so neither is a screen-level primary. Evidence: `app/frontend/src/features/admin/exam-intelligence/ExamActionConsole.jsx:164-181`.
- **Evidence:** Action queue CTAs render inside each queue item (`actions.map`) using backend-provided `cta_route` and `cta_label`, so they are item-scoped contextual actions rather than screen-level primaries. Evidence: `app/frontend/src/features/admin/exam-intelligence/ExamActionConsole.jsx:195-226`.
- **Required result:** Action Console header navigation is secondary; queue actions are contextual. **Satisfied.**

### 4. Guided Exam Wizard — pass

- **Classification:** The wizard exposes one **screen-level primary CTA** per active step; organization mode controls are **pressed selector/filter** controls; the final creation button is a **local form submission** scoped to the wizard review step.
- **Evidence:** Organization mode controls use `aria-pressed` selector semantics, while the step's only primary forward action is `Next: Exam →` with `className="btn btn-primary"`. Evidence: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:216-237` and `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:320-325`.
- **Evidence:** Step 2 has one primary forward action, `Next: Cycle →`, and the back action is plain `btn`. Evidence: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:399-401`.
- **Evidence:** Step 3 has one primary forward action, `Next: Phases →`, and the back action is plain `btn`. Evidence: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:423-427`.
- **Evidence:** Step 4 has one primary forward action, `Review & Create →`, and the back action is plain `btn`. Evidence: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:498-502`.
- **Evidence:** Step 5 has one primary creation action, `Create all` / `Resume creation`, and the back action is plain `btn`; post-success links/buttons are follow-up scoped actions after completion. Evidence: `app/frontend/src/pages/admin/studyos/GuidedExamWizard.jsx:852-858`.
- **Required result:** Guided Wizard has one forward/create primary per step. **Satisfied.**

### 5. Exam Workspace Smart Header — pass

- **Classification:** `Go to next action →` is the sole **screen-level primary CTA** in the Smart Header; cycle selection is a selector, not a CTA.
- **Location method:** Located read-only by searching for `next action`, `SmartHeader`, and workspace shell terms; the file is `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx`.
- **Evidence:** The Smart Header renders the cycle picker as a `<select>` and the readiness strip labels `Next action`; the only primary button in the strip is `Go to next action →` with `className="btn primary"`. Evidence: `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:57-95` and `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx:131-202`.
- **Required result:** Workspace has `Go to next action` as the sole screen-level primary. **Satisfied.**

### 6. Advanced Import / Repair header — pass

- **Classification:** The header has no competing guided-create CTA; the visible controls are **tertiary/advanced navigation**/repair-surface utilities and local create/import controls.
- **Evidence:** The Advanced Import / Repair header text recommends the normal `Exam Governance Console` and `Create-exam wizard` outside this power-user page, but renders no guided-create CTA in the header. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:994-1018`.
- **Evidence:** The first controls after the header are the entity selector plus local `Reload` and `New row` buttons for this repair surface; no `+ New guided exam` or other guided-create CTA appears there. Evidence: `app/frontend/src/pages/admin/studyos/ExamIntelCms.jsx:1020-1045`.
- **Required result:** Advanced Import / Repair has no competing guided-create CTA. **Satisfied.**

## CL-6b note

CL-6b was intentionally not audited for closure here and remains `CLEANUP PENDING` byte-for-byte in the checklist.
