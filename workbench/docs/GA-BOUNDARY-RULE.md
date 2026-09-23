# GA perishability boundary rule — v1

**Status:** decision rule, adopted. Written before re-classification, not after.

**Applies to:** RBI Grade B Phase I General Awareness, and any GA-class question on
another exam. It does not extend to a non-GA subject.

**What it decides:** whether a General Awareness question is **perishable** — its
answer decays, so it may be practised as current affairs but never tagged,
projected, or allowed to contribute permanent topic mastery — or **durable**, so it
is eligible for PYQ tagging and projection like any other question.

The governing product rule is `docs/architecture/subject-practice-framework.md`
§1.1 and its 2026-09-07 amendment §1.1.1, which narrowed the blanket GA exclusion
from "GA" to "perishable GA". That amendment named the boundary
("a durable *subject* with a dated *instance* is perishable") but did not make it
operable. This document does.

---

## 1. Why a rule was needed before any more classifying

Two independent passes over the same 320 RBI Grade B GA questions disagree:

| File | DURABLE | PERISHABLE |
|---|---:|---:|
| `workbench/rbi-ga-classification.csv` (cited by §1.1.1) | 202 | 118 |
| `workbench/ga-classification/rbi-ga-{2023..2026}-classification.csv` | 192 | 128 |

Same 320 `question_id` values, 12 direct contradictions, and the two disagree on
destination subject far more widely than that. Neither file declares precedence.

A boundary spot-check then found a further **29 rows in the durable population
(≈15%) that flip under a stricter reading** — 2023: 11, 2024: 14, 2025: 3,
2026: 1.

> **Note on the baseline.** The spot-check was run against a durable population of
> 191, which matches neither file on record (202 combined, 192 per-year). The
> discrepancy is not reconciled here and is itself evidence for this document: when
> three counts of "how many are durable" exist, the disagreement is not about
> individual calls. Re-classification under §2 supersedes all three counts.

The disagreement was about **how to read the boundary**, not about which way
particular questions fall. Adjudicating the 12 contradictions would have settled
12 rows and left the reading unfixed, so the next pass would have re-opened them.
The rule is therefore fixed first, and all 320 are then re-classified against it.

---

## 2. The rule

Apply the three tests **in order**. Stop at the first that matches.

### T1 — Is the answer a specific dated event or announcement?

→ **PERISHABLE.**

The answer is a thing that happened: a launch, an inauguration, a signing, a
conferral, an appointment, an award, a figure published for a named period. The
question is anchored to an occasion, and a later occasion supplies a different
answer.

Corpus examples, all perishable:

- 2023 Q4 — civilian honour conferred on a named person
- 2023 Q7 — NITI Aayog app launched at a dated visit
- 2023 Q9 — inauguration of the first international cruise vessel
- 2023 Q11 — CAG selected as ILO external auditor (an appointment)
- 2023 Q8 — Economic Survey growth forecast range **for a stated year**
- 2023 Q2 — FRB share of issuances **for 2022-23**

### T2 — Is the answer a current officeholder, rank, winner or host?

→ **PERISHABLE.**

The answer is a slot filled by a rotating occupant. The slot is durable; the
occupant is not. This covers who holds a post, which country or city ranks where,
who won, and who hosts next.

Corpus examples, all perishable:

- 2023 Q3 — gender-parity leader in that year's Global Gender Gap Index
- 2023 Q1 — BSR anniversary year count tied to October 2022

### T3 — Everything else

→ **DURABLE.**

T3 is a residual, and deliberately a large one. If neither T1 nor T2 fires, the
question is durable and eligible for tagging and projection.

Corpus examples, all durable:

- 2023 Q15 — inflation upper threshold and the consecutive-quarter breach rule
- 2023 Q17 — base period of the RBI Digital Payments Index
- 2023 Q5 — Town of Export Excellence threshold (scheme design)
- 2023 Q10 — full form of TRAI's Digital Consent Acquisition facility
- 2023 Q12, Q14 — forum membership, common membership of ASEAN and BIMSTEC
- 2023 Q6 — trilateral highway terminus (fixed project geography)
- 2023 Q18 — RBI public-awareness mascots (institutional)

