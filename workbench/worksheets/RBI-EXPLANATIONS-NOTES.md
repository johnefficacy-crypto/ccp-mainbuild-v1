# RBI Grade B — Explanation Draft: Review Notes (EXPL-03)

Worksheet: `workbench/worksheets/RBI-EXPLANATIONS-DRAFT.json` — 531 rows, one per verified RBI Grade B MCQ
in `workbench/sources/rbi-explanations-input.json`. Every row is authored from subject knowledge and the question's own
text. Set-based questions (puzzles, passages, data tables) carry their shared premise inside `question_text`. No text is
extracted from any third-party source. Nothing here is reviewed.

**What the input actually covers.** general-intelligence-reasoning 285, english-language 138, quantitative-aptitude 108.
The export filtered `reviewer_status = 'verified'`: RBI Grade B has 531 verified MCQs out of 999. The other 468 are General
Awareness and Phase II (ESI, F&M) questions that are tagged but not yet verified at question level, so they are deliberately
out of this batch. No GA, ESI or F&M row appears here, so no row here is current affairs (all 531 are `current_affairs = no`).

Standing rules from EXPL-02 apply (current-affairs treatment, named-slip distractor rationales, `final_answer_option_id` on AGREE
rows, seeded sample). New and permanent from this batch:

- **Keys accepted where defensible.** A key defensible on any reasonable reading is AGREE; `key_note` names the reading set aside.
  AGREE rows whose key_note begins "Accepted as defensible": 53; AGREE rows with any key_note reservation: 111.
  Flags are reserved for keys defensible on no reading, or questions unanswerable as stored.
- **Puzzles work one arrangement.** Each puzzle set is explained from one arrangement that fits the clues and the key, with the
  deductions that pin it down; any other valid arrangement is mentioned in one line at the end.
- **Plain language on every row.** No position codes, symbols or invented labels; arrangements described in words.

## 1. Key verdicts

| Verdict | Count | `final_answer_option_id` |
|---|---|---|
| AGREE | 519 | set = input `correct_option_id` |
| DISPUTED | 3 | null — awaits a human key decision |
| AMBIGUOUS | 1 | null — awaits a human key decision |
| UNANSWERABLE | 8 | null — awaits a human key decision |
| **Total** | **531** | **519 set** |

### 1.1 DISPUTED — the keyed answer is, in my judgement, wrong

#### 2024 Q120 · quantitative-aptitude · `d63175ab-a8ec-4ed6-866a-fd0b30cca23a`

**Stem.** There is a car and a bus. The speed of the car is ‘X’ km/h and the speed of the bus is twice of the car. The car is going from A to B and the bus is going from B to A. The car starts its journey at 10:30 am and finishes at 17:00 pm. The bus covers (672 + 2X) km in 3 hours. If the car speed is reduced by 25%, how much more time will it take? (Note: The car halts two times for 5 minutes each in the entire journey.)

- **Keyed option:** (c) 2 hours
- **Proposed option:** (a) 2 hours 10 minutes
- **Reason.** The key (2 hours) is not reached on any consistent reading. Moving time is 6 hours 20 minutes, and a 25% speed cut adds one-third of it, 2 hours 6 minutes 40 seconds. Ignoring the halts gives exactly 2 hours 10 minutes; either way option a is the nearest listed value, and 2 hours is further away.

#### 2026 Q100 · english-language · `bb04cc71-d8d4-40a8-b0e8-c3d0297e0147`

**Stem.** Directions (93–101): Read the following passage carefully and answer the questions given below it. In the contemporary macroeconomic discourse surrounding post-industrial vulnerabilities, the persistence of food insecurity within the United States presents a profound operational paradox. Despite anchoring an agrarian infrastructure characterized by unparalleled capital intensity, structural integration, and technological sophistication, deep systemic fissures within the domestic distributive network systematically marginalize significant cohorts of the populace. This phenomenon cannot be reduced to a simplistic manifestation of absolute agricultural scarcity; rather, it represents an intricate, self-perpetuating systemic malfunction driven by acute socioeconomic stratification, deliberate geographic segregation (manifested as "food deserts"), and the volatile cascading effects of inflationary shocks on staple commodities. Historically, federal interventions such as the Supplemental Nutrition Assistance Program (SNAP) have served as the primary legislative bulwark against outright caloric deficiency. However, progressive socio-economists argue that these institutional frameworks are fundamentally reactionary, architected to temporarily alleviate transient poverty rather than structurally dismantle the entrenched, cyclical dynamics of systemic deprivation. The programmatic architecture of such safety nets often relies on antiquated, monolithic bureaucratic metrics that fail to account for acute regional disparities in cost-of-living indexations or the insidious expansion of "food mirages"—urban spaces where nutritious provisions are physically accessible but economically prohibitive to the surrounding low- income enclave. Furthermore, the hyper-politicization of budgetary appropriations frequently subjects these essential welfare mechanisms to fiscal austerity measures, thereby compounding the precarity of vulnerable households during periods of macroeconomic contraction. The structural vulnerability of the American food distribution apparatus was explicitly laid bare during recent global supply chain disruptions, which exposed the dangerous hyper- centralization of processing facilities and meat-packing monopolies. When systemic shocks fractured these brittle logistical vectors, the resultant inflationary spiral disproportionately impacted low-income demographics, forcing a regressive substitution toward energy-dense, shelf-stable, and nutrient-poor alimentary options. This dietary shift carries profound long- term public health implications, perpetuating a cruel irony where food-insecure populations simultaneously exhibit disproportionate rates of metabolic syndromes, diabetes, and clinical obesity—a complex clinical state that scholars term the "food-insecurity-obesity paradox." Moreover, the corporate consolidation of the agrarian retail sector has structurally disincentivized the establishment of community-centric distribution nodes. Major retail monopolies consistently prioritize high-margin suburban supermarkets over low-yield urban or isolated rural markets, creating vast zones of corporate abandonment. Beyond the immediate socioeconomic indicators, the intersection of environmental degradation and agricultural policy further exacerbates this domestic precarity. The entrenched reliance on monocultural farming practices, heavily subsidized by federal frameworks, privileges the overproduction of industrial commodities like corn and soy at the expense of localized, diversified specialty crops. This ecological imbalance renders the food supply chain highly fragile to climate-induced anomalies, where localized droughts or extreme weather events trigger cascading failures in supply elasticity. Consequently, addressing this crisis necessitates an ontological shift in policy formulation: moving away from mere emergency caloric supplementation toward the institutionalization of food sovereignty, aggressive supply chain decentralization, and the rigorous statutory regulation of predatory retail cartels. Which of the following statements is/are correct regarding the "food-insecurity- obesity paradox"? (I) It highlights the coexistence of metabolic disorders and clinical obesity within households facing food insecurity. (II) It is directly exacerbated by supply chain disruptions that drive up the cost of premium, nutrient-dense foods. (III) It proves that low-income demographics choose energy-dense food items primarily due to a total lack of health awareness. Only (I)

- **Keyed option:** (b) Both (II) and (III)
- **Proposed option:** (a) Both (I) and (II)
- **Reason.** Keyed option b (II and III) includes III, which the passage contradicts: the shift to energy-dense food is 'forcing a regressive substitution' caused by inflation, not ignorance. I and II are both supported, so option a is correct. The option list appears shifted: 'Only (I)' is stuck on the end of the stem, suggesting the original key 'Both (I) and (II)' has moved.

#### 2026 Q187 · general-intelligence-reasoning · `6021fdea-040b-4457-9b43-fd3e7612cbf2`

**Stem.** Directions (187-189) In each of the following questions, a statement is followed by three assumptions numbered I, II and III. An assumption is something supposed or taken for granted. Read the statement carefully and decide which of the given assumptions is/are implicit in the statement. Statement: The bank has advised customers to update their mobile numbers and email IDs in their accounts. This will help them receive transaction alerts, security messages and important account-related updates on time. Assumptions: I. Some customers may not have updated their latest contact details with the bank. II. Customers who update their contact details will get higher interest on deposits. III. Timely alerts can help customers remain informed about account activities. Which of the above assumptions is/are implicit? Only III

- **Keyed option:** (d) All I, II and III
- **Proposed option:** (c) Both I and III
- **Reason.** The keyed option reads 'All I, II and III', but II (higher interest for updating contact details) is plainly not implicit. Only I and III are, so option c 'Both I and III' is right. The stem ends with a stray 'Only III', which suggests the first option was merged into the stem and the option texts shifted by one; under the original lettering the key letter d may have pointed to 'Both I and III'.

### 1.2 AMBIGUOUS — more than one option is defensible, or the data is inconsistent

#### 2023 Q103 · english-language · `0a6d3b53-6b00-47fe-b43a-13b11939310e`

**Stem.** Four statements have been mentioned below. One or more statements may contain an error. It may contain a grammatical and/or a contextual error. Identify the CORRECT statement. In case, all the statements are incorrect, then, mark option E, ‘None of the above’ as the answer.

- **Keyed option:** (e) None of the above
- **Reason.** Key e ('None of the above') is not defensible: statements b and d are grammatically and factually correct and compete as the correct statement. Statement a (loosely placed 'which') and c (missing full stop) are weaker, but no reasonable reading makes all four statements wrong.

### 1.3 UNANSWERABLE — cannot be answered as written

#### 2022 Q84 · general-intelligence-reasoning · `55de6b49-300e-4690-8476-ef74c9eeafbf`

**Stem.** In which direction is point P with respect to point A?

- **Keyed option:** (d) South -east
- **Reason.** The direction premise for this question is missing from the stored stem and is not found in any other row of the paper; no option can be checked.

#### 2022 Q85 · general-intelligence-reasoning · `1e3f9176-70fd-4b4e-bd2d-6192f383b72e`

**Stem.** Four of the following five are alike in a certain way and hence form a group. Which of the following does not belong to that group? [Option a: Q-C...]

- **Keyed option:** (b) P-F
- **Reason.** Odd-one-out pairs refer to a direction premise that is missing from the stored stem and from the rest of the paper; no option can be checked.

