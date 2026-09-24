# UPSC CSE Prelims — Explanation Draft: Review Notes (EXPL-07)

Worksheet: `workbench/worksheets/UPSC-EXPLANATIONS-DRAFT.json` — 1209 rows, one per UPSC Civil Services Prelims question in
`workbench/sources/upsc-explanations-input.json` (GS Paper I and CSAT Paper II, 2018–2026). Every row is authored from subject
knowledge and the question's own text; CSAT passage and puzzle sets are solved from the premise their rows carry. No text is
extracted from any third-party source. Nothing here is reviewed. Mains descriptive questions are not in this corpus and were not drafted.

**By subject:** upsc-cse-prelims-gs 891, quantitative-aptitude 170, english-language 78, general-intelligence-reasoning 67, NULL 3.

Conventions follow the six earlier batches (SEBI, IFSCA, RBI, RBI top-up, PFRDA, NABARD): keys defensible on any reasonable reading
are AGREE with the competing reading in `key_note`; flags only where the key is contradicted by its source or the question is
unanswerable as written; puzzles explained from one arrangement; plain language on every row; current-affairs rows carry durable
context with the dated fact stated once; named-slip rationales on numerical distractors.

- AGREE rows whose key_note begins "Accepted as defensible": 58; AGREE rows with any key_note reservation: 252.

**Field set.** The requested fields in the requested order, followed by `current_affairs` and the three provenance fields
(`explanation_source_type = platform_original`, `license_status = owned`, `reviewer_status = pending`), as in earlier batches.
`formula_used` is a single string and `option_rationales` an array, as before; the apply step converts both for the CMS routes.

### Question shapes

Classified from each question's own text (not its subject) by the build script:

| Shape | Rows | GS | CSAT |
|---|---|---|---|
| statement-based | 602 | 494 | 108 |
| matching-pairs | 58 | 58 | 0 |
| assertion-reason | 45 | 45 | 0 |
| other | 504 | 294 | 210 |

On statement-based, matching-pairs and assertion-reason rows the `short_explanation` adjudicates each statement, pair, or
assertion and reason in turn, and the option rationales name only the statement that makes each combination wrong.

## 1. Key verdicts

| Verdict | Count | `final_answer_option_id` |
|---|---|---|
| AGREE | 1161 | set = input `correct_option_id` |
| DISPUTED | 48 | null — awaits a human key decision |
| UNANSWERABLE | 0 | null — awaits a human key decision |
| **Total** | **1209** | **1161 set** |

### 1.1 DISPUTED — the keyed answer is not defensible on any reading

#### 2020 Q8 · upsc-cse-prelims-gs · `8da41853-f145-4f61-9596-0357d4b7005e`

**Stem.** Consider the following statements: 1. 36% of India 36% of India’s districts are classified as “overexploited” or “critical” by the Central Ground Water Authority (CGWA). 2. CGWA was formed under the Environment (Protection) Act. 3. India has the largest area under groundwater irrigation in the world. Which of the statements given above is/are correct?

- **Keyed option:** (a) 1 only
- **Proposed option:** (b) 2 and 3 only
- **Reason.** The input key a (1 only) treats statement 2 as false, but CGWA was constituted by notification under Section 3(3) of the Environment (Protection) Act, 1986, so the key is contradicted by the statute it rests on. Statement 3 is also true on FAO data. Statement 1 misdescribes CGWA's unit of classification (blocks, not districts). Proposed: b (2 and 3 only), which is also the answer widely reported for this question.

#### 2020 Q20 · upsc-cse-prelims-gs · `8e9356a4-06be-48bf-a2f6-69680627d0f1`

**Stem.** In the context of India, which of the following is/are considered to be practice(s) of eco-friendly agriculture? 1. Crop diversification 2. Legume intensification 3. Tensiometer use 4. Vertical farming Select the correct answer using the code given below:

- **Keyed option:** (c) 4 only
- **Proposed option:** (d) 1, 2, 3 and 4
- **Reason.** The input key c (4 only) would make crop diversification, legume intensification and tensiometer-based irrigation not eco-friendly, which no reasonable reading supports; all three are standard sustainable-agriculture practices. Proposed: d (all four), the answer widely reported for this question. Option a (1, 2 and 3) is the only other contender, if vertical farming were excluded for its energy use.

#### 2020 Q27 · upsc-cse-prelims-gs · `6bfa8f1d-1eec-431b-a756-01b9b8eb56ae`

**Stem.** Which of the following are the most likely places to find the musk deer in its natural habitat? 1. Askot Wildlife Sanctuary 2. Gangotri National Park 3. Kishanpur Wildlife Sanctuary 4. Manas National Park Select the correct answer using the code given below:

- **Keyed option:** (c) 3 and 4 only
- **Proposed option:** (a) 1 and 2 only
- **Reason.** The input key c (3 and 4 only) names Kishanpur (terai, Uttar Pradesh) and Manas (foothills, Assam), neither of which has musk deer, while Askot was created for musk deer and Gangotri is well-known musk-deer habitat. Proposed: a (1 and 2 only), the answer widely reported for this question.

#### 2020 Q32 · upsc-cse-prelims-gs · `c56fb969-b220-4517-9ce2-efa1de75c29a`

**Stem.** What is the importance of the term “Interest Coverage Ratio” of a firm in India ? 1. It helps in understanding the present risk of a firm that a bank is going to give loan to. 2. It helps in evaluating the emerging risk of a firm that a bank is going to give loan to. 3. The higher a borrowing firm’s level of Interest Coverage Ratio, the worse is its ability to service its debt. Select the correct answer using the code given below:

- **Keyed option:** (c) 1 and 3 only
- **Proposed option:** (a) 1 and 2 only
- **Reason.** The input key c (1 and 3) requires statement 3 to be true, but by definition a higher interest coverage ratio means earnings cover interest more times over, so debt-servicing ability is better. The key is contradicted by the definition it rests on. Proposed: a (1 and 2 only). Option b (2 only) is the other contender if the ratio is seen only as a forward-looking indicator; it is set aside because the ratio is computed from current earnings.

#### 2020 Q38 · upsc-cse-prelims-gs · `35f67d99-fd34-4ef9-b10e-2cf73df955b7`

**Stem.** Consider the following pairs: River – Flows into 1. Mekong- Andaman Sea 2. Thames – Irish Sea 3. Volga – Caspian Sea 4. Zambezi – Indian Ocean Which of the pairs given above is/are correctly matched?

- **Keyed option:** (a) 1 and 2 only
- **Proposed option:** (c) 3 and 4 only
- **Reason.** The input key a (1 and 2 only) requires the Mekong to flow into the Andaman Sea and the Thames into the Irish Sea; both are plainly false, while the Volga and Zambezi pairs are right. Proposed: c (3 and 4 only), the answer widely reported for this question.

#### 2020 Q42 · upsc-cse-prelims-gs · `84e876c4-4765-4334-8985-fe37ea63ec9f`

**Stem.** With reference to the international trade of India at present, which of the following statements is/are correct? 1. India’s merchandise exports are less than its merchandise imports. 2. India’s imports of iron and steel, chemicals, fertilisers and machinery have decreased in recent years. 3. India’s exports of services are more than its imports of services. 4. India suffers from an overall trade/current account deficit. Select the correct answer using the code given below:

