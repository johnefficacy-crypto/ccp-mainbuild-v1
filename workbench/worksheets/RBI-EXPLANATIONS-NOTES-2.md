# RBI Grade B top-up — Explanation Draft: Review Notes (EXPL-05)

Worksheet: `workbench/worksheets/RBI-EXPLANATIONS-DRAFT-2.json` — 364 rows, one per RBI Grade B General Awareness or Phase II MCQ
in `workbench/sources/rbi-explanations-input-2.json`. Every row is authored from subject knowledge and the question's own
text. Set-based questions (puzzles, passages, data tables) carry their shared premise inside `question_text`. No text is
extracted from any third-party source. Nothing here is reviewed.

**Batch.** Top-up to the first RBI batch (`RBI-EXPLANATIONS-DRAFT.json`, 531 rows, EXPL-03). These are the General Awareness and
Phase II questions that were not yet question-level verified when that batch was exported. No question_id overlaps it. By subject: general-knowledge 145, finance 101, economic-social-issues 86, economics 22, management 8, insurance 1, pension-sector 1.

Conventions are those settled by the first batch: keys accepted where defensible (reading set aside named in `key_note`), one worked
arrangement for any puzzle, plain aspirant-friendly language on every row, current-affairs rows carrying durable context with the dated
fact stated once, named-slip rationales on numerical distractors, and the same provenance values. This batch uses three verdicts only:
AGREE, DISPUTED, UNANSWERABLE.

- AGREE rows whose key_note begins "Accepted as defensible": 16; AGREE rows with any key_note reservation: 129.

**Field set.** The requested fields in the requested order, followed by `current_affairs` and the three provenance fields
(`explanation_source_type = platform_original`, `license_status = owned`, `reviewer_status = pending`), so the rows read as the same
corpus as the first batch.

## 1. Key verdicts

| Verdict | Count | `final_answer_option_id` |
|---|---|---|
| AGREE | 354 | set = input `correct_option_id` |
| DISPUTED | 9 | null — awaits a human key decision |
| UNANSWERABLE | 1 | null — awaits a human key decision |
| **Total** | **364** | **354 set** |

### 1.1 DISPUTED — the keyed answer is not defensible on any reading

#### 2025 Q20 · economic-social-issues · `c2d50ff5-5bee-48ca-956d-dde74e95656e`

**Stem.** The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government initiative launched to revolutionize Indian agriculture by making it more productive, sustainable, and financially rewarding for farmers. Announced on February 1, 2025, during the Union Budget 2025-26 by Finance Minister Nirmala Sitharaman and approved by the Union Cabinet on July 16, 2025, PMDDKY targets 100 underperforming districts where farming faces challenges like low crop yields, water scarcity, and limited access to resources. With an annual budget of __________ for six years (2025-26 to 2030-31), totaling ___________, the scheme aims to support 1.7 crore farmers, particularly small and marginal farmers owning less than 2 hectares of land, who constitute 86% of India’s farming population (Economic Survey 2024-25). With reference to the MSME sector as per the Economic Survey 2024-25, consider the following statements: 1. MSMEs contribute approximately 30% to India's Gross Domestic Product (GDP). 2. The sector's share in India's total exports has crossed the 60% mark. 3. Formalization of the sector is being primarily driven by registrations on the Udyam Portal. Which of the statements given above are correct?

- **Keyed option:** (e) 3 only Direction (Q15 – Q18) - Read the passage given below and answer the following questions The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government initiative launched to revolutionize Indian agriculture by making it more productive, sustainable, and financially rewarding for farmers. Announced on February 1, 2025, during the Union Budget 2025-26 by Finance Minister Nirmala Sitharaman and approved by the Union Cabinet on July 16, 2025, PMDDKY targets 100 underperforming districts where farming faces challenges like low crop yields, water scarcity, and limited access to resources. With an annual budget of __________ for six years (2025-26 to 2030-31), totaling ___________, the scheme aims to support 1.7 crore farmers, particularly small and marginal farmers owning less than 2 hectares of land, who constitute 86% of India’s farming population (Economic Survey 2024-25). (This is a recreated passage and not the exact one asked in the exam)
- **Proposed option:** (b) 1 and 3 only
- **Reason.** Key 3 only is not defensible: official figures place the MSME share of GDP at about 30% (30.1% for 2022-23), so statement 1 is true. With statement 2 false (exports about 45%), the answer is 1 and 3 only (option b). A 'GVA, not GDP' reading was considered and set aside, because the official series itself reports MSME GVA as a share of all-India GDP. Option e's text also carries the next set's direction text.

#### 2025 Q20 · management · `94dc7bd6-3e10-4bec-abe6-de1401dbc5ba`

**Stem.** A growing manufacturing company initially relied heavily on precise work-measurement techniques to improve efficiency. Managers conducted detailed time studies, motion studies, and work standardisation exercises to break tasks into smaller units and ensure maximum productivity from each worker. Over time, as the organisation expanded, coordination became difficult, so it adopted a strict hierarchy-based structure with clear authority lines to maintain control. Later, realising that employee involvement improves motivation and decision-making, the company moved toward a participative style where workers’ opinions were actively included in planning and problem-solving. Eventually, as the business environment became more dynamic, the company embraced a systems-based approach, recognising that all departments are interrelated and that organisational success depends on the smooth functioning of the entire system. Which of the following is a key feature of the Systems Theory of management?

- **Keyed option:** (b) Emphasis on unity of command and scalar chain
- **Proposed option:** (c) Interaction with the external environment (open system)
- **Reason.** The key (b) cannot be defended: unity of command and scalar chain are Fayol's principles, which the passage links to the hierarchy stage. Systems Theory's defining feature is that the organisation is an open system interacting with its environment, which is option c. Option e carries stray text from the next question set's directions and passage (an extraction defect); it is read as its first words only.

#### 2025 Q28 · economic-social-issues · `9d75a38c-082c-4ca7-9f6a-80aaa958d7f2`

**Stem.** Covering about one-third of the Earth’s land surface, forests are crucial for food security, livelihoods and for renewable biomaterials and energy. They are habitats for a large proportion of the world’s biodiversity, help regulate global carbon and hydrologic cycles, and can reduce the risks and impacts of drought, desertification, soil erosion, landslides and floods. Yet they also face many challenges and demands, and balancing priorities in forest management requires reliable, timely data. As a knowledge-based organization, the Food and Agriculture Organization of the United Nations (FAO) is mandated to “collect, analyse, interpret and disseminate information relating to nutrition, food and agriculture.” In this regard, FAO has conducted Global Forest Resources Assessments (FRAs) in 2025. FRAs build on data collected and reported by countries. A truly collaborative approach, combined with consolidated data collection, analysis and validation, ensures that the best and most recent knowledge is shared and applied through a standardized set of definitions and methodology. To reduce the reporting burden on countries, to increase synergies among reporting processes, and to improve data consistency, the process also involves collaboration among many partner organizations. With reference to global forest extent as per Global Forest Resources Assessment 2025, consider the following statements: 1. Forests cover approximately 32% of the total global land area. 2. More than half of the world's forests are concentrated in just five countries. 3. The tropical domain accounts for the largest proportion of the world's forests. Which of the statements given above are correct?

- **Keyed option:** (a) 1 and 3 only
- **Proposed option:** (e) 1, 2 and 3 Direction (Q23 – Q26) - Read the passage given below and answer the following questions The launch of Pradhan Mantri Awas Yojana – Urban 2.0 (PMAY-U 2.0) has created a significant need to generate public awareness about the scheme and encourage participation of eligible beneficiaries to avail its benefits. With this aim, the Ministry of Housing and Urban Affairs has launched “____A____”, a last-mile outreach campaign, from 4th September 2025 till 31st December 2025. It aims to boost the implementation of PMAY-U 2.0 by creating widespread awareness about the scheme, along with fast-tracking the verification of applications under the scheme and facilitating the completion of already sanctioned houses under PMAY-U. The campaign also seeks to inform stakeholders about the Credit Risk Guarantee Fund Trust for Low Income Housing (CRGFTLIH) scheme. It will promote last-mile delivery through active community mobilisation, targeted engagement and convergence of schemes of Government of India. Additionally, it aims to enable PMAY-U beneficiaries get benefits of the PM Surya Ghar: Muft Bijli Yojana and prioritises the housing needs of beneficiaries from Special Focus Groups identified under PMAY-U 2.0. (This is a recreated passage and not the exact one asked in the exam)
- **Reason.** Key 1 and 3 only is not defensible: FRA reports have consistently stated that more than half of the world's forest is in five countries, so statement 2 is also true and the answer is 1, 2 and 3 (option e). No reading rescues the key: Russia, Brazil, Canada, the United States and China together hold about 2.2 of the roughly 4.1 billion hectares, which is more than half.

#### 2025 Q29 · economic-social-issues · `37ccaebb-d329-47c0-a0bc-fb668361997b`