#### 2022 Q96 · quantitative-aptitude · `9d9dae9c-3c86-4be2-ba19-7b5477b51a14`

**Stem.** If total amount spends by A on EMI and house rent is 50% of his total monthly income and total amount pay by B for EMI is Rs. 15000, then find total saving of A (Given, A and B had only two expanses from their monthly income i.e., EMI and house rent).

- **Keyed option:** (b) 60000 Rs .
- **Reason.** The question refers to data (a chart or table of A's and B's expenses) that is not in the stem. With only 'A's expenses are 50% of income' and 'B's EMI is ₹15000', A's savings cannot be computed, so the keyed ₹60000 cannot be verified.

#### 2022 Q97 · quantitative-aptitude · `a69e7586-f670-45ed-80f1-9aff4dab7a3a`

**Stem.** The amount spends on house rent by A is Rs. 5000 more than that of B and total amount spends on house rent paid by A is Rs. 3000 more than total amount pays by him for EMI. If house rend paid by B is 1 3rd of the amount pays by A for EMI, then which of the following possible monthly income (in Rs.) of A.

- **Keyed option:** (a) 24000 Rs.
- **Reason.** The set depends on a chart or table that is not in the stem. The stem gives A's EMI ₹3000 and rent ₹6000 (expenses ₹9000), and every option exceeds ₹9000, so nothing picks out ₹24000 (which would make expenses 37.5% of income) without the missing data.

#### 2022 Q118 · quantitative-aptitude · `101f8b0b-71ec-48e8-aa11-f3c7aab5871a`

**Stem.** If 550 people living in the society, then find the people who do not like any of the three cars.

- **Keyed option:** (c) 65
- **Reason.** The correct count is 550 − 405 = 145, which is not among the options. The keyed 65 = 550 − 485 comes from adding the three car totals and double-counting the overlaps; the same region values reproduce the keys of questions 115, 116, 117 and 119, so the data are not at fault. The stored stem for this question omits the shared information of the set (questions 115 to 119); it is taken from questions 115 and 116.

#### 2023 Q152 · general-intelligence-reasoning · `d78ba3ec-9208-4d76-849c-d69ba1fee4c5`

**Stem.** Which of the following symbols should be placed in the blank spaces in order to complete the given expression in such a manner that makes the expressions ‘J ^ F’ and ‘K ? G’ true? K ? J % H ___ G ^ F ! E

- **Keyed option:** (e) Either
- **Reason.** The symbol legend that defines ^, +, %, ? and ! is missing from the stored stem and from neighbouring rows; without it the expression cannot be evaluated.

#### 2026 Q90 · english-language · `b3554c2a-529d-4259-bba0-62777526a715`

**Stem.** Directions (89 –91): In each of the following questions, a long, grammatically complex sentence has been segregated into five parts designated as (A), (B), (C), (D), and (E). These parts are jumbled. Choose the option that provides the most grammatically accurate and contextually coherent alignment of these segments. [Option a: CBDAE...]

- **Keyed option:** (a) CBDAE
- **Reason.** The stem gives only the directions; the five jumbled segments (A) to (E) are missing from the question text, so no order can be verified. The key (CBDAE) cannot be checked until the segments are restored.

#### 2026 Q91 · english-language · `13c64df1-9aff-429d-8a84-d316df3ca497`

**Stem.** Directions (89 –91): In each of the following questions, a long, grammatically complex sentence has been segregated into five parts designated as (A), (B), (C), (D), and (E). These parts are jumbled. Choose the option that provides the most grammatically accurate and contextually coherent alignment of these segments. [Option a: DEACB...]

- **Keyed option:** (a) DEACB
- **Reason.** The stem gives only the directions; the five jumbled segments (A) to (E) are missing from the question text, so no order can be verified. The key (DEACB) cannot be checked until the segments are restored.

### 1.4 Source data defects behind the flags

Most flags here come from the stored question, not from the examiner's key:

- **Option shift (2026 English Q100, 2026 reasoning Q187).** The first option's text slid onto the end of the stem (the stem ends
  "Only (I)" / "Only III"), so each remaining option text moved up one letter while the correct flag stayed on its letter. The
  proposed option in each case is the text the original key pointed to. The fix is to restore the option list, not to change the key.
- **Missing premise or parts (UNANSWERABLE rows).** The direction data for 2022 reasoning Q84–85, the symbol legend for 2023 Q152,
  the jumbled parts for 2026 English Q90–91, and the EMI/rent table for 2022 quant Q96–97 are absent from the stored text. 2022 quant
  Q118 has intact data but the correct count (145) is not among its options.
