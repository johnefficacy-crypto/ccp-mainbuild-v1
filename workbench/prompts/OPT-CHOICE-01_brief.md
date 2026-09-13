# OPT-CHOICE-01 — "my optional": the missing product concept

## THE SITUATION

Twelve optional subjects are now live with 8,302 questions and a published
topic ranking. The PYQ Explorer's Subject dropdown is built from the data, so
an aspirant sees **seventeen entries in one flat list**: GS I-IV plus all
twelve optionals.

A PSIR aspirant sees Anthropology, Geography, History, PubAd and Sociology
beside their own subject. Nothing in the product knows which one is theirs.

**This is not a bug.** No code is wrong and nothing is broken. It is a missing
product concept — *the user's chosen optional* — and it cannot be specified
until four questions are answered by a person, not an agent.

## WHY IT MATTERS MORE THAN IT LOOKS

Every UPSC Mains aspirant takes all four GS papers and **exactly one** optional,
two papers of it. That is not a preference, it is the exam's structure. So:

- Eleven of twelve optional subjects are noise for any given user, permanently.
- The optional is 500 of 1,750 Mains marks — 28% — so it is not a minor
  filtering nicety; it is a third of what the platform should be planning for.
- A study plan that ranks topics across all twelve optionals is not merely
  cluttered, it is wrong: it would allocate time to subjects the user will
  never sit.
- The choice is made once and rarely changed. It is closer to an enrolment
  fact than to a filter setting.

## THE FOUR QUESTIONS

### 1. Where does the choice live?

Candidates, each with a different consequence:

- **User profile.** Simple, but wrong if a user ever prepares for two exams
  with different optional lists.
- **Per-exam enrolment.** Correct in principle — the optional belongs to "my
  UPSC CSE preparation", not to "me" — but requires an enrolment object that
  may not exist yet.
- **Study plan.** Ties the choice to a plan's lifetime, which is wrong if the
  plan is regenerated.

Check what already exists before inventing anything: there may be an exam
enrolment or a plan-scoped subject preference that fits.

### 2. Can it change mid-preparation, and what happens to progress?

Aspirants do switch optionals — usually early, occasionally after a failed
attempt. If mastery, coverage and plan progress are keyed to the old subject's
topics:

- Is the old progress kept and hidden, or discarded?
- Does the plan regenerate, and does the user lose their schedule?
- Is there a confirmation step, given how much work a switch discards?

An answer of "switching is rare, so we will handle it manually" is acceptable
**if it is written down**. Silently orphaning a user's progress is not.

### 3. Do the other eleven disappear, or stay browsable?

Two defensible positions:

- **Hard filter.** The user sees only their optional. Cleanest, but blocks the
  aspirant who is still choosing — and choosing well is a real need the
  platform could serve, since it now has 45 years of question data per subject.
- **Soft default.** Their optional is pre-selected everywhere, the others are
  reachable. More complex, but supports the pre-choice browsing case.

Note that the second is strictly more work and the first is reversible.

### 4. Does GS stay unfiltered while optionals are filtered?

Asymmetric behaviour needs stating explicitly or it reads as a bug: every
aspirant takes all four GS papers, so GS should never be filtered, while
optionals should almost always be. A single "subjects I am studying" concept
applied uniformly would get GS wrong.

## WHAT IS ALREADY IN PLACE

The backend is further along than the UI:

- `GET /api/exam-intelligence/exams/{slug}/pyqs` already accepts `subject_id`
  and `topic_id`.
- M9-rev3 already requires every aspirant-facing read to be subject-scoped, and
  names nine reads that are not — that work is needed regardless of this
  feature and would make it safe.
- Subjects carry stable slugs (`upsc-cse-mains-opt-psir-p1` / `-p2`), so a
  chosen optional is two subject ids, not one. **Any design that stores a
  single subject id is wrong** — Paper-I and Paper-II are separate subjects
  with disjoint syllabi (rev2 M2).

## WHAT TO DO WITH THIS

Answer the four questions. Then the implementation ticket is small: store the
choice, default the filters, and decide the GS asymmetry. The hard part is the
decisions, not the code.

Two things to resolve alongside, since they surface the moment optionals are
filtered:

- **Subject naming.** The dropdown shows `subject_name` — "PSIR Paper-1
  (Optional)", "Sociology Paper-2 (Optional)". Fine in an admin list;
  clunky as a user-facing label once a user has chosen PSIR and sees two
  entries for it.
- **Explorer card count.** M1 chose the B2 paper model partly to keep the card
  list at 41 rather than 165. There are now 47 optional papers across two
  corpus halves. Worth confirming what the summary endpoint returns for a
  single chosen optional before assuming it is manageable.