**Stem.** The launch of Pradhan Mantri Awas Yojana – Urban 2.0 (PMAY-U 2.0) has created a significant need to generate public awareness about the scheme and encourage participation of eligible beneficiaries to avail its benefits. With this aim, the Ministry of Housing and Urban Affairs has launched “____A____”, a last-mile outreach campaign, from 4th September 2025 till 31st December 2025. It aims to boost the implementation of PMAY-U 2.0 by creating widespread awareness about the scheme, along with fast-tracking the verification of applications under the scheme and facilitating the completion of already sanctioned houses under PMAY-U. The campaign also seeks to inform stakeholders about the Credit Risk Guarantee Fund Trust for Low Income Housing (CRGFTLIH) scheme. It will promote last-mile delivery through active community mobilisation, targeted engagement and convergence of schemes of Government of India. Additionally, it aims to enable PMAY-U beneficiaries get benefits of the PM Surya Ghar: Muft Bijli Yojana and prioritises the housing needs of beneficiaries from Special Focus Groups identified under PMAY-U 2.0. Which of the following will come in place of ______A______?

- **Keyed option:** (d) Abhigyan 2025
- **Proposed option:** (e) Angikaar 2025
- **Reason.** Keyed 'Abhigyan 2025' does not match the campaign; MoHUA ran 'Angikaar 2025' from 4 September to 31 December 2025 as a revival of its 2019 Angikaar outreach, so option e is proposed. The dates in the passage match Angikaar 2025 exactly, and no MoHUA campaign called Abhigyan is known, so this is not a case of an unverifiable dated fact.

#### 2025 Q32 · economic-social-issues · `bacb4a40-163e-434a-9613-295668c1e968`

**Stem.** The launch of Pradhan Mantri Awas Yojana – Urban 2.0 (PMAY-U 2.0) has created a significant need to generate public awareness about the scheme and encourage participation of eligible beneficiaries to avail its benefits. With this aim, the Ministry of Housing and Urban Affairs has launched “____A____”, a last-mile outreach campaign, from 4th September 2025 till 31st December 2025. It aims to boost the implementation of PMAY-U 2.0 by creating widespread awareness about the scheme, along with fast-tracking the verification of applications under the scheme and facilitating the completion of already sanctioned houses under PMAY-U. The campaign also seeks to inform stakeholders about the Credit Risk Guarantee Fund Trust for Low Income Housing (CRGFTLIH) scheme. It will promote last-mile delivery through active community mobilisation, targeted engagement and convergence of schemes of Government of India. Additionally, it aims to enable PMAY-U beneficiaries get benefits of the PM Surya Ghar: Muft Bijli Yojana and prioritises the housing needs of beneficiaries from Special Focus Groups identified under PMAY-U 2.0. Consider the following statements regarding 'Special Focus Groups' (SFGs) in PMAY-U 2.0: 1. SFGs include Safai Karamcharis, street vendors, and residents of slums. 2. Single women and widows are not specifically prioritized to avoid gender bias. 3. Senior citizens are eligible for specific housing approvals in states like Uttar Pradesh. Which of the statements given above are correct?

- **Keyed option:** (d) 2 and 3 only
- **Proposed option:** (a) 1 and 3 only
- **Reason.** Key 2 and 3 only is not defensible: the PMAY-U 2.0 guidelines expressly list widows and single women as Special Focus Groups, so statement 2 is false, and statement 1 is true. No reading rescues the key, since it needs statement 2 true and statement 1 false, and both run against the guidelines. Option a (1 and 3) is proposed; if statement 3 is judged false, option c (1 only) would be the answer instead.

#### 2025 Q36 · economic-social-issues · `edd46f08-d848-4ea4-8906-2d867fd5a5e0`

**Stem.** The SEBI circular, issued on May 29, 2025, presents a comprehensive framework aimed at improving transparency, risk monitoring, and trading practices in the equity derivatives market. With increasing retail participation and the popularity of short-tenure index options, SEBI has introduced a structured set of measures in consultation with expert working groups and stakeholders to ensure orderly market conduct. One of the most significant changes is the recalibration of the Market Wide Position Limit (MWPL). With reference to the SEBI measures for the Equity Derivatives segment, consider the following statements: 1. The pre-open session for derivatives was introduced primarily to ensure better price discovery and minimize volatility at the market open. 2. Under the new guidelines, the Market-Wide Position Limit (MWPL) for a stock is calculated based on its total market capitalization only. 3. Intraday monitoring of MWPL is conducted at four random intervals during the trading session to prevent sudden speculative surges. Which of the statements given above is/are correct?