- **Stems without the shared premise.** Several set rows store only their own question line; they were solved from the premise
  carried by the other rows of the same set (noted in each row's `key_note`).

## 2. Current-affairs questions

Classified by one test: could a candidate reason to the answer, or only recall it? `current_affairs = yes` rows carry the
durable context (what the institution, index or instrument is) with the dated fact stated once; option rationales on
arbitrary figures or names say so in one line instead of inventing distinctions; traps appear only where a genuinely
confusable neighbour exists.

| Subject | current_affairs = yes | no | Total |
|---|---|---|---|
| general-intelligence-reasoning | 0 | 285 | 285 |
| english-language | 0 | 138 | 138 |
| quantitative-aptitude | 0 | 108 | 108 |
| **Total** | **0** | **531** | **531** |

On the 0 current-affairs rows: `common_traps` populated on 0, `explanation_text` on 0.

## 3. Numerical distractor rationales

340 rows carry `solution_steps` (numericals and derivation-type reasoning); they hold 1361 wrong-option
rationales. Each numerical distractor was run through a python brute-force over the question's own numbers and
intermediates, plus a fixed slip list (omitted step, intermediate given as answer, wrong percentage base, simple vs
compound, swapped ratio terms, upstream/downstream, per-unit vs total, un-doubled DI average, adjacent series term,
the other person or product).

- **1108** rationales name a wrong step or say what the solved arrangement actually gives.
- **253** are distractors no plausible slip reproduces. They do not use a bare 'does not follow' line; each states
  the value the working actually gives, e.g. "No likely slip gives 70; the working gives 64."
- **0** bare generic lines remain.

Most arbitrary distractors sit in quantitative-aptitude approximation, number-series and caselet items, where the
setter spaces wrong options around the key (often 10 or 100 apart) rather than building them from a slip. Looser
"close to the rounding" matches were rejected as coincidences, not steps a candidate would take.

## 4. Tag defects (flagged, not fixed)

`tag_suspect = yes` on 2 rows. No retagging has been done.

| Year/Q | Subject | Current `topic_name` | Question | Suggested topic |
|---|---|---|---|---|
| 2024 Q151 | general-intelligence-reasoning | Letter-to-symbol coding | What does ‘open’ mean in the code language? Statement I: ‘QR ST UA BQ RS’ means ‘new ye... | Topic should be Coding-decoding (word-to-code) data sufficiency. The codes stand for whole words; no letter-to-symbol substitution is tested. |
| 2025 Q109 | english-language | Phrasal verbs | During the audit, it was found that a senior employee had spilled the beans about the c... | Topic should be Idioms and phrases. 'Spill the beans' is an idiom, not a phrasal verb. |

## 5. Low-confidence rows

- **2022 Q69 · general-intelligence-reasoning · `55db1819-1aba-4cd7-b3f5-80e6de631ad6`** — Direction (69-73): Study the following information carefully and answer the questions given below: Eight persons sit in a row face north at consecutive multi...
  - Keyed: (b) 245m
  - Reason: The spacing clue ('consecutive multiple distance of 7m') cannot be met literally: with gaps of 7, 14 ... 49 m in any order, no seating has A 63 m left of S, R next to S and F as far right of R as A is left. It is relaxed to 'every seat is at a multiple of 7 m'; the clues then leave some distances open, and this draft uses the seating that matches the keys. W's seat 77 m left of R is taken from the keyed total.
- **2022 Q71 · general-intelligence-reasoning · `5fc97189-e9a9-45f6-9b13-41ec20ebb0b8`** — Direction (69-73): Study the following information carefully and answer the questions given below: Eight persons sit in a row face north at consecutive multi...
  - Keyed: (c) 147m
  - Reason: The spacing clue ('consecutive multiple distance of 7m') cannot be met literally: with gaps of 7, 14 ... 49 m in any order, no seating has A 63 m left of S, R next to S and F as far right of R as A is left. It is relaxed to 'every seat is at a multiple of 7 m'; the clues then leave some distances open, and this draft uses the seating that matches the keys.
- **2022 Q72 · general-intelligence-reasoning · `36376d88-1522-44db-99e7-6616dc1a4464`** — Four of the following five are alike in a certain way and hence form a group. Which of the following does not belong to that group? [Option a: W...]
  - Keyed: (e) U
  - Reason: The shared premise is not repeated in this row; solved from the premise of questions 69 to 73. The spacing clue ('consecutive multiple distance of 7m') cannot be met literally: with gaps of 7, 14 ... 49 m in any order, no seating has A 63 m left of S, R next to S and F as far right of R as A is left. It is relaxed to 'every seat is at a multiple of 7 m'; the clues then leave some distances open, and this draft uses the seating that matches the keys.
- **2022 Q73 · general-intelligence-reasoning · `91fc50b0-807a-4cf2-85e5-9143c05e5b1b`** — Which of the following statement is not true?
  - Keyed: (e) All are true
  - Reason: The shared premise is not repeated in this row; solved from the premise of questions 69 to 73. The spacing clue ('consecutive multiple distance of 7m') cannot be met literally: with gaps of 7, 14 ... 49 m in any order, no seating has A 63 m left of S, R next to S and F as far right of R as A is left. It is relaxed to 'every seat is at a multiple of 7 m'; the clues then leave some distances open, and this draft uses the seating that matches the keys.
- **2022 Q84 · general-intelligence-reasoning · `55de6b49-300e-4690-8476-ef74c9eeafbf`** — In which direction is point P with respect to point A?
  - Keyed: (d) South -east
  - Reason: The direction premise for this question is missing from the stored stem and is not found in any other row of the paper; no option can be checked.
- **2022 Q85 · general-intelligence-reasoning · `1e3f9176-70fd-4b4e-bd2d-6192f383b72e`** — Four of the following five are alike in a certain way and hence form a group. Which of the following does not belong to that group? [Option a: Q-C...]
  - Keyed: (b) P-F
  - Reason: Odd-one-out pairs refer to a direction premise that is missing from the stored stem and from the rest of the paper; no option can be checked.
- **2022 Q96 · quantitative-aptitude · `9d9dae9c-3c86-4be2-ba19-7b5477b51a14`** — If total amount spends by A on EMI and house rent is 50% of his total monthly income and total amount pay by B for EMI is Rs. 15000, then find total saving o...
  - Keyed: (b) 60000 Rs .
  - Reason: The question refers to data (a chart or table of A's and B's expenses) that is not in the stem. With only 'A's expenses are 50% of income' and 'B's EMI is ₹15000', A's savings cannot be computed, so the keyed ₹60000 cannot be verified.
- **2022 Q97 · quantitative-aptitude · `a69e7586-f670-45ed-80f1-9aff4dab7a3a`** — The amount spends on house rent by A is Rs. 5000 more than that of B and total amount spends on house rent paid by A is Rs. 3000 more than total amount pays ...
  - Keyed: (a) 24000 Rs.
  - Reason: The set depends on a chart or table that is not in the stem. The stem gives A's EMI ₹3000 and rent ₹6000 (expenses ₹9000), and every option exceeds ₹9000, so nothing picks out ₹24000 (which would make expenses 37.5% of income) without the missing data.
- **2023 Q103 · english-language · `0a6d3b53-6b00-47fe-b43a-13b11939310e`** — Four statements have been mentioned below. One or more statements may contain an error. It may contain a grammatical and/or a contextual error. Identify the ...
  - Keyed: (e) None of the above
  - Reason: Key e ('None of the above') is not defensible: statements b and d are grammatically and factually correct and compete as the correct statement. Statement a (loosely placed 'which') and c (missing full stop) are weaker, but no reasonable reading makes all four statements wrong.
- **2023 Q148 · general-intelligence-reasoning · `234dbd84-5690-4873-9ac0-92874577d847`** — Read the given information and answer the below questions. Below question consist of some conclusions followed by some statements in the option. Study the fo...
  - Keyed: (d) Only Water are Truck. Some Glass are Briefcase. No Umbrella is Glass. Some Water are Umbrella. All Briefcase are Charger.
  - Reason: Accepted as defensible. The word 'never' in conclusion III ('Some Truck can never be Charger') is read as a typo for 'Some Truck can be Charger', because as written d fails III: Truck is linked only to Water, with no chain to Charger. On that reading d satisfies all three. Another reading set aside: option c satisfies all three conclusions as printed, but in c conclusion II is certain (No Umbrella is Charger) rather than a possibility, the same convention used to accept the key in Q149.
- **2023 Q151 · general-intelligence-reasoning · `3f7eaa2b-ee6a-43ab-accc-e9730ebed8c6`** — Read the given information and answer the below questions. Below question consist of some conclusions followed by some statements in the option. Study the fo...
  - Keyed: (c) All Red are Chili. All Tomato are Garlic. Some Garlic are Carrot. No Chili is Carrot. Some Green are Chili. No Green is Garlic.
  - Reason: Accepted as defensible. The second 'not' in conclusion II ('Some Chili being not Garlic is not a possibility') is read as a typo, giving 'is a possibility'. As written, II needs All Chili to be Garlic for certain, and no option satisfies it (in c, Some Green are Chili and No Green is Garlic make some Chili certainly not Garlic), so e would be the literal answer. On the relaxed reading, c is the unique fit.
- **2023 Q152 · general-intelligence-reasoning · `d78ba3ec-9208-4d76-849c-d69ba1fee4c5`** — Which of the following symbols should be placed in the blank spaces in order to complete the given expression in such a manner that makes the expressions ‘J ...
  - Keyed: (e) Either
  - Reason: The symbol legend that defines ^, +, %, ? and ! is missing from the stored stem and from neighbouring rows; without it the expression cannot be evaluated.
- **2025 Q173 · general-intelligence-reasoning · `83e17d83-1102-4431-a2b7-f6593f40a058`** — Which number is third to the left of second word from the right end in Step II? A word and number arrangement machine when given an input line of numbers rea...
  - Keyed: (d) 63
  - Reason: Accepted as defensible. Another reading set aside: counting every element, the third to the left of design in Step II is 87 (option e); the key is accepted on the reading 'third number to the left of design', which gives 63.
- **2026 Q90 · english-language · `b3554c2a-529d-4259-bba0-62777526a715`** — Directions (89 –91): In each of the following questions, a long, grammatically complex sentence has been segregated into five parts designated as (A), (B), (...
  - Keyed: (a) CBDAE
  - Reason: The stem gives only the directions; the five jumbled segments (A) to (E) are missing from the question text, so no order can be verified. The key (CBDAE) cannot be checked until the segments are restored.
- **2026 Q91 · english-language · `13c64df1-9aff-429d-8a84-d316df3ca497`** — Directions (89 –91): In each of the following questions, a long, grammatically complex sentence has been segregated into five parts designated as (A), (B), (...
  - Keyed: (a) DEACB
  - Reason: The stem gives only the directions; the five jumbled segments (A) to (E) are missing from the question text, so no order can be verified. The key (DEACB) cannot be checked until the segments are restored.

| Confidence | Count |
|---|---|
| high | 436 |
| medium | 80 |
| low | 15 |

Medium rows are not listed; where a specific reservation exists it is in that row's `key_note`.

## 6. Field-population counts

| Field | Rows populated | Of 531 |
|---|---|---|
| `short_explanation` | 531 | 100% |
| `explanation_text` | 235 | 44% |
| `solution_steps` | 340 | 64% |
| `formula_used` | 120 | 23% |
| `common_traps` | 312 | 59% |
| `key_note` | 123 | 23% |
| `final_answer_option_id` | 519 | 98% |
| `option_rationales` (entries, not rows) | 2101 | — |

27 rationale entries are the fixed filler line ("Filler option; a correct answer is present.").

## 7. Validation

Enforced by the build script; the worksheet is written only when every check passes.

- **Row count:** 531 rows, one per input question.
- **Uniqueness:** 531 distinct `question_id` values.
- **Completeness:** the worksheet and input `question_id` sets are identical; `year`, `question_number`, `subject_slug`,
  `topic_name` are copied unchanged.
- **Option-rationale integrity:** 2101 entries, each keyed to an `option_id` and `label` on that question, no
  duplicates. Wrong options across the corpus: 2121. Every wrong option on an AGREE row is covered; the only gaps
  are options this draft argues are correct or defensible (proposed option on DISPUTED, co-defensible options on AMBIGUOUS).
- **No contradiction on AGREE rows:** no AGREE row carries a rationale against its own keyed option.
- **final_answer_option_id:** set on all 519 AGREE rows and equal to the input `correct_option_id`; null on every
  non-AGREE row.
- **Verdict integrity:** every DISPUTED row names a `proposed_correct_option_id` on that question and different from the key;
  no other row carries one. Every non-AGREE row and every low-confidence row carries a `key_note`.
- **Tag integrity:** `tag_suspect = yes` ⇔ non-empty `tag_note`. No `topic_name` modified.
- **Provenance:** every row `platform_original` / `owned` / `pending`.

## 8. Field and enum mapping against the live schema

**Table:** `public.pyq_question_explanations` (migration `230_pyq_question_explanations.sql`).
**Write path now exists** (EXPL-01 said none): `POST /admin/exam-intelligence-cms/pyq-question-explanations` (create,
always born `pending`), `PATCH .../{id}` (non-status fields), `POST .../{id}/review` (status transition through
`cms_review_pyq_question_explanation`). All in `app/backend/app/api/admin_exam_intel_cms.py`, `PERM_CMS`-gated and audited.

| Worksheet field | Column | Apply-step note |
|---|---|---|
| `question_id` | `question_id` | create-only; FK → `pyq_questions` |
| `short_explanation` | `short_explanation` | |
| `explanation_text` | `explanation_text` | empty string → NULL |
| `solution_steps` | `solution_steps` | JSON array — matches |
| `formula_used` | `formula_used` | **wrap**: the route rejects a string (422); send `[formula]` or `[]` |
| `common_traps` | `common_traps` | JSON array — matches |
| `option_rationales` | `option_rationales` | **fold**: the route rejects an array (422); send `{option_id: rationale}` |
| `final_answer_option_id` | `final_answer_option_id` | set on AGREE rows; route + trigger prove it belongs to the question |
| `proposed_correct_option_id` | — | not written; becomes `final_answer_option_id` only after a human decides the key |
| `key_verdict` | `ambiguity_status` | AGREE → `none`, DISPUTED → `disputed`, AMBIGUOUS → `multiple_possible`, UNANSWERABLE → `source_conflict` |
| `key_note`, `current_affairs`, `tag_suspect`, `tag_note`, `draft_confidence` | `metadata` | no dedicated columns |
| `explanation_source_type` / `license_status` / `reviewer_status` | same | `platform_original` / `owned` / `pending` (route forces `pending`) |

Constraints the apply step must respect:

- `unique (question_id, explanation_source_type)`: the create route returns 422 on a second `platform_original` row, so a
  re-run must PATCH existing `pending` rows, not re-POST.
- The review RPC and `pyq_question_explanations_guard` refuse `verified` while `ambiguity_status ≠ none` or
  `final_answer_option_id` is null — the 12 non-AGREE rows cannot be verified until the key is resolved.
- Editing learner-facing fields on a verified row downgrades it to `needs_correction`; the apply step should touch only
  `pending` rows.

## 9. Scope

RBI Grade B MCQs only — the 531 questions in the input file (descriptive questions excluded). No database writes, no migrations, no retagging, no change to
any question or option.

## 10. Ready-to-read sample (20 rows)

Chosen with `random.Random(20260923).sample(rows, 20)` over the worksheet rows in file order, then sorted by year, subject
and question number for reading. Re-running the same call on the same file yields the same 20.

---

### S1. 2022 Q40 · general-intelligence-reasoning · Step count and intermediate-step questions

`db6b34e4-2de1-44c4-a7d1-02ea70d4d773` · verdict AGREE · confidence high · current affairs no

**Question.** Direction ( 36-40): A word arrangement machine when given an input line of words rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: mgtuh kaops abewm bwxef mctqe aokpw Step I: oivuj maoru adeyo dyzeh oevse aomry Step II: adeyo aomry dyzeh maoru oevse oivuj Step III: adeoy amory dehyz amoru eeosv ijouv Step IV: 26 26 30 22 27 31 Step V: 3 4 4 8 8 9 Step V is the final step of given input. Answer the following questions based on the following input: - Input: helof kpest fumap hseub lmodu karlx Which among the following word is second to the left of third word from the right end in step II?

- (a) huoar
- (b) matnz
- (c) noofu
- (d) jenoh **← keyed**
- (e) jueud

**Short explanation.** Step II reads huoar jenoh jueud matnz mreuv noofu. The third word from the right is matnz, and the second word to its left is jenoh.

**Explanation.** The machine works like this. Step I: every consonant moves two letters forward (h becomes j, k becomes m) and vowels stay. Step II: the words are sorted alphabetically. Step III: the letters inside each word are sorted alphabetically. Step IV: each word becomes the sum of the alphabet places of its first and last letters. Step V: each number becomes the sum of its digits, and the results are arranged in ascending order. For the input helof kpest fumap hseub lmodu karlx: Step I is jenoh mreuv huoar jueud noofu matnz; Step II is huoar jenoh jueud matnz mreuv noofu; Step III is ahoru ehjno dejuu amntz emruv fnoou; Step IV is 22 20 25 27 27 27; Step V is 2 4 7 9 9 9.

**Why the other options are wrong**

- (a) huoar is third to the left of matnz, the leftmost word.
- (b) matnz is the reference word itself, third from the right.
- (c) noofu is the rightmost word, to the right of matnz.
- (e) jueud is immediately left of matnz, only one place away.

**Solution steps**

1. From the example, Step I shifts each consonant two letters forward and keeps vowels: helof kpest fumap hseub lmodu karlx becomes jenoh mreuv huoar jueud noofu matnz.
2. Step II sorts the words alphabetically: huoar jenoh jueud matnz mreuv noofu. Step III sorts letters inside each word: ahoru ehjno dejuu amntz emruv fnoou.
3. Step IV adds the alphabet places of each word's first and last letters: 22 20 25 27 27 27. Step V takes digit sums in ascending order: 2 4 7 9 9 9.
4. Step II: huoar jenoh jueud matnz mreuv noofu. Third from right = matnz.
5. Moving two words left from matnz: jueud, then jenoh.

---

### S2. 2022 Q44 · general-intelligence-reasoning · Odd-one-out within an arrangement

`e17365e5-a70d-453d-8339-f4b26bdad071` · verdict AGREE · confidence medium · current affairs no

**Question.** Four of the following five are alike in a certain way and thus form a group. Who among the following does not belong to the group? [Option a: A...]

- (a) A
- (b) I
- (c) B
- (d) D
- (e) H **← keyed**

**Short explanation.** A, I, B and D live on odd-numbered floors (third and first), while H lives on the second floor, so H is the odd one out.

**Explanation.** Third floor, west to east: A in flat 1 (Iran), I in flat 2 (Korea), C in flat 3 (Japan). Second floor: H in flat 1 (USA), E in flat 2 (Oman), G in flat 3 (UK). First floor: D in flat 1 (Russia), F in flat 2 (Malta), B in flat 3 (UAE). A and I are on the third floor and B and D on the first; H is the only one of the five on an even floor.

**Why the other options are wrong**

- (a) A lives on the third floor, an odd floor, like the group.
- (b) I lives on the third floor, an odd floor, like the group.
- (c) B lives on the first floor, an odd floor, like the group.
- (d) D lives on the first floor, an odd floor, like the group.

**Solution steps**

1. F is two floors below the Korea person, so Korea is on the third floor and F on the first floor, in flat 2 (an even flat). B and the USA person are in odd flats with B to the south-east, so USA is in flat 1 and B in flat 3; B's odd floor below USA makes it the first floor.
2. Japan is above B in flat 3 and E is immediately south-west of Japan. Japan on the second floor would put E in F's flat, so Japan is on the third floor, flat 3, and E is on the second floor, flat 2. G is east of H on E's floor, so H is in flat 1 and G in flat 3.
3. C is north-east of the USA person, so USA is H (second floor, flat 1) and C is on the third floor. A is on the third floor immediately west of Korea, so A is in flat 1 and Korea in flat 2; C, who is not Korea, is in flat 3 with Japan, and I is the Korea person. D lives below A in flat 1, which leaves the first floor, flat 1.
4. The UAE person is on D's floor but not in flat 2, so B goes to UAE. Oman is west of G, so E goes to Oman. Malta is two floors from I and south-east of Iran, so F goes to Malta and A to Iran. D does not go to UK, so D goes to Russia and G to UK.
5. A and I live on the third floor, B and D on the first floor; H lives on the second floor.

**Key note.** The shared premise is not repeated in this row; solved from the premise of questions 43 to 47.

---

### S3. 2022 Q46 · general-intelligence-reasoning · Floor and flat double-variable puzzle

`84c15ec6-0735-48a9-a993-16c0638ba83d` · verdict AGREE · confidence high · current affairs no

**Question.** Direction (43-47): Study the following information carefully and answer the questions given below. Nine persons live in three floored building marked 1 to 3 from bottom to top respectively. There are three flats on each floor viz. - flat 1, flat 2, and flat 3 from west to east respectively. Only one person lives in each flat. Each person goes to different countries i.e. Iran, USA, Russia, Korea, Oman, Malta, Japan, UK and UAE but not necessarily in the same order. A lives on an odd numbered floor to the immediate west of the one who goes to Korea. F lives two floors below the one who goes to Korea. F lives in an even numbered flat. B lives to the south east flat of the one who goes to USA. B and the one who goes to USA live in odd numbered flat. B lives on an odd numbered floor. C doesn’t go to Korea. C lives to the north east flat of the one who goes t o USA. D lives below A in the same flat with A. The one who goes to UAE lives on the same floor with D but in different flat as F’s flat. The one who goes to Japan lives above B’s flat. E lives to the immediate south west of the one who goes to Japan. G li ves to the east of H in the same floor with E. The one who goes to Oman lives to the west of G. One floor gap is there between I and the one who goes to Malta. The one who goes to Malta lives to the south east of the one who goes to Iran. D doesn’t go to UK. In which among the following floor and flat does G live?

- (a) Floor 2, flat 3 **← keyed**
- (b) Floor 2, flat 2
- (c) Floor 3, flat 3
- (d) Floor 1, flat 2
- (e) None of these

**Short explanation.** G lives on E's floor (the second) to the east of H, and the third flat is the only flat east of both H and E, so G is on floor 2, flat 3.

**Explanation.** Third floor, west to east: A in flat 1 (Iran), I in flat 2 (Korea), C in flat 3 (Japan). Second floor: H in flat 1 (USA), E in flat 2 (Oman), G in flat 3 (UK). First floor: D in flat 1 (Russia), F in flat 2 (Malta), B in flat 3 (UAE). G is on floor 2, flat 3.

**Why the other options are wrong**

- (b) Floor 2, flat 2 is E.
- (c) Floor 3, flat 3 is C.
- (d) Floor 1, flat 2 is F.
- (e) Filler option; a correct answer is present.

**Solution steps**

1. F is two floors below the Korea person, so Korea is on the third floor and F on the first floor, in flat 2 (an even flat). B and the USA person are in odd flats with B to the south-east, so USA is in flat 1 and B in flat 3; B's odd floor below USA makes it the first floor.
2. Japan is above B in flat 3 and E is immediately south-west of Japan. Japan on the second floor would put E in F's flat, so Japan is on the third floor, flat 3, and E is on the second floor, flat 2. G is east of H on E's floor, so H is in flat 1 and G in flat 3.
3. C is north-east of the USA person, so USA is H (second floor, flat 1) and C is on the third floor. A is on the third floor immediately west of Korea, so A is in flat 1 and Korea in flat 2; C, who is not Korea, is in flat 3 with Japan, and I is the Korea person. D lives below A in flat 1, which leaves the first floor, flat 1.
4. The UAE person is on D's floor but not in flat 2, so B goes to UAE. Oman is west of G, so E goes to Oman. Malta is two floors from I and south-east of Iran, so F goes to Malta and A to Iran. D does not go to UK, so D goes to Russia and G to UK.
5. G lives on the second floor in flat 3.

---

### S4. 2022 Q70 · general-intelligence-reasoning · Direction of one point relative to another

`aec19373-d886-4a49-a548-de39a939ca2a` · verdict AGREE · confidence medium · current affairs no

**Question.** Direction (69-73): Study the following information carefully and answer the questions given below: Eight persons sit in a row face north at consecutive multiple distance of 7m. All the persons face towards north. A sits 63m left of S. R sits immediate right of S. Distance between A and R is same as the distance between F and R. Difference between the total distance of W and D to the total distance of D and Y is 7m. Now F goes in the north and walks 50m to reach point C then, takes right turn and walks 98m to reach at point K after that F in the North-west of U. W goes in the south and walks 20m to reach point Q then he takes his left and walks some distance to reach south of R. In which direction is point C with respect to point Q?

- (a) North -east **← keyed**
- (b) South -west
- (c) North
- (d) South -east
- (e) North -west

**Short explanation.** C is 50 m north of F's seat, and Q is 20 m south of W's seat. F sits to the right (east) of W, so C lies north-east of Q.

**Explanation.** All eight face north, so left is west and right is east. From the left end: A at 0 m, W at 28 m, S at 63 m, R at 105 m, D at 126 m, F at 210 m, Y at 217 m and U at 315 m. A to R and R to F are both 105 m, and W to D (98 m) and D to Y (91 m) differ by 7 m. F walks 50 m north to C and 98 m east to K, 308 m from A's line and north-west of U. W walks 20 m south to Q, turns left (east) and walks 77 m to stand south of R.

**Why the other options are wrong**

- (b) South-west is the direction of Q from C, the reverse.
- (c) C is also far east of Q, so it is not due north.
- (d) C is north of Q, not south.
- (e) C is east of Q, since F sits right of W.

**Solution steps**

1. A sits at the left end with S 63 m to A's right; R sits immediately right of S.
2. W walks south, turns left (east) and stops south of R, so W sits left of R. F sits as far right of R as A is left of it.
3. F ends 98 m east of its seat and 50 m north, north-west of U, so U sits more than 98 m right of F.
4. Taking A 0 m, W 28 m, S 63 m, R 105 m, D 126 m, F 210 m, Y 217 m and U 315 m meets these clues: A to R = R to F = 105 m, and 98 m − 91 m = 7 m for W to D against D to Y.
5. C is 50 m north of F (210 m); Q is 20 m south of W (28 m).
6. C is both north and east of Q: north-east.

**Key note.** The spacing clue ('consecutive multiple distance of 7m') cannot be met literally: with gaps of 7, 14 ... 49 m in any order, no seating has A 63 m left of S, R next to S and F as far right of R as A is left. It is relaxed to 'every seat is at a multiple of 7 m'; the clues then leave some distances open, and this draft uses the seating that matches the keys.

---

### S5. 2022 Q75 · general-intelligence-reasoning · Statement and inference

`f0bc42b4-e2c9-428f-88a9-a547d7d0b055` · verdict AGREE · confidence high · current affairs no

**Question.** Obesity is a medical condition in which excess body fat has accumulated to the extent that it may have an adverse effect on a person's health, leading to reduced life expectancy and/or increased health problems. In other words, it means to be dangerously overweight. Obesity is a leading preventable cause of death worldwide, with increasing prevalence in adults and children, and authorities view it as one of the most serious public health problems of the 21st century. Which of the following can be concluded from the above statement?

- (a) Food is often regarded as the factor of sins of sloth
- (b) Obesity is a one of the serious problems nowadays seen in children and adults. **← keyed**
- (c) Obesity is a problem that requires lots of money for its treatment.
- (d) Obesity increases the risk of only heart and kidney diseases.
- (e) Both (b) and (d)

**Short explanation.** The passage says obesity is increasing in adults and children and is one of the most serious public-health problems of the century, which option b restates.

**Why the other options are wrong**

- (a) The passage does not link food with the sin of sloth.
- (c) The cost of treatment is never discussed.
- (d) The passage speaks of health problems generally; 'only heart and kidney diseases' is not stated.
- (e) d does not follow, so 'both b and d' fails.

---

### S6. 2022 Q104 · quantitative-aptitude · Inequalities and relationship determination

`3d527df2-33c0-4f23-8215-bf08d26dde71` · verdict AGREE · confidence medium · current affairs no

**Question.** Given, p > 1 > q > 0. Quantity I: Value of p3−q3 p−q −3pq. Quantity II: Value of (1 −1 q)

- (a) Quantity I = Quantity II or no relation
- (b) Quantity I ≤ Quantity II
- (c) Quantity I ≥ Quantity II
- (d) Quantity I < Quantity II
- (e) Quantity I > Quantity II **← keyed**

**Short explanation.** (p³ − q³)/(p − q) = p² + pq + q², so Quantity I = p² − 2pq + q² = (p − q)², which is positive because p and q differ. Quantity II, 1 − 1/q, is negative because 0 < q < 1 makes 1/q greater than 1. So Quantity I > Quantity II.

**Why the other options are wrong**

- (a) A clear relation exists: Quantity I is positive and Quantity II negative.
- (b) Quantity I is always the larger.
- (c) Loosely true, since Quantity I is always greater, but equality never occurs, so the strict relation in option e is the precise answer and the key.
- (d) Quantity I is always the larger.

**Solution steps**

1. (p³ − q³) ÷ (p − q) = p² + pq + q².
2. Quantity I = p² + pq + q² − 3pq = (p − q)², which is positive since p > 1 > q.
3. Quantity II = 1 − 1/q; with 0 < q < 1, 1/q > 1, so Quantity II is negative.
4. A positive number exceeds a negative one: Quantity I > Quantity II.

**Formula.** a³ − b³ = (a − b)(a² + ab + b²)

**Common traps**

- Expanding p³ − q³ as (p − q)³ and getting a wrong Quantity I.

**Key note.** Stem is garbled; Quantity II '(1 −1 q)' is read as 1 − 1/q. Another reading set aside: 1 − q would make the comparison depend on the values of p and q. Option c (Quantity I ≥ Quantity II) is also loosely true since Quantity I is always greater; the strict option e is the one accepted.

---

### S7. 2024 Q85 · english-language · Explicit detail retrieval

`1f2eedc8-c1df-47d7-afe3-77506aa97fcc` · verdict AGREE · confidence high · current affairs no

**Question.** Read the following passage carefully and answer the questions that follow. The United States and Malaysia have long-standing trade rela- tions that play a significant role in both economies. Malaysia, as one of Southeast Asia’s most rapidly growing economies, has emerged as a key trading partner for the U.S. This partnership is underpinned by trade in goods, services, and investment, with the U.S. being one of Malaysia’s largest foreign inves- tors. Central to this relationship are sectors such as electronics, machinery, petroleum products, and medical devices, which are exported to the U.S. In return, Malaysia imports American goods, including aircraft, machinery, agricultural products, and technology-driven equipment. One of the critical areas where trade intersects is intellectual property (IP) protection, especially patents. In recent years, the importance of intellectual property has grown substantially as innovation becomes a key driver of economic growth. For Ma- laysia, ensuring a robust patent system is essential for attracting foreign direct investment (FDI) and fostering domestic innova- tion. However, patent registration and enforcement in Malaysia present unique challenges, particularly for foreign companies, including those from the U.S. In a globalized economy, patents act as a vital tool for protecting intellectual property, encouraging innovation, and providing companies with the legal right to exclude others from making, using, or selling their inventions. In the context of U.S.-Malay- sia trade, patents are especially crucial in sectors such as bio- technology, pharmaceuticals, medical devices, and electronics, where research and development (R&D) costs are high, and the risk of intellectual property theft is significant. American companies often hold valuable patents on cut- ting-edge technologies, and protecting these patents in foreign markets like Malaysia is essential for safeguarding their compet- itive advantage. The U.S. government has been actively working with Malaysia to strengthen the protection of intellectual proper- ty rights (IPR), and Malaysia has made strides in improving its patent laws to align with international standards. Despite improvements, U.S. companies face several challeng- es in securing patents in Malaysia. The process of registering patents in Malaysia can be ________. The Intellectual Property Corporation of Malaysia (MyIPO) handles patent applications, but delays are common, often due to a backlog of pending applications. For U.S. businesses, these delays can hinder their ability to launch products and gain market access promptly. Additionally, Malaysia operates under a first-to-file system, meaning the first party to file a patent application has the rights to the patent, regardless of the original inventor. This system contrasts with the first-to-invent system once used in the U.S. Although the U.S. has now shifted to a first-to-file system, the transition was smoother due to extensive infrastructure and support mechanisms in place, which Malaysia may still be developing. Another challenge is the enforcement of patent rights. Even after securing a patent, ensuring its enforcement can be prob- lematic. In some cases, U.S. companies have faced difficulties when attempting to enforce their patents in Malaysia’s legal system due to inconsistencies in court rulings and the high costs associated with legal disputes. Furthermore, counterfeit goods and patent infringement remain issues that deter foreign inves- tors, particularly those from the U.S., from fully capitalizing on the Malaysian market. To address these challenges, Malaysia has undertaken several reforms. The government is working to streamline the patent registration process and strengthen the legal framework for IP protection. Initiatives such as increasing the efficiency of MyIPO and enhancing judicial expertise in IP-related cases are underway to improve enforcement and reduce processing times. Additionally, collaboration between U.S. companies and local Malaysian firms is being encouraged. By sharing knowledge and resources, both parties can benefit from better patent pro- tection and innovation growth. Through continued cooperation, Malaysia and the U.S. can ensure a mutually beneficial trade relationship that fosters innovation, protects intellectual proper- ty, and promotes economic growth. As both nations continue to focus on trade expansion and tech- nological innovation, overcoming the hurdles in patent registra- tion and enforcement will be crucial in maintaining the strength of their economic ties. How does Malaysia’s patent system differ from the system originally used in the U.S.?

- (a) Malaysia operates under a first-to-file system, while the U.S. initially used a first-to-invent system. **← keyed**
- (b) Malaysia and U.S. both use the first-to-invent system.
- (c) Malaysia uses the first-to-develop system, while the U.S. originally used a first-to-file system.
- (d) Malaysia and the U.S. both originally used a first-to-market system.
- (e) Malaysia uses a first-to-register system, while the U.S. originally had no patent system.

**Short explanation.** The passage says 'Malaysia operates under a first-to-file system' and that this 'contrasts with the first-to-invent system once used in the U.S.' Option a states exactly that contrast.

**Why the other options are wrong**

- (b) Malaysia uses first-to-file, not first-to-invent, and the U.S. has now moved to first-to-file too.
- (c) The passage has no 'first-to-develop' system, and the U.S. originally used first-to-invent, not first-to-file.
- (d) No 'first-to-market' system is mentioned for either country.
- (e) The passage says the U.S. originally used first-to-invent, so it did have a patent system; 'first-to-register' is not the passage's term.

**Common traps**

- Reading 'Although the U.S. has now shifted to a first-to-file system' and forgetting that the question asks about the system the U.S. originally used.

---

### S8. 2024 Q91 · english-language · Content Relevance

`26cf7b6a-d990-4290-a8a6-5212dd31dd7f` · verdict AGREE · confidence medium · current affairs no

**Question.** Below are five mixed-up sentences related to the topic of social health. Four of these sentences can be arranged to create a coherent paragraph. Determine which sentence does not fit with the others.

- (a) Social health encompasses the ability to form and maintain meaningful relationships, engage in community activities, and contribute to the well-being of others.
- (b) Research has shown that physical health and social health are interconnected, with one influencing the other significantly. **← keyed**
- (c) Strong social connections are linked to improved mental health outcomes, including reduced stress levels and a greater sense of belonging.
- (d) Building and nurturing positive relationships can enhance one’s social support network, which is crucial for emotional resilience and overall life satisfaction.
- (e) Community programs and social initiatives play a vital role in promoting social health by providing opportunities for people to connect and support each other.

**Short explanation.** The paragraph is about social health: what it is (a), how social connections help mental health (c), how relationships build support (d) and how community programmes promote it (e). Sentence b shifts to the link between physical and social health, which the others never take up.

**Why the other options are wrong**

- (a) This defines social health and is the natural opening of the paragraph.
- (c) This gives a benefit of social connections and fits the paragraph's theme.
- (d) This explains how relationships strengthen support networks and fits the theme.
- (e) This shows how community programmes promote social health and fits as a closing line.

**Common traps**

- Picking c because it mentions 'mental health'; it is still about the benefits of social connections, while b brings in physical health, which no other sentence follows up.

---

### S9. 2024 Q107 · english-language · Content Relevance

`c928fa13-43e2-46b1-a706-4201a2eda361` · verdict AGREE · confidence high · current affairs no

**Question.** In the question below, five sentences are provided, with one sentence omitted and replaced by a blank. These sentences are jumbled randomly. Answer the questions that follow. A) Food and drink producers are aware of certain aspects of human psychology. B) . ________________________________________________ _______________. C) It is a component associated with various negative health effects and could potentially harm our brain health. D) These companies also leverage brain science to encourage purchases by adding sugars to their products. E) They apply this knowledge to refine marketing and branding strategies that divert our attention from the unhealthy products they sell and prompt us to make impulsive or emotionally-driven purchases. Which of the following sentences can fill in the blank?