---

## 3. The reading adopted: perishable is narrow

The tests above can be read strictly or loosely. This is the reading adopted, and
it is the substance of the decision — the three tests alone do not settle it.

**Perishable is deliberately narrow.** Four classes that a stricter reading would
call perishable are **DURABLE** here:

1. **Current values, limits and thresholds with no date in the stem.**
   RBI GA asks current-state questions, and an aspirant preparing for RBI is
   expected to track current state. A question asking the present repo rate, a
   present limit, or a present threshold, with no year named in the stem, is
   durable. This is the single largest effect of the reading and the main reason
   the perishable count falls.

2. **Annual-edition report themes.** The theme of a named annual report is fixed
   at publication. Next year's edition has a different theme, but it is a
   different report, not a changed answer. (Contrast T1: a *figure* published
   *for a stated year* is perishable — "Economic Survey forecast for 2023-24" is
   anchored; "the theme of the 2023 Human Development Report" is not.)

3. **Attributed statements.** Who said a thing, in a named speech or report, does
   not stop being true.

4. **Scheme design.** Eligibility rules, structural thresholds, the architecture
   of a scheme or facility. The value inside a design may be revised, but the
   design as asked is a structural fact, not an occasion.

**Consequence, stated up front:** the perishable count is expected to fall below
118, the current file of record's figure. A re-classification producing
substantially *more* than 118 perishable rows has applied a stricter reading than
this document licenses and should be re-checked against §3 before it is accepted.

---

## 4. Known gap — flagged, not solved

**A durable-tagged current value goes stale silently, and nothing detects it.**

This is a real and accepted cost of §3.1. A question asking a present threshold is
tagged durable; the threshold later moves; the tagged question now carries an
answer that was correct when tagged and is wrong afterwards. Nothing in the system
notices.

The machinery that would catch it exists but does not reach here.
`mock_question_bank` carries `valid_until`, `event_anchor_date`, `is_current` and
`is_current_based` (migration 159), and both mock selectors exclude rows that are
`is_current` / `is_current_based` or past `valid_until`. But those columns are
populated **only on the current-affairs pipeline path** — a candidate promoted
through the CA review flow gets a relevance window. A PYQ tagged durable and
projected through the ordinary path gets none of them. It is projected as a
permanent question, because as far as the projection is concerned it is one.

**This rule does not create a staleness mechanism, and adopting it does not imply
one exists.** Closing the gap would mean either a review cadence over
durable-but-moving GA tags, or extending `valid_until` to the PYQ projection path
so a durable current value can carry an expiry without being reclassified as
current affairs. Both are out of scope here. Until one exists, §3.1 trades silent
staleness for coverage, knowingly.

---

## 5. Scope boundaries

- **Per corpus.** §1.1.1 is explicit that the RBI GA carve-out "does not extend to
  any other body's GA section — the classification is per corpus". This rule is
  written to be reusable on another GA corpus, but applying it there is a separate
  decision, and no other GA corpus has been classified. NABARD's 100 GA questions
  remain excluded at load (`workbench/nabard_load.py`).
- **Classification only.** Being classified durable makes a question *eligible*
  for tagging and projection. It does not tag or project it. Tagging remains a
  separate reviewed step, and the verified-only read rule is unchanged: a
  carved-out GA question reaches a learner only after the same review lifecycle as
  any other PYQ.
- **Perishable rows are not deleted.** They stay available as current-affairs
  practice under §1.1, contribute no permanent topic mastery, and are never
  projected.

---

## 6. Not covered by this document

- The re-classification of the 320 itself — this rule is the input to it.
- Any tagging, projection, or database write.
- The 2026 Q35 answer-key defect (IMPS credited to SEBI; should be NPCI). That is a
  content error, not a boundary question, and is tracked separately.
- Which of the two existing classification files is of record. Re-classification
  under §2 supersedes both, so the question stops mattering rather than being
  answered.
- The destination-subject disagreement between the two files (economics 24 vs 6,
  financial-awareness 1 vs 27). Subject routing is a separate axis from
  perishability and is not settled here.
