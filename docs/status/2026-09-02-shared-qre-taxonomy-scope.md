# Shared QRE taxonomy — scope

Date: 2026-09-02
Status: **proposal, not approved**
Owner: unassigned (see §6 — this is the point of the document)

Quantitative aptitude, Reasoning and English are the same skills in every exam
that tests them. A candidate weak in percentages is weak in percentages whether
they sit SSC CGL, UPSC CSAT, IBPS PO or CAT. What differs between exams is
difficulty and weightage, not the topic list.

This document proposes authoring those topics **once**, shared across exams,
with per-exam difficulty and weightage layered on top. It does not propose
building it yet; it establishes that the platform already supports it, names
what is missing, and asks the questions that have to be answered first.

---

## 1. Why this is a different problem from General Studies

The UPSC GS catalogue (244 microtopics, subject `09db7afb`) is correctly
exam-specific. "Delhi Sultanate administration" means something for UPSC and
nothing for a banking exam. It was built from the UPSC corpus and belongs to it.

QRE is the opposite. Building it per-exam produces near-identical catalogues
that cannot share mastery — and a candidate switching from SSC to banking, which
is a common path, starts from zero on skills they already have.

There is a third kind, already decided: **General Awareness has no taxonomy at
all, deliberately.** `docs/architecture/subject-practice-framework.md:44-52`
excludes PYQ ingestion, static-GK practice, permanent topic mastery and SRS from
GA v1; `seeds/exam_intelligence_demo_ssc_cgl.sql:82-88` states that GA "seeds NO
topics, NO exam_topic_coverage, NO PYQ, and never writes user_topic_mastery"
because it is calendar-driven and its content decays.

So the platform already distinguishes subject kinds by how their knowledge
behaves over time:

| kind | example | taxonomy | mastery |
|---|---|---|---|
| decaying | General Awareness | none, by decision | never written |
| exam-specific durable | UPSC General Studies | per exam | per exam |
| **universal durable** | **Quant, Reasoning, English** | **proposed: shared** | **shared, fail-closed** |

The third row is the gap.

---

## 2. The platform already supports this

Nothing needs building at the schema level.

**Subjects and topics are not exam-scoped.** `migrations/029:6-17` — `subjects`
has no `exam_id`. `029:29-43` — `topics` parents only to `subject_id` and
`parent_topic_id`. The only uniqueness constraint is
`unique(subject_id, parent_topic_id, slug)` (`029:42`), which is intra-subject.

**The intent is documented.**
`docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md:865-874`
— "Some entities are shared across exams: exam families, **subjects**,
**topics**, aliases, prerequisites." `docs/architecture/domain-model.md:97-115`
— content is "canonical and reusable across exams", with applicability held as a
separate default-deny scope.

**Per-exam weightage over a shared topic already works.**
`exam_topic_coverage` (`030:95-131`) is keyed
`(exam_id, exam_cycle_id, exam_phase_id, topic_id)` and carries
`coverage_depth` on a five-point scale (`mentioned | light | normal | deep |
core`), `expected_difficulty`, `exam_priority_score` and `is_high_yield`. One
topic can hold independent values per exam, per cycle, per phase.
`topic_id` is `on delete restrict`, so no exam can delete a topic another
depends on.

**There is shipped precedent.** `study_os/shared_core.py` partitions topics
covered by two or more exams as shared core. Its two guardrails are directly
reusable:

- cross-exam mastery reuse is **fail-closed** — only a global
  `user_topic_mastery` row (`exam_id IS NULL`) counts, "so mastery earned for
  one regulator never suppresses a topic for another" (`:12-16`)
- shared core is computed from **common** coverage only (`stream_id IS NULL`),
  so stream-specific topics are never misclassified (`:17-19`)

**One subject is already shared in practice.** Slug `english-language` is
inserted by both `seeds/exam_intelligence_demo_ssc_cgl.sql:80` and
`migrations/205:1060-1063` with `ON CONFLICT (slug) DO NOTHING`; `slug` is
UNIQUE, so both converge on one row serving the SSC exam structure and the
English Writing Practice taxonomy.

---

## 3. What is actually missing

**An owner.** The architecture assumes this taxonomy exists and two lanes
reference it, but nothing builds it:

- `docs/architecture/financial-regulatory-development-family.md:70-82` — Lane R
  lists "Quantitative aptitude, Reasoning | Lane GQR (aptitude) | **Consume
  topic coverage; do not author**"
- `study_os/subject_runtime_policy.py:70-72` — the group→family map is
  described as "stable across exams that share the SSC/RRB taxonomy", presuming
  a shared taxonomy
- `docs/status/career-copilot-pr-plan.md:407-485` — Lane GQR's PRs are GQR-1,
  G0, G2-G6, Q7-Q9, R10, R2, 11: runtime, pipeline, heuristics, gym, signals,
  sets. **No taxonomy or ingestion PR.**

