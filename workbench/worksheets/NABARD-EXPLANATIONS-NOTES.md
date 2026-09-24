# NABARD Grade A — Explanation Draft: Review Notes (EXPL-06)

Worksheet: `workbench/worksheets/NABARD-EXPLANATIONS-DRAFT.json` — 1048 rows, one per question in
`workbench/sources/nabard-explanations-input.json`. Every row is authored from subject knowledge and the
question's own text; set-based questions (passages, puzzles, data tables) are solved from the premise carried
by their set. No text is extracted from any third-party source. Nothing here is reviewed.

Conventions follow EXPL-01 (SEBI), EXPL-02 (IFSCA), EXPL-03 (RBI) and EXPL-04 (PFRDA): keys defensible on any
reasonable reading are AGREE with the competing reading recorded in `key_note`; flags are reserved for keys
defensible on no reading and for questions unanswerable as stored; puzzles are explained from one arrangement;
every row is written in plain language with no position codes or symbolic shorthand.

**What the input covers.** economic-social-issues 286, agriculture-rural-development 268, english-language 160, computer-knowledge 100, quantitative-aptitude 100, general-intelligence-reasoning 95, decision-making 38, NULL 1.
This is the widest subject mix in the lane, so depth was judged per question rather than per subject.

## 1. How the batch was produced

The 1048 rows were authored in 20 chunks by parallel agents working from one shared spec, then merged and
validated centrally. Chunks were cut so that no set sharing a premise was ever split across two agents: every
(year, subject) block stayed whole except the four standalone knowledge blocks (2022 agriculture and 2022
economic-social-issues), which carry no shared premises and were halved. Per-chunk depth counts are in §8 so
drift between chunks is visible.

## 2. Key verdicts

| Verdict | Count | `final_answer_option_id` |
|---|---|---|
| AGREE | 1021 | set = input `correct_option_id` |
| DISPUTED | 11 | null — awaits a human key decision |
| AMBIGUOUS | 0 | null — awaits a human key decision |
| UNANSWERABLE | 16 | null — awaits a human key decision |
| **Total** | **1048** | **1021 set** |

### 2.1 DISPUTED — the keyed answer is, in my judgement, wrong

The key is defensible on no reading. A proposed option is named; resolving it is a human decision.

#### 2020 Q4 · agriculture-rural-development · `387f4613-3055-4110-892f-02786bd03782`

**Stem.** Q.4) What is the first milk produced by animals which is highly nutritious?

- **Topic:** Dairy physiology and milk production
- **Keyed option:** (A) Plasma milk
- **Proposed option:** (B) Colostrum milk
- **Reason.** The key marks 'Plasma milk', which is not a term in dairy science. The first milk after calving is colostrum, option B, on every standard reading; this looks like a key-entry error in the source.

#### 2020 Q38 · economic-social-issues · `ac81fe82-8923-4f5e-a8d1-481059a32c5b`

**Stem.** Q.38) The Mission aims at creating efficient and effective institutional platforms of the rural poor enabling them to increase household income through sustainable livelihood enhancements and improved access to financial services. In November 2015, the program w as renamed. It has set out with an agenda to cover 7 Crore rural poor households, across 600 districts, 6000 blocks, 2.5 lakh Gram Panchayats and 6 lakh villages in the country through self -managed Self Help Groups (SHGs) and federated institutions and support them for livelihoods collectives in a period of 8 -10 years. In addition...

- **Topic:** DAY-NRLM, self-help groups and rural livelihoods
- **Keyed option:** (C) MGNREGA
- **Proposed option:** (A) DAY-NRLM
- **Reason.** The key marks MGNREGA, but MGNREGA is a 2005 wage employment guarantee: it was not renamed in November 2015, it does not work through Self Help Groups, and it has no 7 crore household mobilisation target over 8 to 10 years. Every detail in the passage belongs to Aajeevika, renamed Deendayal Antyodaya Yojana - NRLM in November 2015. Proposed answer: option A, DAY-NRLM.

#### 2021 Q92 · decision-making · `f7a60389-cb45-4399-91fd-26da877b90ff`

**Stem.** Q.92) With a view to improve the process and outcomes of future decisions decision makers generally assess both outcome of a decision and process by which the decision has reached after –

- **Topic:** Steps in the decision-making process
- **Keyed option:** (C) Evaluating alternative course of action
- **Proposed option:** (B) Decision has been made and implemented
- **Reason.** The keyed option, evaluating alternative courses of action, precedes the choice, so at that point there is no decision outcome to assess; the stem describes the post-implementation review. Option B is proposed instead. The official NABARD 2021 key should be checked before publication.

#### 2021 Q128 · economic-social-issues · `b4ae2209-4fee-4e10-b744-c07007b49f0a`

**Stem.** Q.128) Ministry of Education has launched a National Initiative “NIPUN Bharat”. Identify the major aims and objective of this scheme.

- **Topic:** School education schemes and curriculum frameworks
- **Keyed option:** (D) To create efficient administrators in India
- **Proposed option:** (C) to cover the learning needs of children in the age group of 3 to 9 years
- **Reason.** The keyed option, on creating efficient administrators, has nothing to do with NIPUN Bharat on any reading. NIPUN Bharat is a foundational literacy and numeracy mission under Samagra Shiksha, with a target of universal foundational learning by 2026-27 for children up to Class 3, that is the 3-to-9 age group. Option C is the correct answer and the key looks like a data-entry error.

#### 2022 Q13 · agriculture-rural-development · `370c2d1a-cef5-4af7-badc-357dd519ce0a`

**Stem.** Q.13) Which subsidiary of NABARD working with NBFCs is responsible for financing Farmers and cooperations?

- **Topic:** NABARD and rural finance institutions
- **Keyed option:** (B) NABVENTURES
- **Proposed option:** (C) NABKISAN
- **Reason.** NABVENTURES takes equity in start-ups as a fund manager; it is not an NBFC extending credit to farmers or cooperatives, so the key is not defensible on the stem as written. NABKISAN, option C, matches the description exactly and should be the key.

#### 2022 Q122 · economic-social-issues · `5f5c086b-e8a3-46df-afef-097898622ecb`

**Stem.** Q.122) PM Suraksha Bima yojana is an affordable insurance scheme for the poor and underprivileged people in the age group of?

- **Topic:** Life and accident insurance schemes for the poor
- **Keyed option:** (B) 18 to 60
- **Proposed option:** (C) 18 to 70
- **Reason.** The keyed 18 to 60 matches no PMSBY circular. Eligibility under the scheme is 18 to 70 years, which is option C; the 18 to 50 band belongs to PMJJBY. The key should be corrected.

#### 2022 Q125 · economic-social-issues · `bac04390-a785-4904-9484-1c0135b891e6`

**Stem.** Q.125) Who among the following is the implementing agency for Pradhan Mantri Shram Yogi Mandhan Yojana?

- **Topic:** Pension schemes for unorganised workers and farmers
- **Keyed option:** (B) National Insurance Company Limited
- **Proposed option:** (D) Life Insurance Corporation of India
- **Reason.** PM-SYM's notified fund manager and paying agency is Life Insurance Corporation of India; National Insurance Company Limited is a general insurer with no role in the scheme. Question 121 of this same paper keys LIC as the scheme implemented through LIC, so the two keys contradict each other. Recommend correcting this key to LIC after a source check.

#### 2022 Q165 · agriculture-rural-development · `ee21319f-c8ef-4b5e-918d-47bed093c964`

**Stem.** Q.165) TRYSEM is related to which of the following

- **Topic:** Rural employment and training programmes
- **Keyed option:** (D) Providing education facilities to rural people
- **Proposed option:** (B) Providing skills to the rural youth
- **Reason.** The keyed option, education facilities, describes neither TRYSEM's design nor its delivery - it funded trade training with a credit and subsidy package, not schools or education infrastructure. Option B states exactly what the programme did and should be the key.

#### 2022 Q183 · agriculture-rural-development · `224447a8-4a6a-4c57-8e2d-9d64d10f4a7e`

**Stem.** Q.183) Climate smart agriculture does not include ______.

- **Topic:** Climate-smart and sustainable agriculture
- **Keyed option:** (A) Increased productivity, Enhanced resilience & Reduced emissions
- **Proposed option:** (C) Better nutrition, a better environment and a better life for all, leaving no one behind
- **Reason.** The keyed option — increased productivity, enhanced resilience and reduced emissions — is the textbook definition of CSA's three pillars, so it cannot be the thing CSA 'does not include'. The item reads as an 'includes' stem with a stray 'not', in which case the key is right and the question is misprinted. Taken exactly as printed, option C is the only choice outside the CSA frame, which is what this draft proposes. Check against the official key before publication.

#### 2022 Q187 · agriculture-rural-development · `b38410e2-bc79-4631-bf18-aea6ade0d163`

**Stem.** Q.187) Whitish-gray powdery coating on the leaves or fruit. On leaves, initial symptoms appear as chlorotic spots on the upper leaf surface that soon become whitish lesions is the symptom seen in grapes, roses and other aromatic crops are due to which disease?

- **Topic:** Crop diseases and their causal agents
- **Keyed option:** (A) Downey Mildew
- **Proposed option:** (B) Powdery mildew
- **Reason.** The keyed option, downy mildew, contradicts its own stem. Downy mildew never gives a powdery coating on the upper surface: it gives oil spots above and a white downy fungal growth on the lower surface only. Every phrase in the stem — whitish-grey powdery coating, chlorotic spots on the upper leaf surface becoming whitish lesions, grape and rose — is the standard textbook description of powdery mildew. The spellings in the options ('Downey', 'Powdery') suggest the two were simply transposed. Publish only after the official key has been checked.

#### 2023 Q4 · agriculture-rural-development · `612d7ea4-59bb-41df-976f-8ee57a46655e`

**Stem.** Q.4) MSP is recommended by which of the following institutes?

- **Topic:** Minimum Support Price and procurement
- **Keyed option:** (D) Cabinet Committee on Economic Affairs
- **Proposed option:** (B) Commission for Agricultural Costs and Prices
- **Reason.** The paper keys CCEA. CCEA approves and announces MSP but does not recommend it - the recommending body is CACP. Read loosely as which body decides MSP, CCEA fits; as written, with the verb recommended, option B is correct.

### 2.2 AMBIGUOUS — more than one option is defensible

None.

### 2.3 UNANSWERABLE — cannot be answered as written

The premise, data table or a correct value is absent from the stored question and from the rest of its set.

#### 2020 Q89 · quantitative-aptitude · `7a7fa215-fde7-4b0d-8628-b7d3d17dc549`

**Stem.** Q.89)If number of people (male + female) registered on Friday is 20% more than the total number of people (male + female) registered on Monday. If there were 40% females among those who registered on Friday, then find the number of male who registered on Friday.

- **Topic:** Tabular data interpretation
- **Keyed option:** (E) 630
- **Reason.** The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items. The printed key of 630 males implies a Friday total of 1,050 and therefore a Monday total of 875, which is the number the table would have to supply.

#### 2020 Q90 · quantitative-aptitude · `6d5970ed-02a6-498b-a369-ba5237711657`

**Stem.** Q.90)Find difference between the total number of people registered on Tuesday & Wednesday and total number of people attended on Monday & Thursday.

- **Topic:** Tabular data interpretation
- **Keyed option:** (B) 750
- **Reason.** The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.

#### 2020 Q91 · quantitative-aptitude · `2f2a19b1-38f2-4aa8-8e3f-4f3178253145`

**Stem.** Q.91)If on Wednesday, the ratio of number of male and female who attended seminar is 4:1 then find the number of female who registered for seminar but not attended the seminar.

- **Topic:** Tabular data interpretation
- **Keyed option:** (D) 690
- **Reason.** The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.

#### 2020 Q92 · quantitative-aptitude · `4ecef4cd-28ef-4812-b6d9-7668e437e327`

