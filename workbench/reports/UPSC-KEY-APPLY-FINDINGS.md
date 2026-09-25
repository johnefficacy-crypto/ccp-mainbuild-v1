# UPSC Prelims 2020 and 2024: key corrections resolved to option text (UPSC-KEY-APPLY-01)

**Worksheet:** `workbench/worksheets/UPSC-KEY-APPLY-2020-2024.csv` has 272 rows, one per question.

**Builder:** `workbench/scripts/upsc_key_apply_01.py` (stdlib only, no database access). Run it from the repo root and it
regenerates the worksheet and prints every count in this report.

**Inputs:**
- corpus rows from `workbench/sources/upsc-explanations-input.json`
- the 2020 Set C and 2024 Series D booklets in `workbench/sources/upsc-official-keys/`
- UPSC's final keys, transcribed from the upsc.gov.in scans

No database write was made. The explanation drafts, the earlier key-check worksheet and all years other than 2020 and 2024
are unchanged.

## 1. Summary, per year

**2020 GS Paper I, Set C**
- Keys to change: **17**. That is the 16 found by the letter-based check plus Q75.
- Where the defect comes from: the stored key came from `docs/reference/answer-keys/upsc_cse_2020_setc_prelims_gs1.csv`, which has wrong answers. On top of that, Q75's options were labelled by position.
- Repair: apply the 17 rows **by option id**. Replace the reference CSV with UPSC's Set C key. Reloading keys by letter is **not** safe, because it would re-break Q75.

**2024 GS Paper I, Series D**
- Keys to change: **19**, the same 19 the letter-based check found.
- Where the defect comes from: `rekey_2024_setd.sql` misread 19 letters of UPSC's Series D key. The Set-C-on-Set-D mistake did happen, but that SQL had already repaired it.
- Repair: apply the 19 rows by option id. On this paper that gives the same result as a letter reload from UPSC's Series D key, because option order matches the booklet on all 97 rows. Do not re-run `rekey_2024_setd.sql`. Do not import the keys in `pyq_2024_prelims_gs1_setc.json`.

**2024 CSAT Paper II**
- Keys to change: unknown. None of the 75 rows could be checked because there is no CSAT booklet.
- Repair: none possible from this worksheet.

After the changes, both GS papers can be trusted without reloading their option data. The two exceptions are small and
named in §6.

## 2. Part A: option order against the booklet

Each corpus question was matched to a booklet question by text. On all 197 GS rows the best text match is the booklet
question with the same number, with similarity ≥ 0.85 and a clear gap to the runner-up. Options were then compared by
printed label. Whitespace, punctuation, curly quotes and "1." versus "1)" were not counted as differences.

| Paper | Rows | ORDER_OK | ORDER_DIFFERS | TEXT_DIFFERS | UNCHECKABLE |
|---|---|---|---|---|---|
| 2020 GS (Set C) | 100 | 99 | 1 (Q75) | 0 | 0 |
| 2024 GS (Series D) | 97 | 97 | 0 | 0 | 0 |
| 2024 CSAT | 75 | 0 | 0 | 0 | 75 |
| **Total** | **272** | **196** | **1** | **0** | **75** |

**What this means for the 161 rows the letter-based check marked MATCH:** 160 of them sit on an ORDER_OK row, so a letter
match there is also a text match. The 161st is 2020 Q75. The letter-based check did not count it as MATCH but as
UNMAPPABLE. It is the only row in either GS paper where letters and texts disagree. No MATCH row becomes suspect.

**2020 Q75 — how it happened (evidence):**
- The Set C booklet's paragraph prints the options in the order (a) advisory, **(c) A bill of exchange**, (b) diary, (d) order.
- The corpus holds the same four texts in the same printed order, but labelled a, b, c, d by position. So corpus (b) is the
  booklet's (c), and corpus (c) is the booklet's (b).
- UPSC's key for Set C Q75 is C, meaning "A bill of exchange". The stored key is corpus (c), "A diary…", which is wrong.
- The correct target is corpus option (b), `fe6eeaa4-…`.
- No 2020 import JSON exists, so the step that assigned labels by position cannot be pinned to a file.

