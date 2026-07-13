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

## Original production finding (resolved)

`GET /api/exam-intelligence/exams/upsc-cse/pyq-summary` and `.../pyqs` returned HTTP 200
with empty data and an embedded PostgreSQL error `42703: column exam_phases.name does not
exist`. The learner endpoints selected `exam_phases.name`; the canonical column is
`exam_phases.phase_name`. The backend failed closed, so the learner UI showed zero papers
and zero questions despite valid verified data. PR #980 corrected both endpoint queries and
response mappings and updated the regression fixture. This branch corrects the same column
reference in the query/fixture carried on the docs branch.

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

## Data state confirmed

- 4 verified papers; 177 verified questions, each with exactly one verified primary tag.
- 177 active, practice-ready projections (2 stale projections refreshed before validation).
- Reconciles: General Studies 97 + CSAT 80 = 177.

## Learner flow confirmed

PYQ Explorer showed 4 papers / 177 questions / 177 practice-ready with year/phase/subject/
difficulty distributions and enabled **Practice paper** buttons. The 97-question General
Studies paper launched; questions rendered with four labelled options; answers persisted;
submission completed without a failed-save/API error; result analytics (Overview/Topic/Time/
Error) and review (all 97 questions) loaded. Time tab reported total 18m 59s, avg 12s/q.

## Open UI defects (frontend follow-up)

| # | Defect | Priority | Direction |
|---|---|---|---|
| 1 | Attempt-header timer shows `--` during a valid attempt (per-question dwell tracking works — Time tab is correct) | High | Bind timer to launch-payload duration; init after attempt load; render explicit `Untimed` fallback; never `--` on a valid timed attempt; regression asserting a valid time value after load |
| 2 | Navigator clips questions 96–97 behind the fixed action footer; palette does not auto-scroll to / re-highlight the active question under keyboard nav | High | Own scroll container + footer-height reserve; `scrollIntoView({block:'nearest'})` on index change; derive active state from canonical current question id/index; test keyboard/mouse/direct-palette nav on a >95-question paper |
| 3 | Review options concatenated (`A. …B. …C. …D. …`) with no separation | Medium–High | Render each option as a separate block/list item; reuse the shared option-label formatter; test each option renders in its own element |

## Recommended automated coverage

Extend the projected-PYQ e2e (`app/frontend/e2e/flows/pyq-practice-review.spec.ts`) with a
≥97-question paper asserting: valid timer or explicit untimed state; keyboard navigation to
Q97 with the palette item visible + active; all 97 navigator items present in review; options
render as separate readable elements. Guards specifically against sticky header/footer/
navigator viewport clipping.

## Not blockers

The remaining findings are frontend usability defects, not data-integrity, projection-
readiness, answer-persistence or result-generation failures. The original learner-data
production blocker is resolved and validated.
