# RBI GA durable worksheet — v1 → v2 delta

- **v2 worksheet:** `workbench/worksheets/RBI-GA-DURABLE-tags-v2.csv` (203 rows, same 16-column spec as v1).
- **Classification of record:** `workbench/rbi-ga-classification-v2.csv` (203 DURABLE / 117 PERISHABLE, PR #1172).
- **v1 inputs, left untouched:** `workbench/worksheets/RBI-GA-DURABLE-tags.csv` (191 rows, PR #1168) and `workbench/rbi-ga-classification.csv`.

## Counts

| | rows |
|---|---:|
| Carried forward from v1 | **182** |
| Newly tagged in this pass | **21** |
| **v2 worksheet** | **203** = v2 DURABLE count 203 |
| Withdrawn (v1 row now PERISHABLE) | **9** |

- 182 carried + 21 new = 203.
- 182 carried + 9 withdrawn = 191 (the v1 worksheet).

Subjects in v2: general-knowledge 107, finance 86, economics 10.

## Carried forward (182)

The tag fields are verbatim from v1: subject_slug, subject_id, topic_id, topic_level, observed_difficulty, confidence, subject_corrected, section_id and question_text_excerpt. There are 0 mismatches on those fields across all 182 rows.

To meet the zero-blank-cell rule, the only edits were fills of cells that were blank in v1:
- `suggested_subject_original`: blank → `none` (81 rows);
- `topic_name` on finance/economics macro rows: blank → `<subject> (subject-level macro; no microtopic fits)` (11 rows);
- `notes`: blank → `Carried forward from v1 unchanged.` (30 rows).

## Withdrawn (9): now PERISHABLE under v2, T1 in every case

| year-Q | v1 subject | v1 topic | v2 reason |
|---|---|---|---|
| 2023 Q35 | finance | CBDC, stablecoins and crypto policy | CBDC pilot launch date |
| 2023 Q38 | general-knowledge | International agreements and declarations | Signatories of a dated declaration |
| 2024 Q2 | finance | Financial Inclusion Index and schemes | Union Budget 2024-25 change to the Tarun limit |
| 2024 Q3 | finance | Income-tax — penalties and PAN provisions | Union Budget 2024-25 de-penalisation |
| 2024 Q5 | finance | Bank advances — cash credit, overdraft, bill discounting | Union Budget 2024-25 proposal |
| 2024 Q15 | finance | NPCI systems — UPI, IMPS, NEFT, RTGS | Proposed UPI tax-payment limit, recent policy statement |
| 2024 Q22 | economics | Inflation targeting framework and the MPC | Repo increase over May 2022–Feb 2023 |
| 2024 Q62 | general-knowledge | Space missions and spacecraft | Aditya L1 first halo-orbit duration |
| 2025 Q9 | finance | GST — supply, input tax credit, zero-rated, exports | GST rate change effective 22 September 2025 |

## Newly tagged (21)

All 21 carry `suggested_subject_original = none` and `subject_corrected = no`: the v1 classification gave none of them a subject.

| year-Q | subject | level | topic | difficulty | confidence |
|---|---|---|---|---|---|
| 2023 Q31 | finance | macro | — (no insurance/asset-allocation microtopic) | medium | low |
| 2023 Q43 | economics | microtopic | Monetary policy transmission mechanism | medium | medium |
| 2024 Q49 | general-knowledge | microtopic | International organisations and groupings | easy | medium |
| 2025 Q2 | general-knowledge | microtopic | Computing and artificial intelligence | easy | medium |
| 2025 Q14 | general-knowledge | macro | Miscellaneous (observance date) | easy | low |
| 2025 Q19 | general-knowledge | microtopic | Union ministries and departments | medium | medium |
| 2025 Q33 | general-knowledge | macro | Miscellaneous (observance date) | easy | low |
| 2025 Q37 | general-knowledge | macro | Miscellaneous (observance theme) | medium | low |
| 2025 Q65 | general-knowledge | microtopic | Biofuel and renewable energy projects † | medium | medium |
| 2025 Q80 | general-knowledge | microtopic | World Heritage and protected sites † | easy | medium |
| 2026 Q2 | general-knowledge | microtopic | International organisations and groupings | easy | high |
| 2026 Q5 | general-knowledge | macro | Miscellaneous (observance date) | easy | low |
| 2026 Q6 | general-knowledge | macro | Miscellaneous (observance date) | easy | low |
| 2026 Q14 | general-knowledge | microtopic | Digital public platforms and e-governance technology | medium | low |
| 2026 Q16 | general-knowledge | microtopic | Computing and artificial intelligence | easy | medium |
| 2026 Q23 | general-knowledge | microtopic | Transport corridors and ports | medium | medium |
| 2026 Q24 | general-knowledge | microtopic | Biodiversity and wildlife conservation † | easy | medium |
| 2026 Q31 | general-knowledge | microtopic | Civilian awards and the honours system | easy | high |
| 2026 Q39 | general-knowledge | microtopic | Sports terminology and Indian sporting history | easy | low |
| 2026 Q40 | general-knowledge | microtopic | Landmarks and monuments | medium | low |
| 2026 Q77 | general-knowledge | microtopic | Urban development and governance missions † | easy | medium |

† The microtopic is taken from `workbench/rbi-gk-microtopic-map.csv` (migration 273). The other GK microtopics were chosen from migration 273's 55 names, and every name was checked against `app/supabase/migrations/273_general_knowledge_microtopics.sql`.

**Id handling:**
- GK microtopic ids are created live, so they read `NOT_IN_REPO`; the slug and section id are in `notes`.
- A GK macro row carries the section id as its topic_id.
- The finance macro row reads `NOT_IN_REPO`.

**Observance dates:** migration 273 has no microtopic for fixed observance days. Those 4 rows (2025 Q14, Q33; 2026 Q5, Q6), plus the 2025 Q37 theme, sit at the GK Miscellaneous section level. That is a candidate microtopic gap, not proposed here.

## The 12 formerly disputed rows, decided by v2

**4 are DURABLE and in the worksheet**, all newly tagged above:
- 2025 Q65
- 2025 Q80
- 2026 Q24
- 2026 Q77

**8 are PERISHABLE and not in the worksheet:**
- 2023 Q1 (T2)
- 2023 Q27 (T1)
- 2024 Q7 (T1)
- 2024 Q16 (T1)
- 2024 Q75 (T1)
- 2025 Q1 (T2)
- 2025 Q71 (T1)
- 2026 Q3 (T1)

## Catalogues used for id resolution

- **finance:** `workbench/catalogs/topic_catalog_regulatory.json`, subject_id `eb273a33-ea0e-4ca7-ac8f-32afe2be5d48`.
- **economics:** `workbench/catalogs/topic_catalog_regulatory.json`, subject_id `ede9de7a-f24e-4b3b-bba2-fdd8d10f3fff`.

Both are cross-checked against `workbench/catalogs/topic_catalog_rbi_full.json` (subject slug `finance` / `economics`). All 84 non-macro finance/economics topic_ids resolve, and each one's subject matches.

**general-knowledge:** microtopic names come from `app/supabase/migrations/273_general_knowledge_microtopics.sql`. Their ids are not in the repo.
