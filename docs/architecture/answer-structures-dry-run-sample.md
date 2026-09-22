# Answer structures — sample dry-run output

Three fixture questions (`app/backend/tests/fixtures/answer_structures/questions.jsonl`). No model call and no database write was made to produce this file.

## 1. Plain dry run (default mode)

```
python scripts/generate_answer_structures.py \
  --questions-file app/backend/tests/fixtures/answer_structures/questions.jsonl
```

Shows the prompt inputs each question would send and the worst-case cost that the `--max-usd` cap checks before every call.

### `f0000000-0000-4000-8000-000000000001` — worst case $0.1047

```
Question:
Critically examine the role of the Governor in the working of cooperative federalism in India.

Context:
- Subject: General Studies
- Paper: GS2
- Syllabus section: Indian Constitution
- Microtopic: Role of the Governor
- Official syllabus line: Functions and responsibilities of the Union and the States, issues and challenges pertaining to the federal structure
- Marks: 15
- Word limit: 250
- Year: 2023
- Expected length: about 250 words, so scale the number of body points to what fits.
```

### `f0000000-0000-4000-8000-000000000002` — worst case $0.1046

```
Question:
Discuss the challenges of groundwater depletion in India and suggest measures for its sustainable management.

Context:
- Subject: General Studies
- Paper: GS3
- Syllabus section: Environment
- Microtopic: Groundwater management
- Official syllabus line: Conservation, environmental pollution and degradation, environmental impact assessment
- Marks: 10
- Word limit: 150
- Year: 2022
- Expected length: about 150 words, so scale the number of body points to what fits.
```

### `f0000000-0000-4000-8000-000000000003` — worst case $0.1047

```
Question:
What do you understand by probity in governance? Illustrate how it can be strengthened in public service delivery.

Context:
- Subject: General Studies
- Paper: GS4
- Syllabus section: Ethics
- Microtopic: Probity in governance
- Official syllabus line: Probity in Governance: Concept of public service; philosophical basis of governance and probity
- Marks: 10
- Word limit: not known
- Year: 2021
- Expected length: about 150 words, so scale the number of body points to what fits.
```

## 2. Replay dry run (canned model output through the real validator + lint)

```
python scripts/generate_answer_structures.py \
  --questions-file app/backend/tests/fixtures/answer_structures/questions.jsonl \
  --responses app/backend/tests/fixtures/answer_structures/responses.json
```

### `f0000000-0000-4000-8000-000000000001` — dry_run_validated

- **Directive:** Critically examine
- **Demand:** Weigh how the Governor's constitutional role both enables and strains Centre–State cooperation, ending in a balanced verdict.
- **Word budget:** {"total": 250, "intro": 40, "body": 170, "conclusion": 40, "basis": "word_limit"}
- **Body points:**
  - `p1` Constitutional position and discretionary powers — _support with:_ Relevant constitutional articles on appointment, discretion and assent
  - `p2` Ways the office supports cooperative federalism — _support with:_ Instances of the Governor acting as a bridge in Centre–State communication
  - `p3` Friction points: delays in assent, government formation, reports under Article 356 — _support with:_ Recent Supreme Court judgments on the Governor's assent to State Bills
  - `p4` Commission and judicial recommendations on the office — _support with:_ Recommendations of the Sarkaria and Punchhi Commissions
  - `p5` Reforms to align the office with cooperative federalism — _support with:_ Proposals on time-bound assent and consultation with the Chief Minister in appointment
- **Pitfalls:** Writing only criticism — 'critically examine' needs both sides.; Listing articles without linking them to cooperative federalism.; Quoting figures on Article 356 use without being sure of them.
- **Model uncertainty (reviewer-only):** Whether the examiner expects the 2023 judgment on assent specifically is unclear; the point is phrased as an evidence type.
- **Fabrication lint (reviewer-only):** named_case in body_points[3].example: “Bommai v. Union”

### `f0000000-0000-4000-8000-000000000002` — dry_run_validated

- **Directive:** Discuss
- **Demand:** Two parts: the challenges groundwater depletion poses, and practical measures for sustainable management.
- **Word budget:** {"total": 150, "intro": 20, "body": 110, "conclusion": 20, "basis": "word_limit"}
- **Body points:**
  - `p1` Causes of depletion: over-extraction for irrigation, free or subsidised power, water-intensive cropping — _support with:_ Central Ground Water Board assessments of over-exploited blocks
  - `p2` Consequences: falling water tables, quality contamination, rural distress — _support with:_ Recent data on arsenic and fluoride contamination in groundwater
  - `p3` Governance gaps: groundwater as an easement right attached to land — _support with:_ Legal status of groundwater and model groundwater bills
  - `p4` Measures: demand-side (crop diversification, micro-irrigation, power pricing) and supply-side (recharge, watershed works) — _support with:_ Government schemes on participatory groundwater management
- **Pitfalls:** Only listing schemes without linking them to causes.; Ignoring the legal ownership issue.; Inventing percentages of depletion.
- **Model uncertainty (reviewer-only):** none
- **Fabrication lint (reviewer-only):** none

### `f0000000-0000-4000-8000-000000000003` — dry_run_validated

- **Directive:** Explain and illustrate
- **Demand:** Define probity in governance, then show with illustrations how it can be strengthened in public service delivery.
- **Word budget:** {"total": 150, "intro": 20, "body": 110, "conclusion": 20, "basis": "marks"}
- **Body points:**
  - `p1` Meaning of probity and how it differs from legality and efficiency — _support with:_ Standard definitions from ethics texts
  - `p2` Why probity matters for service delivery: trust, equity, reduced leakages — _support with:_ Instances where lack of probity distorted delivery
  - `p3` Institutional measures: citizen charters, social audits, RTI, grievance redress — _support with:_ Examples of social audits in rural employment schemes
  - `p4` Individual measures: codes of conduct, ethics training, leading by example — _support with:_ Recommendations of the Second Administrative Reforms Commission on ethics in governance
  - `p5` Technology: e-governance and direct benefit transfer reducing discretion — _support with:_ E-governance examples reducing face-to-face discretion
- **Pitfalls:** Defining probity only as absence of corruption.; No illustrations despite the directive 'illustrate'.
- **Model uncertainty (reviewer-only):** Directive combines 'what do you understand' and 'illustrate'; recorded as 'Explain and illustrate'.
- **Fabrication lint (reviewer-only):** none

Summary: `generated=3 failed=0 written=0 cost_usd=0.0` (replay tokens cost nothing).
