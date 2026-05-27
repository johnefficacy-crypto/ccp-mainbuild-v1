## Summary
- What changed at a high level?
- Why this PR exists now?

## Problem / Gap Addressed
- What was broken, risky, inconsistent, or missing before this PR?
- Which user/admin flow was impacted?

## Implemented in This PR
- [ ] Item 1
- [ ] Item 2
- [ ] Item 3

## Remaining Work / Intentionally Deferred
- What is explicitly *not* covered in this PR?
- Why is it deferred (scope/risk/dependency)?

## Files Changed
| File | Reason |
|---|---|
| `path/to/file` | Why it changed |

## API Contracts Touched
- Endpoints added/changed/removed (if none, state **None**).
- Request/response payload impacts (if none, state **None**).

## UI States Covered
- Loading state: ✅ / ❌ (where?)
- Empty state: ✅ / ❌ (where?)
- Error state: ✅ / ❌ (where?)
- Success feedback state: ✅ / ❌ (where?)

## Accessibility Checklist
- [ ] All icon-only controls have `aria-label`
- [ ] Form controls have visible labels and proper `id/htmlFor`
- [ ] Status is not conveyed by color alone
- [ ] Keyboard interaction tested for changed controls
- [ ] Screen reader friendly loading/error text (`role="status"`, `aria-live`, etc.)

## E2E Impact
- [ ] I checked whether this change affects the critical E2E flows in `app/frontend/e2e/` (attempt happy path / submit→review / report→attempt drill).
- Flows affected (or **None**):
- `data-testid`s added/changed, or a new flow needed (or **None**):
- [ ] If behaviour covered by E2E changed, the relevant spec(s) and fixtures were updated.

## Click-through verification

For PRs touching user-facing routes, endpoints, or UI:

- [ ] **Author manually clicked through the flow** with browser devtools network tab open
- [ ] **Zero 4xx or 5xx responses** during the flow (or all expected and documented)
- [ ] **Console clean** — no errors, no warnings about missing keys or props
- [ ] **Screenshot or screen recording** attached to PR for the primary flow
- [ ] **Reviewer replicated the click-through** before approving

If this PR does not touch user-facing surface area, write "N/A — backend-only library / docs / tooling" and skip. For backend-only / docs / tooling / migration PRs, also apply the `click-through-na` label. See `docs/process/click_through_review.md`.

### Flow walked

Describe the exact sequence (1-2 sentences):
> e.g. "Login as test user → /admin/mocks/questions → click 'New Question' → fill form → save → verify draft appears in QuestionList → open and verify edit works → request review → switch user → approve → publish."

### Network requests observed

Paste relevant requests from devtools (status codes, paths):
> POST /api/admin/mocks/questions → 201
> GET /api/admin/mocks/questions/{id} → 200
> POST /api/admin/mocks/questions/{id}/dedup-check → 200

### Known issues found and filed (not fixed in this PR)

> - Issue #N: empty state on QuestionList when no questions exist

## Manual Test Checklist
- [ ] Scenario 1:
- [ ] Scenario 2:
- [ ] Scenario 3:

## Commands Run
```bash
# Paste exact commands and outcome markers
# ✅ command-that-passed
# ⚠️ command-with-environment-limitation
# ❌ command-that-failed-due-to-code
```

## Screenshots / Screen Recordings
- UI before/after evidence (attach here)
- `N/A` if no visible UI change
