---
owner: ops
status: live
last_verified_against_code: 2026-06-17
source_of_truth: code
related_code:
  - app/backend
  - app/frontend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# Docs Inventory

This inventory is a routing map, not a second implementation tracker. For
current gaps, use [`known-gaps.md`](known-gaps.md); for domain rules, use the
architecture docs.

| Path | Status | Action |
|---|---|---|
| `docs/architecture/` | live | Source of truth for cross-cutting architecture and domain invariants. |
| `docs/engineering/` | mixed | Keep active specs/runbooks; leave superseded shims only when links still point there. |
| `docs/operations/` | live | Operator runbooks and setup procedures. |
| `docs/product/` | strategy | Product direction; verify against code before using as implementation truth. |
| `docs/status/known-gaps.md` | live | Current code-verified gap list. |
| `docs/status/implementation-status.md` | removed | Removed because implemented-surface tracking had become stale and duplicated code truth. |
| `docs/audits/` | historical/live-by-date | Point-in-time reviews; do not treat older findings as open without re-verifying against code. |
| `docs/archive/` | archived | Historical implementation plans retained for context only. |
