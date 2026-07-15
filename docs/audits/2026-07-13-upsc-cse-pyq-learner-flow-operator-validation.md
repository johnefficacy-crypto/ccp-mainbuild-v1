# Operator validation — UPSC CSE PYQ learner flow (2026-07-13)

**Track:** EI-DATA-01 (UPSC PYQ topic tags) + PR-5/6 learner PYQ practice
**Frontend:** `ccp-web-demo.vercel.app` · **Backend:** `ccp-api-demo.onrender.com`
**Fix under test:** PR #980 (`e98fbb4` — use canonical `exam_phases.phase_name`, merged to `main` via `6dde85b`)

## Disposition

```
API AND CORE LEARNER FLOW VALIDATED
FULL-PAPER PRACTICE FUNCTIONAL
FOLLOW-UP UI DEFECTS OPEN
```

- **Functional validation: PASS**
- **UI quality validation: PASS WITH FOLLOW-UP DEFECTS**

> **Exact-paper follow-up (2026-07-14).** A separate production run validated the exact UPSC CSE 2025 Prelims GS Paper-II CSAT **Set-B** paper, all 80 frozen questions, learner ownership, persistence, submission/result/review, and anon/learner/admin projection-table RLS. That run also refined the UX disposition: the CSAT paper-practice launch was intentionally untimed, so `time_remaining_sec=null` / no countdown is not a defect for that flow; exact Set-B card identity, `UPSC` catalogue search, large-paper palette discoverability, MCQ clear-response, and stale provenance metadata remain open. See `docs/audits/2026-07-14-upsc-cse-2025-csat-set-b-learner-access-validation.md`.

## Original production finding (resolved)

`GET /api/exam-intelligence/exams/upsc-cse/pyq-summary` and `.../pyqs` returned HTTP 200
with empty data and an embedded PostgreSQL error `42703: column exam_phases.name does not
exist`. The learner endpoints selected `exam_phases.name`; the canonical column is
`exam_phases.phase_name`. The backend failed closed, so the learner UI showed zero papers
and zero questions despite valid verified data. PR #980 corrected both endpoint queries and
response mappings and updated the regression fixture, and was deployed. This
documentation-only PR records the deployed correction and the post-deploy operator evidence;
it does not modify runtime code or tests.

## Post-deploy API evidence

`pyq-summary`:
```json
{ "totals": { "papers": 4, "questions": 177, "projected_practice_ready": 177 }, "error": null }
```
`pyqs`:
```json
{ "total": 177, "returned_items": 20, "error": null }
```
First item carried correct paper metadata, `phase_name: "Prelims"`, subject + primary-topic
metadata, four options and the correct option id.

## Data state confirmed (aggregate learner-API scope)

- 4 verified papers; 177 verified questions, each with exactly one verified primary tag.
- 177 active, practice-ready projections (2 stale projections refreshed before validation).
- Reconciles: General Studies 97 + CSAT 80 = 177.

> **Scope caveat — this does NOT close the EI-DATA-01 data gate.** The counts above are the
> aggregate learner-API totals over the whole verified UPSC CSE corpus (177/4). They are a
> different scope from EI-DATA-01's frozen **98**-target / **2**-reject identity set, and this
> validation did **not** capture the runbook's stop-condition evidence pair — the frozen 98-ID
> count + `target_digest`, the Phase 0.3 pre / Phase 2.3 post projection-preview reason
> distributions, and proof the 2 rejects stayed unchanged (`docs/runbooks/
> EI-DATA-01_upsc_2026_primary_topic_tags.md` § Closeout). EI-DATA-01 therefore remains
> `OPERATOR / DATA PENDING`; this record validates the learner read path, not the data gate.

## Learner flow confirmed

PYQ Explorer showed 4 papers / 177 questions / 177 practice-ready with year/phase/subject/
difficulty distributions and enabled **Practice paper** buttons. The 97-question General
Studies paper launched; questions rendered with four labelled options; answers persisted;
submission completed without a failed-save/API error; result analytics (Overview/Topic/Time/
Error) and review (all 97 questions) loaded. Time tab reported total 18m 59s, avg 12s/q.

## Open UI defects (frontend follow-up)

| # | Defect | Priority | Direction |
|---|---|---|---|
| 1 | Attempt-header timer shows `--` during the 2026-07-13 attempt while per-question dwell tracking works | Historical finding — contract clarification required | Distinguish timed from untimed attempts. Timed attempts must render a countdown; untimed PYQ practice must render explicit `Untimed` rather than an ambiguous placeholder. The 2026-07-14 exact Set-B launch was untimed and correctly returned `time_remaining_sec=null`. |
| 2 | Navigator clips questions 96–97 behind the fixed action footer; palette does not auto-scroll to / re-highlight the active question under keyboard nav | High | Own scroll container + footer-height reserve; `scrollIntoView({block:'nearest'})` on index change; derive active state from canonical current question id/index; test keyboard/mouse/direct-palette nav on a >95-question paper |
| 3 | Review options concatenated (`A. …B. …C. …D. …`) with no separation | Medium–High | Render each option as a separate block/list item; reuse the shared option-label formatter; test each option renders in its own element |

The exact Set-B follow-up additionally found: the learner paper card does not expose Set-B identity; catalogue search for `UPSC` misses the exam; the 80-question palette is not sufficiently discoverable without keyboard navigation; and an MCQ answer cannot be cleared back to unattempted even though the API accepts `selected_option_id:null`.

## Recommended automated coverage

Extend the projected-PYQ e2e (`app/frontend/e2e/flows/pyq-practice-review.spec.ts`) with a
≥97-question paper asserting: valid timer or explicit untimed state; keyboard navigation to
Q97 with the palette item visible + active; all 97 navigator items present in review; options
render as separate readable elements. Add exact-paper coverage that identifies `CSAT · Set-B`,
finds UPSC through catalogue search, and clears a selected MCQ response before submit.

## Not blockers

The remaining findings are frontend usability/identification defects, not data-integrity,
projection-readiness, answer-persistence, scoring, result-generation, or RLS failures. The
original learner-data production blocker is resolved and validated. An “exact Set-B is
identifiable and discoverable in the learner UI” release claim remains blocked until the
follow-up defects in the 2026-07-14 audit are corrected.