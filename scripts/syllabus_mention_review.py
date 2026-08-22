#!/usr/bin/env python3
"""Export a syllabus-mention review worksheet, then apply the decisions.

Reviewing several hundred ``syllabus_topic_mentions`` one HTTP call at a time
is impractical, and a bulk "set them all verified" is prohibited (CLAUDE.md ->
verified-only reads; review must be real). This script splits the job:

    export  ->  one CSV, grouped so a reviewer sees each macro topic beside
                the micro-themes claimed to sit under it, with a blank
                `decision` column to fill in.

    apply   ->  reads the filled CSV and issues one review call per decided
                row. Rows left blank are skipped, so the work can be done in
                sittings.

The script never decides anything itself. A blank decision stays pending.

Worksheet columns:

    mention_id      review target (do not edit)
    paper           GS I..IV, from the topic's subject
    macro_topic     the official syllabus line this sits under
    level           topic | microtopic
    mention_type    explicit (official text) | derived (curator decomposition)
    text            the mention's raw_text — what is being asserted
    decision        <- FILL IN: verified | rejected | needs_correction | (blank = skip)
    notes           <- optional reviewer note, stored on the row

Usage:

    export CCP_API_BASE=... CCP_ADMIN_JWT=...

    python scripts/syllabus_mention_review.py export \
        --exam-id <uuid> --document-id <uuid> --out review.csv

    # ... reviewer fills the decision column ...

    python scripts/syllabus_mention_review.py apply --in review.csv --dry-run
    python scripts/syllabus_mention_review.py apply --in review.csv

Export needs ``exam_intelligence.cms``; apply needs ``exam_intelligence.review``.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

CMS = "/api/admin/exam-intelligence-cms"
INTEL = "/api/admin/exam-intelligence"

DECISIONS = {"verified", "rejected", "needs_correction"}
MENTION_TYPES = {"explicit", "implied", "parent_topic_only", "derived"}
FIELDS = ["mention_id", "paper", "macro_topic", "level", "mention_type",
          "text", "decision", "notes"]


class Client:
    def __init__(self, base: str, token: str, timeout: int = 60) -> None:
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
                  page: int = 200) -> list[dict]:
        out: list[dict] = []
        offset = 0
        while True:
            d = self.get(path, {**(params or {}), "limit": page, "offset": offset})
            items = d.get("items") or []
            out.extend(items)
            if len(items) < page:
                return out
            offset += page


def build_topic_index(c: Client, topic_ids: set[str]) -> dict[str, dict]:
    """Resolve topic_id -> {name, level, parent_topic_id, subject_id}.

    The topics endpoint has no id filter, so walk the subjects that own the
    topics we care about. Subjects are few; topics per subject are bounded.
    """
    subjects = c.all_items(f"{CMS}/subjects")
    index: dict[str, dict] = {}
    for s in subjects:
        for t in c.all_items(f"{CMS}/topics", {"subject_id": s["id"]}):
            if t["id"] in topic_ids:
                index[t["id"]] = {**t, "subject_name": s.get("name")}
    return index


def do_export(c: Client, args: argparse.Namespace) -> int:
    mentions = c.all_items(
        f"{CMS}/syllabus-topic-mentions",
        {"syllabus_document_id": args.document_id, "exam_id": args.exam_id},
    )
    mentions = [m for m in mentions if m.get("reviewer_status") == args.status]
    if not mentions:
        print(f"No mentions with reviewer_status={args.status!r} on that document.")
        return 1

    topic_index = build_topic_index(c, {m["topic_id"] for m in mentions})
    missing = [m for m in mentions if m["topic_id"] not in topic_index]
    if missing:
        print(f"warning: {len(missing)} mention(s) point at topics that could not be "
              "resolved — they are still listed, with blank topic context.",
              file=sys.stderr)

    def sort_key(m: dict) -> tuple:
        t = topic_index.get(m["topic_id"], {})
        parent = t.get("parent_topic_id")
        macro = topic_index.get(parent, {}).get("name") if parent else t.get("name", "")
        # macro topic first within each subject, then its micro-themes
        return (t.get("subject_name") or "", macro or "", 0 if not parent else 1,
                t.get("name") or "")

    rows = []
    for m in sorted(mentions, key=sort_key):
        t = topic_index.get(m["topic_id"], {})
        parent = t.get("parent_topic_id")
        macro = topic_index.get(parent, {}).get("name", "") if parent else t.get("name", "")
        rows.append({
            "mention_id": m["id"],
            "paper": t.get("subject_name", ""),
            "macro_topic": macro,
            "level": t.get("level", ""),
            "mention_type": m.get("mention_type", ""),
            "text": (m.get("raw_text") or "").replace("\r", " ").replace("\n", " "),
            "decision": "",
            "notes": "",
        })

    out = Path(args.out)
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["mention_type"]] = by_type.get(r["mention_type"], 0) + 1
    print(f"wrote {len(rows)} rows to {out}")
    print(f"  by mention_type: {by_type}")
    print(f"  macro topics: {len({r['macro_topic'] for r in rows})}")
    print("\nFill the 'decision' column with verified / rejected / needs_correction.")
    print("Leave a row blank to decide it later — blanks stay pending.")
    return 0


def do_retype(c: Client, args: argparse.Namespace) -> int:
    """Change mention_type on specific mentions.

    Used when a row asserts the wrong KIND of claim — e.g. a curator's grouping
    stored as 'explicit', which says the text is a verbatim official syllabus
    line. The CMS edit endpoint cannot touch reviewer_status (that moves only
    through the review queue), so a retyped mention stays pending and is
    reviewed normally afterwards.
    """
    if args.to not in MENTION_TYPES:
        print(f"error: --to must be one of {sorted(MENTION_TYPES)}", file=sys.stderr)
        return 2
    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    if not ids:
        print("error: --ids is empty", file=sys.stderr)
        return 2

    ok = failed = 0
    for mid in ids:
        body = {"reason": args.reason, "payload": {"mention_type": args.to}}
        if args.dry_run:
            print(f"  {mid}: would set mention_type={args.to}")
            continue
        try:
            row = c.patch(f"{CMS}/syllabus-topic-mentions/{mid}", body).get("row") or {}
            print(f"  {mid}: mention_type={row.get('mention_type', args.to)} "
                  f"reviewer_status={row.get('reviewer_status', '?')}")
            ok += 1
        except RuntimeError as exc:
            print(f"  {mid}: {exc}", file=sys.stderr)
            failed += 1

    if args.dry_run:
        print("\nDRY RUN — nothing written.")
    else:
        print(f"\nretyped={ok} failed={failed}")
    return 1 if failed else 0


def do_apply(c: Client, args: argparse.Namespace) -> int:
    with Path(args.infile).open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    decided = [r for r in rows if (r.get("decision") or "").strip()]
    bad = [r for r in decided if r["decision"].strip().lower() not in DECISIONS]
    if bad:
        print(f"error: {len(bad)} row(s) have an unrecognized decision. "
              f"Allowed: {sorted(DECISIONS)}", file=sys.stderr)
        for r in bad[:5]:
            print(f"  {r.get('mention_id')}: {r.get('decision')!r}", file=sys.stderr)
        return 2

    print(f"{len(decided)} decided of {len(rows)} rows "
          f"({len(rows) - len(decided)} left pending)")
    counts: dict[str, int] = {}
    for r in decided:
        d = r["decision"].strip().lower()
        counts[d] = counts.get(d, 0) + 1
    print(f"  {counts}")

    if args.dry_run:
        print("\nDRY RUN — nothing written.")
        return 0

    ok = failed = 0
    for r in decided:
        body: dict[str, Any] = {"reviewer_status": r["decision"].strip().lower()}
        note = (r.get("notes") or "").strip()
        if note:
            body["reviewer_notes"] = note[:500]
        try:
            c.patch(f"{INTEL}/items/syllabus_topic_mention/{r['mention_id']}/review", body)
            ok += 1
        except RuntimeError as exc:
            print(f"  {r['mention_id']}: {exc}", file=sys.stderr)
            failed += 1

    print(f"\napplied={ok} failed={failed}")
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-base", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export", help="write a review worksheet")
    e.add_argument("--exam-id", required=True)
    e.add_argument("--document-id", required=True)
    e.add_argument("--out", default="syllabus_mention_review.csv")
    e.add_argument("--status", default="pending",
                   help="which reviewer_status to export (default: pending)")

    a = sub.add_parser("apply", help="apply decisions from a filled worksheet")
    a.add_argument("--in", dest="infile", required=True)
    a.add_argument("--dry-run", action="store_true")

    t = sub.add_parser("retype", help="change mention_type on specific mentions")
    t.add_argument("--ids", required=True, help="comma-separated mention ids")
    t.add_argument("--to", required=True, help=f"one of {sorted(MENTION_TYPES)}")
    t.add_argument("--reason", required=True, help="audit reason, 8-500 chars")
    t.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    if args.cmd == "retype" and not (8 <= len(args.reason) <= 500):
        print("error: --reason must be 8-500 characters", file=sys.stderr)
        return 2
    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base or not token:
        print("error: set CCP_API_BASE and CCP_ADMIN_JWT", file=sys.stderr)
        return 2

    c = Client(base, token)
    handler = {"export": do_export, "apply": do_apply, "retype": do_retype}[args.cmd]
    return handler(c, args)


if __name__ == "__main__":
    raise SystemExit(main())