- **Keyed option:** (d) 1, 2, and 3
- **Proposed option:** (c) 1 and 3 only
- **Reason.** Key 1, 2 and 3 is not defensible: statement 2 says MWPL uses total market capitalisation only, while the circular (and the stem's own set, where MWPL is the lower of 15% of free float and 65 times delivery value) shows otherwise. No reading rescues the key: 'total market capitalisation only' cannot describe a limit built on free float and delivery value, which is also the 2025 change the question set itself describes. Option c (1 and 3) is proposed.

#### 2026 Q10 · general-knowledge · `4a0e3cc6-8e0b-42ea-a182-4b0a4761a47f`

**Stem.** With reference to the selection process of the Padma Awards, consider the following statements: 1. It is one of the highest civilian awards of India. 2. The selection committee is headed by President of India. 3. A person can self nominate himself/herself for the award.

- **Keyed option:** (e) 1, 2 and 3
- **Proposed option:** (c) 1 and 3 only
- **Reason.** The keyed answer (all three statements) cannot stand: the Padma Awards Committee is headed by the Cabinet Secretary, not the President of India, so statement 2 is false. Statement 1 is true (Padma Vibhushan, Padma Bhushan and Padma Shri rank just after the Bharat Ratna) and statement 3 is true (the online nomination portal accepts self-nominations). The correct choice is option c, 1 and 3 only.

#### 2026 Q21 · general-knowledge · `687061dd-0502-4743-90c1-808b215ebbbe`

**Stem.** Which ancient Indian text is primarily related to economics, polity, administration and statecraft?

- **Keyed option:** (c) Natya Shastra
- **Proposed option:** (b) Arthashastra
- **Reason.** The key (Natya Shastra) is plainly wrong: it is a treatise on the performing arts. The text on economics, polity, administration and statecraft is Kautilya's Arthashastra, option b.

#### 2026 Q43 · general-knowledge · `977fc7d2-9209-41a9-b086-aa58f10c4ae9`

**Stem.** With reference to the Aravalli Range, consider the following statements: 1. The Luni River originates from the Aravalli Range. 2. Guru Shikhar is the highest peak of the Aravalli Range. 3. Sambhar Lake is a wetland located in the Aravalli Range. Which of the statements given above is/are correct?

- **Keyed option:** (e) 1 only
- **Proposed option:** (a) 1 and 2 only
- **Reason.** The key '1 only' cannot stand, because statement 2 (Guru Shikhar is the highest Aravalli peak) is a standard, correct fact. Statement 1 is also correct. Statement 3 is borderline: Sambhar Lake is a Ramsar wetland in the Aravalli region but lies in a basin east of the range; if it is read as 'in the Aravalli Range', option d (all three) would be the answer instead. Option a, 1 and 2 only, is proposed as the strongest reading.

### 1.2 UNANSWERABLE — cannot be answered as written

#### 2023 Q39 · finance · `ee1c526a-1da6-4de1-9686-7a8e5e37adde`

**Stem.** Net Owned Funds (NOF) is a term commonly used in the context of financial institutions, particularly non-banking financial companies (NBFCs) in India. It refers to the difference between the total assets and the outside liabilities of an institution. In simple terms, NOF represents the net worth or capital of the financial institution, including the shareholders’ equity and accumulated reserves. It indicates the financial strength and stability of the institution and is an important parameter for regulatory compliance and risk assessment. The Reserve Bank of India (RBI) had fixed the minimum Net Owned Fund (NOF) size for housing finance companies to ___?

- **Keyed option:** (a) 25 Crores
- **Reason.** RBI's October 2020 revised framework for HFCs (carried into the 2021 Master Direction) fixed the minimum NOF at ₹20 crore, reached via ₹15 crore by March 2022. No option gives ₹20 crore, and the keyed ₹25 crore matches no RBI requirement for HFCs. Option e (₹25 lakh) was only the original NHB Act floor and is not what RBI fixed, so it cannot be proposed either.

### 1.3 Source data notes

- **Repeated question numbers.** 12 (subject, year, question_number) combinations occur more than once in the input, because
  question sets were numbered per section. Match rows by `question_id`, never by number.
- **Spill-over text.** In several rows the last option carries the next set's directions or passage stuck to its end; the
  affected rows say so in `key_note`. No key depends on the spilled text.

## 2. Current-affairs questions

Classified by one test: could a candidate reason to the answer, or only recall it? `current_affairs = yes` rows carry the
durable context (what the institution, index or instrument is) with the dated fact stated once; option rationales on
arbitrary figures or names say so in one line instead of inventing distinctions; traps appear only where a genuinely
confusable neighbour exists.

| Subject | current_affairs = yes | no | Total |
|---|---|---|---|
| general-knowledge | 85 | 60 | 145 |
| finance | 56 | 45 | 101 |
| economic-social-issues | 78 | 8 | 86 |
| economics | 7 | 15 | 22 |
| management | 0 | 8 | 8 |
| insurance | 1 | 0 | 1 |
| pension-sector | 0 | 1 | 1 |
| **Total** | **227** | **137** | **364** |

On the 227 current-affairs rows: `common_traps` populated on 113, `explanation_text` on 0.

## 3. Numerical distractor rationales

4 rows carry `solution_steps` (numericals and derivation-type reasoning); they hold 16 wrong-option
rationales. Each numerical distractor was run through a python brute-force over the question's own numbers and
intermediates, plus a fixed slip list (omitted step, intermediate given as answer, wrong percentage base, simple vs
compound, swapped ratio terms, upstream/downstream, per-unit vs total, un-doubled DI average, adjacent series term,
the other person or product).

- **9** rationales name a wrong step or say what the solved arrangement actually gives.
- **7** are distractors no plausible slip reproduces. They do not use a bare 'does not follow' line; each states
  the value the working actually gives, e.g. "No likely slip gives 70; the working gives 64."
- **0** bare generic lines remain.

Most arbitrary distractors sit in quantitative-aptitude approximation, number-series and caselet items, where the
setter spaces wrong options around the key (often 10 or 100 apart) rather than building them from a slip. Looser
"close to the rounding" matches were rejected as coincidences, not steps a candidate would take.

## 4. Tag defects (flagged, not fixed)

`tag_suspect = yes` on 39 rows. No retagging has been done.

| Year/Q | Subject | Current `topic_name` | Question | Suggested topic |
|---|---|---|---|---|
| 2023 Q25 | economics | Business cycle phases | A bull market is a period of time in financial markets when the price of an asset or se... | Topic should be Stock markets and capital market developments. The question asks which company's share price crossed ₹1 lakh, not about phases of the business cycle. |
| 2023 Q34 | economics | GDP, GNP, NNP and NDP concepts | Household savings play a vital role in India’s financial sector for multiple reasons. F... | Topic should be Savings and investment in the Indian economy. The question is about the composition of household financial savings, not about national income aggregates like GDP and NNP. |
| 2023 Q36 | economics | Non-tax sources of revenue | Small savings schemes are of significant importance in India due to several reasons. Th... | Topic should be Small savings schemes. Small savings are government borrowings in the Public Account, not a non-tax source of revenue. |
| 2023 Q45 | general-knowledge | Union-State relations and the legislative lists | The legislative assembly holds immense importance in a federal structure as it serves a... | Topic should be State legislatures and assembly elections. The question tests when state assembly terms expire, not the division of legislative powers between the Union and the States. |
| 2023 Q48 | finance | SEBI Act 1992 — establishment, powers, penalties | Recently, the capital markets regulator Sebi proposed to tweak the current definition o... | Topic should be Insider trading and listing disclosures (SEBI PIT and LODR). The question tests the UPSI definition, not the establishment or powers of SEBI under the 1992 Act. |
| 2023 Q54 | finance | FDI caps and sectoral limits | According to the data released by the Department for Promotion of Industry and Internal... | Topic should be FDI inflows and source countries. The question asks about source countries of FDI, not caps or sectoral limits. |
| 2023 Q62 | finance | International bodies — IOSCO, BIS, FATF | Foreign reserves, also known as foreign exchange reserves or forex reserves, are assets... | Topic should be Forex reserves management. The question asks where RBI's gold reserves are held, not about the role of IOSCO, BIS or FATF. |
| 2024 Q8 | finance | Fund of Funds for Startups | Under Self Reliant India (SRI) Fund of Rs. 50,000 crore, there is a provision of ______... | Topic should be MSME financing schemes. The SRI Fund is an equity fund for MSMEs under Atmanirbhar Bharat, not the Fund of Funds for Startups run by SIDBI. |
| 2024 Q75 | economic-social-issues | Public sector bank reforms | In a significant development within the banking sector, the Reserve Bank of India (RBI)... | Topic should be Small finance banks and bank mergers. The question concerns a merger of two private small finance banks, not public sector bank reforms. |
| 2025 Q8 | economics | Non-tax sources of revenue | The Public Provident Fund (PPF) is a long-term small savings scheme introduced by the G... | Topic should be Small savings schemes. PPF is a small savings scheme whose deposits are government liabilities, not a non-tax source of revenue. |
| 2025 Q11 | finance | Banking Regulation Act 1949 — licensing, s.35A, scheduled banks | Which of the following option correctly matches Urban cooperative bank tier with housin... | Topic should be Urban co-operative banks — tiered regulatory framework. The question tests UCB housing-loan limits by tier, not licensing, Section 35A or scheduled-bank status. |
| 2025 Q13 | finance | Valuation ratios — price to book, price to earnings | Reserves = 6,00,000 Equity = 4,00,000 Debt to Net Worth = 0.5 Assets Turnover Ratio = 2... | Topic should be Ratio analysis — leverage, turnover and profitability ratios. The set uses debt-to-net-worth, asset turnover and gross margin, not price-based valuation ratios. |
| 2025 Q14 | finance | Valuation ratios — price to book, price to earnings | Reserves = 6,00,000 Equity = 4,00,000 Debt to Net Worth = 0.5 Assets Turnover Ratio = 2... | Topic should be Ratio analysis — leverage, turnover and profitability ratios. The set uses debt-to-net-worth, asset turnover and gross margin, not price-based valuation ratios. |
| 2025 Q15 | finance | Valuation ratios — price to book, price to earnings | Reserves = 6,00,000 Equity = 4,00,000 Debt to Net Worth = 0.5 Assets Turnover Ratio = 2... | Topic should be Ratio analysis — leverage, turnover and profitability ratios. The set uses debt-to-net-worth, asset turnover and gross margin, not price-based valuation ratios. |
| 2025 Q16 | management | Concept and principles of corporate governance | In a large financial institution, several top-level managers gradually began engaging i... | Topic should be Ethical theories in management. The question asks which ethical theory explains an employee's reasoning, not about corporate governance concepts. |
| 2025 Q17 | economic-social-issues | Sustainable agriculture missions | The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government i... | Topic should be MSME sector and its contribution. The question tests a fintech MoU with the Ministry of MSME and SIDBI; the agricultural passage above it is not used. |
| 2025 Q18 | economic-social-issues | Sustainable agriculture missions | The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government i... | Topic should be MSME sector and its contribution. The question tests MSME registration through the Udyam Portal; the agricultural passage above it is not used. |
| 2025 Q19 | management | Taylor's scientific management | A growing manufacturing company initially relied heavily on precise work-measurement te... | Topic should be Fayol's principles of administrative management. The question is about Fayol and hierarchy, not Taylor's scientific management. |
| 2025 Q19 | economic-social-issues | Sustainable agriculture missions | The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government i... | Topic should be MSME sector and its contribution. The question tests which body administers the Udyam Portal; the agricultural passage above it is not used. |
| 2025 Q20 | economic-social-issues | Sustainable agriculture missions | The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government i... | Topic should be MSME sector and its contribution. The question tests MSME facts from the Economic Survey; the agricultural passage above it is not used. |
| 2025 Q20 | management | Taylor's scientific management | A growing manufacturing company initially relied heavily on precise work-measurement te... | Topic should be Systems approach to management. The question asks about Systems Theory, not Taylor's scientific management. |
| 2025 Q24 | economic-social-issues | Sustainable agriculture missions | The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government i... | Topic should be Regional development and the Aspirational Districts Programme. The question tests the programme's indicator count, not a sustainable agriculture mission. |
| 2025 Q25 | economic-social-issues | Watershed development | Covering about one-third of the Earth’s land surface, forests are crucial for food secu... | Topic should be Forests and environmental governance. The question tests FAO's Global Forest Resources Assessment, not watershed development. |
| 2025 Q26 | economic-social-issues | Watershed development | Covering about one-third of the Earth’s land surface, forests are crucial for food secu... | Topic should be Forests and environmental governance. The question tests the Green Credit Programme, not watershed development. |
| 2025 Q27 | economic-social-issues | Watershed development | Covering about one-third of the Earth’s land surface, forests are crucial for food secu... | Topic should be Forests and environmental governance. The question tests the Environment Audit Rules, 2025, not watershed development. |
| 2025 Q28 | economic-social-issues | Watershed development | Covering about one-third of the Earth’s land surface, forests are crucial for food secu... | Topic should be Forests and environmental governance. The question tests global forest extent from FRA 2025, not watershed development. |
| 2025 Q29 | economics | Non-tax sources of revenue | What is the current corpus (amount) of the Contingency Fund of India? | Topic should be Consolidated Fund, Contingency Fund and Public Account. The Contingency Fund is a fund for unforeseen spending, not a non-tax source of revenue. |
| 2025 Q30 | economics | Real vs nominal income; GDP deflator | If the Consumer Price Index (CPI) is increasing while the Wholesale Price Index (WPI) i... | Topic should be Measures of inflation — CPI and WPI. The question compares retail and wholesale price indices, not real vs nominal income or the GDP deflator. |
| 2025 Q32 | management | Internal vs external factors affecting governance | What is the ethical theory that holds that universal, fixed, and unchanging moral princ... | Topic should be Ethical theories in management. The question asks for an ethical theory, not internal or external factors affecting governance. |
| 2025 Q33 | management | Trait approach — personality, intelligence, emotion | Which theory explains that people’s attitudes influence their motivation and performanc... | Topic should be Process theories of motivation. The question tests a motivation theory, not the trait approach to personality. |
| 2025 Q34 | general-knowledge | Statutory commissions and information oversight | After the recent update (June 2025), how many services are covered under the expanded C... | Topic should be RBI functions and customer-service initiatives. The RBI Citizen's Charter is a service-delivery commitment of the central bank, not a statutory commission or information-oversight body. |
| 2025 Q56 | economics | Plan and non-plan expenditure | In which year was the Planning Commission of India replaced by NITI Aayog (National Ins... | Topic should be Economic planning in India — Planning Commission and NITI Aayog. The question is about the institution that replaced the Planning Commission, not the plan and non-plan expenditure split. |
| 2025 Q67 | general-knowledge | Scientific and research institutions | As of 2025, in which of the following countries have fully operational Small Modular Re... | Topic should be Nuclear energy technology. The question is about a reactor type and where it operates, not about a scientific or research institution. |
| 2025 Q78 | economic-social-issues | Life and accident insurance schemes for the poor | Which organization earned a Guinness World Record in 2025 for selling the most life ins... | Topic should be Insurance sector developments and institutions. The question is about LIC's sales record, not about government life and accident insurance schemes for the poor. |
| 2026 Q3 | economic-social-issues | WTO and global trade bodies | India signed a Comprehensive Economic Partnership Agreement (CEPA) in December 2025 wit... | Topic should be India's bilateral trade agreements. A CEPA is a bilateral pact, not a WTO or multilateral trade body matter. |
| 2026 Q44 | finance | Income-tax — assessment and rectification | Under the Income-tax Rules, 2026, Form 130 replaced which earlier form used as the Tax ... | Topic should be Income-tax — TDS and TDS certificates. The question tests which form certifies salary TDS, not assessment or rectification. |
| 2026 Q56 | finance | Banking Regulation Act 1949 — licensing, s.35A, scheduled banks | Mission SAKSHAM, launched by the Reserve Bank of India, is a capacity-building initiati... | Topic should be Urban co-operative banks and their regulation. Mission SAKSHAM is a UCB capacity-building programme, not a Banking Regulation Act licensing provision. |
| 2026 Q76 | economic-social-issues | Public sector bank reforms | What was the year-on-year (YoY) growth in bank credit for Scheduled Commercial Banks (S... | Topic should be Banking sector credit and deposit trends. The question asks for a credit growth statistic for all scheduled commercial banks, not about public sector bank reforms. |
| 2026 Q78 | general-knowledge | Business and startup terminology | According to the JM Financial-Hurun Unlisted Gems 2026 list, which company ranked 1st a... | Topic should be Business rankings and reports. The question asks for a company's rank in a published list, not for a business or startup term. |

## 5. Low-confidence rows

- **2024 Q6 · economic-social-issues · `ff22c6f5-286f-4ab9-97e2-aedf24118a15`** — Which Ministry is recognized as the top achiever in the National Monetisation Pipeline for the financial year 2023-24?
  - Keyed: (d) Ministry of Road Transport and Highways
  - Reason: Accepted as defensible. Some reports placed the Ministry of Coal first in 2023-24; Coal is not an option, and Road Transport and Highways leads among the ministries offered.
- **2024 Q32 · finance · `fbb7d25c-0b56-4599-b422-c45b381efb42`** — According to the RBI’s report on currency and finance 2024, the rise in digital payments has resulted in several significant outcomes. Which of the following...
  - Keyed: (d) All [1], [2], [3], and [4] are correct
  - Reason: Accepted as defensible at lower confidence. Another reading set aside: option e (statements 1, 3 and 4) because digital payments are usually linked to lower demand for currency, and statement 2 could not be matched to the report's text. The key's inclusion of statement 2 could not be corroborated.
- **2024 Q44 · finance · `1af91cef-9299-4846-8359-82d9dc8c63d2`** — The Certificate of Registration granted to Brickwork Ratings India as a Credit Rating Agency (CRA) was cancelled by market regulator SEBI in October 2022. RB...
  - Keyed: (c) 250 crores
  - Reason: Accepted on the key; the Rs 250 crore limit in the RBI's relaxation for Brickwork ratings could not be corroborated from memory.
- **2025 Q4 · economic-social-issues · `a4679a2f-94e7-4caf-adc8-c709420959c4`** — The Government of India and the World Food Programme (WFP) have announced a collaboration aimed at addressing the global hunger crisis. Which SDG is not part...
  - Keyed: (e) None of the Above
  - Reason: Accepted at low confidence. The exact list of SDGs named in the India-WFP announcement could not be corroborated; SDG 7 (clean energy) looks the least likely fit, but the key says all four are covered.
- **2025 Q9 · economic-social-issues · `8ce8cdb3-54cb-4a01-9cb4-6381232c72b6`** — A private training organisation proposes to open a Pradhan Mantri Kaushal Kendra (PMKK) in a semi-urban district of India. The organisation claims to have ex...
  - Keyed: (e) None
  - Reason: Accepted at low confidence. The specific PMKK thresholds (built-up area by district population, the corporate rating test and the years-in-existence rule) could not be corroborated from memory of the guidelines.
- **2025 Q11 · finance · `b47ec150-b1cc-4130-8984-6d45e33fc72a`** — Infrastructure Investment Trusts (InvITs) are investment vehicles designed to facilitate investment in infrastructure assets through a trust structure. They ...
  - Keyed: (c) 75% and 10%
  - Reason: Accepted on the key at lower confidence. The InvIT Regulations as recalled cap institutional allocation at 75% and reserve at least 25% for other investors without naming a separate 10% retail share, so the 10% figure could not be corroborated.
- **2025 Q21 · finance · `91c8e0da-0f3d-42c8-890b-6b68fe32250b`** — What is the minimum credit rating required for a deposit-taking NBFC (NBFC-D) to accept or renew public deposits under the regulations of the Reserve Bank of...
  - Keyed: (a) BBB–
  - Reason: Accepted on the key at lower confidence. The RBI's rating floor for public deposits has been revised over time (earlier an A-grade rating; the current text speaks of a minimum investment-grade rating), and the exact current floor could not be corroborated.
- **2025 Q30 · economic-social-issues · `4a7d9ad0-4c79-428e-a31b-7d6fd2fa6c75`** — The launch of Pradhan Mantri Awas Yojana – Urban 2.0 (PMAY-U 2.0) has created a significant need to generate public awareness about the scheme and encourage ...
  - Keyed: (e) Climate-Resilient Shelter
  - Reason: Accepted at low confidence. A theme for the 2025 campaign could not be corroborated. Another reading set aside: option c, 'Housing for All', is PMAY's long-standing mission and a candidate may read it as the theme.
- **2025 Q35 · economic-social-issues · `6e5c838c-4818-43cc-b3d2-356c7a87bde9`** — What is the daily gross transaction volume in India’s capital market based on recent data (2025)?
  - Keyed: (e) Rs 4 lakh crore
  - Reason: Accepted at low confidence. The source of the ₹4 lakh crore figure and which segments it covers could not be corroborated.
- **2025 Q35 · economic-social-issues · `1a0d88a0-4163-4e27-87be-d7c3fcea6826`** — The SEBI circular, issued on May 29, 2025, presents a comprehensive framework aimed at improving transparency, risk monitoring, and trading practices in the ...
  - Keyed: (b) 1 and 2 only
  - Reason: Accepted at low confidence as a dated regulatory fact. The 2025 circular moved open-interest measurement to a delta-based future-equivalent basis, which supports reading statement 3's 'aggregate open interest exceeds 95%' as outdated. Another reading set aside: option a, if the 95% trigger is taken as retained and a ban-period increase as a violation rather than a permitted trade with penalty.
- **2025 Q61 · finance · `316601a9-1e15-4476-8732-580f584827c4`** — Which of the following data sets is released by the Reserve Bank of India on a daily basis, similar to Liquidity Adjustment Facility (LAF) and Money Market O...
  - Keyed: (d) Reference Exchange Rates data
  - Reason: Accepted on the key at lower confidence. Since 2018 FBIL, not the RBI, calculates reference exchange rates, so 'released by the RBI' holds only for the RBI's publication of FBIL rates. The stem also mislabels money market operations as 'OMO'.
- **2026 Q14 · general-knowledge · `db8e599f-e6a6-4020-85db-ce46a0258cf9`** — Indian Railways launched CHIRAG to strengthen Human Resource systems through information technology, research, analytics and governance support. Where was th...
  - Keyed: (c) Hyderabad
  - Reason: The location of the CHIRAG centre launch could not be corroborated; key accepted.
- **2026 Q17 · finance · `29e05594-470e-4f38-87df-2db9ad5bf3b8`** — Which of the following are the strategic pillars of the Reserve Bank of India’s Utkarsh 2029 strategy framework?
  - Keyed: (e) All of the above
  - Reason: The exact pillar list of Utkarsh 2029 could not be corroborated from a primary RBI document; key accepted at lower confidence.
- **2026 Q22 · general-knowledge · `fba8b074-a1ac-4ac1-ac0b-ae4423d6e9b0`** — Which bank was awarded the National Award for Outstanding Performance in Self- Help Group (SHG)-Bank Linkage 2024–25?
  - Keyed: (a) Karnataka Grameena Bank
  - Reason: The 2024-25 award winner could not be corroborated; key accepted.
- **2026 Q28 · finance · `a7cd2a57-d363-4ead-ba0b-5290d0ceb402`** — The Reserve Bank of India recently cancelled the banking licence of which payments bank in April 2026?
  - Keyed: (a) Paytm Payments Bank
  - Reason: The April 2026 cancellation could not be independently corroborated; key accepted at lower confidence because it follows the 2024 business restrictions on Paytm Payments Bank.
- **2026 Q49 · general-knowledge · `4fe8bf7a-616d-4429-98ff-24bfa1d9ac7f`** — Which of the following was part of the consortium that signed an agreement to acquire Royal Challengers Bengaluru (RCB) from United Spirits Limited in 2026?
  - Keyed: (e) All of the above
  - Reason: The consortium's membership is a dated deal announcement that could not be corroborated; key accepted.
- **2026 Q53 · general-knowledge · `b15cae37-0c87-4b04-a5fc-b7a382470347`** — Which Union Territory set a Guinness World Record by unfurling the largest underwater national flag beneath the sea?
  - Keyed: (c) Andaman and Nicobar Islands
  - Reason: The record-setting event could not be corroborated. Also, 'Daman and Diu' and 'Dadra and Nagar Haveli' were merged into a single Union Territory in 2020; key accepted.
- **2026 Q57 · general-knowledge · `7802b29f-d1c9-4981-a09f-a339deaa043f`** — The JANANI platform, launched by the Union Health Ministry to strengthen maternal and child healthcare, is a service-oriented digital platform for maintainin...
  - Keyed: (c) Journey
  - Reason: The platform's official expansion could not be corroborated; key accepted.
- **2026 Q59 · general-knowledge · `91675498-0569-496e-8d80-11c891abf42b`** — India’s first satellite-tagged Ganges Softshell Turtle was released in which national park?
  - Keyed: (b) Kaziranga National Park
  - Reason: The release site could not be corroborated; key accepted.
- **2026 Q60 · general-knowledge · `928c8863-88b8-4b61-91f4-32d682e5b755`** — The inaugural International Cricket Council (ICC) Women’s Challenge Trophy was hosted by which country?
  - Keyed: (e) Rwanda
  - Reason: The host of the inaugural tournament could not be corroborated; key accepted.
- **2026 Q67 · economic-social-issues · `c26a338e-8567-4748-becf-9d81c59255b4`** — To manage domestic availability and price stability, India extended restrictions on the export in May 2026 of which agricultural commodity till September 2026?
  - Keyed: (c) Sugar
  - Reason: The May 2026 notification could not be corroborated; sugar has been in the 'restricted' export category since 2022, which fits the key, but other commodities have also faced curbs, so confidence is low.
- **2026 Q68 · general-knowledge · `54dd9e3e-17f2-4d72-9939-b53c93cb873e`** — The International Booker Prize 2026 recognises outstanding works of fiction translated into English. Which book won the International Booker Prize 2026?
  - Keyed: (a) Taiwan Travelogue
  - Reason: Accepted as keyed. The 2026 result could not be independently corroborated at drafting time; Taiwan Travelogue is a known prize-winning translated novel, but the 2026 International Booker outcome needs a reviewer check.
- **2026 Q69 · finance · `7ecdb3f0-003c-4c2e-9d80-1ece9f65d7eb`** — In April 2026, which fintech company received approval from the Reserve Bank of India (RBI) for a Non-Banking Financial Company (NBFC) licence to launch its ...
  - Keyed: (d) One MobiKwik Systems
  - Reason: The April 2026 approval could not be independently corroborated; key accepted at lower confidence.
- **2026 Q72 · general-knowledge · `db183f8d-748a-4340-ad0e-5a44a026bf1a`** — Which initiative was launched by the Supreme Court of India to integrate case data across different levels of the judicial system?
  - Keyed: (b) One Case One System
  - Reason: Accepted as keyed. The initiative's exact name could not be independently corroborated at drafting time; option a is a close variant and a reviewer should confirm the official title.
- **2026 Q76 · economic-social-issues · `3b5103c4-e6d0-452c-9366-d7d58a3b779a`** — What was the year-on-year (YoY) growth in bank credit for Scheduled Commercial Banks (SCBs) as on end-March 2026?
  - Keyed: (c) 14.1%
  - Reason: The 14.1% figure for end-March 2026 could not be corroborated; accepted with the key at low confidence.
- **2026 Q77 · general-knowledge · `b2e9bac9-ffee-4db3-b5cb-0737ec403527`** — The report titled “Moving Towards Effective City Government – A Framework for Million-Plus Cities” is released by which of the following?
  - Keyed: (b) NITI Aayog
  - Reason: Accepted as keyed. The report's release could not be independently corroborated at drafting time.

| Confidence | Count |
|---|---|
| high | 248 |
| medium | 90 |
| low | 26 |

Medium rows are not listed; where a specific reservation exists it is in that row's `key_note`.

## 6. Field-population counts

| Field | Rows populated | Of 364 |
|---|---|---|
| `short_explanation` | 364 | 100% |
| `explanation_text` | 5 | 1% |
| `solution_steps` | 4 | 1% |
| `formula_used` | 4 | 1% |
| `common_traps` | 231 | 63% |
| `key_note` | 139 | 38% |
| `final_answer_option_id` | 354 | 97% |
| `option_rationales` (entries, not rows) | 1455 | — |

5 rationale entries are the fixed filler line ("Filler option; a correct answer is present.").

## 7. Validation

Enforced by the build script; the worksheet is written only when every check passes.

- **Row count:** 364 rows, one per input question.
- **Uniqueness:** 364 distinct `question_id` values.
- **Completeness:** the worksheet and input `question_id` sets are identical; `year`, `question_number`, `subject_slug`,
  `topic_name` are copied unchanged.
- **Option-rationale integrity:** 1455 entries, each keyed to an `option_id` and `label` on that question, no
  duplicates. Wrong options across the corpus: 1454. Every wrong option on an AGREE row is covered; the only gaps
  are options this draft argues are correct or defensible (the proposed option on a DISPUTED row).
- **No contradiction on AGREE rows:** no AGREE row carries a rationale against its own keyed option.
- **final_answer_option_id:** set on all 354 AGREE rows and equal to the input `correct_option_id`; null on every
  non-AGREE row.
- **Verdict integrity:** every DISPUTED row names a `proposed_correct_option_id` on that question and different from the key;
  no other row carries one. Every non-AGREE row and every low-confidence row carries a `key_note`.
- **Tag integrity:** `tag_suspect = yes` ⇔ non-empty `tag_note`. No `topic_name` modified.
- **Provenance:** every row `platform_original` / `owned` / `pending`.
- **AGREE rows arguing for another option:** 0. No AGREE row has a rationale against its key, a proposed option, or a null final id.
- **solution_steps:** non-empty on 4 rows, all numericals (finance 3, economics 1). Every other row has `[]`.
- **Verdicts:** AGREE 354, DISPUTED 9, UNANSWERABLE 1. **Confidence:** high 248, medium 90, low 26.

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
  `final_answer_option_id` is null — the 10 non-AGREE rows cannot be verified until the key is resolved.
- Editing learner-facing fields on a verified row downgrades it to `needs_correction`; the apply step should touch only
  `pending` rows.

## 9. Scope

RBI Grade B top-up only — the 364 questions in `rbi-explanations-input-2.json`. The first RBI worksheet is untouched. No database writes, no migrations, no retagging, no change to
any question or option.

## 10. Ready-to-read sample (20 rows)

Chosen with `random.Random(20260923).sample(rows, 20)` over the worksheet rows in file order, then sorted by year, subject
and question number for reading. Re-running the same call on the same file yields the same 20.

---

### S1. 2023 Q29 · economic-social-issues · Higher education, enrolment and AISHE

`0f70f032-86ad-4a9d-8dab-dc7c694f6f78` · verdict AGREE · confidence high · current affairs yes

**Question.** The Union Minister Education, Skill Development and Entrepreneurship, Shri Dharmendra Pradhan released the India Rankings 2023 in June 2023. Which of the following statements is incorrect with respect to the NIRF rankings?

- (a) Indian Institute of Technology Madras retains its 1st position in Overall Category for fifth consecutive year
- (b) Indian Institute of Science, Bengaluru tops the Universities Category
- (c) All India Institute of Medical Sciences (AIIMS), New Delhi occupies the top slot in Medical
- (d) National Law School of India University, Bengaluru retains its first position in Law
- (e) St. Stephens is the best college among all colleges **← keyed**

**Short explanation.** NIRF is the Education Ministry's annual ranking of higher education institutions. In 2023 Miranda House, not St. Stephen's, was the top college, so statement e is incorrect.

**Why the other options are wrong**

- (a) True: IIT Madras was first overall for the fifth year running.
- (b) True: IISc Bengaluru topped the universities category.
- (c) True: AIIMS New Delhi was first in medical.
- (d) True: NLSIU Bengaluru stayed first in law.

**Common traps**

- Missing that the question asks for the incorrect statement.

---

### S2. 2023 Q43 · economics · Monetary policy transmission mechanism

`a4b2c61b-cfa6-4096-8bb2-a27bbab9016e` · verdict AGREE · confidence high · current affairs no

**Question.** As per the RBI’s Annual Report, _____ witnessed an improvement, reflecting the higher degree of transmission of monetary policy to lending rates than to deposit rates in the rising interest rate cycle.

- (a) CASA
- (b) LCR
- (c) PCR
- (d) CRAR
- (e) NIM **← keyed**

**Short explanation.** Net interest margin (NIM) is the gap between what a bank earns on loans and what it pays on deposits, relative to its assets. In a rising rate cycle, lending rates rose faster than deposit rates, so the RBI Annual Report noted that NIM improved.

**Why the other options are wrong**

- (a) CASA is the share of current and savings deposits; it does not measure the gap between lending and deposit rates.
- (b) LCR measures a bank's liquid assets against short-term outflows, not its interest spread.
- (c) PCR measures provisions against bad loans, not the spread between lending and deposit rates.
- (d) CRAR measures capital against risk-weighted assets, not interest spread.

**Common traps**

- Picking CASA because deposit rates are mentioned; the question is about the spread between lending and deposit rates, which is NIM.

---

### S3. 2023 Q17 · finance · RBI Payments Vision and the 4Es

`b89a3e1c-57bb-4aae-8e2a-0c9e914cf3f9` · verdict AGREE · confidence high · current affairs yes

**Question.** The Digital Payment Index (DPI) is a metric used to measure the adoption and growth of digital payments within a country. It provides an assessment of the digital payment ecosystem, taking into account various parameters such as the number of digital transactions, the value of digital payments, the availability of digital payment infrastructure, and the level of consumer awareness and confidence in using digital payment methods. What is the base period of the digital payment index?

- (a) March 2018 **← keyed**
- (b) March 2017
- (c) September 2018
- (d) September 2017
- (e) March 2019

**Short explanation.** The RBI Digital Payments Index tracks how far digital payments have spread, using five weighted parameters. Its base period is March 2018, when the index is set to 100.

**Why the other options are wrong**

- (b) Not the base period; the index is set to 100 at March 2018.
- (c) Not the base period; the index is set to 100 at March 2018.
- (d) Not the base period; the index is set to 100 at March 2018.
- (e) Not the base period; the index is set to 100 at March 2018.

---

### S4. 2023 Q14 · general-knowledge · International organisations and groupings

`828f8e49-5f89-434a-8d4c-dce4ada36b90` · verdict AGREE · confidence high · current affairs no

**Question.** What makes a country worth living is not just economic hegemony and achievements of the state, it is the wealth of the culture of the people, accumulated over centuries of wisdom about how to conduct life. The ancient Indian civilisation is the source of all the extensions of what we call as the Indian subcontinent. The geographic spread covered under this banner stretches far towards the Gulf on one side and towards the expanse of Indo-Pacific on the other. In the present scenario, countries like India and China are jostling for influence over the ports and island nations of the Indian Ocean. The pivot of a major chunk of economics in the extended neighbourhood is the Indian Ocean because many resources like oil, gas, raw materials and goods pass through it. Over a period of time, for political, economic and security reasons, various blocks and groupings were formed for cooperation on several fronts. The two main groupings we have in the Indo-Pacific region are ASEAN and BIMSTEC. Which of the following countries are common members of these two regional blocs? 1) Thailand 2) Cambodia 3) Myanmar 4) Laos 5) Vietnam

