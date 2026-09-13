# OPT-FRONTLOAD-02 — extend the v2 importer to accept descriptive questions

## PRIMING

Read in this order:

1. `workbench/investigations/OPT-FRONTLOAD-01_discovery.md` (branch
   `investigate/opt-frontload-01-discovery`)
2. `docs/status/2026-09-05-mains-optionals-strategy.md`
3. `POWERSHELL-SOP.md`

OPT-FRONTLOAD-01 established: neither importer path accepts this corpus, and
extending v2 is cheaper than 4,015 per-question POSTs because five of seven
MCQ-assuming consumers already fail closed on `question_type != 'mcq'`.

**Correction you must carry.** That report priced the extension off
`correct_option_label` being mcq-conditional at `:559`. That is true but
incomplete. `options` is required **unconditionally** in two further places, and
a descriptive row with no options fails at both:

- `_parse_v2_options_field` — a missing or null `options` returns
  `"options must be a list"` (JSON path) or
  `"options_json is required and must not be empty"` (CSV path)
- the row validator — `len(raw_opts) < 2` yields
  `"options must contain at least 2 entries"`

Neither sits inside a `qtype == "mcq"` branch. The change is therefore three
edits, not one. Verify all three against head and cite `path:line` before
writing any code; if head has moved, the line numbers above are stale but the
shape of the claim should still hold.

---

## PREFLIGHT — STOP gates

**G1.** Re-confirm the three edit sites. If `options` is already conditional at
head, stop and report — the task has shrunk and the plan needs re-cutting.

**G2.** `pyq_readiness` has no `question_type` filter, and its three-gate rule
requires `pyq_papers.trust_status = 'verified'`. Confirm both at head. State in
one sentence what a descriptive question does to readiness once loaded, given
the papers stay `pending` (see D2).

**G3.** The preflight has been run (2026-09-09). Its results are recorded in
`docs/status/2026-09-09-mains-optionals-strategy-rev2.md`, section "Confirmed
live". You do not need to re-run it, but confirm these three at head, because
each shapes the change:

- `marks` and `word_limit` are **not** columns on `pyq_questions`. They live in
  `metadata`, which already carries them on 60 and 8 rows.
- `uq_pyq_questions_idempotency_key` exists — a partial unique index on
  `idempotency_key`. An interrupted run can re-post the same rows safely, so the
  importer does not need a per-row existence check.
- `uq_pyq_question_one_primary_tag` exists **live and in no migration**. Out of
  scope here, but do not remove or rely on changing it.

---

## SINGLE FORCED STRATEGY

One PR, draft, auto-merge off. Extend the v2 importer to accept
`question_type = 'descriptive'` with no options. Change nothing else.

Branch: `feat/opt-frontload-02-v2-descriptive`

### Decisions, locked — do not re-open

- **D1.** `descriptive` joins `_QUESTION_TYPES_V2_SUPPORTED`. No other type is
  added. `numerical`, `caselet`, `matching` and `other` stay unsupported.
- **D2.** Optional papers load as `source_type='aggregator'`,
  `trust_status='pending'`, and are **never** promoted on a coaching URL alone.
  Migration `186` would let `source_url` clear the gate; migration `228` is the
  precedent for declining it, and this follows `228`. Coverage derivation does
  not gate on paper trust, so nothing downstream needs the promotion.
- **D3.** `options` becomes optional **only** when `qtype != 'mcq'`. For `mcq`
  every existing rule stands unchanged — 2+ entries, unique non-empty labels,
  `correct_option_label` resolving to exactly one.
- **D4.** `marks` and `word_limit` land wherever `OPT-PREFLIGHT-01.sql` block G3
  says they can. If no column exists they go in `metadata`, written
  read-merge-write — `metadata` is a whole-column replace and a bare update
  destroys sibling keys.
- **D5.** Rows the corpus flags are loaded, not silently dropped, and carry the
  flag into `metadata`: `structure_anomaly` (102 rows, `marks_inferred` null),
  `duplicate_in_source` (4 rows, Sociology 2014 Paper-2, corrupt at source),
  `map_item` (History Paper-1 Q1 is 20 location rows per year, not 5 sub-parts).
  A reviewer must be able to find them by query later.

### Work

1. The three edit sites from G1, and nothing adjacent.
2. Tests in `app/backend/tests/exam_intelligence/test_cms_pyq_bulk.py`:
   - a descriptive row with no `options` key preflights clean and commits
   - a descriptive row **with** options is accepted and the options are stored
   - an `mcq` row missing `options` still fails, with the message unchanged
   - an `mcq` row missing `correct_option_label` still fails
   - `numerical` is still rejected by type
3. Confirm no consumer regresses: run the existing suites for
   `pyq_mock_projection`, `pyq_readiness` and the CMS bulk tests.

---

## BLAST RADIUS

`app/backend/app/exam_intelligence/pyq_bulk_import.py` and its test file. Any
other modified path at the end must be reverted before committing.

### Already loaded, so do not create it

- 16 optional year-papers, `UPSC-CSE-MAINS-OPT-<year>`, aggregator/pending —
  `workbench/ledgers/OPT-LOAD-02_optional_year_papers.csv`
- 12 optional subjects and 12 sections on Mains phase
  `626ec667-4bbf-4420-8715-48c5b83e0d11` —
  `workbench/ledgers/OPT-LOAD-03_subjects_sections.csv`

The Mains phase now carries 17 sections. `section_ref` resolution must handle
that without ambiguity; section labels are unique (`Optional: <Subject> Paper-N`),
so confirm the resolver keys on the label and not on a prefix match.

## OUT OF SCOPE

- Loading any paper, question or subject — this PR ships the capability only
- Creating subjects or `exam_phase_sections` for optionals
- `pyq_readiness` and the PYQ Explorer card grouping — both need work regardless
  of load path, because the 1,131 GS rows already sit there; file them separately
- Promoting any paper to `verified`
- Topic tagging, and anything resting on `uq_pyq_question_one_primary_tag`
- The `POWERSHELL-SOP.md:17` direct-host correction — operator fix, one line

## VALIDATION

- BE and FE GitHub Actions green on the final commit
- New tests fail against the pre-change file and pass after — state both
- Cite `path:line` at head for every claim about existing behaviour

## OUTPUT / PUBLICATION

You are offline: no GitHub egress, no `gh` CLI, no push. Commit locally, report
the branch and the diffstat, and stop. The operator pushes and opens the draft PR.

Report: the three edit sites with before/after, the test list with pass/fail
either side of the change, and anything you found that contradicts a locked
decision above — flag it, do not act on it.
