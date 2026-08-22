#!/usr/bin/env python3
"""Backfill per-year source URLs on PYQ papers, then optionally promote them.

``POST /pyq-papers/{id}/review`` refuses ``pending -> verified`` unless the
paper has a usable provenance anchor: ``source_type`` other than 'unknown'
AND (a non-empty ``source_url`` OR a ``source_document_id``). Papers created
by a bulk import typically have neither URL nor document, so every promotion
fails with ``422 provenance_incomplete`` until the anchor is filled in.

This script fills that anchor from a year -> URL map (see
``docs/reference/syllabus/upsc_cse_mains_paper_sources.json``) and then, with
``--promote``, transitions each paper to verified.

Provenance honesty: entries in the map carry a ``verified`` flag meaning "this
URL was actually confirmed to exist", not "it matches the expected pattern".
Unconfirmed URLs are SKIPPED unless ``--allow-unverified`` is passed, because
a plausible-looking URL written into an evidence ledger is worse than a blank
one — it reads as checked when nobody checked it.

Promotion is a review action and is never implied: ``--promote`` is opt-in and
requires ``--reason``.

Usage:

    export CCP_API_BASE=... CCP_ADMIN_JWT=...

    # 1. see what would change
    python scripts/backfill_pyq_paper_provenance.py \
        --exam-id <uuid> --exam-phase-id <uuid> \
        --sources docs/reference/syllabus/upsc_cse_mains_paper_sources.json \
        --dry-run

    # 2. write the confirmed URLs only
    python scripts/backfill_pyq_paper_provenance.py ... (no --dry-run)

    # 3. promote, once every paper has an anchor
    python scripts/backfill_pyq_paper_provenance.py ... \
        --promote --reason "Mains PYQ corpus 2013-2025 verified against official UPSC papers"

Requires ``exam_intelligence.cms`` for the URL patch and
``exam_intelligence.review`` for ``--promote``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

CMS = "/api/admin/exam-intelligence-cms"


class Client:
    def __init__(self, base: str, token: str, *, dry_run: bool, timeout: int = 60) -> None:
        self.base = base.rstrip("/")
        self.dry_run = dry_run
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

    def send(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if self.dry_run:
            return {"_dry_run": True}
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        r = self.session.request(method, f"{self.base}{path}", data=data, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}

    def all_papers(self, exam_id: str) -> list[dict]:
        out: list[dict] = []
        offset = 0
        while True:
            d = self.get(f"{CMS}/pyq-papers", {"exam_id": exam_id, "limit": 200, "offset": offset})
            items = d.get("items") or []
            out.extend(items)
            if len(items) < 200:
                return out
            offset += 200


def run(args: argparse.Namespace) -> int:
    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base or not token:
        print("error: set CCP_API_BASE and CCP_ADMIN_JWT", file=sys.stderr)
        return 2

    sources = json.loads(Path(args.sources).read_text(encoding="utf-8"))
    year_map: dict[str, dict[str, Any]] = sources.get("years", {})

    client = Client(base, token, dry_run=args.dry_run)
    papers = [
        p for p in client.all_papers(args.exam_id)
        if p.get("exam_phase_id") == args.exam_phase_id
    ]
    if not papers:
        print("No papers at that exam/phase scope.")
        return 1

    patched = promoted = skipped_unverified = skipped_ok = failed = 0

    for p in sorted(papers, key=lambda x: x.get("year") or 0):
        year = str(p.get("year"))
        pid = p["id"]
        entry = year_map.get(year)
        has_anchor = bool(
            (p.get("source_url") or "").strip() or p.get("source_document_id")
        )

        if has_anchor and args.force_url and entry and (
            entry.get("verified") or args.allow_unverified
        ) and (p.get("source_url") or "") != entry["url"]:
            # An anchor is already set but differs from the map. Only replace it
            # on an explicit --force-url: silently rewriting provenance on a
            # paper someone may already have reviewed against the old URL would
            # invalidate that review without any trace.
            try:
                client.send(
                    "PATCH", f"{CMS}/pyq-papers/{pid}",
                    {"reason": args.reason or
                     "Replace paper source_url with the corrected official anchor",
                     "payload": {"source_url": entry["url"], "source_type": "official"}},
                )
                print(f"  {year}: source_url REPLACED")
                patched += 1
            except RuntimeError as exc:
                print(f"  {year}: PATCH failed — {exc}")
                failed += 1
                continue

        elif not has_anchor:
            if not entry:
                print(f"  {year}: no URL in the source map — skipped")
                failed += 1
                continue
            if not entry.get("verified") and not args.allow_unverified:
                print(f"  {year}: URL present but unconfirmed — skipped "
                      f"(pass --allow-unverified to write it anyway)")
                skipped_unverified += 1
                continue
            try:
                client.send(
                    "PATCH", f"{CMS}/pyq-papers/{pid}",
                    {"reason": args.reason or
                     "Backfill official UPSC source URL to satisfy the provenance gate",
                     "payload": {"source_url": entry["url"], "source_type": "official"}},
                )
                flag = "" if entry.get("verified") else "  [UNCONFIRMED URL]"
                print(f"  {year}: source_url set{flag}")
                patched += 1
                has_anchor = True
            except RuntimeError as exc:
                print(f"  {year}: PATCH failed — {exc}")
                failed += 1
                continue
        else:
            skipped_ok += 1
            print(f"  {year}: already has an anchor — left alone")

        if args.promote and has_anchor and p.get("trust_status") == "pending":
            try:
                client.send("POST", f"{CMS}/pyq-papers/{pid}/review",
                            {"status": "verified", "reason": args.reason})
                print(f"  {year}: promoted to verified")
                promoted += 1
            except RuntimeError as exc:
                print(f"  {year}: promote failed — {exc}")
                failed += 1

    print(
        f"\npatched={patched} promoted={promoted} "
        f"already_ok={skipped_ok} skipped_unverified={skipped_unverified} failed={failed}"
    )
    if args.dry_run:
        print("\nDRY RUN — nothing written.")
    if skipped_unverified:
        print(
            f"\n{skipped_unverified} year(s) have an unconfirmed URL. Open each in a "
            "browser, fix it if it 404s, set \"verified\": true in the source map, "
            "and re-run."
        )
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exam-id", required=True)
    p.add_argument("--exam-phase-id", required=True)
    p.add_argument("--sources", required=True, help="year -> URL map JSON")
    p.add_argument("--api-base", default=None)
    p.add_argument("--reason", default=None,
                   help="Audit reason (8-500 chars). Required with --promote.")
    p.add_argument("--promote", action="store_true",
                   help="Also transition each anchored paper pending -> verified")
    p.add_argument("--allow-unverified", action="store_true",
                   help="Write URLs whose existence was never confirmed")
    p.add_argument("--force-url", action="store_true",
                   help="Replace an existing source_url that differs from the map "
                        "(otherwise papers with any anchor are left alone)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.promote and not (args.reason and len(args.reason) >= 8):
        print("error: --promote requires --reason (8-500 chars)", file=sys.stderr)
        return 2
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