- (a) The fundamental layout of a grocery store is designed to keep customers engaged and encourage them to purchase items, even if they aren’t needed.
- (b) Sugar is a chemical substance produced from the conversion of carbohydrates into energy.
- (c) Surprising research reveals that approximately seventy percent of foods and beverages in grocery stores contain added sugar. **← keyed**
- (d) The sugars found in fruits differ from those derived from processed carbohydrates.
- (e) Grocery stores are mere agents of distribution, and they cannot be blamed for the quality of products that is given by the manufacturers.

**Short explanation.** Sentence D says companies add sugars to products, and sentence C begins 'It is a component associated with various negative health effects'. The missing sentence must sit between them and make sugar its subject: 'approximately seventy percent of foods and beverages in grocery stores contain added sugar' does exactly that.

**Why the other options are wrong**

- (a) Store layout is off the topic of added sugar, and it gives C's 'It' nothing to refer to.
- (b) This defines sugar incorrectly and does not link the companies' added sugar in D to its harms in C.
- (d) Comparing fruit sugar with processed sugar breaks the link between D and C; the passage is about added sugar, not types of sugar.
- (e) This defends grocery stores, which the passage never blames, and gives C's 'It' nothing to refer to.

**Common traps**

- Choosing b because it mentions sugar; the blank must continue the point about added sugar in products and set up C's warning.