**Stem.** Q.92)The number of female registered for seminar on Thursday is what percentage more than the number of male registered for seminar on Monday.

- **Topic:** Tabular data interpretation
- **Keyed option:** (B) 20%
- **Reason.** The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items. Note the base: "what percentage more than" divides the gap by Monday's male registrations, not by Thursday's female figure.

#### 2020 Q93 · quantitative-aptitude · `573547fd-46a6-4b36-a019-6fff961282bd`

**Stem.** Q.93)The ratio of number of people who attended the seminar on Tuesday and number of people who attended the seminar on Wednesday is

- **Topic:** Tabular data interpretation
- **Keyed option:** (E) 35:22
- **Reason.** The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.

#### 2020 Q94 · quantitative-aptitude · `c2e9f69b-e00d-4d7f-9958-7b8825f916c8`

**Stem.** Q.94)If on Thursday, 40% of females who registered for the seminar attended it, then find out the number of males who attended the seminar.

- **Topic:** Tabular data interpretation
- **Keyed option:** (D) 660
- **Reason.** The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.

#### 2021 Q85 · quantitative-aptitude · `7a40b82c-9fe0-4634-a4e4-246876b8f10e`

**Stem.** Q.85) In 2020, number of males in town B was 80% more than number of females in town C in 2019. What was the percentage increase in number of males in town B from 2019 to 2020?

- **Topic:** Tabular data interpretation
- **Keyed option:** (A) 12.5
- **Reason.** The table of male and female populations that Q.85 to Q.90 read from is not printed with this row, and no other row of the paper as stored carries it, so the row cannot be worked as written. Back-solving the six keys together does fix one consistent table — males: A 17,500, B 24,000, C 55,000, D 13,000, E 8,500; females: A 32,500, B 4,000, C 15,000 — and every key follows from it, so the keys are sound and the item only needs its table restored. On that table males in B in 2020 = 1.8 × 15,000 = 27,000 against 24,000 in 2019, a rise of 12.5%.

#### 2021 Q86 · quantitative-aptitude · `dc92ccee-e93f-4b03-be14-1d2a03e4bbfc`

**Stem.** Q.86) Population of males in town D is 13000. Population of females in town D is equal to the average of population of males in A, B, C, D. What is the population of females in D?

- **Topic:** Tabular data interpretation
- **Keyed option:** (B) 27375
- **Reason.** The table of male and female populations that Q.85 to Q.90 read from is not printed with this row, and no other row of the paper as stored carries it, so the row cannot be worked as written. Back-solving the six keys together does fix one consistent table — males: A 17,500, B 24,000, C 55,000, D 13,000, E 8,500; females: A 32,500, B 4,000, C 15,000 — and every key follows from it, so the keys are sound and the item only needs its table restored. On that table females in D = (17,500 + 24,000 + 55,000 + 13,000) ÷ 4 = 27,375.

#### 2021 Q87 · quantitative-aptitude · `08fc1380-7e00-4bb5-a43c-1b081236325a`

**Stem.** Q.87) What is the difference between total males in town A & C together and females in town C?

- **Topic:** Tabular data interpretation
- **Keyed option:** (B) 57500
- **Reason.** The table of male and female populations that Q.85 to Q.90 read from is not printed with this row, and no other row of the paper as stored carries it, so the row cannot be worked as written. Back-solving the six keys together does fix one consistent table — males: A 17,500, B 24,000, C 55,000, D 13,000, E 8,500; females: A 32,500, B 4,000, C 15,000 — and every key follows from it, so the keys are sound and the item only needs its table restored. On that table (17,500 + 55,000) - 15,000 = 57,500.

#### 2021 Q88 · quantitative-aptitude · `1e8f22d7-90da-48dc-909d-d11d5426cd8f`

**Stem.** Q.88) 5000 males from town C work in an organization and the remaining work in a farm. 20% of males in town C who work in farm like coffee, and the remaining like tea. What is the number of males from town C who work in farm and like tea?

- **Topic:** Tabular data interpretation
- **Keyed option:** (D) 40000
- **Reason.** The table of male and female populations that Q.85 to Q.90 read from is not printed with this row, and no other row of the paper as stored carries it, so the row cannot be worked as written. Back-solving the six keys together does fix one consistent table — males: A 17,500, B 24,000, C 55,000, D 13,000, E 8,500; females: A 32,500, B 4,000, C 15,000 — and every key follows from it, so the keys are sound and the item only needs its table restored. On that table 55,000 - 5,000 = 50,000 males work in the farm, and 80% of them, 40,000, like tea.

#### 2021 Q89 · quantitative-aptitude · `a72e684e-ef57-441c-8528-c60072f050bd`

**Stem.** Q.89) Number of females in town A is what percentage more than number of females in town C?

- **Topic:** Tabular data interpretation
- **Keyed option:** (A) 117
- **Reason.** The table of male and female populations that Q.85 to Q.90 read from is not printed with this row, and no other row of the paper as stored carries it, so the row cannot be worked as written. Back-solving the six keys together does fix one consistent table — males: A 17,500, B 24,000, C 55,000, D 13,000, E 8,500; females: A 32,500, B 4,000, C 15,000 — and every key follows from it, so the keys are sound and the item only needs its table restored. On that table (32,500 - 15,000) ÷ 15,000 = 116.7%, which rounds to the keyed 117.

#### 2021 Q90 · quantitative-aptitude · `03e08a46-8356-4a82-b238-875283808de9`

**Stem.** Q.90) The ratio between number of females in town B and number of males in town E is 8:17. What is the ratio between number of males in town E and number of males in town A?

- **Topic:** Tabular data interpretation
- **Keyed option:** (B) 17:35
- **Reason.** The table of male and female populations that Q.85 to Q.90 read from is not printed with this row, and no other row of the paper as stored carries it, so the row cannot be worked as written. Back-solving the six keys together does fix one consistent table — males: A 17,500, B 24,000, C 55,000, D 13,000, E 8,500; females: A 32,500, B 4,000, C 15,000 — and every key follows from it, so the keys are sound and the item only needs its table restored. On that table females in B 4,000 to males in E 8,500 is 8:17, and males in E to males in A is 8,500 : 17,500 = 17:35.

#### 2022 Q84 · quantitative-aptitude · `bb077f10-6f95-4feb-ac96-a304e13bcc05`

**Stem.** Q.84) 12 men can complete a work in 16 days. 10 women can do the same work in 24 days. 6 men leave after working for 8 days. Thereafter, ‘X’ women work for 4 days and complete the remaining work. What is the total men and women required to complete the work?

- **Topic:** Partial work and remaining-work problems
- **Keyed option:** (A) 51
- **Reason.** Solved as written the answer is X = 22.5 women, so the count is not a whole number and no option matches either 12 + 22.5 or 6 + 22.5. The keyed 51 would be the 6 remaining men plus 45 women, which needs the women's rate to be half of what is printed - 10 women in 48 days rather than 24. The stem needs a source check before publication; as printed, no option is reachable.

#### 2022 Q132 · economic-social-issues · `2611394c-e3a0-4359-8b99-d1612a97dc4c`

**Stem.** Q.132) What is the share of agriculture in National income in FY22?

- **Topic:** Agriculture's share in income and employment
- **Keyed option:** (D) 3.6%
- **Reason.** Read as written, the answer is the share of agriculture and allied sectors in gross value added in 2021-22, about 18.8 per cent, which is not among the options. The options sit in the range of the sector's annual growth rate, so the stem appears to confuse share with growth; even on that reading the published FY22 figures are about 3.0 per cent (NSO provisional estimates) and 3.9 per cent (Economic Survey advance estimate), not 3.6. The item needs a source check against the original paper or a rewrite.

#### 2022 Q180 · agriculture-rural-development · `fc803fcb-cf78-4c22-bc5b-7d0273842621`

**Stem.** Q.180) A wax like substance containing the natural flower perfume together with some plant waxes, albumin and colouring matter.

- **Topic:** Aromatic and medicinal plants
- **Keyed option:** (C) Defoliator beetle
- **Reason.** The option block here is identical to the grape defoliator question in the same paper (Q.193), so this row looks like a mis-paired stem rather than a hard question. Taken on its own, the stem's answer is 'concrete': solvent extraction of flowers yields the concrete (essential oil plus waxes, albumin and colouring matter), and alcohol washing of the concrete yields the absolute. Check against the original question paper before publication and repair either the stem or the options.

#### 2022 Q181 · agriculture-rural-development · `a7313195-da95-4324-be2b-81c40060373a`

**Stem.** Q.181) Damping Off of Papaya symptoms

- **Topic:** Crop diseases and their causal agents
- **Keyed option:** (A) The disease prominently appears on green leaves and also on green immature fruits.
- **Reason.** Damping off of papaya is caused by Pythium aphanidermatum, Phytophthora and Rhizoctonia in wet, crowded nursery beds, and shows as pre-emergence seed rot and post-emergence collar rot and toppling; it never affects mature leaves or fruit. The keyed option, symptoms on green leaves and green immature fruit, describes papaya black spot or powdery mildew. The stem or the option set is defective — verify against the original paper and repair before publication.

### 2.4 Source data defects behind the flags

As in EXPL-03, most flags come from the stored question rather than from the examiner's judgement:

- **Missing data tables.** Three tabular data-interpretation sets lost the table they read from — 2020 Q89-Q94 and
  2021 Q85-Q90 — and the table is nowhere in the input file. Those twelve rows are the bulk of the UNANSWERABLE
  count. On the 2021 set the six keys back-solve to one consistent table, which is recorded in each row's
  `key_note`, so those items need the table restored rather than re-keying.
- **Mis-paired option blocks.** 2022 Q180 asks for a perfumery term and is given the insect options belonging to
  Q193 of the same paper; 2022 Q181 asks for damping-off symptoms and no option describes damping off.
