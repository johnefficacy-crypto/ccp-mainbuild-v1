# IFSCA Grade A — Explanation Draft Revision (EXPL-02-REV)

Revises `workbench/worksheets/IFSCA-EXPLANATIONS-DRAFT.json` into `IFSCA-EXPLANATIONS-DRAFT-REV.json`. The original draft and
`IFSCA-EXPLANATIONS-NOTES.md` stay unchanged as the record of the first pass. The 362 rows are already applied to the database
as `pending`; an operator step patches only the rows listed in §5. No database write was made here.

Three revisions:

1. **Accept keys that are defensible on any reasonable reading.** All 17 non-AGREE rows re-examined.
2. **Reasoning puzzles work one valid arrangement.** Each explanation states one arrangement consistent with the premises and the
   key, walks the deductions that pin it down, and mentions any other valid arrangement in one line at the end.
3. **Plain language, reasoning-puzzle rows only.** No other row's wording was touched.

Scope of "reasoning-puzzle rows": the 30 `general-intelligence-reasoning` questions built on a shared premise set (floor-and-flat,
family tree, month-and-date scheduling, linear row, direction and distance, meeting schedule, row of unknown length). The 16
standalone reasoning items (syllogisms, inequalities, coding, word formation, critical reasoning) are not puzzles and are unchanged.

## 1. Verdict counts

| Verdict | Before | After |
|---|---|---|
| AGREE | 345 | 361 |
| DISPUTED | 0 | 1 |
| AMBIGUOUS | 16 | 0 |
| UNANSWERABLE | 1 | 0 |
| **Total** | **362** | **362** |

`final_answer_option_id` is set on all 361 AGREE rows, equal to the input `correct_option_id`, and null on the
1 remaining row(s). Rows with it set: 361.

## 2. Rows whose verdict changed