---

### S10. 2024 Q184 · general-intelligence-reasoning · Floor and flat double-variable puzzle

`4fa5164f-4522-42bc-80be-d3e416f3a822` · verdict AGREE · confidence high · current affairs no

**Question.** Study the following information carefully and answer the below questions. Eight persons namely – A, B, C, D, E, F, G and H lives in eight floored building marked 1 to 8 in such a way that lowermost floor is marked as 1, floor above it is marked as 2 and so on till the top most floor is marked as 8. Each person likes a different fruit amongst watermelon, mango, grapes, apple, banana, guava, orange and kiwi. Each person stays at a different place amongst Nagpur, Chile, Delhi, Indore, Paris, London, Bihar and Tokyo. All the given information is not necessarily in the same order. The one who stays at Tokyo lives in an even numbered floor at a gap of two floors from the one who likes Grapes. G doesn’t live on the lowermost floor but lives just below the one who likes watermelon. Only three person lives between G and the one who stays at Nagpur. The one who likes Watermelon lives on an even numbered floor but doesn’t live on the top most floor. Only one person lives between the one who was likes Apple and H, who stays at Indore. C neither lives adjacent to G nor adjacent to H but lives adjacent to the one who likes Guava. One who stays at Paris lives just above the one who likes Banana. One who likes Grapes stays at Chile, who doesn’t live adjacent to the one who stays at Indore. A neither lives adjacent to C nor adjacent to H but lives at a gap of one floor with the one who likes Mango. Only two person lives between E and D, who doesn’t live in the adjacent floor of the one who stays at Bihar. One who likes Orange lives at a gap of two from the one who stays at Paris. At least four persons live between the one who stays at Delhi and F, who does not like Apple. E lives on one of the floors below B, who neither live on the top most floor nor stays at London. The one who likes Apple doesn’t live adjacent to the one who likes Guava. The one who likes Apple does not live adjacent to D, but lives just above the one who stays at Nagpur. D does not like Guava. One who likes Kiwi lives at a gap of one floor with the one who stays at London. How many people stay between the person who likes Banana and the person who stays in Bihar?