- **A correct value absent from the options.** 2022 Q132 (agriculture's share of national income) and 2022 Q84
  (a work-and-time item whose printed rates give 22.5 women) cannot be answered from what is offered.
- **Transcription damage.** 2022 quantitative Q73 lost a superscript, so `6³` reads as `+ 63`; 2021 English Q33 and
  Q34 lost their instruction lines; 2023 English Q21 prints a keyed word the sentence does not contain; several
  phrase-replacement rows lost their underlining.
- **Duplicated or identical options.** Several items print the same option text twice — 2022 English Q26 and Q29,
  2023 reasoning Q11, 2023 quantitative Q16, the 2023 sickle-cell pair, and the 2021 agriculture item whose option
  E leaked the answer key into its own text.
- **Duplicated questions.** 2022 Q155 and Q157 are the same item, as are 2022 Q7 and Q174, and 2022 Q191 and Q198.

Every one of these is recorded in the affected row's `key_note` as well as here. None was repaired in this batch.

## 3. Current-affairs and circular-set parameters

Classified by one test: could a candidate reason to the answer, or only recall it? `current_affairs = yes` rows
give the durable context — what the institution, scheme or instrument is and how it works — and state the dated
fact once. Where a distractor is an arbitrary number or name, the rationale says so rather than inventing a
distinction. Scheme parameters fixed by circular or government order count as current affairs for this purpose.

| Subject | `current_affairs = yes` | no | Total |
|---|---|---|---|
| economic-social-issues | 131 | 155 | 286 |
| agriculture-rural-development | 54 | 214 | 268 |
| english-language | 0 | 160 | 160 |
| computer-knowledge | 1 | 99 | 100 |
| quantitative-aptitude | 0 | 100 | 100 |
| general-intelligence-reasoning | 0 | 95 | 95 |
| decision-making | 0 | 38 | 38 |
| NULL | 0 | 1 | 1 |
| **Total** | **186** | **862** | **1048** |

On the 186 current-affairs rows: `common_traps` populated on 63, `explanation_text` on 79.

## 4. Tag defects (flagged, not fixed)

`tag_suspect = yes` on 14 rows. No retagging has been done and no `topic_name` or `subject_slug` was modified.

| Year/Q | Subject | Current `topic_name` | Question | Suggested topic |
|---|---|---|---|---|
| 2020 Q32 | NULL | NULL | Q.32) Under which of the above framework the schemes above are mentioned through the 8 ... | Both subject_slug and topic_name are null on this row. It belongs to economic-social-issues, with a topic along the lines of 'Climate change framework and the National Action Plan on Climate Change' - the same set as question 45. |
| 2020 Q45 | economic-social-issues | Climate change initiatives in agriculture | Q. 45) Which of the following schemes are a part of the publication mentioned above in ... | topic_name reads 'Climate change initiatives in agriculture', but none of the four schemes in this row is agricultural. It belongs under climate change policy and clean energy initiatives, with question 32. |
| 2021 Q13 | agriculture-rural-development | Soil classification systems and soil orders | Q.13) Soil that comprises of both sand, silt and organic matter is termed as.............. | The item is about soil texture classes such as sand, silt, clay and loam, not about taxonomic soil classification systems or soil orders. |
| 2021 Q20 | general-intelligence-reasoning | Direct coded inequality | Q.20) Statements: O < F = J < A < I = K Conclusion: I. A > O II. K > F | Nothing in this item is coded — it is a plain single-chain inequality. A tag such as 'Single-chain direct inequality' fits; 'coded inequality' belongs to items where symbols stand in for the relations. |
| 2022 Q6 | general-intelligence-reasoning | Linear row — facing both directions | (Instruction for Q.6 to Q.9) Study the following information carefully and answer the q... | This is a two-parallel-rows puzzle with the rows facing each other, not a single linear row whose members face opposite ways. Suggested tag: parallel rows facing each other. |
| 2022 Q7 | general-intelligence-reasoning | Linear row — facing both directions | (Instruction for Q.6 to Q.9) Study the following information carefully and answer the q... | This is a two-parallel-rows puzzle with the rows facing each other, not a single linear row whose members face opposite ways. Suggested tag: parallel rows facing each other. |
| 2022 Q8 | general-intelligence-reasoning | Linear row — facing both directions | (Instruction for Q.6 to Q.9) Study the following information carefully and answer the q... | This is a two-parallel-rows puzzle with the rows facing each other, not a single linear row whose members face opposite ways. Suggested tag: parallel rows facing each other. |
| 2022 Q9 | general-intelligence-reasoning | Linear row — facing both directions | (Instruction for Q.6 to Q.9) Study the following information carefully and answer the q... | This is a two-parallel-rows puzzle with the rows facing each other, not a single linear row whose members face opposite ways. Suggested tag: parallel rows facing each other. |
| 2022 Q11 | agriculture-rural-development | Soil classification systems and soil orders | Q.11) Soil that comprises of both sand, silt and organic matter is termed as.............. | Textural classes such as loam belong under soil texture or soil physical properties. The tagged topic, soil classification systems and soil orders, covers Soil Taxonomy orders such as Inceptisols and Vertisols, which this question does not touch. |
| 2022 Q21 | english-language | Explicit detail retrieval | Instructions for Q.21 to Q.25: Read the given passage carefully and answer the question... | This is not explicit retrieval — the passage never lists examples of inappropriate behaviour, so the answer has to be inferred from the selection mechanism. "Inference and implied meaning", the tag used on the neighbouring rows of the same set, fits better. |
| 2022 Q121 | economic-social-issues | Life and accident insurance schemes for the poor | Q.121) Which of the following government scheme is implemented through Life Insurance C... | The keyed answer is PM-SYM, a contributory pension scheme. 'Pension schemes for unorganised workers and farmers' - the topic used elsewhere in this same paper - fits better than a life and accident insurance topic. |
| 2022 Q160 | economic-social-issues | Drinking water supply and Jal Jeevan Mission | Q.160) What is the target year for Swachh Bharat Mission-Urban 2.0? | The question is about Swachh Bharat Mission-Urban 2.0, so the topic should be urban sanitation and solid waste management, not drinking water supply and the Jal Jeevan Mission. |
| 2023 Q22 | agriculture-rural-development | Cattle breeds | Q.22) Balangir is a breed of which of the following? | The item is about a sheep breed. Cattle breeds does not describe it - a sheep and goat breeds, or general livestock breeds, topic would fit. |
| 2023 Q39 | economic-social-issues | Pension schemes for unorganised workers and farmers | Q.39) Which of the following is a biometric enabled digital service for pensioners of C... | The tagged topic is pension schemes for unorganised workers and farmers, but Jeevan Pramaan is a digital life certificate service for government and agency pensioners. It fits better under pension administration and digital governance, or e-governance service delivery. |

## 5. Low-confidence rows

42 rows are `draft_confidence = low`. Each is listed with its reason. A row is low either because the keyed
figure could not be corroborated from subject knowledge, or because the stored question forced a relaxation of a
clue, or because the item needs a source check before publication.

- **2020 Q2 · agriculture-rural-development · `d94043e9-7378-4df9-b04a-0040948ee376`** — Q.2) What is the kind of mushroom that ages well and forms gills and wrinkled umbrella?
  - Keyed: (A) Oyster Mushroom
  - Reason: The stem is loosely worded. 'Ages well and opens into a gilled umbrella' also describes Portabello, which is simply a mature Agaricus bisporus; the paper's key is oyster. Worth a source check before publication.
- **2020 Q23 · agriculture-rural-development · `1f836f35-8c75-4955-8f8f-4f667bb77332`** — Q.23)Broilers are marketed between ___________weeks of age?
  - Keyed: (B) 3-4 weeks
  - Reason: Standard poultry texts put broiler marketing at about 6 weeks, and older ones at 6-8 weeks, so options A and C are the defensible readings on subject knowledge. The source key reads (b), 3-4 weeks, which no standard reference supports. Verify against the official key before publication.
- **2020 Q28 · agriculture-rural-development · `a40ebc75-4bdc-4c67-8743-8a23af38394c`** — Q.28) Which of the following is NOT the feature of KCC? 1) A loan of 3 lakh can be sanctioned 2) No collateral will be required that will be amount upto 2 la...
  - Keyed: (C) 2 only
  - Reason: Statement 3 is also shaky: a KCC is sanctioned for five years with annual review, not three, so 'B: 2 and 3 only' is a defensible competing reading. Check against the official key.
- **2020 Q48 · economic-social-issues · `66a0a7cb-08f5-46ac-995f-3c25ff41181f`** — Q.48) Reimbursement % of training layout provided by government under PMKVY is__________.
  - Keyed: (C) 20% of training layout
  - Reason: The 20 per cent figure could not be corroborated from PMKVY's published common norms, which pay training providers against per-hour cost norms released in tranches - broadly 30 per cent on enrolment, 50 per cent on assessment and certification, and 20 per cent on placement. The keyed figure most likely refers to that placement-linked tranche. Check against the scheme guidelines before publication.
- **2020 Q49 · economic-social-issues · `9377fe5e-088f-4a6c-ba56-76fb887c4882`** — Q.49) Three statements are given. Select the correct statement. 1) To increase the number of candidates 2) Get maximum stipend up to Rs 9000. 3) Train candid...
  - Keyed: (B) 1 & 2 only
  - Reason: The stem does not name the scheme. Read with rows 48, 50 and 51, which run on skilling and apprenticeship, this is the apprenticeship promotion set: stipends are graded by qualification and reach about Rs 9,000 for graduate and degree apprentices, while the statutory minimum age is 14 - 18 in hazardous industries - with no upper cap. The item is loosely drafted and should be checked against the paper's source.
- **2020 Q50 · economic-social-issues · `d3dba56b-4caf-4da5-90c1-51e89aef3408`** — Q.50) Maximum financial support can be provided per month per trainee is________.
  - Keyed: (E) Rs. 3000 Solution – (e) 1 Marks Questionnaire
  - Reason: The stem names neither the scheme nor whether the support is a stipend to the trainee or a reimbursement to the employer. Read with rows 48, 49 and 51 as the skilling and apprenticeship set, Rs 3,000 is the keyed cap, but it does not match the apprenticeship reimbursement under NAPS, which is 25 per cent of the stipend subject to Rs 1,500 a month. The parameter should be verified against the paper's source before publication.
- **2020 Q54 · economic-social-issues · `84300146-cc67-438e-a481-1cf12f926f0a`** — Q.54) PSBs measures the performance on the basis of how many numbers of performance metrices.
  - Keyed: (A) 140
  - Reason: The 140-metric count matches the EASE reforms index as reported for its earlier editions, but the metric set is revised with each edition. Match the figure to the edition the paper drew on before publication.
- **2020 Q62 · economic-social-issues · `8acca317-4e37-4c92-8d52-91e70964a687`** — Q.62) “Fraud Prevention and Management function” is based on registry. This registry is based on which of the following?
  - Keyed: (D) Fraud analysis and survey
  - Reason: The key is retained as marked but it is weak: the RBI's Central Fraud Registry is built from the Fraud Monitoring Returns banks file, which is option B. The passage behind this row is not carried in this chunk, so the registry the paper means could not be confirmed. Check against the original source before publication.
- **2020 Q64 · economic-social-issues · `88089352-fbad-4e66-aada-c8247e207100`** — Q.64) What is the contribution of livestock to agriculture GDP?
  - Keyed: (D) 25.74
  - Reason: The livestock share of agricultural GVA is reported year by year and has been quoted at about 25.6 per cent for 2015-16 and near 28 per cent for 2018-19 in later Economic Surveys. Match the keyed 25.74 per cent to the year the paper used before publication.
- **2020 Q89 · quantitative-aptitude · `7a7fa215-fde7-4b0d-8628-b7d3d17dc549`** — Q.89)If number of people (male + female) registered on Friday is 20% more than the total number of people (male + female) registered on Monday. If there were...
  - Keyed: (E) 630
  - Reason: The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items. The printed key of 630 males implies a Friday total of 1,050 and therefore a Monday total of 875, which is the number the table would have to supply.
- **2020 Q90 · quantitative-aptitude · `6d5970ed-02a6-498b-a369-ba5237711657`** — Q.90)Find difference between the total number of people registered on Tuesday & Wednesday and total number of people attended on Monday & Thursday.
  - Keyed: (B) 750
  - Reason: The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.
- **2020 Q91 · quantitative-aptitude · `2f2a19b1-38f2-4aa8-8e3f-4f3178253145`** — Q.91)If on Wednesday, the ratio of number of male and female who attended seminar is 4:1 then find the number of female who registered for seminar but not at...
  - Keyed: (D) 690
  - Reason: The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.
- **2020 Q92 · quantitative-aptitude · `4ecef4cd-28ef-4812-b6d9-7668e437e327`** — Q.92)The number of female registered for seminar on Thursday is what percentage more than the number of male registered for seminar on Monday.
  - Keyed: (B) 20%
  - Reason: The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items. Note the base: "what percentage more than" divides the gap by Monday's male registrations, not by Thursday's female figure.
- **2020 Q93 · quantitative-aptitude · `573547fd-46a6-4b36-a019-6fff961282bd`** — Q.93)The ratio of number of people who attended the seminar on Tuesday and number of people who attended the seminar on Wednesday is
  - Keyed: (E) 35:22
  - Reason: The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.
- **2020 Q94 · quantitative-aptitude · `c2e9f69b-e00d-4d7f-9958-7b8825f916c8`** — Q.94)If on Thursday, 40% of females who registered for the seminar attended it, then find out the number of males who attended the seminar.
  - Keyed: (D) 660
  - Reason: The seminar table that Q.89-Q.94 depend on — registrations and attendance by day, with the male/female split — is not present anywhere in this chunk, and it cannot be reconstructed from the questions alone. The row is marked unanswerable for that reason, not because the printed key is wrong. Restore the table from the original paper before publishing these six items.