Three rows are ORDER_OK but carry a note:

| Row | Note |
|---|---|
| 2020 Q40 | The booklet prints "(a)" twice. The second one ("2, 3 and 4 only") is read as (d), the only label never printed, and it matches corpus (d). UPSC's key (C, "1 and 3 only") does not depend on that reading. |
| 2020 Q61 | The booklet reads "F�rfections", a scan artefact. The corpus reads "Perfections" (similarity ≥ 0.95). Same option. |
| 2024 Q71 | Options (b) and (c) both read "2 and 3 only", in the corpus **and** in the booklet. See §6. |

## 3. Part B: corrections by option text

A row needs correction when the corpus option the stored key points to is not the corpus option whose text equals the
booklet text under UPSC's letter.

| Paper | MATCH | CORRECTION | DROPPED | UNAPPLIABLE | UNAVAILABLE |
|---|---|---|---|---|---|
| 2020 GS | 81 | 17 | 2 (Q42, Q77) | 0 | 0 |
| 2024 GS | 78 | 19 | 0 | 0 | 0 |
| 2024 CSAT | 0 | 0 | 0 | 0 | 75 |
| **Total** | **159** | **36** | **2** | **0** | **75** |

- **Compared with the 35 from the letter-based check:** 36 keys need to change, the same 35 plus **2020 Q75**, which is newly
  resolved. It was UNMAPPABLE before and is now CORRECTION to corpus (b). No other row was newly found.
- **2020:** Q8, 20, 27, 32, 38, 49, 51, 52, 54, 55, 66, 68, **75**, 84, 86, 89, 90.
- **2024 GS:** Q20, 21, 22, 28, 41, 43, 52, 53, 58, 64, 65, 67, 70, 71, 75, 81, 83, 86, 100.
- **Dropped items:** 2020 Q42 and Q77 are dropped by UPSC and already have an empty stored key. No change is needed. They
  must stay unkeyed. The 2024 Series D drops (Q32, 37, 80) are not in the corpus.

**Scan check:** before trusting the transcriptions, I re-read every disputed letter against the UPSC scan: 17 in 2020, 19
in 2024. All 36 agree with the committed transcriptions. The full 100-letter 2020 Set C row also agrees with the scan.

## 4. Import sources

### 2020: the reference CSV fed the database; the CSV carries 17 wrong answers

Letters were compared by question number. "Scorable" leaves out UPSC-dropped items.

