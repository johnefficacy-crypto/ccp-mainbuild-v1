# Operator validation — UPSC CSE 2025 CSAT Set-B learner access (2026-07-14)

**Track:** PYQ Intelligence v2 PR-5/6 learner full-paper practice + production access control  
**Environment:** production  
**Frontend:** `https://ccp-web-demo.vercel.app`  
**Backend:** `https://ccp-api-demo.onrender.com`  
**Frontend deployed SHA:** `33f52f3b2d1e3558821a5c08c62eca56a9c24e82`  
**Backend deployed SHA:** `9d3d1c78be728088d5387147ad06a4d81176f872`  
**Supabase project:** `ylfnbxyqiyiqvxtthhum`

## Disposition

```text
PARTIAL PASS — EXACT CSAT SET-B DATA, ACCESS CONTROL, ATTEMPT LIFECYCLE,
PERSISTENCE, SCORING, RESULT AND REVIEW VALIDATED;
LEARNER IDENTIFICATION / DISCOVERABILITY UX DEFECTS REMAIN.
```

The production learner can reach and complete the exact UPSC CSE 2025 Prelims GS Paper-II CSAT Set-B corpus. The canonical paper, all 80 verified questions, all 80 active projections, the learner-owned frozen attempt, answer persistence, scoring, result, review, and projection-table RLS were validated with real learner/admin sessions. This record does not mark the wider PR-5/6 workstream complete: revision entry mode remains deferred and the UI defects below remain open.

## Identities and role authority

| Principal | User id | `/api/auth/me` | Authoritative role |
|---|---|---:|---|
| Learner | `bfdddedd-20e0-470d-b442-cff682791315` | 200 | `user` |
| Admin | `664d94c6-907d-482a-8a0b-95571712075f` | 200 | `super_admin` |

No access tokens, cookies, API keys, emails, or authorization headers are stored in this audit.

## Canonical paper and provenance

| Field | Validated value |
|---|---|
| Paper id | `505b29a0-0d4d-5230-88aa-3bbc525a6db5` |
| Paper code | `GS-PAPER-II-CSAT` |
| Year / date | `2025` / `2025-05-25` |
| Trust status | `verified` |
| Set identity | `metadata.set_code = B`; `metadata.paper_set = SET-B` |
| Official paper URL | `https://www.upsc.gov.in/sites/default/files/QP-CSP-25-GENERAL-STUDIES-PAPER-II-26052025.pdf` |
| Source registry URL | `https://upsc.gov.in/examinations/previous-question-papers` |
| Verified questions | `80` |
| Active practice projections | `80` |
| Answer key | Present; metadata authority `operator_typed_canonical_official_key` |

Both paper and source rows were `verified`. `metadata.provenance_pending` remained the string value `true` on both rows despite the official PDF/source and verified status being present. Runtime eligibility does not consume this metadata flag, so it did not block the validated flow; it is stale metadata debt and should be reconciled separately.

## Learner discoverability API

`GET /api/exam-intelligence/exams/upsc-cse/pyq-summary` returned HTTP 200 with:

```json
{
  "exam_id": "5466e62f-7382-4a38-ba96-2fe5fbfeaba2",
  "verified_only": true,
  "totals": {
    "papers": 4,
    "questions": 177,
    "projected_practice_ready": 177
  }
}
```

The exact paper entry returned:

```json
{
  "paper_id": "505b29a0-0d4d-5230-88aa-3bbc525a6db5",
  "year": 2025,
  "phase_slug": "prelims",
  "phase_name": "Prelims",
  "subject_id": "ce8d97ee-c1de-4ce2-a5ef-36d05c14d859",
  "subject_name": "upsc-csat",
  "question_count": 80,
  "practice_ready_count": 80,
  "practice_enabled": true
}
```

The direct detail route `/app/exam-intelligence/exams/upsc-cse` worked. The catalogue search did not find the exam when the operator searched `UPSC`; see open defects.

## Exact paper launch and frozen attempt

The learner clicked the 2025 / Prelims / `upsc-csat` card once. Production accepted:

```json
{
  "mode": "paper",
  "target_id": "505b29a0-0d4d-5230-88aa-3bbc525a6db5",
  "exam_id": "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
}
```

`POST /api/study/mocks/practice/start` returned HTTP 200:

```json
{
  "outcome": "ready",
  "attempt_id": "9269bf14-e919-4250-84c0-b9b464117eff",
  "blueprint_id": "c7016626-4d14-4d4d-84b9-3c8187ef9263",
  "question_count": 80,
  "source": "pyq_practice_paper",
  "exam_id": "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
}
```

The frozen database state reconciled exactly:

