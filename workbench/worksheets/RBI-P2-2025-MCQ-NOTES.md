# RBI Grade B 2025 Phase II MCQ — tagging notes

Companion to `workbench/worksheets/RBI-P2-2025-MCQ-tags.csv` (60 rows).
Source: `workbench/sources/rbi-phase2-2025-mcq.json`.
Catalogues: `topic_catalog_regulatory.json` (finance, management, economics, insurance,
pension-sector — matched on `subject_id`) and `topic_catalog_nabard_277.json`
(economic-social-issues — matched on `subject` slug).

Worksheet only. No POST, no live DB, no migration, no stimulus rows created.

---

## 1. Stimulus groups

12 groups covering 39 of the 60 questions. Each group's questions carry a **byte-identical**
passage repeated in full inside every `question_text` — the shared-prefix length is measured,
not assumed. These should be `pyq_stimuli` rows with the questions referencing them, the same
defect PR #1051 fixed elsewhere. **Not fixed here — enumerated so it can be scoped.**

| group | n | shared prefix (chars) | question_ids | what the passage is |
|---|---:|---:|---|---|
| `PMDDKY-2025` | 8 | 818 | `0541d59f-b575-4f4b-af14-40832341bcbd` ESI Q17<br>`e291a985-bbc3-435b-9fe2-2c312d7d9af7` ESI Q18<br>`4e1ebff5-9265-45c7-a578-64e025093728` ESI Q19<br>`c2d50ff5-5bee-48ca-956d-dde74e95656e` ESI Q20<br>`c915b2f1-d15b-4b58-8563-c23013e406fd` ESI Q21<br>`21b7ab30-32f3-49c6-88dc-c20ea27d10f8` ESI Q22<br>`247e610c-1898-4c51-98b2-252ce8e944e5` ESI Q23<br>`2f070e68-cefb-4fe3-b151-4862b9945fac` ESI Q24 | Pradhan Mantri Dhan-Dhaanya Krishi Yojana scheme background (budget blanks left unfilled in the passage itself). |
| `FAO-FRA-2025` | 4 | 1290 | `a424381f-3119-4f8a-8a65-76c8f6cf62d3` ESI Q25<br>`27c00ca1-58ea-4db6-aff9-5090aae709a4` ESI Q26<br>`b33636c8-f41e-4f3b-af56-702d8c743a2c` ESI Q27<br>`9d75a38c-082c-4ca7-9f6a-80aaa958d7f2` ESI Q28 | FAO mandate and the Global Forest Resources Assessment 2025 process. |
| `PMAY-U-2.0` | 4 | 1123 | `37ccaebb-d329-47c0-a0bc-fb668361997b` ESI Q29<br>`4a7d9ad0-4c79-428e-a31b-7d6fd2fa6c75` ESI Q30<br>`3daad2bb-85cf-4e7f-84ae-054a4b438937` ESI Q31<br>`bacb4a40-163e-434a-9613-295668c1e968` ESI Q32 | PMAY-U 2.0 outreach campaign launch, CRGFTLIH, Special Focus Groups. |
| `SEBI-MWPL-2025` | 4 | 513 | `1f979b1e-b13b-4083-95d0-eeb420d59afd` ESI Q33<br>`640ade24-4474-4690-895d-15f0378b9a7c` ESI Q34<br>`1a0d88a0-4163-4e27-87be-d7c3fcea6826` ESI Q35<br>`edd46f08-d848-4ea4-8906-2d867fd5a5e0` ESI Q36 | SEBI circular of 29 May 2025 on the equity derivatives framework and MWPL recalibration. |
| `NABFID-DFI` | 2 | 890 | `428cc00d-5dae-4886-b762-a78b6b187404` F&M Q7<br>`a4fd87e7-49ef-46bc-a485-d36d0f76604a` F&M Q8 | Description of an infrastructure-focused DFI granted AIFI status on 8 March 2022. |
| `NDS-OM` | 2 | 769 | `341a6e07-7991-418c-bb4c-b0d797d6ba56` F&M Q9<br>`ed82d1fc-16c9-42fc-afd1-d4845a1779ff` F&M Q10 | Description of RBI's anonymous order-matching platform for secondary G-sec trading. |
| `INVIT` | 2 | 814 | `b47ec150-b1cc-4130-8984-6d45e33fc72a` F&M Q11<br>`c607909a-a27a-4ec0-991c-3d28c6ce55f7` F&M Q12 | InvIT structure, SEBI regulation and cash-flow distribution. |
| `RATIO-BLOCK` | 3 | 119 | `b5d2bd95-ebb0-4628-bfa8-54f7c9477ba6` F&M Q13<br>`aa2a485b-0462-499a-b894-1f1176268ae3` F&M Q14<br>`7c8e3378-5f94-4de3-bb96-7f4f56820912` F&M Q15 | Five-line financial data block (Reserves, Equity, Debt to Net Worth, Asset Turnover, Gross Profit %). |
| `ETHICS-CASCADE` | 2 | 716 | `adcad044-c53f-4817-9360-7360a58215ab` F&M Q16<br>`43c6bf3c-4d30-4b9f-903b-d4891a9356c0` F&M Q17 | Unethical conduct cascading down a financial institution's hierarchy. |
| `MGMT-SCHOOLS` | 3 | 945 | `249bfc42-9a95-4f4d-bd40-0d8752e68793` F&M Q18<br>`3915d4b9-3492-47df-af9c-8a76f285608e` F&M Q19<br>`94dc7bd6-3e10-4bec-abe6-de1401dbc5ba` F&M Q20 | A manufacturing firm moving through scientific management, hierarchy, participation and systems thinking. |
| `NARASIMHAM-II` | 2 | 898 | `b1f3ba56-2124-45f8-b04a-ab8647d73b40` F&M Q21<br>`1e0491d8-d090-4143-83b6-6a933bbce658` F&M Q22 | The 1997 Narasimham Committee on banking-sector reform. |
| `TREDS` | 3 | 1032 | `fd6a8f5d-4abb-42f9-b849-389ab3ee314c` F&M Q24<br>`78d41388-4784-4bee-be9b-87bebc1f630c` F&M Q25<br>`f9f4f995-2878-494c-89f9-e47bf31f54a8` F&M Q26 | MSME delayed payments and electronic receivables discounting. |