| Year/Q | Subject | Before | After | Reason |
|---|---|---|---|---|
| 2025 Q7 | commerce-accountancy | AMBIGUOUS | AGREE | Accepted as defensible. Another reading set aside: option a (Profit and Loss Account) is where the FCMITDA is amortised over the item's remaining life. The key follows where the balance is presented, under Reserves and Surplus. |
| 2025 Q4 | costing | AMBIGUOUS | AGREE | Accepted as defensible. Another reading set aside: option e (Batch Costing) is the textbook example for biscuits in ICAI and most Indian costing texts. The key follows the stem's 'high volume', which suggests continuous production. |
| 2024 Q22 | finance | AMBIGUOUS | AGREE | Accepted as defensible. Another reading set aside: option b (Forwards) also creates an obligation, and 'between two counterparties' describes a private forward at least as well. The key is taken as the commonly used, exchange-traded form. |
| 2025 Q5 | financial-awareness | AMBIGUOUS | AGREE | Accepted as defensible. Another reading set aside: PM Shram Yogi Maandhan is also a pension scheme for unorganised workers, so option e (B and C) is equally true. No option offers all three. |
| 2025 Q11 | financial-awareness | AMBIGUOUS | DISPUTED | Key not defensible. The stem spells out SMILE as 'Support for Marginalized Individuals for Livelihood and Enterprise', which is the Ministry of Social Justice and Empowerment scheme funded by the Government of India. The Asian Development Bank funds a different SMILE, the Strengthening Multimodal and Integrated Logistics Ecosystem programme. No reading of this stem makes ADB right; option e (None of the above) is correct. |
| 2025 Q23 | financial-awareness | AMBIGUOUS | AGREE | Accepted as defensible. Another reading set aside: IndiQube Spaces (option b) also opened its IPO in July 2025, around 23 July, after Smartworks around 10 July. |
| 2023 Q6 | general-intelligence-reasoning | AMBIGUOUS | AGREE | The stem never says which flat is west; this draft adopts the reading that Flat Alpha is to the west of Flat Beta, as the key does. If N and Q swap floors (N on the fifth floor), nobody is above N and option e would be correct; this draft follows the arrangement that matches the key. |
| 2023 Q7 | general-intelligence-reasoning | AMBIGUOUS | AGREE | In a second valid arrangement, O and P swap, putting P on the second floor of Flat Alpha, which would make option b correct. This draft follows the arrangement that matches the key. |
| 2023 Q8 | general-intelligence-reasoning | AMBIGUOUS | AGREE | Grouping by odd and even floors instead would single out X on the fourth floor, making option e correct; and if O and P swap, all five are in Flat Alpha. This draft groups by flat, as the key does. |
| 2023 Q9 | general-intelligence-reasoning | AMBIGUOUS | AGREE | If N and Q swap floors (N on the fifth floor, Q on the first), Z would be two floors below N, and only option e would fit. This draft follows the arrangement that matches the key. |
| 2023 Q10 | general-intelligence-reasoning | AMBIGUOUS | AGREE | In other valid arrangements (O on the third floor of Flat Beta, or Q on the first floor), there would be one floor or none between Q and O, which would make option a or option e correct. This draft follows the arrangement that matches the key. |
| 2024 Q8 | general-intelligence-reasoning | AMBIGUOUS | AGREE | In the second valid seating (west to east K, E, V, M, G, R, H, A), only G and R sit between M and H, which would make option b correct. This draft follows the seating that matches the key. |
| 2024 Q9 | general-intelligence-reasoning | AMBIGUOUS | AGREE | In the second valid seating (west to east K, E, V, M, G, R, H, A), K and A sit at the ends, which would make option e correct. This draft follows the seating that matches the key. |
| 2025 Q13 | general-intelligence-reasoning | AMBIGUOUS | AGREE | Read literally, the clue "at least three people meet between U and Q" leaves no possible schedule (U would have to be in June and Q in July, with at most two people between them), so this draft relaxes only that clue to "at least three people meet before Q, and at least three people meet after U"; every other clue is kept, and they then give exactly one schedule. In this schedule U and Q, T and M, and P and U also have exactly one person between them, just like O and P, so options b, c and e fit as well; the key's pair R and S is accepted as one of the defensible pairs. |
| 2025 Q15 | general-intelligence-reasoning | UNANSWERABLE | AGREE | Read literally, the clue "at least three people meet between U and Q" leaves no possible schedule (U would have to be in June and Q in July, with at most two people between them), so this draft relaxes only that clue to "at least three people meet before Q, and at least three people meet after U"; every other clue is kept, and they then give exactly one schedule. The grouping behind the key is thin: the only feature that separates N is that N meets in June, the middle month, while the other four meet in the two earliest or two latest months. No clearer grouping singles out any one option. |
| 2025 Q16 | general-intelligence-reasoning | AMBIGUOUS | AGREE | Read literally, the clue "at least three people meet between U and Q" leaves no possible schedule (U would have to be in June and Q in July, with at most two people between them), so this draft relaxes only that clue to "at least three people meet before Q, and at least three people meet after U"; every other clue is kept, and they then give exactly one schedule. In this schedule statements a (O and P both on the 9th) and b (N on 26 June) are also true, while e fails because d (P immediately before U) is false; the key's option c is accepted as the intended answer. |
| 2023 Q3 | pension-sector | AMBIGUOUS | AGREE | Accepted as defensible. Other readings set aside: option a names the same company by its pre-2021 name, and option d (Karvy Computershare, now KFin Technologies) was later registered as a second CRA. The key is taken as the original CRA under its current name. |

### Still flagged

- **2025 Q11 · financial-awareness · `2f5f8353-833d-4f71-874b-8df5525e7fd8`** — DISPUTED. Keyed (a) Asian Development Bank; proposed (e) None of the above. Key not defensible. The stem spells out SMILE as 'Support for Marginalized Individuals for Livelihood and Enterprise', which is the Ministry of Social Justice and Empowerment scheme funded by the Government of India. The Asian Development Bank funds a different SMILE, the Strengthening Multimodal and Integrated Logistics Ecosystem programme. No reading of this stem makes ADB right; option e (None of the above) is correct.

### The 2025 meeting puzzle (Q13–Q16)

Read literally ("at least three people meet between U and Q") the premises admit no schedule at all. This revision relaxes that
one clue to "at least three people meet before Q, and at least three meet after U". Every other clue is kept as written, and
exactly one schedule then fits: 9 March O, 26 March R, 9 April P, 26 April S, 9 June U, 26 June N, 9 July Q, 26 July T,
9 September V, 26 September M. It makes every key defensible. Q13 and Q16 keys are each one of several true options. The Q15 key
(N) rests on a thin grouping: N is the only one of the five who meets in June, the middle month. It is kept at low confidence.
Q15 moves from UNANSWERABLE to AGREE on that basis.

## 3. Rows changed, by revision

