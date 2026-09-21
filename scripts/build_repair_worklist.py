#!/usr/bin/env python3
r"""
build_repair_worklist.py - UPSC CSE Mains GS corpus repair worklist.

Fully OFFLINE and READ-ONLY: no DB connection, no network, no writes to any
input. The only files written are the two outputs listed below.

    .venv/Scripts/python scripts/build_repair_worklist.py

--------------------------------------------------------------------------------
INPUTS (read-only)

  A. Extraction (UnlockIAS aggregator), 1116 rows, 2013-2026, GS1-GS4:
        D:\Users\user\Downloads\unlockias-json\upsc-mains-all-years.json
     Fields used: year, paper, section_id, paper_section (GS4 only),
     paper_local_number, source_question_ref, question_text.

  B. DB export of public.pyq_questions, one JSON per year, as fetched from
     exam_id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 /
     exam_phase_id 626ec667-4bbf-4420-8715-48c5b83e0d11 (the Mains template
     phase that holds the GS papers):
        <repo>/pyq_2013_mains_questions.json ... pyq_2025_mains_questions.json
     Each file is either a bare list or a {items,total,limit,offset} envelope.
     Encoding varies (utf-8, utf-8-sig, utf-16) and is sniffed.
     Fields used: id, section_id, question_number, display_order,
     source_question_ref, question_text.

  C. DB export of public.pyq_question_topic_tags for the same corpus:
        <repo>/pyq_review_out/tags_export.json
     Used ONLY to compute has_tag = (question id appears in the tag export).

  Scope. Only the four GS section_ids are in scope. The Essay section
  (ea24354e-...) exists in the DB export but has no counterpart in the
  extraction; Essay rows are excluded from the worklist entirely rather than
  being emitted as spurious deletes. The count is reported in the summary.

  Years. The DB export covers 2013-2025; there is no 2026 Mains paper in it.
  2026 is therefore an extraction-only year and every 2026 row is an insert.
  This is a computed observation about the export, not an assertion about the
  live database.

OUTPUTS (the only files this script writes)
    workbench/audit/repair_worklist.csv
    workbench/audit/repair_summary.md

REQUIREMENTS
    python 3.12, rapidfuzz (3.14.x). No other third-party dependency.

--------------------------------------------------------------------------------
ALIGNMENT ALGORITHM

Rows are aligned on (year, section_id) + position WITHIN that section. The
DB's global question_number and the extraction's numbering are computed
differently (the DB numbers run across the whole year's paper set and, in some
years, split sub-parts into separate rows), so question_number is NEVER used
as a join key. It is carried through to the CSV as an identifier only.

For each (year, section_id) group present on either side:

  P1. Order the DB rows by display_order when every row in the group has one,
      else by question_number; ties broken by row id. Order the extraction
      rows by display_order, then paper_local_number.

  P2. Normalise each text once, then score every (db_row, extract_row) pair
      in the group:
          score = rapidfuzz.fuzz.partial_ratio(norm(extract_text),
                                               norm(db_text))
      norm(x) = drop non-ASCII, lowercase, keep [a-z0-9 ], collapse spaces.
      partial_ratio aligns the extraction text as a best-fit SUBSTRING of the
      DB text. This is deliberate and matches the prior UnlockIAS cross-check
      run: several DB rows carry a trailing "[Hindi] ..." mojibake block and a
      "(Answer in 150 words) 10 Marks" tail that the extraction does not have,
      and a symmetric ratio would penalise every one of those rows for text
      the extraction was never expected to hold.

  P3. Positional pass. If the group has equal counts on both sides and the
      index-wise pairing scores >= KEEP_MIN on EVERY pair, that pairing is
      accepted as final. The DB's own ordering is authoritative when it is
      consistent with the text.

  P4. Otherwise, greedy global pass. All pairs are sorted by score descending
      (ties broken by db index then extract index, so the result is
      deterministic) and taken in order while both sides are still free and
      score >= LINK_MIN. Below LINK_MIN two rows are never linked: a poor
      pairing is reported as an unmatched row on each side, not as a match.

  P5. Ambiguity. For each DB row, top1/top2 are its two best scores against
      the extraction side of its group. A row is AMBIGUOUS when top1 >=
      LINK_MIN and top1 - top2 < AMBIG_MARGIN - i.e. two counterparts are
      near-equally good and the alignment cannot be settled by text alone.
      An unmatched row is CONTESTED when its best counterpart scored
      >= CONTEST_MIN but was taken by another row. A contested row is not a
      missing question; it is an alignment the script refuses to guess at
      (this is what a DB group that splits sub-parts into separate rows, e.g.
      2013 GS4 Q1a/Q1b against a single extraction Q1, looks like).

  P6. GS4 paper_section. The extraction carries paper_section A/B (B is the
      case studies); the DB export does not carry it as a column (only some
      years encode it in source_question_ref, e.g. "GS4-B-Q1"). GS4 is
      therefore matched as ONE section group and the A/B split is left to the
      text, which separates cleanly: case studies are long and prose-like.
      No A/B is inferred onto DB rows.

ACTIONS
    keep     matched, score >= KEEP_MIN
    replace  matched, score <  KEEP_MIN, unambiguous, slot occupied
    insert   extraction row with no DB slot
    delete   DB row with no counterpart
    review   ambiguous alignment, needs a human. Emitted when:
             - a matched pair scores < KEEP_MIN AND is either ambiguous (P5)
               or non-positional inside an equal-count group;
             - an unmatched row is contested (P5);
             - an unmatched DB row falls in a group carrying a known source
               defect (SOURCE_DEFECT_GROUPS), where a delete could destroy a
               real question the aggregator simply lacks.

THRESHOLDS (all of them)
    KEEP_MIN      = 85.0  keep vs replace cut. Same cut as the prior runs.
    LINK_MIN      = 60.0  below this, two rows are never linked at all.
    CONTEST_MIN   = 75.0  an unmatched row counts as contested (-> review
                          rather than insert/delete) only when the counterpart
                          it lost scored at least this. Below it the
                          similarity is not distinctive: GS4 case studies are
                          long English prose and two unrelated ones routinely
                          score 60-65 against each other, which would turn
                          genuinely missing questions into review noise.
    AMBIG_MARGIN  =  5.0  top1 - top2 under this = ambiguous alignment.
    DUP_MIN       = 95.0  near-duplicate scan within one side of a group,
                          reported in the summary only; changes no action.

SOURCE CONFIDENCE
    aggregator-only  2016, 2017, 2018, 2023 - no official source exists for
                     those years and none can be obtained.
    aggregator       every other year.

SOURCE DEFECTS carried through, NOT fixed
    - 2015 and 2017 GS4 skip Q10 in the aggregator. 2015 GS4 therefore has 5
      Section-B case studies where every other year has 6, and the DB may hold
      a real sixth that UnlockIAS lacks. Unmatched DB rows in those two groups
      are emitted as 'review', never 'delete'.
    - 2019 GS-I Q16 and Q17 are the same question reworded (the hyphen
      differs), so an exact-match dedupe misses it. The near-duplicate scan
      (DUP_MIN) reports it; no action row is changed.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz

REPO = Path(__file__).resolve().parents[1]
EXTRACT_JSON = Path(r"D:\Users\user\Downloads\unlockias-json\upsc-mains-all-years.json")
DB_GLOB = "pyq_2*_mains_questions.json"
TAGS_JSON = REPO / "pyq_review_out" / "tags_export.json"
OUT_CSV = REPO / "workbench" / "audit" / "repair_worklist.csv"
OUT_MD = REPO / "workbench" / "audit" / "repair_summary.md"

EXAM_ID = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
EXAM_PHASE_ID = "626ec667-4bbf-4420-8715-48c5b83e0d11"

KEEP_MIN = 85.0
LINK_MIN = 60.0
CONTEST_MIN = 75.0
AMBIG_MARGIN = 5.0
DUP_MIN = 95.0

SECTION_TO_PAPER = {
    "daca2e9f-012e-46fc-8b10-b6df340b4200": "GS1",
    "d332fcad-6750-4542-af0a-3f203f819096": "GS2",
    "b5cbb735-b687-4de5-90cb-3978f48a71a1": "GS3",
    "dee30326-920a-40cf-bee0-a5b4c76760f7": "GS4",
}
ESSAY_SECTION = "ea24354e-0aa6-4102-a273-36773e3f52d6"

AGGREGATOR_ONLY_YEARS = {2016, 2017, 2018, 2023}
SOURCE_DEFECT_GROUPS = {
    (2015, "dee30326-920a-40cf-bee0-a5b4c76760f7"),
    (2017, "dee30326-920a-40cf-bee0-a5b4c76760f7"),
}

_WS = re.compile(r"\s+")
_KEEP = re.compile(r"[^a-z0-9 ]")


def norm(text: str) -> str:
    """Drop non-ASCII, lowercase, keep [a-z0-9 ], collapse whitespace."""
    if not text:
        return ""
    ascii_only = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return _WS.sub(" ", _KEEP.sub(" ", ascii_only.lower())).strip()


def load_json(path: Path):
    """Read a JSON file whose encoding may be utf-8, utf-8-sig or utf-16."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, UnicodeError, json.JSONDecodeError):
            continue
    raise SystemExit("cannot decode " + str(path))


