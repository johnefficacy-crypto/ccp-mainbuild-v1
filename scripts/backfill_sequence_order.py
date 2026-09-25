#!/usr/bin/env python3
"""Backfill reviewed parajumble ORDERS into pyq_questions.metadata.correct_order.

WHY. Parajumbles ("Sentence rearrangement (para jumble)", "Logical Order") are
stored as 4-option MCQs: ``pyq_options`` marks the correct OPTION ("B A D C"),
never the correct ORDER as data. The English drills page offers drag-to-reorder
and tap-to-swap, which need an order to grade against. Parsing option text at
render time fails silently on oddly formatted options and would show a learner
a wrong order marked right, so the order is derived HERE, offline, put in front
of a human on a worksheet, and only a reviewed row is written.

WHAT IT WRITES. On ``apply --apply --confirm`` each worksheet row whose
``decision`` is ``verified`` gets ``pyq_questions.metadata.correct_order``:

    {
      "version": 1, "verified": true,
      "order": ["B","A","D","C"],                  # the reviewed sequence
      "segments": [{"label":"A","text":"…"}, …],   # N segments, printed order
      "lead": "…", "tail": "…",                    # stem text around them
      "option_orders": {"<pyq_option_id>": [...]}, # every option's order
      "correct_pyq_option_id": "…",
      "verified_by": "…", "verified_at": "…", "worksheet": "…",
      "source": "scripts/backfill_sequence_order.py",
      "digest": "sha256:…"                         # binds all of the above
    }

The digest is computed by ``app/backend/app/study_os/sequence_order.py`` —
loaded by path, so the runtime and this script share ONE implementation. At
attempt freeze the runtime refuses a record whose digest does not match, or
whose correct option no longer agrees with the answer key, and the question
falls back to plain MCQ. Existing ``metadata`` keys are preserved (merge, then
PATCH through the CMS route, which audits the write).

    export  ->  READ-ONLY. For each mapped parajumble microtopic, list the
                verified tags, read each verified question + options (+ paper
                year), derive segments and orders, and write one worksheet CSV
                with a BLANK ``decision`` column. The first nine columns match
                the existing review worksheets
                (row_type,row_id,paper_year,question_number_or_topic_id,
                text_preview,flags,sample_reason,decision,notes).

    apply   ->  Reads the worksheet back. Only ``decision=verified`` rows are
                considered, and each is RE-DERIVED from live data first: a row
                whose derivation now has flags, or whose order / segments differ
                from what the reviewer signed, is refused (drift guard). Dry
                run unless BOTH ``--apply`` and ``--confirm`` are given.

Derivation never guesses. A row is flagged (and cannot be applied) when: no
option or more than one option is marked correct; any option is not a
permutation of one shared label set; two options name the same order; a label
is missing from the stem or appears more than once as a marker; fewer than two
segments are found; or a segment swallows a fixed sentence marker (S1/S6).

Usage:
    export CCP_API_BASE=https://<host> CCP_ADMIN_JWT=<admin jwt>
    python scripts/backfill_sequence_order.py export \\
        --out workbench/sequence-order-worksheet.csv
    # review: set decision=verified on rows a human has checked against the paper
    python scripts/backfill_sequence_order.py apply \\
        --worksheet workbench/sequence-order-worksheet.csv \\
        --reviewer "<name>" --reason "Reviewed parajumble orders vs source papers"
    python scripts/backfill_sequence_order.py apply ... --apply --confirm

Requires the ``exam_intelligence.cms`` permission.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import requests
except ImportError:  # pragma: no cover - offline tests never construct a Client
    requests = None  # type: ignore[assignment]

CMS = "/api/admin/exam-intelligence-cms"
DEFAULT_TIMEOUT = 120
_MAX_PAGES = 2000
SOURCE = "scripts/backfill_sequence_order.py"

# The parajumble microtopics — MUST equal the `pj` module's topics in
# app/frontend/src/features/study/english-drills/drillModules.js (a test
# enforces it).
PARAJUMBLE_TOPIC_IDS = (
    "8d10db27-adf4-21de-1e30-ac69023ab650",  # Sentence rearrangement (para jumble), migration 306
    "b2b889f0-5310-23a4-a50c-daa504f0afe7",  # Logical Order
)

# First nine columns = the existing review-worksheet shape; the rest carry the
# derivation the reviewer signs.
WORKSHEET_COLUMNS = [
    "row_type", "row_id", "paper_year", "question_number_or_topic_id",
    "text_preview", "flags", "sample_reason", "decision", "notes",
    "topic_id", "segment_count", "stem", "segments",
    "winning_option_text", "derived_order", "option_orders",
]
APPLY_DECISION = "verified"

_REPO = Path(__file__).resolve().parents[1]
_SEQ_MODULE_PATH = _REPO / "app" / "backend" / "app" / "study_os" / "sequence_order.py"


def _load_sequence_module():
    """Load the runtime's digest implementation by file path (stdlib-only module;
    importing the app package would pull in the whole backend)."""
    spec = importlib.util.spec_from_file_location("ccp_sequence_order", _SEQ_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


seq = _load_sequence_module()


# ── derivation (pure) ──────────────────────────────────────────────────────

_SEPARATORS = re.compile(r"[\s,\-–—>→.;:()\[\]/|]+")


def option_order(text: str | None) -> list[str] | None:
    """Labels named by an option, e.g. "B-A-D-C" / "(B) (A) (D) (C)" / "BADC".

    Accepted: every separator-delimited token is ONE label (A-Z or 1-9), or the
    whole option is ONE token that is a run of such labels ("BADC"). Nothing is
    case-folded, so prose ("None of these", "B, A and D") is not an order and
    returns None — it is flagged, never read as letters.
    """
    if not text:
        return None
    tokens = [tok for tok in _SEPARATORS.split(text.strip()) if tok]
    if len(tokens) >= 2 and all(re.fullmatch(r"[A-Z1-9]", tok) for tok in tokens):
        return tokens
    if len(tokens) == 1 and (re.fullmatch(r"[A-Z]{2,9}", tokens[0]) or re.fullmatch(r"[1-9]{2,9}", tokens[0])):
        return list(tokens[0])
    return None


def _marker_pattern(label: str) -> re.Pattern:
    # "(A) text", "A. text", "A) text", "A: text", "A - text" at a line/word start.
    return re.compile(
        r"(?:(?<=^)|(?<=[\s\n]))(?:\(\s*" + re.escape(label) + r"\s*\)|" + re.escape(label) + r"\s*[.):\-–])\s*",
        re.M,
    )


_FIXED_SENTENCE = re.compile(r"(?:^|\s)(?:\(?\s*S\s*[0-9]\s*\)?\s*[.:)\-–])", re.I)
# A question line printed AFTER the last sentence would otherwise be swallowed
# into it ("…D. Sentence.\nWhich is the correct sequence?").
_TRAILING_INSTRUCTION = re.compile(
    r"(?:\?\s*$|\b(?:correct|logical|proper|meaningful|coherent)\s+(?:order|sequence|arrangement)\b)", re.I
)


def split_segments(stem: str, labels: list[str]) -> tuple[str, list[dict], str, list[str]]:
    """(lead, segments in printed order, tail, flags). Segments empty when flagged."""
    flags: list[str] = []
    hits: list[tuple[int, int, str]] = []
    for label in labels:
        found = list(_marker_pattern(label).finditer(stem or ""))
        if not found:
            flags.append(f"label_missing_in_stem:{label}")
        elif len(found) > 1:
            flags.append(f"label_marker_ambiguous:{label}")
        else:
            hits.append((found[0].start(), found[0].end(), label))
    if flags:
        return "", [], "", flags
    hits.sort()
    lead = stem[: hits[0][0]].strip()
    segments = []
    for i, (_, end, label) in enumerate(hits):
        stop = hits[i + 1][0] if i + 1 < len(hits) else len(stem)
        text = stem[end:stop].strip()
        if not text:
            flags.append(f"empty_segment:{label}")
        if _FIXED_SENTENCE.search(text):
            flags.append(f"fixed_sentence_in_segment:{label}")
        if i == len(hits) - 1 and _TRAILING_INSTRUCTION.search(text):
            flags.append(f"instruction_in_last_segment:{label}")
        segments.append({"label": label, "text": text})
    if len(segments) < seq.MIN_SEGMENTS:
        flags.append("too_few_segments")
    return lead, (segments if not flags else []), "", flags


def derive(question: dict, options: list[dict]) -> dict:
    """Everything the worksheet shows and the apply step writes, plus flags."""
    flags: list[str] = []
    correct = [o for o in options if o.get("is_correct")]
    if not correct:
        flags.append("no_option_marked_correct")
    elif len(correct) > 1:
        flags.append("multiple_options_marked_correct")

    option_orders: dict[str, list[str]] = {}
    label_sets = set()
    for o in options:
        order = option_order(o.get("option_text"))
        if order is None:
            flags.append(f"option_not_an_order:{o.get('option_label') or o.get('id')}")
            continue
        if len(set(order)) != len(order):
            flags.append(f"option_repeats_a_label:{o.get('option_label') or o.get('id')}")
            continue
        option_orders[str(o["id"])] = order
        label_sets.add(tuple(sorted(order)))
    if len(label_sets) > 1:
        flags.append("options_disagree_on_labels")
    if option_orders and len({tuple(v) for v in option_orders.values()}) != len(option_orders):
        flags.append("two_options_name_one_order")

    labels = sorted(next(iter(label_sets))) if len(label_sets) == 1 else []
    lead, segments, tail = "", [], ""
    if labels:
        lead, segments, tail, seg_flags = split_segments(question.get("question_text") or "", labels)
        flags.extend(seg_flags)

    winner = correct[0] if len(correct) == 1 else None
    order = option_orders.get(str(winner["id"])) if winner else None
    if winner and order is None and "no_option_marked_correct" not in flags:
        flags.append("winning_option_not_an_order")
    return {
        "labels": labels,
        "lead": lead,
        "tail": tail,
        "segments": segments,
        "order": order or [],
        "option_orders": option_orders,
        "correct_pyq_option_id": str(winner["id"]) if winner else "",
        "winning_option_text": (winner or {}).get("option_text") or "",
        "flags": flags,
    }


def build_record(question_id: str, d: dict, *, reviewer: str, worksheet: str, now: str) -> dict:
    record = {
        "version": seq.RECORD_VERSION,
        "verified": True,
        "order": d["order"],
        "segments": d["segments"],
        "lead": d["lead"],
        "tail": d["tail"],
        "option_orders": d["option_orders"],
        "correct_pyq_option_id": d["correct_pyq_option_id"],
        "verified_by": reviewer,
        "verified_at": now,
        "worksheet": worksheet,
        "source": SOURCE,
    }
    record["digest"] = seq.record_digest(record, question_id)
    return record


# ── worksheet ──────────────────────────────────────────────────────────────

def _segments_cell(segments: list[dict]) -> str:
    return " | ".join(f"{s['label']}: {s['text']}" for s in segments)


def worksheet_row(topic_id: str, question: dict, paper_year: Any, d: dict) -> dict:
    stem = question.get("question_text") or ""
    return {
        "row_type": "question",
        "row_id": question["id"],
        "paper_year": paper_year if paper_year is not None else "",
        "question_number_or_topic_id": question.get("question_number") or "",
        "text_preview": re.sub(r"\s+", " ", stem)[:140],
        "flags": ";".join(d["flags"]),
        "sample_reason": "flagged" if d["flags"] else "clean",
        "decision": "",
        "notes": "",
        "topic_id": topic_id,
        "segment_count": len(d["segments"]),
        "stem": stem,
        "segments": _segments_cell(d["segments"]),
        "winning_option_text": d["winning_option_text"],
        "derived_order": " ".join(d["order"]),
        "option_orders": json.dumps(d["option_orders"], ensure_ascii=False, sort_keys=True),
    }


def write_worksheet(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORKSHEET_COLUMNS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def read_worksheet(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ── network ────────────────────────────────────────────────────────────────

class Client:
    def __init__(self, base: str, token: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        if requests is None:  # pragma: no cover
            raise RuntimeError("the 'requests' package is required for export/apply")
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}",
                                     "Content-Type": "application/json; charset=utf-8"})

    def get(self, path: str, params: dict | None = None) -> dict:
        r = self.session.get(f"{self.base}{path}", params=params or {}, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}

    def patch(self, path: str, body: dict) -> dict:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        r = self.session.patch(f"{self.base}{path}", data=data, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"PATCH {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}


def all_items(c, path: str, params: dict | None = None, page: int = 200) -> list[dict]:
    """Walk a CMS list route; stop when a page adds no unseen id (never on a
    short page — /pyq-options caps limit at 50)."""
    out: list[dict] = []
    seen: set = set()
    offset = 0
    for _ in range(_MAX_PAGES):
        items = (c.get(path, {**(params or {}), "limit": page, "offset": offset}).get("items") or [])
        fresh = [it for it in items if it.get("id") not in seen]
        if not fresh:
            break
        for it in fresh:
            seen.add(it.get("id"))
            out.append(it)
        offset += len(items)
    return out


def fetch_question(c, question_id: str) -> tuple[dict, list[dict]]:
    q = c.get(f"{CMS}/pyq-questions/{question_id}")
    opts = all_items(c, f"{CMS}/pyq-options", {"question_id": question_id}, page=50)
    return q, opts


# ── commands ───────────────────────────────────────────────────────────────

def do_export(c, topic_ids: Iterable[str], out: Path) -> dict:
    rows: list[dict] = []
    years: dict[str, Any] = {}
    seen_q: set[str] = set()
    for tid in topic_ids:
        tags = all_items(c, f"{CMS}/pyq-question-topic-tags", {"topic_id": tid, "reviewer_status": "verified"})
        for tag in tags:
            qid = str(tag.get("question_id") or "")
            if not qid or qid in seen_q:
                continue
            seen_q.add(qid)
            q, opts = fetch_question(c, qid)
            if q.get("reviewer_status") != "verified":
                continue
            pid = q.get("pyq_paper_id")
            if pid and pid not in years:
                try:
                    years[pid] = (c.get(f"{CMS}/pyq-papers/{pid}") or {}).get("year")
                except RuntimeError:
                    years[pid] = None
            rows.append(worksheet_row(tid, q, years.get(pid), derive(q, opts)))
    rows.sort(key=lambda r: (r["sample_reason"] != "flagged", str(r["paper_year"]), str(r["row_id"])))
    write_worksheet(rows, out)
    flagged = sum(1 for r in rows if r["flags"])
    return {"rows": len(rows), "flagged": flagged, "clean": len(rows) - flagged, "worksheet": str(out)}


def do_apply(c, worksheet: Path, *, reviewer: str, reason: str, write: bool, now: str | None = None) -> dict:
    now = now or datetime.now(timezone.utc).isoformat()
    report = {"considered": 0, "written": 0, "would_write": 0, "skipped_blank": 0,
              "skipped_other_decision": 0, "refused": [], "dry_run": not write}
    for row in read_worksheet(worksheet):
        decision = (row.get("decision") or "").strip().lower()
        if not decision:
            report["skipped_blank"] += 1
            continue
        if decision != APPLY_DECISION:
            report["skipped_other_decision"] += 1
            continue
        report["considered"] += 1
        qid = row["row_id"]
        q, opts = fetch_question(c, qid)
        if q.get("reviewer_status") != "verified":
            report["refused"].append((qid, "question_not_verified"))
            continue
        d = derive(q, opts)
        if d["flags"]:
            report["refused"].append((qid, "flags:" + ";".join(d["flags"])))
            continue
        # Drift guard: the reviewer signed THIS order over THESE segments.
        if " ".join(d["order"]) != (row.get("derived_order") or "").strip():
            report["refused"].append((qid, "order_changed_since_review"))
            continue
        if _segments_cell(d["segments"]) != (row.get("segments") or ""):
            report["refused"].append((qid, "segments_changed_since_review"))
            continue
        record = build_record(qid, d, reviewer=reviewer, worksheet=worksheet.name, now=now)
        if not seq.validate_record(record, qid):  # belt and braces: runtime must accept it
            report["refused"].append((qid, "record_fails_runtime_validation"))
            continue
        metadata = dict(q.get("metadata") or {})
        metadata[seq.METADATA_KEY] = record
        if not write:
            report["would_write"] += 1
            continue
        c.patch(f"{CMS}/pyq-questions/{qid}", {"reason": reason, "payload": {"metadata": metadata}})
        report["written"] += 1
    return report


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-base", default=None, help="API base URL (default: $CCP_API_BASE)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    sub = p.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="read-only: derive orders and write the review worksheet")
    ex.add_argument("--out", required=True, type=Path)
    ex.add_argument("--topic-id", action="append", default=None,
                    help="parajumble microtopic (repeatable; default: the drills page's two)")
    ap = sub.add_parser("apply", help="write reviewed orders (dry run unless --apply --confirm)")
    ap.add_argument("--worksheet", required=True, type=Path)
    ap.add_argument("--reviewer", required=True, help="who reviewed the worksheet (recorded as verified_by)")
    ap.add_argument("--reason", required=True, help="audit reason for the CMS write (8-500 chars)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base or not token:
        print("error: set CCP_API_BASE and CCP_ADMIN_JWT", file=sys.stderr)
        return 2
    c = Client(base, token, timeout=args.timeout)
    if args.cmd == "export":
        out = do_export(c, args.topic_id or PARAJUMBLE_TOPIC_IDS, args.out)
        print(json.dumps(out, indent=2))
        return 0
    if args.apply and not args.confirm:
        print("--apply needs --confirm to write; running as a dry run.", file=sys.stderr)
    write = bool(args.apply and args.confirm)
    report = do_apply(c, args.worksheet, reviewer=args.reviewer, reason=args.reason, write=write)
    print(json.dumps(report, indent=2, default=list))
    if not write:
        print("\nDRY RUN — nothing written. Re-run with --apply --confirm to PATCH.")
    return 1 if report["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