- (a) 1 and 2 Only
- (b) 2 and 3 Only
- (c) 1 and 3 Only **← keyed**
- (d) 3 and 4 Only
- (e) 4 and 5 Only

**Short explanation.** ASEAN has ten South-East Asian members, while BIMSTEC has seven countries around the Bay of Bengal (Bangladesh, Bhutan, India, Myanmar, Nepal, Sri Lanka and Thailand). Only Thailand and Myanmar belong to both, so the answer is 1 and 3.

**Why the other options are wrong**

- (a) Cambodia is in ASEAN but not in BIMSTEC.
- (b) Cambodia is in ASEAN but not in BIMSTEC.
- (d) Laos is in ASEAN but not in BIMSTEC.
- (e) Laos and Vietnam are in ASEAN but neither is in BIMSTEC.

**Common traps**

- Assuming all mainland South-East Asian countries are in BIMSTEC; only Myanmar and Thailand, which border the Bay of Bengal, are.

---

### S5. 2024 Q75 · economic-social-issues · Public sector bank reforms

`c2377279-c3a4-4bce-9fac-ad9fe5bce7e8` · verdict AGREE · confidence high · current affairs yes

**Question.** In a significant development within the banking sector, the Reserve Bank of India (RBI) has approved a merger that will reshape the landscape of small finance banks in the country. This merger is set to take effect on April 1, 2024, and will involve the consolidation of two entities, allowing for enhanced operational efficiencies and a broader customer base. Shareholders of the bank being merged will receive shares of the acquiring bank in exchange for their existing shares, based on an approved share swap ratio. Which banks are involved in this merger?

