#!/usr/bin/env python3
"""Seed exam_phases from the exam-registry workbook.

This post-import helper looks up already-imported exams by the same slug that
``scripts/import_exam_registry.py`` uses, then previews or inserts phase rows
from the workbook phase columns.  It defaults to dry-run mode; pass ``--live``
only when the operator is ready to write to Supabase.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

from import_exam_registry import (
    _cell,
    _extract_state_from_body,
    _strip_leading_body_from_exam_name,
    exam_slug,
    load_workbook,
    slugify,
)

logger = logging.getLogger("seed_exam_phases")


# ── path bootstrap ────────────────────────────────────────────────────────────

def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / "app" / "backend"))


# ── slug derivation ───────────────────────────────────────────────────────────

def derive_seed_exam_slug(exam_name: str, conducting_body: str) -> tuple[str, str]:
    """Return ``(slug, clean_exam_name)`` using importer-identical slug logic."""
    state_prefix = _extract_state_from_body(conducting_body)
    clean_exam_name = _strip_leading_body_from_exam_name(exam_name, conducting_body)
    return exam_slug(state_prefix, clean_exam_name), clean_exam_name


# ── phase parsing / seeding ───────────────────────────────────────────────────

def parse_phase_names(phases_text: str | None) -> list[str]:
    if not phases_text or not str(phases_text).strip():
        return []
    parts = re.split(r"\s*(?:;|,|→|->|/|\n)\s*", str(phases_text).strip())
    return [p.strip() for p in parts if p and p.strip()]


def _phase_rows_for_sheet(
    sheet_name: str, rows: list[dict]
) -> list[tuple[str, str, list[str]]]:
    derived: list[tuple[str, str, list[str]]] = []
    for row in rows:
        if sheet_name == "State PSC Detailed Registry":
            exam_name = _cell(row, "Exam/Sub-exam Family", "Exam Family") or ""
            conducting_body = (
                _cell(row, "Conducting Body", "PSC Short Name", "Short Name") or ""
            )
            phases_text = _cell(row, "Typical Phases")
        else:
            exam_name = _cell(row, "Exam") or ""
            conducting_body = _cell(row, "Conducting Body") or ""
            phases_text = _cell(row, "Main Phases", "Typical Phases")


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed exam_phases from the exam registry workbook."
    )
    parser.add_argument("--xlsx", required=True, type=Path, help="Path to .xlsx workbook.")
    parser.add_argument("--live", action="store_true", help="Write phase rows. Omit for dry-run.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    _bootstrap_path()
    dry_run = not args.live
    if dry_run:
        logger.info("=== DRY-RUN MODE — no rows will be written ===")
        sb = None
    else:
        from app.db.supabase_client import get_supabase_admin
        sb = get_supabase_admin()

    sheets = load_workbook(args.xlsx)
    stats = process_workbook(sb, sheets, dry_run=dry_run)
    logger.info(
        "Phase seed complete. exams_seen=%d phases=%d existing=%d not_found=%d",
        stats["exams_seen"],
        stats["phases"],
        stats["existing"],
        stats["not_found"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
