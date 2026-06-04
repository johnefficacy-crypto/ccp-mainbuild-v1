#!/usr/bin/env python3
"""One-time bootstrap importer for Subordinate Boards (organizations only).

Usage:
    python scripts/import_subordinate_boards.py --xlsx PATH [--dry-run] [--verbose]

Sheet processed:
    "Subordinate Boards (Draft)"  — header row 4, data from row 5.

Columns consumed:
    State/UT, Board Short Name, Conducting Body, Exam / Sub-exam Family,
    Purpose / Posts, Typical Phases, Typical Cycle, Exam Type,
    Annual Calendar Published?, Board Source URL, Calendar / Schedule URL,
    Coverage Note.

Scope:
    ONLY organizations writes.  No exams, exam_cycles, exam_phases,
    recruitments, or source_registry rows are created.

Every inserted row lands as:
    type            = 'subordinate_board'
    calendar_status = 'needs_review'   (uniform; no keyword-sniffing)
    metadata.import_status = 'pending_review'

Idempotency:
    Exact DB lookup on (type, short_name, state) before insert.
    Found → update metadata only.  Absent → insert.
    Backed by migration 169's partial unique index on
    organizations(type, short_name, state) WHERE short_name IS NOT NULL.

Sentinel / non-board rows are SKIPPED (not failed):
    Board Short Name blank, or (after lower/trim/strip-parens) matches
    {"no single ssb", "none", "n/a", "not applicable"} or contains
    "no single ssb".

Fail-fast for real-board rows:
    Board Short Name is a real value but Conducting Body or State/UT is
    blank → abort with a descriptive error (malformed row).
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("import_subordinate_boards")

# ── path bootstrap ─────────────────────────────────────────────────────────────

def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / "app" / "backend"))


# ── sentinel detection ─────────────────────────────────────────────────────────

_SENTINEL_EXACT: frozenset[str] = frozenset({
    "no single ssb",
    "none",
    "n/a",
    "not applicable",
})


def _normalize_for_sentinel(raw: str | None) -> str:
    """Lower, trim, collapse whitespace, strip surrounding parentheses."""
    s = str(raw or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^\(+|\)+$", "", s).strip()
    return s


def _is_sentinel(raw: str | None) -> bool:
    """Return True if the Board Short Name cell is blank or a known non-board sentinel."""
    if not raw or not str(raw).strip():
        return True
    norm = _normalize_for_sentinel(raw)
    if norm in _SENTINEL_EXACT:
        return True
    if "no single ssb" in norm:
        return True
    return False


# ── sheet processor ────────────────────────────────────────────────────────────

_SHEET_NAME = "Subordinate Boards (Draft)"

# Forbidden tables — guard against accidental scope creep.
_FORBIDDEN_TABLES = frozenset({
    "exams", "exam_cycles", "exam_phases", "recruitments", "source_registry",
})


def _guarded_supabase(sb: Any) -> Any:
    """Wrap the supabase client so .table() raises on forbidden tables."""
    class _Guard:
        def table(self, name: str) -> Any:
            if name in _FORBIDDEN_TABLES:
                raise AssertionError(
                    f"import_subordinate_boards must not write to '{name}'"
                )
            return sb.table(name)
        def __getattr__(self, attr: str) -> Any:
            return getattr(sb, attr)
    return _Guard()


def _build_metadata(row: dict, _cell: Any) -> dict:
    return {
        "import_source": "subordinate_boards_workbook",
        "import_status": "pending_review",
        "source_sheet": _SHEET_NAME,
        "board_short_name_raw": _cell(row, "Board Short Name"),
        "annual_calendar_published": _cell(row, "Annual Calendar Published?"),
        "exam_family": _cell(row, "Exam / Sub-exam Family", "Exam/Sub-exam Family"),
        "purpose_posts": _cell(row, "Purpose / Posts", "Purpose/Posts"),
        "typical_phases": _cell(row, "Typical Phases"),
        "typical_cycle": _cell(row, "Typical Cycle"),
        "exam_type": _cell(row, "Exam Type"),
        "coverage_note": _cell(row, "Coverage Note"),
        "source_urls": {
            "board": _cell(row, "Board Source URL"),
            "calendar": _cell(row, "Calendar / Schedule URL", "Calendar/Schedule URL"),
        },
    }


def process_subordinate_boards_sheet(
    sb: Any,
    rows: list[dict],
    dry_run: bool,
    _cell: Any,
    normalize_short_name: Any,
) -> dict[str, Any]:
    """Process all rows from the Subordinate Boards (Draft) sheet.

    Returns stats dict with keys:
        imported, updated, skipped_non_board_rows (list of dicts)
    """
    stats: dict[str, Any] = {
        "imported": 0,
        "updated": 0,
        "skipped_non_board_rows": [],
    }

    for row_idx, row in enumerate(rows, start=5):  # data starts at workbook row 5
        raw_short = _cell(row, "Board Short Name")
        state = _cell(row, "State/UT", "State")
        conducting_body = _cell(row, "Conducting Body")

        # ── sentinel / non-board skip ──────────────────────────────────────────
        if _is_sentinel(raw_short):
            entry = {
                "row": row_idx,
                "board_short_name_raw": raw_short,
                "state": state,
                "conducting_body": conducting_body,
            }
            stats["skipped_non_board_rows"].append(entry)
            logger.info(
                "SKIP non-board row %d: short_name=%r  state=%r  body=%r",
                row_idx, raw_short, state, conducting_body,
            )
            continue

        # ── fail-fast on malformed real-board rows ─────────────────────────────
        if not conducting_body:
            raise ValueError(
                f"Row {row_idx}: Board Short Name={raw_short!r} but Conducting Body is blank. "
                "Fix the workbook before re-running."
            )
        if not state:
            raise ValueError(
                f"Row {row_idx}: Board Short Name={raw_short!r} but State/UT is blank. "
                "Fix the workbook before re-running."
            )

        short_name = normalize_short_name(raw_short)
        metadata = _build_metadata(row, _cell)

        if dry_run:
            logger.info(
                "[DRY-RUN] would upsert org: short_name=%s  name=%r  state=%r  "
                "type=subordinate_board  calendar_status=needs_review",
                short_name, conducting_body, state,
            )
            stats["imported"] += 1
            continue

        # ── idempotent upsert ──────────────────────────────────────────────────
        existing_rows = (
            sb.table("organizations")
            .select("id,metadata")
            .eq("type", "subordinate_board")
            .eq("short_name", short_name)
            .eq("state", state)
            .execute()
            .data or []
        )

        if existing_rows:
            existing = existing_rows[0]
            merged_meta = {**(existing.get("metadata") or {}), **metadata}
            sb.table("organizations").update({"metadata": merged_meta}).eq(
                "id", existing["id"]
            ).execute()
            stats["updated"] += 1
            logger.debug(
                "org updated (existing): short_name=%s state=%s id=%s",
                short_name, state, existing["id"],
            )
        else:
            payload = {
                "name": conducting_body,
                "short_name": short_name,
                "type": "subordinate_board",
                "state": state,
                "is_active": True,
                "calendar_status": "needs_review",
                "metadata": metadata,
            }
            resp = sb.table("organizations").insert(payload).execute()
            org_id = resp.data[0]["id"]
            stats["imported"] += 1
            logger.info(
                "org inserted: %s (%s)  state=%s  id=%s",
                conducting_body, short_name, state, org_id,
            )

    return stats


# ── main ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import Subordinate Boards as organizations (pending_review)."
    )
    parser.add_argument(
        "--xlsx", type=Path,
        help="Path to the exam-registry workbook (.xlsx). Required for --live runs.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview rows without writing to the database.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not args.dry_run and not args.xlsx:
        logger.error("--xlsx is required for live runs. Use --dry-run to preview.")
        return 1

    if args.xlsx and not args.xlsx.exists():
        logger.error("Workbook not found: %s", args.xlsx)
        return 1

    _bootstrap_path()

    # Import shared helpers from the existing importer — zero reimplementation.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from import_exam_registry import _cell, load_workbook, normalize_short_name

    if args.dry_run:
        logger.info("=== DRY-RUN MODE — no rows will be written ===")
        sb = None
    else:
        from app.db.supabase_client import get_supabase_admin
        sb = _guarded_supabase(get_supabase_admin())

    if not args.xlsx:
        # --dry-run without --xlsx: nothing to parse.
        logger.info("No --xlsx provided; nothing to preview.")
        return 0

    all_sheets = load_workbook(args.xlsx)
    if _SHEET_NAME not in all_sheets:
        logger.error("Sheet %r not found in workbook. Available: %s", _SHEET_NAME, sorted(all_sheets))
        return 1

    rows = all_sheets[_SHEET_NAME]
    logger.info("Sheet %r: %d data rows loaded.", _SHEET_NAME, len(rows))

    stats = process_subordinate_boards_sheet(
        sb, rows, args.dry_run, _cell, normalize_short_name,
    )

    skipped = stats["skipped_non_board_rows"]
    logger.info(
        "Done. imported=%d  updated=%d  skipped_non_board_rows=%d",
        stats["imported"], stats["updated"], len(skipped),
    )
    if skipped:
        logger.info("Skipped non-board rows:")
        for entry in skipped:
            logger.info(
                "  row %-3d  state=%-25s  body=%-40s  raw_short=%r",
                entry["row"], entry["state"] or "(blank)",
                entry["conducting_body"] or "(blank)",
                entry["board_short_name_raw"],
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