- (a) Ujjivan SFB and Equitas SFB
- (b) Jana SFB and Utkarsh SFB
- (c) Bandhan Bank and IDFC First Bank
- (d) Fincare SFB and AU SFB **← keyed**
- (e) Capital Small Finance Bank and North East Small Finance Bank

**Short explanation.** Small finance banks serve under-banked customers and can merge with RBI approval. The RBI approved the merger of Fincare Small Finance Bank into AU Small Finance Bank, effective 1 April 2024, with Fincare shareholders receiving AU shares under a share swap.

**Why the other options are wrong**

- (a) Ujjivan and Equitas did not merge.
- (b) Jana and Utkarsh did not merge.
- (c) Bandhan and IDFC First did not merge; IDFC First merged with its own parent, IDFC.
- (e) Capital and North East SFBs did not merge.

**Tag note.** Topic should be Small finance banks and bank mergers. The question concerns a merger of two private small finance banks, not public sector bank reforms.

---

### S6. 2024 Q28 · finance · Payment banks and differentiated banks

`9c570193-9a1e-4cbd-b7b3-681465a46cc8` · verdict AGREE · confidence high · current affairs yes

**Question.** The Reserve Bank of India (RBI) has outlined specific eligibility criteria for Small Finance Banks (SFBs) to transition into Universal Banks (UBs) under its on-tap licensing policy. Which of the following accurately describes one of the key criteria for such a transition?

