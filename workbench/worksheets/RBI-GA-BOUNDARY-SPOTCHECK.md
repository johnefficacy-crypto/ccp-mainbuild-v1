# RBI GA durable worksheet: boundary-rule spot-check

**Result: 29 of the 191 durable rows (15%) would flip to PERISHABLE** under the same rule used in the 12 adjudications, *"a durable subject with a dated instance is perishable"* (`docs/architecture/subject-practice-framework.md` §1.1.1 boundary rule, quoted in `workbench/reports/RBI-GA-STRATEGY-FINDINGS-2026-09-22.md` §3.1).

By year: **2023: 11**, **2024: 14**, **2025: 3**, **2026: 1**.

This is information only. `workbench/worksheets/RBI-GA-DURABLE-tags.csv` is **not** changed on the strength of it, and every row there is still `DURABLE` per the file of record.

## What this tells the reviewer

The file of record is not wrong on just the 12 disputed rows. Applied consistently, the rule would also move about 1 in 7 of the rows both passes agreed were durable. That is 29 rows, more than double the 12 in dispute, so the disagreement is systematic. The two classification passes read the rule differently. Neither was careless on a handful of rows. A human should settle the reading of the rule first, then re-run the classification, rather than adjudicating 12 rows in isolation.

Taken together: 12 adjudication rows (10 recommended against the file of record) plus 29 here. At most 39 of the 202 durable rows carry a dated anchor that the rule, read strictly, would make perishable.

## Method

1. Stem search over all 191 rows (text from `workbench/sources/rbi-ga-pending.json`) for dated anchors: a year (1950-2039), a month name, *recent/recently, latest, current/currently, new/newly, launched, inaugurated, announced, proposed, revised, Union Budget*. 65 rows hit.
2. Each hit was read by hand. A row flips **only** if the dated anchor governs the fact being asked: launch news, a stated as-of figure, a per-edition document, or a Budget or "recent" change. It is kept durable when the date is only background or a statute's name:
   - statute or scheme names carrying a year (SEBI MF Regulations 1996, SARFAESI Act 2002, Companies Act 2013, RB-IOS 2021, Interest Rate on Deposits Directions 2025, Income-tax Rules 2026);
   - fixed history (Smart Cities launched 25 June 2015, PARIVESH 2018, the NPA-mechanism enactment years, Nobel 1968);
   - a "recent" hook whose asked fact is static (2024-63 Tenth Schedule, 2024-65 Houthis' home country, 2026-74 CTBC Bank's country);
   - false hits (*current* account, *New* Delhi, *may*).
   36 of the 65 hits were kept on these grounds.
3. Not counted: as-of figures with **no** dated anchor in the stem (e.g. 2024-1 PMAY-U 2.0 outlay, 2025-16 UPI capital-market limit, 2024-20 BSDA ceiling). A stricter "as-of figure" reading would push the number higher. The rule tested here is the dated-instance rule only.

## Flipping rows (all 29; the first 10 are the requested examples)

| year-Q | question_id | subject | dated anchor |
|---|---|---|---|
| 2023-6 | `ff2a43cf-19d2-4b71-9e78-815af74a91a9` | general-knowledge | "a recent meeting" - dated proposal |
| 2023-10 | `dc375824-9bd8-42ee-a07b-acdf2ac88636` | general-knowledge | TRAI measures "in recent past" |
| 2023-12 | `92ec9348-e725-4bc2-86c1-6484d7617e01` | general-knowledge | Morgan Stanley 2023 forecast to 2028 |
| 2023-26 | `6cae56ac-d728-447c-a155-ad062d02e25c` | finance | Payments Vision 2025 - superseded edition |
| 2023-32 | `a5817e98-78ab-4dbd-abb2-27f1e3c22b35` | finance | Foreign Trade Policy 2023 - per-edition |
| 2023-38 | `fb85f00d-5fa9-4fe8-aaaa-239e35d338f7` | general-knowledge | Atlantic Declaration - "new" dated agreement |
| 2023-46 | `c3f3f398-3537-4897-83f9-208043670daa` | finance | "latest base year" - as-of |
| 2023-48 | `c8a89a5b-7f4f-4290-b18d-fd44672489cf` | finance | "Recently" SEBI proposal |
| 2023-60 | `fc688826-eec8-4593-9f75-90a67a191e68` | general-knowledge | May 2023 commemorative coin |
| 2023-72 | `b4f5f20f-b40d-48c5-9e91-0189760913db` | finance | PIDF tenure/targets from Jan 2021 edition |
| 2023-77 | `33b11bae-3149-4094-8a02-a209c867dc95` | general-knowledge | Country Partnership Strategy 2023-2027 - per-edition |
| 2024-2 | `c03cf54f-6f27-4e8e-a958-f11435df69ef` | finance | Union Budget 2024-25 change |
| 2024-3 | `1eac5e45-a56c-4514-bdc4-c2d64bc5b156` | finance | Union Budget 2024-25 change |
| 2024-5 | `09bdd252-7913-4235-a3ad-f204400ce21a` | finance | Union Budget 2024-25 proposal |
| 2024-15 | `6c6fabd9-b2b5-403b-8d72-3f5cfb7cdb7e` | finance | "Recently" proposed UPI limit |
| 2024-22 | `25bf3b60-a3f7-4fd5-b440-799f15c4fa54` | economics | May 2022-Feb 2023 repo cycle |
| 2024-25 | `4fc90b0f-6ed7-4354-9010-ad78c0d78f6e` | finance | "now" revised HFC rules |
| 2024-26 | `fe284090-9d9a-4778-b5d7-8077b79b8919` | finance | "recent update" bulk deposits |
| 2024-30 | `5c3e362e-0dba-4003-958b-ceadce1d9318` | finance | "most recent FSR" |
| 2024-32 | `fbb7d25c-0b56-4599-b422-c45b381efb42` | finance | Report on Currency and Finance 2024 - per-edition |
| 2024-38 | `55094ce0-40a8-4990-9eaf-03ffc2186a32` | finance | "can now" new SEBI rules |
| 2024-39 | `cbf8c8e6-eb92-4b50-bcb5-17d4206cf7b6` | finance | "recently proposed" |
| 2024-44 | `1af91cef-9299-4846-8359-82d9dc8c63d2` | finance | October 2022 cancellation |
| 2024-46 | `b61bbbac-da6c-4286-a75f-5a618ca7fd9d` | finance | "recent changes" bond minimum |
| 2024-73 | `d699bb86-2cf3-4195-8a66-7b4d2c5faec9` | general-knowledge | "Recently" named lunar site |
| 2025-9 | `619759c6-e9ee-425b-bf4c-7305035fe1f9` | finance | GST slab effective 22 September 2025 |
| 2025-29 | `308ef4be-d09b-42c0-970e-0cf7baea5fcd` | finance | "recent regulations" |
| 2025-30 | `7b50ed9a-79a9-4723-b307-188c86c6ef1b` | finance | "Recently" NPCI limit |
| 2026-17 | `29e05594-470e-4f38-87df-2db9ad5bf3b8` | finance | Utkarsh 2029 - per-edition strategy |