- (a) Two
- (b) Five
- (c) Three **← keyed**
- (d) One
- (e) Four

**Short explanation.** Banana is on the seventh floor and Bihar on the third. The people on floors 6, 5 and 4 lie between them: three persons.

**Explanation.** From the top floor down: floor 8 A (Apple, Paris), floor 7 F (Banana, Nagpur), floor 6 H (Mango, Indore), floor 5 D (Orange, London), floor 4 B (Watermelon, Tokyo), floor 3 G (Kiwi, Bihar), floor 2 E (Guava, Delhi), floor 1 C (Grapes, Chile). 'At a gap of one floor' is read as one floor in between, and 'a gap of two floors' as two floors in between. Between Banana (floor 7) and Bihar (floor 3) live H, D and B: three persons.

**Why the other options are wrong**

- (a) Two leaves out one of H, D and B, who are all between the seventh and third floors.
- (b) Five overcounts; only floors 6, 5 and 4 lie between.
- (d) One is too few; three floors lie between the seventh and third floors.
- (e) Four counts one of the end floors as well.

**Solution steps**

1. Watermelon is on an even floor below the top and G lives just below it, so G is on the third or fifth floor. Nagpur has three people between it and G, and Apple is just above Nagpur. Only G on the third floor works: Watermelon on the fourth floor, Nagpur on the seventh and Apple on the eighth.
2. H, at Indore, has one floor between him and Apple, so H is on the sixth floor. Paris is just above Banana and Orange has two floors between it and Paris, which puts Paris on the eighth floor, Banana on the seventh and Orange on the fifth.
3. E and D have two floors between them, E is below B, and A is next to neither C nor H. This places A on the eighth floor, F on the seventh, D on the fifth, B on the fourth, E on the second and C on the first; A has one floor between him and Mango, so Mango is on the sixth floor with H.
4. Grapes is at Chile, not next to Indore, and Tokyo (even floor) has two floors between it and Grapes: Grapes and Chile on the first floor, Tokyo on the fourth. C is next to Guava, so Guava is on the second floor (E); Kiwi goes to the third floor (G). Kiwi has one floor between it and London, so London is on the fifth floor; Delhi is at least five floors from F, so Delhi is on the second floor and Bihar on the third.
5. Floors 6, 5 and 4 lie between floor 7 and floor 3: three persons.

---

### S11. 2024 Q134 · quantitative-aptitude · Caselet data interpretation

`ffc0de0b-e1b0-4992-8699-2fcad9ee0601` · verdict AGREE · confidence high · current affairs no

**Question.** Study the following information carefully and answer the questions given beside: There are four studios P, Q, R and S of a renowned news channel “The Republic TV”. The number of reporters in studio S is 450 more than the number of reporters in studio R and 1650 less than the number of reporters in studio P. The number of reporters in studio Q is 24 more than 4.6 times of the number of computer operators in that studio. The number of reporters in studio R is 60 less than 3.8 times the number of computer operators in studio S. The number of computer operators in studio S is 125 more than that of computer operators in studio P and 160 less than that of computer operators in studio Q. The number of computer operators in studio P and that in studio R are 825 and 1200 respectively. The number of female reporters in studio P is 40% of the total number of reporters in studio Q. The number of female computer operators in studio P is 48% of the total number of computer operators in studio S. The number of male reporters in studio R is 5 times of the number of female computer operators in studio P. The number of male reporters in studio S is double the number of female reporters in studio R. The number of male reporters in studio Q is 2250 more than the number of male reporters in studio R. The number of male computer operators in studio Q is 16% of the total number of reporters of studio S. The number of female computer operators in studio R is 60 less than that of male computer operators in studio Q. The number of male computer operators in studio S is 1.5 times that of female computer operators in studio Q. What is the difference between the number of male reporters in studios P, Q and R together and the number of male computer operators in all the studios together?

- (a) 8074 **← keyed**
- (b) 8096
- (c) 8084
- (d) 8062
- (e) 8080

**Short explanation.** Male reporters in P, Q and R total 3598 + 4530 + 2280 = 10408. Male computer operators in all four studios total 369 + 640 + 620 + 705 = 2334. The difference is 8074.

**Explanation.** Working through the statements in order gives the full table. Computer operators: P 825, Q 1110, R 1200, S 950. Reporters: P 5650, Q 5130, R 3550, S 4000. Reporters by gender (male, female): P 3598 and 2052, Q 4530 and 600, R 2280 and 1270, S 2540 and 1460. Computer operators by gender (male, female): P 369 and 456, Q 640 and 470, R 620 and 580, S 705 and 245.