| Cause | Rows |
|---|---|
| Revision 1 only, non-reasoning rows (verdict and key wording) | 7 |
| Revision 1 plus Revisions 2–3, reasoning-puzzle rows (verdict changed and rewritten) | 10 |
| Revisions 2–3 only, reasoning-puzzle rows (rewritten, verdict unchanged) | 20 |
| **Total rows changed** | **37** |
| Rows byte-identical to the original | 325 |

## 4. Wording changes — old and new `short_explanation`

### 2025 Q7 · commerce-accountancy · `ef002276-c10b-4f2a-8a74-dc21156f629c`

Cause: R1. Verdict AMBIGUOUS → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| Under para 46A of AS 11, exchange differences on long-term foreign-currency monetary items not related to depreciable assets are held in the FCMITDA. The balance is shown in the balance sheet as a separate line under 'Reserves and Surplus', which is the keyed answer. | Under para 46A of AS 11, exchange differences on long-term foreign-currency monetary items not related to depreciable assets are held in the FCMITDA. The balance is shown in the balance sheet as a separate line under 'Reserves and Surplus', which is the keyed answer. |

Fields changed: `option_rationales`, `key_note`, `key_verdict`, `final_answer_option_id`.

### 2025 Q4 · costing · `26ee28d2-28eb-4f6f-8140-a9a6c59b22b7`

Cause: R1. Verdict AMBIGUOUS → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| Continuous, high-volume production of identical biscuits through successive stages points to process costing, which is the key. | A bakery turning out identical biscuits in high volume runs a continuous flow through mixing, baking and packing stages, and process costing collects cost stage by stage over that flow. The stem's stress on high volume points to process costing. |

Fields changed: `short_explanation`, `option_rationales`, `key_note`, `key_verdict`, `final_answer_option_id`.

### 2024 Q22 · finance · `e78ace07-4078-428b-a92d-add1421ba2ab`

Cause: R1. Verdict AMBIGUOUS → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| Both forwards and futures create a binding obligation to buy or sell gold at a set price on a future date. The key takes futures, which are standardised and traded on exchanges such as MCX, but the stem's phrase 'between two counterparties' describes a bilateral forward just as well. | A futures contract binds both sides to buy or sell gold at a fixed price on a set future date, and it is the standard way gold is traded forward in India, on exchanges such as MCX. The word 'obligation' rules out options, which give only a right. |

Fields changed: `short_explanation`, `option_rationales`, `key_note`, `key_verdict`, `final_answer_option_id`.

### 2025 Q5 · financial-awareness · `abe318b3-6a80-48a7-b824-1c461d28c1ce`

Cause: R1. Verdict AMBIGUOUS → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| All three schemes serve the unorganised sector. APY is aimed chiefly at unorganised-sector workers, PM Shram Yogi Maandhan is a pension scheme for unorganised workers, and the Laghu Vyapari Maandhan (NPS-Traders) covers small traders and self-employed persons outside formal pension cover. | Atal Pension Yojana is aimed chiefly at unorganised-sector workers, and Laghu Vyapari Maandhan covers small traders and self-employed people outside formal pension cover. Both target the unorganised sector, so 'A and C' is right. |

Fields changed: `short_explanation`, `option_rationales`, `key_note`, `key_verdict`, `final_answer_option_id`.

### 2025 Q11 · financial-awareness · `2f5f8353-833d-4f71-874b-8df5525e7fd8`

Cause: R1. Verdict AMBIGUOUS → DISPUTED. Confidence low → medium.

| Before | After |
|---|---|
| The expansion in the stem is the Ministry of Social Justice and Empowerment's SMILE scheme for transgender persons and people engaged in begging, which is a central sector scheme funded by the Government of India. The keyed Asian Development Bank finances a different SMILE, the Strengthening Multimodal and Integrated Logistics Ecosystem programme for India. | The expansion in the stem is the Ministry of Social Justice and Empowerment's SMILE scheme for transgender persons and people engaged in begging, which is a central sector scheme funded by the Government of India. The keyed Asian Development Bank finances a different SMILE, the Strengthening Multimodal and Integrated Logistics Ecosystem programme for India. |

Fields changed: `option_rationales`, `key_note`, `key_verdict`, `draft_confidence`, `proposed_correct_option_id`.

### 2025 Q23 · financial-awareness · `2ebee501-ad8d-441e-a172-3a69278efe7d`

