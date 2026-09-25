#!/usr/bin/env python3
r"""REG-CORPUS-03 — SME review worksheets, one CSV per corpus batch.

Writes ``workbench/corpus/reg/review/<batch>.csv`` from
``workbench/corpus/reg/out/<batch>.json`` and the REG-FACTCHECK-1 results.
No database access.

Row order:
  1. rows REG-FIX-1 changed (factcheck verdict ``wrong_key`` or ``fix_needed``);
  2. a seeded 10% random sample (rounded up) of the batch's ``confirmed`` rows,
     marked ``sample=Y``;
  3. every other row.
File order is kept inside each block. The same seed always picks the same sample.

Reviewers fill ``reviewer``, ``decision`` (verified | fix | reject), ``fix_note``
and ``minutes_spent``. An existing worksheet is never overwritten without
``--force``, so filled-in decisions are not lost by a re-run.

    python scripts/reg_corpus_worksheet.py                     # every batch
    python scripts/reg_corpus_worksheet.py --batch REG-CORPUS-CST
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reg_corpus_to_import as conv  # noqa: E402 — corpus/factcheck loaders, case splits

REVIEW_DIR = conv.REG / "review"
DEFAULT_SEED = "REG-CORPUS-03"
SAMPLE_RATE = 0.10
FIX_VERDICTS = ("wrong_key", "fix_needed")
DECISIONS = ("verified", "fix", "reject")
COLUMNS = [
    "id", "subject", "microtopic", "level", "factcheck_verdict", "verify_fact",
    "stem_excerpt", "keyed_answer", "ref", "sample",
    "reviewer", "decision", "fix_note", "minutes_spent",
]
_EXCERPT = 160


def _one_line(text: str) -> str:
    return " ".join(str(text or "").split())


def _excerpt(q: dict, split: tuple[str, str] | None) -> str:
    stem = _one_line(split[1] if split else q["stem"])
    if len(stem) > _EXCERPT:
        stem = stem[: _EXCERPT - 1].rstrip() + "…"
    return f"[case {q['stimulus_group']}] {stem}" if split else stem


def _keyed(q: dict) -> str:
    o = next(o for o in q["options"] if o["is_correct"])
    return f"{o['label']}. {_one_line(o['text'])}"


def _ref(q: dict) -> str:
    return " | ".join(_one_line(r.get("note")) for r in q.get("source_refs") or [] if r.get("note"))


def order_rows(questions: list[dict], factcheck: dict[str, str], *, batch: str,
               seed: str = DEFAULT_SEED) -> list[tuple[dict, bool]]:
    """``[(question, is_sample)]`` in worksheet order (see module docstring)."""
    fixed = [q for q in questions if factcheck.get(q["id"]) in FIX_VERDICTS]
    confirmed = [q for q in questions if factcheck.get(q["id"]) == "confirmed"]
    n = math.ceil(len(confirmed) * SAMPLE_RATE)
    picked = set(random.Random(f"{seed}:{batch}").sample([q["id"] for q in confirmed], n)) if n else set()
    sample = [q for q in confirmed if q["id"] in picked]
    taken = {q["id"] for q in fixed} | picked
    rest = [q for q in questions if q["id"] not in taken]
    return [(q, False) for q in fixed] + [(q, True) for q in sample] + [(q, False) for q in rest]


def worksheet_rows(questions: list[dict], factcheck: dict[str, str], *, batch: str,
                   seed: str = DEFAULT_SEED) -> list[dict]:
    splits, _ = conv.case_splits(questions)
    out = []
    for q, is_sample in order_rows(questions, factcheck, batch=batch, seed=seed):
        out.append({
            "id": q["id"],
            "subject": q["subject"],
            "microtopic": q["microtopic_name"],
            "level": q["rubric_level"],
            "factcheck_verdict": factcheck.get(q["id"], conv.NOT_FLAGGED),
            "verify_fact": "Y" if q.get("verify_fact") else "N",
            "stem_excerpt": _excerpt(q, splits.get(q["id"])),
            "keyed_answer": _keyed(q),
            "ref": _ref(q),
            "sample": "Y" if is_sample else "",
            "reviewer": "", "decision": "", "fix_note": "", "minutes_spent": "",
        })
    return out


def write_worksheet(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so spreadsheet apps read ₹ and — correctly.
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--batch", action="append", default=None, help="batch name (repeatable; default: all)")
    ap.add_argument("--seed", default=DEFAULT_SEED, help="sample seed (default %(default)s)")
    ap.add_argument("--out", type=Path, default=REVIEW_DIR)
    ap.add_argument("--corpus-dir", type=Path, default=conv.CORPUS_DIR)
    ap.add_argument("--factcheck", type=Path, default=conv.FACTCHECK_CSV)
    ap.add_argument("--force", action="store_true", help="overwrite existing worksheets")
    args = ap.parse_args(argv)

    try:
        corpus = conv.load_corpus(args.corpus_dir, args.batch)
        factcheck = conv.load_factcheck(args.factcheck)
    except conv.CorpusError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    existing = [b for b in corpus if (args.out / f"{b}.csv").exists()]
    if existing and not args.force:
        print(f"ERROR: worksheet(s) already exist, pass --force to overwrite: {existing}", file=sys.stderr)
        return 1
    for batch, questions in corpus.items():
        rows = worksheet_rows(questions, factcheck, batch=batch, seed=args.seed)
        write_worksheet(args.out / f"{batch}.csv", rows)
        fixed = sum(1 for r in rows if r["factcheck_verdict"] in FIX_VERDICTS)
        sample = sum(1 for r in rows if r["sample"] == "Y")
        print(f"{batch}: {len(rows)} rows · REG-FIX-1 {fixed} · sample {sample} · rest {len(rows) - fixed - sample}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