- **2020 Q123 · economic-social-issues · `556ae734-dcf8-48db-ad06-be6a3cd55c09`** — Q.123)Sansad Adarsh Gram Yojana which is a demand driven scheme, inspired by society, is based on which of the following principles
  - Keyed: (C) Housing
  - Reason: The stem asks for a single 'principle' while SAGY is deliberately holistic: its values run across personal, human, social, economic and environmental development, and its village development plan is built from the Gram Sabha's own demands. Housing for all is one of the basic amenities a model village must achieve, which makes the key defensible, but community development has an equally strong claim. The item is loosely drafted; treat it as recall of the paper's source rather than a settled point.
- **2020 Q134 · economic-social-issues · `911a9609-d9fb-447f-b1d2-1bea69c7b894`** — Q.134) NABARD to raise Rs 55000 Cr from the market for the year 2020 through longterm bonds of usually __________ years tenure
  - Keyed: (D) 10-15
  - Reason: The tenor band is a market operations detail reported in press coverage rather than a published scheme parameter. Verify the 10 to 15 year figure against NABARD's borrowing programme for that year before publication.
- **2020 Q151 · economic-social-issues · `f246bd20-e6f6-40a9-8643-ba3f5764fe18`** — Q.151) Rashtriya Gram Swaraj yojana which is a restructured erstwhile scheme and launched in 2018, has a sunset date of
  - Keyed: (D) 2030
  - Reason: The scheme's approved implementation period was 2018-19 to 2021-22 and was extended later, while 2030 is the SDG horizon written into its design. Check which of the two the paper's source calls the sunset date before publication.
- **2020 Q157 · economic-social-issues · `309556c3-d4e8-4780-97fe-0ce08bfc0df1`** — Q.157) Which of the following is the reason behind IMF’s lowering of GDP growth of India for 2019-20?
  - Keyed: (A) Country ‘s shadow-banking sector
  - Reason: The IMF's January 2020 World Economic Outlook update named both stress in the non-bank financial sector and weak rural income growth, so option D has a fair claim. The key is defensible if the credit squeeze is read as the principal cause, which is how the downgrade was reported; treat the rural income slowdown as the second reason rather than an alternative one.
- **2020 Q165 · agriculture-rural-development · `23e4a626-a7b1-46f5-b864-cea0e96a781e`** — Q.165) According to 5th Minor irrigation Census 2013 – 14, Which state has the highest number of minor irrigation projects/Schemes?
  - Keyed: (C) Andhra Pradesh
  - Reason: The Fifth Minor Irrigation Census is generally reported with Uttar Pradesh holding the largest number of schemes, chiefly groundwater structures. The paper keys Andhra Pradesh, which I cannot corroborate; check the census report before publication.
- **2020 Q173 · agriculture-rural-development · `8f79aaff-63b0-4050-911e-6e39c476a2b5`** — Q.173) Which one is false for PM KISAN?
  - Keyed: (E) All of the above
  - Reason: The key is loose. Statement C accurately describes the exclusion of income tax payers, so 'all of the above are false' does not hold strictly; B and D are the clearly false statements, and the item has no single clean answer. Kept as AGREE because no other single option is better.
- **2020 Q176 · agriculture-rural-development · `f207d9ac-e716-44d3-8f6c-1daf8d89653b`** — Q.176) The 6th world congress of agriculture held at _____________.
  - Keyed: (A) New Delhi
  - Reason: I cannot identify a congress by exactly this name and number from subject knowledge; the venue should be checked against the source before publication.
- **2020 Q186 · agriculture-rural-development · `9e2c81e5-5f78-4ff0-bfb1-1e8176f02d5f`** — Q.186) Inarching is used in the propagation of
  - Keyed: (E) Guava
  - Reason: Inarching is used in mango, sapota, guava and jackfruit, and standard horticulture texts most often cite mango. The key reads guava; because more than one option is defensible the item needs a source check.
- **2020 Q188 · agriculture-rural-development · `130c89d8-999b-4654-9a96-11ff7a9db0f3`** — Q.188)What is the subsidy given by bank for financing combine harvester?
  - Keyed: (A) 40 % when the cost of harvestor limited to 24 lakhs
  - Reason: Subsidy rates and cost ceilings on farm machinery change with each SMAM circular and vary by state and category of farmer. I cannot corroborate this exact pair of figures; verify against the current operational guidelines before publication.
- **2020 Q196 · agriculture-rural-development · `03e7a791-1584-456f-81de-852005e7d5e5`** — Q.196)Which of the following is the knowledge partner for the committee on doubling of farmers Income?
  - Keyed: (A) National Council of Applied Economic Research
  - Reason: The Dalwai committee's fourteen-volume report is the durable content here — the seven sources of income growth it identified. I cannot corroborate the knowledge partner from memory; verify before publication.
- **2021 Q15 · economic-social-issues · `2c43841f-02c8-4f33-8632-d9bf27228f39`** — Q.15) Which of the following statements is correct in relation with UNICEF data on child education during pandemic? 1) 5-6 hrs of online education is less th...
  - Keyed: (A) all are correct.
  - Reason: The UNICEF passage this row refers to is not in question_text and no other row in the chunk carries it. The answer is reconstructed from the three statements, each of which matches UNICEF's documented pandemic schooling findings, but the specific report and its wording should be checked before publication.
- **2021 Q176 · agriculture-rural-development · `435eedca-06fd-4990-a277-f780fdb48885`** — Q.176) Maximum selling agricultural commodity through National Agriculture Market (eNAM).
  - Keyed: (A) Vegetables
  - Reason: The ranking of commodities traded on e-NAM shifts from year to year and the keyed answer should be checked against the e-NAM trade data for the year in question before this explanation is published.
- **2022 Q84 · quantitative-aptitude · `bb077f10-6f95-4feb-ac96-a304e13bcc05`** — Q.84) 12 men can complete a work in 16 days. 10 women can do the same work in 24 days. 6 men leave after working for 8 days. Thereafter, ‘X’ women work for 4...
  - Keyed: (A) 51
  - Reason: Solved as written the answer is X = 22.5 women, so the count is not a whole number and no option matches either 12 + 22.5 or 6 + 22.5. The keyed 51 would be the 6 remaining men plus 45 women, which needs the women's rate to be half of what is printed - 10 women in 48 days rather than 24. The stem needs a source check before publication; as printed, no option is reachable.
- **2022 Q126 · economic-social-issues · `ba6f2ed9-77ef-4ac0-8d3c-4ec8b2ad2edd`** — Q.126) According to government data, India has become defecation free, but according to recent data how much percentage of households in rural area are still...
  - Keyed: (D) 0.8%
  - Reason: The 0.8 per cent figure could not be corroborated against a named published series. Sample surveys give a far larger gap - NFHS-5 (2019-21) reports about 19 per cent of rural households with no toilet facility - so the keyed number appears to come from the Swachh Bharat Mission-Grameen coverage dashboard rather than from a survey. Check the source before publication.
- **2022 Q132 · economic-social-issues · `2611394c-e3a0-4359-8b99-d1612a97dc4c`** — Q.132) What is the share of agriculture in National income in FY22?
  - Keyed: (D) 3.6%
  - Reason: Read as written, the answer is the share of agriculture and allied sectors in gross value added in 2021-22, about 18.8 per cent, which is not among the options. The options sit in the range of the sector's annual growth rate, so the stem appears to confuse share with growth; even on that reading the published FY22 figures are about 3.0 per cent (NSO provisional estimates) and 3.9 per cent (Economic Survey advance estimate), not 3.6. The item needs a source check against the original paper or a rewrite.
- **2022 Q141 · economic-social-issues · `e453d92f-1e0a-4a3a-8f85-a4f82af69c91`** — Q.141) As per AISHE 2019 -20 Report, what is the gross enrolment ratio for Schedule Cast students?
  - Keyed: (B) 23.2
  - Reason: AISHE 2019-20 gives an all-India GER of 27.1, with Scheduled Castes around 23 and Scheduled Tribes around 18. Whether the Scheduled Caste figure in the published table is 23.2 or 23.4 could not be settled from subject knowledge and should be verified against the report before this explanation is released.
- **2022 Q143 · economic-social-issues · `5b7a623b-c1e6-4f26-9c36-6a3e50da7e37`** — Q.143) Which of the following in not the eligible beneficiary under Prime Minister's Overarching Scheme for Holistic Nourishment Abhiyaan POSHAN 2.0 -
  - Keyed: (C) Adolescent girls from north east region
  - Reason: The competing reading is strong. The Scheme for Adolescent Girls inside Saksham Anganwadi and POSHAN 2.0 expressly covers girls of 14-18 years in Aspirational Districts and the North-Eastern states, which would make option E the better answer. The scheme guidelines should be checked before this row is published.
- **2022 Q148 · economic-social-issues · `f5db7b41-b769-47ba-bd9e-855869fa3669`** — Q.148) Which organization regulates angel investment?
  - Keyed: (A) IFSCA
  - Reason: This key is doubtful. Angel funds in India are registered and regulated by SEBI under Chapter III-A of the SEBI (Alternative Investment Funds) Regulations, 2012, with IFSCA covering only vehicles set up inside the IFSC. Unless the question is read as being about GIFT City, SEBI is the better answer, and the official key should be verified before publication.
- **2022 Q154 · economic-social-issues · `3cce30b9-cd07-4bb9-8c5b-fb3e8009fa06`** — Q.154) How much amount has been invested by World Bank since the implementation of Pradhan Mantri Gram Sadak Yojna (PMGSY)?
  - Keyed: (B) $2.1 billion
  - Reason: The World Bank's own notes on PMGSY have more often cited roughly $1.8 billion of cumulative lending since 2004. The $2.1 billion figure could not be corroborated from subject knowledge and should be checked against the Bank's project page before this row is published.
- **2022 Q155 · economic-social-issues · `450c15ac-eb17-495a-ab70-e358d6980253`** — Q.155) What is the percentage decline in the annual per capita availability of water in India?
  - Keyed: (C) 75%
  - Reason: The standard pair of figures is 5,177 cubic metres per person in 1951 against about 1,486 in 2021 — roughly a 71% fall — with 1,341 projected for 2025, about 74%. The keyed 75% is a rounding of that range, so the source year behind it should be confirmed before publication.
- **2022 Q156 · economic-social-issues · `2e29ba7e-b5d8-443b-a25a-a7860a327eda`** — Q.156) According to the CMIE, what was the Labour force participation rate in rural India between January to April 2022?
  - Keyed: (D) 40.9
  - Reason: CMIE's LFPR is a monthly series that moves by a point or more between months, so this figure should be tied to the exact release before publication. CMIE also measures participation on a different definition from the official Periodic Labour Force Survey, whose rural LFPR is substantially higher, so the two are not comparable.
- **2022 Q162 · agriculture-rural-development · `cb83c5ea-abe5-488a-ab4f-9218f9211e1a`** — Q.162) MSP of Lentil of Rabi Marketing Season (2020-21) is __________.
  - Keyed: (C) 5500
  - Reason: The season in the stem and the keyed figure do not line up: Rs 5,500 is the RMS 2022-23 lentil MSP, while RMS 2020-21 was about Rs 4,800, which is not among the options. Verify both against the CACP price policy statement before publication - the item may need its season label corrected rather than its key.
- **2022 Q183 · agriculture-rural-development · `224447a8-4a6a-4c57-8e2d-9d64d10f4a7e`** — Q.183) Climate smart agriculture does not include ______.
  - Keyed: (A) Increased productivity, Enhanced resilience & Reduced emissions
  - Reason: The keyed option — increased productivity, enhanced resilience and reduced emissions — is the textbook definition of CSA's three pillars, so it cannot be the thing CSA 'does not include'. The item reads as an 'includes' stem with a stray 'not', in which case the key is right and the question is misprinted. Taken exactly as printed, option C is the only choice outside the CSA frame, which is what this draft proposes. Check against the official key before publication.
