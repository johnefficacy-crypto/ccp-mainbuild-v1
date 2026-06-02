#!/usr/bin/env python3
"""Seed exam_phases stubs for exams imported by the workbook importer (#578/#579).

Usage:
    python scripts/seed_exam_phases.py --xlsx PATH [--dry-run] [--live] [--verbose]

The workbook importer created exams + cycles + orgs but NOT exam_phases rows.
The "Main Phases" column on the Exam Registry sheet is freeform text (e.g.
"Prelims, Mains, Interview") that was never fanned out into structured phase rows.
Without exam_phases rows the #577 worklist has nothing to surface for date authoring.

This script seeds ONE stub per parsed phase name, with NO dates, so the worklist
can surface them for human date-authoring.

Safety contract:
- phase_start = NULL and phase_end = NULL on every stub. No date is invented.
- metadata.import_status = 'pending_review' — never auto-verified.
- metadata.import_source = 'exam_registry_workbook'
- metadata.phase_source_text = original "Main Phases" cell (provenance)
- metadata.phase_window = phase_name — required so #577 worklist gate
  (legacyWindow() fn in SetupPanel.jsx:40) returns truthy and surfaces the stub.
- Only operates on exams where metadata.import_source='exam_registry_workbook'.
  Manually-created exams and the recruitment pipeline are never touched.
- Dedupe on (exam_id, phase_name): re-run = zero new rows.
- Empty / TBD / unparseable Main Phases: zero rows created, counted and logged.

Slug fn is IMPORTED from import_exam_registry — not reimplemented — so slugs
match the slugs the 225 exams already have.

--dry-run  : default-safe; prints intent, no DB writes, always exits 0.
--live     : opt-in to actually write. Requires explicit flag to prevent accidents.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("seed_exam_phases")

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))


def _bootstrap_path() -> None:
    repo_root = _SCRIPT_DIR.parent
    sys.path.insert(0, str(repo_root / "app" / "backend"))


# Import slug functions from the workbook importer — do NOT reimplement.
from import_exam_registry import (
    _extract_state_from_body,
    exam_slug,
    load_workbook,
    slugify,
    _cell,
)


# ── phase name parsing ────────────────────────────────────────────────────────

# Delimiters accepted (in order of precedence):
#   1. comma   — "Prelims, Mains, Interview"
#   2. slash   — "Prelims / Mains"
#   3. " and " — "Written and Interview"
# Applied as a single regex split so mixed inputs collapse correctly.
_SPLIT_RE = re.compile(r"\s*[,/]\s*|\s+and\s+", re.IGNORECASE)

# Values treated as "unparseable / no structured phases"
_SKIP_VALUES = {"", "tbd", "n/a", "na", "none", "—", "-", "nil"}


def split_phases(raw: str | None) -> list[str] | None:
    """Return list of phase names, or None if the cell is empty/TBD/unparseable.

    Returns None (not []) so callers can distinguish "cell present but unparseable"
    from "cell split to zero parts" — both are counted, neither fabricates a phase.
    """
    if not raw or not str(raw).strip():
        return None
    cleaned = str(raw).strip()
    if cleaned.lower() in _SKIP_VALUES:
        return None
    parts = [p.strip() for p in _SPLIT_RE.split(cleaned) if p.strip()]
    return parts if parts else None


def normalize_phase_name(name: str) -> str:
    """Collapse internal whitespace; title-case for canonical dedupe form."""
    return " ".join(name.split()).title()


# ── stub builder ──────────────────────────────────────────────────────────────

def build_stubs(
    exam_id: str,
    exam_slug_val: str,
    phases_raw: str,
    phase_names: list[str],
) -> list[dict]:
    """Build insert-ready stub dicts for each parsed phase name."""
    stubs = []
    for order, name in enumerate(phase_names, start=1):
        normalized = normalize_phase_name(name)
        stubs.append({
            "exam_id": exam_id,
            "phase_name": normalized,
            "phase_slug": slugify(normalized),
            "phase_order": order,
            "status": "expected",
            "phase_start": None,
            "phase_end": None,
            "metadata": {
                "import_status": "pending_review",
                "import_source": "exam_registry_workbook",
                "phase_source_text": phases_raw,
                # Required for #577 worklist gate: legacyWindow() in SetupPanel.jsx:40
                # returns phase.metadata?.phase_window. Without this the stub is invisible
                # to the worklist even when phase_start IS NULL.
                "phase_window": normalized,
            },
        })
    return stubs


# ── DB helpers ────────────────────────────────────────────────────────────────

def fetch_imported_exams(sb: Any) -> dict[str, str]:
    """Return {slug: id} for all exams where import_source='exam_registry_workbook'."""
    rows = (
        sb.table("exams")
        .select("id,slug,metadata")
        .execute()
        .data or []
    )
    return {
        r["slug"]: r["id"]
        for r in rows
        if (r.get("metadata") or {}).get("import_source") == "exam_registry_workbook"
    }


def fetch_existing_phase_names(sb: Any, exam_id: str) -> set[str]:
    """Return lowercased phase names already present for this exam."""
    rows = (
        sb.table("exam_phases")
        .select("phase_name")
        .eq("exam_id", exam_id)
        .execute()
        .data or []
    )
    return {r["phase_name"].lower() for r in rows}


def insert_stubs(sb: Any, stubs: list[dict]) -> None:
    if stubs:
        sb.table("exam_phases").insert(stubs).execute()


# ── main seeding logic ────────────────────────────────────────────────────────

def seed(
    sb: Any,
    workbook_path: Path,
    dry_run: bool,
    stats: dict,
) -> None:
    sheets = load_workbook(workbook_path)
    exam_registry = sheets.get("Exam Registry", [])
    if not exam_registry:
        logger.warning("Exam Registry sheet not found in workbook.")
        return

    # In dry-run mode we don't have a DB connection — skip DB lookups.
    if not dry_run:
        imported_exams = fetch_imported_exams(sb)
    else:
        imported_exams = {}

    stats["sheet_rows"] = len(exam_registry)

    for row in exam_registry:
        exam_name = _cell(row, "Exam") or ""
        conducting_body = _cell(row, "Conducting Body") or ""
        phases_raw = _cell(row, "Main Phases") or ""

        if not exam_name:
            continue

        stats["exams_processed"] += 1

        # Derive the slug the same way the importer did.
        state_prefix = _extract_state_from_body(conducting_body)
        slug = exam_slug(state_prefix, exam_name)

        # Parse phase names
        phase_names = split_phases(phases_raw)
        if phase_names is None:
            stats["unparseable"] += 1
            logger.info(
                "SKIP unparseable: slug=%s  raw=%r", slug, phases_raw or "(empty)"
            )
            continue

        # Build stubs
        stubs = build_stubs(
            exam_id=slug,  # placeholder in dry-run; replaced below in live
            exam_slug_val=slug,
            phases_raw=phases_raw,
            phase_names=phase_names,
        )

        if dry_run:
            logger.info(
                "[DRY-RUN] slug=%s  phases=%s  stubs=%d",
                slug, phase_names, len(stubs),
            )
            stats["stubs_would_create"] += len(stubs)
            continue

        # Live path
        exam_id = imported_exams.get(slug)
        if not exam_id:
            stats["not_found"] += 1
            logger.debug("Exam not found in DB (not imported or slug mismatch): %s", slug)
            continue

        existing = fetch_existing_phase_names(sb, exam_id)
        to_insert = []
        for stub in stubs:
            # Patch in real exam_id
            stub["exam_id"] = exam_id
            if stub["phase_name"].lower() in existing:
                stats["dedupe_skips"] += 1
            else:
                to_insert.append(stub)

        if to_insert:
            insert_stubs(sb, to_insert)
            stats["stubs_created"] += len(to_insert)
            logger.info(
                "Inserted %d stub(s) for exam %s (%s)",
                len(to_insert), exam_name, exam_id,
            )
        else:
            stats["all_deduped"] += 1


# ── main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed exam_phases stubs from workbook Main Phases column."
    )
    parser.add_argument("--xlsx", required=True, type=Path, help="Path to .xlsx workbook.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview only; no DB writes (default).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually write stubs to DB. Must be explicit.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    # --live overrides --dry-run; dry-run is the safe default.
    dry_run = not args.live

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if dry_run:
        logger.info("=== DRY-RUN MODE — no rows will be written ===")
        sb = None
    else:
        _bootstrap_path()
        from app.db.supabase_client import get_supabase_admin
        sb = get_supabase_admin()

    stats: dict = {
        "sheet_rows": 0,
        "exams_processed": 0,
        "unparseable": 0,
        "stubs_would_create": 0,
        "stubs_created": 0,
        "dedupe_skips": 0,
        "not_found": 0,
        "all_deduped": 0,
    }

    seed(sb, args.xlsx, dry_run, stats)

    if dry_run:
        logger.info(
            "DRY-RUN complete. sheet_rows=%d  exams_processed=%d  "
            "stubs_would_create=%d  unparseable=%d",
            stats["sheet_rows"], stats["exams_processed"],
            stats["stubs_would_create"], stats["unparseable"],
        )
    else:
        logger.info(
            "Live run complete. exams_processed=%d  stubs_created=%d  "
            "dedupe_skips=%d  unparseable=%d  not_found=%d",
            stats["exams_processed"], stats["stubs_created"],
            stats["dedupe_skips"], stats["unparseable"], stats["not_found"],
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
