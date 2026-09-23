# RBI GA re-classification v2 — under `workbench/docs/GA-BOUNDARY-RULE.md`

Output: `workbench/rbi-ga-classification-v2.csv` (320 rows). Source text: `workbench/sources/rbi-ga-pending.json`. Rule: `workbench/docs/GA-BOUNDARY-RULE.md` v1 (PR #1169). Classification only: nothing is tagged, projected or written to a database.

## Result

| | DURABLE | PERISHABLE |
|---|---:|---:|
| **v2 (this pass)** | **203** | **117** |
| combined file (v1 of record) | 202 | 118 |

| year | DURABLE | PERISHABLE |
|---|---:|---:|
| 2023 | 43 | 37 |
| 2024 | 48 | 32 |
| 2025 | 55 | 25 |
| 2026 | 57 | 23 |

Test that fired: T1 **82**, T2 **35**, T3 **203**.

**Perishable fell by 1, not "well below" 118.** The net figure hides movement both ways: **33 rows changed** against the combined file.

- **17 PERISHABLE → DURABLE.** These are the §3 classes and T3 examples the combined pass had marked perishable:
  - fixed observance dates;
  - annual-edition themes (§3.2);
  - statements attributed to a named report (§3.3);
  - current values with no date in the stem (§3.1);
  - project or installation geography (the §2 T3 highway example);
  - static facts behind a news hook.
- **16 DURABLE → PERISHABLE.** These are rows whose stem names a dated occasion that the combined pass nonetheless called durable. Examples:
  - Union Budget 2024-25 changes;
  - figures for a stated period;
  - dated launches and signings;
  - a merger with an effective date.

T1 fires on these as written. The §3.1 exemption covers current values with *no date in the stem*, and these stems carry one.

The §3 sanity check ("substantially more than 118 → re-check") is satisfied. The count did not fall further because the combined file was not uniformly strict: it was loose on dated-stem rows and strict on static-fact rows. The rule corrects both. No verdict was steered toward any prior count, and the 29-row v1 spot-check was not used as a source.

## Rulings used where the rule text needed applying

These are recorded so a reviewer can overturn them as a class, not row by row.

1. **Rule's own examples are fixed points.** All 16 corpus examples in §2 (2023 Q1–Q18) carry the verdict the rule gives them.
2. **T1 fires when the answer is a detail of the dated occasion itself:** what was launched, who signed, where it was conferred, the figure for the stated period. Also when the stem dates the fact ("as of 2025", "for 2023-24", "Union Budget 2024-25").
3. **A static fact behind a news hook is T3.** Examples: the Houthis' home country (2024 Q65), a new NATO Secretary-General's nationality (2024 Q49), a finalist's nationality (2026 Q39), a foreign bank's country (2026 Q74). The occupant or event is only the hook. The asked fact does not decay.
4. **Project and installation geography is T3,** per the §2 highway example. This covers the bamboo-ethanol plant (2025 Q65), the underwater tunnel (2026 Q23), the underwater museum (2026 Q40) and the CHIRAG centre (2026 Q14). An *event* location stays T1: the city of a conferral (2026 Q4), the park of a release (2026 Q59).
5. **Fixed annual observance dates are T3:** World Mental Health Day, the International Day for the Elimination of Violence against Women, GST Day, Yoga Day. These are not occasions; they recur on the same date.
6. **Fixed history is T3:** 2015 flagship launches, Bindra 2008, historic Bharat Ratna conferrals, portfolios once held by a minister. T2 is limited to the *current* occupant.
7. **Product identity with no date in the stem is T3** (Nano Banana, Flippi).

## Effect on the v1 durable worksheet (not changed here)

`workbench/worksheets/RBI-GA-DURABLE-tags.csv` (PR #1168) is an input and is left untouched.

- **9 v1-tagged rows are now PERISHABLE,** and their tags would have to be withdrawn: 2023 Q35, Q38; 2024 Q2, Q3, Q5, Q15, Q22, Q62; 2025 Q9.
- **21 v2-durable rows carry no v1 tag,** and would need tagging:
  - 2023 Q31, Q43;
  - 2024 Q49;
  - 2025 Q2, Q14, Q19, Q33, Q37, Q65, Q80;
  - 2026 Q2, Q5, Q6, Q14, Q16, Q23, Q24, Q31, Q39, Q40, Q77.

The 12 v1 conflict rows: 9 match the v1 adjudication recommendation, and 3 go the other way (2025 Q65, 2026 Q24, 2026 Q77 are DURABLE under the rule).

## Confidence

235 high, 85 medium. Medium marks rows that a ruling above decides, or where the stem's anchor is implicit.