The one sized taxonomy proposal in the repo is CSAT-only and was declined —
`docs/status/coverage-pipeline-and-design-inventory-2026-08-27.md:600-616`,
deferred in commit `8ad9004` "until 2023/2024 CSAT data lands (operator
decision)". That data has now landed (2023: 80 q, 2024: 71 q, 2026: 70 q), so
the stated condition for revisiting is met.

**No banking exam is modelled at all.** IBPS appears only in scraping mockups.
Any sharing argument that depends on banking is currently theoretical.

---

## 4. Two live defects this would trip over

**CSAT's `subject_group` is unrecognised.** Subject `ce8d97ee` (slug
`upsc-csat`) carries `subject_group='aptitude'` in production. That value is in
neither `_GROUP_FAMILY` nor `_SLUG_FAMILY`, so `family_for_subject()` returns
`None` and CSAT falls through to `_GENERIC_POLICY` — behaviourally identical to
UPSC `gs`. Every repo artefact expects `reasoning`:
`seeds/exam_intelligence_demo_upsc_cse.sql:99`, the Part D investigation, and
`checks/reasoning_content_readiness_preflight.sql:72,77,100,105` which matches
`lower(subject_group)='reasoning'`. The live value silently opts CSAT out of the
reasoning family and its readiness checks.

Note `subject_group` is nullable free text with no CHECK constraint
(`029:11`) — nothing in the database constrains the vocabulary, which is how
`aptitude`, `language` and `social_science` all came to exist unmapped.

**CSAT has no microtopic hierarchy.** Subject `ce8d97ee` has six topics and zero
microtopics. Its one tagged paper (2025, 80 questions, live) is tagged entirely
at topic level: 42 reasoning, 29 comprehension, 8 decision-making, 1 data
interpretation, two topics unused.

---

## 5. Design questions to answer before building

**5.1 Is comprehension separable from the rest?**

Reasoning and quant decompose cleanly — percentages, ratios, time-and-work,
syllogisms, seating arrangement, blood relations, data interpretation behave
exactly like GS topics.

Reading comprehension does not. Worse, it cannot currently be tagged: **61 of
80 CSAT stems are passage-dependent, and no tagging path reads the passage.**
The tag gate keys on `question_id` alone; neither
`scripts/propose_pyq_topic_tags.py`, `scripts/pyq_question_review.py` nor the
CMS bulk-import reads stimulus text. A comprehension question tagged from
"Which one of the following statements best reflects the central idea conveyed
by the passage?" carries no information at all.

Proposal: an **asymmetric catalogue** — fine-grained on quant and reasoning,
deliberately coarse on comprehension, because finer is not achievable with the
current tagging path. Revisit if stimulus-aware tagging lands.

**5.2 One shared subject, or per-exam subjects over shared topics?**

`topics.subject_id` is single-valued, so a shared topic implies a shared
subject. Either QRE gets one subject each (`quantitative-aptitude`,
`reasoning`, `english-language`) serving all exams, or every exam gets its own
subject and topics cannot be shared.

The `english-language` precedent (§2) suggests the former already happens by
accident. Doing it deliberately means deciding what `subject_group` those
subjects carry, since that drives runtime policy.

**5.3 How does difficulty differ from the GS difficulty field?**

The UPSC GS work put a three-point `observed_difficulty` on the question. For
shared QRE topics the same question is easy for CGL and hard for CAT — but
questions stay exam-scoped even when topics are shared, so question-level
difficulty is still coherent. The per-exam variation lives in
`exam_topic_coverage.expected_difficulty` and `coverage_depth`.

Worth confirming that is the intended split rather than assuming it.

**5.4 Does mastery share, and under what guard?**

`shared_core.py` already answers this: fail-closed, only global
`user_topic_mastery` rows (`exam_id IS NULL`) count. Whether QRE mastery should
be written globally or per-exam is a product decision, not a schema one —
`user_topic_mastery.exam_id` is nullable (`033:39`), so both are expressible.

**5.5 Where does the topic list come from?**

The GS catalogue was built from the corpus, not the syllabus, and that decision
held up — 92% of microtopics earned at least one question from 800. QRE has
published syllabi from every exam board, which is a different and arguably
better starting point. But the corpus-first principle is worth keeping: a
microtopic with no questions across any exam is a microtopic nobody needs.

---

## 6. What this document asks for

1. **An owner.** Lane GQR is named as the author by Lane R but has no
   deliverable. Either add one or reassign.
2. **A decision on §5.1** — asymmetric catalogue, or wait for stimulus-aware
   tagging.
3. **A decision on §5.2** — shared subjects, and their `subject_group` values.
4. **Fix `subject_group='aptitude'`** (§4) independently and first. It is a
   one-value change that restores CSAT to the reasoning family and its readiness
   checks, and it should not wait on the taxonomy question.

Not asked for yet: the catalogue itself. That is a content project on the scale
of the GS one — 244 microtopics took a full session to build and validate — and
it should not start before §5.1 and §5.2 are settled.
