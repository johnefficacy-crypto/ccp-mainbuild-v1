# GA perishability boundary rule (v1)

Applies to RBI Grade B Phase I General Awareness questions, and to any
GA-class question on other exams. One question, one verdict, no middle.

PERISHABLE  -> never tagged, never projected, excluded from mastery.
DURABLE     -> tagged to finance / economics / general-knowledge, projected.

## The test, in order

First rule that fires decides.

**T1. Is the correct answer a specific dated event or announcement?**
"In June 2023 NITI Aayog launched two initiatives", "the measures announced
in the October 2025 policy", "Budget 2024-25 introduced". If removing the
date makes the question unanswerable or ambiguous, PERISHABLE.

**T2. Is the answer a current officeholder, a current rank, or a current
winner/host?** Who is the Deputy Governor now, India's rank this year, this
year's host country. PERISHABLE.

**T3. Everything else is DURABLE.** This includes, explicitly:
- current values, limits, thresholds and rates with no date in the stem
  (E1b) — an aspirant is expected to know the current figure
- annual-edition report themes, findings and structures once published (E2)
- attributed statements, where the attribution is fixed even if the office
  is not (E3)
- scheme and initiative design, purpose and mechanism, whether or not the
  scheme is still running (E4)
- statutes, definitions, structures, mechanisms, fixed history
- "recently"/"launched" framing where the asked fact is what the thing is,
  not when it happened

## Consequence of this reading

Perishable is now narrow — only dated events (T1) and current-holder
questions (T2). Expect the perishable count to fall well below the file of
record's 118, not rise above it. That is the intended effect of E1b: RBI GA
asks current-state questions and aspirants are expected to track current
state, so a moving value is study material, not disposable content.

The cost: a durable-tagged current value goes stale silently. Nothing in the
system flags it. `mock_question_bank` has valid_until and event_anchor_date
but they are only set on the current-affairs pipeline path, not on tagged
PYQs. A staleness mechanism for durable-but-moving GA facts does not exist
and is not created by this rule. Flagged, not solved.