# COV-GAP-01 — PSIR Paper-I's 27 unscored coverage rows

**Status:** investigated, offline (code read only — no live database access from
this session). **Verdict: correct behaviour, not a defect.** No code change
made, and none is recommended.

Follows up the open item in
[`2026-09-12-optionals-publication-defects.md`](./2026-09-12-optionals-publication-defects.md)
(line 164): *"PSIR Paper-I has 27 coverage rows with no score — 100 scored of
127 — while every other optional paper is complete. Not investigated."*

---

## The mechanism, in two lines of code

`derive_topic_coverage` builds its work list from the **union** of two inputs,
not from the snapshots alone:

```python
# app/backend/app/exam_intelligence/coverage_derivation.py:621
topic_ids = sorted(set(snapshot_by_topic.keys()) | set(mention_counts.keys()))
```

and it writes a row for every topic in that union that clears the bucket
function:

```python
# app/backend/app/exam_intelligence/coverage_derivation.py:181-183
if evidence_count == 0 and syllabus_mentions == 0:
    return None          # "no row"
if evidence_count == 0:
    return "mentioned"   # row IS written, with no evidence behind it
```

A topic that appears in the **verified syllabus** but carries **no verified
primary PYQ tag** therefore gets a coverage row and no score. The row is not
half-written — `_proposed_row` fills it in deliberately
(`coverage_derivation.py:354-374`):

| field | value for such a row |
|---|---|
| `coverage_depth` | `mentioned` |
| `exam_priority_score` | `0` (written, not NULL — `(snapshot or {}).get(...) or 0`) |
| `confidence_score` | `0` |
| `is_high_yield` | `false` |
| `metadata.evidence.snapshot_id` | `null` |
| `metadata.evidence.evidence_count` | `0` |
| `metadata.evidence.derivation_basis` | `syllabus_only` |

`syllabus_only` exists precisely for this case and was added deliberately
rather than overloading `hybrid` — see the P2 comment at
`coverage_derivation.py:338-350`.

**The 27 rows are PSIR Paper-I topics that are in the verified syllabus and
have zero verified primary-tagged questions.** They are `coverage_depth =
'mentioned'`, `derivation_basis = 'syllabus_only'`, score 0.

---

## PREFLIGHT

### G1 — Identify the 27 topics; are they macro topics?

I cannot enumerate them from here: this is an offline session with no database
or API access, and the topic tree, tag rows and coverage rows all live in
Supabase. What the code does settle is the **exact predicate** that selects
them, so the enumeration is one query:

```sql
select t.id,
       t.name,
       t.level,                                    -- 'topic' vs microtopic
       c.coverage_depth,                           -- expect 'mentioned'
       c.metadata->'evidence'->>'derivation_basis' -- expect 'syllabus_only'
         as derivation_basis,
       (select count(*)
          from public.pyq_question_topic_tags g
          join public.pyq_questions q on q.id = g.question_id
         where g.topic_id = t.id
           and g.tag_role = 'primary'
           and g.reviewer_status = 'verified'
           and q.reviewer_status = 'verified')     as verified_primary_tags,
       (select count(*)
          from public.syllabus_topic_mentions m
         where m.topic_id = t.id
           and m.exam_id = c.exam_id
           and m.reviewer_status = 'verified')     as verified_mentions
  from public.exam_topic_coverage c
  join public.topics t   on t.id = c.topic_id
  join public.subjects s on s.id = t.subject_id
 where s.slug = 'upsc-cse-mains-opt-psir-p1'
   and c.source_basis = 'evidence_derived'
   and c.metadata->'evidence'->>'snapshot_id' is null
 order by t.level, t.name;
```

The prediction the code supports: every returned row has
`verified_primary_tags = 0`, `verified_mentions >= 1`, `coverage_depth =
'mentioned'`, `derivation_basis = 'syllabus_only'`.

On **level**: the ticket notes 21 macro topics vs 27, and warns not to assume.
The code does not branch on `level` anywhere in this path — nothing in
`coverage_derivation.py` or `score_snapshots.py` reads it. So level is not the
selector. It is nonetheless the likely *correlate*: taggers attach primary tags
to microtopics, so macro topics accumulate verified syllabus mentions without
ever accumulating a primary tag. A split of 21 macro + 6 microtopics would fit
the arithmetic exactly and would mean six microtopics are in the syllabus but
have never been asked — a perfectly ordinary state for a 392-question corpus
against a 106-microtopic tree. **Do not treat that split as established**; the
query above settles it.