**Why the other options are wrong**

- (b) No likely slip gives 8096; the working gives 10408 − 2334 = 8074.
- (c) No likely slip gives 8084; the working gives 10408 − 2334 = 8074.
- (d) No likely slip gives 8062; the working gives 10408 − 2334 = 8074.
- (e) No likely slip gives 8080; the working gives 10408 − 2334 = 8074.

**Solution steps**

1. Computer operators: S = 825 + 125 = 950, Q = 950 + 160 = 1110 (P 825, R 1200 given).
2. Reporters: Q = 24 + 4.6 × 1110 = 5130; R = 3.8 × 950 − 60 = 3550; S = 3550 + 450 = 4000; P = 4000 + 1650 = 5650.
3. Female reporters in P = 40% of 5130 = 2052; female operators in P = 48% of 950 = 456; male reporters in R = 5 × 456 = 2280, so female reporters in R = 1270.
4. Male reporters in S = 2 × 1270 = 2540; male reporters in Q = 2280 + 2250 = 4530. Male operators in Q = 16% of 4000 = 640; female operators in R = 640 − 60 = 580; male operators in S = 1.5 × 470 = 705.
5. Male reporters P + Q + R = 10408; male operators = 369 + 640 + 620 + 705 = 2334; difference = 8074.

**Common traps**

- Leaving out studio P's male operators (825 − 456 = 369), which are not stated directly.

---

### S12. 2024 Q135 · quantitative-aptitude · Caselet data interpretation

`a81c1d87-42b5-4834-bb3b-08a817888c93` · verdict AGREE · confidence high · current affairs no

**Question.** Study the following information carefully and answer the questions given beside: There are four studios P, Q, R and S of a renowned news channel “The Republic TV”. The number of reporters in studio S is 450 more than the number of reporters in studio R and 1650 less than the number of reporters in studio P. The number of reporters in studio Q is 24 more than 4.6 times of the number of computer operators in that studio. The number of reporters in studio R is 60 less than 3.8 times the number of computer operators in studio S. The number of computer operators in studio S is 125 more than that of computer operators in studio P and 160 less than that of computer operators in studio Q. The number of computer operators in studio P and that in studio R are 825 and 1200 respectively. The number of female reporters in studio P is 40% of the total number of reporters in studio Q. The number of female computer operators in studio P is 48% of the total number of computer operators in studio S. The number of male reporters in studio R is 5 times of the number of female computer operators in studio P. The number of male reporters in studio S is double the number of female reporters in studio R. The number of male reporters in studio Q is 2250 more than the number of male reporters in studio R. The number of male computer operators in studio Q is 16% of the total number of reporters of studio S. The number of female computer operators in studio R is 60 less than that of male computer operators in studio Q. The number of male computer operators in studio S is 1.5 times that of female computer operators in studio Q. In which studio are male reporters the maximum and female computer operators the minimum respectively?

- (a) Q and S **← keyed**
- (b) P and S
- (c) Q and P
- (d) P and P
- (e) R and S

**Short explanation.** Male reporters are highest in studio Q (4530). Female computer operators are lowest in studio S (245).

**Explanation.** Working through the statements in order gives the full table. Computer operators: P 825, Q 1110, R 1200, S 950. Reporters: P 5650, Q 5130, R 3550, S 4000. Reporters by gender (male, female): P 3598 and 2052, Q 4530 and 600, R 2280 and 1270, S 2540 and 1460. Computer operators by gender (male, female): P 369 and 456, Q 640 and 470, R 620 and 580, S 705 and 245.

**Why the other options are wrong**

- (b) Studio P has 3598 male reporters, fewer than Q's 4530.
- (c) Studio P has 456 female operators, more than S's 245.
- (d) Studio P leads on neither count: Q has more male reporters and S fewer female operators.
- (e) Studio R has only 2280 male reporters, the lowest.

**Solution steps**

1. Computer operators: S = 825 + 125 = 950, Q = 950 + 160 = 1110 (P 825, R 1200 given).
2. Reporters: Q = 24 + 4.6 × 1110 = 5130; R = 3.8 × 950 − 60 = 3550; S = 3550 + 450 = 4000; P = 4000 + 1650 = 5650.
3. Female reporters in P = 40% of 5130 = 2052; female operators in P = 48% of 950 = 456; male reporters in R = 5 × 456 = 2280, so female reporters in R = 1270.
4. Male reporters in S = 2 × 1270 = 2540; male reporters in Q = 2280 + 2250 = 4530. Male operators in Q = 16% of 4000 = 640; female operators in R = 640 − 60 = 580; male operators in S = 1.5 × 470 = 705.
5. Male reporters: P 3598, Q 4530, R 2280, S 2540, so Q is highest. Female operators: P 456, Q 470, R 580, S 245, so S is lowest.

**Common traps**

- Comparing total reporters (P has the most, 5650) instead of male reporters.

---

### S13. 2025 Q103 · english-language · Logical Order

`9fafc648-0993-4b27-8e59-9a27f5692f29` · verdict AGREE · confidence high · current affairs no

**Question.** (A) She drafted a list of interview questions to keep the discussion focused. (B) Before meeting the artisan, Mira researched traditional weaving patterns. (C) The published article highlighted how modern designs preserved heritage. (D) During the interview, she noticed subtle updates in the motifs. Rearrange the following five sentences (A), (B), (C) and (D) in the proper sequence to form a meaningful paragraph and then answer the question given below.

- (a) B A D C **← keyed**
- (b) A B D C
- (c) B D A C
- (d) D A B C
- (e) A D B C

**Short explanation.** The story runs in time order: Mira researched weaving patterns before the meeting (B), drafted interview questions (A), noticed changes in the motifs during the interview (D), and the published article came last (C). So the order is B A D C.

**Why the other options are wrong**

- (b) Starts with drafting questions, but B says 'Before meeting the artisan' she researched, which should open the account.
- (c) Puts the interview (D) before drafting questions (A), but questions are prepared before an interview.
- (d) Opens with 'During the interview', yet research and preparation must come first.
- (e) Puts the interview before the research that B says came 'before meeting the artisan'.

**Common traps**

- Both A and B are preparation steps; the phrase 'Before meeting the artisan' marks B as the very first step.

---

### S14. 2025 Q155 · general-intelligence-reasoning · Circular arrangement — facing centre

`17ee7b1b-108f-435f-86b2-ec7779051fa6` · verdict AGREE · confidence high · current affairs no

**Question.** . What is the total number of persons who sit around this circular shaped table? Study the following information carefully and answer the questions given below: A certain number of persons sit around a circular table, all facing towards the centre. Some of them likes a different colour. S sits six places away from B. The one who likes blue colour sits third to the right of B. Two persons sit between G and the one who likes blue colour. A sits third to the left of M. M sits two places away from the one who likes white colour. Only one person sits between G and the who likes white colour. A sits fourth to the left of S and immediate right of the one who likes red colour. The ones who like white and blue colour are not immediate neighbours. E likes green colour and sits ninth to the left of the one who likes red colour. L sits third to the left of the one who likes red colour. The one who likes black colour sits exactly between E and L. M likes grey colour. One of the immediate neighbours of A is R.

- (a) 18
- (b) 20
- (c) 12
- (d) 14
- (e) 17 **← keyed**

**Short explanation.** The only way to satisfy every clue together, in particular the white-liker sitting two seats from both M and G and the black-liker sitting exactly between E and L, is a circle of 17 seats.

**Explanation.** Seventeen people sit round the table. Start from G, who likes red, and go round to G's left: the first and second seats to G's left are taken by people not named in the clues, L (blue) sits third to the left of G, the fourth and fifth seats are again unnamed, B (black) sits sixth to the left of G, the seventh and eighth seats are unnamed, E (green) sits ninth to the left of G, the tenth and eleventh seats are unnamed, S sits twelfth to the left of G, M (grey) thirteenth, the fourteenth seat is unnamed, R (white) fifteenth and A sixteenth, which is the seat immediately to G's right.

**Why the other options are wrong**

- (a) No likely slip gives 18; the arrangement closes with 17 seats, and an 18th seat breaks the distance clues for G, M and the white-liker.
- (b) No likely slip gives 20; the arrangement closes with 17 seats.
- (c) No likely slip gives 12; E alone is already ninth to the left of the red-liker, and the full working needs 17 seats.
- (d) No likely slip gives 14; the working needs 17 seats.

**Solution steps**