**Duplicated passage text across the export: 39 questions carry 12 distinct passages.**
The `RATIO-BLOCK` group is the shortest at 119 characters and is a data block rather than prose,
but it is shared verbatim by three questions and belongs in the same fix.

21 questions carry no shared passage: ESI Q7-Q16, F&M Q23, Q27-Q36.

---

## 2. DEFECT rows

**1 row, not tagged.**

### ESI Q17 — `0541d59f-b575-4f4b-af14-40832341bcbd`

`topic_id = NEEDS_SOURCE`, `topic_level = NEEDS_SOURCE`, `topic_name = NEEDS_SOURCE`.

Carries the PMDDKY passage (agriculture, 100 underperforming districts) followed by:

> Which fintech company has signed MoU with the Ministry of Micro, Small and Medium
> Enterprises (MSMEs), and the Small Industries Development Bank of India, to register
> more small merchants?

Passage and stem are about different subjects and the intended stem is not recoverable
from this export. Left untagged per the brief.

### Same-class mismatches found in the other 59

The brief asked for a sweep. The mismatch is **not confined to Q17** — the whole first half of
the `PMDDKY-2025` group is affected, and two rows in `FAO-FRA-2025` are too. Six further
questions carry a passage that does not govern their stem:

| question | passage | what the stem actually asks | disposition |
|---|---|---|---|
| ESI Q18 `e291a985-bbc3-435b-9fe2-2c312d7d9af7` | PMDDKY | Udyam — the 2020 MSME formalisation platform, and SIDBI's assist platform | tagged on the question (stem is self-sufficient) |
| ESI Q19 `4e1ebff5-9265-45c7-a578-64e025093728` | PMDDKY | which authority regulates 'platform A' | tagged, **low** — see below |
| ESI Q20 `c2d50ff5-5bee-48ca-956d-dde74e95656e` | PMDDKY | MSME GDP/export shares per Economic Survey 2024-25 | tagged on the question |
| ESI Q26 `27c00ca1-58ea-4db6-aff9-5090aae709a4` | FAO/FRA forests | goals of the Green Credit Programme | tagged on the question |
| ESI Q27 `b33636c8-f41e-4f3b-af56-702d8c743a2c` | FAO/FRA forests | auditor selection under Environment Audit Rules 2025 | tagged on the question |

**ESI Q19 carries a second, independent defect.** Its stem refers to "platform A", but `A` is
defined in **Q18's stem**, not in the shared passage. As exported, Q19 is unanswerable in
isolation and will stay unanswerable after the passage is normalised into a `pyq_stimuli` row,
because the dependency is question-to-question rather than question-to-passage. It is tagged on
its MSME content at low confidence, but it needs a source check of its own.

ESI Q17 and Q20 are separately notable: four consecutive questions (Q17-Q20) under the PMDDKY
passage are all MSME questions, which is consistent with two different question blocks having
been concatenated under one passage during extraction.

---

## 3. Low-confidence rows, with reasons

**15 rows.** Every one is a catalogue gap, not an uncertain reading of the question —
with two exceptions, marked below.

