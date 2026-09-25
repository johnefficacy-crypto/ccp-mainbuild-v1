# QRE-CORPUS builder brief (Quant, Reasoning, English, static GK) — shared across exams for topic grinding

## Tooling (mandatory)
- ONE builder: /home/claude/corpus2/builders/build_QRE-<BATCH>.py (+ optional part modules <batch>_p1.py… each add_all(B)).
  Paths repo-relative: `import os as _os, sys; _REG=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))); sys.path.insert(0,_REG)`
  then `from reglib import Batch, inr, R, pct, lakh, crore`. NO /home/claude paths in builders. Read /home/claude/corpus2/reglib.py first.
- `B = Batch("QRE-<BATCH>", "<subject-slug>", "<PREFIX>")`; every `B.add(..., tier="foundation"|"officer")`.
- Quality reference: /home/claude/build_costing_pilot.py and /home/claude/reg_costing_marginal_pilot_review.md.
- Microtopics: ONLY slugs in /home/claude/corpus2/lists/<BATCH>.tsv. Exactly 15 per microtopic: 5 foundation + 10 officer.
- Run the builder until clean. Then the length-cue check must print 0:
  python3 -c "import json;q=json.load(open('/home/claude/corpus2/out/QRE-<BATCH>.json'))['questions'];print(sum(1 for x in q if (lambda L,c:L[-1]>=25 and c==L[-1] and c>1.15*L[-2])(sorted(len(o['text']) for o in x['options']),[len(o['text']) for o in x['options'] if o['is_correct']][0])))"

## Tiers and levels
- foundation = SSC CGL/CHSL, IBPS/SBI Clerk, RRB level: direct, speed-oriented. Levels L1–L2 (a few L3).
- officer = IBPS/SBI PO, RBI Grade B, SEBI/NABARD/IFSCA Phase I level: multi-step, disguised, close options. Levels L2–L4.
- L4 = case sets (use group=; repeat the identical shared stimulus text at the top of each question in the set, then "\n\n" + the question).
  Use case sets for: puzzles, seating arrangements, DI (table/bar/pie/caselet — give data as markdown tables), RC passages, multi-blank cloze,
  input-output machines, family-tree puzzles. 3–5 questions per set.

## Correctness (non-negotiable)
- Quant: every key and distractor computed in Python; asserts on keys. Distractors = named errors (wrong base, sign, missed step, formula mix-up).
- Reasoning puzzles / seating / scheduling / blood relations / ranking / inequalities / syllogisms / coding / input-output / direction:
  write a small SOLVER in the builder (itertools brute force, set-model enumeration for syllogisms) and ASSERT the clue set yields a UNIQUE
  solution and that exactly one option is correct. Data-sufficiency: assert sufficiency per statement by enumeration.
- English: ORIGINAL passages and sentences only (no copied text from books, newspapers or coaching material). Exactly one defensible answer;
  follow standard Indian competitive-exam conventions (British spelling). Error spotting: exactly one erroneous segment, or "No error" when keyed.
  Vocabulary: standard dictionary senses.
- Static GK: durable facts only (history, polity/Constitution, geography, science, institutions, awards' nature/history, books-authors classics,
  international organisations' HQ/founding). NO current affairs (who won 2025/2026 events, current office-holders, latest scheme figures).
  verify_fact=True + ref=<source type, e.g. "Constitution of India, Art. 21" / "NCERT Class 11 Geography"> on EVERY GK question.
  Skip any fact you are not sure is still true as of 2026.
- Original wording; no text reproduced from PYQ papers or books.
- Kinds allowed: numerical, conceptual, statement, assertion-reason, match (markdown table), case. No figure/image questions.

## Report (short)
Count, tier split, level split, case sets, microtopics covered/total, any skipped microtopic and why, least-confident ids.
