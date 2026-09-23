# IFSCA Grade A — Explanation Draft: Review Notes (EXPL-02)

Worksheet: `workbench/worksheets/IFSCA-EXPLANATIONS-DRAFT.json` — 362 rows, one per verified IFSCA Grade A question
in `workbench/sources/ifsca-explanations-input.json`. Every row is authored from subject knowledge and the question's own
text (plus the shared passage, puzzle premise or data table for the 53 set-based questions). No text is extracted from any
third-party source. Nothing here is reviewed.

Changes from EXPL-01 (SEBI): a `current_affairs` flag with its own treatment (§2); wrong-step rationales on numerical
distractors (§3); `final_answer_option_id` emitted on every AGREE row (§1); a seeded human-readable sample at the end (§10).

## 1. Key verdicts

| Verdict | Count | `final_answer_option_id` |
|---|---|---|
| AGREE | 345 | set = input `correct_option_id` |
| DISPUTED | 0 | null — awaits a human key decision |
| AMBIGUOUS | 16 | null — awaits a human key decision |
| UNANSWERABLE | 1 | null — awaits a human key decision |
| **Total** | **362** | **345 set** |

### 1.1 DISPUTED — the keyed answer is, in my judgement, wrong

None.

### 1.2 AMBIGUOUS — more than one option is defensible, or the data is inconsistent

#### 2023 Q3 · pension-sector · `b5297708-48ff-416b-9eac-7896e0d9be86`

**Stem.** The Central Government had introduced the National Pension System (NPS) with effect from January 1, 2004 (except for armed forces). Pension Fund Regulatory and Development Authority (PFRDA), the regulatory body for NPS, has appointed _________________ as Central Recordkeeping Agency (CRA) for National Pension System. (Topic- National Pension Scheme)

- **Keyed option:** (b) Protean eGov Technologies Limited
- **Reason.** Options a (NSDL e-Governance Infrastructure Ltd) and b (Protean eGov Technologies Ltd) are the same entity before and after its 2021 rename, so both are defensible; the original appointment was made in the NSDL e-Gov name. Option d is also arguably defensible, since PFRDA registered Karvy Computershare (now KFin Technologies) as a second CRA.

#### 2023 Q6 · general-intelligence-reasoning · `649b73c0-79e6-4907-88fd-feb22e5379fd`

**Stem.** Who among the following person stays immediately above N?

- **Keyed option:** (d) The one who stays west of Y
- **Reason.** The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. With N on Alpha 1 the answer is the Alpha 2 occupant, which is option d only if Alpha is taken to be west of Beta (never stated); with N on Alpha 5 nobody is above N and option e holds. Competing options: d and e.

#### 2023 Q7 · general-intelligence-reasoning · `da42d118-aaaa-4815-ac8a-df9dc904be2b`

**Stem.** On which of the following floor and flat does P stay?

- **Keyed option:** (a) Flat Beta, floor 3
- **Reason.** The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. O and P are adjacent and both below S in either assignment, so P can be on Beta 3 (option a) or Alpha 2 (option b).

#### 2023 Q8 · general-intelligence-reasoning · `e3d8429c-66bf-465d-9991-5d94a413efb0`

**Stem.** Four of the following five are alike in a certain way as per the given arrangement and hence form a group. Find the one who doesn’t belong to that group.

- **Keyed option:** (d) P
- **Reason.** The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. With P on Beta 3, P is the only one in Flat Beta (d), but X is the only one on an even floor (4) while Q, N, Z, P are on odd floors (e); with P on Alpha 2 all five are in Flat Alpha. Competing options: d and e.

#### 2023 Q9 · general-intelligence-reasoning · `33f5bc51-298d-4b27-80e5-90e72ec8af26`

**Stem.** What is the position of Z with respect to N?

- **Keyed option:** (a) Two floors above
- **Reason.** The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. N on Alpha 1 gives 'two floors above' (a); N on Alpha 5 gives 'two floors below', which only option e (None of these) covers. Competing options: a and e.

#### 2023 Q10 · general-intelligence-reasoning · `0dfb0389-494f-4b88-bbd0-04d26192a566`

**Stem.** How many floors are between Q and O?

- **Keyed option:** (c) two
- **Reason.** The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. Q5/O2 gives two floors between (c); Q5/O3 or Q1/O3 gives one (a); Q1/O2 gives none, the same as between Y (2) and R (1), which is option e. Competing options: a, c and e.

#### 2024 Q8 · general-intelligence-reasoning · `ced3a18c-7c15-4395-8efb-0e684aa9730e`

**Stem.** How many persons sit between M and H?

- **Keyed option:** (c) Four
- **Reason.** The premises allow two arrangements, E K M V R G A H (used by the key) and K E V M G R H A (zero persons left of K and right of A). E K M V R G A H gives four between M and H (c); K E V M G R H A gives two, G and R (b). Competing options: b and c.

#### 2024 Q9 · general-intelligence-reasoning · `66c297b8-70e0-4df7-9cf5-7abe340f5e0e`

**Stem.** Which among the following is the right combination of persons sitting at the left and right end of the respectively?

- **Keyed option:** (d) E, H
- **Reason.** The premises allow two arrangements, E K M V R G A H (used by the key) and K E V M G R H A (zero persons left of K and right of A). E K M V R G A H gives E, H (d); K E V M G R H A gives K, A, which only 'None of these' (e) covers. Competing options: d and e.

#### 2024 Q22 · finance · `e78ace07-4078-428b-a92d-add1421ba2ab`

**Stem.** What type of contract that gives obligation and is commonly used between two counterparties to trade gold at a specified price on a future date?

- **Keyed option:** (d) Futures
- **Reason.** Forwards (b) and futures (d) both fit. Each creates an obligation to trade gold at a fixed price on a future date, and 'between two counterparties' describes the bilateral OTC forward at least as well as an exchange-traded future. The stem does not mention standardisation or exchange trading, which would single out futures.

#### 2025 Q4 · costing · `26ee28d2-28eb-4f6f-8140-a9a6c59b22b7`

**Stem.** Which of the following is best suited for a bakery that produces biscuits in high volume?

- **Keyed option:** (c) Process Costing
- **Reason.** Options (c) Process Costing and (e) Batch Costing are both defensible: the key relies on 'high volume', but ICAI and most Indian costing texts list biscuit manufacturing as the standard example of batch costing.

#### 2025 Q5 · financial-awareness · `abe318b3-6a80-48a7-b824-1c461d28c1ce`

**Stem.** Which of the following schemes targets the unorganised sector?

- **Keyed option:** (d) Both A and C
- **Reason.** Options d (A and C) and e (B and C) are both defensible: PM Shram Yogi Maandhan is explicitly a pension scheme for unorganised workers, so excluding it (key d) has no basis, and APY equally targets the unorganised sector. No option offers all three.

#### 2025 Q7 · commerce-accountancy · `ef002276-c10b-4f2a-8a74-dc21156f629c`

**Stem.** As per AS-11, the profit or loss arising in the Foreign Currency Monetary Item Translation Difference Account (FCMITDA) is transferred to ______.

- **Keyed option:** (e) Reserves and Surplus
- **Reason.** Options (a) Profit and Loss Account and (e) Reserves and Surplus are both defensible: para 46A amortises the FCMITDA balance to the Statement of Profit and Loss over the item's remaining life, while the unamortised balance is presented under Reserves and Surplus. 'Transferred to' fits the amortisation better, 'shown under' the key.

#### 2025 Q11 · financial-awareness · `2f5f8353-833d-4f71-874b-8df5525e7fd8`

