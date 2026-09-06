# Regulatory corpus — decision provenance

**Written** 2026-09-06. Reconstructs where the SEBI / IFSCA / PFRDA review
decisions live, why the audit table looks empty, and pins the recording rule for
the RBI Grade B pass.

---

## 1. Why `admin_audit_logs` shows nothing

`PATCH /api/admin/exam-intelligence/items/pyq_question/{id}/review` writes **no
audit row at all**. It calls `update_pyq_question_review_atomic` and returns
(`admin_exam_intelligence.py:966-978`); there is no `_audit()` call on that
branch, and neither migration 162 nor 227 inserts one inside the RPC.

Consequences:

- A zero count on `new_value->'patch'->>'reviewer_status'` is the **expected**
  result whether the status was set through the review API or through SQL. It is
  not evidence of a direct SQL write. That predicate only ever matches the CMS
  envelope shape written by `admin_exam_intel_cms.py`, and the CMS question route
  refuses to touch `reviewer_status` by design ("Lifecycle stays where it is",
  `admin_exam_intel_cms.py:2136-2138`).
- `reviewer_notes` is dropped server-side for both reviewable kinds — the RPC
  takes no notes parameter, and `pyq_question_topic_tag` is `supports_notes=False`.
  `scripts/pyq_question_review.py` sends it anyway and says so at line 127:
  **the worksheet CSV is the audit trail.**

So there is exactly one durable place a per-question cause can be written today:
`pyq_questions.metadata`, via `PATCH /api/admin/exam-intelligence-cms/pyq-questions/{id}`
with the `{reason, payload}` envelope. `metadata` is in `_QUESTION_FIELDS`, and
that route **does** audit, storing `{reason, patch, previous}`
(`admin_exam_intel_cms.py:2172-2177`).

## 2. Where the SEBI / IFSCA / PFRDA causes actually are

Not in the worksheets. `workbench/{sebi,ifsca,pfrda}-worksheet.csv` have `decision`,
`notes` and `assign_topic_id` blank on every row and always did — every worksheet
commit on this corpus states it (`e1120cc`, `bf5cf33`, `5fd4195`, `6c3a8d3`,
`e075d74`). Those sweeps were a **difficulty-only** pass over an already-reviewed
corpus. No filled decision column was overwritten, because none was ever filled.

The causes are in
`docs/status/Regulatory-PYQ-needs-correction-backlog-2026-08-31.md`, produced by
the question-by-question EI-DATA-03 review that set the statuses. It carries the
cause breakdown for the `needs_correction` population, the three papers that
should be pulled rather than repaired, and the four-way split of the 60 rejected.

Counts have moved since that doc was written: it records 121 / 60 / 18, the
exports record **101 / 60 / 18**. Exactly 20 `needs_correction` rows were
repaired to `verified` in between (verified totals rose 886 → 906). The doc's
*causes* still stand; only its `needs_correction` count is stale.

## 3. Re-sweep loss — difficulty, not decisions

Re-sweeping does wipe a filled worksheet, and it happened once here: `0c2a507`
restored 181 already-applied IFSCA difficulty grades after `9e2d15d` re-swept the
file. Only the `difficulty` column was affected.

## 4. RBI General Awareness exclusion

Documented, not ad hoc. `docs/architecture/subject-practice-framework.md` §1.1
locks GA v1 to current-affairs practice and **explicitly excludes PYQ ingestion /
projection, PYQ-based prioritisation, and permanent topic mastery**. Commits
`546b11f` and `85e9486` cite that section as the reason GA rows were left blank.

Verifiable scope: **320** GA rows untouched in the swept worksheets — 80 each in
`rbi-{2023,2024,2025,2026}-worksheet.csv`. `review_out_rbi2022/questions_export.json`
carries no `General Awareness` section at all (115 rows: English 30, Reasoning 60,
Quant 25), so a 400 figure is not reproducible from anything in the repo. Treat
320 as the number, and re-derive from the database before quoting 400.

## 5. Recording rule for the RBI Grade B pass

For every RBI row set to `needs_correction` or `rejected`:

1. `PATCH /api/admin/exam-intelligence-cms/pyq-questions/{id}` with
   `{"reason": "<why>", "payload": {"metadata": {...existing..., "review_cause": "<cause>"}}}`
   **before** the status change. This writes the audited row.
   `metadata` is a whole-column replace — read the row first and merge, or the
   patch drops every other key.
2. Then `PATCH /api/admin/exam-intelligence/items/pyq_question/{id}/review` for
   the status itself.
3. Keep the filled worksheet. It remains the only place `notes` survives.

Never set `reviewer_status` by direct SQL: it bypasses the option cascade in the
RPC as well as leaving no trace.

The RBI worksheets already follow the spirit of this — `85e9486` and `7e57795`
name each of the eight `needs_correction` rows and its cause in the commit
message (missing machine rules, missing source statement, missing equations,
unrendered stacked fractions, duplicated option values). That is recoverable but
still commit-only; step 1 puts it on the row.

## 6. Open, needs one query

RBI's 939 `observed_difficulty` values predate this session's grading and cannot
be judged from the repo — the RBI exports carry no `observed_difficulty` key.
Run:

```sql
select observed_difficulty, count(*)
from pyq_questions q
join pyq_papers p on p.id = q.pyq_paper_id
join exams e on e.id = p.exam_id
where e.slug = 'rbi-grade-b'
group by 1 order by 2 desc;
```

A single value across the set means the August bulk-import default, not
judgement. This is the first item of the handoff's suggested order
(`docs/status/HANDOFF-regulatory-corpus-2026-09-05.md`).

---

## Related

- `docs/status/Regulatory-PYQ-needs-correction-backlog-2026-08-31.md` — the cause list
- `docs/status/HANDOFF-regulatory-corpus-2026-09-05.md` — corpus state
- `docs/architecture/subject-practice-framework.md` §1.1 — GA scope lock
- `scripts/pyq_question_review.py` — worksheet-as-audit-trail contract