- **ESI Q16** `d2248ef9-6299-4f8e-9641-3d7dfe54de47` → finance / Scheme types and fund of funds  
  SEBI Specialized Investment Funds 2025. GAP: no SIF or accredited-investor microtopic exists in finance; 'Scheme types and fund of funds' is the nearest active home.
- **ESI Q17** `0541d59f-b575-4f4b-af14-40832341bcbd` → economic-social-issues / NEEDS_SOURCE  
  DEFECT. PMDDKY passage followed by an unrelated MSME/SIDBI fintech-MoU question. Passage and stem do not match and the intended stem is not recoverable from the export. Not tagged.
- **ESI Q19** `4e1ebff5-9265-45c7-a578-64e025093728` → economic-social-issues / MSME sector and its contribution  
  MISMATCH: PMDDKY passage, but 'platform A' is defined in Q18's stem, not in the shared passage. The question is unanswerable in isolation. Tagged on its MSME content.
- **ESI Q23** `247e610c-1898-4c51-98b2-252ce8e944e5` → economic-social-issues / Sustainable agriculture missions  
  Which body reviews the PMDDKY district plan. GAP: no scheme-governance/committee microtopic in ESI; tagged to the parent mission topic.
- **ESI Q26** `27c00ca1-58ea-4db6-aff9-5090aae709a4` → economic-social-issues / Climate change initiatives in agriculture  
  MISMATCH: forests passage, Green Credit Programme question. GAP: no environment/forestry microtopic; tagged to climate-initiatives because GCP's listed activities include sustainable agriculture and water management.
- **ESI Q27** `b33636c8-f41e-4f3b-af56-702d8c743a2c` → economic-social-issues / Consumer protection and regulatory law  
  MISMATCH: forests passage, Environment Audit Rules 2025 question. GAP: no environmental-regulation microtopic; tagged to the regulatory-law topic as nearest active.
- **ESI Q33** `1f979b1e-b13b-4083-95d0-eeb420d59afd` → finance / Open interest interpretation  
  Objectives of the revised MWPL framework. GAP: no derivatives-overview microtopic; MWPL is an aggregate open-interest cap, so tagged to open-interest interpretation.
- **ESI Q34** `640ade24-4474-4690-895d-15f0378b9a7c` → finance / Open interest interpretation  
  Entity-level position limits for single stocks. Same catalogue gap as Q33.
- **ESI Q36** `edd46f08-d848-4ea4-8906-2d867fd5a5e0` → finance / Open interest interpretation  
  Spans pre-open session, MWPL basis and intraday monitoring. Same catalogue gap as Q33.
- **F&M Q13** `b5d2bd95-ebb0-4628-bfa8-54f7c9477ba6` → finance / Valuation ratios — price to book, price to earnings  
  Gross profit from the shared ratio block. GAP: no financial-statement-ratio microtopic in the six permitted subjects (commerce-accountancy is not permitted); 'Valuation ratios' is the nearest active home.
- **F&M Q14** `aa2a485b-0462-499a-b894-1f1176268ae3` → finance / Valuation ratios — price to book, price to earnings  
  Total debt from debt-to-net-worth. Same catalogue gap as Q13.
- **F&M Q15** `7c8e3378-5f94-4de3-bb96-7f4f56820912` → finance / Valuation ratios — price to book, price to earnings  
  Total liabilities from the same block. Same catalogue gap as Q13.
- **F&M Q16** `adcad044-c53f-4817-9360-7360a58215ab` → management / Concept and principles of corporate governance  
  'Everyone is doing it' justification. GAP: management has no business-ethics microtopic; tagged to corporate-governance principles as nearest active.
- **F&M Q32** `c9750969-9dd0-4541-82f4-e2116b5ce8b0` → management / Concept and principles of corporate governance  
  Moral absolutism. Same business-ethics gap as Q16.
- **F&M Q33** `3887be9d-ecf6-429a-aa9d-5b10bca32dc4` → management / Concept of morale  
  Attitudes influencing motivation and performance. Morale is the attitude construct; a833010e (Morale vs motivation) is an equally defensible home, which is why this is low.

### The gaps these rows are evidence for

| missing microtopic | subject | rows affected |
|---|---|---|
| environment / forestry / environmental regulation | economic-social-issues | ESI Q26, Q27 (and Q25, Q28 at medium) |
| derivatives overview and participants | finance | ESI Q33, Q34, Q36 (and Q35 at medium) |
| financial-statement ratio analysis | finance | F&M Q13, Q14, Q15 |
| business ethics | management | F&M Q16, Q32 |
| SIF / accredited investor | finance | ESI Q16 |
| scheme-governance and review committees | economic-social-issues | ESI Q23 |
| Weber and bureaucratic structure | management | F&M Q19 |

The two rows that are *not* pure catalogue gaps:

