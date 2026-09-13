# SCORE-MAINS-01 — make `exam_priority_score` discriminate on descriptive Mains papers

## PRIMING

Read:

1. `app/backend/app/exam_intelligence/score_snapshots.py` — the whole file,
   `compute_exam_topic_scores` in particular
2. `app/backend/app/exam_intelligence/coverage_derivation.py` — the consumer
3. `docs/status/2026-09-10-mains-optionals-strategy-rev3.md` and
   `2026-09-11-mains-optionals-strategy-rev3.1.md`

On 2026-09-11 the optional corpus completed the full evidence chain: 16 papers
verified, 4,038 questions loaded with 3,924 verified, 3,924 primary tags
verified, and 1,227 score snapshots computed with 0 errors. The chain works.
**The scores it produces are unusable.**

Live numbers from that run, UPSC CSE Mains, the twelve optional subjects:

| topic | questions | exam_priority_score | is_high_yield |
|---|---:|---:|---|
| Temple architecture, sculpture and painting | 24 | 10.25 | false |
| Beginning of agriculture: Neolithic/Chalcolithic | 23 | 10.24 | false |
| Formation of states: the Mahajanapadas | 19 | 10.20 | false |
| Panchayati Raj institutions (PSIR P1) | 14 | 10.15 | false |

A topic asked 24 times in nine years scores 1% above one asked 14 times, and
**`is_high_yield` is false on every one of 937 optional snapshots.**

The cause is visible in `score_components`:

```
{"evidence_quality": 1, "coverage_component": 0, "frequency_component": 0.005}
```

Only `frequency_component` varies, and it varies in the third decimal place.

---

## PREFLIGHT — STOP gates

**G1.** Quote the three component lines and the composite from
`compute_exam_topic_scores`, with `path:line`. Confirm by reading that:

- `freq_component = primary_counts[tid] / total_primary`, where `total_primary`
  is **every verified primary tag on the whole exam**
- `evidence_quality = min(count / 10.0, 1.0)` — saturates at 10 questions
- `cov_component` reads locked `exam_topic_coverage` rows with
  `source_basis != 'evidence_derived'`
- `is_high_yield` requires `freq_component > 0.15`

**G2.** Compute, from live data or by reasoning against the counts above, the
maximum `freq_component` any Mains topic can reach. UPSC CSE Mains has ~5,133
verified primary tags across ~1,252 topics. State whether `> 0.15` is reachable
**at all** on that distribution. If it is not, say so plainly — that is the
finding, and it means the high-yield flag has never fired for Mains and cannot.

**G3.** Establish what Prelims looks like on the same measures: how many
verified primary tags, how many topics, what the top `freq_component` values
are, and whether `is_high_yield` currently fires there. **You cannot change
Prelims behaviour without knowing what it currently is.** If you cannot query
live data, say so and derive what you can from the code and the repo's status
docs rather than assuming.

**G4.** List every consumer of `exam_topic_score_snapshots` and of
`exam_topic_coverage.exam_priority_score` / `.is_high_yield`. The planner,
report cards, PYQ readiness and the aspirant-facing surfaces are candidates.
A rescale changes what they rank. Name them before changing anything.

---

## SINGLE FORCED STRATEGY

One PR, draft, auto-merge off. Branch: `fix/score-model-mains-scale`.

### The problem, stated as a modelling question

The model assumes a topic can be a meaningful *fraction of the exam's
questions*. That holds for Prelims: 100 questions a paper, a topic recurring
across years can plausibly reach several percent. It does not hold for
descriptive Mains: 1,252 topics share ~5,133 questions, so no topic exceeds
0.5% and the frequency signal is compressed into noise.

`evidence_quality` makes it worse rather than better: it saturates at 10
questions, so every topic asked 10 or more times contributes an identical 10
points — which is precisely the band where discrimination matters most.

### Decisions, locked

- **D1. Prelims and every other exam must be unchanged.** Same inputs, same
  outputs, bit for bit. Prove it with a test that pins current Prelims scores
  and passes before and after.
- **D2. Do not add a config knob per exam.** A magic number tuned per exam is
  how this becomes unmaintainable. The scale should follow from a property of
  the data — question count per paper, topic count per subject, or similar —
  not from a hardcoded exam id.
- **D3. `is_high_yield` must be reachable on Mains** and must mean something:
  a topic asked far more than its peers. It must not become true for
  everything, which would be as useless as false for everything.
- **D4. Do not change what counts as evidence.** Verified primary tags on
  verified questions on verified papers. The gates are correct; only the
  arithmetic on top of them is wrong.
- **D5. Existing locked snapshots are not rewritten** by this change. If a
  recompute is needed to benefit, say so; do not silently mutate locked rows.

### Candidate directions, not prescriptions

You are expected to choose and justify. Some starting points:

- Normalise frequency **within the topic's own subject or paper** rather than
  the whole exam. "Panchayati Raj is 14 of PSIR Paper-I's 392 questions" is a
  meaningful share; "14 of the exam's 5,133" is not.
- Replace the saturating `evidence_quality` with something that keeps
  discriminating above 10 — a log, or a percentile against sibling topics.
- Make `is_high_yield` relative rather than absolute: top decile within its
  subject, say, rather than a fixed fraction of the whole exam.

Whatever you choose, the top of the optional list should separate visibly: a
24-question topic must outrank a 14-question one by a margin a human would act
on, and both must outrank a 1-question topic decisively.

---

## BLAST RADIUS

`score_snapshots.py` and its tests. `coverage_derivation.py` only if the change
genuinely requires it — say why if so. Anything else touched must be reverted.

## OUT OF SCOPE

- Recomputing or locking any snapshot. That is an operator action.
- The 937 optional drafts currently sitting unlocked — they exist precisely
  because the scores were not trustworthy; leave them.
- Difficulty. `observed_difficulty` is null on every Mains descriptive question
  by design; the Prelims traceability rubric does not transfer and a
  predictability axis has not been designed.
- The review gates, the tagging, the corpus.

## VALIDATION

- A test pinning current Prelims output that passes **before and after** — D1
  is the whole constraint and an untested claim of it is worthless.
- A test showing Mains topics at 24, 14 and 1 questions now separate, with the
  expected ordering and a stated minimum margin.
- A test that `is_high_yield` fires for a plausibly high-yield Mains topic and
  does not fire for a median one.
- Cite `path:line` at head for every claim about existing behaviour.
- BE GitHub Actions green.

## OUTPUT / PUBLICATION

Report:

1. G1–G4 answers, with the quoted lines and the live numbers
2. The modelling change in one paragraph: what the score now measures and why
   that is the right thing for a descriptive paper
3. Before/after scores for the four topics in the table above
4. Proof Prelims is unchanged
5. Whether a recompute is needed for the change to take effect, and what an
   operator would have to run

You are offline: no GitHub egress, no `gh`, no push. Commit locally and stop.
