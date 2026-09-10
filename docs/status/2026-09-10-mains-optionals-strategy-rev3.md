# UPSC Mains optionals — strategy amendment, revision 3

Amends `2026-09-09-mains-optionals-strategy-rev2.md` on M8 and M9 only.
M1–M7 and M10 stand unchanged.

Written 2026-09-10, after OPT-SPIKE-01.

---

## M8 as written cannot be built

Revision 2 required that an optional question tag a `concept`-level row owned by
the optional's subject and **parented to the GS microtopic**, so that sharing
was expressed by parentage rather than by two subjects tagging one `topic_id`.

OPT-SPIKE-01 established that no such row can be created. All four topic write
paths reject a `parent_topic_id` whose subject differs from the row's own, with
a 422:

- `admin_exam_intel_cms.py:3410-3413` and `:3458-3459`
- `admin_exam_intel_manage.py:305-309` and `:391-398`

No database constraint forbids it — `029:29-44` carries only the foreign key and
the level CHECK — so direct SQL would succeed and produce a row that no API can
create, re-parent or repair. That is worse than not having it.

The spike created no row. The blocker is the finding.

---

## The parent edge was never going to do the work M8 gave it

This is the more important discovery, and it stands independently of the guards.

**Mastery does not traverse `parent_topic_id`.** It groups strictly on
`(topic_id, exam_id, exam_phase_id)` (`mastery.py:170-176`, `:210-215`).
`parent_topic_id` appears nowhere in that file and no recursive walk exists in
any migration. The answer to revision 2's open question — does mastery roll up
or down the parent edge — is **neither**.

`parent_topic_id` is read by exactly one consumer: the projection's level split.
Nothing in mastery, planning or coverage reads it.

So revision 1's motivating example does not survive, and would not have survived
even if the guards had allowed the row: an aspirant with high GS-II mastery on
*Federalism* starts the PSIR treatment of federalism from zero either way. Under
M8, sharing-by-parentage was decorative.

**Migration 270 already considered concept depth and declined it.** Its comment
at `:332-334` states that a deeper concept row would land its immediate parent in
`topic_id` — reintroducing, one level down, the exact defect 270 was written to
fix. Its Python mirror shares the assumption
(`admin/pyq_mock_projection.py:198-215`). Dormant while the optional corpus is
entirely descriptive, since `270:189` blocks non-MCQ projection; live the day it
is not.

---

## Decision M8-rev3, replacing M8

**An optional question is never tagged to a topic owned by a GS subject. Every
optional tag resolves to a row owned by that optional paper's own subject.
Optional topics have no parent outside their own subject; where a GS
counterpart exists, it is recorded in `metadata`, not as a parent edge.**

Concretely:

- Optional topic trees are self-contained. `parent_topic_id` links a microtopic
  to its own subject's macro topic and never crosses a subject boundary.
- Where an optional microtopic covers ground a GS microtopic also covers, the GS
  `topic_id` is recorded as `metadata.gs_counterpart_topic_id` with a short
  `metadata.gs_counterpart_note`. This is a documented pointer for a future
  consumer, not a structural claim.
- The `concept` level is not used. Optional depth lives at `microtopic`, the
  same level GS uses. The twelve spines already ingested are built this way.

**Why the pointer rather than the edge.** The edge bought one thing in theory —
mastery reuse — and buys nothing in fact, because no consumer walks it. A
`metadata` pointer costs nothing, survives the write guards, and is honest about
what it is: a note that two topics overlap, not a claim that the system does
anything about it.

**What is given up, stated plainly.** Revision 1 wanted a PSIR aspirant's GS-II
mastery to count toward the PSIR treatment of the same theme. It does not, and
did not under M8 either. Building that would need a real mastery roll-up across
some relationship, which is its own piece of work and is not assumed anywhere in
this strategy.

---

## Isolation, restated on what actually holds

M8's purpose — a GS-only aspirant never sees optional material — survives, and
the spike found it better enforced than revision 2 claimed.

**Coverage rows stay distinct.** `coverage_derivation.py:621` unions per-topic
keys and `:641` writes one row per id, so a GS microtopic's `coverage_depth`,
`exam_priority_score` and `is_high_yield` cannot be overwritten by an optional
derivation. Under M8-rev3 the topics are distinct rows in distinct subjects
anyway, so the collision revision 2 feared cannot arise at all.

**The GS topic tree excludes optional rows twice.** `subjects.py:390-394`
filters on `subject_id` **and** on `level in ('topic','microtopic')`. Optional
topics sit under optional subjects, so a GS-scoped read cannot reach them.

**Correction to revision 2's citation.** M8 cited the coverage unique index as
`030:124-125`. Migration `242:140-141` drops both indexes from `030:124-130` and
replaces them with `stream_id` in the key (`242:143-152`, `nulls not distinct`);
a third exam-wide index sits at `217:104`. `section_id` remains absent from all
three, and GS shares the Mains phase with the optionals, so revision 2's
conclusion was right and only its `path:line` was wrong.

**Not yet observed.** Coverage derivation reads a topic only via a locked
snapshot or a **verified** mention (`coverage_derivation.py:234-273`). All 1,252
optional mentions are `pending`, so none of the above has run in practice. Prove
it on one optional paper before tagging at scale — see the sequence below.

---

## Decision M9-rev3 — the unscoped reads are a work item, not a caveat

Revision 2 stated that every aspirant-facing read of topics or PYQs is scoped by
`subject_id`. The spike found **nine reads that are not**, each cited in
`workbench/investigations/OPT-SPIKE-01_concept_level.md` §4.

Under M8-rev3 these are less dangerous than under M8 — optional topics are
ordinary microtopics under optional subjects, so an unscoped read returns them
the same way it would return any other subject's rows. But "no worse than the
existing bug" is not the same as safe, and the optionals multiply what an
unscoped read can surface.

- `planner.py:287` is first. Its own comment describes rendering the
  "Subject → Topic → Microtopic → Concept hierarchy", so it is already written
  for a depth that would leak.
- `content_studio.py:847-858` is the one route that 422s on an unscoped read.
  It is the pattern the other eight should copy.

Fixing these is a separate PR and does not block tagging, because under M8-rev3
nothing an unscoped read returns is structurally novel.

---

## Sequence, amended

1. **Prove coverage isolation once.** Promote the mentions for a single optional
   paper — PSIR Paper-I — to `verified`, derive coverage, and confirm the GS-II
   rows are untouched. This is the only claim above that has never run.
2. **Overlap worksheet**, rebuilt on M8-rev3: two columns, not three. Each
   optional microtopic is either `new` or `gs_counterpart` with the GS
   `topic_id` recorded in `metadata`. The `concept-child` branch is withdrawn
   along with `shared`.
3. **Tag**, PSIR first, end to end.
4. **M9 reads**, as its own PR, any time.

## Still open

- Whether mastery should ever roll across an overlap relationship. Deliberately
  not designed here. If it is ever wanted, `metadata.gs_counterpart_topic_id`
  is the pointer a future implementation would read.
- The projection's behaviour at concept depth (`270:332-334`) is dormant only
  while the optional corpus stays descriptive. It should be revisited before any
  descriptive question becomes projectable.