- (a) A minimum net worth of Rs 1,500 crore and scheduled bank status with at least 3 years of operation.
- (b) A minimum net worth of Rs 1,000 crore, scheduled bank status, and a satisfactory performance track record of at least 5 years. **← keyed**
- (c) A minimum net worth of Rs 1,000 crore, with no requirement for scheduled bank status.
- (d) No minimum net worth requirement, but SFBs must have been in operation for 7 years with scheduled bank status.
- (e) A minimum net worth of Rs 500 crore, with listed shares on a recognized stock exchange.

**Short explanation.** Under RBI's on-tap framework, a Small Finance Bank may move to universal banking if it has net worth of at least ₹1,000 crore, scheduled status, a satisfactory track record of at least five years, listed shares and low NPAs.

**Why the other options are wrong**

- (a) Wrong figures; the net worth floor is ₹1,000 crore and the track record is five years.
- (c) Scheduled bank status is required.
- (d) A minimum net worth of ₹1,000 crore is required, and the track record is five years.
- (e) The net worth floor is ₹1,000 crore; listing is required but alone is not enough.

**Common traps**

- Other conditions (listing, gross NPA up to 3%, net NPA up to 1%) also apply; any option naming a different net worth or tenure is wrong.

---

### S7. 2024 Q31 · finance · RBI, SEBI, IRDAI, PFRDA — mandate boundaries

`896c2b31-f466-409b-b800-641be3efc1f0` · verdict AGREE · confidence high · current affairs no

**Question.** The International Financial Services Centres Authority (IFSCA) plays a pivotal role in regulating financial institutions, financial products, and services within India’s International Financial Services Centres (IFSCs). Which of the following statements is not correct regarding IFSCA?

- (a) IFSCA was established under the IFSCA Act, 2019, to regulate financial services in IFSCs in India.
- (b) The IFSCA operates as a statutory body under the Ministry of Finance, overseeing banking, insurance, and securities markets in IFSCs.
- (c) Like SEBI or RBI, the IFSCA have the power to issue regulations related to capital markets in IFSCs.
- (d) IFSCA is empowered to regulate all financial products, including derivatives, within India’s IFSCs.
- (e) The IFSCA do not have the authority to develop and regulate international bullion exchanges in India. **← keyed**

**Short explanation.** IFSCA, set up under the IFSCA Act, 2019, is the single unified regulator for banking, capital markets, insurance and bullion in India's IFSCs such as GIFT City, so the claim that it cannot develop and regulate international bullion exchanges is false. IFSCA in fact regulates the India International Bullion Exchange (IIBX) at GIFT City.

**Explanation.** Before 2020, activity in GIFT City was split among RBI, SEBI, IRDAI and PFRDA. The IFSCA Act, 2019 moved these powers to one statutory body, which took charge in 2020. Its mandate covers financial products, services and institutions in IFSCs, including derivatives, capital-market regulations, and bullion exchanges; the IFSCA (Bullion Exchange) Regulations, 2020 govern the IIBX.

**Why the other options are wrong**

- (a) True; IFSCA was constituted under the IFSCA Act, 2019.
- (b) True; IFSCA is a statutory body under the Ministry of Finance with oversight of banking, insurance and securities business in IFSCs.
- (c) True; like SEBI or RBI in the domestic market, IFSCA frames its own regulations for capital markets in IFSCs.
- (d) True; the Act lets IFSCA regulate all financial products in IFSCs, including derivatives.

**Common traps**

- Assuming SEBI or a commodity regulator runs the GIFT City bullion exchange; IFSCA is the regulator of IIBX.

---

### S8. 2024 Q51 · general-knowledge · Computing and artificial intelligence

`502ce244-eebd-45d6-873c-07b8e0daec11` · verdict AGREE · confidence high · current affairs yes

**Question.** The field of Generative Artificial Intelligence (Gen AI) has seen significant advancements and innovations, leading to an increase in patent filings worldwide. Various countries are competing to establish themselves as leaders in this emerging technology. Understanding which country is at the forefront of this trend is essential for grasping the global landscape of AI development. As companies and research institutions invest heavily in Gen AI, identifying the nation that has filed the maximum number of patents in this area can provide insights into future technological advancements. Which country has filed the maximum number of patents in Gen AI?