- **2022 Q195 · agriculture-rural-development · `0dec7b2b-c4da-4283-b16d-594bb7211e41`** — Q.195) What is the GVA share of agriculture sector according to the First Income estimates
  - Keyed: (A) 18.4
  - Reason: The stem does not say which year's first estimates it means, and the year decides the answer: about 20.2 per cent for 2020-21, 18.8 per cent for 2021-22 in the Economic Survey 2021-22, and 18.3 per cent for 2022-23 in the Economic Survey 2022-23. The keyed 18.4 per cent could not be tied to a named release. Check the year and the source release before publication, and add the year to the stem.
- **2022 Q198 · agriculture-rural-development · `1c16b87a-cd78-43ed-ba9a-4ec9316e50a1`** — Q.198) According to Census 2011, what is the percentage of the rural workforce?
  - Keyed: (A) 33.69%
  - Reason: Census 2011 gives 481.7 million total workers, a national work participation rate of 39.8 per cent, a rural work participation rate of about 41.8 per cent, and roughly 348.6 million rural workers, which is about 72 per cent of all workers and about 29 per cent of the total population. The keyed 33.69 per cent could not be matched to any of these standard Census 2011 ratios. The base and the source table must be checked before this row is published, and the stem should state what the percentage is of.
- **2023 Q7 · economic-social-issues · `d44261f6-cb82-471e-b7cb-7d25eeacb379`** — Q.7) What is the eligible age group of beneficiaries under the Khadi Gramodyog Vikas Yojana?
  - Keyed: (B) 18 – 55 years
  - Reason: I cannot corroborate the 18 to 55 band from the published KGVY guidelines, which mostly set component-wise eligibility rather than one age range. Check the current KVIC scheme guidelines before publishing this figure.
- **2023 Q19 · agriculture-rural-development · `27ac0625-03a6-49d8-aaa3-309b2ecefea2`** — Q.19) Saline soil has _________g/l of Na.
  - Keyed: (C) 12g/L
  - Reason: Sodium concentration in g/L is not a criterion in the standard saline soil definition, which uses EC, pH and ESP, and the 12 g/L figure could not be corroborated from subject knowledge. Check it against the source paper before publication.

Rows marked `medium` (272) are not listed individually; they are medium either because the item is loosely
drafted or because the underlying fact is a narrow scheme or threshold parameter rather than a principle. Where a
specific reservation exists it is recorded in that row's `key_note`.

| Confidence | Count |
|---|---|
| high | 734 |
| medium | 272 |
| low | 42 |

## 6. Numerical distractor rationales

91 rows carry `solution_steps`; they hold 364 wrong-option rationales. Each numerical distractor was
checked against the question's own numbers and intermediates and against a fixed slip list (omitted step,
intermediate given as the answer, percentage taken on the wrong base, simple against compound, swapped ratio
terms, per-unit against total, adjacent series term, the other person or product).

- **324** rationales name a wrong step, or say what the solved arrangement actually gives.
- **40** are distractors no plausible slip reproduces; each states the value the working gives instead.

## 7. Depth and field-population counts

| Field | Rows populated | Of 1048 |
|---|---|---|
| `short_explanation` | 1048 | 100% |
| `explanation_text` | 422 | 40% |
| `solution_steps` | 91 | 9% |
| `formula_used` | 69 | 7% |
| `common_traps` | 447 | 43% |
| `key_note` | 340 | 32% |
| `final_answer_option_id` | 1021 | 97% |
| `option_rationales` (entries, not rows) | 4192 | — |

Rows by subject:

| Subject | Rows | `explanation_text` | `solution_steps` | `common_traps` | `current_affairs` |
|---|---|---|---|---|---|
| economic-social-issues | 286 | 140 | 0 | 111 | 131 |
| agriculture-rural-development | 268 | 126 | 0 | 96 | 54 |
| english-language | 160 | 35 | 0 | 68 | 0 |
| computer-knowledge | 100 | 27 | 1 | 44 | 1 |
| quantitative-aptitude | 100 | 20 | 88 | 70 | 0 |
| general-intelligence-reasoning | 95 | 49 | 2 | 43 | 0 |
| decision-making | 38 | 24 | 0 | 14 | 0 |
| NULL | 1 | 1 | 0 | 1 | 0 |

## 8. Per-chunk depth counts

Stated so drift between the parallel authoring chunks is visible rather than hidden in an average. `t` is
`explanation_text`, `st` `solution_steps`, `f` `formula_used`, `tr` `common_traps`, `ca` `current_affairs`,
`ts` `tag_suspect`, `kn` `key_note`, `low` `draft_confidence = low`. Percentages are of that chunk's rows.

| Chunk | Rows | t | st | f | tr | ca | ts | kn | low | Verdicts |
|---|---|---|---|---|---|---|---|---|---|---|
| `01_2020_agri` | 65 | 28 (43%) | 0 (0%) | 0 (0%) | 25 (38%) | 15 (23%) | 0 | 24 (37%) | 9 | AGREE 64, DISPUTED 1 |
| `02_2020_esi` | 80 | 38 (48%) | 0 (0%) | 0 (0%) | 25 (31%) | 34 (42%) | 2 | 20 (25%) | 10 | AGREE 79, DISPUTED 1 |
| `03_2020_eng` | 40 | 7 (18%) | 0 (0%) | 0 (0%) | 13 (32%) | 0 (0%) | 0 | 7 (18%) | 0 | AGREE 40 |
| `04_2020_comp_gir_qa` | 60 | 16 (27%) | 14 (23%) | 8 (13%) | 32 (53%) | 1 (2%) | 0 | 31 (52%) | 6 | AGREE 54, UNANSWERABLE 6 |
| `05_2021_agri` | 55 | 26 (47%) | 0 (0%) | 0 (0%) | 23 (42%) | 15 (27%) | 1 | 12 (22%) | 1 | AGREE 55 |
| `06_2021_esi` | 55 | 27 (49%) | 0 (0%) | 0 (0%) | 24 (44%) | 21 (38%) | 0 | 19 (35%) | 1 | AGREE 54, DISPUTED 1 |
| `07_2021_eng_dm` | 40 | 12 (30%) | 0 (0%) | 0 (0%) | 23 (58%) | 0 (0%) | 0 | 8 (20%) | 0 | AGREE 39, DISPUTED 1 |
| `08_2021_comp_gir_qa` | 60 | 14 (23%) | 14 (23%) | 5 (8%) | 24 (40%) | 0 (0%) | 1 | 24 (40%) | 0 | AGREE 54, UNANSWERABLE 6 |
| `09_2022_agri_A` | 48 | 24 (50%) | 0 (0%) | 0 (0%) | 9 (19%) | 9 (19%) | 1 | 20 (42%) | 1 | AGREE 46, DISPUTED 2 |
| `10_2022_agri_B` | 47 | 23 (49%) | 0 (0%) | 0 (0%) | 15 (32%) | 6 (13%) | 0 | 18 (38%) | 3 | AGREE 43, DISPUTED 2, UNANSWERABLE 2 |
| `11_2022_esi_A` | 48 | 23 (48%) | 0 (0%) | 0 (0%) | 28 (58%) | 21 (44%) | 1 | 17 (35%) | 2 | AGREE 45, DISPUTED 2, UNANSWERABLE 1 |
| `12_2022_esi_B` | 47 | 24 (51%) | 0 (0%) | 0 (0%) | 16 (34%) | 21 (45%) | 1 | 20 (43%) | 6 | AGREE 47 |
| `13_2022_eng` | 60 | 16 (27%) | 0 (0%) | 0 (0%) | 21 (35%) | 0 (0%) | 1 | 20 (33%) | 0 | AGREE 60 |
| `14_2022_comp_dm` | 60 | 21 (35%) | 1 (2%) | 0 (0%) | 25 (42%) | 0 (0%) | 0 | 9 (15%) | 0 | AGREE 60 |
| `15_2022_gir` | 35 | 28 (80%) | 2 (6%) | 1 (3%) | 17 (49%) | 0 (0%) | 4 | 26 (74%) | 0 | AGREE 35 |
| `16_2022_qa` | 40 | 14 (35%) | 40 (100%) | 40 (100%) | 29 (72%) | 0 (0%) | 0 | 5 (12%) | 1 | AGREE 39, UNANSWERABLE 1 |
| `17_2023_agri` | 53 | 25 (47%) | 0 (0%) | 0 (0%) | 24 (45%) | 9 (17%) | 1 | 13 (25%) | 1 | AGREE 52, DISPUTED 1 |
| `18_2023_esi` | 57 | 29 (51%) | 0 (0%) | 0 (0%) | 19 (33%) | 34 (60%) | 1 | 12 (21%) | 1 | AGREE 57 |
| `19_2023_eng_dm` | 38 | 11 (29%) | 0 (0%) | 0 (0%) | 18 (47%) | 0 (0%) | 0 | 10 (26%) | 0 | AGREE 38 |
| `20_2023_comp_gir_qa` | 60 | 16 (27%) | 20 (33%) | 15 (25%) | 37 (62%) | 0 (0%) | 0 | 25 (42%) | 0 | AGREE 60 |

`explanation_text` ranges from 18% to 80% across chunks, and the spread tracks subject rather than author.
The knowledge subjects cluster tightly: the six agriculture and economic-social-issues chunks sit between 43% and
51% whichever year and whichever agent wrote them. English sits between 18% and 30%, because the passage itself
carries the reasoning; the computer, reasoning and quantitative chunks between 23% and 35%.

The one outlier is `15_2022_gir` at 80%, and it is the puzzle chunk. Every row there belongs to a seating, floor,
scheduling or coding set whose answer only means something once the arrangement is stated in words, so the
paragraph is doing work a one-line answer cannot. `16_2022_qa` at 100% `solution_steps` is the same effect in the
other direction: every row in it calculates something. Both were checked against the equivalent blocks in other
years (`04`, `08`, `20`) before the sample below was drawn, and the difference is the corpus, not the author.

The `current_affairs` column shows the same pattern from the other side: it is 0% in every English, reasoning,
quantitative and computer chunk and between 13% and 60% in every agriculture and economic-social-issues chunk.

## 9. Validation — every number

Enforced by the build script; the worksheet is written only when every check passes.

- **Row count:** 1048 rows, one per input question.
- **Uniqueness:** 1048 distinct `question_id` values — no duplicates, and no question authored by two chunks.
- **Completeness:** the worksheet and input `question_id` sets are identical; `year`, `question_number`,
  `subject_slug` and `topic_name` are copied through unchanged.
- **Option-rationale integrity:** 4192 entries, each keyed to an `option_id` and `label` that exist on that
  question. Wrong options across the corpus: 4192. Coverage is 4192/4192 — every wrong option on every row is
  covered, including the flagged rows, where the rationale says what is missing rather than asserting the option
  is wrong.
- **No contradiction on AGREE rows:** no AGREE row carries a rationale against its own keyed option. 0 such rows.
- **final_answer_option_id:** set on all 1021 AGREE rows and equal to the input `correct_option_id`;
  null on all 27 non-AGREE rows.
- **Verdict integrity:** every DISPUTED row names a `proposed_correct_option_id` that exists on its own question and
  differs from the key; no other row carries one. Every non-AGREE row and every low-confidence row carries a `key_note`.
- **Numericals:** 91 rows carry `solution_steps` and 69 carry `formula_used`. The build rejects steps on any
  row whose stem and options contain fewer than two numbers, so no pure recall row can carry a worked solution.
- **Tag integrity:** `tag_suspect = yes` on 14 rows, each with a non-empty `tag_note`; every `no` row has an empty
  `tag_note`. No `topic_name` or `subject_slug` was modified.
