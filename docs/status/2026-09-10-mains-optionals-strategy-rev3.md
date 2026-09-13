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

---

## Decision M10-rev3 — parts are metadata, and M10 as written cannot be built

Revision 2's M10 is headed "Syllabus parts are topics, not sections" and
requires a syllabus's internal parts to become **top-level `topic` rows** under
the paper's subject.

The twelve spines do not do that. Four of them — PSIR Paper-I and Paper-II,
Geography Paper-I, Sociology Paper-II — carry their parts in a `section_ref`
field on each node, and cite M10 while doing the opposite of what it says.
SYL-VERIFY-01 caught the inversion, and the verification brief had inherited it,
restating M10 to match the files rather than the decision.

**The engineering reason is sound and M10 did not account for it.**
`ingest_upsc_gs_syllabus.py` is strictly two-level: `macro_topic` becomes
`level='topic'` and `micro_themes` become `level='microtopic'`. M10's
part → unit → micro-theme tree needs three. Spending the topic level on a
binary split would have left PSIR Paper-I with 2 topics and 106 microtopics,
which is not a tree anyone can tag 392 questions against.

**But `section_ref` is read by nothing.** It appears nowhere in the ingest, so
it reaches no database row. For those four papers the official division is
currently recorded in neither form — not as topics per M10, nor as metadata per
the files' own stated intent.

**Decision M10-rev3.** The numbered units are the topic level. A syllabus's
named parts are **node metadata**, carried through the ingest into
`topics.metadata.syllabus_part`, and are never topic rows and never
`exam_phase_sections`.

- The prohibition in M10 stands: parts must not become `exam_phase_sections`.
  Modelling parts as sections would invent divisions for eight of the twelve
  papers and undercount Sociology Paper-II, which has three parts against two
  paper sections.
- What changes is the positive half. M10 said "topic rows"; that requires a
  third level the ingest does not have. Metadata is what the two-level tree can
  actually carry.
- `section_ref` in the twelve source files is the right field with no plumbing
  behind it. Either teach the ingest to map `section_ref` into
  `topics.metadata.syllabus_part`, or rename it there — but until one of those
  happens, the four part-bearing papers have lost their division.

**One thing SYL-VERIFY-01 confirmed clean:** `section_ref` usage matches M10's
own table of official divisions row for row. Four part-bearing papers carry
parts, eight flat papers omit the field, and no file missed a part its syllabus
has. The classification was right; only the plumbing is missing.

---

## The verbatim claim, and why it needed correcting

`ingest_upsc_gs_syllabus.py:361-364` sets `mention_type` from
`official_syllabus_line_is_verbatim`, **defaulting to true**. No node in any of
the twelve files sets that flag, so all 183 unit mentions landed as `explicit` —
which the script's own comment at `:353` defines as asserting the text IS a
verbatim official syllabus line.

Every one of those files also carries a `provenance_note` stating the text was
never diffed against the UPSC notification. The database asserted what the
source document denied, and review could not have caught it: `reviewer_status`
and `mention_type` are independent columns, so the claim was never the thing
being reviewed.

Corrected by `SYL-FIX-01_mention_type.sql` — the 183 reclassified to `derived`,
with the reason in `metadata`. Same call made on 2026-08-24 for three GS macro
rows that turned out to be editorial groupings rather than official lines.

The source files still need `"official_syllabus_line_is_verbatim": false` on
every node so a re-ingest does not reintroduce it. That edit changes each file's
content hash and so creates a fresh `syllabus_documents` row with a full new
mention set — it belongs in a deliberate batch with the other pending source
edits, not applied on discovery.

---

## Sequence, amended

1. **Run SYL-FIX-01's G3 block**, which was a STOP gate on SYL-VERIFY-01 and is
   still unanswered. If any optional mention is not `pending`, something has
   been reviewed against the wrong verbatim claim and that review needs
   revisiting before anything else.
2. **Correct `mention_type`** on the 183 unit mentions (SYL-FIX-01).
3. **Merge the branch holding ten of the twelve source files.** They currently
   live only on `fix/ingest-subject-slug-no-hash`, so the reproducible input
   behind 1,252 live rows is not on `main`.
4. **Prove coverage isolation once.** Promote the mentions for a single optional
   paper — PSIR Paper-I — to `verified`, derive coverage, and confirm the GS-II
   rows are untouched. This is the only claim above that has never run.
5. **Overlap worksheet**, rebuilt on M8-rev3: two columns, not three. Each
   optional microtopic is either `new` or `gs_counterpart` with the GS
   `topic_id` recorded in `metadata`. The `concept-child` branch is withdrawn
   along with `shared`.
6. **Tag**, PSIR first, end to end.
7. **M9 reads**, as its own PR, any time.
8. **`section_ref` plumbing** (M10-rev3), so the four part-bearing papers keep
   their official division.

## Still open

- Whether mastery should ever roll across an overlap relationship. Deliberately
  not designed here. If it is ever wanted, `metadata.gs_counterpart_topic_id`
  is the pointer a future implementation would read.
- The projection's behaviour at concept depth (`270:332-334`) is dormant only
  while the optional corpus stays descriptive. It should be revisited before any
  descriptive question becomes projectable.