def items_of(doc):
    return doc["items"] if isinstance(doc, dict) and "items" in doc else doc


def load_db():
    """DB rows in scope, grouped by (year, section_id)."""
    groups: dict[tuple[int, str], list[dict]] = defaultdict(list)
    essay = 0
    files = sorted(REPO.glob(DB_GLOB))
    if not files:
        raise SystemExit("no DB export files match " + DB_GLOB)
    for path in files:
        year = int(re.search(r"pyq_(\d{4})_", path.name).group(1))
        for row in items_of(load_json(path)):
            sid = row.get("section_id")
            if sid == ESSAY_SECTION:
                essay += 1
                continue
            if sid not in SECTION_TO_PAPER:
                continue
            groups[(year, sid)].append(
                {
                    "id": row.get("id"),
                    "question_number": row.get("question_number"),
                    "display_order": row.get("display_order"),
                    "ref": row.get("source_question_ref") or "",
                    "text": row.get("question_text") or "",
                }
            )
    for rows in groups.values():
        if all(r["display_order"] is not None for r in rows):
            rows.sort(key=lambda r: (r["display_order"], str(r["id"])))
        else:
            rows.sort(key=lambda r: (r["question_number"] or 0, str(r["id"])))
    return groups, essay, [p.name for p in files]


def load_extract():
    groups: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for row in load_json(EXTRACT_JSON):
        sid = row.get("section_id")
        if sid not in SECTION_TO_PAPER:
            continue
        groups[(int(row["year"]), sid)].append(
            {
                "local": row.get("paper_local_number"),
                "display_order": row.get("display_order"),
                "ref": row.get("source_question_ref") or "",
                "paper_section": row.get("paper_section") or "",
                "text": row.get("question_text") or "",
            }
        )
    for rows in groups.values():
        rows.sort(
            key=lambda r: (
                r["display_order"] if r["display_order"] is not None else 0,
                r["local"] or 0,
            )
        )
    return groups