- **Provenance:** all 1048 rows are `platform_original` / `owned` / `pending`.

Counts by verdict: AGREE 1021, DISPUTED 11, AMBIGUOUS 0, UNANSWERABLE 16.
Counts by confidence: high 734, medium 272, low 42.

## 10. Field and enum mapping against the live schema

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
| `proposed_correct_option_id` | — | not written; becomes `final_answer_option_id` only after a human decides the key |
| `key_verdict` | `ambiguity_status` | AGREE → `none`, DISPUTED → `disputed`, AMBIGUOUS → `multiple_possible`, UNANSWERABLE → `source_conflict` |
| `key_note`, `current_affairs`, `tag_suspect`, `tag_note`, `draft_confidence` | `metadata` | no dedicated columns |
| `explanation_source_type` / `license_status` / `reviewer_status` | same | `platform_original` / `owned` / `pending` (the route forces `pending`) |

Enum values emitted by this batch, checked against the CHECK constraints in migration 230 and the route's own
allowlists:

- `explanation_source_type` = **`platform_original`** (of `official`, `platform_original`, `coaching`, `community`, `imported`).
- `license_status` = **`owned`** (of `owned`, `licensed`, `public_domain`, `permission_pending`, `restricted`).
- `reviewer_status` = **`pending`** (of `pending`, `verified`, `rejected`, `needs_correction`).
- `ambiguity_status` = **`none`** on the 1021 AGREE rows, and the mapped value on the 27 flagged rows.

Constraints the apply step must respect:

- `unique (question_id, explanation_source_type)`: the create route returns 422 on a second `platform_original`
  row for the same question, so a re-run must PATCH the existing `pending` row rather than re-POST.
- `pyq_question_explanations_guard` and the review RPC refuse `verified` while `ambiguity_status ≠ none` or
  `final_answer_option_id` is null, so the 27 flagged rows cannot be verified until the key is resolved.
- Editing a learner-facing field on an already-verified row downgrades it to `needs_correction` and clears
  reviewer identity, so the apply step should touch only rows still in `pending`.

## 11. Scope

NABARD Grade A only — the 1048 questions in `workbench/sources/nabard-explanations-input.json`. No database writes,
no migrations, no retagging, no change to any question or option, and no change to the SEBI, IFSCA, RBI or PFRDA
batches.

## 12. Ready-to-read sample (20 rows)

Chosen with `random.Random(20260924).sample(rows, 20)` over the worksheet rows in file order, then sorted by year,
subject and question number for reading. Re-running the same call on the same file yields the same 20.

---

### S1. 2020 Q16 · agriculture-rural-development · Irrigation coverage and statistics

`05cdbb35-80b7-428f-b7ba-b00608b73aec` · verdict **AGREE** · confidence **high**

**Stem.** Q.16) The proportion area irrigated is high in which state?

- **(A)** Punjab  ✅ **keyed**
- **(B)** Haryana
- **(C)** Himachal Pradesh
- **(D)** Uttarakhand
- **(E)** Kerala Solution – (a)

**short_explanation.** Punjab has the highest proportion of its cropped area irrigated — close to 98 per cent — on the back of canal command from the Sutlej and Beas and very dense tubewell cover.

**option_rationales.**

- **(B)** Haryana is second on this measure, at roughly 90 per cent, but still below Punjab.
- **(C)** Himachal Pradesh is largely rainfed hill farming with a low irrigated share.
- **(D)** Uttarakhand irrigates only the Terai plains well; the hill districts pull the share down.
- **(E)** Kerala has high rainfall and a low irrigated proportion.

**common_traps.**

- The question is about the share of cropped area irrigated, not the absolute irrigated area. Uttar Pradesh leads on absolute area; Punjab leads on proportion.

---

### S2. 2020 Q61 · economic-social-issues · Bank fraud prevention and early warning

`ce5b2d6d-b963-4fe9-b76c-834b9ffb52a2` · verdict **AGREE** · confidence **medium**

**Stem.** Q.61) Government has launched "Fraud Prevention and Management Function" to enable, among others, effective investigation of fraud cases. It talked about Red Flagged Account and EWS. In EWS, S stands for?

- **(A)** System (Early Warning System)
- **(B)** Stream (Early Warning Stream)
- **(C)** Surveillance (Early Warning Surveillance)
- **(D)** Signals (Early Warning Signals)  ✅ **keyed**
- **(E)** Sight (Early Warning Sight) Solution – (d) Three things you can’t miss – Daily current affairs sessions, PIB sessions and Governmental schemes sessions on daily basis. To solve such type of question

**short_explanation.** In the fraud prevention framework EWS stands for Early Warning Signals - the indicators, such as unusual cash movements or delayed stock statements, that put an account on the watchlist.

**explanation_text.** The chain runs in order: early warning signals are triggered in an account, the bank classifies it as a Red Flagged Account, a staff accountability check and forensic examination follow, and if fraud is established it is reported to the RBI and the investigative agencies. The point of the signals is to act while the money is still there, rather than after the account has turned bad.

**option_rationales.**

- **(A)** 'Early Warning System' is the expansion most candidates reach for, but the framework names the signals themselves, which then feed a system.
- **(B)** 'Early Warning Stream' is not a term used in the framework.
- **(C)** 'Early Warning Surveillance' is not the expansion used.
- **(E)** 'Early Warning Sight' is not a term in banking supervision.

**common_traps.**

- 'System' is the natural guess; the framework's term is 'Signals'.

---

### S3. 2020 Q133 · economic-social-issues · Constitutional amendments and reservation

`c1a57f42-8b2a-498f-9b1f-681c33398650` · verdict **AGREE** · confidence **high** · current affairs

**Stem.** Q.133) 124th constitutional amendment Bill states 10% reservation to EWS, the Bill shows income limit for the same is _____ Lakhs

- **(A)** 4
- **(B)** 6
- **(C)** 8  ✅ **keyed**
- **(D)** 10
- **(E)** 12

**short_explanation.** The 124th Constitutional Amendment Bill, enacted as the 103rd Amendment in 2019, gave 10 per cent reservation to economically weaker sections with a family income ceiling of Rs 8 lakh a year.

**explanation_text.** Income is not the only test. The family must also hold less than 5 acres of agricultural land, a residential flat below 1,000 square feet, and residential plots under the notified size. EWS reservation is over and above the existing SC, ST and OBC quotas, which is why it pushes total reservation past the 50 per cent line - upheld by the Supreme Court in 2022.

**option_rationales.**

- **(A)** Rs 4 lakh is not the EWS ceiling.
- **(B)** Rs 6 lakh is not the ceiling; it is often confused with older creamy layer limits.
- **(D)** Rs 10 lakh is above the notified ceiling.
- **(E)** Rs 12 lakh is above the notified ceiling.

**common_traps.**

- Rs 8 lakh is also the OBC creamy layer limit - the same number, but a different test, since EWS adds land and housing conditions.

---

### S4. 2020 Q37 · english-language · Sentence-level correctness selection

`6a8d9dc5-f0ba-4685-b494-5858da75d57e` · verdict **AGREE** · confidence **high**

**Stem.** Q.37) In following question, five different ways of presenting an idea are given. Choose the one that conforms most closely to the standard English usage. “There is little doubt that there has been a significant rise in the number of Indians aware of, and concerned of environmental issues and this number will increase further when more people start realizing that threats to lives are very real when imbalances are created in the system.”

- **(A)** There is little doubt that there has been a significant raise in the number of Indians aware of, and concerned about environmental issues
- **(B)** There is a little doubt that there has been a significant rise in the number of Indians aware of and concerned over environmental issues
- **(C)** There is little doubt that there has been a significant rise in the number of Indians aware of and concerned over environmental issues  ✅ **keyed**
- **(D)** There is little doubt that there has been a significant rise in the number of Indians aware and concerned about environmental issues
- **(E)** There is little doubt that there has been a significant rise in the number of Indians aware and concerned of environmental issues

**short_explanation.** The original's fault is "concerned of"; the fixed combination is "concerned about" or "concerned over", and "aware" must keep its own "of" before the shared object.

**explanation_text.** Two rules decide this item. First, when two adjectives share one object but take different prepositions, both prepositions have to appear: "aware of and concerned over environmental issues". Drop the first and the sentence reads "aware ... environmental issues", which is not English. Second, "little doubt" and "a little doubt" are not the same phrase. Without the article the word is negative and means hardly any doubt, which is what this sentence intends; with the article it means that some doubt does exist.

**option_rationales.**

- **(A)** "Raise" is wrong for an increase in a number - a raise is an increase in pay - and rise is needed.
- **(B)** "A little doubt" says some doubt exists, reversing the sentence's claim that the rise is beyond question.
- **(D)** "Aware and concerned about" leaves aware without its "of".
- **(E)** It drops the "of" after aware and keeps the original's wrong "concerned of".

**common_traps.**

- "Little doubt" against "a little doubt" turns on a single article and flips the meaning.

---

### S5. 2020 Q60 · english-language · Sentence completion with a missing part

`c815efcc-30c2-4bac-b33b-6f6d37550675` · verdict **AGREE** · confidence **high**

**Stem.** Q.60) Which of the following options is carrying forward the idea of the paragraph? Patriotism is a deep love, devotion, and loyalty to one's country, often motivating individuals to contribute positively to its growth and well-being. It can inspire unity and a sense of shared identity, fostering a collective effort ____________________________________

- **(A)** should overcome challenges and work towards a common vision for the nation's progress
- **(B)** will overcome challenges and work towards a common vision for the nation's progress
- **(C)** to overcome challenges and work towards a common vision for the nation's progress  ✅ **keyed**
- **(D)** might overcome challenges and work towards a common vision for the nation's progress
- **(E)** could overcome challenges and work towards a common vision for the nation's progress

**short_explanation.** "Effort" takes a to-infinitive: a collective effort to overcome challenges and work towards a common vision for the nation's progress.

**option_rationales.**

- **(A)** "Should overcome" is a finite verb with no subject; the phrase has to modify "effort".
- **(B)** "Will overcome" has the same fault and turns the purpose into a prediction.
- **(D)** "Might overcome" has the same fault and weakens the purpose to a chance.
- **(E)** "Could overcome" has the same fault.

---

### S6. 2021 Q168 · agriculture-rural-development · Farmer Producer Organisations

`5d37d81d-699f-4c30-a50b-97a244a9ed9d` · verdict **AGREE** · confidence **medium** · current affairs

**Stem.** Q.168) Which state has maximum FPOs?

- **(A)** Maharashtra  ✅ **keyed**
- **(B)** Madhya Pradesh
- **(C)** Karnataka
- **(D)** Uttar Pradesh
- **(E)** West Bengal

**short_explanation.** Maharashtra has the largest number of Farmer Producer Organisations in the country, built up over years of promotion by the state, SFAC and NABARD.

**option_rationales.**

- **(B)** Madhya Pradesh has a large FPO base but fewer than Maharashtra.
- **(C)** Karnataka has an active FPO programme, still behind Maharashtra in numbers.
- **(D)** Uttar Pradesh has many FPOs under the newer scheme but did not lead on the count at the time of this paper.
- **(E)** West Bengal is not among the leading states by FPO count.

---

### S7. 2021 Q23 · english-language · Author tone, attitude and purpose

`dee865ef-584e-46da-8b56-64992ed4228c` · verdict **AGREE** · confidence **medium**