**Stem.** The SMILE Initiative (Support for Marginalized Individuals for Livelihood and Enterprise) is funded by which of the following organization?

- **Keyed option:** (a) Asian Development Bank
- **Reason.** Options a and e compete. The stem's expansion (Support for Marginalized Individuals for Livelihood and Enterprise) is the MoSJE scheme funded by the Union Government, making e (None of the above) correct as written; the keyed ADB funds the logistics programme also called SMILE. The setter appears to have mixed up the two acronyms.

#### 2025 Q13 · general-intelligence-reasoning · `13452ac5-49dd-4413-a0a1-2453e00a4775`

**Stem.** The number of persons who have meeting between O and P is the same as between____ and ___?

- **Keyed option:** (a) R and S
- **Reason.** Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. O-P has one person between; so do R-S (P), U-Q (N), T-M (V) and P-U (S). Competing options: a, b, c and e.

#### 2025 Q16 · general-intelligence-reasoning · `ab69edb7-2254-411b-8352-3ca7b7ba6220`

**Stem.** Which of the following statements is correct?

- **Keyed option:** (c) V and M have the meeting in the same month
- **Reason.** Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. On that order statements a (O and P on the 9th), b (N on 26 June) and c (V and M in September) are all true, while d is false and so e fails. Competing options: a, b and c.

#### 2025 Q23 · financial-awareness · `2ebee501-ad8d-441e-a172-3a69278efe7d`

**Stem.** Which of the following co-working space company in India successfully launched its Initial Public Offering (IPO) in July 2025?

- **Keyed option:** (d) Smartworks
- **Reason.** Options b and d are both correct: Smartworks (key d) opened its IPO around 10 July 2025, and IndiQube Spaces (b) opened its IPO around 23 July 2025. Both were co-working companies that launched IPOs in July 2025.

### 1.3 UNANSWERABLE — cannot be answered as written

#### 2025 Q15 · general-intelligence-reasoning · `ce0272eb-49ae-4e1e-bfba-5a7168c211d8`

**Stem.** Four of the following five are alike in a certain way and hence form a group. Find the one that doesn't belong to that group.

- **Keyed option:** (d) N
- **Reason.** Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. No attribute of that order (date, month, month length, position) groups P, Q, M, R apart from N, and no arrangement matching all the keyed answers of this set satisfies the premises, so the set appears to be built on a different arrangement.

## 2. Current-affairs questions

Classified by one test: could a candidate reason to the answer, or only recall it? `current_affairs = yes` rows carry the
durable context (what the institution, index or instrument is) with the dated fact stated once; option rationales on
arbitrary figures or names say so in one line instead of inventing distinctions; traps appear only where a genuinely
confusable neighbour exists.

| Subject | current_affairs = yes | no | Total |
|---|---|---|---|
| financial-awareness | 75 | 17 | 92 |
| finance | 6 | 61 | 67 |
| quantitative-aptitude | 0 | 61 | 61 |
| general-intelligence-reasoning | 0 | 46 | 46 |
| english-language | 0 | 20 | 20 |
| pension-sector | 2 | 15 | 17 |
| insurance | 0 | 17 | 17 |
| ifsca-gift-city | 3 | 11 | 14 |
| costing | 0 | 12 | 12 |
| management | 0 | 8 | 8 |
| commerce-accountancy | 0 | 8 | 8 |
| **Total** | **86** | **276** | **362** |

On the 86 current-affairs rows: `common_traps` populated on 39, `explanation_text` on 1.

## 3. Numerical distractor rationales

105 rows carry `solution_steps` (numericals and derivation-type reasoning); they hold 407 wrong-option
rationales. Each numerical distractor was run through a python brute-force over the question's own numbers and
intermediates, plus a fixed slip list (omitted step, intermediate given as answer, wrong percentage base, simple vs
compound, swapped ratio terms, upstream/downstream, per-unit vs total, un-doubled DI average, adjacent series term,
the other person or product).

- **247** rationales name a wrong step or say what the solved arrangement actually gives.
- **160** are distractors no plausible slip reproduces. They do not use a bare 'does not follow' line; each states
  the value the working actually gives, e.g. "No likely slip gives 70; the working gives 64."
- **0** bare generic lines remain.

Most arbitrary distractors sit in quantitative-aptitude approximation, number-series and caselet items, where the
setter spaces wrong options around the key (often 10 or 100 apart) rather than building them from a slip. Looser
"close to the rounding" matches were rejected as coincidences, not steps a candidate would take.

## 4. Tag defects (flagged, not fixed)

`tag_suspect = yes` on 18 rows. No retagging has been done.

| Year/Q | Subject | Current `topic_name` | Question | Suggested topic |
|---|---|---|---|---|
| 2023 Q2 | pension-sector | Asset classes E, C, G and A | What is the maximum investment in equity allowed under the Atal Pension Yojana (APY) gu... | Topic should be Atal Pension Yojana (investment pattern). The question is about APY's prescribed equity cap, not the E/C/G/A asset-class choice available to NPS subscribers. |
| 2023 Q3 | finance | Clearing corporations and settlement | What is the Minimum Lock-in period of the medium- and long-term government deposits und... | Topic should be Gold Monetization Scheme / bullion. The question tests GMS deposit rules, not clearing corporations or settlement. |
| 2023 Q4 | finance | Clearing corporations and settlement | Banks must maintain a stock of gold that is at least equal to the amount of gold that i... | Topic should be Gold Monetization Scheme / bullion. The question tests GMS deposit rules, not clearing corporations or settlement. |
| 2023 Q5 | finance | Clearing corporations and settlement | Which of the following entities can participate in the auction of gold under the Gold M... | Topic should be Gold Monetization Scheme / bullion. The question tests GMS gold auctions, not clearing corporations or settlement. |
| 2023 Q6 | ifsca-gift-city | IFSCA Act 2019 — establishment and composition | According to the International Financial Services Centres Authority Act of 2019, which ... | Topic should be IFSCA Act 2019 — definitions (financial product, financial service). The question tests the Section 3 definition, not how the Authority is established or composed. |
| 2024 Q3 | financial-awareness | Current events of national importance | In India, a Super Senior Citizen is defined as an individual resident who is of what ag... | Topic should be Direct taxation (income tax slabs and assessee categories). The question tests a standing Income-tax Act age classification, not a current event. |
| 2024 Q10 | insurance | Claims management | According to the Insurance Regulatory and Development Authority of India (IRDAI) guidel... | Topic should be Grievance redressal / policyholder protection. The question tests the insurer's complaint-resolution timeline, not claims handling. |
| 2024 Q13 | finance | Digital Public Infrastructure and India Stack | ________ refers to a platform that facilitates IT-related services to connect buyers an... | Topic should be E-commerce models / FDI in e-commerce. The question tests the marketplace-versus-inventory definition, not Digital Public Infrastructure or India Stack. |
| 2024 Q23 | finance | Clearing corporations and settlement | What is the full form of IIBX? | Topic should be Bullion exchange / IFSC market infrastructure. The question tests what IIBX stands for, not clearing corporations or settlement. |
| 2025 Q3 | financial-awareness | Budget concepts and approach | In the context of the prudential framework followed by entities regulated by IFSCA, the... | Topic should be banking prudential norms / credit-risk provisioning (ECL). The question tests loan-loss accounting under the prudential framework, not budget concepts. |
| 2025 Q3 | finance | Forwards vs futures | The value of a derivative is derived from the value of _____. | Topic should be Derivatives basics and definition. The question tests what a derivative is, not the difference between forwards and futures. |
| 2025 Q8 | finance | RBI Act 1934 — constitution, note issue, functions | The RBI subsidiary created specifically for its IT and cyber-security needs is: | Topic should be RBI subsidiaries and associated institutions. The question tests which RBI subsidiary does IT and cyber security, not the RBI Act 1934. |
| 2025 Q10 | finance | Credit rating agencies and sovereign ratings | The sentiment index used for Micro and Small Enterprises in India is: | Topic should be MSME finance and economic indicators. The question tests an MSE sentiment index, not credit rating agencies or sovereign ratings; CRISIL is only its co-sponsor. |
| 2025 Q10 | finance | RBI, SEBI, IRDAI, PFRDA — mandate boundaries | What is the primary purpose of the Audit Committee? | Topic should be Corporate governance and board committees. The audit committee is a company-law and LODR subject, not about the mandate boundaries between RBI, SEBI, IRDAI and PFRDA. |
| 2025 Q12 | finance | Digital Public Infrastructure and India Stack | In zero-trust network architecture, which statement summarises the core idea? | Topic should be Cyber security (zero-trust architecture). The question tests a network security principle, not Digital Public Infrastructure or India Stack. |
| 2025 Q14 | finance | Digital Public Infrastructure and India Stack | To improve financial inclusion, expand opportunities for innovation and enhance efficie... | Topic should be Artificial intelligence and emerging technology in finance. The question is about AI in financial services, not Digital Public Infrastructure or India Stack. |
| 2025 Q18 | finance | RBI, SEBI, IRDAI, PFRDA — mandate boundaries | Under the IFSCA (Fund Management) Regulations, a Fund Management Entity (FME) operating... | Topic should be IFSCA fund management regulations. The question tests an IFSCA FME net-worth requirement, not the mandate boundaries between RBI, SEBI, IRDAI and PFRDA. |
| 2025 Q21 | financial-awareness | Current events of national importance | Consider the following statements regarding the basic functions and identity of a Non-B... | Topic should be banking and NBFC regulation. The question tests the statutory definition and principal-business test for NBFCs, not a current event. |