def load_tagged_ids() -> set:
    return {t["question_id"] for t in items_of(load_json(TAGS_JSON)) if t.get("question_id")}


def top_two(scores):
    if not scores:
        return (0.0, 0.0)
    ordered = sorted(scores, reverse=True)
    return (ordered[0], ordered[1] if len(ordered) > 1 else 0.0)


def align(db_rows, ex_rows):
    """Return (pairs, db_unmatched, ex_unmatched, matrix, positional_used)."""
    n, m = len(db_rows), len(ex_rows)
    db_norm = [norm(db["text"]) for db in db_rows]
    ex_norm = [norm(ex["text"]) for ex in ex_rows]
    matrix = [
        [float(fuzz.partial_ratio(e, d)) for e in ex_norm]
        for d in db_norm
    ]
    if n == m and n > 0 and all(matrix[i][i] >= KEEP_MIN for i in range(n)):
        return [(i, i, matrix[i][i]) for i in range(n)], [], [], matrix, True

    candidates = sorted(
        ((matrix[i][j], -i, -j) for i in range(n) for j in range(m)),
        reverse=True,
    )
    db_free, ex_free = set(range(n)), set(range(m))
    pairs = []
    for score, neg_i, neg_j in candidates:
        if score < LINK_MIN:
            break
        i, j = -neg_i, -neg_j
        if i in db_free and j in ex_free:
            db_free.discard(i)
            ex_free.discard(j)
            pairs.append((i, j, score))
    pairs.sort(key=lambda p: p[0])
    return pairs, sorted(db_free), sorted(ex_free), matrix, False


