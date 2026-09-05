# Handoff — regulatory exam corpus (SEBI / IFSCA / PFRDA / RBI)

Written 2026-09-05, at the end of the UPSC session.

Read alongside `docs/status/2026-08-31-upsc-prelims-corpus-findings.md`. That
document is the UPSC work, but §7, §11 and §12 are platform-wide and apply
directly here.

---

## State

| exam | papers | years | questions | keyed | verified | tagged | difficulty | projected |
|---|---|---|---|---|---|---|---|---|
| sebi-grade-a | 48 | 2020-2025 | 440 | 440 | 402 | 402 | none | 402 |
| ifsca-grade-a | 43 | 2023-2025 | 444 | 435 | 362 | 362 | none | 362 |
| pfrda-grade-a | 47 | 2021-2025 | 201 | 192 | 142 | 142 | none | 142 |
| **rbi-grade-b** | **11** | **2022-2026** | **999** | **939** | **0** | **0** | **939** | **0** |

The three regulatory exams are keyed, tagged to microtopics, verified and
projected, all republished with `microtopic_id` populated on 2026-09-05. What
they lack is judged difficulty.

**RBI Grade B is the opposite and is the largest untouched corpus on the
platform** — 999 questions, more than the other three combined, 939 keyed and
939 carrying difficulty, but nothing verified, nothing tagged, nothing
projected. Note the difficulty is present without any tagging, which is unusual
and worth checking: it may be the August bulk default rather than judgement.

RBI by year: 2022 130q / 2 papers, 2023 204/2, 2024 210/2, 2025 264/4,
2026 191/1.

---

## The subjects are genuinely shared, and that is the important finding

| subject | microtopics | exams using |
|---|---|---|
| Finance | 100 | 3 |
| Companies Act 2013 | 91 | 2 |
| Management | 78 | 3 |
| Economics | 73 | 2 |
| Commerce & Accountancy | 62 | 3 |
| Costing | 58 | 3 |
| Pension Sector | 31 | 2 |

Plus the QRE subjects that CSAT also uses — Quantitative Aptitude, English
Language, General Intelligence & Reasoning.

Per-exam counts look lopsided (SEBI's Finance shows 60 microtopics, IFSCA's 40,
PFRDA's 20) but that is depth of coverage, not divergence: one catalogue, three
exams drawing from it unevenly.

**This answers §5.2 of `docs/status/2026-09-02-shared-qre-taxonomy-scope.md` in
practice.** The scope doc asks whether QRE subjects should be shared across
exams; four exams already share seven domain subjects and three QRE subjects.
`study_os/shared_core.py` partitions topics covered by two or more exams as
shared core, with cross-exam mastery deliberately fail-closed. Read it before
proposing anything — the model exists and is shipped.

---

## What applies here from the UPSC session

**§12 — `reviewer_status='draft'` on a bank row may mean "was invalidated", not
"unreviewed".** `183_pyq_mock_projection_bridge.sql:855-898` demotes a row to
draft whenever its projection goes stale or blocked. 872 of 906 regulatory rows
were in that state on 2026-09-05 with every paper and question verified. The fix
was a re-sync, never a promotion. Do not bulk-promote draft bank rows.

**§7 — `microtopic_id`.** Closed. Migration 270 populates it, and all three
exams were re-synced. Any newly projected paper gets it automatically; any paper
tagged after projection needs a re-sync.

**§11 — tagging a projected paper takes it offline until re-synced.** Changing a
tag or difficulty changes the content hash, which marks the projection stale,
which demotes the bank row to draft. Expect practice availability to drop while
a paper is being worked on, and re-sync when finished.

**PR #1065** fixed an unbatched `.in_()` that returned a false zero for
`practice_ready_count`. The regulatory exams are each under the 250-id ceiling
so they were never affected, but the same pattern exists in nine other
swallow points listed in that PR body.

---

## Suggested order

1. **Establish what RBI's 939 difficulty values are.** If every question is
   `medium`, it is the August import default and not judgement. One query:
   `select observed_difficulty, count(*) ... group by 1`. A single value across
   999 questions means defaulted.

2. **Decide the difficulty rubric before judging anything.** The UPSC Prelims
   rubric measures traceability — NCERT is easy, standard reference is medium,
   untraceable is hard. That transfers to regulatory papers only partly: there
   is no NCERT, but there is a standard-reference tier (the Acts themselves,
   ICAI material, the regulator's own circulars). Worth adapting deliberately
   rather than borrowing. CSAT's rule-derived difficulty is recorded in the
   handoff as "worth a real pass" — do not repeat that shortcut.

3. **RBI: verify, tag, then project.** 999 questions is roughly ten sittings at
   the pace the UPSC papers took. The subjects already exist, so tagging is
   against a live catalogue rather than building one.

4. **Difficulty for the three tagged exams** — 906 questions, no rubric yet.

5. **Multi-paper year grouping** (findings §13). IFSCA has up to 15 papers in a
   year, PFRDA 18, SEBI 12. The PYQ Explorer renders one card per paper, which
   produces 43 undifferentiated cards for SEBI. `subject_name` and `phase_name`
   are already on every row the endpoint returns.

---

## Operator notes that cost time on UPSC

- **The Supabase SQL editor auto-commits per execution.** An explicit `begin;`
  opens a nested transaction that is discarded. Statements silently roll back.
  Run migrations through `psql -f`, or paste without a wrapper.
- **An UPDATE that changes zero rows reports "Success. No rows returned"** —
  identical to one that changed eighty. Always follow with a SELECT.
- **Joining `pyq_options` or `pyq_question_topic_tags` inflates question counts.**
  A question with four options counts four times; a CSAT question with a primary
  and a secondary tag counts twice.
- **The editor caps display at 100 rows** and truncates long UUIDs pasted into a
  query. Use `\copy` for anything larger, with `$env:PGCLIENTENCODING = "UTF8"`.
- **`Invoke-RestMethod` header hashtables capture the token at creation.**
  Rebuild `$hdr` after every `$env:CCP_ADMIN_JWT` change.
- **`$pid` is a PowerShell built-in** and cannot be assigned.
- **The summary endpoint takes a slug, not an exam id**, and returns `paper_id`
  rather than `id` on each paper.
- **The API is free-tier Render** and cold-starts past the 60s client timeout.
  Warm it before any batch run. `pyq_question_review.py` still has no
  `--timeout` flag.

## Key ids

| thing | id |
|---|---|
| sebi-grade-a | query `exams` by slug |
| pfrda-grade-a | `85dbbb6c-0665-462c-aaf0-caaf268cc769` |
| projection preview | `GET /api/admin/mocks/pyq-papers/{id}/projection/preview` |
| projection sync | `POST …/projection/sync`, body `{audit_reason}` |
| summary | `GET /api/exam-intelligence/exams/{slug}/pyq-summary` |