## 5. Low-confidence rows

- **2023 Q1 · pension-sector · `8b886eb7-f6c1-43fb-be44-bd12a8c9d1cb`** — Under NPS, how many Pension funds (PFs) other than the government sector are registered with PFRDA? (Topic- National Pension Scheme)
  - Keyed: (e) 10
  - Reason: Registered PF count changes as PFRDA licenses new managers (e.g. Tata, Axis/Max Life, DSP registered in 2022-24); the keyed 10 cannot be corroborated for the exact exam date, and the count depends on whether SBI, LIC and UTI are included.
- **2023 Q2 · financial-awareness · `d20d52d3-62b1-4b9a-b400-d286a59acba8`** — How many complaints against companies and market intermediaries received through SCORES platform was disposed of in February according to the data provided b...
  - Keyed: (a) 2672
  - Reason: Monthly SCORES disposal count accepted from the key; the specific figure cannot be corroborated from knowledge.
- **2023 Q5 · financial-awareness · `20fb8bc4-b04c-4c4e-b930-3e2edb473c93`** — How much liquidity has been infused into the banking system by Reserve Bank of India (RBI) via the 14-day Variable Repo Rate (VRR) auction amid tightening li...
  - Keyed: (b) Rs.82,650 crore
  - Reason: Auction amount accepted from the key; the exact figure and auction date cannot be corroborated from knowledge.
- **2023 Q6 · general-intelligence-reasoning · `649b73c0-79e6-4907-88fd-feb22e5379fd`** — Who among the following person stays immediately above N?
  - Keyed: (d) The one who stays west of Y
  - Reason: The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. With N on Alpha 1 the answer is the Alpha 2 occupant, which is option d only if Alpha is taken to be west of Beta (never stated); with N on Alpha 5 nobody is above N and option e holds. Competing options: d and e.
- **2023 Q7 · general-intelligence-reasoning · `da42d118-aaaa-4815-ac8a-df9dc904be2b`** — On which of the following floor and flat does P stay?
  - Keyed: (a) Flat Beta, floor 3
  - Reason: The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. O and P are adjacent and both below S in either assignment, so P can be on Beta 3 (option a) or Alpha 2 (option b).
- **2023 Q8 · general-intelligence-reasoning · `e3d8429c-66bf-465d-9991-5d94a413efb0`** — Four of the following five are alike in a certain way as per the given arrangement and hence form a group. Find the one who doesn’t belong to that group.
  - Keyed: (d) P
  - Reason: The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. With P on Beta 3, P is the only one in Flat Beta (d), but X is the only one on an even floor (4) while Q, N, Z, P are on odd floors (e); with P on Alpha 2 all five are in Flat Alpha. Competing options: d and e.
- **2023 Q9 · general-intelligence-reasoning · `33f5bc51-298d-4b27-80e5-90e72ec8af26`** — What is the position of Z with respect to N?
  - Keyed: (a) Two floors above
  - Reason: The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. N on Alpha 1 gives 'two floors above' (a); N on Alpha 5 gives 'two floors below', which only option e (None of these) covers. Competing options: a and e.
- **2023 Q10 · general-intelligence-reasoning · `0dfb0389-494f-4b88-bbd0-04d26192a566`** — How many floors are between Q and O?
  - Keyed: (c) two
  - Reason: The stimulus leaves N/Q (Alpha 1 vs Alpha 5) and O/P (Alpha 2 vs Beta 3) interchangeable; all four arrangements satisfy every premise. Q5/O2 gives two floors between (c); Q5/O3 or Q1/O3 gives one (a); Q1/O2 gives none, the same as between Y (2) and R (1), which is option e. Competing options: a, c and e.
- **2024 Q2 · finance · `2f2353e1-e67a-45ff-9247-bdb86d66960a`** — What is the minimum size of a futures contract that can be made public for individuals on exchanges in India as of 2024?
  - Keyed: (d) ₹5 lakhs
  - Reason: Low confidence: 'as of 2024' spans both ₹5 lakh (until 19 November 2024) and ₹15 lakh (from 20 November 2024). The key is right only if the question means the rule in force before the late-2024 revision.
- **2024 Q8 · general-intelligence-reasoning · `ced3a18c-7c15-4395-8efb-0e684aa9730e`** — How many persons sit between M and H?
  - Keyed: (c) Four
  - Reason: The premises allow two arrangements, E K M V R G A H (used by the key) and K E V M G R H A (zero persons left of K and right of A). E K M V R G A H gives four between M and H (c); K E V M G R H A gives two, G and R (b). Competing options: b and c.
- **2024 Q9 · general-intelligence-reasoning · `66c297b8-70e0-4df7-9cf5-7abe340f5e0e`** — Which among the following is the right combination of persons sitting at the left and right end of the respectively?
  - Keyed: (d) E, H
  - Reason: The premises allow two arrangements, E K M V R G A H (used by the key) and K E V M G R H A (zero persons left of K and right of A). E K M V R G A H gives E, H (d); K E V M G R H A gives K, A, which only 'None of these' (e) covers. Competing options: d and e.
- **2024 Q12 · insurance · `d4d2050b-52cc-4aa5-9018-e4a1dec3b02c`** — What is the term used for the basis of settlement of loss when the insurance cover is for an amount below the actual value of the item?
  - Keyed: (d) Market Value
  - Reason: The stem describes under-insurance, whose settlement consequence is the average (pro-rata) condition, which is not offered. Market value is accepted as the indemnity valuation basis against which under-insurance is measured, but the wording is loose.