def near_duplicates(rows):
    out = []
    normed = [norm(r["text"]) for r in rows]
    for a in range(len(rows)):
        for b in range(a + 1, len(rows)):
            score = float(fuzz.ratio(normed[a], normed[b]))
            if score >= DUP_MIN:
                out.append((a, b, score))
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    db_groups, essay_rows, db_files = load_db()
    ex_groups = load_extract()
    tagged = load_tagged_ids()

    keys = sorted(set(db_groups) | set(ex_groups), key=lambda k: (k[0], SECTION_TO_PAPER[k[1]]))
    out_rows = []
    per_year_actions = defaultdict(Counter)
    per_year_counts = defaultdict(lambda: [0, 0])
    dup_report = []

    for year, sid in keys:
        paper = SECTION_TO_PAPER[sid]
        db_rows = db_groups.get((year, sid), [])
        ex_rows = ex_groups.get((year, sid), [])
        per_year_counts[year][0] += len(db_rows)
        per_year_counts[year][1] += len(ex_rows)

        for a, b, score in near_duplicates(db_rows):
            dup_report.append((year, paper, "DB", db_rows[a], db_rows[b], score))
        for a, b, score in near_duplicates(ex_rows):
            dup_report.append((year, paper, "extraction", ex_rows[a], ex_rows[b], score))

        pairs, db_unmatched, ex_unmatched, matrix, _positional = align(db_rows, ex_rows)
        matched_db = {i: (j, s) for i, j, s in pairs}
        equal_counts = len(db_rows) == len(ex_rows)
        confidence = "aggregator-only" if year in AGGREGATOR_ONLY_YEARS else "aggregator"

        def emit(db_i, ex_j, score, action):
            db = db_rows[db_i] if db_i is not None else None
            ex = ex_rows[ex_j] if ex_j is not None else None
            has_tag = "" if db is None else ("true" if db["id"] in tagged else "false")
            out_rows.append(
                {
                    "year": year,
                    "paper": paper,
                    "section_id": sid,
                    "db_question_number": "" if db is None else db["question_number"],
                    "db_source_question_ref": "" if db is None else db["ref"],
                    "extract_paper_local_number": "" if ex is None else ex["local"],
                    "extract_source_question_ref": "" if ex is None else ex["ref"],
                    "db_text": "" if db is None else db["text"],
                    "unlockias_text": "" if ex is None else ex["text"],
                    "score": "" if score is None else "%.1f" % score,
                    "action": action,
                    "has_tag": has_tag,
                    "source_confidence": confidence,
                }
            )
            per_year_actions[year][action] += 1

        for i in range(len(db_rows)):
            if i in matched_db:
                j, score = matched_db[i]
                if score >= KEEP_MIN:
                    action = "keep"
                else:
                    t1, t2 = top_two(matrix[i])
                    ambiguous = t1 >= LINK_MIN and (t1 - t2) < AMBIG_MARGIN
                    crossed = equal_counts and j != i
                    action = "review" if (ambiguous or crossed) else "replace"
                emit(i, j, score, action)
            else:
                row_scores = matrix[i] if matrix else []
                best = max(row_scores) if row_scores else None
                contested = best is not None and best >= CONTEST_MIN
                defect_group = (year, sid) in SOURCE_DEFECT_GROUPS
                action = "review" if (contested or defect_group) else "delete"
                emit(i, None, best, action)

        for j in ex_unmatched:
            column = [matrix[i][j] for i in range(len(db_rows))]
            best = max(column) if column else None
            action = "review" if (best is not None and best >= CONTEST_MIN) else "insert"
            emit(None, j, best, action)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "year", "paper", "section_id", "db_question_number", "db_source_question_ref",
        "extract_paper_local_number", "extract_source_question_ref", "db_text",
        "unlockias_text", "score", "action", "has_tag", "source_confidence",
    ]
    out_rows.sort(
        key=lambda r: (
            r["year"],
            r["paper"],
            r["db_question_number"] if r["db_question_number"] != "" else 10 ** 6,
            r["extract_paper_local_number"] if r["extract_paper_local_number"] != "" else 10 ** 6,
        )
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    write_summary(out_rows, per_year_actions, per_year_counts, dup_report, essay_rows, db_files)
    print(str(OUT_CSV.relative_to(REPO)) + ": " + str(len(out_rows)) + " rows")
    print(str(OUT_MD.relative_to(REPO)))
    return 0


def _short(text: str, limit: int = 300) -> str:
    text = _WS.sub(" ", (text or "").strip())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def write_summary(out_rows, per_year_actions, per_year_counts, dup_report, essay_rows, db_files):
    actions = ["keep", "replace", "insert", "delete", "review"]
    totals = Counter()
    for year in per_year_actions:
        totals.update(per_year_actions[year])

    retag = [
        r for r in out_rows
        if r["action"] in ("replace", "insert", "delete") and r["has_tag"] == "true"
    ]
    retag_by_action = Counter(r["action"] for r in retag)
    reviews = [r for r in out_rows if r["action"] == "review"]

    lines = []
    lines.append("# UPSC GS Mains corpus repair worklist - summary")
    lines.append("")
    lines.append(
        "Generated by `scripts/build_repair_worklist.py`. Offline: no DB connection, no "
        "network, no writes to any input. Worklist only - nothing in the corpus was changed."
    )
    lines.append("")
    lines.append("- exam_id `" + EXAM_ID + "` / exam_phase_id `" + EXAM_PHASE_ID + "`")
    lines.append("- extraction: `" + str(EXTRACT_JSON) + "`")
    lines.append(
        "- DB export: " + str(len(db_files)) + " files, `" + db_files[0] + "` ... `" + db_files[-1] + "`"
    )
    lines.append("- tags: `pyq_review_out/tags_export.json` (drives `has_tag`)")
    lines.append(
        "- thresholds: KEEP_MIN=%g / LINK_MIN=%g / CONTEST_MIN=%g / AMBIG_MARGIN=%g / "
        "DUP_MIN=%g" % (KEEP_MIN, LINK_MIN, CONTEST_MIN, AMBIG_MARGIN, DUP_MIN)
    )
    lines.append(
        "- Essay rows in the DB export, excluded from the worklist (the extraction has no "
        "Essay, so they are not deletes): " + str(essay_rows)
    )
    lines.append("")

    lines.append("## Per year")
    lines.append("")
    lines.append(
        "| year | DB rows | extraction rows | " + " | ".join(actions) +
        " | worklist rows | source_confidence |"
    )
    lines.append("|---|---:|---:|" + "---:|" * len(actions) + "---:|---|")
    for year in sorted(per_year_counts):
        db_n, ex_n = per_year_counts[year]
        counts = per_year_actions[year]
        conf = "aggregator-only" if year in AGGREGATOR_ONLY_YEARS else "aggregator"
        lines.append(
            "| " + str(year) + " | " + str(db_n) + " | " + str(ex_n) + " | "
            + " | ".join(str(counts[a]) for a in actions)
            + " | " + str(sum(counts.values())) + " | " + conf + " |"
        )
    all_db = sum(v[0] for v in per_year_counts.values())
    all_ex = sum(v[1] for v in per_year_counts.values())
    lines.append(
        "| **all** | **" + str(all_db) + "** | **" + str(all_ex) + "** | "
        + " | ".join("**" + str(totals[a]) + "**" for a in actions)
        + " | **" + str(len(out_rows)) + "** | |"
    )
    lines.append("")

    lines.append("## Retagging load")
    lines.append("")
    lines.append(
        "Rows needing retagging - action in replace/insert/delete AND the DB row carries a "
        "topic tag: **" + str(len(retag)) + "**."
    )
    lines.append("")
    for action in ("replace", "delete", "insert"):
        lines.append("- `" + action + "` with a tag: " + str(retag_by_action[action]))
    lines.append("")
    lines.append(
        "`insert` rows have no DB row and therefore no tag by construction, so they "
        "contribute 0 to that total; they are new tagging work rather than retagging: "
        + str(totals["insert"]) + " rows."
    )
    lines.append("")

    lines.append("## Review rows - every one listed, these need a human")
    lines.append("")
    lines.append(str(len(reviews)) + " rows.")
    lines.append("")
    for r in reviews:
        head = (
            "### " + str(r["year"]) + " " + r["paper"]
            + " - DB #" + (str(r["db_question_number"]) or "-")
            + " (" + (r["db_source_question_ref"] or "no ref") + ")"
            + " vs extraction local #" + (str(r["extract_paper_local_number"]) or "-")
            + " (" + (r["extract_source_question_ref"] or "no ref") + ")"
            + " - score " + (r["score"] or "-")
        )
        lines.append(head)
        lines.append("")
        lines.append(
            "- has_tag: `" + (r["has_tag"] or "n/a") + "` / source_confidence: `"
            + r["source_confidence"] + "`"
        )
        lines.append("- **DB**: " + (_short(r["db_text"]) or "_(no DB row)_"))
        lines.append("- **UnlockIAS**: " + (_short(r["unlockias_text"]) or "_(no extraction row)_"))
        lines.append("")

    lines.append("## Source defects carried through, not fixed")
    lines.append("")
    lines.append(
        "- **2015 and 2017 GS4 skip Q10** in the aggregator. 2015 GS4 therefore has 5 "
        "Section-B case studies where every other year has 6. The DB may hold a real sixth "
        "that UnlockIAS lacks, so unmatched DB rows in those two groups are emitted as "
        "`review`, never `delete`."
    )
    lines.append(
        "- **2019 GS-I Q16 and Q17 are the same question reworded** - the hyphen differs, so "
        "an exact-match dedupe misses it. It is not repaired here; the near-duplicate scan "
        "below reports it and no action row is changed on account of it."
    )
    lines.append(
        "- **2026 has no DB rows in the export used here.** Every 2026 extraction row is "
        "therefore an `insert`."
    )
    lines.append("")
    lines.append(
        "### Near-duplicate scan (score >= %g, within one side of a group)" % DUP_MIN
    )
    lines.append("")
    if not dup_report:
        lines.append("No near-duplicate pairs found.")
    else:
        lines.append(str(len(dup_report)) + " pairs.")
        lines.append("")
        for year, paper, side, a, b, score in dup_report:
            ref_a = a.get("ref") or ("local #" + str(a.get("local")))
            ref_b = b.get("ref") or ("local #" + str(b.get("local")))
            lines.append(
                "- " + str(year) + " " + paper + " (" + side + ") - " + ref_a + " vs " + ref_b
                + ", score %.1f" % score
            )
            lines.append("  - " + _short(a["text"], 200))
            lines.append("  - " + _short(b["text"], 200))
    lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