- (a) United States
- (b) Germany
- (c) South Korea
- (d) Japan
- (e) China **← keyed**

**Short explanation.** The World Intellectual Property Organization's July 2024 Patent Landscape Report on generative AI found that China filed by far the most GenAI patent families from 2014 to 2023, about 38,000, around six times the United States. South Korea, Japan and India followed.

**Why the other options are wrong**

- (a) The United States was a distant second in GenAI patent filings, though it leads in many AI models and companies.
- (b) Germany was well behind the top five in GenAI patent filings.
- (c) South Korea ranked third in GenAI patent filings.
- (d) Japan ranked fourth in GenAI patent filings.

**Common traps**

- Assuming the US leads because the best-known GenAI firms are American; by patent filings, China is far ahead.

---

### S9. 2024 Q52 · general-knowledge · Sports terminology and Indian sporting history

`9bcb0ef0-a3f5-4943-b99f-0df2c20550d0` · verdict AGREE · confidence medium · current affairs yes

**Question.** Carlos Alcaraz, a rising star in the world of tennis, has made headlines with his impressive performances in various Grand Slam tournaments. His remarkable skills and determination have led him to secure victories in several prestigious events. However, despite his success, there are still some Grand Slams that he has yet to win. Understanding which tournaments have eluded him is essential for analyzing his career trajectory and future potential. Which of the following Grand Slams did Carlos Alcaraz not win?

- (a) French Open
- (b) Wimbledon
- (c) Australian Open **← keyed**
- (d) US Open
- (e) None

**Short explanation.** By the time of the 2024 exam, Spain's Carlos Alcaraz had won the US Open (2022), Wimbledon (2023 and 2024) and the French Open (2024). The Australian Open was the one Grand Slam he had not yet won.

**Why the other options are wrong**

- (a) Alcaraz won the French Open in 2024.
- (b) Alcaraz won Wimbledon in 2023 and 2024.
- (d) Alcaraz won the US Open in 2022, his first Grand Slam title.
- (e) Filler option; the Australian Open was a Grand Slam he had not won.

**Key note.** Correct as of the 2024 exam. The fact is time-bound: Alcaraz is reported to have won the Australian Open in January 2026, completing the career Grand Slam, so a current version of this question would have no correct option other than e.

---

### S10. 2025 Q12 · economic-social-issues · Social legislation on women, children and the elderly

`13001bdb-7836-4d9b-9463-e3d542f0ad8e` · verdict AGREE · confidence high · current affairs yes

**Question.** Which of the following are eligible under the CARA rules 2025? 1. A female single parent aged 45 want to adopt a male or female child aged 4 years. 2. Parents having composite age 92 years want to adopt a child aged upto 4 years. 3. A single male parent wants to adopt a female child aged 2 years.

- (a) 1 and 3 only
- (b) 1 only **← keyed**
- (c) 3 only
- (d) 1 and 2 only
- (e) None

**Short explanation.** Under the CARA adoption regulations a single woman may adopt a child of either gender, and for a child up to 4 years the maximum age is 45 for a single parent and 90 composite for a couple. So the 45-year-old single mother qualifies, the couple with a composite age of 92 does not, and a single man cannot adopt a girl.

**Why the other options are wrong**

- (a) Statement 3 is wrong: a single male parent is not eligible to adopt a girl child.
- (c) Statement 3 is wrong, and statement 1 is correct.
- (d) Statement 2 is wrong: the composite age limit for a child up to 4 years is 90.
- (e) Statement 1 is correct.

**Common traps**

- Assuming a single parent can adopt any child; the gender bar applies only to single men adopting girls.

---

### S11. 2025 Q16 · economic-social-issues · Capital market instruments and regulation

`d2248ef9-6299-4f8e-9641-3d7dfe54de47` · verdict AGREE · confidence high · current affairs yes

**Question.** Specialized Investment Funds (SIFs) are a new category of investment products in India, introduced by the Securities and Exchange Board of India (SEBI) in early 2025. They are designed to bridge the gap between traditional mutual funds (MFs), which have limited flexibility, and Portfolio Management Services (PMS) or Alternative Investment Funds (AIFs), which have very high minimum investment thresholds. Consider the following statements regarding Specialized Investment Funds (SIFs): 1. An investor must commit a minimum of ₹50 lakh per strategy to be eligible for enrollment. 2. The unhedged short exposure in a SIF is capped at 50% of the fund's net assets. 3. Notice periods for redemptions in SIFs can extend up to 15 working days. 4. An individual with a net worth of at least ₹7.5 crore, of which at least ₹3.75 crore is in financial assets is called accredited investor eligible under investment in SIF. Which of the following statement given above is correct?

- (a) 1 and 2 only
- (b) 3 and 4 only **← keyed**
- (c) 1, 2 and 3 only
- (d) 2, 3 and 4 only
- (e) 1, 2, 3 and Direction (Q11 – Q14) - Read the passage given below and answer the following questions The Pradhan Mantri Dhan-Dhaanya Krishi Yojana (PMDDKY) is a groundbreaking government initiative launched to revolutionize Indian agriculture by making it more productive, sustainable, and financially rewarding for farmers. Announced on February 1, 2025, during the Union Budget 2025-26 by Finance Minister Nirmala Sitharaman and approved by the Union Cabinet on July 16, 2025, PMDDKY targets 100 underperforming districts where farming faces challenges like low crop yields, water scarcity, and limited access to resources. With an annual budget of __________ for six years (2025-26 to 2030-31), totaling ___________, the scheme aims to support 1.7 crore farmers, particularly small and marginal farmers owning less than 2 hectares of land, who constitute 86% of India’s farming population (Economic Survey 2024-25). (This is a recreated passage and not the exact one asked in the exam)

**Short explanation.** SEBI's Specialized Investment Funds sit between mutual funds and PMS. Redemption notice periods of up to 15 working days are allowed, and accredited investors (for example, net worth at least ₹7.5 crore with at least ₹3.75 crore in financial assets) are exempt from the minimum ticket; the minimum is ₹10 lakh, not ₹50 lakh, and unhedged short exposure is capped at 25%.

**Why the other options are wrong**

- (a) Both statements are wrong: the minimum is ₹10 lakh across SIF strategies and unhedged short exposure is capped at 25% of net assets.
- (c) Statements 1 and 2 are wrong.
- (d) Statement 2 is wrong: the cap is 25%, not 50%.
- (e) Statements 1 and 2 are wrong.

**Common traps**

- ₹50 lakh is the PMS minimum, and ₹1 crore the AIF minimum; the SIF minimum is ₹10 lakh.

**Key note.** Option e's text is truncated in the source and carries the next set's direction text; it is read as '1, 2, 3 and 4'.

---

### S12. 2025 Q25 · economic-social-issues · Watershed development

`a424381f-3119-4f8a-8a65-76c8f6cf62d3` · verdict AGREE · confidence medium · current affairs yes

**Question.** Covering about one-third of the Earth’s land surface, forests are crucial for food security, livelihoods and for renewable biomaterials and energy. They are habitats for a large proportion of the world’s biodiversity, help regulate global carbon and hydrologic cycles, and can reduce the risks and impacts of drought, desertification, soil erosion, landslides and floods. Yet they also face many challenges and demands, and balancing priorities in forest management requires reliable, timely data. As a knowledge-based organization, the Food and Agriculture Organization of the United Nations (FAO) is mandated to “collect, analyse, interpret and disseminate information relating to nutrition, food and agriculture.” In this regard, FAO has conducted Global Forest Resources Assessments (FRAs) in 2025. FRAs build on data collected and reported by countries. A truly collaborative approach, combined with consolidated data collection, analysis and validation, ensures that the best and most recent knowledge is shared and applied through a standardized set of definitions and methodology. To reduce the reporting burden on countries, to increase synergies among reporting processes, and to improve data consistency, the process also involves collaboration among many partner organizations. Which of the following statements is correct regarding Global Forest Resources Assessment 2025? 1. Global Forest Resources Assessment 2025 is the only worldwide assessment based on official national data. 2. It is the first ever Global Forest Resources Assessment report. 3. FRA identifies two broad categories of forest: naturally regenerating and planted.

- (a) 1 and 2 only
- (b) 1 and 3 only **← keyed**
- (c) 2 and 3 only
- (d) 1, 2 and 3
- (e) 3 only

**Short explanation.** FAO's Global Forest Resources Assessment is the only worldwide forest assessment built on official national data, and it classifies forests as naturally regenerating or planted. FRAs have been run since 1946, so the 2025 edition is far from the first.

**Why the other options are wrong**

- (a) Statement 2 is wrong: FRAs date back to 1946.
- (c) Statement 2 is wrong, and statement 1 is correct.
- (d) Statement 2 is wrong.
- (e) Leaves out statement 1, which FAO itself claims for the FRA.

**Tag note.** Topic should be Forests and environmental governance. The question tests FAO's Global Forest Resources Assessment, not watershed development.

---

### S13. 2025 Q56 · economics · Plan and non-plan expenditure

`b59c62bf-e5d7-496f-b9ca-a06dba55d2b8` · verdict AGREE · confidence high · current affairs no

**Question.** In which year was the Planning Commission of India replaced by NITI Aayog (National Institution for Transforming India)?

- (a) 2012
- (b) 2013
- (c) 2014
- (d) 2015 **← keyed**
- (e) 2016