- **2024 Q13 · financial-awareness · `f95cc160-a98a-4256-8a94-cda6d9e760e1`** — What percentage of its stake does State Bank of India (SBI) aim to sell in Yes Bank by the end of March 2024?
  - Keyed: (c) 24%
  - Reason: Accepted from the key but doubtful as framed: about 24% was roughly SBI's total holding after dilution, and the 'by end of March 2024' deadline cannot be corroborated.
- **2024 Q14 · financial-awareness · `b01c84e2-8a2f-4e31-b32f-f360b3f6c4d5`** — What is the annual fee that broker-dealers need to pay to IFSCA, as per the June 2024 clarificatory circular, if they access global markets directly through ...
  - Keyed: (b) USD 1,000
  - Reason: Fee amount accepted from the key; the specific figure in the June 2024 IFSCA circular cannot be corroborated from knowledge.
- **2024 Q24 · financial-awareness · `218fc15f-296c-4a30-8d5d-0f3ab10e62c3`** — How many registered International Insurance Offices (IIOs) are there in the Life Segment after IFSCA granted Certificate of Registration (CoR) to Canara HSBC...
  - Keyed: (b) 5
  - Reason: The count of five is taken from the key; the specific IFSCA figure for June 2024 could not be independently corroborated.
- **2025 Q2 · costing · `f0843034-d174-4196-87bc-594c9b9749cd`** — Both BPR and PI were introduced in 1999. While BPR (Business Process Reengineering) focuses on ________ of the processes, Process Innovation focuses on renov...
  - Keyed: (c) Amend
  - Reason: Loosely drafted item: BPR (Hammer and Champy) and Process Innovation (Davenport) date from the early 1990s, not 1999, and standard theory calls BPR radical redesign. 'Amend' is accepted as the examiner's intended word.
- **2025 Q4 · financial-awareness · `b4012303-2060-4e01-b6e5-947e17a24c69`** — FICCI, under the aegis of its Centre for Sustainability Leadership, successfully organised the 15th India Climate Policy and Business Conclave focused on cli...
  - Keyed: (b) Hyderabad
  - Reason: The host city of the 15th edition is accepted from the key; it could not be independently corroborated.
- **2025 Q5 · financial-awareness · `71f17347-cf8b-4309-8479-01ab99578096`** — As the new Goods and Services Tax (GST) rates took effect on September 22, digital payments surged to around __________, nearly 10 times the previous day, ac...
  - Keyed: (e) ₹11 trillion
  - Reason: The ₹11 trillion figure is accepted from the key; the specific daily RBI value could not be independently corroborated.
- **2025 Q9 · financial-awareness · `03241735-4b36-4b4b-afc0-07c3540b3b31`** — The United Nations Secretary-General hosted the first Biennial Summit for a sustainable, inclusive, and resilient global economy. In which city was this summ...
  - Keyed: (d) New York
  - Reason: The venue of the first Biennial Summit is accepted from the key; it could not be independently corroborated.
- **2025 Q11 · financial-awareness · `2f5f8353-833d-4f71-874b-8df5525e7fd8`** — The SMILE Initiative (Support for Marginalized Individuals for Livelihood and Enterprise) is funded by which of the following organization?
  - Keyed: (a) Asian Development Bank
  - Reason: Options a and e compete. The stem's expansion (Support for Marginalized Individuals for Livelihood and Enterprise) is the MoSJE scheme funded by the Union Government, making e (None of the above) correct as written; the keyed ADB funds the logistics programme also called SMILE. The setter appears to have mixed up the two acronyms.
- **2025 Q13 · general-intelligence-reasoning · `13452ac5-49dd-4413-a0a1-2453e00a4775`** — The number of persons who have meeting between O and P is the same as between____ and ___?
  - Keyed: (a) R and S
  - Reason: Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. O-P has one person between; so do R-S (P), U-Q (N), T-M (V) and P-U (S). Competing options: a, b, c and e.
- **2025 Q15 · general-intelligence-reasoning · `ce0272eb-49ae-4e1e-bfba-5a7168c211d8`** — Four of the following five are alike in a certain way and hence form a group. Find the one that doesn't belong to that group.
  - Keyed: (d) N
  - Reason: Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. No attribute of that order (date, month, month length, position) groups P, Q, M, R apart from N, and no arrangement matching all the keyed answers of this set satisfies the premises, so the set appears to be built on a different arrangement.
- **2025 Q16 · general-intelligence-reasoning · `ab69edb7-2254-411b-8352-3ca7b7ba6220`** — Which of the following statements is correct?
  - Keyed: (c) V and M have the meeting in the same month
  - Reason: Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. On that order statements a (O and P on the 9th), b (N on 26 June) and c (V and M in September) are all true, while d is false and so e fails. Competing options: a, b and c.

| Confidence | Count |
|---|---|
| high | 268 |
| medium | 71 |
| low | 23 |

Medium rows are not listed; where a specific reservation exists it is in that row's `key_note`.

## 6. Field-population counts

| Field | Rows populated | Of 362 |
|---|---|---|
| `short_explanation` | 362 | 100% |
| `explanation_text` | 50 | 14% |
| `solution_steps` | 105 | 29% |
| `formula_used` | 70 | 19% |
| `common_traps` | 245 | 68% |
| `key_note` | 87 | 24% |
| `final_answer_option_id` | 345 | 95% |
| `option_rationales` (entries, not rows) | 1427 | — |

35 rationale entries are the fixed filler line ("Filler option; a correct answer is present.").

## 7. Validation

Enforced by the build script; the worksheet is written only when every check passes.

- **Row count:** 362 rows, one per input question.
- **Uniqueness:** 362 distinct `question_id` values.
- **Completeness:** the worksheet and input `question_id` sets are identical; `year`, `question_number`, `subject_slug`,
  `topic_name` are copied unchanged.
- **Option-rationale integrity:** 1427 entries, each keyed to an `option_id` and `label` on that question, no
  duplicates. Wrong options across the corpus: 1448. Every wrong option on an AGREE row is covered; the only gaps
  are options this draft argues are correct or defensible (proposed option on DISPUTED, co-defensible options on AMBIGUOUS).
- **No contradiction on AGREE rows:** no AGREE row carries a rationale against its own keyed option.
- **final_answer_option_id:** set on all 345 AGREE rows and equal to the input `correct_option_id`; null on every
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
  `final_answer_option_id` is null — the 17 non-AGREE rows cannot be verified until the key is resolved.
- Editing learner-facing fields on a verified row downgrades it to `needs_correction`; the apply step should touch only
  `pending` rows.

## 9. Scope

IFSCA Grade A only — the 362 questions in the input file. No database writes, no migrations, no retagging, no change to
any question or option.

## 10. Ready-to-read sample (20 rows)

Chosen with `random.Random(20260923).sample(rows, 20)` over the worksheet rows in file order, then sorted by year, subject
and question number for reading. Re-running the same call on the same file yields the same 20.

---

### S1. 2023 Q8 · financial-awareness · Themes and findings of the latest Economic Survey

`22a5c76b-99c8-4e97-b9a6-be7aaf5180b8` · verdict AGREE · confidence medium · current affairs yes

**Question.** The average monthly gross GST collection has increased from crore in _________ FY18 to ₹1.49 lakh crore in FY23 (Topic- Latest Economic Survey)

- (a) ₹0.65 lakh crore
- (b) ₹0.70 lakh crore
- (c) ₹0.75 lakh crore
- (d) ₹0.80 lakh crore
- (e) ₹0.90 lakh crore **← keyed**

