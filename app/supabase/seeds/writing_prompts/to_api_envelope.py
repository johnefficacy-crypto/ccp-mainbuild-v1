#!/usr/bin/env python3
"""Wrap a UI-uploadable row-array seed file into the `/writing-prompts/bulk`
API envelope for a direct `curl`.

The committed `NN_*.json` files are ROW ARRAYS (the shape the Content Studio
Bulk Import UI parses). The bulk API endpoint instead wants
`{reason, subject_id, rows}`. This prints that envelope on stdout.

Usage:
  python3 to_api_envelope.py 03_grammar.json \
      --subject-id "$SUBJECT_ID" \
      --reason "Seed import: grammar batch" > /tmp/grammar_envelope.json
  curl -X POST "$API/api/admin/content-studio/writing-prompts/bulk" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      --data @/tmp/grammar_envelope.json

Resolve --subject-id from the LIVE english-language subject (see preflight_ids.py);
do not assume the deterministic default matches every environment.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("rows_file", type=Path)
    ap.add_argument("--subject-id", required=True)
    ap.add_argument("--reason", required=True)
    args = ap.parse_args(argv)

    rows = json.loads(args.rows_file.read_text())
    if not isinstance(rows, list):
        print("ERROR: expected a JSON array of rows", file=sys.stderr)
        return 2
    if not (8 <= len(args.reason) <= 500):
        print("ERROR: reason must be 8–500 characters", file=sys.stderr)
        return 2

    envelope = {"reason": args.reason, "subject_id": args.subject_id, "rows": rows}
    json.dump(envelope, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