**Stem.** Instructions for Q.21 to Q.25: Read the following passage and answer the questions that follows: It is time to take note of the costs and benefits of nuclear tests. It is now established that India can produce nuclear warheads and the means of delivering them up to a certain distance. With Chinese nuclear warheads deployed in Lhasa and pointed at Indian targets, India has no option but to meet the nuclear blackmail of China with countervailing Indian nuclear deterrent. Indian agencies should push on with plans to develop missiles which can deliver up to 15,000 km, that should be adequately deterrent to all and shall discourage adventurism from any quarter. It has been China's obsession to prevent India from graduating. China assiduously built Pakistan against India, violating commitments under agreements and against the spirit of non-proliferation measures like NPT, CTBT, FMCT and MTCR. Conveniently, USA looked the other way and went out of the way to invent alibis and enact legislation to help in the further building up of Pakistan. China and USA did not endear themselves to thinking Indians. May 1998 shall be remembered in history as the month which saw fundamental changes in power equations in several areas. The change is not limited nuclear weapons; till now exercised by the five powers. It has upset the balance of power so carefully built by the sole remaining superpower and has made nonsense of USA's will and determination, ability and pretension to establish and keep in place a world order which would ensure, among other things, continued maintenance of that monopoly. It has shattered the lingering vestiges of dominance in the nuclear field which has been guarded, so far, by a carefully devised and controlled cartel. With two more Asiatic latecomers and a third knocking at the door (and not even caring to seek admittance), that myth has been demolished. Nothing that the five powers may agree upon, even with the support of several economic powers (Japan, Germany, Canada and Italy) shall revive or re-establish the myth of nuclear superiority or even the nuclear monopoly of the five. The five have no choice but to make peace with the new actuality. The realisation has been most grudging and painful for the five, especially for USA. India should not be begging for recognition as a nuclear weapon state. The Prime Minister's declaration meets the requirement adequately. We should leave the world alone and allow them reasonable time to reconcile themselves to the fact. Nor do we need to beg for a permanent seat on the UN Security Council. If that status is due, the rest of the world shall see that. Let us concentrate on building up our economic strength. The word will, then, want to do business with us. And nothing much will be lost if they don't do business with us. we are not dependent on others for anything basic. Nor are we likely to be brought to our knees if they do not buy our products. Q.23) The author's attitude can be best described as-

- **(A)** Objective
- **(B)** Critical
- **(C)** Nationalistic  ✅ **keyed**
- **(D)** Ambivalent
- **(E)** Arrogant

**short_explanation.** The author writes as an Indian arguing India's case - 'India has no option but to meet the nuclear blackmail of China', 'Let us concentrate on building up our economic strength.' That partisan pride in the national interest is a nationalistic attitude.

**option_rationales.**

- **(A)** An objective writer would weigh the costs he promises at the start to take note of. He never does; the whole piece argues one side.
- **(B)** He is critical of China and the USA, but in passing and in service of the larger claim about India's position. Criticism is one strand here, not the attitude of the piece.
- **(D)** Ambivalence means being pulled two ways. The author shows no doubt at all about the tests or about India's course.
- **(E)** Confidence in one's country is not arrogance. He claims nothing beyond India's right to deter and its capacity to grow, and belittles no one's worth.

**common_traps.**

- 'Critical' feels right just after the paragraph on China and the USA. Attitude has to be judged from the whole passage, and the closing exhortation is pro-India rather than anti-anyone.

---

### S8. 2022 Q93 · decision-making · Anchoring, framing and presentation effects

`cc6eb947-cfe9-4e9b-80dc-3e7b1a72f1ce` · verdict **AGREE** · confidence **high**

**Stem.** Q.93) What type of bias relies too heavily on one piece of information in making a final decision?

- **(A)** Confirmation
- **(B)** Validation
- **(C)** Escalation of Commitment
- **(D)** Anchoring  ✅ **keyed**
- **(E)** Hindsight

**short_explanation.** Anchoring is letting the first piece of information received, such as an opening price or an initial estimate, dominate the final judgement, with later adjustments made only slightly away from it.

**option_rationales.**

- **(A)** Confirmation bias is hunting for evidence that supports a conclusion already reached, which involves many pieces of information, not one.
- **(B)** Not a recognised bias in this list.
- **(C)** Escalation of commitment is pouring more resources into a failing course of action to justify what has already been spent.
- **(E)** Hindsight bias is the after-the-fact sense that the outcome was predictable.

**common_traps.**

- Anchoring is about the weight of the first input; framing is about the way the same information is worded.

---

### S9. 2022 Q122 · economic-social-issues · Life and accident insurance schemes for the poor

`5f5c086b-e8a3-46df-afef-097898622ecb` · verdict **DISPUTED** · confidence **high**

**Stem.** Q.122) PM Suraksha Bima yojana is an affordable insurance scheme for the poor and underprivileged people in the age group of?

- **(A)** 20 to 45
- **(B)** 18 to 60  ✅ **keyed**
- **(C)** 18 to 70
- **(D)** 25 to 75
- **(E)** 30 to 60

**short_explanation.** Pradhan Mantri Suraksha Bima Yojana covers savings account holders aged 18 to 70. That is the widest band among the Jan Suraksha schemes because accident cover does not need the mortality screening that life cover does.

**explanation_text.** PMSBY is a one-year renewable personal accident policy bought by auto-debit from a savings bank account: Rs 2 lakh for accidental death or total permanent disability and Rs 1 lakh for partial permanent disability. The premium was raised from Rs 12 to Rs 20 a year with effect from 1 June 2022. Its sister scheme PMJJBY is life cover, and life cover carries the narrower entry band of 18 to 50 with cover ceasing at 55.

**option_rationales.**

- **(A)** 20 to 45 matches no Jan Suraksha scheme; PMSBY starts at 18 and runs to 70.
- **(C)** 18 to 70 is the band the PMSBY rules actually lay down - see the note on this item.
- **(D)** 25 to 75 matches no scheme circular; entry is from 18 and cover ends at 70.
- **(E)** 30 to 60 matches no scheme circular; PMSBY is open from 18.

**common_traps.**

- PMSBY 18 to 70 for accident cover; PMJJBY 18 to 50 for life cover. The two bands get swapped.

**key_note.** The keyed 18 to 60 matches no PMSBY circular. Eligibility under the scheme is 18 to 70 years, which is option C; the 18 to 50 band belongs to PMJJBY. The key should be corrected.

---

### S10. 2022 Q134 · economic-social-issues · Differentiated banks and rural banking

`a8b13b0a-ec88-4662-bb01-54885f915ebb` · verdict **AGREE** · confidence **high**

**Stem.** Q.134) Regional Rural Banks (RRBs) is not located in which of the following states?

- **(A)** Goa  ✅ **keyed**
- **(B)** Maharashtra
- **(C)** Uttarakhand
- **(D)** Uttar Pradesh
- **(E)** Madhya Pradesh

**short_explanation.** Goa has no Regional Rural Bank; Sikkim is the other state without one. Elsewhere RRBs cover the states, with the heaviest presence in the northern and central plains.

**explanation_text.** RRBs were created by an ordinance in 1975 and the Regional Rural Banks Act, 1976, on the Narasimham Working Group's recommendation, to combine a commercial bank's discipline with a cooperative's local reach. Equity is held 50 per cent by the Centre, 35 per cent by the sponsor commercial bank and 15 per cent by the state government; the RBI regulates them while NABARD supervises them and refinances their lending. Successive rounds of amalgamation cut their number from 196 to 43.

**option_rationales.**

- **(B)** Maharashtra has Maharashtra Gramin Bank and Vidharbha Konkan Gramin Bank.
- **(C)** Uttarakhand has Uttarakhand Gramin Bank.
- **(D)** Uttar Pradesh has several, including Baroda UP Bank, Aryavart Bank and Prathama UP Gramin Bank.
- **(E)** Madhya Pradesh has Madhya Pradesh Gramin Bank and Madhyanchal Gramin Bank.

---

### S11. 2022 Q157 · economic-social-issues · Watershed development

`e26503ca-d06c-4a6e-97d6-1fd757cc31af` · verdict **AGREE** · confidence **medium**

**Stem.** Q.157) Which of the following is not the objective of Watershed Management -

- **(A)** Pollution control
- **(B)** Minimising over-exploitation of resources
- **(C)** Water storage, flood control, checking sedimentation
- **(D)** Wildlife preservation
- **(E)** Sewerage Control  ✅ **keyed**

**short_explanation.** Watershed management works on a drainage basin — conserving soil and moisture, moderating floods and sedimentation, and easing pressure on land, water and vegetation. Sewerage control is an urban sanitation function and does not belong to that set of objectives.

**option_rationales.**

- **(A)** Controlling pollution in the catchment, especially from agricultural and surface runoff, is a standard watershed objective.
- **(B)** Reducing the over-exploitation of soil, water and vegetation is central to the watershed approach.
- **(C)** Water storage, flood moderation and checking sedimentation are the classic objectives of treating a watershed.
- **(D)** Improved vegetation cover and restored water bodies support wildlife, and habitat protection is listed among watershed objectives.

**common_traps.**

- The stem asks which is NOT an objective. Four options are genuine watershed goals, so the answer is the one that belongs to municipal sanitation rather than to catchment treatment.

---

### S12. 2022 Q159 · economic-social-issues · Financial inclusion and Jan Dhan

`4b8e65aa-3b1f-436a-98dd-b1b15d37e7de` · verdict **AGREE** · confidence **high**

**Stem.** Q.159 Consider the following statement - 1) Access 2) Usage 3) Quality Which of the above are sub-Indices of Financial Inclusion Index -

- **(A)** I only
- **(B)** II only
- **(C)** III only
- **(D)** I and II only
- **(E)** I, II and III  ✅ **keyed**

**short_explanation.** RBI's Financial Inclusion Index is built from three sub-indices — Access, Usage and Quality — so all three of the listed items belong.

**explanation_text.** The three dimensions carry different weights: Access 35%, Usage 45% and Quality 20%, drawn together from 97 indicators. The index runs from 0 to 100, where 0 means complete exclusion and 100 full inclusion, and it is published annually for the year ending March. It has no base year — it is constructed afresh each year — so the level is what is read, not a growth rate. Quality is the dimension that captures financial literacy, consumer protection and inequalities in service, which is what separates this index from a simple count of accounts opened.

**option_rationales.**

- **(A)** Access alone leaves out Usage and Quality, both of which are sub-indices.
- **(B)** Usage alone is the heaviest weighted dimension but not the whole index.
- **(C)** Quality alone is the smallest of the three dimensions and cannot stand for the index.
- **(D)** Access and Usage together still omit Quality, the dimension that carries literacy and consumer protection.

---

### S13. 2022 Q31 · english-language · Multi-blank passage cloze

`a7b3a867-e6ef-4263-be06-058a96a3cb59` · verdict **AGREE** · confidence **medium**

**Stem.** Instruction for Q.29 to Q.33: In the following passage, some of the words have been left out. Read the passage carefully and fill in the blanks by selecting the most appropriate alternatives. The question number from which a word is to be selected out of the five given alternatives, is written in each blank space: With their impossible colonial era architecture, lush lawns and prime locations, India’s most exclusive clubs have always been ____(29)___ of the privileged, of which diplomats are an especially ___(30)___ tribes. Established through the 19th century, these clubs were used by colonists as ____(31)____ refuges from the native hordes. Haughty resistance to criticism and ___(32)____ against reform means some rules will remain and leave the clubs ____(33)___ in their colonial affectations for quite a while yet. If you want in, get in line, it’s a long one and straighten your tie. Q.31) Fill the blank -

- **(A)** philistine
- **(B)** churlish
- **(C)** indecorous
- **(D)** urbane  ✅ **keyed**
- **(E)** eloquent

**short_explanation.** The colonists' clubs are being described as polished, sophisticated boltholes, and "urbane" is the one option that means refined and civilised.

**option_rationales.**

- **(A)** Philistine means hostile to culture and refinement — the opposite of what these clubs claimed to be.
- **(B)** Churlish means rude and surly, a description of bad manners rather than of a refuge.
- **(C)** Indecorous means improper or in bad taste, again the reverse of the sense required.
- **(E)** Eloquent describes fluent speech or writing and cannot sensibly describe a refuge.