Cause: R1. Verdict AMBIGUOUS → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| Flexible and co-working workspace operators tapped the Indian IPO market in 2025 as demand for managed office space grew. Smartworks Coworking Spaces launched its IPO in July 2025, but IndiQube Spaces also opened its IPO in July 2025. | Flexible and co-working workspace operators tapped the Indian IPO market in 2025 as demand for managed offices grew. Smartworks Coworking Spaces launched its IPO in July 2025. |

Fields changed: `short_explanation`, `option_rationales`, `key_note`, `key_verdict`, `final_answer_option_id`.

### 2023 Q6 · general-intelligence-reasoning · `649b73c0-79e6-4907-88fd-feb22e5379fd`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| If N is on Alpha 1 (as the key assumes), the person immediately above N is O on Alpha 2, whom the key describes as the one west of Y; but the premises allow N to be on Alpha 5 as well, and they never say which flat lies west. | N is on the first floor of Flat Alpha, so the person immediately above N is O on the second floor of Flat Alpha. O is on the same floor as Y but in the other flat, which the key describes as the one who stays west of Y. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2023 Q7 · general-intelligence-reasoning · `da42d118-aaaa-4815-ac8a-df9dc904be2b`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| P and O occupy Beta 3 and Alpha 2, but the premises allow either assignment: the key's Beta 3 holds only if P, not O, is in Beta 3. | P stays on the third floor of Flat Beta, next to O, who is on the second floor of Flat Alpha. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2023 Q8 · general-intelligence-reasoning · `e3d8429c-66bf-465d-9991-5d94a413efb0`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| In the key's arrangement Q, N, Z and X are in Flat Alpha and P alone is in Flat Beta. That same arrangement also puts X alone on an even floor, and if O and P are swapped all five are in Flat Alpha. | Q, N, Z and X all stay in Flat Alpha, while P stays in Flat Beta. So P is the odd one out. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2023 Q9 · general-intelligence-reasoning · `33f5bc51-298d-4b27-80e5-90e72ec8af26`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| Z is on floor 3; if N is on floor 1, as the key assumes, Z is two floors above N, but the premises also allow N on floor 5, where Z would be two floors below. | Z is on the third floor of Flat Alpha and N is on the first floor of Flat Alpha, so Z is two floors above N. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2023 Q10 · general-intelligence-reasoning · `0dfb0389-494f-4b88-bbd0-04d26192a566`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| The key's arrangement puts Q on floor 5 and O on floor 2, with two floors (3 and 4) between them, but the premises leave both Q's and O's floors open. | Q is on the fifth floor and O on the second floor, so the third and fourth floors lie between them: two floors. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2023 Q16 · general-intelligence-reasoning · `72bfaad3-c34f-438b-a030-82974d962840`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Atlas's mother is Orion, and Orion has no siblings, so she can be Zane's sister-in-law only as the wife of Zane's brother. Orion is therefore the sister-in-law. | Atlas's mother is Orion. She has no siblings, so she can be Zane's sister-in-law only as the wife of Zane's brother Lyra. Orion is Zane's sister-in-law. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`.

### 2023 Q17 · general-intelligence-reasoning · `e5e22611-99ac-4052-a46b-03b3b6dfb3b7`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Luna is Atlas's uncle on the father's side, so Luna is a brother of Lyra and a son of Harper and Nova; since only three people are female, Luna is male. | Luna is a son of Nova and Harper, so Luna is Harper's son. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2023 Q18 · general-intelligence-reasoning · `c9a62049-9d47-4eb8-8090-f8c068596141`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Orion's husband must be Harper's son. Zane is her brother-in-law and Luna is Atlas's uncle, which leaves Lyra. | Orion's husband is Harper's son, and he cannot be Zane (her brother-in-law) or Luna (Atlas's uncle). So Orion's husband is Lyra. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`.

### 2023 Q19 · general-intelligence-reasoning · `604dbd30-efc1-4855-90fc-db0cec1ef276`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Lyra is Orion's husband, and Orion is the mother of two children, Atlas and Vega, so Lyra has two children. | Lyra and Orion have two children, Atlas and Vega. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`.

