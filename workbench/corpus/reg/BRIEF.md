# REG-CORPUS builder brief (shared by all builders)

Goal: original, hard, exam-realistic MCQs for SEBI / PFRDA / IFSCA Grade A (Phase I & II) core subjects.
Recent papers moved from textbook recall to APPLICATION: passage-like stems, tables with many figures, close options,
cases traceable in STYLE to ICAI / ICMAI study-material illustrations, Companies Act schedules, AS / Ind AS illustrations.

## Tooling (mandatory)
- Write ONE script: /home/claude/corpus/builders/build_<BATCH>.py. It must `import sys; sys.path.insert(0,'/home/claude/corpus')`
  and use `from reglib import Batch, inr, R, pct, lakh, crore`. Read /home/claude/corpus/reglib.py first.
- Reference example (quality bar and style): /home/claude/build_costing_pilot.py and its output
  /home/claude/reg_costing_marginal_pilot_review.md. Match that bar.
- Every numeric correct answer AND every numeric distractor is COMPUTED in Python from the stated figures. Add `assert`s
  on key values you hand-check. Never type a computed number by hand into an option.
- Each wrong option = a NAMED error (wrong base, sign reversed, missed adjustment, confused concept, outdated rule...).
  No random numbers. Options must be close/plausible.
- Tag each question with an exact microtopic slug from your list file (/home/claude/corpus/lists/<file>.tsv).
- Run the script; fix until it runs clean. Output lands in /home/claude/corpus/out/<BATCH>.json + _review.md.

## Mix
- Level rubric: L1 recall (~20%), L2 one-step application (~30%), L3 multi-step / table / statement-combination (~30%),
  L4 case or passage stem with close distractors (~20%). L4 = case sets: one fictional case stem (use `group=` key,
  repeat the stem text in each question of the set), 3-5 questions per case. At least 2 case sets per batch.
- Kinds: numerical, conceptual, statement ("Which of the statements is/are correct? 1..3" with options like
  "1 and 2 only"), assertion-reason, match-the-following (render as markdown table in stem), case.
- Use markdown tables in stems for data (renderer will support GFM tables + KaTeX `$..$`). Indian formats (₹, lakh, crore).
- Cover as many microtopics as possible (every microtopic ≥1, heavier weight on high-yield ones). Hit your QUOTA exactly.

## Integrity
- ORIGINAL text only. Do NOT copy ICAI/ICMAI/textbook questions or wording; use fictional entities and your own figures.
  Statutory text (Companies Act 2013, Rules, Schedules, notified Ind AS) may be paraphrased accurately.
- Law / rate / threshold / date facts: only use provisions you are confident of as of mid-2026. Set verify_fact=True and
  put the section/rule/standard in ref= for EVERY question whose key depends on a statutory number, threshold, rate,
  date, or regulator rule. If unsure a fact is current, don't use it.
- No current-affairs figures (budget numbers, recent repo rate etc.) unless given inside the stem as data.

## Report back (short)
Batch name, count, level split, microtopics covered/total, number of verify_fact items, any microtopics skipped and why,
and any question you are least confident in (id + reason). Don't paste questions.