| Check | Result |
|---|---:|
| Attempt owner | `bfdddedd-20e0-470d-b442-cff682791315` |
| Attempt status before submit | `in_progress` |
| Frozen source | `pyq_practice_paper` |
| Practice mode | `paper` |
| Practice target id | exact CSAT Set-B paper id |
| Template question ids | 80 |
| Response rows | 80 |
| Unique bank questions | 80 |
| Rows carrying exact `pyq_paper_id` | 80 |
| Unique canonical `pyq_question_id` values | 80 |
| Saved answers at evidence capture | 9 |
| Saved dwell at evidence capture | 307 seconds |

The operator confirmed selected answers remained after refresh and questions beyond the initially visible palette range were reachable by keyboard navigation. Answer writes succeeded.

## Submission, result and review

`POST /api/study/mocks/attempts/9269bf14-e919-4250-84c0-b9b464117eff/submit`, `GET .../result`, and `GET .../review` each returned HTTP 200.

Final authoritative result:

```json
{
  "status": "submitted",
  "score_raw": 2.0,
  "score_percentage": 2.5,
  "total_correct": 2,
  "total_wrong": 11,
  "total_unattempted": 67,
  "time_used_sec": 2167,
  "time_remaining_sec": null,
  "avg_time_per_q_sec": 27.1
}
```

Reconciliation: `2 correct + 11 wrong + 67 unattempted = 80`. Thirteen answers were present at submission, consistent with `2 + 11`. The review response used immutable `attempt_order`, began at 1, contained the frozen question snapshot, and preserved printed source option labels such as `(a)` and `(b)` rather than exposing UUIDs.

`time_remaining_sec = null` is expected for this launch. Full-paper PYQ practice is untimed unless a duration is supplied; the long abandonment TTL is intentionally not exposed as a learner countdown. Per-question dwell still persists and feeds result analytics.

## Real-JWT projection-table RLS proof

Direct PostgREST reads against `public.pyq_mock_question_projections` were executed with the production anon key and real sessions:

| Principal | HTTP | Body | Result |
|---|---:|---|---|
| Anonymous | 200 | `[]` | PASS — no row exposure |
| Learner (`user`) | 200 | `[]` | PASS — no row exposure |
| Admin (`super_admin`) | 200 | one `{mock_question_id, sync_status}` row | PASS — admin policy works |

This is valid RLS evidence because it used real PostgREST/JWT requests rather than a Supabase Studio connection that can bypass row-level security.

## Open defects and disposition

| # | Defect | Severity | Required correction |
|---|---|---|---|
| 1 | Exact Set-B identity is absent from the learner paper card. The API card exposes no `paper_code`, `set_code`, `paper_set`, or reviewed display label; the UI shows only `2025 · Prelims · upsc-csat · 80 questions`. | High / blocker for an “exact Set-B is identifiable in UI” claim | Extend the learner paper summary contract with a safe paper display identity and render `CSAT · Set-B` (or equivalent reviewed label). Add a regression using two same-year/same-phase papers. |
| 2 | Searching `UPSC` in the Exam Intelligence catalogue returns no match although `/app/exam-intelligence/exams/upsc-cse` works. Search only matches `exam.name`; deployed naming does not contain the expected acronym. | High discoverability | Search normalized name, slug, aliases/acronyms and exam family; add `UPSC` → `upsc-cse` regression. |
| 3 | The question palette does not make all 80 numbers discoverable without keyboard navigation. All questions exist and are reachable, but lower items are visually clipped/hidden in the operator viewport. | High usability | Give the palette an explicit scroll area with footer-height reserve, active-item `scrollIntoView`, and >80-question viewport regressions. |
| 4 | After selecting an MCQ option, the learner cannot clear it back to unattempted. The API accepts and persists `selected_option_id: null`; the UI has no clear-response control or deselect behavior. | High correctness-of-intent UX | Add an explicit `Clear response` action that queues a null answer through `useAnswerSync`, updates counts/palette immediately, persists after refresh, and is covered through submit/review. |
| 5 | `provenance_pending=true` remains in verified paper/source metadata despite the official source being attached. | Metadata cleanup | Reconcile the promotion workflow so verified provenance clears/updates the pending flag atomically, or remove the stale flag from runtime-facing metadata. |

The earlier 2026-07-13 aggregate validation reported a timer `--` finding for a different attempt context. For this exact CSAT Set-B paper-practice launch, the absence of a countdown is intentional untimed behavior and is not carried forward as a defect. The earlier concatenated-review-option finding was not reproduced here; printed labels and structured option snapshots were present in the live review response.

## Gate result

- Exact production data/readiness: **PASS**
- Learner launch and frozen lineage: **PASS**
- Resume/answer persistence: **PASS**
- Submit/scoring/result/review: **PASS**
- Projection RLS using anon/learner/admin identities: **PASS**
- Exact Set-B learner identification and catalogue discoverability: **FAIL / follow-up required**
- Overall: **PARTIAL PASS**

No further operator testing is required for this attempt. The next work is a bounded frontend/API follow-up plus regression coverage for the defects above.