- **Keyed option:** none — the input carries no key
- **Proposed option:** (d) 1, 3 and 4 only
- **Reason.** No key in the input (the question appears to have been dropped from UPSC's final key). Solved as of 2019-20 data: statements 1, 3 and 4 are true, giving d. The likely reason for the drop is that India's current account turned to surplus in the April-June 2020 quarter, before the exam, making statement 4 uncertain; on that reading no option would fit exactly.

#### 2020 Q49 · upsc-cse-prelims-gs · `b374b04f-94a6-4f74-8cd2-ad831d96ed46`

**Stem.** Consider the following statements: 1. In terms of short-term credit delivery to the agriculture sector, District Central Cooperative Banks (DCCBs) deliver more credit in comparison to Scheduled Commercial Banks and Regional Rural Banks. 2. One of the most important functions of DCCBs is to provide funds to the Primary Agricultural Credit Societies. Which of the statements given above is/are correct?

- **Keyed option:** (d) Neither 1 nor 2
- **Proposed option:** (b) 2 only
- **Reason.** Keyed option d (neither) is not defensible: statement 2 describes the DCCB's basic role in the three-tier cooperative structure and is correct. UPSC's own reading is only 2. Proposed b.

#### 2020 Q51 · upsc-cse-prelims-gs · `1da61e0a-8889-4b7f-bb2a-9b046a7fbfc3`

**Stem.** With reference to carbon nanotubes, consider the following statements : 1. They can be used as carriers of drugs and antigens in the human body. 2. They can be made into artificial blood capillaries for an injured part of human body. 3. They can be used in biochemical sensors. 4. Carbon nanotubes are biodegradable. Which of the statements given above are correct?

- **Keyed option:** (a) 1 and 2 only
- **Proposed option:** (d) 1, 2, 3 and 4
- **Reason.** Keyed option a (1 and 2 only) is not defensible because it leaves out statement 3, and nanotube biosensors are well established. Proposed d, matching UPSC's published answer; option c (dropping statement 2) is the other reading candidates took and is set aside because nanotube-based vascular grafts are an active research use.

#### 2020 Q52 · upsc-cse-prelims-gs · `b1ce30b2-5dde-4c57-afe9-f3ca408208ac`

**Stem.** Consider the following activities: 1. Spraying pesticides on a crop field 2. Inspecting the craters of active volcanoes 3. Collecting breath samples from spouting whales for DNA analysis At the present level of technology, which of the above activities can be successfully carried out by using drones?

- **Keyed option:** (a) 1 and 2 only
- **Proposed option:** (d) 1, 2 and 3
- **Reason.** Keyed option a (1 and 2 only) is not defensible: drones already collect whale blow samples (the SnotBot programme), so activity 3 is also possible. Proposed d, which is UPSC's own answer.

#### 2020 Q54 · upsc-cse-prelims-gs · `899a3e91-0514-4792-b7ee-0f8b66bc31f1`

**Stem.** Consider the following statements: 1. Genetic changes can be introduced in the cells that produce eggs or sperms of a prospective parent. 2. A person’s genome can be edited before birth at the early embryonic stage. 3. Human induced pluripotent stem cells can be injected into the embryo of a pig. Which of the statements given above is/are correct?

- **Keyed option:** (a) 1 only
- **Proposed option:** (d) 1, 2 and 3
- **Reason.** Keyed option a (1 only) is not defensible: embryo editing and human-pig chimera experiments have both been reported. Proposed d, UPSC's own answer.

#### 2020 Q55 · upsc-cse-prelims-gs · `785eb850-8fa9-4783-9306-a63ace6ae9d7`

**Stem.** What is the importance of using Pneumococcal Conjugate Vaccines in India? 1. These vaccines are effective against pneumonia as well as meningitis and sepsis. 2. Dependence on antibiotics that are not effective against drug-resistant bacteria can be reduced. 3. These vaccines have no side effects and cause no allergic reactions. Select the correct answer using the code given below:

- **Keyed option:** (d) 1.2 and 3
- **Proposed option:** (b) 1 and 2 only
- **Reason.** Keyed option d (all three) is not defensible because statement 3 claims no side effects or allergic reactions, which is false for PCV as for any vaccine. Proposed b, UPSC's own answer.

#### 2020 Q66 · upsc-cse-prelims-gs · `538b55a8-7847-44ed-aeb4-79ac397840b3`

**Stem.** With reference to the scholars/litterateurs of ancient India, consider the following statements: 1. Panini is associated with Pushyamitra Shunga. 2. Amarasimha is associated with Harshavardhana. 3. Kalidasa is associated with Chandra Gupta – II. Which of the statements given above is/are correct?

- **Keyed option:** (d) 1, 2 and 3
- **Proposed option:** (c) 3 only
- **Reason.** Keyed option d (all three) is not defensible: Panini predates the Shungas and Amarasimha is placed in Chandragupta II's court. Proposed c, UPSC's own answer.

#### 2020 Q68 · upsc-cse-prelims-gs · `b026b038-56ac-4c5e-a5ef-cfcc30a11699`

**Stem.** With the present state of development, Artificial Intelligence can effectively do which of the following? 1. Bring down electricity consumption in industrial units 2. Create meaningful short stories and songs 3. Disease diagnosis 4. Text-to-Speech Conversion 5. Wireless transmission of electrical energy Select the correct answer using the code given below:

- **Keyed option:** (c) 2, 4 and 5 only
- **Proposed option:** (b) 1, 3 and 4 only
- **Reason.** Keyed option c (2, 4 and 5) is not defensible because it includes wireless transmission of electrical energy, which is not something AI does. Proposed b, UPSC's own answer. Whether AI can create 'meaningful' stories and songs was contested in 2020 and is more plausible today; that does not rescue option c.

#### 2020 Q75 · upsc-cse-prelims-gs · `06ac4820-0c31-4979-b5de-7bc55fdf84c8`

**Stem.** Which of the following phrases defines the nature of the ‘Hundi’ generally referred to in the sources of the post-Harsha period?

- **Keyed option:** (c) A diary to be maintained for daily accounts
- **Proposed option:** (b) A bill of exchange
- **Reason.** Keyed option c (a diary of daily accounts) is not defensible: a hundi is by definition a bill of exchange. Proposed b, UPSC's own answer.

#### 2020 Q77 · upsc-cse-prelims-gs · `b2ab3c54-1152-4fcd-b270-9b98f7f757bf`

**Stem.** The Gandhi-Irwin Pact included which of the following? 1. Invitation to Congress to participate in the Round Table Conference Withdrawal of Ordinances promulgated in connection with the Civil Disobedience Movement 3. Acceptance of Gandhiji’s suggestion for enquiry into police excesses 4. Release of only those prisoners who were not charged with violence Select the correct answer using the code given below:

- **Keyed option:** none — the input carries no key
- **Proposed option:** (b) 1, 2 and 4 only
- **Reason.** No key in the input (the question appears to have been dropped from UPSC's final key). The stem is also garbled: the number of item 2 (withdrawal of ordinances) is missing. On the historical record items 1, 2 and 4 were in the pact and item 3 was refused, so option b is proposed.

#### 2020 Q84 · upsc-cse-prelims-gs · `0caaffdf-9450-4b45-affb-2181717f6a7f`

**Stem.** One common agreement between Gandhism and Marxism is

- **Keyed option:** (d) economic determinism
- **Proposed option:** (a) the final goal of a stateless society
- **Reason.** Keyed option d (economic determinism) is not defensible: Gandhi explicitly rejected the materialist view of history. The shared ideal is a stateless society. Proposed a, UPSC's own answer.

#### 2020 Q86 · upsc-cse-prelims-gs · `0f868ff0-00f0-44c2-a552-fb0b22bfd574`

**Stem.** The Preamble to the Constitution of India is

- **Keyed option:** (a) a part of the Constitution but has no legal effect
- **Proposed option:** (d) a part of the Constitution but has no legal effect independently of other parts
- **Reason.** Keyed option a (no legal effect) is not defensible when option d offers the precise position: the Preamble has interpretive legal effect but none on its own. Proposed d, UPSC's own answer.

#### 2020 Q90 · upsc-cse-prelims-gs · `c9b2ce8e-1f63-4dcd-b7eb-d077fad24031`

**Stem.** Consider the following statements: 1. The President of India can summon a session of the Parliament at such place as he/she thinks fit. 2. The Constitution of India provides for three sessions of the Parliament in a year, but it is not mandatory to conduct all three sessions. There is no minimum number of days that the Parliament is required to meet in a year. Which of the statements given above is/are correct?

- **Keyed option:** (d) 2 and 3 only
- **Proposed option:** (c) 1 and 3 only
- **Reason.** Keyed option d (2 and 3) is not defensible: statement 2 is false because the three-session pattern is convention, and statement 1 is true under Article 85. The stem also lacks the number 3 before its third statement. Proposed c, UPSC's own answer.

#### 2021 Q30 · upsc-cse-prelims-gs · `557f3882-b268-4413-ba53-f771267d6223`

**Stem.** Consider the following statements: In India, there is no law restricting the candidates from contesting in one Lok Sabha election from three constituencies. In 1991, Lok Sabha Election, Shri Devi Lal contested from three Lok Sabha constituencies As per the existing rules, if a candidate contests in one Lok Sabha election from many constituencies, his/her party should bear the cost of bye-elections to the constituencies vacated by him/her in the event of him/her winning in all the constituencies. Which of the statements given above is/are correct?

- **Keyed option:** none — the input carries no key
- **Proposed option:** (b) 2 Only
- **Reason.** No key in the input (the question appears to have been dropped from UPSC's final key). Solved as 2 only: statement 1 is wrong under Section 33(7) of the RP Act and statement 3 describes only an Election Commission proposal. The likely reason for dropping is doubt over the historical detail in statement 2.

#### 2022 Q60 · upsc-cse-prelims-gs · `5755484f-3834-4059-b2ec-39465464c4d8`

**Stem.** According to Kautilya’s Arthashastra, which of the following are correct? A person could be a slave as a result of the judicial punishment. If a females slave bore her master a son she was legally free. If a son born to a female slave was fathered by her master, the son was entilted to the legal status of the master’s son. Which of the statements given above are correct?

- **Keyed option:** (b) 2 and 3 only
- **Proposed option:** (d) 1, 2 and 3
- **Reason.** The keyed option b (2 and 3 only) leaves out statement 1, but the Arthashastra names enslavement by judicial punishment (dandapranita) as a recognised route, and the standard account of these rules states all three points together. UPSC's own final key is understood to give d (1, 2 and 3). Proposed d.

#### 2022 Q61 · upsc-cse-prelims-gs · `0dba293a-dfde-4bb2-831a-b088430da53f`

**Stem.** Consider the following statements: Tight monetary policy of US Federal Reserve could lead to capital flight. Capital flight may increase the interest cost of firms with existing External Commercial Borrowings (ECBs). Devaluation of domestic currency decreases the currency risk associated with ECBS. Which of the statements given above are correct?

- **Keyed option:** none — the input carries no key
- **Proposed option:** (a) 1 and 2 only
- **Reason.** No key in the input (the question appears to have been dropped from UPSC's final key). On a plain reading statements 1 and 2 hold and statement 3 is false, so option a. The drop was probably because statement 2 is loosely worded: the contracted rate on an existing ECB does not change, only its rupee cost.

#### 2022 Q67 · upsc-cse-prelims-gs · `6be57bb2-eb58-4056-ba3f-780b175e6370`

**Stem.** Consider the following statements: Vietnam has been one of the fastest growing economies in the world in the recent years. Vietnam is led by a multi-party political system. Vietnam’s economic growth is linked to its integration with global supply chains and focus on exports. For a long time Vietnam’s low labour costs and stable exchange rates have attracted global manufacturers. Vietnam has the most productive e-service sector in the Indo-Pacific region. Which of the statements given above are correct?

- **Keyed option:** (c) 1 and 2
- **Proposed option:** (d) 1, 3 and 4
- **Reason.** The keyed option c (1 and 2) includes statement 2, which is plainly false: Vietnam is governed by a single party, the Communist Party of Vietnam. Statements 1, 3 and 4 are the correct ones, which is option d; UPSC's own final key is understood to give d.

#### 2023 Q34 · upsc-cse-prelims-gs · `49681c80-c36e-4da5-82de-1efae2d4c18c`

**Stem.** In India, which one of the following Constitutional Amendments was widely believed to be enacted to overcome the judicial interpretations of the Fundamental Rights?

- **Keyed option:** none — the input carries no key
- **Proposed option:** (a) 1st Amendment
- **Reason.** No key in the input (the question appears to have been dropped from UPSC's final key). Option a is proposed: the First Amendment is the classic case of an amendment passed to undo court rulings on Fundamental Rights. The 42nd Amendment is a weaker rival, since it also sought to curb judicial review, which is likely why the question was dropped.

#### 2023 Q57 · quantitative-aptitude · `e771c4d7-b18c-4355-9956-2e18028fa819`

**Stem.** A rectangular floor measures 4 m in length and 2.2m in breadth. Tiles of size 140 cm by 60 cm have to be laid such that the tiles do not overlap. A tile can be placed in any orientation so long as its edges are parallel to the edges of the floor. What is the maximum number of tiles that can be accommodated on the floor?

- **Keyed option:** (c) 8
- **Proposed option:** (d) 9
- **Reason.** The key gives 8, but a concrete layout fits 9 tiles within the 400 cm × 220 cm floor with edges parallel to the walls (verified by an exhaustive search on a 20 cm grid, which found no layout of 10). Since the question asks for the maximum, 8 is not defensible; 9 (option d) is proposed.

#### 2024 Q20 · upsc-cse-prelims-gs · `b3305b4a-483e-441d-a71c-d26399c4d2a8`

**Stem.** The North Eastern Council (NEC) was established by the North Eastern Council Act, 1971. Subsequent to the amendment of NEC Act in 2002, the Council comprises which of the following members? Governor of the Constituent State Chief Minister of the Constituent State Three Members to be nominated by the President of India The Home Minister of India Select the Correct answer using the code given below:

- **Keyed option:** (b) 1, 3 and 4 only
- **Proposed option:** (a) 1, 2 and 3 only
- **Reason.** The keyed option b (1, 3 and 4) omits the Chief Ministers, who are members under Section 3 of the NEC Act as amended in 2002, so the key is not defensible. Proposed a (1, 2 and 3 only), the statutory composition the stem asks about. Secondary reading: d (all four), if the Union Home Minister's ex officio chairmanship under the 2018 Cabinet decision is counted; set aside because it does not come from the Act. Either way b fails.

#### 2024 Q21 · upsc-cse-prelims-gs · `623f2387-100b-4e2f-9896-5fe18d6767ba`

**Stem.** Consider the following statements regarding ‘Nari Shakti Vandan Adhiniyam’: Provisions will come into effect from the 18th Lok Sabha. This will be in force for 15 years after becoming an Act. There are provisions for the reservation of seats for scheduled Castes Women within the quota reserved for the Scheduled Castes. Which of the statements given above are correct?

- **Keyed option:** (d) 1 and 3
- **Proposed option:** (c) 2 and 3 only
- **Reason.** The input key (d, statements 1 and 3) includes statement 1, which is contradicted by Article 334A: the reservation takes effect only after delimitation following the first census after commencement, so it could not apply to the 18th Lok Sabha. Statements 2 and 3 are both correct, giving option c.

#### 2024 Q22 · upsc-cse-prelims-gs · `0882c6df-1b80-4fd7-b786-7b8b48d4c265`

**Stem.** Which of the following statements about ‘Exercise Mitra Shakti-2023’ are correct? This was a joint military exercise between India and Bangladesh. It commenced in Aundh (Pune). Joint response during counter-terrorism operations was a goal of this operation. Indian Air Force was a part of this exercise Select the answer using the code given below:

- **Keyed option:** (c) 1, 3 and 4
- **Proposed option:** (d) 2, 3 and 4
- **Reason.** The input key (c) includes statement 1, but Mitra Shakti is an India–Sri Lanka exercise; the 2023 edition at Aundh, Pune also included IAF personnel, so statements 2, 3 and 4 are correct and option d is right.

#### 2024 Q25 · upsc-cse-prelims-gs · `6e88e0bb-718a-4e9a-84fe-6664204ad399`

**Stem.** With reference to Union Budget, consider the following statements: The Union Finance Minister on behalf of the Prime Minister lays the Annual Financial Statement before both the House of Parliament. At the Union level, no demand for a grant can be made except on the recommendation of the President of India. Which of the statements given above is/are correct?

- **Keyed option:** (c) Both 1 and 2
- **Proposed option:** (b) 2 only
- **Reason.** The input key (c, both) cannot stand: Article 112 has the President cause the Annual Financial Statement to be laid, so the Finance Minister acts on the President's behalf, not the Prime Minister's. Only statement 2 is correct, giving option b.

#### 2024 Q35 · upsc-cse-prelims-gs · `fbca24f4-91e2-4c66-86b2-5d38e52842fa`

**Stem.** Consider the following information –> Archaeological Site: State Description Salihundam – Andhra Pradesh Rock-cut cave shrines Chandraketugarh – Odisha Trading Port town Inamgaon – Maharashtra Chalcolithic site Mangadu – Kerala Megalithic site In which of the above rows is the given information correctly matched?

- **Keyed option:** (b) 2 and 3
- **Proposed option:** (c) 3 and 4
- **Reason.** The input key (b, rows 2 and 3) includes row 2, but Chandraketugarh lies in North 24 Parganas district of West Bengal, not Odisha. Rows 3 and 4 are correct, giving option c.

#### 2024 Q38 · upsc-cse-prelims-gs · `2f37036a-7941-4740-8ac1-d4520282146c`

**Stem.** Consider the following statements: There are parables in Upanishads. Upanishads were composed earlier than the Puranas Which of the statements given above is/are correct?

- **Keyed option:** (b) 2 only
- **Proposed option:** (c) Both 1 and 2
- **Reason.** The input key (b, only 2) treats statement 1 as false, but the Upanishads plainly contain parables (Nachiketa, Satyakama, Svetaketu and the salt in water, the contest of the senses). Both statements are correct, giving option c.

#### 2024 Q41 · upsc-cse-prelims-gs · `09b05d83-41b2-43fd-830d-edc8b0568cd4`

**Stem.** Consider the following statements: Statement-I : There is instability and worsening security situation in the Sahel region. Statement-II : There have been military takeovers/coups d’etat in several countries of the Sahel region in the recent past. Which one of the following is correct in respect of the above statements?

- **Keyed option:** (d) Statement-I is incorrect, but Statement-II in correct
- **Proposed option:** (a) Both Statement-I and Statement-II are correct and Statement-II explains Statement-I
- **Reason.** The input key (d) says Statement-I is incorrect, which is contradicted by the widely reported insecurity across the Sahel. Both statements are correct; option a is proposed because the coups feed the instability. Option b is the competing reading if the insurgency, not the coups, is taken as the root cause.

#### 2024 Q43 · upsc-cse-prelims-gs · `35c5afcd-80c8-4732-8dcb-d790df0c25f5`

**Stem.** With reference to the Speaker of the Lok Sabha, consider the following statements: While any resolution for the removal of the Speaker of the Lok Sabha is under consideration He She shall not preside He/She shall not have the right to speak He She shall not be entitled to vote on the resolution in the first instance. Which of the statements given above is/are correct

- **Keyed option:** (c) 2 and 3 only
- **Proposed option:** (a) 1 only
- **Reason.** The input key (c, statements 2 and 3) contradicts Article 96(2), which gives the Speaker the right to speak and to vote in the first instance during the removal resolution. Only statement 1 is correct, giving option a.

#### 2024 Q52 · upsc-cse-prelims-gs · `18b7adde-6b72-4ab8-aedd-9af63781ccd1`

**Stem.** Consider the following statements: Statement-I: Thickness of the troposphere at the equator is much greater as compared to poles. Statement-II: At the equator, heat is transported to great heights by strong convectional currents. Which one of the following is correct in respect of the above statements?

- **Keyed option:** (b) Both Statement-I and Statement-II are correct, but Statement-II does not explain Statement-I
- **Proposed option:** (a) Both Statement-I and Statement-II are correct and Statement-I Statement-II explains
- **Reason.** The input key (b) says Statement-II does not explain Statement-I, but the NCERT geography text gives exactly this reason: the troposphere is thickest at the equator because strong convectional currents carry heat to great heights. Option a is proposed.

#### 2024 Q53 · upsc-cse-prelims-gs · `da459d32-01ff-4e07-a0af-0216469cf259`

**Stem.** Consider the following: Pyroclastic debris Ash and dust Nitrogen compounds Sulphur compounds How many of the above are products of volcanic eruptions?

- **Keyed option:** (c) Only three
- **Proposed option:** (d) All four
- **Reason.** The input key (c, only three) cannot stand: standard geography texts list pyroclastic debris, ash and dust, and gases including nitrogen compounds and sulphur compounds among volcanic products. All four apply, giving option d.

#### 2024 Q58 · upsc-cse-prelims-gs · `a9c69e0b-c622-4d75-bdbe-f79cb030f47e`

**Stem.** Consider the following countries: Finland Germany Norway Russia How many of the above countries have a border with the North Sea?

- **Keyed option:** (c) Only three
- **Proposed option:** (b) Only two
- **Reason.** The input key (c, only three) cannot stand: of the four countries only Germany and Norway touch the North Sea; Finland and Russia front the Baltic. Option b is proposed.

#### 2024 Q64 · upsc-cse-prelims-gs · `37693dcb-a24d-4b61-9c55-638233e37e60`

**Stem.** Consider the following statements regarding World Toilet Organization: It is one of the agencies of the United Nations. World Toilet Summit, World Toilet Day and World Toilet College are the initiatives of this organization, to inspire action to tackle the global sanitation crisis. The main focus of its function is to grant funds to the least developed countries and developing countries to achieve the end of open defecation. Which of the statements given above is/are correct?

- **Keyed option:** (d) 2 and 3
- **Proposed option:** (a) 2 only
- **Reason.** The input key (d, statements 2 and 3) includes statement 3, but the World Toilet Organization is an advocacy and training NGO, not a donor that funds countries. Only statement 2 is correct, giving option a.

#### 2024 Q65 · upsc-cse-prelims-gs · `d76de44b-a734-43e9-b46b-8d1207b08020`

**Stem.** Consider the following statements: Lions do not have a particular breeding season. Unlike most other big cats, cheetahs do not roar. Unlike male lions, male leopards do not proclaim their territory by scent marking. Which of the statements given above are correct?

- **Keyed option:** (c) 1 and 3 only
- **Proposed option:** (a) 1 and 2 only
- **Reason.** The input key (c, statements 1 and 3) includes statement 3, but male leopards do proclaim territory by scent marking, and omits statement 2, which is true since cheetahs do not roar. Option a is proposed.

#### 2024 Q67 · upsc-cse-prelims-gs · `6b938cbe-c52f-4c43-84c6-8ba71e5d03f1`

**Stem.** Consider the following: Battery storage Biomass generators Fuel cells Rooftop solar photovoltaic units How many of the above are considered “Distributed Energy Resources”?

- **Keyed option:** (b) Only two
- **Proposed option:** (d) All four
- **Reason.** The input key (b, only two) cannot stand: standard definitions (for example the US EPA's) list battery storage, fuel cells, generators including biomass, and rooftop solar as distributed energy resources. All four qualify, giving option d.

#### 2024 Q70 · upsc-cse-prelims-gs · `57d52a3b-f232-4d4c-987e-d3b126d0296e`

**Stem.** Consider the following: Cashew Papaya Red sanders How many of the above trees are actually native to India?

- **Keyed option:** (d) None
- **Proposed option:** (a) Only one
- **Reason.** The input key (d, none) cannot stand: red sanders (Pterocarpus santalinus) is endemic to the Eastern Ghats of Andhra Pradesh and so is native to India. Exactly one tree is native, giving option a.

#### 2024 Q71 · upsc-cse-prelims-gs · `4e703559-287a-4355-a460-1eb2ec60d1f7`

**Stem.** Consider the following airports: Donyi Polo Airport Kushinagar International Airport Vijayawada International Airport In the recent past, which of the above have been constructed as Greenfield projects?

- **Keyed option:** (b) 2 and 3 only
- **Proposed option:** (a) 1 and 2 only
- **Reason.** The input key (b, 2 and 3 only) omits Donyi Polo, which was built from scratch as a greenfield airport, and includes Vijayawada, an existing airport upgraded with a new terminal. Option a is proposed. Options b and c carry identical text in the input.

#### 2024 Q75 · upsc-cse-prelims-gs · `8f1a11a7-26ac-4c3a-a10d-eb867872cb9c`

**Stem.** On June 21 every year, which of the following latitude(s) experience(s) a sunlight of more than 12 hours? Equator Tropic of Cancer Tropic of Capricorn Arctic Circle Select the correct answer using the code given below:

- **Keyed option:** (b) 2 only
- **Proposed option:** (d) 2 and 4
- **Reason.** The input key (b, 2 only) omits the Arctic Circle, which has 24 hours of daylight on 21 June, so it too has more than 12 hours. Option d is proposed.

#### 2024 Q81 · upsc-cse-prelims-gs · `c5260b80-4bc1-40a1-addd-82fe43001844`

**Stem.** The total fertility rate in an economy is defined as:

- **Keyed option:** (c) the birth rate minus death rate.
- **Proposed option:** (d) the average number of live births a woman would have by the end of her child-bearing age.
- **Reason.** The input key (c) gives the rate of natural increase (birth rate minus death rate), which is not the total fertility rate. Option d states the standard definition and is proposed.

#### 2024 Q82 · upsc-cse-prelims-gs · `2e712ad3-2360-47fa-ab03-ee4e693fad35`

**Stem.** Consider the following statements: In India, Non-Banking Financial Companies can access the Liquidity Adjustment Facility window of the Reserve Bank of India. In India, Foreign Institutional Investors can hold the Government Securities (G-Secs). In India, Stock Exchanges can offer separate trading platforms for debts. Which of the statements given above is/are correct?

- **Keyed option:** (c) 1, 2 and 3
- **Proposed option:** (d) 2 and 3 only
- **Reason.** The input key (c, all three) needs statement 1, but the LAF window is for banks and standalone primary dealers, not NBFCs generally. A reading set aside: standalone primary dealers are registered as NBFCs and do access the LAF, but the statement speaks of NBFCs as a class. Option d is proposed; confidence medium because of that narrow exception.

#### 2024 Q83 · upsc-cse-prelims-gs · `459035d6-a907-48ae-a15b-ae1c87cf19c1`

**Stem.** In India, which of the following can trade in Corporate Bonds and Government Securities? Insurance Companies Pension Funds Retail Investors Select the correct answer using the code given below:

- **Keyed option:** (b) 2 and 3 only
- **Proposed option:** (d) 1, 2 and 3
- **Reason.** The input key (b) leaves out insurance companies, which are among the largest holders of government securities and corporate bonds. All three categories can trade, giving option d.

#### 2024 Q86 · upsc-cse-prelims-gs · `937b1d0f-14bb-4f36-9aad-87547456df20`

**Stem.** Consider the following materials: Agricultural residues Corn grains Wastewater treatment sludge Wood mill waste Which of the above can be used as feedstock for producing Sustainable Aviation Fuel?

- **Keyed option:** (a) 1 and 2 only
- **Proposed option:** (c) 1, 2, 3 and 4
- **Reason.** The keyed option (a, 1 and 2 only) is contradicted by the standard SAF feedstock lists, which name corn grain, agricultural residues, wood mill waste and wastewater treatment sludge together. No reasonable reading excludes sludge and wood mill waste while keeping residues. Proposed c (all four). Worth a reviewer check that the input key maps to the right booklet series.

#### 2024 Q100 · upsc-cse-prelims-gs · `846ebbd8-6370-4ccc-8372-f402daf513be`

**Stem.** With reference to the Indian economy, “Collateral Borrowing and Lending Obligations” are the instruments of:

- **Keyed option:** (b) Forex market
- **Proposed option:** (c) Money market
- **Reason.** The keyed option (b, forex market) is contradicted by RBI and CCIL descriptions, which class CBLO as a money market instrument for short-term rupee borrowing and lending against government securities. Proposed c. Worth a reviewer check that the input key maps to the right booklet series.

#### 2025 Q56 · upsc-cse-prelims-gs · `92a51f9e-ebd6-4411-937e-04a8b8233ea5`

**Stem.** Consider the following statements : With reference to the Constitution of India, if an area in a State is declared as Scheduled Area under the Fifth Schedule I. the State Government loses its executive power in such areas and a local body assumes total administration II. the Union Government can take over the total administration of such areas under certain circumstances on the recommendations of the Governor Which of the statements given above is/are correct?

- **Keyed option:** (C) Both I and II
- **Proposed option:** (B) II only
- **Reason.** The keyed option c needs Statement I to be correct, but paragraph 2 of the Fifth Schedule says the executive power of the State extends to the Scheduled Areas; no local body assumes total administration. Option b is proposed, reading Statement II as the Union's power to give directions on the Governor's reports. If Statement II is read strictly ('take over total administration' is not in the Schedule), option d (neither) would follow instead.

#### 2025 Q88 · upsc-cse-prelims-gs · `34c03f48-ef68-473b-bbd0-f2e0137adf5e`

**Stem.** Consider the following statements : I. If any question arises as to whether a Member of the House of the People has become subject to disqualification under the 10th Schedule, the President's decision in accordance with the opinion of the Council of Union Ministers shall be final. II. There is no mention of the word 'political party' in the Constitution of India. Which of the statements given above is/are correct?

- **Keyed option:** (A) I only
- **Proposed option:** (D) Neither I nor II
- **Reason.** The keyed option a needs Statement I to be correct, but paragraph 6 of the Tenth Schedule gives the decision to the Speaker, not to the President on the Council of Ministers' opinion. Statement II is also false because the Tenth Schedule uses 'political party'. Option d is proposed; the input key may be mis-mapped from another booklet series.

### 1.2 UNANSWERABLE — cannot be answered as written

None.

### 1.3 Rows with no key in the input

5 GS rows arrive with `correct_option_id` null and no option flagged correct, consistent with questions UPSC dropped
from its final key. They cannot be AGREE (there is no key to agree with). Each is drafted, marked DISPUTED with the draft's answer
proposed, and listed in §1.1 above; a human decides whether to publish them at all.

- 2020 Q42 · `84e876c4-4765-4334-8985-fe37ea63ec9f` · proposed (d) 1, 3 and 4 only
- 2020 Q77 · `b2ab3c54-1152-4fcd-b270-9b98f7f757bf` · proposed (b) 1, 2 and 4 only
- 2021 Q30 · `557f3882-b268-4413-ba53-f771267d6223` · proposed (b) 2 Only
- 2022 Q61 · `0dba293a-dfde-4bb2-831a-b088430da53f` · proposed (a) 1 and 2 only
- 2023 Q34 · `49681c80-c36e-4da5-82de-1efae2d4c18c` · proposed (a) 1st Amendment

### 1.4 Where the disputes fall

Disputes on keyed rows, by year and paper:

| Year | GS rows | GS disputed | CSAT rows | CSAT disputed |
|---|---|---|---|---|
| 2018 | 100 | 0 | 0 | 0 |
| 2019 | 100 | 0 | 0 | 0 |
| 2020 | 100 | 16 | 0 | 0 |
| 2021 | 100 | 0 | 0 | 0 |
| 2022 | 100 | 2 | 0 | 0 |
| 2023 | 100 | 0 | 80 | 1 |
| 2024 | 97 | 22 | 75 | 0 |
| 2025 | 100 | 2 | 80 | 0 |
| 2026 | 94 | 0 | 83 | 0 |

The disputes are not spread evenly: they sit almost entirely in the 2020 and 2024 GS papers. In those rows the stored key
contradicts a plain fact (for example 2020 Q86: the Preamble is part of the Constitution but has no legal effect independently
of other parts; 2020 Q75: a hundi is a bill of exchange; 2024 Q22: Mitra Shakti is an India–Sri Lanka exercise), and for the
2020 items checked by hand the proposed option matches UPSC's own published answer while the stored key does not. The likely
cause is key ingestion (for example a key taken from a different booklet series), not UPSC error. **Before anything is
verified, the stored keys for the 2020 and 2024 GS papers should be re-checked against UPSC's official answer key**; the AGREE
rows in those two papers were accepted on their stored keys and may carry the same defect where the stored key happens to be
defensible.

### 1.5 CSAT rows stored without their passage

81 CSAT rows (comprehension, assumption and inference items) arrive with only the question and options; the passage
they depend on is not in `question_text`. The repository holds CSAT passages only for 2025 (migration
`228_pyq_upsc_cse_2025_prelims_csat_canonical.sql`), and 2025 rows were drafted from those passages with quotations, except four
items (2025 Q3, Q4, Q11, Q12) that migration 228 itself marks `source_passage_absent`. None exist for 2023, 2024 or 2026.
The rows listed here accept the official key and
explain it from the wording of the statements; each says in `key_note` that the passage was not available, and most are at
medium or low confidence. They should be re-drafted with quotations once the passages are loaded.

| Year | Rows without passage |
|---|---|
| 2023 | 27 |
| 2024 | 27 |
| 2025 | 4 |
| 2026 | 23 |

## 2. Current-affairs questions

Classified by one test: could a candidate reason to the answer, or only recall it? `current_affairs = yes` rows carry the
durable context (what the institution, index or instrument is) with the dated fact stated once; option rationales on
arbitrary figures or names say so in one line instead of inventing distinctions; traps appear only where a genuinely
confusable neighbour exists.

| Subject | current_affairs = yes | no | Total |
|---|---|---|---|
| upsc-cse-prelims-gs | 90 | 801 | 891 |
| quantitative-aptitude | 0 | 170 | 170 |
| english-language | 0 | 78 | 78 |
| general-intelligence-reasoning | 0 | 67 | 67 |
| None | 0 | 3 | 3 |
| **Total** | **90** | **1119** | **1209** |

On the 90 current-affairs rows: `common_traps` populated on 63, `explanation_text` on 7.

## 3. Numerical distractor rationales

203 rows carry `solution_steps` (numericals and derivation-type reasoning); they hold 609 wrong-option
rationales. Each numerical distractor was run through a python brute-force over the question's own numbers and
intermediates, plus a fixed slip list (omitted step, intermediate given as answer, wrong percentage base, simple vs
compound, swapped ratio terms, upstream/downstream, per-unit vs total, un-doubled DI average, adjacent series term,
the other person or product).

- **429** rationales name a wrong step or say what the solved arrangement actually gives.
- **180** are distractors no plausible slip reproduces. They do not use a bare 'does not follow' line; each states
  the value the working actually gives, e.g. "No likely slip gives 70; the working gives 64."
- **0** bare generic lines remain.

Most arbitrary distractors sit in quantitative-aptitude approximation, number-series and caselet items, where the
setter spaces wrong options around the key (often 10 or 100 apart) rather than building them from a slip. Looser
"close to the rounding" matches were rejected as coincidences, not steps a candidate would take.

## 4. Tag defects (flagged, not fixed)

`tag_suspect = yes` on 90 rows. No retagging has been done.

| Year/Q | Subject | Current `topic_name` | Question | Suggested topic |
|---|---|---|---|---|
| 2018 Q29 | upsc-cse-prelims-gs | Early nationalism and the moderate phase | In 1920, which of the following changed its name to “Swarajya Sabha”? | Topic should be Home Rule Movement and the start of the Gandhian phase. The Home Rule League (1916) and its 1920 renaming fall after the moderate phase. |
| 2018 Q34 | upsc-cse-prelims-gs | States of matter and material properties | “3D printing” has application in which of the following? 1. Preparation of confectioner... | Topic should be Emerging technologies (3D printing / additive manufacturing). The question tests applications of a technology, not states of matter. |
| 2018 Q57 | upsc-cse-prelims-gs | Demand, supply and market equilibrium | If a commodity is provided free to the public by the Government, then | Topic should be Public finance and opportunity cost. The question tests who bears the cost of free public provision, not demand, supply or equilibrium. |
| 2018 Q88 | upsc-cse-prelims-gs | Population and demography | As per the NSSO 70 th Round “Situation Assessment Survey of Agricultural Households”, c... | Topic should be Agriculture — farm households and rural income. The question tests findings of an agricultural household survey, not population or demography. |
| 2020 Q4 | upsc-cse-prelims-gs | Agricultural marketing, MSP and procurement | With reference to chemical fertilizers in India, consider the following statements: 1. ... | Topic should be Agricultural inputs and fertiliser subsidy. The question tests fertiliser pricing and raw materials, not marketing, MSP or procurement. |
| 2020 Q63 | upsc-cse-prelims-gs | Colonial land revenue systems | Indigo cultivation in India declined by the beginning of the 20th century because of | Topic should be Colonial economy and commercialisation of agriculture. The question is about the fall of indigo as a commercial crop, not land revenue systems. |
| 2020 Q73 | upsc-cse-prelims-gs | Colonial land revenue systems | Which of the following statements correctly explains the impact of Industrial Revolutio... | Topic should be Colonial economy and deindustrialisation. The question tests the effect of British industrial goods on Indian handicrafts, not land revenue. |
| 2020 Q84 | upsc-cse-prelims-gs | Philosophy of the Constitution | One common agreement between Gandhism and Marxism is | Topic should be Political ideologies (Gandhism and Marxism). The question compares two political philosophies, not the philosophy of the Constitution. |
| 2021 Q5 | upsc-cse-prelims-gs | Official languages and the Eighth Schedule | With reference to India, the terms ‘Halbi, Ho and Kui’ pertain to | Topic should be Tribal languages of India. Halbi, Ho and Kui are not Eighth Schedule or official languages. |
| 2021 Q55 | upsc-cse-prelims-gs | Delhi Sultanate — administration and revenue | With reference to medieval India, which one of the following is the correct sequence in... | Topic should be Mughal administration. The suba-sarkar-pargana hierarchy is the Mughal system set up under Akbar, not Delhi Sultanate administration. |
| 2022 Q50 | upsc-cse-prelims-gs | Sustainable agriculture practices | The “Miyawaki method” is well known for the: | Topic should be Afforestation and urban forestry. The method creates dense native forests, not an agricultural practice. |
| 2022 Q61 | upsc-cse-prelims-gs | Foreign investment — FDI and FPI | Consider the following statements: Tight monetary policy of US Federal Reserve could le... | Topic should be External sector — capital flows and external commercial borrowing. The item tests capital flight and ECB currency risk, not FDI or FPI. |
| 2023 Q8 | quantitative-aptitude | Ages — present, past and future | Consider the following statements: 1. A is older than B. 2. C and D are of the same age... | Topic should be Ranking and ordering (comparison of ages). No ages are calculated; the item orders people from comparisons. |
| 2023 Q11 | english-language | Explicit detail retrieval | Which one of the following statements best reflects the most logical and rational impli... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2023 Q14 | quantitative-aptitude | Linear equations in one and two variables | If 7  9  10 = 8, 9  11  30 = 5, 11  17  21 = 13, what is the value of 23  4  15 ? | Topic should be Number patterns and analogies. The item finds a rule linking three numbers; no equation is solved. |
| 2023 Q16 | quantitative-aptitude | Linear equations in one and two variables | If p, q, r and s are distinct single digit positive numbers, then what is the greatest ... | Topic should be Number properties (maximising with digits). No linear equation is involved. |
| 2023 Q20 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | ABCD is a square. One point on each of AB and CD; and two distinct points on each of BC... | Topic should be Permutations, combinations and counting. The item counts triangles; no area or perimeter is found. |
| 2023 Q28 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | 125 identical cubes are arranged in the form of cubical block. How many cubes are surro... | Topic should be Cubes and cuboids (counting unit cubes). The item is about a solid block, not area or perimeter. |
| 2023 Q29 | quantitative-aptitude | LCM, HCF and divisibility | How many distinct 8-digit numbers can be formed by rearranging the digits of the number... | Topic should be Permutations, combinations and counting. The item counts arrangements of digits, not divisibility. |
| 2023 Q31 | english-language | Explicit detail retrieval | Which one of the following statements best reflects the most rational, practical and im... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2023 Q35 | quantitative-aptitude | Number series — arithmetic and difference patterns | In how many ways can a batsman score exactly 25 runs by scoring single runs, fours and ... | Topic should be Permutations, combinations and counting. The item counts combinations of scoring shots, not a number series. |
| 2023 Q42 | english-language | Explicit detail retrieval | Which one of the following statements best reflects the most rational, logical and prac... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2023 Q47 | general-intelligence-reasoning | Category and attribute matching puzzle | Consider the following statements in respect of five candidates P, Q, R, S, and T. Two ... | Topic should be Logical deduction from true and false statements. The question tests truth-value reasoning, not category-attribute matching. |
| 2023 Q49 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | A cuboid of dimensions 7cm × 5cm × 3cm is painted red, green and blue colour on each pa... | Topic should be Cubes and cuboids (painted cube counting). The item counts painted unit cubes, not area or perimeter. |
| 2023 Q55 | quantitative-aptitude | Percentage increase and decrease | In an examination, the maximum marks for each of the four papers namely P, Q, R and S a... | Topic should be Permutations, combinations and counting. The percentage only sets the total; the item counts distributions. |
| 2023 Q58 | quantitative-aptitude | Sets of consecutive and patterned numbers | There are five persons, P, Q, R, S and T each one of whom has to be assigned one task. ... | Topic should be Permutations, combinations and counting. The item counts task assignments under restrictions. |
| 2023 Q62 | english-language | Explicit detail retrieval | Which one of the following statements best reflects the most logical and practical mess... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2023 Q69 | upsc-cse-prelims-gs | Microbes and biological classification | Aerial metagenomics’ best refers to which one of the following situations? | Topic should be Biotechnology applications (environmental DNA). The question tests a DNA-based biodiversity survey method, not microbial classification. |
| 2023 Q73 | english-language | Explicit detail retrieval | Which one of the following statements best reflects the most logical, rational and cruc... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2023 Q74 | quantitative-aptitude | Percentage increase and decrease | A principal P becomes Q in 1 year when compounded half-yearly with R% annual rate of in... | Topic should be Simple and compound interest. The question compares half-yearly and annual compounding, not a percentage change. |
| 2023 Q76 | upsc-cse-prelims-gs | Water pollution and its control | Consider the following statements : Statement-I : According to the United Nations ‘Worl... | Topic should be Water resources and groundwater use. The question is about groundwater extraction volumes, not pollution. |
| 2023 Q77 | quantitative-aptitude | LCM, HCF and divisibility | What is the sum of all 4-digit numbers less than 2000 formed by the digits 1, 2, 3 and ... | Topic should be Permutations, combinations and counting. The question sums numbers formed by arranging digits, not divisibility. |
| 2023 Q80 | quantitative-aptitude | Clocks and calendars | There are three traffic signals. Each signal changes colour from green to red and then ... | Topic should be LCM, HCF and divisibility. The traffic-signal problem is solved by an LCM of cycle times, not by clock or calendar reasoning. |
| 2023 Q94 | upsc-cse-prelims-gs | Territorial and maritime disputes | Consider the fqllowing statements : Statement-I : Israel has established diplomatic rel... | Topic should be West Asia diplomacy (Arab-Israeli relations). The question is about diplomatic recognition and a peace proposal, not a territorial or maritime dispute. |
| 2024 Q5 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | What is the least possible number of cuts required to cut a cube into 64 identical pieces? | Topic should be Cube cutting (solid geometry and counting). The question counts cuts on a cube, not area or perimeter. |
| 2024 Q5 | upsc-cse-prelims-gs | Philosophy of the Constitution | Which one of the following statements is correct as per the Constitution of India? | Topic should be Seventh Schedule and distribution of legislative powers. The question tests which list holds each subject, not constitutional philosophy. |
| 2024 Q6 | quantitative-aptitude | Linear equations in one and two variables | In the expression 5 * 4* 3* 2* 1, * is chosen from +, -, × each at most two times. What... | Topic should be Mathematical operations and operator placement. No equation is solved; the task is choosing operators under a usage limit. |
| 2024 Q10 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | On January 1st, 2023, a person saved Rs 1. On January 2nd, 2023, he saved Rs. 2 more th... | Topic should be Arithmetic progressions and perfect powers. The question sums an odd-number series; there is no area or perimeter. |
| 2024 Q17 | quantitative-aptitude | Linear equations in one and two variables | What is the rightmost digit preceding the zeros in the value of 3030? | Topic should be Unit digits of powers. No linear equation is involved. |
| 2024 Q25 | quantitative-aptitude | Cost price, selling price and margin | Two persons P and Q enter into a business. P puts ₹ 14,000 more than Q, but P has inves... | Topic should be Partnership (profit sharing by capital and time). The question divides profit between partners, not cost and selling price. |
| 2024 Q29 | general-intelligence-reasoning | Family tree puzzle with generations | A father said to his son, “n years back I was as old as you are now. My present age is ... | Topic should be Problems on ages. The question is an age equation, not a family-tree relationship puzzle. |
| 2024 Q30 | quantitative-aptitude | Sets of consecutive and patterned numbers | Consider the following : 1. 1000 litres = 1m3 2. 1 metric ton = 1000 kg 3. 1 hectare = ... | Topic should be Units and measurement conversions. The statements test metric unit equivalences, not number patterns. |
| 2024 Q39 | quantitative-aptitude | Sets of consecutive and patterned numbers | Let p, q, r and s be distinct positive integers. Let p, q be odd and r, s be even. Cons... | Topic should be Odd and even numbers (parity). The statements test the parity of sums and products, not a number pattern. |
| 2024 Q48 | quantitative-aptitude | LCM, HCF and divisibility | If the sum of the two-digit numbers AB and CD is the three-digit number 1CE, where the ... | Topic should be Number puzzles (letter-digit addition). No LCM or HCF is involved. |
| 2024 Q53 | english-language | Explicit detail retrieval | Which one of the following statements best reflect the most logical and rational and pr... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2024 Q75 | quantitative-aptitude | Linear equations in one and two variables | a + b means a – b; a – b means a x b; a x b means a ÷ b; a ÷ b; means a + b, then what ... | Topic should be Mathematical operations (symbol substitution). The task is replacing operators and applying order of operations, not solving an equation. |
| 2025 Q1 | upsc-cse-prelims-gs | Insurance and risk products | With reference to investments, consider the following : I. Bonds II. Hedge Funds III. S... | Topic should be Capital market instruments and alternative investment funds. The question is about SEBI's AIF categories, not insurance. |
| 2025 Q4 | upsc-cse-prelims-gs | Insurance and risk products | Consider the following statements : I. The Reserve Bank of India mandates all the liste... | Topic should be Corporate governance and ESG disclosure. The question is about SEBI's sustainability reporting, not insurance. |
| 2025 Q7 | quantitative-aptitude | Averages — simple and weighted | P and Q walk along a circular track. They start at 5:00 a.m. from the same point in opp... | Topic should be Speed, time and distance (circular track). The question is about relative speed on a track, not averages. |
| 2025 Q8 | general-intelligence-reasoning | Letter shifting and alphabet position | If P = +, Q = –, R = ×, S = ÷, then insert the proper notations between the successive ... | Topic should be Mathematical operations and symbol substitution. It replaces letters with arithmetic signs; no letter shifting is involved. |
| 2025 Q9 | quantitative-aptitude | Averages — simple and weighted | A tram overtakes 2 persons X and Y walking at an average speed of 3 km/hr and 4 km/hr i... | Topic should be Speed, time and distance (relative speed). The tram problem uses relative speed, not averages. |
| 2025 Q10 | quantitative-aptitude | LCM, HCF and divisibility | If N^2 = 12345678987654321, then how many digits does the number N have? | Topic should be Squares and square roots. The question asks the digit count of a square root, not LCM, HCF or divisibility. |
| 2025 Q13 | upsc-cse-prelims-gs | Early trade and urban centres | The irrigation device called 'Araghatta' was | Topic should be Agriculture and irrigation technology in early medieval India. The araghatta is an irrigation device, not a trade or urban topic. |
| 2025 Q17 | upsc-cse-prelims-gs | Early trade and urban centres | With reference to ancient India (600–322 BC), consider the following pairs : Territoria... | Topic should be Mahajanapadas and their geography. The question tests the rivers of the sixteen mahajanapadas, not trade or towns. |
| 2025 Q19 | quantitative-aptitude | LCM, HCF and divisibility | Let PQR be a 3-digit number, PPT be a 3-digit number and PS be a 2-digit number, where ... | Topic should be Number puzzles (letter-digit subtraction). No LCM or HCF is involved. |
| 2025 Q20 | quantitative-aptitude | Number series — arithmetic and difference patterns | Consider the sequence AB_CC_A_BCCC_BBC_C that follows a certain pattern. Which one of t... | Topic should be Letter series and pattern completion. The item repeats a letter block, not a number series. |
| 2025 Q23 | english-language | Explicit detail retrieval | Which one of the following statements best reflects the critical message conveyed by th... | Topic should be Inference and implied meaning. The item asks for the passage's overall message or implication, not an explicitly stated detail. |
| 2025 Q25 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | A solid cube is painted yellow on all its faces. The cube is then cut into 60 smaller b... | Topic should be Cube cutting and painted-cube counting. The item tests cuts and painted faces, not area or perimeter. |
| 2025 Q35 | upsc-cse-prelims-gs | Global summits, declarations and compacts | Which one of the following launched the 'Nature Solutions Finance Hub for Asia and the ... | Topic should be International financial institutions. The question asks which multilateral development bank launched a finance facility. |
| 2025 Q40 | upsc-cse-prelims-gs | Energy flow and ecological pyramids | With reference to the planet Earth, consider the following statements : I. Rain forests... | Topic should be Marine ecosystems and oxygen production. The question is about sources of Earth's oxygen, not energy flow or ecological pyramids. |
| 2025 Q53 | english-language | Explicit detail retrieval | Which one of the following statements reflects the best explanation of the above passage? | Topic should be Inference and implied meaning. The answer is not stated in the one-sentence passage and must be inferred from the word 'buffer'. |
| 2025 Q56 | general-intelligence-reasoning | Letter shifting and alphabet position | In a certain code if 64 is written as 343 and 216 is written as 729, then how is 512 wr... | Topic should be Number coding (cube pattern). It codes numbers, not letters. |
| 2025 Q68 | quantitative-aptitude | LCM, HCF and divisibility | The 5-digit number PQRST (all distinct digits) is such that T is not equal to 0. P is t... | Topic should be Digit puzzles and counting. The item counts numbers meeting digit conditions; no LCM, HCF or divisibility is involved. |
| 2025 Q75 | quantitative-aptitude | Percentage increase and decrease | A set (X) of 20 pipes can fill 70% of a tank in 14 minutes. Another set (Y) of 10 pipes... | Topic should be Pipes and cisterns. The item is a filling-and-emptying rate problem, not a percentage change. |
| 2025 Q79 | general-intelligence-reasoning | Category and attribute matching puzzle | A mobile phone has been stolen. There are 3 suspects P, Q and R. They were questioned k... | Topic should be Truth-teller and liar logic puzzle. The item tests whether suspects' statements can be consistent, not matching categories to attributes. |
| 2025 Q80 | quantitative-aptitude | Cost price, selling price and margin | Three teams P, Q, R participated in a tournament in which the teams play with one anoth... | Topic should be Logical puzzles (tournament and points tables). The item has nothing to do with cost price or selling price. |
| 2026 Q2 | upsc-cse-prelims-gs | Colonial land revenue systems | The artificially fixed rupee-sterling exchange rate prescribed by the Hilton-Young Comm... | Topic should be Colonial economic policy and the drain of wealth. The question is about currency and exchange-rate policy, not land revenue. |
| 2026 Q4 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | A cut on a solid object divides the object into two parts where the new surfaces thus p... | Topic should be Cube cutting and spatial reasoning. The item counts pieces made by plane cuts, not area or perimeter. |
| 2026 Q14 | upsc-cse-prelims-gs | Buddhist and Jain rock-cut architecture | Which of the following statements on the Amaravati Stupa and its relief sculpture is/ar... | Topic should be Stupa architecture and sculpture (Amaravati school). The Amaravati stupa is a structural stupa, not rock-cut architecture. |
| 2026 Q14 | quantitative-aptitude | Permutations, combinations and counting | Two identical straight rods are painted in five distinct colours so that each of them g... | Topic should be Arrangement puzzles. The item asks which placements are possible under clues, not for a count of arrangements. |
| 2026 Q16 | upsc-cse-prelims-gs | Revolutionary movements and armed struggle | Which of the following factors contributed to the formation of the Forward Bloc by Subh... | Topic should be Congress politics and the Left, 1935-1939. The Forward Bloc's formation arose from the Tripuri crisis within Congress, not from armed revolutionary movements. |
| 2026 Q29 | upsc-cse-prelims-gs | Services sector and e-commerce | Which of the following is/are the most significant implication(s) of obtaining Oeko-Tex... | Topic should be Textiles and handloom industry. The question is about certification of a silk for export markets, not services or e-commerce. |
| 2026 Q30 | general-intelligence-reasoning | Path tracing and final position | X travels 6 km on a bicycle with average speeds of 5 km per hour, 10 km per hour and 4 ... | Topic should be Speed, time and distance. The item computes journey times from speeds over stretches; no path or direction is traced. |
| 2026 Q31 | quantitative-aptitude | Area and perimeter — rectangle, square, triangle | Seven cubes are identical in shape. Out of these, the weight of each of the six cubes i... | Topic should be Logical puzzles (balance and weighing). The item has no area or perimeter content. |
| 2026 Q38 | upsc-cse-prelims-gs | Marine ecosystems and coral reefs | At the United Nations Ocean Conference (UNOC) held in June, 2025 in France, the Food an... | Topic should be International organisations (FAO) and fisheries. The question tests FAO's strategic framework, not marine ecosystems or coral reefs. |
| 2026 Q45 | quantitative-aptitude | Percentage increase and decrease | An alloy P contains 20% copper and 80% zinc by weight. Another alloy Q contains 60% cop... | Topic should be Mixtures and alligation. The item mixes two alloys to a target strength. |
| 2026 Q51 | None | None | Mr. X, a senior officer, was overseeing a critical vaccination programme during a pande... | Topic should be Ethics, integrity and aptitude (case study). The item tests an officer's ethical conduct in an administrative dilemma; subject and topic are null in the input. |
| 2026 Q52 | None | None | In a multi-ethnic district where both economic competition and historical grievances fr... | Topic should be Ethics, integrity and aptitude (case study). The item tests an officer's ethical conduct in an administrative dilemma; subject and topic are null in the input. |
| 2026 Q53 | None | None | Ms. X is a mid-level civil service official working in the urban development department... | Topic should be Ethics, integrity and aptitude (case study). The item tests an officer's ethical conduct in an administrative dilemma; subject and topic are null in the input. |
| 2026 Q56 | upsc-cse-prelims-gs | Fundamental Rights | Which of the following statements with regard to the persons with disabilities in India... | Topic should be Welfare of vulnerable sections (persons with disabilities). The question tests a statute, a scheme and a corporation, not Part III rights. |
| 2026 Q58 | quantitative-aptitude | Cost price, selling price and margin | Three partners A, B and C entered into a business. A invested one-third of the capital ... | Topic should be Partnership. Profit is shared by capital and time, not a cost-price or margin calculation. |
| 2026 Q59 | quantitative-aptitude | Percentage increase and decrease | There are two chemicals which do not react with each other. A container contains 10 lit... | Topic should be Mixtures and replacement. The item is a repeated-replacement problem, not a percentage change. |
| 2026 Q60 | quantitative-aptitude | Cost price, selling price and margin | A shopkeeper employs a delivery boy and gives him a motorcycle for home delivery. For e... | Topic should be Linear inequalities (earnings conditions). There is no cost price, selling price or margin in the item. |
| 2026 Q69 | quantitative-aptitude | Sets of consecutive and patterned numbers | How many words can one form by shuffling the letters of the word QUEUE, if Q is always ... | Topic should be Permutations of letters with repetition. The question counts arrangements of the letters of a word. |
| 2026 Q73 | quantitative-aptitude | LCM, HCF and divisibility | A toy T jumps forward or backward. In each forward jump, it moves 5' forward whereas in... | Topic should be Linear equations in two variables. The jump counts come from two simultaneous equations, not from LCM, HCF or divisibility. |
| 2026 Q75 | quantitative-aptitude | Number series — arithmetic and difference patterns | The top of a table is rectangular and its dimensions are 6' × 10'. Two rectangular port... | Topic should be Counting and arrangements (geometric placement). It counts placements of rectangles on a table top; no number series is involved. |
| 2026 Q77 | upsc-cse-prelims-gs | Natural vegetation | Which of the following statements in relation to NIRANTAR (National Institute for Resea... | Topic should be Environmental institutions and governance. NIRANTAR is a research and capacity platform of MoEFCC, not a natural vegetation topic. |
| 2026 Q78 | quantitative-aptitude | Number series — arithmetic and difference patterns | A pattern formed by two characters a and b is repeated more than once in the following ... | Topic should be Letter series and repeating patterns. The string is a letter pattern, not a number series. |
| 2026 Q97 | upsc-cse-prelims-gs | Insurance and risk products | Which of the following statements about Crowdfunding is/are correct ? 1. Crowdfunding i... | Topic should be Capital markets and alternative finance (crowdfunding). The question tests a fund-raising method, not insurance or risk products. |
| 2026 Q98 | upsc-cse-prelims-gs | Insurance and risk products | With reference to different Committees in India, consider the following details : Sl No... | Topic should be Financial sector reforms and committees. The rows span insurance, SEBI and RBI committees, not insurance products. |

## 5. Low-confidence rows

- **2021 Q43 · upsc-cse-prelims-gs · `ad5ecdbc-a889-4e95-be01-9b61cf3cdeec`** — with reference to the Indus river system, of the following four rivers, three of them pour into one of them which joins the Indus direct. Among the following...
  - Keyed: (d) Sutlej
  - Reason: Accepted as defensible. Another reading set aside: option a (Chenab), since many maps treat the Chenab as the trunk stream that receives the Sutlej to form the Panjnad; the key treats the Panjnad as the continuation of the Sutlej.
- **2023 Q1 · general-intelligence-reasoning · `9914d3fe-4c7c-4faf-b7ce-6542cd5462e9`** — Based on the above passage, the following assumptions have been made: 1. Collection, processing and segregation of municipal waste should be with government ...
  - Keyed: (d) Neither 1 nor 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2023 Q3 · general-intelligence-reasoning · `38721bc7-a427-4b73-8a75-e2a2ecf3ec48`** — Based on the above passage, the following assumptions have been made: 1. Organic farming is inherently unsafe for both farmers and consumers. 2. Farmers and ...
  - Keyed: (b) 2 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2023 Q5 · general-intelligence-reasoning · `758ad0cd-4a83-40b3-87b8-0f7e95b3d073`** — Based on the above passage, the following assumptions have been made: 1. To implement the Sustainable Development Goals and to achieve zero-hunger goal, mono...
  - Keyed: (b) 2 and 3 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2023 Q14 · upsc-cse-prelims-gs · `e8b1b72c-4af0-4676-a4ca-0f1b39d97eef`** — Consider the following ‘fauna : Lion-tailed Macaque Malabar Civet Sambar Deer How many of the above are generally nocturnal or most active after sunset?
  - Keyed: (a) Only one
  - Reason: Accepted as defensible. Another reading set aside: option b, because the sambar is often described as largely nocturnal or crepuscular; the official key counts only the Malabar civet.
- **2023 Q22 · general-intelligence-reasoning · `5713b301-9e4f-45e3-9dfc-b674659093c4`** — Which one of the following statements best implies the most rational assumption that can be made from the passage?
  - Keyed: (a) We are likely to spend more money on cure than prevention.
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2023 Q38 · upsc-cse-prelims-gs · `1890f66a-e656-4335-9caf-b69f0f572aed`** — Consider the following statements : Once the Central Government notifies an area as a ‘Community Reserve’ the Chief Wildlife Warden of the State becomes the ...
  - Keyed: (b) Only two
  - Reason: Accepted as defensible. Reading of statements 3 and 4 is uncertain: some treat traditional agriculture as permitted and NTFP collection as restricted; the count of two is the same either way, so the key holds.
- **2023 Q53 · general-intelligence-reasoning · `e0b861dc-05ba-4ede-b741-c0f760cda681`** — Based on the above passage, the following assumptions have been made: 1. Patent protection given to patentees puts a huge burden on public's purchasing power...
  - Keyed: (b) 1 and 4
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2023 Q54 · general-intelligence-reasoning · `bbfd95be-d4d1-41d2-a2ef-25cdea10d256`** — Based on the above passage, the following assumptions have been made: 1. Protection of privacy is not just a right, but it has value to the economy. 2. There...
  - Keyed: (c) Both 1 and 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2023 Q71 · general-intelligence-reasoning · `54315efe-47a6-4d33-bd10-742db1873af5`** — With reference to the above passage, the following assumptions have been made: 1. Global warming is causing spring to come early and for longer durations. 2....
  - Keyed: (a) 1 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q2 · general-intelligence-reasoning · `3539fbdd-6d76-4f49-8c93-4f03f73b4edc`** — Based on the above passage, the following assumptions have been made : 1.The food distribution mechanism needs to be reimagined and made effective to reduce ...
  - Keyed: (a) 1 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q4 · general-intelligence-reasoning · `82d0955f-843e-4df2-ba94-8303096c89be`** — Based on the above passage, the following assumptions have been made : 1. Fiscal policies of governments are solely responsible for higher prices. 2. Higher ...
  - Keyed: (d) Neither 1 nor 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q12 · general-intelligence-reasoning · `302100d5-a1dc-4f70-9f27-351f76b92e9c`** — Based on the above passage, the following assumptions have been made : India needs a new generation of urban professionals with knowledge relevant to modern ...
  - Keyed: (a) 1 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The two assumptions are printed without numbers; they are read in order as 1 and 2.
- **2024 Q14 · general-intelligence-reasoning · `39d3782b-3479-4097-b074-bf49ca0ae601`** — Based on the above passage, the following assumptions have been made : 1. Internet is not inclusive enough. 2. Internet can adversely affect the quality of p...
  - Keyed: (c) Both 1 and 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q21 · general-intelligence-reasoning · `97c86058-851f-4e92-9ab5-a740724d6c98`** — Based on the above passage, the following assumptions have been made : For effective school education, parents have greater role than the governments. School...
  - Keyed: (d) Neither 1 nor 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The two assumptions are printed without numbers; they are read in order as 1 and 2.
- **2024 Q28 · upsc-cse-prelims-gs · `23c8b66b-d7ae-4c25-8fcc-5c5cee9c12d0`** — Consider the following statements: Statement-I : Sumed pipeline is a strategic route for Persian Gulf oil and natural gas shipments to Europe. Statement-II :...
  - Keyed: (d) Statement-I is incorrect, but Statement-II is correct
  - Reason: Accepted as defensible on a strict reading of Statement-I. Another reading set aside: option a, which treats Statement-I as broadly true because SUMED is a strategic bypass for Persian Gulf crude to Europe and Statement-II explains it; energy-agency descriptions apply the 'oil and natural gas' phrase to the Suez Canal and SUMED jointly. Confidence low because the more common reading favours a.
- **2024 Q32 · general-intelligence-reasoning · `223bac19-05a5-4d01-ad50-4baaf8c3d363`** — Based on the above passage, the following assumptions have been made: 1. The horrors of modern life are the inevitable result of the progress of science. 2. ...
  - Keyed: (b) 2 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q34 · general-intelligence-reasoning · `3fede841-e44b-4467-945e-d010939e0e51`** — With reference to the above passage, the following assumptions have been made : 1. Travel leads to an understanding of humans. 2. Travel helps those who wish...
  - Keyed: (a) 1 and 2 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q42 · general-intelligence-reasoning · `50d27b8e-da2c-438d-8f8f-afc821e05db4`** — Based on the above passage, the following assumptions have been made : As a large number of workers in our country are employed in unorganized sector, India ...
  - Keyed: (d) Neither 1 nor 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The two assumptions are printed without numbers; they are read in order as 1 and 2.
- **2024 Q43 · general-intelligence-reasoning · `05112a99-97f9-4ac6-8cfe-c0679059d2b1`** — Based on the above passage, the following assumptions have been made : The adolescent does not feel comfortable with his parents because they tend to be domi...
  - Keyed: (a) 1 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The two assumptions are printed without numbers; they are read in order as 1 and 2.
- **2024 Q52 · general-intelligence-reasoning · `7a273537-8a48-4ab1-9b70-811299f3f838`** — Based on the above passage, the following assumptions have been made : 1. Giant icebergs have a bearing on primary productivity and food chains of the Southe...
  - Keyed: (a) 1 only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2024 Q72 · general-intelligence-reasoning · `f595b163-eead-4799-84ef-a50ed5cbd975`** — Based on the above passage, the following assumptions have been made : 1. The author of the passage believes that flowers are creations of Nature's luxury. 2...
  - Keyed: (d) Neither 1 nor 2
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.
- **2025 Q4 · general-intelligence-reasoning · `70207b87-6621-5341-82e2-01b0f629c952`** — With reference to the above passage, the following assumptions have been made: I. The food manufacturing and processing industries in every country should al...
  - Keyed: (B) II only
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The canonical 2025 CSAT import (migration 228) also records this passage as absent from its source document.
- **2025 Q12 · general-intelligence-reasoning · `72bd302c-e9bb-5a1c-a8da-2646fc8bd2d8`** — With reference to the passage, the following assumptions have been made: The growing divergence between the fortunes of the agricultural and non-agricultural...
  - Keyed: (D) Neither I nor II
  - Reason: The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The canonical 2025 CSAT import (migration 228) also records this passage as absent from its source document.
- **2025 Q71 · upsc-cse-prelims-gs · `25f5926c-ab44-4f76-b9e1-c40433c094b9`** — "Sedition has become my religion" was the famous statement given by Gandhiji at the time of
  - Keyed: (D) the launch of the Quit India Movement
  - Reason: Accepted on the official key. The quotation's exact occasion is not settled in standard texts; some sources connect similar remarks with the Salt Satyagraha of 1930 (option b), which is set aside in favour of the key.
- **2025 Q81 · upsc-cse-prelims-gs · `0d94006a-a018-4543-afa5-f972d8b002f1`** — Consider the following statements : Statement I : Some rare earth elements are used in the manufacture of flat television screens and computer monitors. Stat...
  - Keyed: (C) Statement I is correct but Statement II is not correct
  - Reason: Accepted on the official key with doubt. On a loose reading Statement II is true, because rare-earth-doped materials such as europium-doped strontium aluminate are phosphorescent, and that would give option a. The key is defended on the strict reading that the elements themselves are not phosphorescent and that screens use fluorescence.
- **2026 Q6 · english-language · `a4da5ae3-f39f-486d-9758-f6ada9dc8316`** — Which of the following conclusions is/are valid? Though SARS-CoV-2 and HMPV are similar viruses with somewhat different epidemiology, the former became a pan...
  - Keyed: (b) 2 only
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q7 · english-language · `3ad9ae44-e316-4074-804e-06e31a9d437a`** — Which of the following reflect the intent of the writer in the above passage? To evolve methodologies for objective analysis of the two viruses To establish ...
  - Keyed: (d) None of the above
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted. Intent 2 is the closest call; the key treats the comparison as a device rather than the writer's aim.
- **2026 Q8 · english-language · `1d84fb75-3ba0-4408-923c-186f9335c199`** — Which of the following statements reflect the logical and rational inferences that can be drawn from the passage? HMPV has, historically, had longer document...
  - Keyed: (b) 1, 2 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q12 · english-language · `747bc0b0-6ec1-4431-b469-d41846aac229`** — Which of the following statements is/are not correct? Tech-savvy farmers will drive the AgTech companies of the future. The development of advisory services ...
  - Keyed: (a) 1 and 3 only
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q26 · english-language · `a9265c56-df8e-4d31-9c64-013465e93703`** — Which of the following inferences is/are correct? The source of the energy we consume is the key to the battle for cleaner air. Bans are effective where the ...
  - Keyed: (c) 1 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q27 · english-language · `c2248ba9-6c53-46ce-a002-cd1fc7a85de9`** — Which of the following statements is/are correct? Thermal power stations in Delhi were required to summarily shut down. CNG supplies had to be assured once d...
  - Keyed: (c) 2 only
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q34 · english-language · `bf36a8ec-41c8-4735-ae94-72e188954f86`** — Which of the following conclusions is/are correct? All landlords essentially have some goodness trapped within them. The common grazing grounds of a village ...
  - Keyed: (c) 3 only
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q35 · english-language · `814d6f8c-b891-4d0c-b383-550f9b0cb6e6`** — Which of the following statements are not correct? The landholdings of Rai Sahib were currently not being used for farming. Temperamentally, Rai Sahib was as...
  - Keyed: (d) 1, 2 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted. The reading is consistent with the set's other key (question 34), where concern for tenants is the one valid conclusion.
- **2026 Q41 · english-language · `f1301ee1-dbf5-4b3c-8c2c-2aeffb267917`** — Which of the following statements is/are correct? Radical action can also be attributed to mild surrender where one acts against societal expectations. Submi...
  - Keyed: (c) 1, 2 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q43 · english-language · `bd63cc64-768d-456e-95f9-67395dd9d432`** — Which of the following conclusions are correct? In the breakaway phase, economic progress is slow for the technology followers. In the catch-up phase, leader...
  - Keyed: (a) 3 and 4 only
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted. Conclusion 4 is awkwardly worded but gives the sequence scavenging, hunting, farming, industry, which the key accepts.
- **2026 Q44 · english-language · `a83580c8-f18a-45b1-8907-57879499227c`** — Which of the following statements is/are correct? The convergence model divides nations into three phases of economic progress. At the heart of the convergen...
  - Keyed: (c) 3 only
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q66 · english-language · `f270b72b-3a85-4d48-b23f-21b751ec704f`** — Which of the following conclusions are valid? Seven Sanskriti Angans, representing different regions of India, had been showcased in Kalagram. Regional artis...
  - Keyed: (d) 1 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted. Question 67 of the same set accepts that the thematic zones were inspired by well-known temples.
- **2026 Q67 · english-language · `18e0b00c-dd79-43ce-909e-a9ef210b4c70`** — Which one of the following statements is not correct?
  - Keyed: (a) Paintings from four States of India have been mentioned.
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted. The count of States cannot be checked without the passage.
- **2026 Q71 · english-language · `df00332f-3776-4b8e-92d7-c5903e014b85`** — Which of the following conclusions are valid? Sport is more than just games; it is a way of life. Sport can help mitigate the problems of seclusion among the...
  - Keyed: (d) 1, 2 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q72 · english-language · `1848f249-db1f-45f0-b426-ae278ce4c8cd`** — Which of the following statements is/are correct? Parents are not encouraging enough when it comes to children playing sport. Participation in sporting activ...
  - Keyed: (b) 2 and 3
  - Reason: The passage itself was not supplied with this row (question_text holds only the stem and statements) and could not be located in the repository, so no passage words are quoted; the explanation follows the statement wording, the other keyed questions of the same set and the official key, which is accepted.
- **2026 Q77 · upsc-cse-prelims-gs · `13049005-8013-4772-88f6-ce2e0d18eef6`** — Which of the following statements in relation to NIRANTAR (National Institute for Research and Application of Natural Resources to Transform, Adapt and Build...
  - Keyed: (B) 1 and 3 only
  - Reason: Accepted as the official key; the lead institutes of NIRANTAR's verticals could not be independently corroborated.
- **2026 Q78 · upsc-cse-prelims-gs · `c4b37d8d-7ad2-4dee-9cdf-2a31f26bc44c`** — The Chancellor of the Federal Republic of | Germany visited India in January, 2026. Which of the following is/are not correct in terms of outcomes of this vi...
  - Keyed: (B) 1 and 4
  - Reason: Dated list of visit outcomes that could not be fully corroborated item by item; key accepted and confidence lowered.

| Confidence | Count |
|---|---|
| high | 944 |
| medium | 222 |
| low | 43 |

Medium rows are not listed; where a specific reservation exists it is in that row's `key_note`.

## 6. Field-population counts

| Field | Rows populated | Of 1209 |
|---|---|---|
| `short_explanation` | 1209 | 100% |
| `explanation_text` | 197 | 16% |
| `solution_steps` | 203 | 17% |
| `formula_used` | 128 | 11% |
| `common_traps` | 961 | 79% |
| `key_note` | 300 | 25% |
| `final_answer_option_id` | 1161 | 96% |
| `option_rationales` (entries, not rows) | 3627 | — |

2 rationale entries are the fixed filler line ("Filler option; a correct answer is present.").

### Per-chunk depth counts

The rows were drafted in 20 chunks by parallel agents from one spec. Depth per chunk, so drift is visible:

| Chunk | Rows | Statement-type | explanation_text | common_traps | solution_steps | Non-AGREE | Low conf |
|---|---|---|---|---|---|---|---|
| u01 | 62 | 34 | 6 | 53 | 0 | 0 | 0 |
| u02 | 62 | 38 | 11 | 56 | 0 | 0 | 0 |
| u03 | 62 | 34 | 2 | 39 | 0 | 0 | 0 |
| u04 | 62 | 45 | 10 | 59 | 0 | 6 | 0 |
| u05 | 62 | 33 | 8 | 46 | 0 | 12 | 0 |
| u06 | 62 | 37 | 6 | 47 | 0 | 1 | 1 |
| u07 | 62 | 46 | 20 | 44 | 0 | 0 | 0 |
| u08 | 62 | 46 | 12 | 52 | 0 | 3 | 0 |
| u09 | 62 | 43 | 9 | 53 | 0 | 1 | 2 |
| u10 | 62 | 48 | 13 | 42 | 1 | 1 | 0 |
| u11 | 62 | 48 | 8 | 51 | 0 | 19 | 1 |
| u12 | 62 | 45 | 17 | 46 | 0 | 2 | 0 |
| u13 | 62 | 46 | 14 | 48 | 2 | 2 | 2 |
| u14 | 62 | 38 | 13 | 49 | 0 | 0 | 1 |
| u15 | 62 | 25 | 12 | 40 | 36 | 1 | 1 |
| u16 | 62 | 5 | 1 | 57 | 61 | 0 | 0 |
| u17 | 62 | 6 | 11 | 61 | 62 | 0 | 0 |
| u18 | 62 | 22 | 14 | 57 | 30 | 0 | 20 |
| u19 | 62 | 48 | 5 | 30 | 11 | 0 | 0 |
| u20 | 31 | 18 | 5 | 31 | 0 | 0 | 15 |

## 7. Validation

Enforced by the build script; the worksheet is written only when every check passes.

- **Row count:** 1209 rows, one per input question.
- **Uniqueness:** 1209 distinct `question_id` values.
- **Completeness:** the worksheet and input `question_id` sets are identical; `year`, `question_number`, `subject_slug`,
  `topic_name` are copied unchanged.
- **Option-rationale integrity:** 3627 entries, each keyed to an `option_id` and `label` on that question, no
  duplicates. Wrong options across the corpus: 3627. Every wrong option on an AGREE row is covered; the only gaps
  are options this draft argues are correct or defensible (the proposed option on a DISPUTED row).
- **No contradiction on AGREE rows:** no AGREE row carries a rationale against its own keyed option.
- **final_answer_option_id:** set on all 1161 AGREE rows and equal to the input `correct_option_id`; null on every
  non-AGREE row.
- **Verdict integrity:** every DISPUTED row names a `proposed_correct_option_id` on that question and different from the key;
  no other row carries one. Every non-AGREE row and every low-confidence row carries a `key_note`.
- **Tag integrity:** `tag_suspect = yes` ⇔ non-empty `tag_note`. No `topic_name` modified.
- **Provenance:** every row `platform_original` / `owned` / `pending`.
- **AGREE rows arguing for another option:** 0. No AGREE row has a rationale against its key, a proposed option, or a null final id.
- **solution_steps:** non-empty on 203 rows, all numericals or worked puzzles (quantitative-aptitude 169, general-intelligence-reasoning 31, upsc-cse-prelims-gs 3). Every other row has `[]`.
- **Verdicts:** AGREE 1161, DISPUTED 48, UNANSWERABLE 0. **Confidence:** high 944, medium 222, low 43.

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
| `key_verdict` | `ambiguity_status` | AGREE → `none`, DISPUTED → `disputed`, UNANSWERABLE → `source_conflict` |
| `key_note`, `current_affairs`, `tag_suspect`, `tag_note`, `draft_confidence` | `metadata` | no dedicated columns |
| `explanation_source_type` / `license_status` / `reviewer_status` | same | `platform_original` / `owned` / `pending` (route forces `pending`) |

Constraints the apply step must respect:

- `unique (question_id, explanation_source_type)`: the create route returns 422 on a second `platform_original` row, so a
  re-run must PATCH existing `pending` rows, not re-POST.
- The review RPC and `pyq_question_explanations_guard` refuse `verified` while `ambiguity_status ≠ none` or
  `final_answer_option_id` is null — the 48 non-AGREE rows cannot be verified until the key is resolved.
- Editing learner-facing fields on a verified row downgrades it to `needs_correction`; the apply step should touch only
  `pending` rows.

## 9. Scope

UPSC CSE Prelims only — the 1209 questions in `upsc-explanations-input.json`. No Mains descriptive question was drafted. No database writes, no migrations, no retagging, no change to
any question or option.

## 10. Ready-to-read sample (20 rows)

Chosen with `rng = random.Random(20260923)`: `rng.sample(statement_type_rows, 8)` then `rng.sample(other_rows, 12)`, both over
the worksheet rows in file order, where statement-type means statement-based, matching-pairs or assertion-reason as classified
above. The 20 are then sorted by year, subject and question number for reading. Re-running the same calls on the same file yields
the same 20.

---

### S1. 2018 Q33 · upsc-cse-prelims-gs · Climate treaties, institutions and initiatives

`03d621bb-1dfa-4df1-9bef-efbb0d1d89f7` · verdict AGREE · confidence high · current affairs yes · shape other

**Question.** The partnership for action on green economy (PAGE) a UN mechanism to assist countries transition towards greener and more inclusive economics emerged at

- (a) The Earth summit on sustainable Development 2002, Johannesburg
- (b) The United Nation conference on sustainable Development 2012, Rio de Janeiro **← keyed**
- (c) The United Nations Framework Convention on Climate Change 2015, Paris
- (d) The World sustainable Development Summit 2016, New Delhi

**Short explanation.** PAGE was launched in 2013 in response to the call in 'The Future We Want', the outcome document of the UN Conference on Sustainable Development (Rio+20) held in Rio de Janeiro in 2012, to support countries moving to green economies.

**Why the other options are wrong**

- (a) The 2002 Johannesburg summit predates the green-economy agenda that produced PAGE.
- (c) PAGE existed before the 2015 Paris climate conference.
- (d) The 2016 World Sustainable Development Summit in New Delhi is a TERI forum; PAGE predates it.

**Common traps**

- 'Green economy' was the headline theme of Rio+20; linking it to the better-known Paris 2015 meeting is the common slip.

---

### S2. 2018 Q46 · upsc-cse-prelims-gs · Emerging technologies

`58837182-5380-48f1-9e2f-c35dd307d1d7` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** When the alarm of your smartphone rings in the morning, you wake up and tap it to stop the alarm which causes your geyser to be switched on automatically. The smart mirror in your bathroom shows the day’s weather and also indicates the level of water in your overhead tank. After you take some groceries from your refrigerator for making breakfast, it recognises the shortage of stock in it and places an order for the supply of fresh grocery items. When you step out of your house and lock the door, all lights fans, geysers and AC machines get switched off automatically. On your way to office, your cars warns you about traffic congestion ahead and suggest an alternative route, and if you are late for a meeting, its send a message to your office accordingly. In the context of emerging communication technologies, which one of the following terms best applies to the above scenario?

- (a) Border Gateway Protocol
- (b) Internet of things **← keyed**
- (c) Internet protocol
- (d) Virtual private network

**Short explanation.** Everyday devices (alarm, geyser, mirror, fridge, lights, car) sensing data and talking to each other over the internet to act on their own is exactly the Internet of Things.

**Why the other options are wrong**

- (a) Border Gateway Protocol routes traffic between networks on the internet backbone; it is not about smart devices.
- (c) Internet Protocol is the basic addressing rule for all internet traffic, not the idea of connected household things.
- (d) A VPN is a secure tunnel over a public network, not device automation.

---

### S3. 2018 Q63 · upsc-cse-prelims-gs · Emergency provisions

`10cc984f-f2d5-4bcb-9779-dd7ef741909c` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** If the President of India exercises his power as provided under article 356 of the Constitution in respect State, then

- (a) the Assembly of the India state is automatically dissolved.
- (b) the powers of the Legislature of that State shall be exercisable by or under the authority of the Parliament **← keyed**
- (c) Article 19 is suspended in that State
- (d) the president can make laws relating to that State.

**Short explanation.** Under Article 356(1)(b), when President's Rule is imposed the President may declare that the powers of the State Legislature shall be exercisable by or under the authority of Parliament.

**Explanation.** Article 356 lets the President assume the executive functions of the State and transfer the State Legislature's powers to Parliament. Article 357 then allows Parliament to confer law-making power on the President, or on an authority he names. The Assembly may be dissolved or kept in suspended animation; after S. R. Bommai (1994) dissolution should normally wait until Parliament has approved the proclamation.

**Why the other options are wrong**

- (a) The Assembly is not automatically dissolved; it may be kept in suspended animation, and dissolution is a separate decision.
- (c) Article 19 is suspended only under a national emergency on grounds of war or external aggression (Article 358), not under Article 356.
- (d) The President can make laws for the State only if Parliament delegates that power under Article 357; it does not flow directly from the proclamation, so option b is the accurate description.

**Common traps**

- Assuming President's Rule automatically dissolves the Assembly.
- Mixing up Article 356 with Article 358, which suspends Article 19 during an external emergency.

**Key note.** Accepted as defensible. Another reading set aside: option d is conditionally true because Parliament may delegate law-making for the State to the President under Article 357, but that is a delegated power, whereas option b is the direct effect of the proclamation.

---

### S4. 2020 Q78 · upsc-cse-prelims-gs · Colonial education and social reform

`9423c52f-5b55-48a6-a07a-ec866f7d35e3` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** The Vital-Vidhvansak, the first monthly journal to have the untouchable people as its target audience was published by

- (a) Gopal Baba Walangkar **← keyed**
- (b) Jyotiba Phule
- (c) Mohandas Karamchand Gandhi
- (d) Bhimrao Ramji Ambedkar

**Short explanation.** Gopal Baba Walangkar, an early Mahar reformer and ex-soldier, published Vital-Vidhvansak (Destroyer of Brahmanical Pollution) in 1888, the first journal aimed at untouchable readers.

**Why the other options are wrong**

- (b) Jyotiba Phule founded the Satyashodhak Samaj; he did not publish Vital-Vidhvansak.
- (c) Gandhi published Harijan from 1933, much later.
- (d) Ambedkar's papers were Mooknayak (1920) and Bahishkrit Bharat (1927), later than 1888.

**Common traps**

- Picking Ambedkar as the best-known leader of the depressed classes; Walangkar's journal came decades earlier.

---

### S5. 2021 Q58 · upsc-cse-prelims-gs · Regional kingdoms and the Marathas

`278681d1-c8ed-4567-821c-55fe91b7ccaa` · verdict AGREE · confidence medium · current affairs no · shape statement-based

**Question.** With reference to Indian history, which of the following statements is/are correct? The Nizamat of Arcot emerged out of Hyderabad State. The Mysore Kingdom emerged out of Vijaynagara Empire. Rohilkhand Kingdom was formed out of the territories occupied by Ahmad Shah Durrani. Select the correct answer using the codes given below.

- (a) 1 and 2
- (b) 2 Only **← keyed**
- (c) 2 and 3
- (d) 3 Only

**Short explanation.** Statement 1 is incorrect: the Nawabs of Arcot (Carnatic) were appointed under the Mughals in the 1690s, before Hyderabad became a separate State in 1724, so Arcot did not emerge out of Hyderabad State. Statement 2 is correct: the Wodeyars of Mysore were feudatories of Vijayanagara who became independent after its decline. Statement 3 is incorrect: Rohilkhand was carved out by Ali Muhammad Khan Rohilla from Mughal territory, not from lands held by Ahmad Shah Durrani. So 2 only.

**Why the other options are wrong**

- (a) Includes statement 1, which is incorrect.
- (c) Includes statement 3, which is incorrect.
- (d) Statement 3 is incorrect, and statement 2 is correct.

**Common traps**

- Arcot was nominally under the Nizam in the 18th century, which tempts candidates to say it emerged from Hyderabad; its nawabship predates Hyderabad State.

---

### S6. 2022 Q14 · upsc-cse-prelims-gs · Prime Minister and Council of Ministers

`78244c98-2ebe-49bc-a9f4-6e43bf1307d8` · verdict AGREE · confidence high · current affairs no · shape statement-based

**Question.** Consider the following statements: The Constitution of India classifies the ministers into four ranks viz. Cabinet Minister, Minister of State with Independent Charge, Minister of State and Deputy Minister. The total number of ministers in the Union Government, including the Prime Minister, shall not exceed 15 percent of the total number of members in the Lok Sabha. Which of the statements given above is/are correct?

- (a) 1 only
- (b) 2 only **← keyed**
- (c) Both 1 and 2
- (d) Neither 1 nor 2

**Short explanation.** Statement 1 is incorrect: the Constitution does not rank ministers; the three-tier system of Cabinet Ministers, Ministers of State and Deputy Ministers comes from convention and practice. Statement 2 is correct: Article 75(1A), inserted by the 91st Amendment, 2003, caps the total number of ministers including the Prime Minister at 15 percent of the Lok Sabha's total strength. So 2 only.

**Why the other options are wrong**

- (a) Marks statement 1; ministerial ranks are not classified in the Constitution.
- (c) Includes statement 1, which is incorrect.
- (d) Omits statement 2; the 15 percent cap is in Article 75(1A).

**Common traps**

- Assuming a familiar practice must have a constitutional basis; ministerial ranks are conventional.

---

### S7. 2022 Q15 · upsc-cse-prelims-gs · Parliament: composition and procedure

`826c6b41-fdd3-4680-862e-1c4485a07ff0` · verdict AGREE · confidence high · current affairs no · shape statement-based

**Question.** Which of the following is/are the exclusive power(s) of Lok Sabha? To ratify the declaration of Emergency To pass a motion of no-confidence against the Council of Ministers To impeach the President of India Select the correct answer using the code given below:

- (a) 1 and 2
- (b) 2 only **← keyed**
- (c) 1 and 3
- (d) 3 only

**Short explanation.** Item 1 is incorrect: a proclamation of emergency must be approved by both Houses of Parliament. Item 2 is correct: only the Lok Sabha can pass a no-confidence motion, because the Council of Ministers is collectively responsible to it under Article 75(3). Item 3 is incorrect: the President is impeached by both Houses under Article 61. So 2 only.

**Why the other options are wrong**

- (a) Includes item 1; emergency approval needs both Houses.
- (c) Includes items 1 and 3, both of which involve both Houses.
- (d) Marks only impeachment, which is shared by both Houses.

**Common traps**

- Treating the Lok Sabha's special role in approving revocation of an emergency as an exclusive power to ratify it.

---

### S8. 2022 Q79 · upsc-cse-prelims-gs · Agricultural marketing, MSP and procurement

`2b8052d5-bc25-4cd4-8969-c2c5459df7a1` · verdict AGREE · confidence high · current affairs no · shape statement-based

**Question.** With reference to the “Tea Board” in India, consider the following statements: The Tea Board is a statutory body. It is a regulatory body attached to the Ministry of Agriculture and Farmers Welfare. The Tea Board’s Head Office is situated in Bengaluru. The Board has overseas offices at Dubai and Moscow. Which of the statements given above are correct?

- (a) 1 and 3
- (b) 2 and 4
- (c) 3 and 4
- (d) 1 and 4 **← keyed**

**Short explanation.** Statement 1 is correct: the Tea Board is a statutory body set up under the Tea Act, 1953. Statement 2 is incorrect: it functions under the Ministry of Commerce and Industry, not the Ministry of Agriculture. Statement 3 is incorrect: its head office is in Kolkata. Statement 4 is correct: it has overseas offices in Dubai and Moscow to promote Indian tea. So 1 and 4.

**Why the other options are wrong**

- (a) Includes statement 3, which is incorrect, and omits statement 4, which is also correct.
- (b) Includes statement 2, which is incorrect, and omits statement 1, which is also correct.
- (c) Includes statement 3, which is incorrect, and omits statement 1, which is also correct.

**Common traps**

- Tea is a crop, so candidates assume the Agriculture Ministry; plantation commodity boards (tea, coffee, rubber, spices) sit under the Commerce Ministry.
- Bengaluru is the head office of the Coffee Board, not the Tea Board.

---

### S9. 2023 Q32 · english-language · Inference and implied meaning

`4606591d-a95a-43e7-8474-f180360460a9` · verdict AGREE · confidence medium · current affairs no · shape statement-based

**Question.** Which one the following statements best reflects what is implied by the passage?

- (a) Education system must be strengthened in rural areas.
- (b) Large scale and effective implementation of skill development programme is the need of the hour.
- (c) For economic development, health and nutrition of only skilled workers needs special attention.
- (d) For rapid economic growth as envisaged by us, attention should be paid to health and nutrition of the people. **← keyed**

**Short explanation.** The passage ties the growth we envisage to the productivity of people, which rests on their health and nutrition; the implication is that health and nutrition of the population need attention.

**Why the other options are wrong**

- (a) Rural education is not the passage's focus.
- (b) Skill development is narrower; the passage makes health and nutrition the foundation.
- (c) 'Only skilled workers' narrows a point the passage makes about people in general.

**Common traps**

- Absolute words such as 'only', 'all', 'cannot' or 'completely' usually push an option beyond what the passage supports.

**Key note.** The passage text is not included in this input row, so the explanation paraphrases the argument the keyed option summarises and does not quote the passage.

---

### S10. 2023 Q54 · general-intelligence-reasoning · Statement and assumption

`bbfd95be-d4d1-41d2-a2ef-25cdea10d256` · verdict AGREE · confidence low · current affairs no · shape statement-based

**Question.** Based on the above passage, the following assumptions have been made: 1. Protection of privacy is not just a right, but it has value to the economy. 2. There is a fundamental link between privacy and innovation. Which of the above assumptions is/are valid?

- (a) 1 only
- (b) 2 only
- (c) Both 1 and 2 **← keyed**
- (d) Neither 1 nor 2

**Short explanation.** Assumption 1 is valid: the argument treats privacy as having economic value, not only as a right. Assumption 2 is valid: the argument links privacy protection with innovation. So both are valid.

**Why the other options are wrong**

- (a) Omits assumption 2, which is also valid.
- (b) Omits assumption 1, which is also valid.
- (d) Assumption 1 is valid, so 'neither' is wrong.

**Common traps**

- Picking an assumption because it sounds like sensible advice or a true fact; an assumption must be something the author's argument actually relies on.

**Key note.** The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing.

---

### S11. 2023 Q78 · upsc-cse-prelims-gs · Refugee and humanitarian crises

`298b6c95-6d78-406d-8561-236c114cfc64` · verdict AGREE · confidence high · current affairs yes · shape other

**Question.** Which one of the following countries has been suffering from decades of civil strife and food shortages and was in news in the recent past for its very severe famine?

- (a) Angola
- (b) Costa Rica
- (c) Ecuador
- (d) Somalia **← keyed**

**Short explanation.** Somalia has endured civil conflict since 1991 and repeated droughts; in 2022 it faced warnings of famine after successive failed rainy seasons.

**Why the other options are wrong**

- (a) Angola's civil war ended in 2002; it was not the famine in the news.
- (b) Costa Rica is a stable democracy with no famine.
- (c) Ecuador has faced crime and political turmoil, not famine.

---

### S12. 2024 Q43 · general-intelligence-reasoning · Statement and assumption

`05112a99-97f9-4ac6-8cfe-c0679059d2b1` · verdict AGREE · confidence low · current affairs no · shape other

**Question.** Based on the above passage, the following assumptions have been made : The adolescent does not feel comfortable with his parents because they tend to be dominating and assertive. The adolescent of modern times does not have much respect for parents. Which of the assumptions given above is/are valid?

- (a) 1 only **← keyed**
- (b) 2 only
- (c) Both 1 and 2
- (d) Neither 1 nor 2

**Short explanation.** Assumption 1 is valid: the argument rests on parents' dominating, assertive manner making the adolescent uncomfortable. Assumption 2 is not valid: a general lack of respect for parents among modern adolescents is a sweeping judgement the argument does not need. So 1 only.

**Why the other options are wrong**

- (b) Includes assumption 2, which is not valid.
- (c) Includes assumption 2, which is not valid.
- (d) Assumption 1 is valid, so 'neither' is wrong.

**Common traps**

- Turning discomfort with parents into lack of respect for them.

**Key note.** The passage is not embedded in this row's question_text, so its words could not be quoted; the adjudication follows UPSC's published key and the assumptions' own wording. Check the explanation against the passage before publishing. The two assumptions are printed without numbers; they are read in order as 1 and 2.

---

### S13. 2024 Q10 · quantitative-aptitude · Area and perimeter — rectangle, square, triangle

`004f4422-206c-4db1-a2fb-8133b2d0c309` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** On January 1st, 2023, a person saved Rs 1. On January 2nd, 2023, he saved Rs. 2 more than that on the previous day. On January 3rd, 2023, he saved Rs. 2 more than that on the previous day and so on. At the end of which date was his total savings a perfect square as well a perfect cube?

- (a) 7th January, 2023
- (b) 8th January, 2023 **← keyed**
- (c) 9th January, 2023
- (d) Not possible

**Short explanation.** The savings are 1, 3, 5, 7, ..., and the first n odd numbers add up to n². n² is also a cube only when n is itself a cube, so n = 8: at the end of 8th January the total is 64 = 8 × 8 = 4 × 4 × 4.

**Why the other options are wrong**

- (a) After 7 days the total is 49, a square but not a cube.
- (c) After 9 days the total is 81, a square but not a cube.
- (d) It is possible: the total is 64 at the end of 8th January.

**Solution steps**

1. Daily savings: 1, 3, 5, ... rupees (odd numbers).
2. Total after n days = n².
3. n² is a perfect cube exactly when n is a perfect cube: n = 1, 8, 27, ...
4. n = 8 gives 64 = 8² = 4³, at the end of 8th January.

**Formula.** 1 + 3 + 5 + ... + (2n − 1) = n²

**Common traps**

- Reading 'Rs. 2 more than the previous day' as saving Rs. 2 every day.

**Key note.** The total at the end of 1st January (Rs 1) is trivially both a square and a cube, but that date is not offered; 8th January is the first non-trivial case and is the key.

**Tag note.** Topic should be Arithmetic progressions and perfect powers. The question sums an odd-number series; there is no area or perimeter.

---

### S14. 2024 Q5 · upsc-cse-prelims-gs · Philosophy of the Constitution

`5ac5cead-d026-4622-b41d-4b95d4903459` · verdict AGREE · confidence high · current affairs no · shape statement-based

**Question.** Which one of the following statements is correct as per the Constitution of India?

- (a) Inter-State trade and commerce is a State subject under the State List.
- (b) Inter-State migration is a State subject under the State List.
- (c) Inter-State quarantine is a Union subject under the Union List. **← keyed**
- (d) Corporation tax is a State subject under the State List.

**Short explanation.** Entry 81 of the Union List covers inter-State migration and inter-State quarantine, so inter-State quarantine is a Union subject.

**Why the other options are wrong**

- (a) Inter-State trade and commerce is in the Union List (Entry 42); only trade within a State is a State subject.
- (b) Inter-State migration is in the Union List (Entry 81).
- (d) Corporation tax is in the Union List (Entry 85).

**Common traps**

- Confusing intra-State matters (State List) with inter-State ones (Union List).

**Tag note.** Topic should be Seventh Schedule and distribution of legislative powers. The question tests which list holds each subject, not constitutional philosophy.

---

### S15. 2024 Q9 · upsc-cse-prelims-gs · International boundaries and border disputes

`5d2ce052-06c0-40e5-bb91-95235e936027` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** The longest border between any two countries in the world is between:

- (a) Canada and the United States of America **← keyed**
- (b) Chile and Argentina
- (c) China and India
- (d) Kazakhstan and Russian Federation

**Short explanation.** The Canada-United States border, about 8,900 km including the Alaska section, is the longest international border in the world.

**Why the other options are wrong**

- (b) The Chile-Argentina border is long but shorter than the Canada-US one.
- (c) The India-China border is about 3,500 km.
- (d) The Kazakhstan-Russia border, about 7,600 km, is the second longest, not the longest.

**Common traps**

- Picking Kazakhstan-Russia, which is the longest continuous land border but second overall.

---

### S16. 2024 Q81 · upsc-cse-prelims-gs · Population and demography

`c5260b80-4bc1-40a1-addd-82fe43001844` · verdict DISPUTED · confidence high · current affairs no · shape other

**Question.** The total fertility rate in an economy is defined as:

- (a) the number of children born per 1000 people in the population in a year.
- (b) the number of children born to a couple in their lifetime in a given population.
- (c) the birth rate minus death rate. **← keyed**
- (d) the average number of live births a woman would have by the end of her child-bearing age. **← proposed**

**Short explanation.** Total fertility rate is the average number of children a woman would bear over her reproductive years if she experienced the current age-specific fertility rates. A TFR of about 2.1 is replacement level.

**Why the other options are wrong**

- (a) Children born per 1,000 people in a year is the crude birth rate.
- (b) TFR is measured per woman, not per couple.
- (c) Birth rate minus death rate is the rate of natural increase, not fertility.

**Common traps**

- Confusing TFR with crude birth rate, which uses the whole population as its base.

**Key note.** The input key (c) gives the rate of natural increase (birth rate minus death rate), which is not the total fertility rate. Option d states the standard definition and is proposed.

---

### S17. 2024 Q84 · upsc-cse-prelims-gs · Mutual funds, ETFs and investment trusts

`ca228e0b-2318-47ab-a4c0-65c64733dba5` · verdict AGREE · confidence high · current affairs no · shape statement-based

**Question.** Consider the following: Exchange-Traded Funds (ETF) Motor vehicls Currency swap Which of the above is/are considered financial instruments?

- (a) 1 only
- (b) 2 and 3 only
- (c) 1, 2 and 3
- (d) 1 and 3 only **← keyed**

**Short explanation.** An exchange-traded fund is a financial instrument: a tradable claim on a pool of assets. A motor vehicle is not: it is a physical asset. A currency swap is a financial instrument: a derivative contract to exchange payments in two currencies. So 1 and 3.

**Why the other options are wrong**

- (a) Omits the currency swap, which is a financial instrument.
- (b) Includes motor vehicles, a physical asset, and omits ETFs.
- (c) Includes motor vehicles, which are not a financial instrument.

**Common traps**

- A vehicle loan is a financial instrument; the vehicle itself is not.

---

### S18. 2025 Q2 · general-intelligence-reasoning · Statement and assumption

`59e8ec00-7ab1-5146-bf7a-f769f784f17c` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** With reference to the above passage, the following assumptions have been made: I. Higher education is a constantly evolving subject that needs to align towards new developments in all spheres of society. II. In our country, sufficient funds are not allocated for promoting higher education. Which of the above assumptions is/are valid?

- (A) I only **← keyed**
- (B) II only
- (C) Both I and II
- (D) Neither I nor II

**Short explanation.** Assumption I is valid: the passage says 'the new demands of society and the future of work require critical and independent thinking' and that 'teaching has to be re-invented', so it rests on higher education having to keep pace with change. Assumption II is not valid: the passage says nothing about funding. So I only.

**Why the other options are wrong**

- (B) Includes assumption II, which is not valid.
- (C) Includes assumption II, which is not valid.
- (D) Assumption I is valid, so 'neither' is wrong.

**Common traps**

- Choosing II because under-funding of universities is a familiar complaint; the passage is about how teaching should change, not about money.

---

### S19. 2026 Q5 · upsc-cse-prelims-gs · Jainism

`771876fe-d031-4b18-a8d6-b13aaf696c4b` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** Among the four main forms of existence of life recognized in Jainism, which one of the following is not included ?

- (A) Deva (gods)
- (B) Yaksha (demi-gods) **← keyed**
- (C) Manushya (humans)
- (D) Tiryancha (animals and plants)

**Short explanation.** Jainism recognises four gatis, or forms of existence, into which a soul can be reborn: deva (gods), manushya (humans), tiryancha (animals and plants) and naraki (hell-beings). Yaksha, a demi-god, is not one of the four; yakshas fall within the deva class.

**Why the other options are wrong**

- (A) Deva is one of the four gatis.
- (C) Manushya is one of the four gatis.
- (D) Tiryancha is one of the four gatis.

**Common traps**

- Forgetting naraki (hell-beings) as the fourth form, which makes yaksha look plausible.

---

### S20. 2026 Q26 · upsc-cse-prelims-gs · International boundaries and border disputes

`0d76e28b-cbf4-45c6-9381-1935fd83580d` · verdict AGREE · confidence high · current affairs no · shape other

**Question.** Which of the following with reference to Indian States is/are not correct ? 1. Uttar Pradesh shares its boundary with the highest number of other Indian States. 2. Rajasthan shares the longest international border among all Indian States. 3.Sikkim is the only State that shares its boundary with just one other Indian State. Select the answer using the code given below:

- (A) 1 only
- (B) 1 and 2
- (C) 2 and 3 **← keyed**
- (D) 3 only

**Short explanation.** The question asks which are NOT correct. Statement 1 is correct: Uttar Pradesh borders eight states, more than any other. Statement 2 is not correct: West Bengal has the longest international border (mainly with Bangladesh), longer than Rajasthan's border with Pakistan. Statement 3 is not correct: Sikkim borders only West Bengal, but Meghalaya also borders only Assam, so Sikkim is not the only one. So 2 and 3.

**Why the other options are wrong**

- (A) Statement 1 is correct; the question asks for incorrect statements.
- (B) Includes statement 1, which is correct, and omits statement 3.
- (D) Omits statement 2, which is also incorrect.

**Common traps**

- Assuming Rajasthan has the longest international border because of its long border with Pakistan.
- The word 'only' in statement 3: Meghalaya also touches just one state.
