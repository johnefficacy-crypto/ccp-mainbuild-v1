# UPSC Mains optionals — strategy amendment, revision 3.1

Amends `2026-09-10-mains-optionals-strategy-rev3.md` on the **sequence only**.
M1–M10 and their rev3 replacements stand unchanged.

Written 2026-09-11, after tagging all 4,038 optional questions.

---

## What rev3's sequence got wrong

Rev3 step 4 said "prove coverage isolation once", step 6 said "tag", and the
tagging plan that followed said to derive coverage afterwards and confirm
`exam_priority_score` is no longer flat.

It stays flat. All 392 PSIR Paper-I questions are tagged and its 127 coverage
rows still read `exam_priority_score = 0.00`.

**Coverage derivation does not read tags.** `coverage_derivation.py` states its
inputs are "locked snapshots + verified syllabus mentions", and that the score
is "copied verbatim from the locked snapshot — never recomputed here."
`score_snapshots.py` is what turns tags into scores, and it requires three
things verified before it will compute anything:

| gate | where | our state |
|---|---|---|
| papers `trust_status='verified'` | `score_snapshots.py:196` | **pending**, by M5 |
| questions `reviewer_status='verified'` | `:222` | pending |
| tags `reviewer_status='verified'` (primary only) | `:249` | pending |

and coverage reads only snapshots at `reviewer_status='locked'` (`:302`).

**The first gate is one we closed ourselves.** M5 holds the optional papers at
`pending` until the six LotusArise PDFs are registered as `document_assets` and
linked as `source_document_id`, because a coaching URL is not an auditable
anchor. That decision is right and is not being revisited here — but its
consequence is larger than M5 recorded. It does not merely delay readiness; it
blocks the entire scoring axis. Nothing downstream of it can produce a non-zero
priority score.

---

## Sequence, corrected

Steps 1–3 of rev3 are done. What follows replaces steps 4–8.

**Done**

1. `mention_type` corrected on the 183 unit mentions (SYL-FIX-01).
2. Twelve syllabus source files on `main`; reproducible input secured.
3. Coverage isolation proven on PSIR Paper-I — 127 rows written, `updated: 0`,
   456 GS rows untouched. M8-rev3 holds on `subject_id` alone.
4. **All 4,038 questions tagged**, one primary topic each, read individually.

**Next — and the order matters, because each gate feeds the one after**

5. **Register the six compiler PDFs as `document_assets`** and link each optional
   year-paper's `source_document_id`. This is the unblocking task for everything
   below, and it is the one nobody has started.
6. **Promote the 16 optional papers** to `trust_status='verified'` — via the
   document anchor, never on `source_url` alone (M5; migration `186:147-151`
   would accept a URL and no non-official paper has ever been promoted that way).
7. **Review the 4,038 questions.** Separate gate from tag review; neither implies
   the other.
8. **Review the 4,038 tags.** Primary-only is what the snapshot counts.
9. **Compute and lock a score snapshot.**
10. **Derive coverage.** Only now does `exam_priority_score` stop reading zero.

**Independent of the above, any time**

- M9's nine unscoped topic reads, as its own PR.
- `section_ref` plumbing (M10-rev3), so PSIR P1/P2, Geography P1 and Sociology
  P2 keep their official part divisions — currently `section_ref` is read by
  nothing and those divisions reach no database row.
- The three repairs behind an API deploy: 8 History map labels, 45 Sociology
  ligature rows, and the `load_mention_index` resume defect.

---

## One more thing M5 should have said

M5 recorded that the optionals have "a real route to `verified`, and it is the
same one the regulatory corpora took." True. What it did not say is that until
somebody walks that route, the optional corpus can be fully loaded, fully
tagged and fully isolated — as it now is — and still produce no ranking at all.

The 4,038 tags are not wasted; they are the input the snapshot will read. But
anyone looking at a flat `exam_priority_score` and wondering what went wrong
should look at step 5, not at the tagging.
