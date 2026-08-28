#!/usr/bin/env python3
"""Repair cp1252-as-UTF-8 mojibake in PYQ question and option text — safely.

An import campaign on 2026-08-17 loaded PYQ content through a client that read
the UTF-8 source as Windows-1252 text and re-encoded it as UTF-8. Smart
punctuation was mangled in transit: ``India’s`` was stored as ``Indiaâ€™s``.
The bytes that reached the database are valid UTF-8, so nothing errored and
nothing downstream noticed.

This tool reverses that transform. It is deliberately shaped like
``scripts/pyq_question_review.py``: offline-first, dry-run by default, and it
never decides on its own that a row is repairable.

    scan    ->  read every question/option in scope, classify each text field,
                write a report with per-paper counts and before/after samples.
                READ-ONLY — it has no write path at all.

    repair  ->  read that scan report back, re-verify every row against the
                live value, and PATCH only rows the scan classified MANGLED.
                Dry-run unless BOTH --apply and --confirm are given.

    THE SCAN REPORT IS THE DECISION GATE. ``repair`` refuses to run without
    one, so a human has always had the chance to read the before/after pairs
    before anything is written. If a row's live text has drifted since the
    scan, that row is skipped rather than overwritten.

Why the inverse is not just ``.encode('cp1252')``
-------------------------------------------------
cp1252 leaves five byte slots undefined (0x81, 0x8D, 0x8F, 0x90, 0x9D), and
0x9D is the third byte of ``”`` (U+201D) — common in this corpus. Python's
cp1252 codec raises on those; the .NET Windows-1252 encoding that did the
damage passes them through as C1 control codepoints. The mapping here mirrors
.NET, so the inverse is exact where a naive cp1252 round-trip would fail.

Hashes
------
``pyq_questions.normalized_question_hash`` and
``pyq_options.normalized_option_hash`` were computed by the create endpoint
FROM THE MANGLED TEXT, and migration 224 puts a unique index on
``(pyq_paper_id, normalized_question_hash)``. Repairing text without
re-hashing would leave dedup comparing clean incoming hashes against stale
mangled ones — future imports would not dedup at all.

This tool does not compute hashes itself. The CMS PATCH endpoints already
re-hash when ``question_text``/``option_text`` changes and no hash is supplied
(``update_pyq_question`` / ``update_pyq_option``), so the fix is to send the
text and NOT send a hash. ``_patch_payload`` enforces that, and a test locks
it. Before applying, ``repair`` checks that no two rows in a paper collapse to
the same repaired hash, which would violate that unique index mid-run.

Usage::

    export CCP_API_BASE=...      # e.g. https://<host>
    export CCP_ADMIN_JWT=...     # admin/super_admin JWT

    # 1. Scan (always read-only).
    python scripts/repair_pyq_mojibake.py scan \
        --exam-id <uuid> --out mojibake_scan.json

    # ... a human reads the report's before/after samples ...

    # 2. Repair — dry run, writes a diff report and nothing else.
    python scripts/repair_pyq_mojibake.py repair \
        --scan mojibake_scan.json --out mojibake_diff.json

    # 3. Repair for real.
    python scripts/repair_pyq_mojibake.py repair \
        --scan mojibake_scan.json --out mojibake_diff.json \
        --audit mojibake_audit.jsonl --apply --confirm

Both subcommands need ``exam_intelligence.cms`` and
``ADMIN_STUDY_OS_ENABLED=true`` on the target backend.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable

try:  # requests is only needed for the live paths, not for the offline tests
    import requests
except ImportError:  # pragma: no cover - exercised only where requests is absent
    requests = None

CMS = "/api/admin/exam-intelligence-cms"

DEFAULT_EXAM_ID = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"  # UPSC CSE

# The five byte values cp1252 leaves undefined. .NET's Windows-1252 passes them
# through as the matching C1 control codepoint; Python's codec raises. Modelling
# .NET is what makes the inverse exact on ” (U+201D = E2 80 9D).
_C1_PASSTHROUGH = {0x81, 0x8D, 0x8F, 0x90, 0x9D}

# Row classifications. Only MANGLED is ever repaired.
CLEAN = "clean"              # ASCII, or unchanged by the round-trip
MANGLED = "mangled"          # exact, lossless inverse available
AMBIGUOUS = "ambiguous"      # looks damaged but the inverse is not provably exact
NON_LATIN = "non_latin"      # carries characters cp1252 cannot represent (e.g. Devanagari)


# ─── the inverse mapping ────────────────────────────────────────────────────
def mangle(text: str) -> str:
    """Model the damage: UTF-8 bytes read as .NET Windows-1252 text.

    Used to *verify* a candidate repair, never to modify data.
    """
    return "".join(
        chr(b) if b in _C1_PASSTHROUGH else bytes([b]).decode("cp1252")
        for b in text.encode("utf-8")
    )


def demangle(text: str) -> str | None:
    """Reverse the damage, or None when this text cannot have been damaged this way.

    Returns None rather than raising so callers can treat "not applicable" and
    "broken" the same way: leave the row alone.
    """
    try:
        raw = bytes(
            ord(ch) if ord(ch) in _C1_PASSTHROUGH else ch.encode("cp1252")[0]
            for ch in text
        )
    except (UnicodeEncodeError, ValueError):
        return None  # character outside the cp1252 repertoire — not this bug
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None  # not the byte pattern this bug produces


def _has_lost_characters(text: str) -> bool:
    """Replacement chars or stray C1 controls mean the transform lost data."""
    return any(ch == "�" or unicodedata.category(ch) == "Cc" and ch not in "\t\n\r"
               for ch in text)


def classify(text: str | None) -> tuple[str, str | None]:
    """Decide what, if anything, to do with one text field.

    Returns ``(classification, repaired_text_or_None)``. A row is only ever
    MANGLED when the inverse is provably exact:

    1. every character is representable in the cp1252 + C1 repertoire — text
       carrying Devanagari or any other script cannot have come from this bug;
    2. the resulting bytes are valid UTF-8;
    3. the result actually differs from the input;
    4. re-mangling the result reproduces the input **byte for byte** — this is
       the strong check, and it is what rules out coincidental matches;
    5. the result carries no replacement characters or stray C1 controls;
    6. the result is not itself still mangled — double-mangled text is a
       different repair and is left for a human.
    """
    if not text:
        return CLEAN, None
    if text.isascii():
        return CLEAN, None

    repaired = demangle(text)
    if repaired is None:
        # Either non-cp1252 characters, or bytes that are not valid UTF-8.
        try:
            text.encode("cp1252")
        except UnicodeEncodeError:
            return NON_LATIN, None
        return CLEAN, None

    if repaired == text:
        return CLEAN, None
    if mangle(repaired) != text:
        return AMBIGUOUS, None
    if _has_lost_characters(repaired):
        return AMBIGUOUS, None
    if demangle(repaired) not in (None, repaired):
        # Repairing once leaves something that still round-trips — the row was
        # mangled more than once, or the text genuinely looks like mojibake.
        return AMBIGUOUS, None
    return MANGLED, repaired


# ─── HTTP client (mirrors scripts/pyq_question_review.py) ───────────────────
class Client:
    def __init__(self, base: str, token: str, timeout: int = 60) -> None:
        if requests is None:  # pragma: no cover - environment guard
            raise RuntimeError("the 'requests' package is required for live calls")
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}",
             "Content-Type": "application/json; charset=utf-8"}
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self.session.get(f"{self.base}{path}", params=params or {}, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}

    def patch(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        r = self.session.patch(f"{self.base}{path}", data=data, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"PATCH {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}

    def all_items(self, path: str, params: dict[str, Any] | None = None,
                  page: int = 50) -> list[dict]:
        """Loop offset until a short page. ``page`` is 50 because
        GET /pyq-options caps limit at 50 (``le=50``)."""
        out: list[dict] = []
        offset = 0
        while True:
            d = self.get(path, {**(params or {}), "limit": page, "offset": offset})
            items = d.get("items") or []
            out.extend(items)
            if len(items) < page:
                return out
            offset += page


# ─── scope ──────────────────────────────────────────────────────────────────
def select_papers(papers: Iterable[dict], phase_ids: set[str] | None,
                  paper_ids: set[str] | None) -> list[dict]:
    """Narrow to the operator's scope; no scope means every paper in the exam.

    Unlike the review tool, scanning the whole exam is the safe default here —
    ``scan`` cannot write, and a corruption sweep wants the widest view.
    ``repair`` is bounded by the scan file, not by this.
    """
    out = list(papers)
    if paper_ids:
        return [p for p in out if p.get("id") in paper_ids]
    if phase_ids:
        return [p for p in out if p.get("exam_phase_id") in phase_ids]
    return out


# ─── scan ───────────────────────────────────────────────────────────────────
def scan_rows(questions: list[dict], options_by_q: dict[str, list[dict]]) -> list[dict]:
    """Classify every text field. Pure — no I/O, no mutation."""
    rows: list[dict] = []
    for q in questions:
        cls, repaired = classify(q.get("question_text"))
        rows.append({
            "kind": "question",
            "id": q.get("id"),
            "question_id": q.get("id"),
            "question_number": q.get("question_number"),
            "classification": cls,
            "old": q.get("question_text"),
            "new": repaired,
        })
        for o in options_by_q.get(q.get("id"), []):
            ocls, orep = classify(o.get("option_text"))
            rows.append({
                "kind": "option",
                "id": o.get("id"),
                "question_id": q.get("id"),
                "question_number": q.get("question_number"),
                "option_label": o.get("option_label"),
                "classification": ocls,
                "old": o.get("option_text"),
                "new": orep,
            })
    return rows


def summarise(rows: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        bucket = out.setdefault(r["kind"], {CLEAN: 0, MANGLED: 0, AMBIGUOUS: 0, NON_LATIN: 0})
        bucket[r["classification"]] += 1
    return out


def do_scan(c: Client, args: argparse.Namespace) -> int:
    phase_ids = {p.strip() for p in (args.exam_phase_id or []) if p.strip()} or None
    paper_ids = {p.strip() for p in (args.paper_id or []) if p.strip()} or None

    all_papers = c.all_items(f"{CMS}/pyq-papers", {"exam_id": args.exam_id})
    papers = select_papers(all_papers, phase_ids, paper_ids)
    if not papers:
        print(f"error: no papers in scope for exam {args.exam_id} "
              f"(checked {len(all_papers)}).", file=sys.stderr)
        return 1

    report: dict[str, Any] = {"exam_id": args.exam_id, "papers": []}
    grand = {"question": {MANGLED: 0, AMBIGUOUS: 0, NON_LATIN: 0, CLEAN: 0},
             "option": {MANGLED: 0, AMBIGUOUS: 0, NON_LATIN: 0, CLEAN: 0}}

    for p in sorted(papers, key=lambda x: (str(x.get("year")), str(x.get("id")))):
        pid = p["id"]
        questions = c.all_items(f"{CMS}/pyq-questions", {"pyq_paper_id": pid})
        options_by_q: dict[str, list[dict]] = {}
        for q in questions:
            if q.get("id"):
                options_by_q[q["id"]] = c.all_items(f"{CMS}/pyq-options", {"question_id": q["id"]})
                if args.sleep:
                    time.sleep(args.sleep)
        rows = scan_rows(questions, options_by_q)
        counts = summarise(rows)
        for kind, bucket in counts.items():
            for k, v in bucket.items():
                grand[kind][k] = grand[kind].get(k, 0) + v

        affected = [r for r in rows if r["classification"] in (MANGLED, AMBIGUOUS)]
        report["papers"].append({
            "paper_id": pid,
            "year": p.get("year"),
            "paper_code": p.get("paper_code"),
            "exam_phase_id": p.get("exam_phase_id"),
            "question_count": len(questions),
            "counts": counts,
            "rows": affected,     # only rows repair will consider
        })
        q_m = counts.get("question", {}).get(MANGLED, 0)
        o_m = counts.get("option", {}).get(MANGLED, 0)
        print(f"  {p.get('year')} {pid[:8]}  questions {len(questions):>4}  "
              f"mangled q={q_m:>4} opt={o_m:>4}  "
              f"ambiguous={sum(c2.get(AMBIGUOUS, 0) for c2 in counts.values())}")

    report["totals"] = grand
    print(f"\nTOTAL mangled: questions={grand['question'][MANGLED]} "
          f"options={grand['option'][MANGLED]}")
    print(f"      ambiguous (skipped, need a human): "
          f"questions={grand['question'][AMBIGUOUS]} options={grand['option'][AMBIGUOUS]}")
    print(f"      non-Latin (left alone): "
          f"questions={grand['question'][NON_LATIN]} options={grand['option'][NON_LATIN]}")

    out = Path(args.out)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote scan report -> {out}")
    print("Read the before/after pairs in that file before running repair.")
    return 0


# ─── repair ─────────────────────────────────────────────────────────────────
def _patch_payload(kind: str, new_text: str, reason: str) -> dict[str, Any]:
    """Build the CMS write envelope.

    Deliberately sends ONLY the text field. The PATCH endpoints re-hash when
    the text changes and no hash is supplied, so omitting the hash is what
    keeps ``normalized_question_hash`` / ``normalized_option_hash`` correct
    after the repair. Sending a hash here would suppress that.
    """
    field = "question_text" if kind == "question" else "option_text"
    return {"reason": reason, "payload": {field: new_text}}


def _read_live_text(c, kind: str, row: dict) -> str | None:
    """Fetch the row's current text, for the pre-write drift check.

    Questions have a single-row route; options do NOT — the CMS exposes only
    ``GET /pyq-options?question_id=``. Reading an option through its parent
    question is therefore the only way to see its live value, and getting this
    wrong would 404 on every option and silently skip the whole option repair.
    """
    if kind == "question":
        live = c.get(f"{CMS}/pyq-questions/{row['id']}")
        return (live.get("row") or live).get("question_text")
    listing = c.get(f"{CMS}/pyq-options", {"question_id": row.get("question_id"),
                                           "limit": 50, "offset": 0})
    for item in listing.get("items") or []:
        if item.get("id") == row["id"]:
            return item.get("option_text")
    return None  # option no longer present under that question


def hash_collisions(rows: list[dict]) -> list[tuple[str, list[str]]]:
    """Rows in one paper whose repaired text collapses to the same canonical form.

    Migration 224 puts a unique index on (pyq_paper_id, normalized_question_hash),
    so two questions repairing to the same text would fail the second UPDATE
    mid-run. Detected up front rather than discovered halfway through.
    """
    seen: dict[str, list[str]] = {}
    for r in rows:
        if r["kind"] != "question" or r["classification"] != MANGLED:
            continue
        canon = " ".join((r["new"] or "").split()).lower()
        seen.setdefault(canon, []).append(r["id"])
    return [(k, v) for k, v in seen.items() if len(v) > 1]


def do_repair(c: Client, args: argparse.Namespace) -> int:
    try:
        report = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"error: cannot read scan report — {exc}", file=sys.stderr)
        return 2

    planned: list[dict] = []
    skipped_ambiguous = 0
    for paper in report.get("papers", []):
        rows = paper.get("rows") or []
        collisions = hash_collisions(rows)
        if collisions:
            print(f"error: paper {paper.get('paper_id')} has {len(collisions)} repaired-text "
                  f"collision(s); the unique index on (pyq_paper_id, "
                  f"normalized_question_hash) would reject the second UPDATE. "
                  f"Resolve these by hand first:", file=sys.stderr)
            for canon, ids in collisions[:5]:
                print(f"    {ids} -> {canon[:70]!r}", file=sys.stderr)
            return 2
        for r in rows:
            if r["classification"] == MANGLED:
                planned.append({**r, "paper_id": paper.get("paper_id"),
                                "year": paper.get("year")})
            else:
                skipped_ambiguous += 1

    print(f"{len(planned)} row(s) to repair; {skipped_ambiguous} ambiguous row(s) "
          f"skipped for manual review.")
    by_kind: dict[str, int] = {}
    for r in planned:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    print(f"  by kind: {dict(sorted(by_kind.items()))}")

    diff_path = Path(args.out)
    diff_path.write_text(json.dumps(
        {"planned": planned, "skipped_ambiguous": skipped_ambiguous},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote diff report -> {diff_path}")

    if not (args.apply and args.confirm):
        print("\nDRY RUN — nothing written. Re-run with --apply --confirm to PATCH.")
        return 0

    audit = Path(args.audit) if args.audit else None
    if audit is None:
        print("error: --audit <file> is required with --apply --confirm; every "
              "write must be recorded.", file=sys.stderr)
        return 2

    ok = failed = drifted = 0
    with audit.open("a", encoding="utf-8") as ah:
        for r in planned:
            kind, row_id = r["kind"], r["id"]
            path = (f"{CMS}/pyq-questions/{row_id}" if kind == "question"
                    else f"{CMS}/pyq-options/{row_id}")
            # Re-verify against the live row: if the text changed since the
            # scan, someone else edited it and our "old" is stale.
            try:
                current = _read_live_text(c, kind, r)
            except RuntimeError as exc:
                print(f"  {row_id}: re-read failed — {exc}", file=sys.stderr)
                failed += 1
                continue
            if current != r["old"]:
                print(f"  {row_id}: SKIPPED — live text differs from the scan "
                      f"(edited since?)", file=sys.stderr)
                drifted += 1
                continue

            # Audit BEFORE the write, so a crash still leaves a record.
            ah.write(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "kind": kind, "row_id": row_id, "question_id": r.get("question_id"),
                "paper_id": r.get("paper_id"), "year": r.get("year"),
                "old": r["old"], "new": r["new"],
            }, ensure_ascii=False) + "\n")
            ah.flush()

            try:
                c.patch(path, _patch_payload(kind, r["new"], args.reason))
                ok += 1
            except RuntimeError as exc:
                print(f"  {row_id}: {exc}", file=sys.stderr)
                failed += 1
            if args.sleep:
                time.sleep(args.sleep)

    print(f"\nrepaired={ok} failed={failed} skipped_drifted={drifted} "
          f"(audit -> {audit})")
    return 1 if failed else 0


# ─── CLI ────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-base", default=None, help="API base URL (default: $CCP_API_BASE)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="classify every question/option text (READ-ONLY)")
    s.add_argument("--exam-id", default=DEFAULT_EXAM_ID)
    s.add_argument("--exam-phase-id", action="append", default=None,
                   help="restrict to these phase(s); repeatable")
    s.add_argument("--paper-id", action="append", default=None,
                   help="restrict to these paper id(s); repeatable")
    s.add_argument("--out", default="mojibake_scan.json")
    s.add_argument("--sleep", type=float, default=0.0,
                   help="delay between per-question option fetches")

    r = sub.add_parser("repair", help="apply the inverse to rows the scan marked mangled")
    r.add_argument("--scan", required=True, help="scan report from the scan subcommand")
    r.add_argument("--out", default="mojibake_diff.json")
    r.add_argument("--audit", default=None,
                   help="JSONL audit file; REQUIRED with --apply --confirm")
    r.add_argument("--reason", default="repair cp1252-as-utf8 mojibake from the 2026-08-17 import")
    r.add_argument("--sleep", type=float, default=0.1)
    r.add_argument("--apply", action="store_true")
    r.add_argument("--confirm", action="store_true",
                   help="required WITH --apply to actually PATCH")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base or not token:
        print("error: set CCP_API_BASE and CCP_ADMIN_JWT", file=sys.stderr)
        return 2
    c = Client(base, token)
    handler: Callable[[Client, argparse.Namespace], int] = {
        "scan": do_scan, "repair": do_repair}[args.cmd]
    return handler(c, args)


if __name__ == "__main__":
    raise SystemExit(main())