**Short explanation.** GST replaced multiple indirect taxes from 1 July 2017, so FY18 covers only nine months of collections. The Economic Survey 2022-23 noted that average monthly gross GST collection rose from ₹0.90 lakh crore in FY18 to ₹1.49 lakh crore in FY23.

**Why the other options are wrong**

- (a) Arbitrary alternative figure; the Survey cited ₹0.90 lakh crore for FY18.
- (b) Arbitrary alternative figure; the Survey cited ₹0.90 lakh crore for FY18.
- (c) Arbitrary alternative figure; the Survey cited ₹0.90 lakh crore for FY18.
- (d) Arbitrary alternative figure; the Survey cited ₹0.90 lakh crore for FY18.

**Key note.** Stem is garbled (the blank sits after 'FY18' while the word 'crore' precedes it) but the intended fill is clear.

---

### S2. 2023 Q3 · ifsca-gift-city · IFSCA Banking Regulations

`90f7ca25-b20b-49f9-9036-5d9bd0a71bb1` · verdict AGREE · confidence medium · current affairs no

**Question.** What is the minimum capital requirement of an IFSC Banking Unit (IBU)? (Topic- IFSCA Regulations - Banking, Bullion, Capital Market and Insurance)

- (a) USD 1 million
- (b) USD 5 million
- (c) USD 10 million
- (d) USD 15 million
- (e) USD 20 million **← keyed**

**Short explanation.** Under the IBU scheme, the parent bank must give each IFSC Banking Unit a minimum capital of US$ 20 million or its equivalent in foreign currency.

**Why the other options are wrong**

- (a) Arbitrary lower figure; the stipulated minimum is US$ 20 million.
- (b) Arbitrary lower figure; the stipulated minimum is US$ 20 million.
- (c) Arbitrary lower figure; the stipulated minimum is US$ 20 million.
- (d) Arbitrary lower figure; the stipulated minimum is US$ 20 million.

**Key note.** Figure matches the RBI 2015 IBU scheme; IFSCA's current banking handbook may frame capital differently.

---

### S3. 2023 Q6 · ifsca-gift-city · IFSCA Act 2019 — establishment and composition

`4115f49f-0e0c-46a3-9a7b-65641924e207` · verdict AGREE · confidence high · current affairs no

**Question.** According to the International Financial Services Centres Authority Act of 2019, which of the following options is not classified as a financial product? (Topic- IFSCA Act)

- (a) Foreign Exchange Spot Contract **← keyed**
- (b) Securities
- (c) Contracts of Insurance
- (d) Deposits
- (e) Credit Arrangements

**Short explanation.** Section 3(1)(e) of the IFSCA Act, 2019 defines financial products to include securities, contracts of insurance, deposits and credit arrangements, and foreign-currency contracts other than those settled immediately. A spot foreign-exchange contract falls under that exception.

**Explanation.** The definition covers foreign currency contracts 'other than contracts to exchange one currency (whether Indian or not) for another which are to be settled immediately'. Spot FX is therefore carved out, while forwards and other FX derivatives remain financial products. The Central Government may also notify further products.

**Why the other options are wrong**

- (b) Securities are expressly listed as a financial product.
- (c) Contracts of insurance are expressly listed.
- (d) Deposits are expressly listed.
- (e) Credit arrangements are expressly listed.

**Common traps**

- Candidates see 'foreign currency contracts' in the definition and assume all FX contracts qualify; the immediate-settlement carve-out removes spot deals.

**Tag note.** Topic should be IFSCA Act 2019 — definitions (financial product, financial service). The question tests the Section 3 definition, not how the Authority is established or composed.

---

### S4. 2023 Q3 · pension-sector · Central Recordkeeping Agency

`b5297708-48ff-416b-9eac-7896e0d9be86` · verdict AMBIGUOUS · confidence medium · current affairs yes

**Question.** The Central Government had introduced the National Pension System (NPS) with effect from January 1, 2004 (except for armed forces). Pension Fund Regulatory and Development Authority (PFRDA), the regulatory body for NPS, has appointed _________________ as Central Recordkeeping Agency (CRA) for National Pension System. (Topic- National Pension Scheme)

- (a) NSDL e-Governance Infrastructure Limited (NSDL)
- (b) Protean eGov Technologies Limited **← keyed**
- (c) Central Depository Services (India) Limited (CDSL)
- (d) Karvy Computershare Private Limited
- (e) Both Option A and C

**Short explanation.** A Central Recordkeeping Agency keeps NPS subscriber records, issues PRANs and handles contribution and switch processing. PFRDA's first CRA was NSDL e-Governance Infrastructure Limited, which renamed itself Protean eGov Technologies Limited in 2021, so the two names refer to the same company.

**Explanation.** PFRDA appointed NSDL e-Governance Infrastructure Limited as the first CRA when NPS was set up. In 2021 the company changed its name to Protean eGov Technologies Limited. PFRDA later registered further CRAs, first the Karvy group (now KFin Technologies) and then CAMS, so NPS now has more than one CRA. A question that asks which company 'has been appointed' therefore has more than one valid answer unless it names the original appointment and the era.

**Why the other options are wrong**

- (c) CDSL is a securities depository and is not a PFRDA-appointed CRA for NPS.
- (e) Fails because CDSL (option C) is not a CRA; the combination therefore cannot be correct.

**Common traps**

- Not realising that NSDL e-Gov and Protean are the same company under old and new names.

**Key note.** Options a (NSDL e-Governance Infrastructure Ltd) and b (Protean eGov Technologies Ltd) are the same entity before and after its 2021 rename, so both are defensible; the original appointment was made in the NSDL e-Gov name. Option d is also arguably defensible, since PFRDA registered Karvy Computershare (now KFin Technologies) as a second CRA.

---

### S5. 2024 Q16 · english-language · Synonyms

`6b9c5d2c-a4c0-4840-bb09-195d59128702` · verdict AGREE · confidence high · current affairs no

**Question.** The committee's decision was met with widespread approval and was seen as a highly commendable move.

- (a) controversial
- (b) admirable **← keyed**
- (c) questionable
- (d) ambiguous
- (e) negligible

**Short explanation.** 'Commendable' means deserving praise; 'admirable' carries the same meaning and fits the 'widespread approval' in the sentence.

**Why the other options are wrong**

- (a) 'Controversial' means causing disagreement, which clashes with widespread approval.
- (c) 'Questionable' means doubtful, close to the opposite of commendable.
- (d) 'Ambiguous' means unclear, unrelated to praise.
- (e) 'Negligible' means too small to matter, not worthy of praise.

---

### S6. 2024 Q24 · english-language · Subject-verb agreement

`80df0d91-7146-4684-9cb0-d134be01bf04` · verdict AGREE · confidence high · current affairs no

**Question.** Neither the manager nor the employees were aware of the changes that was implemented last week.

- (a) Neither the manager
- (b) nor the employees
- (c) were aware
- (d) of the changes
- (e) that was implemented **← keyed**

**Short explanation.** The relative pronoun 'that' refers to 'the changes', which is plural, so it should read 'that were implemented'.

**Why the other options are wrong**

- (a) 'Neither the manager' correctly opens the neither-nor pair.
- (b) 'Nor the employees' is correct; with neither-nor, the verb agrees with the nearer subject, 'employees'.
- (c) 'Were aware' correctly agrees with the nearer plural subject 'employees'.
- (d) 'Of the changes' is correct; 'aware of' is the right preposition.