**Short explanation.** The Prime Minister announced the end of the Planning Commission on 15 August 2014, but NITI Aayog was formally set up by a Cabinet resolution on 1 January 2015, so the replacement took effect in 2015.

**Why the other options are wrong**

- (a) The Planning Commission was still working in 2012.
- (b) The Planning Commission was still working in 2013.
- (c) 2014 is when the end of the Planning Commission was announced; NITI Aayog came into being on 1 January 2015.
- (e) NITI Aayog was already working by 2016.

**Common traps**

- Choosing 2014, the year of the Independence Day announcement, instead of 2015 when NITI Aayog was actually set up.

**Key note.** Accepted as defensible. Another reading set aside: option c (2014), because that is only when the plan to replace the Planning Commission was announced; NITI Aayog was created on 1 January 2015.

**Tag note.** Topic should be Economic planning in India — Planning Commission and NITI Aayog. The question is about the institution that replaced the Planning Commission, not the plan and non-plan expenditure split.

---

### S14. 2025 Q42 · finance · Basel norms and capital adequacy

`35b8579a-a850-4859-8cd4-5e0c9bbc3429` · verdict AGREE · confidence high · current affairs no

**Question.** Capital Adequacy and Provisioning Guidelines as per Basel III norms are applicable to which of the following regulated entities? 1. Local Area Banks 2. Payments Banks 3. Regional Rural Banks 4. Scheduled Commercial Banks

- (a) 1 and 4 only
- (b) 2, 3 and 4 only
- (c) 1, 2 and 4 only
- (d) 4 only **← keyed**
- (e) 1, 2, 3 and 4 only

**Short explanation.** In India the RBI's Basel III capital rules apply to scheduled commercial banks. Local area banks, payments banks and regional rural banks are expressly kept out and follow simpler capital rules of their own.

**Why the other options are wrong**

- (a) Local area banks are outside the Basel III framework.
- (b) Payments banks and RRBs are outside the Basel III framework.
- (c) Local area banks and payments banks are outside the Basel III framework.
- (e) Only scheduled commercial banks come under Basel III; the other three are excluded.

**Common traps**

- Assuming RRBs are covered because they are scheduled; the RBI's Basel III circular leaves them out.

---

### S15. 2025 Q36 · general-knowledge · Geographical indication tags and crafts

`9606ad52-7f77-4113-a731-4a0cc675f0c3` · verdict AGREE · confidence high · current affairs no

**Question.** The traditional craft “Thewa Art”, which has received a Geographical Indication (GI) tag, is associated with which Indian state?

- (a) Gujarat
- (b) Rajasthan **← keyed**
- (c) Madhya Pradesh
- (d) Uttar Pradesh
- (e) Maharashtra

**Short explanation.** Thewa is a jewellery craft from Pratapgarh in Rajasthan: finely worked gold sheet is fused onto coloured glass. It carries a Geographical Indication tag, which links a product to its place of origin.

**Why the other options are wrong**

- (a) Not the home of Thewa; Gujarat's GI crafts include Patola and Sadeli.
- (c) Not the home of Thewa.
- (d) Not the home of Thewa.
- (e) Not the home of Thewa.

---

### S16. 2025 Q55 · general-knowledge · Defence forces, exercises and expeditions

`d4eb19f3-b01e-43a9-8914-8b18eb6b75f7` · verdict AGREE · confidence high · current affairs yes

**Question.** In which year was the Mikoyan-Gurevich MiG-21 commissioned into the Indian Air Force (IAF)?

- (a) 1957
- (b) 1962
- (c) 1963 **← keyed**
- (d) 1971
- (e) 1983

**Short explanation.** The MiG-21, India's first supersonic fighter, entered IAF service in 1963 and was later licence-built by HAL. It was in the news when it was retired in September 2025 after more than six decades of service.

**Why the other options are wrong**

- (a) Arbitrary alternative year; the first MiG-21s were inducted in 1963.
- (b) The deal for the MiG-21 was signed in 1962; the aircraft were inducted in 1963.
- (d) The MiG-21 was already in service by the 1971 war, in which it saw action.
- (e) Arbitrary alternative year; the MiG-21 was inducted in 1963.

---

### S17. 2026 Q66 · finance · NPCI systems — UPI, IMPS, NEFT, RTGS

`94ce286e-c5cb-447f-bc2f-65c818c4becc` · verdict AGREE · confidence medium · current affairs yes

**Question.** To support small-value digital payments even in areas with weak or limited internet connectivity, which version of Unified Payments Interface (UPI) allows offline paymentsupto Rs 500?

- (a) UPI 123PAY
- (b) UPI Lite X **← keyed**
- (c) UPI AutoPay
- (d) UPI Circle
- (e) UPI Global

**Short explanation.** UPI Lite is an on-device wallet for small payments without a PIN; UPI Lite X extends it to fully offline payments by tapping phones (NFC), for small amounts such as ₹500 per payment.

**Why the other options are wrong**

- (a) UPI 123PAY lets feature-phone users pay (for example by missed call or voice), not small offline tap payments from a Lite wallet.
- (c) UPI AutoPay sets up recurring mandates, not offline payments.
- (d) UPI Circle lets a primary user delegate payments to family members; it is not an offline feature.
- (e) UPI Global is for payments abroad, not offline payments.

**Common traps**

- Picking UPI 123PAY because it also works without mobile internet; it serves feature phones, whereas UPI Lite X is the offline small-value wallet.

**Key note.** The small-value per-payment limit for UPI Lite has been revised over time; the ₹500 figure is taken as given in the stem.

---

### S18. 2026 Q11 · general-knowledge · International organisations and groupings

`567adce5-89df-4dc8-8e92-f2716b321b54` · verdict AGREE · confidence high · current affairs no

**Question.** Which of the following countries is not a member of the Commonwealth of Nations?

- (a) Austria **← keyed**
- (b) Australia
- (c) Canada
- (d) New Zealand
- (e) India

**Short explanation.** The Commonwealth of Nations is a voluntary association of 56 countries, mostly former parts of the British Empire. Austria, a central European country that was never under British rule, is not a member.

**Why the other options are wrong**

- (b) Australia is a Commonwealth member.
- (c) Canada is a Commonwealth member.
- (d) New Zealand is a Commonwealth member.
- (e) India is a Commonwealth member; it became a republic in 1950 but stayed in the association.

**Common traps**

- Reading 'Austria' as 'Australia' in a hurry.

---

### S19. 2026 Q43 · general-knowledge · Mountain ranges and peaks

`977fc7d2-9209-41a9-b086-aa58f10c4ae9` · verdict DISPUTED · confidence medium · current affairs no

**Question.** With reference to the Aravalli Range, consider the following statements: 1. The Luni River originates from the Aravalli Range. 2. Guru Shikhar is the highest peak of the Aravalli Range. 3. Sambhar Lake is a wetland located in the Aravalli Range. Which of the statements given above is/are correct?

- (a) 1 and 2 only **← proposed**
- (b) 2 and 3 only
- (c) 1 and 3 only
- (d) 1, 2 and 3
- (e) 1 only **← keyed**

**Short explanation.** Statements 1 and 2 are correct: the Luni rises in the Aravalli hills near Ajmer, and Guru Shikhar at Mount Abu, about 1,722 metres, is the Aravalli Range's highest peak. The key '1 only' wrongly rejects statement 2.

**Why the other options are wrong**

- (b) Leaves out statement 1; the Luni does rise in the Aravalli hills near Ajmer.
- (c) Leaves out statement 2, which is correct; statement 3 is doubtful at best.
- (d) Rests on statement 3, which is doubtful: Sambhar Lake lies in a basin east of the main Aravalli ridge rather than in the range itself.
- (e) Rejects statement 2, but Guru Shikhar is the highest peak of the Aravalli Range.

**Common traps**

- Thinking Mount Abu's Guru Shikhar belongs to a different range because it stands apart at the south-western end; it is the Aravalli's highest point.

**Key note.** The key '1 only' cannot stand, because statement 2 (Guru Shikhar is the highest Aravalli peak) is a standard, correct fact. Statement 1 is also correct. Statement 3 is borderline: Sambhar Lake is a Ramsar wetland in the Aravalli region but lies in a basin east of the range; if it is read as 'in the Aravalli Range', option d (all three) would be the answer instead. Option a, 1 and 2 only, is proposed as the strongest reading.

---

### S20. 2026 Q50 · general-knowledge · Transport corridors and ports

`cbaa3783-ccfe-4e0b-a8b3-204aad07c090` · verdict AGREE · confidence high · current affairs no

**Question.** Chabahar Port is located in which country?

- (a) Iran **← keyed**
- (b) Oman
- (c) United Arab Emirates
- (d) Qatar
- (e) Saudi Arabia

**Short explanation.** Chabahar Port is on the Gulf of Oman coast in Iran's Sistan-Baluchestan province. India operates its Shahid Beheshti terminal, which gives India a route to Afghanistan and Central Asia that bypasses Pakistan.

**Why the other options are wrong**

- (b) Oman has its own ports such as Duqm and Muscat; Chabahar is on the Iranian side of the Gulf of Oman.
- (c) Not the country where Chabahar is located.
- (d) Not the country where Chabahar is located.
- (e) Not the country where Chabahar is located.

**Common traps**

- Confusing Chabahar (Iran, India-backed) with Gwadar (Pakistan, China-backed), about 170 km apart on the same coast.
