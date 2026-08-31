# `pyq_questions.observed_difficulty` — canonical vocabulary

**Status:** writers constrained (this PR). DB CHECK **proposed, not applied**.

---

## The canonical set

`easy` | `medium` | `hard`. NULL is legal and means "no difficulty recorded".

Not chosen on taste — it is the set the pipeline already enforces at its far
end. Migration 239's `project_pyq_question_to_bank()` writes

```sql
case when lower(v_q.observed_difficulty) in ('easy','medium','hard')
     then lower(v_q.observed_difficulty) else 'medium' end
```

into `mock_question_bank.difficulty`. Any fourth value is therefore not a
finer-grained label — it is `medium` with extra steps, and the operator who
chose it is never told. The projection is also where the value stops being an
annotation and starts affecting a learner: `mastery_delta._difficulty_weight`
reads `hard → 1.5`, `medium → 1.0`, `easy → 0.5` off the projected row.

The alternative — widen the projection to carry a fourth value — was rejected
by scope, not by merit. The `case` expression is inside the projected content
hash (`239…sql:318-328`); changing it re-hashes and re-projects all 1,083
existing rows. If a fourth bucket is ever wanted, that is the cost, and it is a
deliberate migration, not a dropdown edit.

## Where the disagreement was

| surface | accepted before | now |
|---|---|---|
| `PyqPaperWorkspace.jsx` difficulty dropdown | easy/medium/hard/**very_hard** | easy/medium/hard |
| `ExamIntelCms.jsx` generic entity editor | easy/**moderate**/hard | easy/medium/hard |
| `admin_exam_intel_cms.py` create / PATCH / bulk-import | **anything** | easy/medium/hard, NULL ok |
| `pyq_bulk_import.py` v1 + v2 | **anything non-empty** | easy/medium/hard, NULL ok |
| `exam_intelligence_demo_ssc_cgl.sql` seed | wrote **`medium_high`** | writes `hard` |
| `scripts/docx_to_pyq_json.py --difficulty` | already `choices=(easy, medium, hard)` | unchanged |

`moderate` and `medium_high` both normalise to `medium` in
`pyq_papers._normalize_difficulty` and both project to `medium`, so they were
never wrong on the chart — but they are invisible to
`GET /pyq-questions?difficulty=medium`, which filters with `.eq()` on the raw
column. `very_hard` was wrong everywhere: chart said `hard`, bank said
`medium`.

## Read-side tolerance is deliberate

`pyq_papers._normalize_difficulty` still maps `very_hard → hard`,
`medium_high → medium`, `moderate → medium`, plus `e`/`m`/`h`/`tough`/
`easy_low`/`easy_mid`. Kept, with a comment, because rows written before this
change still hold those values; dropping the aliases would move them to
`unknown` and discard the reviewer's stated judgement without making anything
more correct. Delete the alias block once the corpus is clean and the CHECK
below is in place.

Note the aliases do not agree with the projection (`very_hard → hard` here,
`→ medium` there). That disagreement is the defect, and it is closed by
preventing the write, not by picking a different lie on the read side.

---

## Proposed CHECK constraint — recommended, blocked on data

**Recommendation: add it, in a follow-up PR, once the non-canonical rows are
repaired.** The coupling is worth it. The column is bare `text` with a
three-value domain that the projection already enforces unilaterally; a CHECK
does not constrain anything the system was willing to honour anyway. Every
sibling column on this table (`question_type`, `reviewer_status`,
`source_type`, `tag_role`) already carries one. The cost of widening the set
later is a migration — but widening the set already requires a migration,
because the projection is the real gate.

It is not in this PR because two rows would fail it. Applying a CHECK against
violating data aborts the migration.

### Step 1 — find the violators (read-only)

```sql
select id, pyq_paper_id, question_number, observed_difficulty
from public.pyq_questions
where observed_difficulty is not null
  and observed_difficulty not in ('easy', 'medium', 'hard')
order by pyq_paper_id, question_number;
```

### Step 2 — repair. **Not run by this PR.**

Known from code inspection, one row, the SSC CGL demo seed. The seed file now
emits `hard`, but its insert is `on conflict (id) do nothing`, so re-running
the seed will not repair an already-seeded database:

```sql
update public.pyq_questions
set observed_difficulty = 'hard'
where id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeee3'
  and observed_difficulty = 'medium_high';
```

Questions 61 and 72 of UPSC paper `22ea7f1b-d40b-46e2-b111-efdfc20e6f94` held
`very_hard` and were corrected by hand before this PR. Step 1 confirms whether
any `very_hard` survives elsewhere; repair each to the reviewer's intent
(`hard` if the reviewer meant "harder than hard", since that is what the
heatmap has been showing them).

A repaired row that has already been projected keeps its old
`mock_question_bank.difficulty` until re-projected — the content hash changes,
so the next projection run picks it up.

### Step 3 — the migration, once step 1 returns zero rows

```sql
-- <next>_pyq_observed_difficulty_check.sql
alter table public.pyq_questions
  add constraint pyq_questions_observed_difficulty_check
  check (
    observed_difficulty is null
    or observed_difficulty in ('easy', 'medium', 'hard')
  );

comment on constraint pyq_questions_observed_difficulty_check
  on public.pyq_questions is
  'Canonical observed_difficulty vocabulary. These three are the only values '
  'project_pyq_question_to_bank() carries into mock_question_bank; anything '
  'else is silently rewritten to medium there. NULL means no difficulty '
  'recorded and is legal.';
```

Number it `MAX(main) + 1` at authoring time —
`select max(version)::int + 1 from schema_migrations`, per migration
discipline. Do not take the number from this document.

The constraint is NOT `NOT VALID`: the point is to reject writes *and* to
assert the corpus is clean. If step 1 still returns rows, fix them; do not
weaken the constraint to land it.