**Common traps**

- Candidates focus on the neither-nor verb, which is correct here; the error is the second verb, which must agree with the antecedent of 'that'.

---

### S7. 2024 Q7 · finance · FBIL benchmark rates

`b1a5ca4d-8ad5-4680-a6a7-c2b0fadb7b76` · verdict AGREE · confidence high · current affairs no

**Question.** ________ is a voluntary market association for Fixed Income, Money, and Derivatives markets in India.

- (a) Reserve Bank of India (RBI)
- (b) Securities and Exchange Board of India (SEBI)
- (c) Fixed Income Money Market and Derivatives Association of India (FIMMDA) **← keyed**
- (d) National Stock Exchange (NSE)
- (e) Bombay Stock Exchange (BSE)

**Short explanation.** FIMMDA is a voluntary market body of banks, financial institutions and primary dealers for India's fixed income, money and derivatives markets. It sets market conventions and publishes valuation guidance, and it co-promoted FBIL.

**Why the other options are wrong**

- (a) RBI is the statutory central bank and regulator, not a voluntary market association.
- (b) SEBI is the statutory securities regulator, not a voluntary association.
- (d) NSE is a stock exchange, not a voluntary association of fixed income market participants.
- (e) BSE is a stock exchange, not a voluntary association of fixed income market participants.

**Common traps**

- Candidates confuse FIMMDA with FBIL, which it co-promoted and which administers benchmark rates.

---

### S8. 2024 Q3 · financial-awareness · Themes and findings of the latest Economic Survey

`cb4f4795-d582-467f-9a18-895ad0332003` · verdict AGREE · confidence medium · current affairs yes

**Question.** According to the Economic Survey 2023-24, India's equity market capitalization as a percentage of GDP ranks as the ____ largest in the world.

- (a) 3rd
- (b) 4th
- (c) 5th **← keyed**
- (d) 6th
- (e) 7th

**Short explanation.** Market capitalisation to GDP compares the value of listed equities with the size of the economy and indicates stock-market depth. The Economic Survey 2023-24 noted that India's ratio ranked fifth largest in the world.

**Why the other options are wrong**

- (a) Not the rank stated in the Survey.
- (b) Not the rank stated in the Survey.
- (d) Not the rank stated in the Survey.
- (e) Not the rank stated in the Survey.

**Common traps**

- Mixing up rank by ratio to GDP with rank by absolute market capitalisation, a separate league table.

**Key note.** Rank accepted from the key; consistent with recall of the Survey but not independently corroborated.

---

### S9. 2024 Q7 · general-intelligence-reasoning · Linear row — single row, one direction

`d2312a22-1769-45e6-9af9-95e09354e332` · verdict AGREE · confidence medium · current affairs no

**Shared stimulus**

> A, E, G, H, K, M, R and V are sitting in a row that runs from East to West, all facing North, but not necessarily in the same order. V is sitting 2nd to the left of G. Only one person is sitting between V and K. M is sitting beside V. G is sitting 2nd to the left of H. M is sitting second to right of E. The number of persons sitting to the left of K is same as the number of persons sitting to the right of A. R is not sitting at any extreme end.

**Question.** How many persons sit between V and A?

- (a) One
- (b) Two **← keyed**
- (c) Three
- (d) Five
- (e) None

**Short explanation.** In E K M V R G A H, V is seat 4 and A seat 7, so R and G, two persons, sit between them.

**Explanation.** The alternative seating K E V M G R H A puts four persons between V and A, which no option offers, so Two is the only listed answer.

**Why the other options are wrong**

- (a) Two persons (R, G) sit between V and A, not one.
- (c) Three would count A itself.
- (d) Five is not the gap in either valid seating.
- (e) V and A are not adjacent.

**Solution steps**

1. Number seats 1 to 8 from the left (west) end, since all face north.
2. G = V + 2, H = G + 2 = V + 4, and K is two seats from V on the side away from G, so K = V - 2. Hence V is 3 or 4.
3. V = 4: K2, G6, H8; A = 9 - K = 7; M beside V with E two to its left gives M3/E1 (R then takes seat 5) or M5/E3 (R would be left at seat 1, an end, so rejected). Arrangement: E K M V R G A H.
4. V = 3: K1, G5, H7; M must be 4 (M2 would put E off the row), E2; A = 9 - 1 = 8; R takes seat 6. Arrangement: K E V M G R H A, which also satisfies every clue (0 persons left of K, 0 right of A).
5. The answer key uses E K M V R G A H.

**Key note.** The premises allow two arrangements, E K M V R G A H (used by the key) and K E V M G R H A (zero persons left of K and right of A). The alternative gives four, not an option.

---

### S10. 2024 Q3 · ifsca-gift-city · GIFT City ecosystem

`5514f067-3008-42d8-b116-bea23928ac52` · verdict AGREE · confidence high · current affairs no

**Question.** What is the full form of GIFT in GIFT City?

- (a) Gujarat International Financial Trade-City
- (b) Gujarat Investment Finance Trade-City
- (c) Gujarat International Finance Tec-City **← keyed**
- (d) Global International Finance Trade-City
- (e) Global Investment Finance Tec-City

**Short explanation.** GIFT stands for Gujarat International Finance Tec-City, India's first operational smart city and IFSC, at Gandhinagar.

**Why the other options are wrong**

- (a) 'Financial Trade' is wrong; the name is 'Finance Tec'.
- (b) 'Investment' and 'Trade' are both wrong.
- (d) 'Global' replaces 'Gujarat', and 'Trade' replaces 'Tec'.
- (e) 'Global' and 'Investment' are both wrong; only 'Tec-City' matches.

**Common traps**

- 'Tec' (not 'Trade' or 'Tech') is the unusual spelling examiners test.

---

### S11. 2024 Q18 · insurance · Product design

`e46d758f-01cf-4d02-95f8-26ae4c087e39` · verdict AGREE · confidence high · current affairs no

**Question.** What is the lock-in period for Linked Insurance products, during which policy proceeds cannot be paid to policyholders except in case of death or other covered contingencies?

- (a) 3 years
- (b) 4 years
- (c) 5 years **← keyed**
- (d) 6 years
- (e) 10 years

**Short explanation.** IRDAI regulations set a 5-year lock-in for unit-linked insurance products: surrender or maturity proceeds cannot be paid out in the first five years except on death or other covered contingencies.

**Why the other options are wrong**

- (a) 3 years was the lock-in before IRDAI raised it to 5 years in 2010.
- (b) 4 years is not the prescribed lock-in.
- (d) 6 years is not the prescribed lock-in.
- (e) 10 years is not the lock-in; it relates to other product thresholds such as the minimum policy term for some products.

**Common traps**

- Recalling the pre-2010 three-year lock-in.

---

### S12. 2024 Q11 · quantitative-aptitude · Caselet data interpretation

`6eecc4fc-b56d-4d77-9bff-dca2135a2158` · verdict AGREE · confidence high · current affairs no

**Shared stimulus**

> Direction (11-15): Read the following information carefully and answer the questions. Three friends Mayank, Isha and Lalit prepared for an exam to get their dream job. Each dedicated certain hours of time in three domains such as technical, non-technical and general knowledge in a month. Mayank spent 60 hours totally on non-technical preparation which is 30 hours less than the time he spent on technical preparation. The ratio of the number of hours spent by Lalit on technical preparation to the number of hours spent by Mayank on general knowledge is 7: 5. The total number of hours dedicated by Mayank on total is 200 hours which is 56 th of the number of hours dedicated by Isha on total. The number of hours spent by Isha on non-technical preparation is 40 hours more than the number of hours spent by Mayank on general knowledge. The number of hours spent by Isha on technical preparation is 20% more than the number of hours spent by Lalit on same preparation. The ratio of the number of hours spent by Isha and Lalit on general knowledge is 3:2. Three friends spent totally 190 hours on non-technical preparation.

