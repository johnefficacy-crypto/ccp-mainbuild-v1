#!/usr/bin/env python3
"""Reshape a ``--descriptive`` converter envelope into a generic CMS import body.

``scripts/docx_to_pyq_json.py --descriptive`` emits the v2 paper-importer
envelope, ``{"format_version": 2, "questions": [...]}``. The v2 paper importer
rejects descriptive rows on three independent gates (question_type is mcq-only,
options must be a list, options must contain at least 2 entries), and lifting
them was judged not worth widening that contract for five papers. The generic
CMS endpoint takes these rows as they are, so this script performs the one
transform between the two::

    {"format_version": 2, "questions": [...]}
        -> {"reason": ..., "entity": "pyq-questions", "rows": [...]}

Why this script is defensive out of proportion to its size
----------------------------------------------------------
The generic CMS path is a whitelist passthrough. It requires only
``pyq_paper_id`` and ``question_text``; ``question_number`` is optional and
nothing cross-checks it. That is exactly how 1,789 rows across 19 papers were
written with ``question_number`` NULL — the numbering lived only in
``display_order`` and had to be backfilled. Anything this script hands that
endpoint therefore carries an explicit ``question_number``, and the numbering is
asserted again after the reshape and before a single byte is written.

The same passthrough silently discards any key outside its whitelist, so a key
this script does not recognise is a hard error rather than a quiet loss.

Usage::

    python scripts/pyq_cms_body.py envelope.json \
        --paper-id 9ca02669-5875-4e97-b2bb-5f04ed49e94b \
        -o cms_body.json

Then POST the result to ``/api/admin/exam-intelligence-cms/bulk-import``.
"""
from __future__ import annotations

import argparse
import json
import sys

ENTITY = "pyq-questions"

# Mirrors _QUESTION_FIELDS in app/backend/app/api/admin_exam_intel_cms.py. The
# endpoint drops anything outside it without comment, so the mirror exists to
# turn that silence into an error here. Keep the two in sync.
CMS_QUESTION_FIELDS = frozenset({
    "pyq_paper_id", "question_number", "question_text",
    "normalized_question_hash", "question_type", "explanation_text",
    "observed_difficulty", "expected_solve_time_sec", "language", "metadata",
    "source_kind", "source_document_id", "source_page", "source_regions",
    "extractor_version", "extraction_run_id", "idempotency_key",
    "content_hash", "confidence_by_field",
    "section_id", "source_question_ref", "display_order",
})

# Envelope keys that belong to the v2 paper importer and have no CMS equivalent.
# Their presence means an MCQ envelope was passed, which this script refuses
# rather than silently dropping the options.
MCQ_ONLY_KEYS = ("options", "correct_option_label")

# Every emitted row carries these, always.
REQUIRED_IN_EVERY_ROW = ("pyq_paper_id", "question_number", "question_type",
                         "question_text", "source_question_ref")


def reshape(envelope: dict, *, paper_id: str, reason: str) -> dict:
    """Build the CMS bulk-import body from a descriptive converter envelope.

    Raises ValueError listing every problem at once, rather than failing on the
    first: an operator fixing a source document wants the whole list.
    """
    problems: list[str] = []

    if not isinstance(envelope, dict) or "questions" not in envelope:
        raise ValueError("not a converter envelope: expected an object with a 'questions' list")
    questions = envelope["questions"]
    if not isinstance(questions, list) or not questions:
        raise ValueError("envelope 'questions' must be a non-empty list")

    rows: list[dict] = []
    for i, q in enumerate(questions):
        where = f"questions[{i}]"
        if not isinstance(q, dict):
            problems.append(f"{where} is not an object")
            continue

        for key in MCQ_ONLY_KEYS:
            if key in q:
                problems.append(
                    f"{where} carries {key!r} — this is an MCQ envelope. Import it "
                    f"through the v2 paper importer, which handles options; "
                    f"reshaping it here would discard them."
                )

        qtype = q.get("question_type")
        if qtype != "descriptive":
            problems.append(f"{where} has question_type {qtype!r}, expected 'descriptive'")

        unknown = sorted(set(q) - CMS_QUESTION_FIELDS - set(MCQ_ONLY_KEYS))
        if unknown:
            problems.append(
                f"{where} carries {unknown} which the CMS whitelist would discard "
                f"without comment — drop them deliberately or add them to "
                f"CMS_QUESTION_FIELDS if the endpoint has gained them"
            )

        row = {k: v for k, v in q.items() if k in CMS_QUESTION_FIELDS}
        row["pyq_paper_id"] = paper_id
        # Set explicitly rather than left to the column default of 'manual'.
        # Nothing on the write path stamps this, so a bulk import is otherwise
        # indistinguishable from a row typed by hand.
        row["source_kind"] = "bulk_import"

        missing = [k for k in REQUIRED_IN_EVERY_ROW if row.get(k) in (None, "")]
        if missing:
            problems.append(f"{where} is missing required field(s) {missing}")

        rows.append(row)

    problems.extend(_numbering_problems(rows))

    if problems:
        raise ValueError("\n".join(problems))

    return {"reason": reason, "entity": ENTITY, "rows": rows}


def _numbering_problems(rows: list[dict]) -> list[str]:
    """question_number must be a contiguous 1..N run of integers.

    The CMS endpoint accepts the field as optional and never checks it, so this
    is the only place the guarantee exists.
    """
    problems: list[str] = []
    numbers: list[int] = []
    for i, row in enumerate(rows):
        n = row.get("question_number")
        if n is None:
            problems.append(f"rows[{i}] has no question_number")
        elif isinstance(n, bool) or not isinstance(n, int):
            problems.append(f"rows[{i}] question_number is {n!r}, expected an integer")
        else:
            numbers.append(n)
    if len(numbers) == len(rows) and numbers != list(range(1, len(rows) + 1)):
        problems.append(
            f"question_number values are {numbers}, expected a contiguous "
            f"1..{len(rows)} run"
        )
    return problems


def assert_every_row_numbered(rows: list[dict]) -> None:
    """Last gate before anything is written. Raises ValueError if any row would
    reach the CMS endpoint without a usable question_number."""
    problems = _numbering_problems(rows)
    if problems:
        raise ValueError(
            "refusing to write a body whose rows are not fully numbered — the CMS "
            "endpoint would accept them and leave question_number NULL:\n"
            + "\n".join(problems)
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("envelope", help="JSON emitted by docx_to_pyq_json.py --descriptive")
    ap.add_argument("--paper-id", required=True, help="pyq_papers.id to import into")
    ap.add_argument("--reason", default="bulk import of Phase II descriptive paper",
                    help="audit reason recorded by the CMS endpoint (min 8 chars)")
    ap.add_argument("-o", "--out", help="Write the CMS body here (default: stdout)")
    args = ap.parse_args(argv)

    if len(args.reason) < 8:
        print("--reason must be at least 8 characters (the CMS endpoint requires it)",
              file=sys.stderr)
        return 2

    with open(args.envelope, encoding="utf-8-sig") as fh:
        envelope = json.load(fh)

    try:
        body = reshape(envelope, paper_id=args.paper_id, reason=args.reason)
        # Belt and braces: reshape already checked, but nothing is written until
        # the numbering has been verified against the rows as they will be sent.
        assert_every_row_numbered(body["rows"])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    text = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(body['rows'])} rows to {args.out} "
              f"(entity={ENTITY}, paper={args.paper_id})", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
