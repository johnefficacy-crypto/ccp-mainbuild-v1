---
owner: ops
status: live
last_verified_against_code: 2026-05-16
source_of_truth: code
related_code:
  - app/backend
related_migrations:
  - app/supabase/migrations
review_cadence: per-sprint
---

# Decision Log

- 2026-05-16: Adopt docs reorg plan; split strategy vs runbook docs; align ADRs 0005-0007.
- 2026-06-12 (Track 3 — Verification Reviewer Console):
  - D1: Guided-form subset = `cycle_date_update` + `phase_date_update` only;
    `policy_update_create/edit` stay on existing JSON textarea path.
  - D2: Guided date inputs generate POST patch internally (changed fields only);
    no raw JSON exposed for cycle/phase actions.
  - D3: Inline provenance block sourced from existing report-detail payload
    (`evidence_summary`, `resolver_status`, `resolver_confidence`); no new
    endpoint.
  - D4: `ApplyRegistryActionPanel` client gate mirrors endpoint permission
    (`exam_intelligence.cms` OR `super_admin`); route guard unchanged.
  - D5: Single report → single action per submit; no bulk apply path in UI.
  - Date validation runs on the MERGED target row (`{...selectedRow,
    ...changedFields}`); equal `start == end` is valid; comparison normalizes
    date-only vs timestamptz to YYYY-MM-DD before comparing.
  - `scrape_queue` not consulted for `exam_id` derivation — queue-stage data is
    unverified; only post-promotion `recruitments.exam_id` is a trusted scope key.
  - Parked: status guided-editing (enum drift hazard), `event_source_id` UI,
    backend apply write-path transactionality, non-admin-reviewer page-route.
- 2026-06-12 (Track 2 — Calendar/Phase Authoring UI — DEFERRED):
  - Operator preflight confirmed zero backlog: no `exam_phases` row carries
    legacy `metadata.phase_window` without `phase_start`. Track 2 reduces to
    preventive validation only; deferred in favor of Track 3.
  - Decisions locked for if/when un-deferred: see
    `docs/status/implementation-status.md § Track 2` for D1–D8.