| Compared | Agreement |
|---|---|
| `upsc_cse_2020_setc_prelims_gs1.csv` vs stored DB key | 99/100 (differs only at Q82, where the DB carries UPSC's A and the CSV has D) |
| CSV vs UPSC Set C (scorable) | 81/98 |
| DB vs UPSC Set C (scorable) | 82/98 |
| CSV vs UPSC Sets A / B / D | 21 / 18 / 25 of 98 (chance level) |

**The operator's reading is confirmed.** The DB key is a faithful import of this CSV with one row (Q82) fixed. The CSV is
the right series but has 17 wrong letters: the 16 CORRECTION letters plus Q82. The wrong letters are not another series'
letters either: only 3, 2 and 7 of the 17 equal Sets A, B and D at the same number.

**Is replacing the CSV and reloading the cleaner repair?** Replacing the CSV, yes: the file should hold UPSC's Set C key so
that a future re-import cannot bring the errors back. Reloading **by letter**, no: Q75's letter is already correct (C), and
the corpus's (c) is the wrong text, so a letter reload leaves Q75 wrong. The 17 id-level changes in this worksheet are the
repair. Replacing the CSV is a follow-up to that repair, not a substitute for it.

### 2024: the Set C key really was applied to Series D questions, but that is no longer the state of the DB

| Compared | Result |
|---|---|
| `pyq_2024_prelims_gs1_setc.json` questions vs the Series D booklet, by text | 100/100 match the same number: **the questions are Series D** |
| JSON questions and option label→text vs corpus | 97/97 and 97/97 identical |
| JSON key vs UPSC Series C / Series D | **97/97** / 18/97: the key is exactly UPSC's Set C key |
| `upsc_cse_2024_setc_prelims_gs1.csv` vs UPSC Series C | 92/97 scorable. It is a Set C key, as its name says. |
| Stored DB key vs JSON key | 17/97 |
| Stored DB key vs UPSC Series D / C | 78/97 / 17/94 |
| Stored DB key vs `rekey_2024_setd.sql` | **97/97 identical** |

**What happened:**
1. The JSON paired a Series C key with Series D questions. Loaded by number, that would have left about 18 of 97 keys
   right, which is the chance-level outcome the brief warned about.
2. On 2026-09-03, commit `5f0f0f79` ("key 2024 fixed. earlier mistakenly Set C was used instead of set D") added
   `rekey_2024_setd.sql`. Its header says the DB "was keyed against Set C". The SQL clears every key on the paper and
   rewrites all 97 from a Series D transcription.
3. The exported corpus matches that SQL on all 97 rows, so the rekey was applied.

**Its Series D transcription is wrong on exactly the 19 CORRECTION rows.** For those 19, UPSC's scan agrees with the
committed transcription, not with the SQL. Those 19 wrong letters match Sets A, B and C on only 3, 5 and 3 rows, so they
are misreads, not series leakage.

**Consequences:**
- The 78 MATCH rows are genuine. They agree with UPSC's Series D key by letter and by text.
- The repair is not "reload from Series D". That was already done once, and the reload is where the 19 errors came from.
  The repair is the 19 id-level rows here, whose letters were checked against the scan.
- Because 2024 option order is ORDER_OK on all 97 rows, a letter reload from the committed Series D transcription would
  give the same end state. The id rows remain the safer form.
- **Do not re-run** `rekey_2024_setd.sql`.
- **Do not load** the keys in `pyq_2024_prelims_gs1_setc.json`. Doing so would put back about 79 wrong answers.

## 5. The other six years — is this confined to two papers?

`upsc.gov.in` could be reached this time. I fetched UPSC's final GS Paper I keys for 2018, 2019, 2021, 2022, 2023 and 2025
and transcribed them into `workbench/sources/upsc-official-keys/csp_2018_2025_gs1_key_transcription.py`, with the URLs in
its header. The 2025 upsc.gov.in key is the same document as the repo's `UPSC-CSE-2025-GS-1-set A-OFFCIAL-ANSWER-KEY.pdf`.

All comparisons below are by **letter**. Option order was not checked for these years; that would need the same
booklet-text pass.

| Year (series) | Stored DB key vs UPSC (scorable) | Reference CSV vs UPSC | CSV vs DB | Import JSON vs UPSC |
|---|---|---|---|---|
| 2018 (C) | **100/100** | 65/100 | 65/100 | 99/100 |
| 2019 (B) | **100/100** | 99/100 | 99/100 | 100/100 |
| 2021 (C) | **99/99** | 83/99 | 84/100 | 99/99 |
| 2022 (A) | **99/99** | 63/99 | 63/100 | 99/99 |
| 2023 (A) | **99/99** | 89/99 | 89/100 | 99/99 |
| 2025 (A) | **96/100**: wrong at Q56, Q71, Q81, Q88 | 96/100 | 100/100 | 96/100 |

- Each year's dropped items (2021 Q30, 2022 Q61, 2023 Q34) have an empty stored key.
- 2018 was checked against all four series. The DB agrees with Series C at 100 and with the others at 19–32, which
  confirms the series.

**Stored DB keys, apart from 2020 and 2024:**
- 2018, 2019, 2021, 2022 and 2023 agree with UPSC's final key on every scorable row.
- **2025 has 4 wrong keys**: Q56 (stored C, UPSC D), Q71 (D→B, the "Sedition has become my religion" question), Q81 (C→A)
  and Q88 (A→D). The 2025 DB key, CSV and JSON all agree with each other, so the 2025 source key itself is wrong on those
  four. This worksheet does not apply them (out of scope). They need their own text-level check, and there is no 2025
  booklet in the repository.

**Reference CSVs:** `docs/reference/answer-keys/` is unreliable. Five of the eight CSVs are materially wrong against
UPSC: 2018 (65), 2020 (81/98), 2021 (83/99), 2022 (63/99), 2023 (89/99). For 2018 and 2021–2023 the DB is right anyway;
those papers' import JSONs carry the correct keys, and `docs/reference/corrections/` exists for 2018, 2021 and 2022. For
2020 and 2025 the DB inherited the CSV's errors. 2024's CSV is a correct Set C key; the problem was pairing it with
Series D questions.

**Verdict on scope:** the defect is not confined to two papers. Three GS papers carry wrong stored keys: 2020 (17), 2024
(19) and 2025 (4). Five papers (2018, 2019, 2021, 2022, 2023) are clean by letter. 2026 GS (94 rows) and every CSAT paper
were not checked.

## 6. UNAPPLIABLE, UNCHECKABLE, and option-data defects

- **UNAPPLIABLE:** none. Every UPSC answer text matches exactly one corpus option.
- **UNCHECKABLE:** the 75 2024 CSAT rows. There is no CSAT booklet in the repository, so option order and a text-resolved
  key cannot be established. UPSC's CSAT key is reachable
  (`AnsKey-CivilServicesPExam-2024-GeneralStudies-II-210525.pdf`), but applying it by letter would repeat the risk this
  task exists to remove. It needs the CSAT booklet first.
- **Option data defect, 2024 Q71 (Greenfield airports):**
  - Evidence: options (b) and (c) both read "2 and 3 only" in the corpus and in the booklet .docx.
  - Inference: the real paper's (c) is almost certainly "1 and 3 only".
  - UPSC's answer (a) "1 and 2 only" is unique, so the correction applies safely. The duplicated option still needs an
    option-text repair.
- **Option labelling, 2020 Q75:** after the id fix the right text is keyed, but it sits under corpus label (b) while UPSC's
  booklet calls it (c). If labels are shown to learners next to "UPSC answer: (c)", swap the labels of (b) and (c) as well.
  That is a separate fidelity repair.

## 7. Can these papers be trusted once the changes are applied?

**2020 GS and 2024 GS: yes.** The option data does not need reloading.
- 196 of 197 rows have option order and text identical to UPSC's booklet.
- The one misordered row (Q75) is corrected by option id.
- Every stored key will then equal UPSC's final key by text.
- 2024 Q71's duplicated option remains a separate option-text repair.

**2024 CSAT: unknown.**

## 8. Evidence versus inference

**What the evidence shows:**
- 36 GS keys need to change: 17 in 2020 and 19 in 2024. Each target option id was resolved by text, and each disputed
  letter was re-read against the UPSC scan.
- 2020 Q75 is labelled by position, while the booklet prints the labels out of order.
- The 2020 DB key matches the 2020 reference CSV on 99 of 100 rows.
- The 2024 DB key matches `rekey_2024_setd.sql` on 97 of 97 rows. That SQL is a Series D reload that replaced an earlier
  Set C keying and misread 19 letters.
- The 2024 import JSON holds Series D questions with the exact Set C key.
- 2018, 2019, 2021, 2022 and 2023 DB keys match UPSC. 2025 has 4 mismatches.

**What I infer but have not proved:**
- The 2020 CSV and the 2021–2023 CSVs look like typed transcriptions made from a non-final or non-official key. Their
  error rates (11–37 per paper) are too high for UPSC-to-UPSC drift and they show no series signature.
- The 2025 differences may come from a provisional key. UPSC's scan is the final key dated 13-05-2026.
- 2024 Q71's missing option is probably "1 and 3 only".
- The Q75 position-labelling happened in an import step that is not in the repository.

## 9. Operator step (not done here)

1. Apply the 36 rows where `applies = yes`: set `pyq_questions.correct_option_id` to `new_correct_option_id` and move
   `pyq_options.is_correct` to match, by id and never by label. Each id was checked to belong to its own question.
2. Leave 2020 Q42 and Q77 unkeyed.
3. Retire or annotate `rekey_2024_setd.sql` and `pyq_2024_prelims_gs1_setc.json` so neither is re-run.
4. Replace `upsc_cse_2020_setc_prelims_gs1.csv` with UPSC's Set C key.
5. Open follow-ups for the four 2025 keys, the 2024 Q71 option text, the 2020 Q75 label swap, and the 2024 CSAT booklet.
