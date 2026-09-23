# Topic-id resolution report

**Resolution source:** `workbench/catalogs/ga_topic_ids_live.json` (PRs #1174, #1175). It holds five subjects:
- `general_knowledge`: 62 entries (55 microtopic + 7 topic);
- `finance_economics_macro`: 28 macros (17 finance + 11 economics);
- `insurance`: 31 entries (26 microtopic + 5 topic);
- `pension-sector`: 38 entries (31 microtopic + 7 topic);
- all five subject ids under `subjects`.

**Matching:** exact topic name within the row's subject. If there was no exact match, the name was compared again after collapsing whitespace and treating `-`, en dash and em dash as the same.

**Inputs, left untouched:** `RBI-GA-DURABLE-tags-v2.csv`, `RBI-GA-DURABLE-tags.csv` (v1) and `RBI-P2-DESCRIPTIVE-TOPICAL-tags.csv`.

**Outputs:** `RBI-GA-DURABLE-tags-v3.csv` and `RBI-P2-DESCRIPTIVE-TOPICAL-tags-v2.csv`. Each has the input's columns plus `resolution_status`.

No POSTs, no live DB, no migrations, no re-classification.

---

## 1. RBI-GA-DURABLE-tags-v3.csv (203 rows)

| resolution_status | rows |
|---|---:|
| ALREADY_PRESENT | 91 |
| RESOLVED_EXACT | 100 |
| RESOLVED_NORMALISED | 0 |
| MACRO_ASSIGNED | 9 |
| SUBJECT_MOVED | 2 |
| UNRESOLVED | **1** |
| **total** | **203** |

Subjects: general-knowledge 107, finance 84, economics 10, insurance 1, pension-sector 1.

`ALREADY_PRESENT` (91) covers:
- 84 finance/economics microtopic ids, verified in `topic_catalog_regulatory.json`;
- 7 GK section-level rows whose id is a GK section.

All 7 GK section ids appear in the live file as `level: topic`.

`RESOLVED_EXACT` (100) are the GK microtopic rows. Every `NOT_IN_REPO` name matched its live entry exactly.

### Subject moves (2)

Every finance and economics row was re-read for pension or insurance content, carried-forward v1 rows included. Two moved:

| row | old subject / level / topic | new subject / level / topic | why |
|---|---|---|---|
| 2024 Q4 | finance / macro / (subject level) | **pension-sector / microtopic / Withdrawal, exit and deferment rules** | "What percentage of money can be withdrawn from the National Pension Scheme (NPS) after 3 years?" This is an NPS withdrawal rule. |
| 2023 Q31 | finance / macro / (subject level) | **insurance / microtopic / Investment of insurance funds** | The question asks which company invests most of its AUM in central G-secs, then equities and state G-secs (answer LIC). That is investment of insurance funds. |

**Considered and kept on finance:**
- 2026 Q79 (PPF minimum contribution): PPF is a government small-savings scheme, not a PFRDA pension product.
- 2024 Q29, 2024 Q31, 2025 Q15 and 2026 Q15: these name IRDAI or PFRDA only as one regulator among several. The question is about regulatory mandates generally, or about SIDBI/EXIM.

No row involves reinsurance.

### Macro assignments (10 rows at subject level; 9 assigned, 1 unresolved)

Of the 12 subject-level rows proposed earlier, 2 moved subject (above), leaving these 10.

| row | subject | macro | reason |
|---|---|---|---|
| 2023 Q63 | finance | **Debt Market & Bond Analytics** | See below. |
| 2024 Q24 | finance | Banking Regulation & NBFCs | DEA Fund transfer of inoperative deposits is an RBI banking-regulation rule. |
| 2024 Q37 | finance | Banking Regulation & NBFCs | Banking-sector committees and their years of establishment. |
| 2024 Q42 | finance | Banking Regulation & NBFCs | Banking Ombudsman and digital-transactions ombudsman schemes. |
| 2025 Q41 | finance | Banking Regulation & NBFCs | RBI Interest Rate on Deposits Directions govern bank deposit pricing. |
| 2025 Q50 | finance | Payments, Fintech & Digital Finance | RBI FREE-AI framework on AI in financial services. |
| 2025 Q75 | finance | Banking Regulation & NBFCs | RB-IOS 2021 ombudsman tenure. |
| 2026 Q51 | finance | Capital Market — Secondary & Infrastructure | NIFTY 50 is the NSE secondary-market benchmark index. |
| 2026 Q61 | finance | Banking Regulation & NBFCs | PRAVAAH handles regulatory applications to the RBI. |
| 2025 Q13 | economics | **UNRESOLVED** | See below. |

**2023 Q63.** Question text:

> "To facilitate transparency and informed decision-making among the investors, markets regulator Sebi mandated additional requirements for the issuance and listing of ____ bonds. This is one of the sub-categories of 'green debt security'. These bonds are generally used for raising funds for transitioning to a more sustainable form of operations in line with India's intended nationally determined contributions."

The blank is the instrument itself (answer: transition). The stem identifies it by what it is and what it funds: a green-debt sub-category raising money for transition. The SEBI mandate is the frame of the sentence, not what is being tested. So the choice is **Debt Market & Bond Analytics**, not Securities Market Regulation.

**2025 Q13 — UNRESOLVED.** Question text:

> "The All-India Debt and Investment Survey (AIDIS), which collects detailed data on the assets, liabilities, and capital expenditures of Indian households in rural and urban areas, is conducted periodically by which of the following institutions?"

The question tests which institution runs a household survey (answer: National Statistical Office). Neither candidate fits:
- **Money & Banking** would fit a question about household credit or indebtedness. This one asks who administers the survey.
- **Public Finance** covers budgets, fiscal policy and taxation. A statistical survey is not a public-finance instrument.

None of the other 9 economics macros covers official statistics either. The row keeps `topic_id = NOT_IN_REPO`, `topic_level = macro` and `resolution_status = UNRESOLVED`. It needs a taxonomy decision (e.g. an official-statistics home) before it can be POSTed.

### Normalised matches

None. All 100 GK names and all 9 macro names matched exactly.

### UNRESOLVED rows: **1**

- 2025 Q13 (AIDIS), economics. Reason above.

---

## 2. RBI-P2-DESCRIPTIVE-TOPICAL-tags-v2.csv (48 rows)

| resolution_status | rows |
|---|---:|
| ALREADY_PRESENT | 48 |
| RESOLVED_EXACT | 0 |
| RESOLVED_NORMALISED | 0 |
| MACRO_ASSIGNED | 0 |
| SUBJECT_MOVED | 0 |
| UNRESOLVED | **0** |
| **total** | **48** |

Subjects: economic-social-issues 27, management 11, finance 10.

**No NOT_IN_REPO cells.** The input carries no `NOT_IN_REPO` values and no macro rows: all 48 rows are microtopic-level with real ids. So there was nothing to resolve, contrary to the brief's expectation.

**Id checks.** Every topic_id resolves, and its subject matches the row:
- finance and management: `topic_catalog_regulatory.json`;
- economic-social-issues: `topic_catalog_nabard_277.json`.

**Pension/insurance check.** All 48 rows were read for pension or insurance content, and none has any. The finance rows cover NBFCs, blockchain/CBDC, TLTRO, Retail Direct, ONDC, UPI credit lines, derivatives, growth vs value investing, AT1 bonds and the RBI's role. There are no moves.

**Encoding repair (6 rows, ids unchanged).** Six `topic_name` values carried `ΓÇö`, which is a UTF-8 em dash wrongly decoded as code page 437. They were inherited from `topic_catalog_rbi_full.json`, `topic_catalog_reg_full.json` and `topic_catalog_nabard_277.json`, which all carry the same mojibake. `topic_catalog_regulatory.json` has the correct em dash. Each repaired row's `notes` says so. The status stays `ALREADY_PRESENT` because the id was already present.

| row | before | after |
|---|---|---|
| 2022 ESI Q9 | NBFC categories ΓÇö IFC, Factor, P2P | NBFC categories — IFC, Factor, P2P |
| 2022 F&M Q13 | Monetary policy operations ΓÇö SDF, VRRR, LAF | Monetary policy operations — SDF, VRRR, LAF |
| 2023 F&M Q11 | Trait approach ΓÇö personality, intelligence, emotion | Trait approach — personality, intelligence, emotion |
| 2023 F&M Q15 | NPCI systems ΓÇö UPI, IMPS, NEFT, RTGS | NPCI systems — UPI, IMPS, NEFT, RTGS |
| 2024 F&M Q10 | Trait approach ΓÇö personality, intelligence, emotion | Trait approach — personality, intelligence, emotion |
| 2025 F&M Q5 | RBI Act 1934 ΓÇö constitution, note issue, functions | RBI Act 1934 — constitution, note issue, functions |

The three mojibake catalogues themselves are not modified here.

---

## 3. GK section count

The live catalogue has **7** GK sections. The 7th, **International Relations** (`level: topic`), does not exist in `app/supabase/migrations/273_general_knowledge_microtopics.sql`, which defines 6. No worksheet row uses it.

## 4. Validation

- **Row counts:** GA v3 **203**; P2 v2 **48**.
- **Status totals:** 91+100+0+9+2+1 = **203**; 48+0+0+0+0+0 = **48**.
- **Subject mismatches:** **0** rows whose resolved topic's subject differs from the row's subject_slug, in either worksheet. Topics were checked against the live file, `topic_catalog_regulatory.json` and `topic_catalog_nabard_277.json`. Every subject_id matches its slug.
- **Permitted subjects:** **0** rows on general-awareness in either worksheet. **0** GA rows are outside the five permitted subjects.
- **Difficulty:** **0** rows with observed_difficulty `hard`.
- **Blank cells:** **0** in either worksheet.
- **Duplicates:** **0** duplicate question_ids in either worksheet.
- **UNRESOLVED:** GA **1**, P2 **0**. `NOT_IN_REPO` remains on that single row only.