### 2023 Q20 · general-intelligence-reasoning · `04cb450f-2a15-4af3-8f3f-261acf778429`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Daniel performed on October 12th and Harper on October 23rd, consecutive slots, so no performance falls between them. | Daniel performs on 12 October and Harper on 23 October, one straight after the other, so no performance comes between them. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2023 Q21 · general-intelligence-reasoning · `29bcd77c-4860-429b-86c0-6f4693cb0247`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Harper is on the 23rd (odd date) of a 31-day month other than August; July 23rd is Liam's, so Harper performed in October. | Harper performs on 23 October, the last turn of the competition. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2023 Q22 · general-intelligence-reasoning · `45a6a8d5-52cb-4355-a5c1-188133d206f8`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Noah performed on August 23rd (slot 6), and the next slot, September 12th, is Ava's. | Noah performs on 23 August, and the next turn, 12 September, belongs to Ava. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2023 Q23 · general-intelligence-reasoning · `cd28117d-ad42-44b2-89c1-218e74f24906`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Olivia performed on June 12th, the first slot, so nobody performed before her. | Olivia performs on 12 June, the very first turn, so no one performs before her. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2023 Q24 · general-intelligence-reasoning · `1257cd2b-5e04-40c9-9336-67e13e41e4a2`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Harper, Noah, Liam and Mia all performed on the 23rd; Ava alone performed on the 12th (September 12th). | Harper, Noah, Liam and Mia all perform on the 23rd of their months; Ava alone performs on the 12th (12 September). |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`.

### 2024 Q6 · general-intelligence-reasoning · `4474f5d0-e945-4511-935d-8d7ed50a344c`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| In the arrangement the key uses, E K M V R G A H, G sits immediately right of R. | R sits fifth from the west end and G sits sixth, so G is immediately to R's right. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`.

### 2024 Q7 · general-intelligence-reasoning · `d2312a22-1769-45e6-9af9-95e09354e332`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| In E K M V R G A H, V is seat 4 and A seat 7, so R and G, two persons, sit between them. | V sits fourth from the west end and A seventh, so R and G, two persons, sit between them. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`.

### 2024 Q8 · general-intelligence-reasoning · `ced3a18c-7c15-4395-8efb-0e684aa9730e`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| In E K M V R G A H, M is seat 3 and H seat 8, with V, R, G and A (four persons) between them. The other valid seating gives two. | M sits third from the west end and H at the east end, so V, R, G and A, four persons, sit between them. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2024 Q9 · general-intelligence-reasoning · `66c297b8-70e0-4df7-9cf5-7abe340f5e0e`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| In E K M V R G A H the ends are E (left) and H (right); in the other valid seating they are K and A. | Facing north, the left end is the west end, where E sits, and the right end is the east end, where H sits. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2024 Q10 · general-intelligence-reasoning · `c21c2406-b9a2-4dc9-8d91-c588bbb15b43`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| In E K M V R G A H, the pairs EK, RG, HA and VR are all immediate neighbours, while M and R have V between them. | E and K, R and G, H and A, and V and R each sit side by side; M and R have V between them, so MR is the odd one out. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`.

### 2024 Q14 · general-intelligence-reasoning · `01f649fd-1d6e-42d0-a603-2ada9458a2bf`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| G and T are the first-generation couple and E is their child. If G is female, T is her husband and so E's father. | G and T are the oldest couple and E is their child. If G is female, T is her husband, so T is E's father. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2024 Q15 · general-intelligence-reasoning · `4a55abae-7d82-4a29-a082-662c66fe5987`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Q is the mother of U, and H is U's wife, so Q is H's mother-in-law. | Q is U's mother, and H is married to U, so Q is H's mother-in-law. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2024 Q17 · general-intelligence-reasoning · `2ca25634-cd1d-4f6d-80ba-3d8a8b9d9027`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| G is (9, 11) and D is (16, -4), so the gaps are 7 m east-west and 15 m north-south, and the distance is the square root of 49 + 225 = 274. | G is 7 m west of D and 15 m north of it, so the shortest distance is √(7² + 15²) = √274 m. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `formula_used`, `common_traps`.

### 2024 Q18 · general-intelligence-reasoning · `e017f891-419c-4db9-a989-a3d6da7a931d`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| The girl ends at E (16, 1) and the boy started at F (9, -3). E is 7 m east and 4 m north of F, so it is to the northeast. | The girl ends at E, which is 7 m east and 4 m north of the boy's starting point F, so she is to the northeast of F. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2024 Q19 · general-intelligence-reasoning · `b13d9ede-1293-4c36-ae62-5e2365bdf06a`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| C is (7, -4) and I is (16, 11). C is 9 m west and 15 m south of I, so it is to the southwest. | C is 9 m west and 15 m south of I, so C is to the southwest of I. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`.