- **ESI Q19** — low because the question is defective (see §2), not because the catalogue is thin.
- **F&M Q33** — low because two management microtopics are equally defensible:
  `ba588c32` *Concept of morale* (chosen — morale is the attitude construct) and
  `a833010e` *Morale vs motivation*. A reviewer should pick one.

---

## 4. Two decisions a reviewer should look at

### 4.1 Atal Vayo — locked routing not followed

**ESI Q14 `7cc7dcad-b90e-4f35-b008-7a2cb53e13e5` is tagged `economic-social-issues` / *Welfare schemes for senior citizens*, not
pension-sector or insurance.**

The brief groups Atal Vayo with PMSBY, NPS and PM-SYM as "pension or insurance content" that
"must go to those subjects". The stem does not support that: Atal Vayo Abhyuday Yojana is an
old-age-home and senior-citizen grant scheme, and the four statements are about BPL age
eligibility, Ministry of Social Justice equity support to startups, minimum bedroom area per
resident, and the NGO grant share. No pension or insurance element appears. Neither
pension-sector (31 topics) nor insurance (26 topics) has a home for it, so following the
routing would have produced a wrong tag rather than a cross-subject one. The rule's stated
purpose — keep this content off an ESI or finance **macro** — is met either way: `a9893874`
*Welfare schemes for senior citizens* is a precise microtopic.

PMSBY, NPS and PM-SYM were routed as instructed.

### 4.2 PMSBY — the locked routing costs precision

**ESI Q7 is tagged `insurance` / *Group insurance and pensions* (`19ed7d9d`) as instructed.**
ESI's own `ec1c423a` *Life and accident insurance schemes for the poor* names this scheme class
more exactly, and insurance has no personal-accident microtopic. The tag is correct at sector
level and slightly loose at scheme level. Flagged, not overridden.

PM-SYM (ESI Q15) loses nothing by the same move: pension-sector `db2d5615` and ESI `75791278`
name the same thing.

---

## 5. Two things the brief assumed that do not hold in the repo

### 5.1 The six new microtopics are not resolvable

The brief lists six microtopics "added this session and available", to be resolved "from the
catalogue file or by name": `mgmt-organisational-change-and-resistance`,
`mgmt-barriers-to-communication`, `fin-derivatives-overview-and-participants`,
`esi-urban-development-and-smart-cities`, `esi-multiculturalism-and-diversity`,
`econ-official-statistics-and-household-surveys`.

**None of the six exists in any catalogue file on this branch**, by slug or by name. Every
`workbench/catalogs/*.json` file was searched for each slug and for the concepts behind them.
The live export that would have carried them, `ga_topic_ids_live.json` (regenerated today),
covers general-knowledge, finance, economics, insurance and pension-sector only — not
management, and not economic-social-issues. Resolving them would need a live call, which is out
of scope for this task.

Only one of the six would have been used by this paper:
`fin-derivatives-overview-and-participants`, which is the right home for ESI Q33, Q34 and Q36.
Those three are tagged to `3140dd31` *Open interest interpretation* at low confidence and say so
in `notes`. The other five are not needed by these 60 questions: no MCQ here is about
organisational change, communication barriers, smart cities, multiculturalism, or household
survey methodology. **Re-tagging when the six land is a three-row job, not a re-run.**

### 5.2 ESI topics carry no level

`topic_level` is `microtopic` for the 35 rows drawn from `topic_catalog_regulatory.json`, which
records a level per topic. It is `unstated` for the 24 rows drawn from
`topic_catalog_nabard_277.json`, which has no `level` field at all — all 134
economic-social-issues entries are `{id, text, slug, subject}`. The value is recorded as
`unstated` rather than guessed at `microtopic`. The one DEFECT row is `NEEDS_SOURCE`.

Judged by shape, the ESI entries are leaf topics comparable to the regulatory catalogue's
microtopics, but that is an inference and is not written into the worksheet.

---

## 6. Difficulty

Capped at `medium` throughout — this is a memory-based paper, so no observed difficulty can be
traced to anything harder. `easy` is used only where the stem is a single-clause direct recall
with no statement set and no computation:

- F&M Q8 — Development financial institutions — NABARD, SIDBI, NHB, NaBFID, EXIM
- F&M Q9 — NDS-OM and the G-sec auction platform
- F&M Q18 — Taylor's scientific management
- F&M Q23 — Phillips curve — short run and long run
- F&M Q24 — RBI, SEBI, IRDAI, PFRDA — mandate boundaries
- F&M Q27 — Upward, downward and lateral communication
- F&M Q28 — Financial inclusion and Jan Dhan
- F&M Q34 — Cost-push inflation

The remaining 52 rows are `medium`: multi-statement "which of the following is/are correct"
sets, specific numeric thresholds, or a computation from the shared data block.
