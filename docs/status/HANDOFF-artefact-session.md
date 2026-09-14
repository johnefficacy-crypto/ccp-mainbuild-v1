# Handoff — study artefacts for aspirants

For a fresh session. Everything below is state as of 2026-09-13; nothing here
needs re-deriving or re-checking to start designing.

---

## What you are starting from

The platform holds **8,302 UPSC optional PYQ questions spanning 1980-2026**,
across six subjects and twelve subject-papers, every one tagged to a specific
line of the official syllabus. 1,252 syllabus topics exist across those twelve
papers, and 1,016 of them have at least one question against them.

That is the raw material. But the more useful asset is what was derived from it.

### You know which topics matter, and you can prove it

Every topic carries a **predictability** score and band, computed from 46 years
of recurrence:

| band | topics | what it means |
|---|---:|---|
| `near_certain` | 137 | asked in a large share of years, on a rhythm |
| `likely` | 329 | recurs often enough to expect |
| `occasional` | 575 | shows up |
| `rare` | 265 | thin record of ever being asked |

Plus, per topic: the exact list of years it was asked in, how evenly spaced
those years are, and when it last appeared.

**This is the answer to "which topics deserve an artefact".** You do not have to
guess across 1,252 topics. The 137 near-certain ones are identified, named, and
defensible — and the reasoning is published (see the six blog posts under
`docs/blog/`).

### Where to read it

- `workbench/analysis/predictability.json` — 1,016 topics with year lists,
  scores and bands, grouped by subject-paper. Offline, no DB needed.
- `docs/status/2026-09-12-predictability-axis-design.md` — what the measure is,
  the measurements behind its weights, and what it deliberately is not.
- `exam_topic_coverage` / `exam_topic_score_snapshots` in the DB carry the same
  values live, on phase `f42ffb84-082e-49db-9154-9fd973e8b6e5` (the 2026 Mains
  cycle phase).

---

## The framing that makes this tractable

The instinct is "what artefacts could we build for Sociology". That produces a
list and no priorities.

**The better question: which topics earn an artefact, and what kind does each
one earn?** The first half is answered by predictability. The second half is
the design work.

### Artefact type follows topic SHAPE, not subject

A first pass at the mapping, to be argued with rather than accepted:

| topic shape | artefact | example from the corpus |
|---|---|---|
| a sequence of dated events | timeline | *Indian nationalism: constitutionalism to mass Satyagraha* |
| a spatial distribution | map | *Physiographic regions of India*; *Tribal communities and their distribution* |
| two or more competing positions | comparison table | *Theories of stratification: structural-functionalist, Marxist, Weberian* |
| a named thinker and their concepts | concept card / mindmap | *Max Weber: social action, ideal types, authority, bureaucracy* |
| an enumerable list with detail | ready-reckoner | *Statutory institutions and commissions*; *Constitutional amendments* |
| a process or causal chain | flow diagram | *The budgetary process*; *Policy formulation and implementation* |
| a syllabus unit with many children | roadmap | any macro topic with 8+ microtopics |

If that mapping holds, artefact type is **derivable** from the topic text and
the questions asked under it — which turns 137 bespoke commissions into a
generation problem with review. That is the difference between a feature and a
content project, and it is worth testing early on ten topics before committing
to either.

---

## The honest constraint

**The corpus is questions, not answers.**

You have what UPSC asked, 46 years of it, tagged and scored. You do not have
model answers, source material, or subject content. A mindmap of *Weber's
bureaucratic model* needs substance the platform does not hold.

So each artefact type sits somewhere on this spectrum, and it matters which:

- **Derivable from the corpus.** A timeline of *which years this topic was
  asked and in what form*; a frequency chart; a "what has actually been asked
  here" reckoner. These are honest, unique to you, and buildable today.
- **Derivable from the syllabus.** A roadmap of a unit's microtopics, the
  official wording, how the parts relate. Also honest; thinner.
- **Requires subject content.** A mindmap of Weber's concepts, a map of Harappan
  sites, a comparison of Rawls and Nozick. Real teaching value, and it comes
  from somewhere other than your corpus — generated, licensed or authored, each
  with a different cost and a different trust problem.

The first category is the one nobody else can copy. Worth deciding deliberately
whether the session is about that, or about the third with the corpus only
choosing priorities.

---

## Bring to the session

1. **One exam, one subject to prototype on.** PSIR or Sociology — both are
   commonly chosen and both have clean, well-tagged corpora.
2. **One artefact type done properly, or a sampler across types?** A sampler
   shows range; one type done well shows whether the pipeline works.
3. **Where these live.** A topic page, a downloadable, a study-plan step, the
   blog. Changes what "done" means.
4. **Who authors the substance** for the third category above, if it is in
   scope at all.

## Useful context, briefly

- **Subjects and papers.** Six optionals, two papers each, disjoint syllabi —
  PSIR, Sociology, Anthropology, Public Administration, History, Geography.
  Mathematics and Commerce have no corpus (Mathematics failed OCR; the evidence
  is filed at `workbench/corpus/optionals/upsc-maths-ocr-RAW.json`).
- **Topic counts vary wildly.** Sociology Paper-I has 43 microtopics;
  Anthropology Paper-I has 122. An artefact-per-topic plan means very different
  volumes per subject.
- **An aspirant takes exactly one optional**, two papers of it, worth 500 of
  1,750 Mains marks. Migration 287 (`exam_electives`) added the schema for
  storing that choice; the UI does not exist yet. Artefacts should assume a
  chosen optional, not a browse-everything user.
- **GS is a separate corpus**, 1,209 Mains questions across GS1-4, tagged and
  scored the same way. Everything above applies there too, and GS has 5 subjects
  rather than 12 — a smaller first target if that appeals.
- **The six blog posts** at `docs/blog/upsc-*-what-actually-gets-asked.md` are
  publishable as-is and are the clearest statement of what the data supports.
  Worth reading one before designing anything.