1. Take the red-liker as the reference. A sits immediately to the right of the red-liker, L third to the left, E (green) ninth to the left, and the black-liker exactly midway between L and E, sixth to the left.
2. A is fourth to the left of S and third to the left of M, so S sits fifth and M fourth to the right of the red-liker.
3. B sits six places from S. If B sat sixth to the left of S, the blue-liker (third to B's right) would leave G no free seat, so B sits sixth to the right of S. The blue-liker is then third to B's right, and G, with two people between G and blue, sits a further three seats round.
4. The white-liker must be two seats from M and two seats from G, and not next to the blue-liker. This works only if G is the red-liker himself and the circle has 17 seats; the white-liker is then R, second to the right of G and immediately to the right of A. B turns out to be the black-liker and L the blue-liker.
5. Counting every seat once round the table gives 17 people.

**Common traps**

- Counting only the eight people who are named or given a colour misses the nine unnamed seats.

---

### S15. 2025 Q157 · general-intelligence-reasoning · Three or more statement syllogism

`f5239959-52c2-4a6d-aa71-03b90c74c1b3` · verdict AGREE · confidence high · current affairs no

**Question.** Statements: Some imaginations are good No good is bright All bright is light Some light is yellow Conclusions: In the question below, some statements are given followed by five conclusions written as five options. You have to take the given statements to be true even if they seem to be at variance with commonly known facts. Read all the conclusions and then decide which of the given conclusions logically follows from the given statements, disregarding commonly known facts. Give answer-

- (a) All imagination are yellow
- (b) Some good are yellow
- (c) All light being good is a possibility
- (d) Some yellow being good is a possibility **← keyed**
- (e) No light is bright.

**Short explanation.** Nothing in the statements stops yellow and good from overlapping: good is kept apart only from bright, and yellow is tied only to light. So some yellow being good is possible.

**Why the other options are wrong**

- (a) Imagination is linked to yellow by no chain of statements, so 'all imagination is yellow' is not certain.
- (b) Some yellow being good is only a possibility, not a certainty, so the definite 'some good are yellow' does not follow.
- (c) All bright is light and no good is bright, so the bright part of light can never be good; 'all light being good' is impossible.
- (e) All bright is light, so light certainly contains bright things; 'no light is bright' is false.

**Solution steps**

1. No good is bright and all bright is light: the bright part of light can never be good.
2. Some light is yellow, and yellow may lie in the part of light that is not bright, where good can also sit.
3. So yellow and good can overlap: 'some yellow being good is a possibility' follows.

**Common traps**

- Treating 'no good is bright' as 'no good is light' wrongly rules out any overlap between good and light-related sets.

---

### S16. 2025 Q125 · quantitative-aptitude · Data sufficiency

`778fca08-9961-4177-98db-463af8c51f49` · verdict AGREE · confidence high · current affairs no

**Question.** In how many days 6 men can complete the work? I: 8 men and 10 women can finish the work in 2 days. II: 4 men and 5 women can finish the work in 4 days.

- (a) Only I is required
- (b) Only II is required
- (c) Both I and II are required
- (d) Either I or II is required
- (e) Cannot be answered even from both I and II **← keyed**

**Short explanation.** Statement II (4 men and 5 women in 4 days) is exactly half the workforce of Statement I (8 men and 10 women in 2 days), so both give the same single equation. One equation cannot separate a man's rate from a woman's rate, so the time for 6 men cannot be found.

**Why the other options are wrong**

- (a) Statement I gives one equation in two unknowns (a man's and a woman's daily work).
- (b) Statement II gives the same single equation.
- (c) Together they are still only one equation, since II is I halved.
- (d) Neither statement alone is sufficient.

**Solution steps**

1. Let a man do m and a woman do w of the work per day.
2. Statement I: 2(8m + 10w) = 1, so 8m + 10w = 1/2.
3. Statement II: 4(4m + 5w) = 1, so 4m + 5w = 1/4, which is Statement I divided by 2.
4. Only one independent equation, so m cannot be found and the question cannot be answered.

**Formula.** Work = Rate × Time

**Common traps**

- Assuming two statements always give two equations; check whether one is a multiple of the other.

---

### S17. 2026 Q89 · english-language · Logical Order

`1769f42b-6bee-4f1f-89e1-9407d9fff411` · verdict AGREE · confidence high · current affairs no

**Question.** Directions (89 –91): In each of the following questions, a long, grammatically complex sentence has been segregated into five parts designated as (A), (B), (C), (D), and (E). These parts are jumbled. Choose the option that provides the most grammatically accurate and contextually coherent alignment of these segments. (A) structural fissures within the domestic distributive network continue to (B) systematically marginalize significant cohorts of the population, leaving them highly vulnerable (C) despite anchoring an agrarian infrastructure characterized by unparalleled capital intensity, (D) to sudden, unpredictable macroeconomic contractions and commodity price spirals (E) structural integration, and technological sophistication,

- (a) CABED
- (b) CEABD **← keyed**
- (c) ACEBD
- (d) CAEBD
- (e) CEBDA

**Short explanation.** The sentence begins with the 'despite' phrase (C), completes its list with 'structural integration, and technological sophistication' (E), gives the main subject and verb 'structural fissures ... continue to' (A), then 'systematically marginalize ... leaving them highly vulnerable' (B), ending with 'to sudden, unpredictable ... contractions' (D). So the order is C E A B D.

**Why the other options are wrong**

- (a) Puts A straight after C, but C ends mid-list ('capital intensity,') and needs E to finish the list.
- (c) Starts with A, leaving the 'despite' phrase in the middle of the main clause.
- (d) Puts A between the two halves of the list, splitting 'capital intensity, structural integration'.
- (e) Puts B before A, so 'systematically marginalize' comes before the subject 'structural fissures ... continue to'.

**Common traps**

- 'Vulnerable' at the end of B must be followed by 'to', which is how D begins.

---

### S18. 2026 Q166 · general-intelligence-reasoning · Only and only-a-few statements

`fe950b8b-652a-4722-bf52-aa394d60a60e` · verdict AGREE · confidence high · current affairs no

**Question.** Directions (165-167): Study the following statements and then decide which of the given conclusion logically follows from the given statements disregarding the commonly known facts. Statements: All Delhi is Goa. Only a few Jaipur is Surat. Only a few Surat is Delhi. Some Shimla is Jaipur. Conclusions:

- (a) All Shimla is Delhi
- (b) Some Jaipur is Goa
- (c) No Delhi is Surat
- (d) Some Goa is Delhi **← keyed**
- (e) Some Surat is not Jaipur

**Short explanation.** 'All Delhi is Goa' means every Delhi is Goa, so at least some Goa is Delhi.

**Why the other options are wrong**

- (a) Shimla is linked only to Jaipur; nothing makes all Shimla Delhi.
- (b) Jaipur reaches Goa only through Surat and Delhi with 'some' links, so no definite link exists.
- (c) 'Only a few Surat is Delhi' says some Surat is Delhi, which contradicts 'No Delhi is Surat'.
- (e) 'Only a few' gives some Surat is not Delhi and some Jaipur is not Surat, but nothing definite about Surat outside Jaipur.

**Common traps**

- Mixing up which term 'only a few' makes negative: 'Only a few Jaipur is Surat' says some Jaipur is not Surat, not some Surat is not Jaipur.

---

### S19. 2026 Q175 · general-intelligence-reasoning · Shifting and rearrangement machine

`19e983b0-cba0-4bcd-ba7b-ee8930eb5b50` · verdict AGREE · confidence high · current affairs no

**Question.** Directions (174 -178) Study the following information carefully and answer the below questions. The numbers arrangement machine when given an input line of numbers rearranges them following a particular rule in each step. The following is an illustration of input and rearrangement. Input: 245 368 127 492 583 716 639 854 431 Step I: 644 245 127 492 583 716 854 431 365 Step II: 588 644 245 127 716 854 431 365 489 Step III: 436 588 644 245 127 854 365 489 713 Step IV: 250 436 588 644 127 365 489 713 851 Step V: 132 250 436 588 644 365 489 713 851 Step V is the last step Input: 537 684 219 456 795 328 671 942 153 In Step IV, how many numbers are there between the number obtained from 671 and the number obtained from 942?

- (a) Three
- (b) Four
- (c) Five **← keyed**
- (d) Six
- (e) Seven

**Short explanation.** In Step IV (224 542 676 800 153 325 453 681 939), 671 has become 676 and 942 has become 939. Between them are 800, 153, 325, 453 and 681: five numbers.

**Explanation.** In each step the largest remaining odd number of the input is increased by 5 and placed at the left end, and the smallest remaining even number of the input is reduced by 3 and placed at the right end; the other numbers keep their order. For the new input: Step I is 800 537 684 219 456 671 942 153 325. Step II is 676 800 537 684 219 942 153 325 453. Step III is 542 676 800 219 942 153 325 453 681. Step IV is 224 542 676 800 153 325 453 681 939. Step V is 158 224 542 676 800 325 453 681 939.

**Why the other options are wrong**

- (a) Five numbers lie between 676 and 939, not three.
- (b) Five numbers lie between 676 and 939, not four.
- (d) Six would count one of the end numbers as well.
- (e) Only nine numbers are in the line; seven is too many.

**Solution steps**

1. In the example, 639 (largest odd) becomes 644 at the left end and 368 (smallest even) becomes 365 at the right end in Step I, and so on.
2. New input odd numbers, largest first: 795, 671, 537, 219, 153. Even numbers, smallest first: 328, 456, 684, 942.
3. Step I: 800 537 684 219 456 671 942 153 325. Step II: 676 800 537 684 219 942 153 325 453. Step III: 542 676 800 219 942 153 325 453 681.
4. Step IV: 224 542 676 800 153 325 453 681 939. Step V: 158 224 542 676 800 325 453 681 939.
5. Between 676 (from 671) and 939 (from 942) in Step IV are 800, 153, 325, 453, 681: five numbers.

**Common traps**

- Looking for 671 and 942 unchanged instead of their changed forms 676 and 939.

---

### S20. 2026 Q198 · general-intelligence-reasoning · Statement and inference

`19e4483c-2e5b-4b70-a7ba-2e24294fe08c` · verdict AGREE · confidence high · current affairs no

**Question.** Directions (198) - Read the following statement carefully and choose the conclusion that logically follows from the information given in the statement. Statement: The Reserve Bank of India’s Clean Note Policy aims to ensure that the public receives clean and good-quality currency notes. Banks are expected to sort notes into issuable and non- issuable categories and avoid practices such as stapling or writing on currency notes. Soiled or unfit notes are to be withdrawn from circulation through the banking system. Which of the following conclusions can be drawn from the above statement?

- (a) The Clean Note Policy is intended to improve the quality of currency notes available to the public. **← keyed**
- (b) Banks are allowed to issue soiled notes if customers agree to accept them.
- (c) Stapling of currency notes helps increase the life of banknotes.
- (d) The policy applies only to coins and not to currency notes.
- (e) RBI has stopped the circulation of all physical currency notes.

**Short explanation.** The policy's stated aim is that the public receives clean, good-quality notes, with banks sorting notes and withdrawing soiled ones, so it is meant to improve the quality of notes available to the public.

**Why the other options are wrong**

- (b) Contradicts the statement; soiled notes are to be withdrawn, not issued.
- (c) The statement tells banks to avoid stapling, which damages notes.
- (d) The statement is about currency notes throughout; coins are not mentioned.
- (e) The policy manages note quality; it does not stop circulation of notes.