**Question.** How many hours totally did the three friends spend on technical preparation?

- (a) 244 hrs **← keyed**
- (b) 284 hrs
- (c) 254 hrs
- (d) 224 hrs
- (e) None of these

**Short explanation.** Technical hours are Mayank 90, Isha 84 and Lalit 70, totalling 244 hours.

**Why the other options are wrong**

- (b) No likely slip gives 284 hrs; the working gives 90 + 84 + 70 = 244 hrs.
- (c) No likely slip gives 254 hrs; the working gives 90 + 84 + 70 = 244 hrs.
- (d) No likely slip gives 224 hrs; the working gives 90 + 84 + 70 = 244 hrs.
- (e) Filler option; a correct answer is present.

**Solution steps**

1. Mayank: non-technical 60, technical 60 + 30 = 90, total 200, so GK = 50.
2. Lalit technical : Mayank GK = 7 : 5 ⇒ Lalit technical = 70.
3. Mayank's 200 is 5/6 of Isha's total ⇒ Isha total = 240.
4. Isha non-technical = 50 + 40 = 90; Isha technical = 1.2 × 70 = 84; Isha GK = 240 − 90 − 84 = 66.
5. Isha GK : Lalit GK = 3 : 2 ⇒ Lalit GK = 44.
6. Lalit non-technical = 190 − 60 − 90 = 40; Lalit total = 70 + 40 + 44 = 154.
7. Technical total = 90 + 84 + 70 = 244 hours.

**Common traps**

- Reading '56 th' as 56 rather than the fraction 5/6 garbled in transcription.
- Reading Mayank's technical time as 60 − 30 = 30 instead of 60 + 30 = 90.

---

### S13. 2025 Q3 · finance · Forwards vs futures

`a8184f0a-b37e-45a7-b15b-16cbfa95d135` · verdict AGREE · confidence high · current affairs no

**Question.** The value of a derivative is derived from the value of _____.

- (a) Government securities
- (b) Underlying assets **← keyed**
- (c) Exchange rates only
- (d) Interest rates fixed by the RBI
- (e) The issuer’s credit rating

**Short explanation.** A derivative is a contract whose value depends on the price of an underlying asset, which may be a stock, index, commodity, currency, interest rate or bond.

**Why the other options are wrong**

- (a) Government securities are one possible underlying, not the general source of a derivative's value.
- (c) Exchange rates underlie only currency derivatives; 'only' makes this too narrow.
- (d) Interest rates underlie interest rate derivatives, and are not in general fixed by RBI; this is too narrow and inaccurate.
- (e) The issuer's credit rating matters for credit instruments; a derivative's value comes from its underlying.

**Tag note.** Topic should be Derivatives basics and definition. The question tests what a derivative is, not the difference between forwards and futures.

---

### S14. 2025 Q3 · financial-awareness · Demographic trends

`4915b18d-5b91-4dfd-83a4-4795c2804e08` · verdict AGREE · confidence medium · current affairs yes

**Question.** Consider the following statements regarding India’s population peak as per the UN’s “World Population Prospects 2025”: 1. India’s population is projected to peak in 2062. 2. The peak population is expected to be around 1.7 billion. 3. After the peak, India’s population is expected to decline gradually. Which of the following is correct?

- (a) Only Statement 1
- (b) Only Statements 1 and 2
- (c) Only Statements 2 and 3
- (d) Only Statement 3
- (e) All Statements 1, 2 and 3 **← keyed**

**Short explanation.** UN population projections show India, already the world's most populous country, growing for about four more decades. It is projected to peak in the early 2060s at around 1.7 billion and then decline gradually, so all three statements are correct.

**Why the other options are wrong**

- (a) Omits Statements 2 and 3; the projected peak is about 1.7 billion, followed by a gradual decline.
- (b) Omits Statement 3; the projections show a gradual decline after the peak.
- (c) Omits Statement 1; the peak is projected around 2062.
- (d) Omits Statements 1 and 2, which are also part of the projection.

**Key note.** The UN DESA edition carrying these figures is World Population Prospects 2024; the stem's '2025' label appears to conflate it with UNFPA's 2025 report. The facts themselves support the key.

---

### S15. 2025 Q5 · financial-awareness · Insurance and pension schemes

`abe318b3-6a80-48a7-b824-1c461d28c1ce` · verdict AMBIGUOUS · confidence medium · current affairs no

**Question.** Which of the following schemes targets the unorganised sector?

- (a) Atal Pension Yojana (APY)
- (b) Pradhan Mantri Shram Yogi Maandhan
- (c) Laghu Vyapari Maandhan
- (d) Both A and C **← keyed**
- (e) Both B and C

**Short explanation.** All three schemes serve the unorganised sector. APY is aimed chiefly at unorganised-sector workers, PM Shram Yogi Maandhan is a pension scheme for unorganised workers, and the Laghu Vyapari Maandhan (NPS-Traders) covers small traders and self-employed persons outside formal pension cover.

**Why the other options are wrong**

- (a) APY alone is incomplete; the paired options show more than one listed scheme is expected, and several qualify.
- (b) PM-SYM does target unorganised workers, but on its own it is incomplete as more than one scheme qualifies.
- (c) Laghu Vyapari Maandhan alone is incomplete; other listed schemes also target the unorganised sector.

**Key note.** Options d (A and C) and e (B and C) are both defensible: PM Shram Yogi Maandhan is explicitly a pension scheme for unorganised workers, so excluding it (key d) has no basis, and APY equally targets the unorganised sector. No option offers all three.

---

### S16. 2025 Q15 · general-intelligence-reasoning · Odd-one-out within an arrangement

`ce0272eb-49ae-4e1e-bfba-5a7168c211d8` · verdict UNANSWERABLE · confidence low · current affairs no

**Shared stimulus**

> Ten persons, namely M, N, O, P, Q, R, S, T, U, and V, have a meeting on two different dates viz. 9th and 26th of five different months among March, April, June, July and September of the same year, but not necessarily in the given order. Q and U have a meeting in a month having 31 days and 30 days respectively. At least three people have a meeting before Q and after U. Both N and U have a meeting in the same month. S has a meeting in one of the months before N. Only three people have a meeting between S and T. O has a meeting four months before T, but not on an even-numbered date. P, who has a meeting in April, has a meeting in one of the months before M and one of the months after R. Both R and V do not have a meeting on the same numbered date. More than two people have a meeting between V and U. Both P and U have a meeting on the same numbered date.

**Question.** Four of the following five are alike in a certain way and hence form a group. Find the one that doesn't belong to that group.

- (a) P
- (b) Q
- (c) M
- (d) N **← keyed**
- (e) R

**Short explanation.** In the solved order N (Jun 26) has nothing that sets it apart from P, Q, M and R: dates split 9th (P, Q) and 26th (M, N, R), and month lengths split 30 days (P, M, N) and 31 days (Q, R).

**Explanation.** The order that satisfies the premises (with the U/Q clue read as 'at least three before Q and at least three after U') is O (Mar 9), R (Mar 26), P (Apr 9), S (Apr 26), U (Jun 9), N (Jun 26), Q (Jul 9), T (Jul 26), V (Sep 9), M (Sep 26). The natural reading of that clue, U before Q with three or more between, has no solution.