**key_note.** The cloze passage for blanks 29 to 33 is reprinted in this row's stem. Four of the five options are pejorative or apply only to persons, so elimination settles the blank even if "urbane refuges" reads oddly on its own.

---

### S14. 2022 Q33 · english-language · Multi-blank passage cloze

`6b14a443-7c3e-424a-a010-fb40a44624a6` · verdict **AGREE** · confidence **high**

**Stem.** Instruction for Q.29 to Q.33: In the following passage, some of the words have been left out. Read the passage carefully and fill in the blanks by selecting the most appropriate alternatives. The question number from which a word is to be selected out of the five given alternatives, is written in each blank space: With their impossible colonial era architecture, lush lawns and prime locations, India’s most exclusive clubs have always been ____(29)___ of the privileged, of which diplomats are an especially ___(30)___ tribes. Established through the 19th century, these clubs were used by colonists as ____(31)____ refuges from the native hordes. Haughty resistance to criticism and ___(32)____ against reform means some rules will remain and leave the clubs ____(33)___ in their colonial affectations for quite a while yet. If you want in, get in line, it’s a long one and straighten your tie. Q.33) Fill the blank -

- **(A)** abjuring
- **(B)** ensconced  ✅ **keyed**
- **(C)** spurning
- **(D)** abdicating
- **(E)** decry

**short_explanation.** The clubs are going to stay comfortably settled in their colonial habits, and "ensconced" is the word for being firmly and snugly established somewhere.

**option_rationales.**

- **(A)** Abjuring means solemnly renouncing, which is the reverse of clinging to colonial affectations.
- **(C)** Spurning means rejecting with contempt, again the opposite direction.
- **(D)** Abdicating means giving up a position or responsibility, which does not fit clubs that keep their rules.
- **(E)** Decry is a verb in the wrong form for the slot and means to denounce, the opposite of the required sense.

**key_note.** The cloze passage for blanks 29 to 33 is reprinted in this row's stem. Four of the five options mean rejecting or giving up; only one means settling in, so the sentence's "will remain" decides it.

---

### S15. 2022 Q45 · english-language · Logical Order

`1f5b716b-d852-4d2b-ab18-c08902faa0c5` · verdict **AGREE** · confidence **high**

**Stem.** Q.45) The sentences given in the following question, when properly sequenced, form a coherent paragraph. Choose the most logical order of sentences and mark the answer: (1) With forests covering two-thirds of Russia's territory, wildfires break out every summer. (2) The worst heatwave on record, aggravated by a severe drought has triggered ferocious wildfires that have burned down scores of villages, left thousands of people homeless and forced an evacuation at the country's main nuclear facility. (3) This year, deadly wildfires engulfed European Russia, where four- fifths of the country's 142 million people live. (4) Forests, Russia's great wealth after hydrocarbons, have turned into its curse this summer. (5) But in previous years, they most often affected the sparsely populated territories of Siberia and the far East.

- **(A)** 34521
- **(B)** 23451
- **(C)** 12345
- **(D)** 54321
- **(E)** 42153  ✅ **keyed**

**short_explanation.** The order runs 4-2-1-5-3: sentence 4 states the theme (forests turned from wealth into curse this summer), 2 describes this summer's heatwave and fires, 1 gives the yearly background, 5 contrasts previous years in Siberia, and 3 brings it back to this year in European Russia.

**option_rationales.**

- **(A)** Opening with 3 ("This year") assumes a comparison with earlier years that has not yet been made.
- **(B)** This begins with the heatwave before the theme sentence and ends with the general statement about yearly fires, which belongs before the year-by-year contrast.
- **(C)** The numerical order puts "But in previous years" (5) after "This year" (3), reversing the contrast.
- **(D)** This reverses the whole chain, so the contrast words no longer point anywhere sensible.

**common_traps.**

- The time markers form a chain that cannot be broken: "wildfires break out every summer" (1), then "But in previous years" (5), then "This year" (3). Fixing 1-5-3 as a block leaves only one workable order.

---

### S16. 2022 Q13 · general-intelligence-reasoning · Month and date scheduling puzzle

`cb224fc8-e4ec-4bdd-bad4-a8256ef43eaf` · verdict **AGREE** · confidence **high**

**Stem.** (Instruction for Q.11 to Q.14) Read the given information carefully and answer the questions given below: Eight friends namely G, O, T, L, M, K, A and R were born in different months among January, March, April, July, September and November. Three persons were born in same month. Each of them is from different Cities viz. Kolkata, Patna, Nainital, Agra, Lucknow, Dehradun, Pune and Ranchi. All the above information is not necessarily in the same order. The one who is from Dehradun was born in the month having less than 31 days. T is from Kolkata. G and M were born in same month. Persons who is from Agra and Patna were born in November. L is from Lucknow and he was born in the month having 31 days but not in March. R is from Ranchi and he was born in April. The one who is from Kolkata was born in the month having 30 days after July but before November. The one who is from Pune was born in month having 31 days before April. K was born in July and he is from Nainital. A is from Agra and M is not from Patna. Q.13) Who among the following persons is from Pune?

- **(A)** G
- **(B)** M
- **(C)** O  ✅ **keyed**
- **(D)** Either 1 or 3
- **(E)** None of these

**short_explanation.** Pune's person needs a thirty-one-day month before April, which rules out G and M in November, and once G takes Patna the only city left for O is Pune.

**explanation_text.** One assignment fits everything. L from Lucknow was born in January, O from Pune in March, R from Ranchi in April, K from Nainital in July, T from Kolkata in September, and A from Agra, G from Patna and M from Dehradun all in November, which is the month shared by three people. Three deductions pin it down. The Kolkata person needs a thirty-day month after July and before November, which leaves only September for T. Patna's person is born in November like Agra's, and Patna cannot be T, L, R, K, A or M, so Patna is G or O. If O held Patna, then G and M would take Dehradun and Pune between them, but Pune needs a thirty-one-day month before April while Dehradun needs a month shorter than thirty-one days, and G and M share a birth month, so that branch dies. G is therefore from Patna and born in November, M shares that month, and since Pune's month cannot be November, M is from Dehradun and O from Pune. That leaves the last three months: K already holds July, so L, who needs a thirty-one-day month that is not March, takes January, and O takes March.

**option_rationales.**

- **(A)** G is from Patna, born in November along with A from Agra.
- **(B)** M is from Dehradun, whose person must be born in a month shorter than thirty-one days; November suits that.
- **(D)** G is settled at Patna, so there is nothing open between G and O.
- **(E)** O is from Pune, so a named option is correct.

**key_note.** Solved from the direction block printed with this question, shared across the four questions of the set. Among the six listed months, January, March and July have thirty-one days and April, September and November have thirty. The assignment comes out unique.

---

### S17. 2023 Q17 · computer-knowledge · Input devices and pointing hardware

`0b8a597c-f4c5-47f4-91f6-99927725f2c5` · verdict **AGREE** · confidence **medium**

**Stem.** Q. 17 The action of dragging two fingers across the touchpad of the laptop is used for?

- **(A)** Closing all the open tabs
- **(B)** Zooming in or out of a document or web page  ✅ **keyed**
- **(C)** Right-clicking
- **(D)** Dragging and dropping files or objects
- **(E)** Switching between applications

**short_explanation.** Of the actions listed, the two-finger gesture on a touchpad is the zoom — moving the fingers apart enlarges the view and bringing them together shrinks it.

**option_rationales.**

- **(A)** No standard touchpad gesture closes all open tabs.
- **(C)** Right-clicking is a two-finger tap, a brief press rather than a drag.
- **(D)** Dragging and dropping uses one finger after a click-and-hold, or a three-finger drag where that is enabled.
- **(E)** Switching applications is a three-finger or four-finger swipe on most touchpads.

**common_traps.**

- A two-finger tap is the right-click while a two-finger move is scroll or pinch-zoom — tap and drag are different gestures.

**key_note.** Strictly, dragging two fingers straight across a touchpad scrolls the page; zooming is the pinch form of the same two-finger gesture. Scrolling is not among the options, and zoom is the only listed action that a two-finger movement performs, so the key is the best reading available.

---

### S18. 2023 Q9 · decision-making · Rational decision-making model and its assumptions

`f5e266a3-d51a-45d3-8224-6f6fa0d172e3` · verdict **AGREE** · confidence **high**

**Stem.** Q.9) Among the following, which assumption does not align with the principles of rational decision-making?

- **(A)** Perfect information
- **(B)** Consistency in preferences
- **(C)** Emotion-driven decision making  ✅ **keyed**
- **(D)** Transitivity of preferences
- **(E)** Maximizing utility

**short_explanation.** The rational model assumes a decision-maker with full information who ranks options consistently and picks the one with the highest utility; letting emotion drive the choice contradicts every part of that.

**option_rationales.**

- **(A)** Perfect information is one of the model's standing assumptions.
- **(B)** Consistency of preferences is assumed — the same ranking holds from one choice to the next.
- **(D)** Transitivity, that preferring A to B and B to C implies preferring A to C, is a core axiom of the model.
- **(E)** Maximising utility is the model's stated objective.

**common_traps.**

- The stem asks which assumption does NOT align with the model; four options are genuine assumptions and only one is the odd one out.

---

### S19. 2023 Q9 · economic-social-issues · MGNREGA design, entitlements and performance

`c231f2c2-704e-4fe1-a0be-ab9f05f10ae1` · verdict **AGREE** · confidence **medium**

**Stem.** Q.9) How many days of wage employment is provided under MGNREGS for Scheduled Tribe households living in forest areas?

- **(A)** 120
- **(B)** 130
- **(C)** 140
- **(D)** 150  ✅ **keyed**
- **(E)** 175

**short_explanation.** Scheduled Tribe households living in forest areas who hold no other entitlement under the Forest Rights Act are given 150 days of wage employment, against the general guarantee of 100.

**option_rationales.**

- **(A)** 120 days matches no MGNREGA provision.
- **(B)** 130 days is arbitrary; the enhanced entitlement is 150.
- **(C)** 140 days is arbitrary and falls short of the enhanced entitlement.
- **(E)** 175 days exceeds every entitlement under the Act, including the drought top-up.

**common_traps.**

- 100 days is the base guarantee; 150 for these ST forest households; and 150 again in a drought or calamity-notified area, but that one comes from a different provision.

---

### S20. 2023 Q5 · quantitative-aptitude · Wrong-term series

`1b045273-3a34-4d00-9c74-9023e14430fb` · verdict **AGREE** · confidence **high**

**Stem.** Q.5) 15, 18, 42, 125, 506, 2537

- **(A)** 18
- **(B)** 42  ✅ **keyed**
- **(C)** 125
- **(D)** 2537
- **(E)** 506

**short_explanation.** Each step multiplies by 1, 2, 3, ... and adds 3, 4, 5, ... — so after 15 × 1 + 3 = 18 the next term should be 18 × 2 + 4 = 40, not 42.

**solution_steps.**

1. 15 × 1 + 3 = 18, which matches the series.
2. 18 × 2 + 4 = 40, but the series prints 42.
3. Carrying on from the correct 40: 40 × 3 + 5 = 125, 125 × 4 + 6 = 506, 506 × 5 + 7 = 2537.
4. Every later term is right, so the single wrong term is 42, which should read 40.

**option_rationales.**

- **(A)** 18 is right: 15 × 1 + 3 = 18.
- **(C)** 125 is right: the corrected 40 × 3 + 5 = 125.
- **(D)** 2537 is right: 506 × 5 + 7 = 2537.
- **(E)** 506 is right: 125 × 4 + 6 = 506.

**common_traps.**

- Every later term follows correctly from the corrected 40, so the error sits early in the series rather than at the tail where it is usually hunted.