### 2024 Q20 · general-intelligence-reasoning · `8101a505-3869-414f-9b66-0d9b5122ab68`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| B is (7, 0) and I is (16, 11), so the gaps are 9 m and 11 m and the distance is the square root of 81 + 121 = 202. | I is 9 m east and 11 m north of B, so the shortest distance is √(9² + 11²) = √202 m. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `formula_used`, `common_traps`.

### 2025 Q13 · general-intelligence-reasoning · `13452ac5-49dd-4413-a0a1-2453e00a4775`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| O and P have one person (R) between them. In the solved order R-S, U-Q, M-T and P-U also have exactly one person between them, so four options fit. | O meets on 9 March and P on 9 April, with only R (26 March) between them. R and S also have exactly one person between them: P, on 9 April. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2025 Q14 · general-intelligence-reasoning · `7a1d4e98-db99-4587-a9a2-2feb9a4e288f`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| In the solved order T (Jul 26) meets immediately before V (Sep 9), and none of options a to d describes T. | V meets on 9 September, and the person just before V is T, who meets on 26 July. None of options a to d describes T, so the answer is None of these. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`.

### 2025 Q15 · general-intelligence-reasoning · `ce0272eb-49ae-4e1e-bfba-5a7168c211d8`

Cause: R1, R2/R3. Verdict UNANSWERABLE → AGREE. Confidence low → low.

| Before | After |
|---|---|
| In the solved order N (Jun 26) has nothing that sets it apart from P, Q, M and R: dates split 9th (P, Q) and 26th (M, N, R), and month lengths split 30 days (P, M, N) and 31 days (Q, R). | N meets in June, the middle of the five months. P and R meet in the two earliest months (April and March) and Q and M in the two latest (July and September), so N is the odd one out. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `common_traps`, `key_note`, `key_verdict`, `final_answer_option_id`.

### 2025 Q16 · general-intelligence-reasoning · `ab69edb7-2254-411b-8352-3ca7b7ba6220`

Cause: R1, R2/R3. Verdict AMBIGUOUS → AGREE. Confidence low → medium.

| Before | After |
|---|---|
| In the solved order O and P both meet on the 9th, N meets on June 26th and V and M both meet in September. Options a, b and c are all true, and only d is false. | V meets on 9 September and M on 26 September, so V and M meet in the same month and statement c is correct. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `key_note`, `key_verdict`, `draft_confidence`, `final_answer_option_id`.

### 2025 Q18 · general-intelligence-reasoning · `06abf31b-cf25-4378-af7e-a6b411a1953d`

Cause: R2/R3. Verdict AGREE → AGREE. Confidence high → high.

| Before | After |
|---|---|
| Fixing M's position from the Q-R-S equal spacing and S being 12th from the left places M at 6, N at 13 and P at 14; P is 4th from the right, so there are 14 + 3 = 17 persons. | S is 12th from the left, which puts M 6th and N 13th. P sits next to N, so P is 14th from the left; as P is 4th from the right, there are 14 + 3 = 17 persons. |

Fields changed: `short_explanation`, `explanation_text`, `option_rationales`, `solution_steps`, `formula_used`, `common_traps`.

### 2023 Q3 · pension-sector · `b5297708-48ff-416b-9eac-7896e0d9be86`

Cause: R1. Verdict AMBIGUOUS → AGREE. Confidence medium → medium.

| Before | After |
|---|---|
| A Central Recordkeeping Agency keeps NPS subscriber records, issues PRANs and handles contribution and switch processing. PFRDA's first CRA was NSDL e-Governance Infrastructure Limited, which renamed itself Protean eGov Technologies Limited in 2021, so the two names refer to the same company. | A Central Recordkeeping Agency keeps NPS subscriber records, issues PRANs and processes contributions and switches. PFRDA's first CRA is Protean eGov Technologies Limited, the name NSDL e-Governance Infrastructure Limited has carried since 2021, so the keyed answer names the original CRA by its current name. |

Fields changed: `short_explanation`, `option_rationales`, `key_note`, `key_verdict`, `final_answer_option_id`.

## 5. question_ids to patch

37 rows. The operator patches only these; every other row is byte-identical to the applied draft.

