# UPSC CSE 2025 CSAT Set-B defect revalidation

Use this runbook after PR #1008 is deployed and migration 264 is applied.

1. Confirm frontend and backend deployment SHAs and the live migration maximum.
2. Confirm the CSAT Set-B card displays reviewed paper identity and `Set B` without exposing raw metadata.
3. Search `UPSC` in Exam Intelligence and confirm `upsc-cse` appears.
4. Start or resume an 80-question Set-B attempt and confirm every palette item is discoverable; active navigation must scroll the item into view.
5. Select an MCQ answer, use **Clear response**, refresh, and confirm it remains unattempted.
6. Confirm verified `pyq_papers` and `pyq_sources` no longer retain `metadata.provenance_pending` after migration 264.
7. Re-run the exact paper launch, submit, result, review, and anon/learner/admin projection RLS checks from the 2026-07-14 audit.
8. Record each defect ID (`csat-setb-01` through `csat-setb-05`) as revalidated or still open in one immutable evidence record.

Do not mark the gate passed from unit tests or migration inspection alone.
