# PFRDA Grade A — Explanation Draft: Review Notes (EXPL-04)

Worksheet: `workbench/worksheets/PFRDA-EXPLANATIONS-DRAFT.json` — 142 rows, one per question in
`workbench/sources/pfrda-explanations-input.json`. Every row is authored from subject knowledge and the
question's own text. No text is extracted from any third-party source. Nothing here is reviewed.

Conventions follow EXPL-01 (SEBI) and EXPL-02 (IFSCA), including the EXPL-02-REV posture on keys: a key
that is defensible on any reasonable reading is accepted, with the competing reading recorded in `key_note`
rather than raised to a flag. There is therefore no `AMBIGUOUS` row in this batch by design.

## 1. Key verdicts

| Verdict | Count | `final_answer_option_id` |
|---|---|---|
| AGREE | 136 | set = input `correct_option_id` |
| DISPUTED | 0 | null — awaits a human key decision |
| AMBIGUOUS | 0 | null — awaits a human key decision |
| UNANSWERABLE | 6 | null — awaits a human key decision |
| **Total** | **142** | **136 set** |

### 1.1 DISPUTED — the keyed answer is, in my judgement, wrong

None.

### 1.2 AMBIGUOUS

None. Per the EXPL-02-REV posture, every key defensible on some reasonable reading is accepted as AGREE and
the competing reading is recorded in `key_note`. Those rows are listed in §5.

### 1.3 UNANSWERABLE — cannot be answered as written