```
01f649fd-1d6e-42d0-a603-2ada9458a2bf
04cb450f-2a15-4af3-8f3f-261acf778429
06abf31b-cf25-4378-af7e-a6b411a1953d
0dfb0389-494f-4b88-bbd0-04d26192a566
1257cd2b-5e04-40c9-9336-67e13e41e4a2
13452ac5-49dd-4413-a0a1-2453e00a4775
26ee28d2-28eb-4f6f-8140-a9a6c59b22b7
29bcd77c-4860-429b-86c0-6f4693cb0247
2ca25634-cd1d-4f6d-80ba-3d8a8b9d9027
2ebee501-ad8d-441e-a172-3a69278efe7d
2f5f8353-833d-4f71-874b-8df5525e7fd8
33f5bc51-298d-4b27-80e5-90e72ec8af26
4474f5d0-e945-4511-935d-8d7ed50a344c
45a6a8d5-52cb-4355-a5c1-188133d206f8
4a55abae-7d82-4a29-a082-662c66fe5987
604dbd30-efc1-4855-90fc-db0cec1ef276
649b73c0-79e6-4907-88fd-feb22e5379fd
66c297b8-70e0-4df7-9cf5-7abe340f5e0e
72bfaad3-c34f-438b-a030-82974d962840
7a1d4e98-db99-4587-a9a2-2feb9a4e288f
8101a505-3869-414f-9b66-0d9b5122ab68
ab69edb7-2254-411b-8352-3ca7b7ba6220
abe318b3-6a80-48a7-b824-1c461d28c1ce
b13d9ede-1293-4c36-ae62-5e2365bdf06a
b5297708-48ff-416b-9eac-7896e0d9be86
c21c2406-b9a2-4dc9-8d91-c588bbb15b43
c9a62049-9d47-4eb8-8090-f8c068596141
cd28117d-ad42-44b2-89c1-218e74f24906
ce0272eb-49ae-4e1e-bfba-5a7168c211d8
ced3a18c-7c15-4395-8efb-0e684aa9730e
d2312a22-1769-45e6-9af9-95e09354e332
da42d118-aaaa-4815-ac8a-df9dc904be2b
e017f891-419c-4db9-a989-a3d6da7a931d
e3d8429c-66bf-465d-9991-5d94a413efb0
e5e22611-99ac-4052-a46b-03b3b6dfb3b7
e78ace07-4078-428b-a92d-add1421ba2ab
ef002276-c10b-4f2a-8a74-dc21156f629c
```

Patch notes: the fields that change are listed per row in §4. On the one DISPUTED row, `final_answer_option_id` stays null and
`ambiguity_status` should become `disputed`. On every row that became AGREE, `ambiguity_status` goes to `none` and
`final_answer_option_id` is set, which is what the review RPC needs before it will allow `verified`. The shape rules from the
first-pass notes still apply: `formula_used` becomes a one-item array (or an empty one), and `option_rationales` becomes an object
keyed by option id.

## 6. Validation

- **Rows:** 362 out; `question_id` set equal to the original and to the input file. Field set and key order identical.
- **Changed rows:** 37 = 7 (Revision 1, non-reasoning) + 10 (Revision 1 + 2–3, puzzles) + 20 (Revisions 2–3 only, puzzles).
- **Verdicts:** before {'AGREE': 345, 'AMBIGUOUS': 16, 'UNANSWERABLE': 1}; after {'AGREE': 361, 'DISPUTED': 1}.
- **final_answer_option_id:** present on all 361 AGREE rows and equal to the input `correct_option_id`; null on the rest.
- **Non-reasoning rows:** 316. Wording changed on 7, all of them Revision 1 key re-examinations
  (listed in §2). Outside Revision 1, wording changed on 0 non-reasoning rows, diffed field by field against the original.
- **Standalone reasoning rows (not puzzles):** 16; changed: 0.
- **Unchanged rows:** 325, each byte-identical to the original when serialised.
- **Fixed fields:** `question_id`, `year`, `question_number`, `subject_slug`, `topic_name`, `current_affairs`, `tag_suspect`, `tag_note` and
  the provenance values are unchanged on every row. No retagging.
- **Option rationales:** every AGREE row covers every wrong option; the DISPUTED row omits only its proposed option.

## 7. Scope

IFSCA Grade A only. No database writes, no migrations, no retagging (the 18 `tag_suspect` rows are a separate job), no SEBI change.