### G2 — Does each half of the pipeline behave as the gap requires?

**Does `compute_exam_topic_scores` produce a snapshot for a topic with zero
primary tags?** Only via one route, and it is not the syllabus:

```python
# app/backend/app/exam_intelligence/score_snapshots.py:513
all_topic_ids = set(primary_counts.keys()) | set(locked_cov.keys())
```

`primary_counts` comes from verified primary tags on verified questions;
`locked_cov` comes from **locked, human-authored** coverage rows
(`reviewer_status = 'locked'` and `source_basis <> 'evidence_derived'`, the
OD-3 self-reinforcement break at `score_snapshots.py:430-444`). Verified
syllabus mentions are not an input to snapshots at all. So a topic with zero
primary tags gets a snapshot only if an operator has already locked
non-derived coverage for it — which is not the case for these 27, or they
would have scored.

**Does `derive_topic_coverage` write a coverage row for a topic with no
snapshot?** Yes — the union at line 621 plus the `mentioned` bucket, quoted
above.

**The combination:** an unscored coverage row is **expected**, not anomalous.
It is the designed representation of "this is in the syllabus, and we have no
PYQ evidence for it yet". Given the direction of the pipeline it is also the
only sound one: a score would have to be invented, and PD-1 makes locked
snapshots the sole evidence-number authority.

This also explains why the 27 survived a run the incident report describes as
clean. "All 392 PSIR Paper-I questions are verified and carry a verified
primary tag" and "1,227 snapshots computed with 0 errors" are both true and
neither is in tension with the gap: the missing evidence is not at the
question level, it is that no question points at these 27 topics.

### G3 — Does the same gap exist elsewhere and go unnoticed?

The predicate is subject-agnostic, so structurally it can occur on any
subject. But the published table's alignment (`n` rows, `n` scored) is not
evidence that other subjects are free of the same *situation* — the counts can
align for either of two reasons, and they mean different things:

1. Every topic with a verified mention also carries a verified primary tag →
   genuinely no gap.
2. The untagged topics carry **no verified syllabus mention either**, so
   `bucket_coverage_depth` returned `None` and no coverage row was ever
   written → the same untagged topics exist, but they are absent from the
   table rather than unscored in it.

Case 2 is the one that "happens to align", and it is the more likely reading
for the other optionals: PSIR Paper-I has 127 coverage rows against 21 + 106 =
127 topics, i.e. **every topic in its tree has a row**, which means its
syllabus mentions were verified all the way up to the macro level. History
Paper-I's 106 rows and PSIR Paper-II's 89 are not obviously equal to their
tree sizes. Different syllabus-mention verification depth per subject, not
different scoring behaviour.

One query settles it across all optionals:

```sql
select s.slug,
       count(*)                                                as coverage_rows,
       count(*) filter (
         where c.metadata->'evidence'->>'snapshot_id' is not null) as scored,
       count(*) filter (
         where c.coverage_depth = 'mentioned')                 as mentioned_only,
       (select count(*) from public.topics t2
         where t2.subject_id = s.id)                           as topics_in_tree
  from public.exam_topic_coverage c
  join public.topics t   on t.id = c.topic_id
  join public.subjects s on s.id = t.subject_id
 where s.slug like 'upsc-cse-mains-opt-%'
   and c.source_basis = 'evidence_derived'
 group by s.slug, s.id
 order by s.slug;
```

`coverage_rows < topics_in_tree` on a subject with `mentioned_only = 0` is
case 2 — the same untagged topics, invisible.

---

## Is it a defect?

**No.** An `exam_priority_score` of 0 on a `mentioned` / `syllabus_only` row is
the derivation reporting, correctly, that it has no evidence for that topic;
inventing a score would violate PD-1 and the deterministic-scoring rule.

Two things adjacent to it are worth separating out, neither in this task's
scope and neither a scoring change:

- **A presentational gap, not a data one.** Nothing in the coverage list route
  distinguishes "scored 0 because it was never asked" from "scored 0 because
  the score computed to 0". The signal already exists on the row
  (`coverage_depth = 'mentioned'`, `derivation_basis = 'syllabus_only'`,
  `snapshot_id = null`); the admin surface just does not surface it. If the 27
  are to stop reading as a defect on sight, that is where to fix it — one
  column in `CoveragePanel`, no backend change.
- **The 27 are a tagging worklist, not a bug.** They are precisely the PSIR
  Paper-I syllabus topics with no PYQ evidence. That is useful signal for the
  corpus team, and it is what the `mentioned` bucket is for.