6 rows, all of them reasoning questions that belong to a shared premise set which is absent from
the input file. Each carries a stand-alone stem ("How many people celebrate between B and the one who has
Acer?") with no arrangement, no clue list and no input row to work from. Nothing in the record makes the keyed
answer derivable, so no final answer is asserted on any of them. They are enumerated in §2; the missing
stimulus is a corpus defect to be scoped, not something this draft can repair.

#### 2025 Q7 · general-intelligence-reasoning · `90e0a40c-336f-48fd-9c8c-f4f40abda007`

**Stem.** How many people celebrate between B and the one who Acer?

- **Topic:** Category and attribute matching puzzle
- **Keyed option:** (a) Three
- **Reason.** The shared premise set for this category-and-attribute puzzle is missing from the input file. Without it the keyed answer of 'Three' cannot be verified or refuted, so no final answer is asserted. The stimulus must be supplied before this item can be reviewed.

#### 2025 Q8 · general-intelligence-reasoning · `1323449c-67e2-4f2b-afce-aed87cbba863`

**Stem.** Which of the following is correct?

- **Topic:** Category and attribute matching puzzle
- **Keyed option:** (c) A celebrates just after D
- **Reason.** The shared premise set for this category-and-attribute puzzle is missing from the input file, so the keyed statement 'A celebrates just after D' cannot be verified. No final answer is asserted.

#### 2025 Q9 · general-intelligence-reasoning · `9493f208-b993-4f1c-8d56-404cbf702e47`

**Stem.** Which of the following laptops has the one who celebrates on 13th May?

- **Topic:** Category and attribute matching puzzle
- **Keyed option:** (e) None of these
- **Reason.** The shared premise set is missing from the input file, so the keyed 'None of these' cannot be verified. No final answer is asserted.

#### 2025 Q10 · general-intelligence-reasoning · `9711c2d3-6fb2-4f64-bc6c-94bec3f53344`

**Stem.** Which of the following combinations is true with respect to the final arrangement?

- **Topic:** Category and attribute matching puzzle
- **Keyed option:** (e) All are correct
- **Reason.** The shared premise set is missing from the input file, so the keyed 'All are correct' cannot be verified. No final answer is asserted.

#### 2025 Q11 · general-intelligence-reasoning · `023df684-a039-49a5-9934-cfe8b7e5a961`

**Stem.** How many steps are required to obtain the final output?

- **Topic:** Step count and intermediate-step questions
- **Keyed option:** (b) Four
- **Reason.** The input row and the machine's rule are missing from the input file, so the keyed count of four steps cannot be verified. No final answer is asserted.

#### 2025 Q15 · general-intelligence-reasoning · `ffb6d5a3-0888-4f0a-90cd-f1ec4e3e65a7`

**Stem.** Which among the following is the fifth element from the right end in the final step?

- **Topic:** Shifting and rearrangement machine
- **Keyed option:** (e) 48
- **Reason.** The input row and the intermediate steps are missing from the input file, so the keyed answer of 48 cannot be verified. No final answer is asserted.

## 2. Missing reasoning stimuli (flagged, not fixed)

The six UNANSWERABLE rows fall into three premise sets. Enumerated here so the gap can be scoped; no stimulus
row is created by this batch.

| Premise set | Rows | What is missing |
|---|---|---|
| Category-and-attribute puzzle (people, birthday dates, laptop brands) | 2025 Q7, Q8, Q9, Q10 | The clue list that fixes the date order and the brand assignment. |
| Input-output machine — step count | 2025 Q11 | The input row and the worked steps. |
| Shifting-and-rearrangement machine | 2025 Q15 | The input row and the intermediate steps. |

The other three reasoning rows — the two syllogisms (2025 Q16, Q17) and the critical-reasoning item (2025 Q20) —
are self-contained and are answered in full.

## 3. Current-affairs and circular-set parameters

Classified by one test: could a candidate reason to the answer, or only recall it? `current_affairs = yes` rows
give the durable mechanism — what the scheme, body or instrument is and how the parameter works — and state the
current figure once. Where a distractor is an arbitrary number, the rationale says so rather than inventing a
distinction.

6 rows are marked `current_affairs = yes`:

| Year/Q | Subject | Parameter | Why it is treated this way |
|---|---|---|---|
| 2022 Q2 | finance | Income-distance weight of 45% in the 15th Finance Commission formula | Set by one Commission's report and replaced by the next; the durable content is what income distance measures and why it carries the largest weight. |
| 2022 Q3 | finance | ₹50 lakh minimum annual social spending for SSE registration | A SEBI eligibility threshold, alterable by circular; the durable content is what a Social Stock Exchange is and why a size threshold exists. |
| 2022 Q6 | finance | SEBI's August 2022 clarification on AIF overseas investment | A dated regulatory action; the durable content is what an AIF is and how its three categories work. |
| 2022 Q7 | finance | ₹1,000 crore asset threshold in NBFC scale-based regulation | A threshold fixed by the RBI framework; the durable content is the four-layer structure and what puts a company in each. |
| 2025 Q3 | finance | RBI's FX intervention during the Russia–Ukraine war | A dated episode; the durable content is how spot and forward intervention works and what a volatility-management objective means. |
| 2025 Q5 | pension-sector | APY contribution amounts of ₹210 / ₹626 / ₹1,239 | Read off the official APY contribution chart rather than calculated; the durable content is why contributions rise with entry age and why paying in advance costs slightly less. |

## 4. Tag defects (flagged, not fixed)

`tag_suspect = yes` on 5 rows. No retagging has been done and no `topic_name` was modified.

| Year/Q | Subject | Current `topic_name` | Question | Suggested topic |
|---|---|---|---|---|
| 2022 Q3 | finance | Financial Inclusion Index and schemes | A bank giro transfer is a method of transferring money by instructing a bank to directl... | Topic should be Direct Benefit Transfer and payment systems, not the Financial Inclusion Index and schemes. The question is about the mechanism of a giro transfer, not about an index. |
| 2022 Q6 | pension-sector | Status and coverage of the pension sector | is a biometric enabled Aadhaar-based Digital Life Certificate for pensioners. Pensioner... | Topic should be pension disbursement and life certificates (Jeevan Pramaan), not the status and coverage of the pension sector. The question is about a specific disbursement facility, not about coverage. |
| 2022 Q6 | pension-sector | PFRDA Act 2013 — powers and functions | Which of the following portal acts as grievances redressal cell for the pensioners? Opt... | Topic should be grievance redressal under NPS (CGMS and the Ombudsman), not the powers and functions of the PFRDA Act 2013. The question asks about a redressal portal, not a statutory power. |
| 2025 Q2 | pension-sector | PFRDA Act 2013 — powers and functions | As per PFRDA (Redressal of Subscriber Grievance) Regulations, 2015, every intermediary ... | Topic should be the PFRDA (Redressal of Subscriber Grievance) Regulations, 2015, not the powers and functions of the PFRDA Act 2013. The question is about a regulation-level service timeline. |
| 2025 Q2 | economics | Measurement methods — income, expenditure, product | Manufacturing comes under which of the following sectors of the economy? | Topic should be the sectors of the economy (primary, secondary, tertiary), not the measurement methods for national income. The question does not touch the income, expenditure or product method. |

## 5. Rows carrying a `key_note`

28 rows carry a `key_note`. These record a competing reading that was set aside, a question defect
that does not change the answer, or a figure that should be checked against a live source before publication.

### 5.1 Low-confidence rows

11 rows are `draft_confidence = low`. Each is listed with its reason.

- **2022 Q4 · pension-sector · `262df99e-cb13-430d-8677-4b91d1f7c893`** — Under Atal Pension Yojana, if a subscriber wants to change the tenure and mode of auto debit facility, then he or she can do so, how many times in ...
  - Keyed: (e) Only once in a year in any month
  - Reason: On the original scheme rules the answer was April, and older study material still says so. The key follows the relaxed position, under which the once-a-year change can be made in any month. A reviewer should confirm which vintage the paper intended.
- **2022 Q6 · finance · `52d10634-cf9a-47f7-88d9-7b816a5eacdf`** — In August 2022, SEBI has allowed Alternate investment Funds (AIF) are now allowed to invest in
  - Keyed: (c) Overseas companies
  - Reason: The keyed answer refers to a specific SEBI clarification of August 2022; the dated fact is accepted as stated in the question.
- **2022 Q8 · management · `cd3fb691-9354-4f89-b012-c7f5be94688b`** — Identify the role of the leader, wherein the leader established a two-way communication between Management and employees and the manager motivates ...
  - Keyed: (d) Link Building
  - Reason: The options use labels that are not standardised across texts, so the choice rests on the description in the stem rather than on a settled taxonomy.
- **2025 Q3 · pension-sector · `35e9be36-c2e8-40da-8c5a-3056f0ce80f3`** — As per the PFRDA (Redressal of Subscriber Grievance) Regulations, 2015 (as amended), the NPS Trust must resolve or reply to a grievance received fr...
  - Keyed: (c) 21 days
  - Reason: The 21-day figure for the NPS Trust is a regulation-level service timeline that has been amended over time. The key is accepted, but the current text of the 2015 Regulations should be checked before publication.
- **2025 Q7 · pension-sector · `3348c013-b514-4511-a14e-83b5bf063dc8`** — Upon making a contribution to your NPS account, how many working days does it typically take for the amount to reflect in your account?
  - Keyed: (b) 2 working days
  - Reason: This is an operational service timeline rather than a statutory one and has shortened as the process has been digitised; it should be checked against the current position before publication.
- **2025 Q7 · general-intelligence-reasoning · `90e0a40c-336f-48fd-9c8c-f4f40abda007`** — How many people celebrate between B and the one who Acer?
  - Keyed: (a) Three
  - Reason: The shared premise set for this category-and-attribute puzzle is missing from the input file. Without it the keyed answer of 'Three' cannot be verified or refuted, so no final answer is asserted. The stimulus must be supplied before this item can be reviewed.
- **2025 Q8 · general-intelligence-reasoning · `1323449c-67e2-4f2b-afce-aed87cbba863`** — Which of the following is correct?
  - Keyed: (c) A celebrates just after D
  - Reason: The shared premise set for this category-and-attribute puzzle is missing from the input file, so the keyed statement 'A celebrates just after D' cannot be verified. No final answer is asserted.
- **2025 Q9 · general-intelligence-reasoning · `9493f208-b993-4f1c-8d56-404cbf702e47`** — Which of the following laptops has the one who celebrates on 13th May?
  - Keyed: (e) None of these
  - Reason: The shared premise set is missing from the input file, so the keyed 'None of these' cannot be verified. No final answer is asserted.
- **2025 Q10 · general-intelligence-reasoning · `9711c2d3-6fb2-4f64-bc6c-94bec3f53344`** — Which of the following combinations is true with respect to the final arrangement?
  - Keyed: (e) All are correct
  - Reason: The shared premise set is missing from the input file, so the keyed 'All are correct' cannot be verified. No final answer is asserted.
- **2025 Q11 · general-intelligence-reasoning · `023df684-a039-49a5-9934-cfe8b7e5a961`** — How many steps are required to obtain the final output?
  - Keyed: (b) Four
  - Reason: The input row and the machine's rule are missing from the input file, so the keyed count of four steps cannot be verified. No final answer is asserted.
- **2025 Q15 · general-intelligence-reasoning · `ffb6d5a3-0888-4f0a-90cd-f1ec4e3e65a7`** — Which among the following is the fifth element from the right end in the final step?
  - Keyed: (e) 48
  - Reason: The input row and the intermediate steps are missing from the input file, so the keyed answer of 48 cannot be verified. No final answer is asserted.

### 5.2 Question defects that do not change the answer

| Year/Q | Subject | Defect |
|---|---|---|
| 2022 Q1 | pension-sector | Options (b) and (d) are both printed as '65% of the purchase price', so the item offers four distinct choices rather than five. The key, 75%, is unaffected. |
| 2025 Q2 | commerce-accountancy | Options (b) and (c) are both printed as '1:1', so the item offers four distinct choices rather than five. The key, 1.5:1, is unaffected. |
| 2025 Q5 | economics | Option (e) reads 'High Income Costing', which appears to be a corruption of 'High Income'. Read literally it is a second option that is not a World Bank category, which would give the item two defensible answers. |

### 5.3 Other rows with a competing reading recorded

- **2022 Q1 · pension-sector · `e8f71c16-eb41-4024-a4bf-e312114cec39`** — A settlement timeline of this kind is fixed administratively and has been compressed over time, so it should be checked against the current PFRDA position before publication.
- **2022 Q3 · management · `bcb64165-9825-4af2-9345-7ff490ad1f10`** — Delegation and autonomy sit close together, and an argument could be made for delegation. The key follows the narrower sense of freedom within one's own expertise, which is what the stem describes.
- **2022 Q4 · economics · `27692a8a-ed88-4a53-89fb-78c0d52b53ba`** — The stem speaks of a rightward shift of 'IS-LM' together, which is loose — a change in the money supply moves the LM curve, not both. The key is the only option that shifts either curve rightwards, so it is accepted.
- **2022 Q5 · finance · `0f0f533c-ab2a-49e1-8c49-9c284cc7f43d`** — The stem sets up the account through Bank of India and then asks about Bank of Baroda's account, which makes the perspective harder to follow than it needs to be. On the natural reading — a third party's account — 'loro' is right, and the key is accepted.
- **2022 Q6 · management · `f6497a4d-5801-445a-be78-9a2332088d1e`** — The integration of classical structure with behavioural science is often labelled the neoclassical school, which is not among the options. Of those offered, modern theory is the only one that describes an integration, and the key is accepted on that basis.
- **2022 Q6 · companies-act · `693b995f-c370-48a3-9cf2-f55aaca4c237`** — The keyed 'more than 10%' matches the post-2019 threshold. Material published before that amendment states 25%, so a candidate meeting the older figure is not misremembering.
- **2022 Q7 · pension-sector · `bce7a1b2-c043-43a4-bee9-ff1a59cd76bf`** — Material published before the 2020 revision states ₹7.5 lakh. The key follows the revised ceiling.
- **2025 Q1 · companies-act · `c242d11d-4538-48c3-b956-468d55086375`** — The auditor must intimate both the company and the Registrar. The Board option is therefore not absurd, but only the Registrar is a statutory filing under section 140(2), and it is the one of the two that appears in the options in that form.
- **2025 Q2 · commerce-accountancy · `97098263-bc0b-4f1c-b554-d9945882fe06`** — The keyed wording 'assets used for ordinary course of business' is looser than the standard's own phrase, 'held for sale in the ordinary course of business'. It is still the only option AS 2 covers, so the key is accepted.
- **2025 Q4 · companies-act · `dce6ef5e-9f98-48e6-acb1-19843069cfed`** — The prospectus does have to be filed with the Registrar, so the Registrar option is not absurd. The key follows the listing requirement, which is the step specific to a public issue.
- **2025 Q5 · pension-sector · `fcca5b3e-8457-40db-9923-7eb15a99ee84`** — These amounts come from the official APY contribution chart rather than from a calculation, so they should be checked against the current chart before publication.
- **2025 Q5 · commerce-accountancy · `9579e5bf-cc5d-49cc-b88b-a4bafb056a1d`** — On a strict working-capital reading, paying off creditors changes two current items and so alters no fund flow at all. The key follows the simpler sources-and-applications reading used in most texts, under which it is an application.
- **2025 Q6 · companies-act · `b4e8cc4e-0e87-431c-92fa-d47292a3a6b5`** — The rule says 'not more than' twenty thousand rupees while the keyed option says 'less than'. The difference matters only for a holding of exactly ₹20,000; the key is the only option at the right figure and is accepted.
- **2025 Q20 · general-intelligence-reasoning · `85fafe94-978a-4475-a2e3-9a43e77c9587`** — Options (c) and (d) also weaken the argument to some degree. The key is accepted as the strongest weakener because it attacks the price-to-consumption assumption on which the whole chain depends, while the others attack a secondary claim or an implementation difficulty.

## 6. Depth and field-population counts

| Field | Rows populated | Of 142 |
|---|---|---|
| `short_explanation` | 142 | 100% |
| `explanation_text` | 108 | 76% |
| `solution_steps` | 17 | 12% |
| `formula_used` | 16 | 11% |
| `common_traps` | 58 | 41% |
| `key_note` | 28 | 20% |
| `final_answer_option_id` | 136 | 96% |
| `option_rationales` (entries, not rows) | 568 | — |

`short_explanation` is on every row by contract. `solution_steps` and `formula_used` are confined to the
genuine numericals, enforced by an assertion in the build.

`explanation_text` sits far higher here than in EXPL-01 (14%) or EXPL-02 (14%), and the reason is the corpus
rather than a change of standard. Of these 142 rows, 56 are companies-act, pension-sector or finance items that
turn on a statutory section, a scheme rule or a regulatory threshold, and a further 6 are accounting-standard
items. Those questions come with conditions, companion timelines and exclusions that a one-line answer cannot
carry. The rule applied to every row was: keep `explanation_text` only where at least one of these holds —

1. a statutory or regulatory provision whose conditions, timelines or companion figures are not already in the
   `short_explanation` (for example the 5 / 30 / 7-day dividend chain around section 123);
2. a distinction between two options the paper itself offers, or between two terms candidates routinely swap
   (accrual against matching, nostro against vostro against loro, zero-rated against exempt);
3. a method point on a numerical that the `solution_steps` do not carry (the 360-day against 365-day
   convention, or the two independent routes to the value of a right).

Seventeen rows that had carried a paragraph of general background were stripped of it on that test. The
remaining bare-recall rows — 31 March as the fiscal year end, the operating profit ratio, the Phillips curve —
keep the one-line explanation deliberately.

Rows by subject:

| Subject | Rows | of which `current_affairs = yes` | with `solution_steps` |
|---|---|---|---|
| management | 22 | 0 | 0 |
| pension-sector | 21 | 1 | 1 |
| commerce-accountancy | 18 | 0 | 9 |
| companies-act | 18 | 0 | 0 |
| finance | 17 | 5 | 0 |
| economics | 15 | 0 | 0 |
| costing | 12 | 0 | 2 |
| general-intelligence-reasoning | 9 | 0 | 0 |
| english-language | 5 | 0 | 0 |
| quantitative-aptitude | 5 | 0 | 5 |
| **Total** | **142** | **6** | **17** |

## 7. Numerical distractor rationales

17 rows carry `solution_steps`. Each distractor on them was checked against the question's own numbers
and intermediates and against a fixed slip list (wrong denominator, omitted adjustment, intermediate given as
the answer, percentage taken on the wrong base, ratio inverted, normal loss computed on output rather than
input, exact multiple where the official chart is not an exact multiple, comparison made on one root pair only).

- **49** rationales name the wrong step that produces the figure, or say what the correct working gives instead.
- **19** are distractors no plausible slip reproduces. None uses a bare 'does not follow' line; each states the
  value the working actually gives, e.g. "No likely slip gives 4.51%; the working gives 6.92%."

They are concentrated in a few items rather than spread across the numericals:

| Year/Q | Subject | Arbitrary distractors | of wrong options |
|---|---|---|---|
| 2021 Q3 | commerce-accountancy | 4 | 4 |
| 2022 Q1 | commerce-accountancy | 4 | 4 |
| 2022 Q7 | costing | 4 | 4 |
| 2022 Q2 | commerce-accountancy | 3 | 4 |
| 2025 Q4 | commerce-accountancy | 3 | 4 |
| 2025 Q4 | costing | 1 | 4 |

The remaining 11 numerical rows have a named wrong step behind every distractor. Where a setter simply
spaces the wrong options around the key — as in the 2021 ROCE item and the 2022 forex item — no slip is invented
to explain them.

## 8. Validation — every number

Enforced by the build script; the worksheet is written only when every check passes.

- **Row count:** 142 rows, one per input question.
- **Uniqueness:** 142 distinct `question_id` values — no duplicates.
- **Completeness:** the worksheet and input `question_id` sets are identical; `year`, `question_number`,
  `subject_slug` and `topic_name` are copied through unchanged.
- **Option-rationale integrity:** 568 entries, each keyed to an `option_id` and `label` that exist on that
  question. Wrong options across the corpus: 568. Coverage is 568/568 — every wrong option on every row
  is covered, including the UNANSWERABLE rows, where the rationale states that the premise set is missing rather
  than asserting that the option is wrong.
- **No contradiction on AGREE rows:** no AGREE row carries a rationale against its own keyed option. 0 such rows.
- **final_answer_option_id:** set on all 136 AGREE rows and equal to the input `correct_option_id`;
  null on all 6 non-AGREE rows.
- **Verdict integrity:** no row carries a `proposed_correct_option_id`, because there is no DISPUTED row. Every
  non-AGREE row and every low-confidence row carries a `key_note`.
- **Numericals:** 17 rows carry `solution_steps` and 16 carry `formula_used`; both are
  restricted to that set by an assertion in the build, so no recall row carries either.
- **Tag integrity:** `tag_suspect = yes` on 5 rows, each with a non-empty `tag_note`; `tag_suspect = no` rows
  carry an empty `tag_note`. No `topic_name` was modified.
- **Provenance:** all 142 rows are `platform_original` / `owned` / `pending`.

Counts by verdict: AGREE 136, DISPUTED 0, AMBIGUOUS 0, UNANSWERABLE 6.
Counts by confidence: high 93, medium 38, low 11.

## 9. Field and enum mapping against the live schema

**Table:** `public.pyq_question_explanations` (migration `230_pyq_question_explanations.sql`).
**Write path:** `POST /admin/exam-intelligence-cms/pyq-question-explanations` (create, always born `pending`),
`PATCH .../{id}` (non-status fields), `POST .../{id}/review` (status transition through
`cms_review_pyq_question_explanation`). All in `app/backend/app/api/admin_exam_intel_cms.py`, `PERM_CMS`-gated
and audited.

| Worksheet field | Column | Apply-step note |
|---|---|---|
| `question_id` | `question_id` | create-only; FK → `pyq_questions` |
| `short_explanation` | `short_explanation` | |
| `explanation_text` | `explanation_text` | empty string → NULL |
| `solution_steps` | `solution_steps` | JSON array — matches |
| `formula_used` | `formula_used` | **wrap**: the route rejects a string with 422 (`_validate_explanation_shapes`); send `[formula]` or `[]` |
| `common_traps` | `common_traps` | JSON array — matches |
| `option_rationales` | `option_rationales` | **fold**: the route rejects an array with 422; send `{option_id: rationale}` |
| `final_answer_option_id` | `final_answer_option_id` | set on AGREE rows; route and DB trigger both prove it belongs to the question |
| `proposed_correct_option_id` | — | unused in this batch; no DISPUTED row |
| `key_verdict` | `ambiguity_status` | AGREE → `none`, DISPUTED → `disputed`, AMBIGUOUS → `multiple_possible`, UNANSWERABLE → `source_conflict` |
| `key_note`, `current_affairs`, `tag_suspect`, `tag_note`, `draft_confidence` | `metadata` | no dedicated columns |
| `explanation_source_type` / `license_status` / `reviewer_status` | same | `platform_original` / `owned` / `pending` (the route forces `pending`) |

Enum values emitted by this batch, checked against the live CHECK constraints in migration 230 and the route's
own allowlists:

- `explanation_source_type` = **`platform_original`** (of `official`, `platform_original`, `coaching`, `community`, `imported`).
- `license_status` = **`owned`** (of `owned`, `licensed`, `public_domain`, `permission_pending`, `restricted`).
- `reviewer_status` = **`pending`** (of `pending`, `verified`, `rejected`, `needs_correction`).
- `ambiguity_status` = **`none`** on the 136 AGREE rows and **`source_conflict`** on the 6 UNANSWERABLE rows.

Constraints the apply step must respect:

- `unique (question_id, explanation_source_type)`: the create route returns 422 on a second `platform_original`
  row for the same question, so a re-run must PATCH the existing `pending` row rather than re-POST.
- `pyq_question_explanations_guard` and the review RPC refuse `verified` while `ambiguity_status ≠ none` or
  `final_answer_option_id` is null, so the 6 UNANSWERABLE rows cannot be verified until their stimulus is
  supplied and the key resolved.
- Editing a learner-facing field on an already-verified row downgrades it to `needs_correction` and clears
  reviewer identity, so the apply step should touch only rows still in `pending`.

## 10. Scope

PFRDA Grade A only — the 142 questions in `workbench/sources/pfrda-explanations-input.json`. No database writes, no
migrations, no retagging, no change to any question or option, and no change to the SEBI or IFSCA batches.

## 11. Ready-to-read sample (20 rows)

Chosen with `random.Random(20260924).sample(rows, 20)` over the worksheet rows in file order, then sorted by year,
subject and question number for reading. Re-running the same call on the same file yields the same 20.

---

### S1. 2021 Q5 · commerce-accountancy · Turnover ratios — receivables, working capital, inventory

`f16ca3d2-1f75-4265-946f-e692c8b16d97` · verdict **AGREE** · confidence **high**

**Stem.** Given, Credit Sales = ₹72,00,000 Average Accounts Receivable = ₹12,00,000 Calculate the Average age of Receivables

- **(a)** 60 days  ✅ **keyed**
- **(b)** 45 days
- **(c)** 90 days
- **(d)** 180 days
- **(e)** 72 days

**short_explanation.** Receivables turnover is credit sales divided by average receivables: 72,00,000 / 12,00,000 = 6 times a year. Spreading a 360-day year over 6 turns gives an average collection period of 60 days.

**explanation_text.** Both a 360-day and a 365-day convention are used in practice. On 365 days the answer is 60.83 days, which still rounds to the same option, so the choice of convention does not change the answer here — but it is worth knowing which one a paper expects, because on other numbers it does.

**solution_steps.**

1. Receivables turnover = Credit sales / Average receivables = 72,00,000 / 12,00,000 = 6 times.
2. Average age of receivables = 360 / 6 = 60 days.
3. (On a 365-day year the same working gives 60.83 days, which still points to the 60-day option.)

**formula_used.** Average age of receivables = Days in year / Receivables turnover ratio

**option_rationales.**

- **(b)** 45 days implies a turnover of 8 times a year; the given figures give 6.
- **(c)** 90 days implies a turnover of 4 times a year; the given figures give 6.
- **(d)** 180 days implies a turnover of twice a year, which would mean receivables of ₹36,00,000.
- **(e)** 72 days simply echoes the ₹72 lakh sales figure; no step in the working produces it.

**common_traps.**

- Inverting the ratio and dividing receivables by sales.

---

### S2. 2022 Q2 · economics · GDP, GNP, NNP and NDP concepts

`0a3740a7-012a-46d3-a6d7-8b7ba8da293f` · verdict **AGREE** · confidence **high**

**Stem.** In the field of economics, what is the correct formula to calculate Net National Product ?

- **(a)** Gross National Product - NFIA
- **(b)** Gross National Product – Depreciation  ✅ **keyed**
- **(c)** Gross National Product + Depreciation
- **(d)** Gross National Product – Indirect Taxes + Subsidies
- **(e)** Gross National Product + NFIA

**short_explanation.** Net National Product is Gross National Product less depreciation — the consumption of fixed capital. 'Net' always means that wear and tear on the capital stock has been taken out.

**explanation_text.** Two adjustments run through this family of aggregates and it is worth keeping them separate. Moving from 'gross' to 'net' subtracts depreciation. Moving from 'domestic' to 'national' adds net factor income from abroad. So GDP + NFIA = GNP, and GNP − depreciation = NNP. Subtracting indirect taxes net of subsidies converts a market-price measure to a factor-cost one, which is a third and different step.

**option_rationales.**

- **(a)** Subtracting net factor income from abroad converts GNP back to GDP; it does not give NNP.
- **(c)** Adding depreciation moves in the wrong direction — net is smaller than gross.
- **(d)** Removing indirect taxes and adding subsidies converts market prices to factor cost, a separate adjustment.
- **(e)** Adding net factor income from abroad again would double-count it, since GNP already includes it.

**common_traps.**

- Confusing the gross-to-net adjustment with the domestic-to-national one.

---

### S3. 2022 Q1 · finance · Price stabilisation and the green shoe option

`41c4d3fa-14fa-4715-8e48-c02e517c0077` · verdict **AGREE** · confidence **high**

**Stem.** Which of the following mechanism is used to bring price stability in the share price during the Initial Public Offer (IPO) ?

- **(a)** Circuit Breakers
- **(b)** White washing
- **(c)** Green-shoe option  ✅ **keyed**
- **(d)** Underwriting
- **(e)** None of the above

**short_explanation.** The green shoe option is the price-stabilisation mechanism in a public issue. It lets the issuer allot extra shares and appoint a stabilising agent to buy in the market if the price falls below the issue price soon after listing.

**explanation_text.** In India the mechanism runs for up to thirty days after listing. The stabilising agent borrows shares from a promoter, sells them with the issue, and then buys them back in the market if the price sags — the buying supports the price. If the price instead stays firm, the issuer allots fresh shares to return the borrowed ones.

**option_rationales.**

- **(a)** Circuit breakers halt trading across the market when an index moves sharply; they are not an issue-specific device.
- **(b)** 'White washing' is not a capital-markets mechanism.
- **(d)** Underwriting guarantees that the issue is subscribed; it does not support the price after listing.
- **(e)** One of the options is correct.

**common_traps.**

- Underwriting and the green shoe both involve the merchant banker, but underwriting protects subscription, not the post-listing price.

---

### S4. 2022 Q7 · finance · Scale-based regulation of NBFCs

`95da4941-0329-4b9a-b350-44d47b6e0e08` · verdict **AGREE** · confidence **medium** · current affairs

**Stem.** As per the recent regulations released by RBI for regulation of NBFCs, Non-Deposit Taking NBFC (wherein the asset size is more than 1000 crore) will be categorized as which of the following layers of the NBFCs?

- **(a)** Upper Layer
- **(b)** Base Layer
- **(c)** Middle Layer  ✅ **keyed**
- **(d)** Top Layer
- **(e)** None of the above

**short_explanation.** Under the Reserve Bank's scale-based regulation, a non-deposit-taking NBFC with assets above ₹1,000 crore falls in the Middle Layer.

**explanation_text.** The framework sorts NBFCs into four layers by size and activity, with regulation tightening as the layer rises. The Base Layer holds non-deposit-taking NBFCs below ₹1,000 crore. The Middle Layer holds all deposit-taking NBFCs plus non-deposit-takers above ₹1,000 crore, along with certain specified categories. The Upper Layer holds those the Reserve Bank identifies as systemically significant, and the Top Layer is kept empty unless supervisory concern requires a company to be moved into it.

**option_rationales.**

- **(a)** The Upper Layer is reserved for NBFCs the Reserve Bank specifically identifies as systemically significant.
- **(b)** The Base Layer holds non-deposit-taking NBFCs with assets below ₹1,000 crore.
- **(d)** The Top Layer is ordinarily kept empty.
- **(e)** One of the options is correct.

---

### S5. 2022 Q2 · management · Classical, neoclassical, behavioural and modern schools

`286025f9-8390-4291-a9c3-d9d58c986e77` · verdict **AGREE** · confidence **high**

**Stem.** From the following given option identify the theory of management, which explains that Organizations are social entities that are purpose-oriented, sub-divided, consciously structured and designed as coordinated activity systems and Organisation is a system composed of interacting and interdependent parts, called subsystems.

- **(a)** Content theory
- **(b)** System theory  ✅ **keyed**
- **(c)** Scientific theory
- **(d)** Management Theory
- **(e)** None of the above

**short_explanation.** Systems theory treats an organisation as a set of interacting, interdependent subsystems that together pursue a purpose — which is exactly what the stem describes.

**option_rationales.**

- **(a)** Content theories, such as Maslow's and Herzberg's, explain what motivates people, not how an organisation is structured.
- **(c)** Scientific management focuses on work methods and efficiency at the task level.
- **(d)** 'Management theory' is too general to name any particular school.
- **(e)** One of the options is correct.

---

### S6. 2022 Q5 · management · Manager's role in HRD and employee support

`183a4eb0-483b-4887-a960-26e0891ff14b` · verdict **AGREE** · confidence **medium**

**Stem.** Which of the following role does a manager plays in Human Resource Development, when the manager helps the employee to handle the problems of the employee and this role also increases the productivity of the employees

- **(a)** Career Anchors
- **(b)** Career Orientation
- **(c)** Career Path
- **(d)** Career Counselling  ✅ **keyed**
- **(e)** Career ladder

**short_explanation.** Career counselling is the role in which the manager helps an employee work through problems — personal or work-related — and in doing so lifts the employee's productivity.

**explanation_text.** The related terms describe different things and are easy to mix up. A career anchor is the value an individual will not give up when choosing work. A career path is the sequence of positions leading somewhere. A career ladder is the hierarchy of those positions. Counselling is the manager's act of guiding the individual through them.

**option_rationales.**

- **(a)** A career anchor is the value or motive an individual will not trade away in a career choice.
- **(b)** Career orientation is the direction of an individual's career preferences.
- **(c)** A career path is the sequence of roles an employee may move through.
- **(e)** A career ladder is the hierarchy of positions available.

---

### S7. 2022 Q7 · management · Steps in the communication process

`be81cfa4-549a-4efb-a20a-3dc5ebc160ff` · verdict **AGREE** · confidence **high**

**Stem.** Suppose in an organisation, employees have good communication skills, there is a high level of mutual trust and every employee respects the every other employee, such situation will lead to which of the following scenarios ?

- **(a)** Effective Communication will leader to an argumentative situation
- **(b)** Effective Communication will increase the time taken to complete the work
- **(c)** There will be less inter-change of thoughts and partaking of ideas
- **(d)** There will be an increase in the management efficiency  ✅ **keyed**
- **(e)** None of the above

**short_explanation.** Good communication skills, mutual trust and mutual respect are the conditions for effective communication, and effective communication raises management efficiency — decisions are understood and carried out without repeated correction.

**option_rationales.**

- **(a)** Effective communication reduces argument rather than causing it.
- **(b)** It shortens the time taken to complete work, because less is done twice.
- **(c)** It increases the interchange of thoughts and ideas.
- **(e)** One of the options is correct.

---

### S8. 2022 Q4 · pension-sector · APY eligibility and contribution

`52391257-4534-4869-a4d8-aecfe2e4b8aa` · verdict **AGREE** · confidence **medium**

**Stem.** Under Atal Pension Yojana, an unmarried subscriber has to nominate which of the following person as nominee ?

- **(a)** Brother
- **(b)** Mother
- **(c)** Father
- **(d)** Sister
- **(e)** Any of the above  ✅ **keyed**

**short_explanation.** Under Atal Pension Yojana the spouse is the default nominee for a married subscriber. An unmarried subscriber may nominate any other person, so any of the relatives listed is acceptable.

**explanation_text.** The nominee rules follow from how the scheme pays out. On the subscriber's death the same pension continues to the spouse, and only after both have died does the accumulated corpus go to the nominee. Where there is no spouse, that constraint falls away and the subscriber is free to choose. A married subscriber must also furnish spouse details, and the spouse is the default nominee by operation of the scheme rather than by choice.

**option_rationales.**

- **(a)** A brother may be nominated, but so may the other relatives listed, so this alone is incomplete.
- **(b)** A mother may be nominated, but this alone is incomplete.
- **(c)** A father may be nominated, but this alone is incomplete.
- **(d)** A sister may be nominated, but this alone is incomplete.

---

### S9. 2022 Q6 · pension-sector · PFRDA Act 2013 — powers and functions

`8d475ef0-337c-4cec-bc23-9c4577c866b2` · verdict **AGREE** · confidence **medium**

**Stem.** Which of the following portal acts as grievances redressal cell for the pensioners? Options:

- **(a)** Pensioners Redressal Cell
- **(b)** Pensioners Ombudsman Cell
- **(c)** Pension and Pensioners Welfare Cell
- **(d)** Central Grievance Management System (CGMS)  ✅ **keyed**
- **(e)** None of the above

**short_explanation.** Grievances relating to NPS are raised through the Central Grievance Management System, the online portal maintained within the NPS architecture for subscribers and intermediaries.

**explanation_text.** The escalation ladder is worth knowing as a whole: the subscriber first raises the grievance with the intermediary concerned through CGMS, then with the NPS Trust if it is not resolved, and finally with the Ombudsman appointed by PFRDA. Each stage has its own time limit.

**option_rationales.**

- **(a)** There is no body of this name in the NPS grievance framework.
- **(b)** PFRDA appoints an Ombudsman, but the portal through which grievances are lodged is CGMS.
- **(c)** The Department of Pension and Pensioners' Welfare serves central government pensioners; it is not the NPS grievance portal.
- **(e)** One of the options is correct.

**tag_note.** Topic should be grievance redressal under NPS (CGMS and the Ombudsman), not the powers and functions of the PFRDA Act 2013. The question asks about a redressal portal, not a statutory power.

---

### S10. 2022 Q7 · pension-sector · Types and features of retirement schemes in India

`bce7a1b2-c043-43a4-bee9-ff1a59cd76bf` · verdict **AGREE** · confidence **medium**

**Stem.** Pradhan Mantri Vaya Vandana Yojana (PMVVY) was launched in the year 2017, PMVVY aims to protect elderly persons aged 60 years and above, against a future fall in their interest income due to the uncertain market conditions. In the same regard, what is the limit of maximum investment in PMVVY.

- **(a)** 10,00,000
- **(b)** 20,00,000
- **(c)** 15,00,000  ✅ **keyed**
- **(d)** 5,00,000
- **(e)** 25,00,000

**short_explanation.** The maximum that may be invested in Pradhan Mantri Vaya Vandana Yojana is ₹15 lakh per senior citizen.

**explanation_text.** The ceiling was doubled from ₹7.5 lakh to ₹15 lakh in 2020, and it applies per senior citizen rather than per family — so a couple who are both 60 or above can invest ₹15 lakh each. Because the scheme pays a guaranteed rate, the cap is what stops it from becoming an unlimited government-backed deposit.

**option_rationales.**

- **(a)** Ten lakh rupees is below the current ceiling.
- **(b)** Twenty lakh rupees is above the ceiling.
- **(d)** Five lakh rupees is well below the ceiling.
- **(e)** Twenty-five lakh rupees is well above the ceiling.

**key_note.** Material published before the 2020 revision states ₹7.5 lakh. The key follows the revised ceiling.

---

### S11. 2025 Q1 · commerce-accountancy · Stages of the accounting process

`1d9f687b-031d-47f5-98e7-4663a2229147` · verdict **AGREE** · confidence **high**

**Stem.** In the accounting process, which of the following represents the final step?

- **(a)** Identification of transactions
- **(b)** Summary and analysis of financial data
- **(c)** Communication of financial information  ✅ **keyed**
- **(d)** Recording of transactions
- **(e)** None of the above

**short_explanation.** The accounting process runs from identifying transactions, through recording, classifying and summarising, to communicating the results to users. Communication is the last step, and it is the point of the whole exercise — statements exist to be read.

**option_rationales.**

- **(a)** Identification is the first step, not the last.
- **(b)** Summary and analysis precede communication; the summarised figures are what gets communicated.
- **(d)** Recording follows identification and sits early in the sequence.
- **(e)** One of the listed steps is the final one, so this is not correct.

---

### S12. 2025 Q2 · commerce-accountancy · Liquidity ratios — current and quick

`9693d7e7-f490-42a0-8ef3-98fc209b4916` · verdict **AGREE** · confidence **high**

**Stem.** Calculate Current Ratio from the following: • Cash= 1,00,000 • Disposable Investments (less than 1 year)= 50,000 • Inventory= 75,000 • Creditors= 15,000 • Bank Overdraft = 1,25,000 • Outstanding Expenses= 10,000

- **(a)** 1.5:1  ✅ **keyed**
- **(b)** 1:1
- **(c)** 1:1
- **(d)** 1:2
- **(e)** 1.8:1

**short_explanation.** Current assets are cash ₹1,00,000, short-term investments ₹50,000 and inventory ₹75,000 = ₹2,25,000. Current liabilities are creditors ₹15,000, bank overdraft ₹1,25,000 and outstanding expenses ₹10,000 = ₹1,50,000. The current ratio is 2,25,000 / 1,50,000 = 1.5:1.

**explanation_text.** A bank overdraft is the item candidates most often leave out. It is repayable on demand, so it is a current liability and belongs in the denominator. Investments count as current assets only because the question states they are disposable within a year; a long-term investment would not.

**solution_steps.**

1. Current assets = 1,00,000 + 50,000 + 75,000 = ₹2,25,000.
2. Current liabilities = 15,000 + 1,25,000 + 10,000 = ₹1,50,000.
3. Current ratio = 2,25,000 / 1,50,000 = 1.5:1.

**formula_used.** Current Ratio = Current Assets / Current Liabilities

**option_rationales.**

- **(b)** 1:1 is the quick ratio — the ₹75,000 of inventory dropped from current assets, giving 1,50,000 / 1,50,000.
- **(c)** This option repeats 1:1, which is the quick ratio, not the current ratio.
- **(d)** No step in the working gives 1:2; that would need current liabilities of ₹4,50,000.
- **(e)** 1.8:1 counts only the ₹1,25,000 bank overdraft as a current liability and drops creditors and outstanding expenses.

**common_traps.**

- Leaving the bank overdraft out of current liabilities.
- Excluding inventory, which gives the quick ratio instead.

**key_note.** Options (b) and (c) are printed identically as '1:1', so the paper offers four distinct choices rather than five. The key is unaffected: 1.5:1 is the only correct value. The duplicate should be corrected before this item is published.

---

### S13. 2025 Q4 · commerce-accountancy · AS 11 — foreign exchange, FCMITDA, non-integrated operations

`c3f342ae-f1ff-468c-a33b-3bfb07866139` · verdict **AGREE** · confidence **medium**

**Stem.** Which of the following statements about non-integrated foreign operations is incorrect according to Accounting Standard 11 (AS 11)?

- **(a)** Contingent liabilities at the closing date are translated at the closing exchange rate.
- **(b)** Income and expenses of non-integrated operations are translated at the exchange rates prevailing on the dates of the transactions rate.
- **(c)** Assets and liabilities of non-integrated operations are translated at the date of transaction.  ✅ **keyed**
- **(d)** Foreign exchange transaction differences on investments in non-integrated foreign operations are recognized in the books of accounts.
- **(e)** Monetary items and non-monetary items at the closing rate.

**short_explanation.** For a non-integral foreign operation, AS 11 translates all assets and liabilities — monetary and non-monetary alike — at the closing rate. The statement that they are translated at the transaction-date rate is therefore the incorrect one.

**explanation_text.** The two categories are treated very differently, and that is the whole point of the classification. An integral operation is accounted for as though its transactions were the reporting entity's own, so non-monetary items stay at historical rates. A non-integral operation is a largely self-contained business, so everything on its balance sheet moves to the closing rate and the resulting differences go to a foreign currency translation reserve rather than to profit and loss.

**option_rationales.**

- **(a)** Contingent liabilities of a non-integral operation are indeed translated at the closing rate.
- **(b)** Income and expense items are translated at the rates on the dates of the transactions, or at an average rate as an approximation.
- **(d)** Exchange differences on a net investment in a non-integral foreign operation are recognised, accumulating in the translation reserve.
- **(e)** Both monetary and non-monetary items go at the closing rate for a non-integral operation, which is exactly what makes option (c) wrong.

**common_traps.**

- The question asks which statement is INCORRECT; a hurried reading picks the first statement that sounds right.

---

### S14. 2025 Q6 · companies-act · Small shareholders' director

`b4e8cc4e-0e87-431c-92fa-d47292a3a6b5` · verdict **AGREE** · confidence **medium**

**Stem.** Under the Companies Act, 2013, who is considered a "small shareholder" based on the value of shares held?

- **(a)** A shareholder holding shares worth less than Rs 50,000
- **(b)** A shareholder holding shares worth less than Rs 10,000
- **(c)** A shareholder holding shares worth less than Rs 20,000  ✅ **keyed**
- **(d)** A shareholder holding shares worth less than Rs 1,00,000
- **(e)** A shareholder holding shares worth less than Rs 5,000

**short_explanation.** For the purpose of appointing a small shareholders' director, a small shareholder is one holding shares of nominal value of not more than twenty thousand rupees.

**explanation_text.** The definition supports section 151, under which a listed company may — and on a requisition by at least one thousand small shareholders or one-tenth of them, whichever is less, must — appoint a director elected by small shareholders. The threshold is measured on nominal value, not market value, so a holding is judged by its face value.

**option_rationales.**

- **(a)** Fifty thousand rupees is above the prescribed threshold.
- **(b)** Ten thousand rupees is below the prescribed threshold.
- **(d)** One lakh rupees is well above the prescribed threshold.
- **(e)** Five thousand rupees is below the prescribed threshold.

**key_note.** The rule says 'not more than' twenty thousand rupees while the keyed option says 'less than'. The difference matters only for a holding of exactly ₹20,000; the key is the only option at the right figure and is accepted.

---

### S15. 2025 Q2 · economics · Measurement methods — income, expenditure, product

`4856b840-5587-4351-b11c-05ecc265e2ae` · verdict **AGREE** · confidence **high**

**Stem.** Manufacturing comes under which of the following sectors of the economy?

- **(a)** Primary Sector
- **(b)** Secondary Sector  ✅ **keyed**
- **(c)** Tertiary Sector
- **(d)** Quaternary Sector
- **(e)** Quinary Sector

**short_explanation.** Manufacturing belongs to the secondary sector, which takes the raw materials produced by the primary sector and turns them into finished goods.

**explanation_text.** The three-way split follows what each sector does to the product. The primary sector extracts — farming, mining, fishing. The secondary sector transforms — manufacturing, construction, electricity. The tertiary sector serves — trade, transport, banking, education. Quaternary and quinary are later refinements of the service sector covering knowledge work and top-level decision-making.

**option_rationales.**

- **(a)** The primary sector extracts raw materials rather than processing them.
- **(c)** The tertiary sector provides services.
- **(d)** The quaternary sector covers knowledge-based activity such as research.
- **(e)** The quinary sector covers the highest levels of decision-making.

**tag_note.** Topic should be the sectors of the economy (primary, secondary, tertiary), not the measurement methods for national income. The question does not touch the income, expenditure or product method.

---

### S16. 2025 Q15 · english-language · No-improvement-required cases

`96ee11f5-c59f-404f-98a0-13bb8b64341b` · verdict **AGREE** · confidence **medium**

**Stem.** The biologist demonstrated how adaptation (A) in ecosystems is driven not by hierarchy (B), but by cooperation (C) and evolutionary contingency (D).

- **(a)** A-B & C-D
- **(b)** A-C
- **(c)** B-D
- **(d)** A-D & B-C
- **(e)** No interchange required  ✅ **keyed**

**short_explanation.** The sentence already reads correctly: adaptation is driven not by hierarchy but by cooperation and evolutionary contingency. Every part sits where it belongs, so no interchange is required.

**explanation_text.** In interchange questions the test is grammatical and logical fit, not style. 'Not by X, but by Y' sets up a contrast, so X must be the rejected cause and Y the accepted one — hierarchy and cooperation respectively, which is how the sentence already stands. Swapping any pair would either break that contrast or put a cause where the subject belongs.

**option_rationales.**

- **(a)** Exchanging A with B and C with D would make hierarchy the thing being driven and adaptation a cause, which reverses the sense.
- **(b)** Exchanging A with C would make cooperation the thing driven and adaptation a cause of it.
- **(c)** Exchanging B with D would make evolutionary contingency the rejected cause, contradicting the sentence's own contrast.
- **(d)** Exchanging A with D and B with C would leave both halves of the contrast incoherent.

**common_traps.**

- A long sentence with technical vocabulary invites the assumption that something must be wrong with it.

---

### S17. 2025 Q15 · general-intelligence-reasoning · Shifting and rearrangement machine

`ffb6d5a3-0888-4f0a-90cd-f1ec4e3e65a7` · verdict **UNANSWERABLE** · confidence **low**

**Stem.** Which among the following is the fifth element from the right end in the final step?

- **(a)** 56
- **(b)** 33
- **(c)** 17
- **(d)** 26
- **(e)** 48  ✅ **keyed**

**short_explanation.** This question asks for the fifth element from the right end of the final step of a shifting-and-rearrangement machine. The input row and the intermediate steps are not part of this record, so the final step cannot be reconstructed. Method, for when the input is available: derive the rule from the early steps, carry the arrangement through to the last step, and then count from the correct end — counting from the wrong end is the commonest error in this question type, and both ends usually appear among the options.

**option_rationales.**

- **(a)** The premise set this question belongs to is not part of this record, so no arrangement can be worked and no option can be evaluated.
- **(b)** The premise set this question belongs to is not part of this record, so no arrangement can be worked and no option can be evaluated.
- **(c)** The premise set this question belongs to is not part of this record, so no arrangement can be worked and no option can be evaluated.
- **(d)** The premise set this question belongs to is not part of this record, so no arrangement can be worked and no option can be evaluated.

**key_note.** The input row and the intermediate steps are missing from the input file, so the keyed answer of 48 cannot be verified. No final answer is asserted.

---

### S18. 2025 Q16 · general-intelligence-reasoning · Only and only-a-few statements

`ad034028-d3c7-49bb-9036-618a325a4e52` · verdict **AGREE** · confidence **high**

**Stem.** Statements: Only a few Blue is Yellow All Yellow is Pink No Pink is Grey Conclusions: I. All Grey can be Blue II. All Yellow can be Grey

- **(a)** Only I follow  ✅ **keyed**
- **(b)** Only II follow
- **(c)** Either I or II follows
- **(d)** Neither I nor II follows
- **(e)** Both I and II follows

**short_explanation.** 'All Yellow is Pink' and 'No Pink is Grey' together mean no Yellow can ever be Grey, so conclusion II fails outright. 'Only a few Blue is Yellow' means some Blue are Yellow and some are not, and that second group is free to overlap Grey — so all Grey being Blue is possible and conclusion I follows. Only I follows.

**explanation_text.** Two different kinds of conclusion are being tested here and they need different tests. A possibility conclusion ('All Grey can be Blue') fails only if the premises make it impossible; you have to look for one arrangement that allows it. A definite conclusion ('No Pink is Grey' style) must hold in every arrangement. Conclusion II is a possibility claim that the premises rule out completely: Yellow sits inside Pink, Pink and Grey never meet, so no Yellow can be Grey under any arrangement.

**option_rationales.**

- **(b)** Conclusion II claims all Yellow can be Grey, but Yellow lies entirely inside Pink and no Pink is Grey, so it is impossible.
- **(c)** 'Either-or' applies where two conclusions are complementary and exactly one must hold; here I is possible and II is impossible, so they are not alternatives.
- **(d)** Conclusion I does follow, so this cannot be right.
- **(e)** Conclusion II is impossible, so both cannot follow.

**common_traps.**

- 'Only a few A is B' carries two statements at once: some A are B, and some A are not B. The second half is what makes conclusion I work.

---

### S19. 2025 Q5 · management · PESTEL analysis

`d1bf69e7-79ec-41f9-8897-897eaf6fe753` · verdict **AGREE** · confidence **high**

**Stem.** Which of the following correctly represents the meanings of E, S, and L in the PESTEL analysis framework?

- **(a)** E = Environmental, S = Structural, L = Legislative
- **(b)** E = Economic, S = Social, L = Legal  ✅ **keyed**
- **(c)** E = Emotional, S = Societal, L = Logistical
- **(d)** E = Ecological, S = Service, L = Lawful
- **(e)** E = Educational, S = Supportive, L = Local

**short_explanation.** PESTEL stands for Political, Economic, Social, Technological, Environmental and Legal. So E is Economic, S is Social and L is Legal.

**explanation_text.** The framework scans the external environment a business cannot control, which is what separates it from SWOT — strengths and weaknesses are internal. Note that the E in the middle of the acronym is Economic while the second E, near the end, is Environmental; the options exploit that.

**option_rationales.**

- **(a)** Environmental is the second E in the acronym, not the first, and neither Structural nor Legislative appears in it.
- **(c)** Emotional, Societal and Logistical are not PESTEL terms.
- **(d)** Ecological is sometimes used for the second E, but Service and Lawful are not PESTEL terms.
- **(e)** Educational, Supportive and Local are not PESTEL terms.

---

### S20. 2025 Q2 · quantitative-aptitude · Quadratic equations — root comparison (x vs y)

`a92f9740-c15d-4c84-b429-a09079166df0` · verdict **AGREE** · confidence **high**

**Stem.** I. x2 + 19x + 90 = 0 II. 3y - 16 = 8y + 24

- **(a)** x > y
- **(b)** x < y  ✅ **keyed**
- **(c)** x ≥ y
- **(d)** x = y or no relation can be established between x and y
- **(e)** x ≤ y

**short_explanation.** The first equation gives x = −9 or −10. The second is linear: 3y − 16 = 8y + 24 gives −5y = 40, so y = −8. Both values of x are below −8, so x < y.

**explanation_text.** Signs are what make this one awkward. Both roots are negative, and −10 is smaller than −9, which is smaller than −8 — the larger the digit, the smaller the number. Checking only that the extreme value of x stays on one side of y is enough here, because there is a single y to compare against.

**solution_steps.**

1. x² + 19x + 90 = 0 factorises as (x + 9)(x + 10) = 0, so x = −9 or −10.
2. 3y − 16 = 8y + 24 → 3y − 8y = 24 + 16 → −5y = 40 → y = −8.
3. −9 < −8 and −10 < −8, so x < y in both cases.

**formula_used.** For x² + Sx + P = 0, the roots are the pair with sum −S and product P

**option_rationales.**

- **(a)** x > y is false; both roots of x are below −8.
- **(c)** x ≥ y would require some x to equal or exceed −8; neither does.
- **(d)** A definite relation does exist, since both values of x are less than y.
- **(e)** x ≤ y is weaker than the truth, and equality never occurs — x is strictly less than y in both cases.

**common_traps.**

- Treating −10 as larger than −9 because the digit is larger.
- Choosing 'x ≤ y' when equality never actually arises.