**Why the other options are wrong**

- (a) P (Apr 9) shares its date with Q and its month length with M and N.
- (b) Q (Jul 9) shares its date with P and its month length with R.
- (c) M (Sep 26) shares its date with N and R.
- (e) R (Mar 26) shares its date with M and N.

**Solution steps**

1. Slots: 1 Mar 9, 2 Mar 26, 3 Apr 9, 4 Apr 26, 5 Jun 9, 6 Jun 26, 7 Jul 9, 8 Jul 26, 9 Sep 9, 10 Sep 26.
2. P is in April, R in an earlier month (March) and M in a later month. O is four months before T on an odd date: O Mar 9 (T in July), so R is Mar 26 and V (different date from R) is on a 9th.
3. If U must come before Q with at least three people between them, no arrangement exists: Q (31-day month) can only be July, U would have to be April with N, but April already holds P. Reading the clue as 'at least three before Q and at least three after U' gives a solution.
4. Q takes Jul 9 and T Jul 26. S is four slots from T: S = Apr 26, so P = Apr 9 and U (same date as P, same month as N, after S's month) = Jun 9, N = Jun 26.
5. V is on a 9th with at least three people between V and U: V = Sep 9, M = Sep 26.
6. Unique order: O, R, P, S, U, N, Q, T, V, M.

**Key note.** Under the natural reading of the U/Q clue the premises have no solution; under the only workable reading the order is O, R, P, S, U, N, Q, T, V, M. No attribute of that order (date, month, month length, position) groups P, Q, M, R apart from N, and no arrangement matching all the keyed answers of this set satisfies the premises, so the set appears to be built on a different arrangement.

---

### S17. 2025 Q8 · insurance · Pricing

`7f9d0bda-9279-4e31-ae7b-ef88952871a8` · verdict AGREE · confidence high · current affairs no

**Question.** Who carries out actuarial valuation and pricing of insurance products?

- (a) Auditors
- (b) Surveyors
- (c) Actuaries **← keyed**
- (d) Brokers
- (e) Underwriters

**Short explanation.** Actuaries use mortality, morbidity, interest and expense assumptions to price products and value insurers' liabilities; IRDAI requires an Appointed Actuary for this work.

**Why the other options are wrong**

- (a) Auditors examine the financial statements; they do not price products or value liabilities.
- (b) Surveyors assess losses in general-insurance claims.
- (d) Brokers arrange cover for clients; they do not price products.
- (e) Underwriters assess and classify individual risks within the pricing framework actuaries set; they do not carry out actuarial valuation.

**Common traps**

- Confusing underwriting (accepting individual risks) with actuarial pricing and valuation.

---

### S18. 2025 Q5 · management · Communication channels and channel richness

`b6bec02c-f407-4b80-9406-cec08c535935` · verdict AGREE · confidence high · current affairs no

**Question.** Which of the following communication channels can be used to handle ambiguous managerial problems?

- (a) Quarterly reports
- (b) Newsletters
- (c) Face-to-face meetings **← keyed**
- (d) Notice board circulars
- (e) Pre-recorded video messages

**Short explanation.** Under media richness theory (Daft and Lengel), ambiguous problems need rich channels with instant feedback, several cues and a personal touch. Face-to-face meetings are the richest channel.

**Why the other options are wrong**

- (a) Quarterly reports are lean, one-way and slow, suited to routine data.
- (b) Newsletters are lean, one-way broadcasts.
- (d) Notice-board circulars are the leanest, impersonal written medium.
- (e) Pre-recorded video carries voice and visual cues but allows no real-time feedback, so it is not rich enough.

**Common traps**

- Video seems rich, but without two-way feedback it cannot resolve ambiguity.

---

### S19. 2025 Q17 · quantitative-aptitude · Averages — simple and weighted

`317e8848-1491-426e-8946-5a12a75b2156` · verdict AGREE · confidence high · current affairs no

**Question.** Average salary of 30 workers of a company is Rs.5000 and is increased by Rs. (s + 500) when the salary of 10 new workers is added. If the average salary of new workers is Rs. 60s, then the value of 's' is equal to -

- (a) 120
- (b) 100
- (c) 200
- (d) 225
- (e) 125 **← keyed**

**Short explanation.** Total for the 40 workers = 30 × 5000 + 10 × 60s = 40 × (5000 + s + 500). So 150000 + 600s = 220000 + 40s, giving 560s = 70000 and s = 125.

**Why the other options are wrong**

- (a) No likely slip gives 120; the working gives 125 (560s = 70000).
- (b) No likely slip gives 100; the working gives 125 (560s = 70000).
- (c) No likely slip gives 200; the working gives 125 (560s = 70000).
- (d) No likely slip gives 225; the working gives 125 (560s = 70000).

**Solution steps**

1. Old total = 30 × 5000 = 150000.
2. New workers' total = 10 × 60s = 600s.
3. New average = 5000 + s + 500 = 5500 + s, over 40 workers.
4. 150000 + 600s = 40(5500 + s) = 220000 + 40s.
5. 560s = 70000, so s = 125. Check: new average 5625, new workers average 7500.

**Formula.** Total = Average × Number

**Common traps**

- Dropping the extra 500 in the increase (s + 500), which gives s = 625/7 ≈ 89.3.
- Multiplying the new average by 30 instead of 40 workers.

---

### S20. 2025 Q21 · quantitative-aptitude · Tabular data interpretation

`2a2c658e-2101-400b-9c92-cf215e0feed5` · verdict AGREE · confidence high · current affairs no

**Shared stimulus**

> Directions (20- 21): Read the data carefully and answer the following questions. Following table represents the ratio of sale of Power bank to Earbuds in a store from May to October and the average sale of Power bank and Earbuds in respective months. Month Ratio of sale of Power bank to Earbuds Average sale of Power bank and Earbuds May 2: 3 750 June 4: 11 750 July 13: 7 500 August 5: 3 600 September 3: 5 400 October 5: 6 550

**Question.** Sale of Power bank in September is increased or decreased by what percentage as compared to that in previous month?

- (a) 40%
- (b) 30%
- (c) 75%
- (d) 55%
- (e) 60% **← keyed**

**Short explanation.** Power bank sale in August = 5/8 of 1200 = 750 and in September = 3/8 of 800 = 300. The fall is 450 on a base of 750, i.e. a 60% decrease.

**Explanation.** The table gives the average of Power bank and Earbuds sales for each month, so the month's combined sale is twice that figure, which is then split in the given ratio: May 600/900, June 400/1100, July 650/350, August 750/450, September 300/500, October 500/600 (Power bank/Earbuds).

**Why the other options are wrong**

- (a) 40% is September's sale as a percentage of August's (300/750), not the percentage change.
- (b) No likely slip gives 30%; the working gives a 60% decrease (750 to 300).
- (c) No likely slip gives 75%; the working gives a 60% decrease (750 to 300).
- (d) No likely slip gives 55%; the working gives a 60% decrease (750 to 300).

**Solution steps**

1. August combined = 2 × 600 = 1200; Power bank = 1200 × 5/8 = 750.
2. September combined = 2 × 400 = 800; Power bank = 800 × 3/8 = 300.
3. Change = 750 - 300 = 450 (decrease).
4. Percentage decrease = 450/750 × 100 = 60%.

**Formula.** Percentage change = (New - Old) / Old × 100

**Common traps**

- Reporting 300/750 = 40% (the ratio) instead of the 60% fall.
- Using September (300) as the base, which gives 150%.
