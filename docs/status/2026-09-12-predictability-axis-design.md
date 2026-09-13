# Predictability: a difficulty axis that works for descriptive papers

Design note, 2026-09-12. Supersedes rev2's "predictability is the candidate
axis, design it before judging anything" with an actual design.

---

## The problem this replaces

`pyq_questions.observed_difficulty` is a three-value field — easy, medium,
hard — and it is **null on all 8,188 verified Mains descriptive questions**,
deliberately.

For Prelims, difficulty is judgeable: there is a correct answer, so you can
count plausible distractors, steps to elimination, and how obscure the traced
fact is. The Prelims rubric does exactly that.

None of it transfers. "Discuss the impact of globalisation on workers in the
informal sector" has no answer key, no distractors, no elimination path. A
difficulty label on it would be a guess wearing the clothes of data — and
`planner.py` reads the field to sequence a study plan, so the guess would
silently order somebody's preparation.

**The honest axis for a descriptive paper is not how hard a question is. It is
how reliably its topic recurs.** A theme asked in 1991, 1998, 2007, 2015 and
2023 must be prepared. One asked once in 2019 need not be. That is a property
of the corpus, measurable, and it is what an aspirant actually needs to know.

---

## What the corpus says

Measured on the 4,264 thematic questions, 1980-2010, tagged to 891 topics.
(The year-wise half extends this to 2026 and should be folded in before
implementation; the shape below is unlikely to change.)

### Recurrence is broadly distributed — so it discriminates

| distinct years a topic was asked in | topics |
|---|---:|
| 1 | 182 (20%) |
| 2-4 | 365 |
| 5-7 | 185 |
| 8+ | 159 (18%) |

A fifth of topics appeared once in thirty-one years. A fifth appeared eight
times or more. That is a real signal, not noise, and it is invisible in a
2011-2026 window where almost everything looks like "once or twice".

### Decay is rare — so recency should carry little weight

Of 176 topics asked 6+ times, **only 3 stopped being asked by 1998**:

- Survivals and parallels among hunting/foraging communities, 11y, 1981-1997
- Biological and cultural factors in human evolution, 10y, 1981-1997
- Mendelian genetics in man: single-factor inheritance, 8y, 1982-1993

173 were still live at 2008 or later. UPSC's optional syllabi are stable; a
topic that has recurred keeps recurring. **A decay term would do almost no
work**, and weighting recency heavily would be modelling a phenomenon that
barely exists in this data.

Keep recency as a guard, not a driver: it exists to catch the next
Mendelian-genetics case, not to reshape the ranking.

### Regularity is a separate, real property

Of 344 topics asked 5+ times, gap-regularity splits them almost evenly —
181 regular (coefficient of variation below 0.6), 163 irregular.

The irregular ones are interesting rather than noisy:

- *e-Governance and information technology*, 8 asks 1989-2010, irregular
  because the topic **emerged** — absent, then frequent.
- *Structuralism: Levi-Strauss and Leach*, 12 asks 1981-2009, clustered in the
  1980s then sporadic.

So regularity carries information breadth does not: **a topic asked every
third year without fail is a different preparation object from one asked
twelve times in bursts.** The first is schedulable; the second is a risk.

---

## The measure

For each topic, over a scope of Y years (the corpus span for that subject-paper):

```
breadth      = distinct_years_asked / Y
regularity   = 1 - min(cv_of_gaps, 1.5) / 1.5        # 0 when erratic, 1 when metronomic
recency      = 1 if last_asked within the most recent third of Y
               else 0.5 if within the middle third
               else 0.2

predictability = 0.65 * breadth
               + 0.25 * regularity
               + 0.10 * recency
```

**Weights follow the data, not intuition.** Breadth dominates because it is
what the distribution actually separates on. Regularity is secondary because it
splits the frequently-asked set meaningfully. Recency is small because only 3
of 176 topics ever went quiet — it is a guard against a case that is real but
rare.

`regularity` is undefined for a topic asked once or twice; treat it as 0 and
let breadth carry those, which is correct — a topic asked once is not
predictable regardless of anything else.

### Bands, because a number is not advice

| band | rule | what it means to an aspirant |
|---|---|---|
| `near_certain` | breadth ≥ 0.35 and regularity ≥ 0.5 | appears most cycles, on a rhythm. Prepare properly. |
| `likely` | predictability ≥ 0.35 | recurs often enough to expect. Prepare. |
| `occasional` | predictability ≥ 0.15 | shows up. Know the outline. |
| `rare` | below that | asked once or twice in decades. Do not spend time here. |

The band is what a UI should show. The score is what sorts within a band.

---

## Where it lives, and what it is not

**A new column, not a reuse of `observed_difficulty`.** They are different
claims about different objects: difficulty is a property of a *question*,
predictability is a property of a *topic*. Overwriting the one with the other
would make every existing consumer silently wrong.

Proposal: `exam_topic_score_snapshots.predictability` (numeric) and
`.predictability_band` (text), computed alongside `exam_priority_score` in
`score_snapshots.py`, projected into `exam_topic_coverage` the same way, and
locked through the same review gates. It is derived evidence and belongs in the
same lifecycle as everything else derived from evidence.

**Leave `observed_difficulty` null on descriptive questions.** It is honest. A
separate future rubric may fill it — one built for descriptive answers, about
answer structure and marking, not about distractors — but that rubric does not
exist and inventing one is not this design.

**What predictability is NOT:**

- Not importance. A rarely-asked topic may be foundational.
- Not difficulty. A topic asked every year may be hard.
- Not a forecast. It says how a topic has behaved, not what UPSC will do next.
  The band names avoid "will appear" wording for that reason.

---

## What this needs from the planner

`planner.py` currently reads `observed_difficulty`, which is null for every
Mains descriptive question — so it is sequencing on nothing. Predictability
gives it a real input, but **how it should use it is a product decision, not a
derivation**:

- Front-load `near_certain` topics, or spread them?
- Does `rare` get zero plan time, or a single pass for completeness?
- Does a high-mastery `near_certain` topic get revision time, or yield to a
  low-mastery `likely` one?

Those want answering before the planner reads the field. Deriving the number is
the small half of this.

## Sequence

1. Recompute the measure over the **full 1980-2026 corpus**, not just the
   thematic half. The figures above are pre-2011 only.
2. Add the two columns to `exam_topic_score_snapshots`; compute in
   `score_snapshots.py` beside `exam_priority_score`.
3. Project into `exam_topic_coverage`; same review gates, same lock.
4. Surface the band — explorer and topic pages — before touching the planner.
5. Answer the planner questions, then wire it.

## Open

- **The 2011-2026 half uses a different unit.** Thematic rows are one per
  theme-year; year-wise rows are one per question, and a paper can ask two
  questions on one topic in a year. Breadth counts *distinct years*, which is
  robust to that — but any rate-based variant would not be. Keep breadth
  year-based.
- Sparse early years (1980 has one question, 1981 has 36) inflate `Y` for
  subjects whose coverage starts late. Scope `Y` per subject-paper to the span
  where that paper actually has evidence, not to 1980-2026 globally.
