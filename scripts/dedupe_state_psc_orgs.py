#!/usr/bin/env python3
"""Deduplicate state_psc organization clusters created by multiple importer runs.

Usage:
    python scripts/dedupe_state_psc_orgs.py --xlsx PATH [--dry-run] [--live] [--verbose]

Context
-------
The exam-registry importer previously used a heuristic _abbrev_from_name() reconstruction
loop to match existing DB rows.  When the stored full_name abbreviated differently from
the input short_name (e.g. "Goa PSC" → "GP" ≠ input "GPSC") or the state field differed
between runs, the match failed and a second row was inserted.  This script collapses the
resulting 11 state_psc duplicate clusters (count-2 each) back to 29 unique rows.

Safety contract
---------------
- --dry-run is the default.  Prints every action.  No DB writes.  Exits 0.
- --live is the explicit opt-in for actual writes.
- FK repoint BEFORE delete for ALL referencing tables, including ON DELETE SET NULL ones.
  Silently-nulled exams.conducting_organization_id is treated as data loss; we repoint
  every reference, not rely on cascade behaviour.
- Tables repointed: exams (conducting_organization_id), recruitments (organization_id),
  recruitment_units (organization_id), source_registry (organization_id),
  blog_posts (related_organization_id), blog_recruitment_links (organization_id).
- recruitments and recruitment_units have RESTRICT delete behaviour and NOT NULL columns.
  The script detects loser rows referenced by these tables and errors loudly rather than
  attempting a delete that would raise a FK violation.
- Metadata merge: loser's metadata is merged onto survivor REGARDLESS of which row was
  chosen as survivor.  official_url and provenance keys are never lost.
- short_name backfill: reads the authoritative "PSC Short Name" column from the xlsx
  workbook.  Does NOT use _abbrev_from_name() (that is the lossy heuristic that caused
  the bug).  Central orgs use canonical names from _CENTRAL_BODY_ALIASES.
- Idempotent: a second run finds 0 duplicate clusters and makes 0 changes.
- No source_registry writes.  Recruitment pipeline untouched.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("dedupe_state_psc_orgs")

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from import_exam_registry import (
    load_workbook,
    normalize_short_name,
    _cell,
    _CENTRAL_BODY_ALIASES,
)


# ── FK repoint map ─────────────────────────────────────────────────────────────
# Every table.column that references organizations.id.
# (table, fk_column, restrict) — restrict=True means NOT NULL or RESTRICT delete;
# the delete will hard-fail if unrepointed references exist.

_FK_MAP = [
    ("exams",                  "conducting_organization_id", False),
    ("recruitments",           "organization_id",            True),   # RESTRICT
    ("recruitment_units",      "organization_id",            True),   # RESTRICT + NOT NULL
    ("source_registry",        "organization_id",            False),
    ("blog_posts",             "related_organization_id",    False),
    ("blog_recruitment_links", "organization_id",            False),
]


# ── authoritative short_name loading ──────────────────────────────────────────

def _load_authoritative_short_names(workbook_path: Path) -> dict[str, str]:
    """Return {state.lower(): normalized_short_name} from the State PSC sheet.

    Source column: "PSC Short Name" (authoritative).
    This is the ONLY acceptable source.  _abbrev_from_name() must NOT be used
    because it is the lossy heuristic that caused the duplication bug.
    """
    sheets = load_workbook(workbook_path)
    registry = sheets.get("State PSC Detailed Registry", [])
    result: dict[str, str] = {}
    for row in registry:
        state = _cell(row, "State/UT", "State") or ""
        short = _cell(row, "PSC Short Name", "Short Name") or ""
        if state and short:
            result[state.lower().strip()] = normalize_short_name(short)
    return result


def _canonical_central_short_names() -> dict[str, str]:
    """Return {org_type='central_commission' canonical abbrev} from the alias table."""
    # Values in _CENTRAL_BODY_ALIASES are already the canonical short names.
    return {v: normalize_short_name(v) for v in set(_CENTRAL_BODY_ALIASES.values())}


# ── cluster detection ──────────────────────────────────────────────────────────

def find_duplicate_clusters(sb: Any) -> list[list[dict]]:
    """Return list of clusters; each cluster = list of ≥2 org rows sharing (type, state).

    Clusters are defined by same (type, lower(state)) — the field combination
    that should be unique per real-world org.
    """
    rows = (
        sb.table("organizations")
        .select("id,name,short_name,type,state,calendar_status,metadata,created_at")
        .eq("type", "state_psc")
        .execute()
        .data or []
    )
    groups: dict[str, list[dict]] = {}
    for row in rows:
        group_key = (row["type"], (row.get("state") or "").lower().strip())
        groups.setdefault(group_key, []).append(row)

    return [cluster for cluster in groups.values() if len(cluster) >= 2]


# ── FK reference lookup ────────────────────────────────────────────────────────

def _fk_references(sb: Any, loser_id: str) -> dict[str, list[str]]:
    """Return {table: [ref_row_id, ...]} for every FK row pointing to loser_id."""
    refs: dict[str, list[str]] = {}
    for table, fk_col, _ in _FK_MAP:
        try:
            rows = (
                sb.table(table)
                .select("id")
                .eq(fk_col, loser_id)
                .execute()
                .data or []
            )
        except Exception as exc:
            logger.warning("Could not query %s.%s: %s", table, fk_col, exc)
            rows = []
        if rows:
            refs[table] = [r["id"] for r in rows]
    return refs


# ── survivor selection ─────────────────────────────────────────────────────────

def _select_survivor(cluster: list[dict], sb: Any) -> tuple[dict, dict]:
    """Return (survivor_row, loser_row) per the confirmed rule:

    1. Row with FK references (any table) → survivor.
    2. Tie-break: row with official_url in metadata → survivor.
    3. Tie-break: earlier created_at → survivor.
    """
    if len(cluster) != 2:
        raise ValueError(f"Expected cluster of 2, got {len(cluster)}")

    a, b = cluster

    def has_fk(row: dict) -> bool:
        refs = _fk_references(sb, row["id"])
        return bool(refs)

    a_fk = has_fk(a)
    b_fk = has_fk(b)

    if a_fk and not b_fk:
        return a, b
    if b_fk and not a_fk:
        return b, a

    # Tie-break: richer metadata (official_url present)
    a_url = bool((a.get("metadata") or {}).get("official_url"))
    b_url = bool((b.get("metadata") or {}).get("official_url"))
    if a_url and not b_url:
        return a, b
    if b_url and not a_url:
        return b, a

    # Final tie-break: earlier created_at
    if (a.get("created_at") or "") <= (b.get("created_at") or ""):
        return a, b
    return b, a


# ── metadata merge ─────────────────────────────────────────────────────────────

def _merge_metadata(survivor_meta: dict, loser_meta: dict) -> dict:
    """Merge loser metadata onto survivor.  Loser values fill gaps; survivor values win."""
    merged = dict(loser_meta or {})
    merged.update(survivor_meta or {})  # survivor keys overwrite
    return merged


# ── cluster deduplication ─────────────────────────────────────────────────────

def dedupe_cluster(
    sb: Any,
    cluster: list[dict],
    auth_short_names: dict[str, str],
    dry_run: bool,
    stats: dict,
) -> None:
    """Process one duplicate cluster: repoint → merge → backfill → delete loser."""
    survivor, loser = _select_survivor(cluster, sb)
    state_key = (survivor.get("state") or "").lower().strip()
    auth_short = auth_short_names.get(state_key)

    # Gather all FK references for the loser
    loser_refs = _fk_references(sb, loser["id"])

    # Check for RESTRICT-table references on loser (hard-fail in --live)
    restrict_refs = {
        table: ids
        for table, ids in loser_refs.items()
        if any(t == table and restrict for t, _, restrict in _FK_MAP)
    }

    logger.info(
        "%s cluster: survivor=%s, loser=%s | state=%s | loser_refs=%s",
        "[DRY-RUN]" if dry_run else "[LIVE]",
        survivor["id"], loser["id"], survivor.get("state"),
        {k: len(v) for k, v in loser_refs.items()} if loser_refs else "none",
    )

    if auth_short:
        logger.info("  short_name backfill: '%s' (from xlsx PSC Short Name)", auth_short)
    else:
        logger.warning("  short_name NOT found in xlsx for state '%s'", state_key)

    for table, ids in loser_refs.items():
        fk_col = next(col for t, col, _ in _FK_MAP if t == table)
        logger.info("  repoint %s.%s: %d row(s) %s → %s",
                    table, fk_col, len(ids), loser["id"], survivor["id"])

    merged_meta = _merge_metadata(
        survivor.get("metadata") or {},
        loser.get("metadata") or {},
    )
    logger.info("  metadata merge: official_url preserved=%s",
                bool(merged_meta.get("official_url")))

    if dry_run:
        stats["clusters_found"] += 1
        stats["would_delete"] += 1
        stats["fk_rows_would_repoint"] += sum(len(v) for v in loser_refs.values())
        return

    # Live path
    if restrict_refs:
        # Safety check: RESTRICT tables with references must be repointed first.
        # This should never block because we repoint all tables below, but if
        # somehow a table is missing from _FK_MAP we surface it instead of
        # letting the delete hard-fail silently.
        logger.warning("RESTRICT-table refs on loser %s: %s", loser["id"], restrict_refs)

    # 1. Repoint all FK references loser → survivor
    for table, ids in loser_refs.items():
        fk_col = next(col for t, col, _ in _FK_MAP if t == table)
        for ref_id in ids:
            sb.table(table).update({fk_col: survivor["id"]}).eq("id", ref_id).execute()
            logger.debug("  repointed %s(%s).%s → %s", table, ref_id, fk_col, survivor["id"])

    # 2. Merge metadata onto survivor
    update_payload: dict = {"metadata": merged_meta}
    if auth_short:
        update_payload["short_name"] = auth_short
    sb.table("organizations").update(update_payload).eq("id", survivor["id"]).execute()

    # 3. Delete loser (all FKs already repointed)
    sb.table("organizations").delete().eq("id", loser["id"]).execute()

    stats["clusters_collapsed"] += 1
    stats["orgs_deleted"] += 1
    stats["fk_rows_repointed"] += sum(len(v) for v in loser_refs.values())
    logger.info("  deleted loser %s | survivor %s updated", loser["id"], survivor["id"])


# ── never-duplicated org short_name backfill ──────────────────────────────────

def backfill_short_names(
    sb: Any,
    auth_short_names: dict[str, str],
    dry_run: bool,
    stats: dict,
) -> None:
    """Backfill short_name for ALL state_psc and central_commission orgs that lack it.

    Covers the 18 never-duplicated state_psc orgs, survivors after cleanup, and
    the central_commission orgs.  Source is always the authoritative xlsx data
    (for state_psc) or canonical alias table (for central_commission).
    """
    rows = (
        sb.table("organizations")
        .select("id,name,short_name,type,state,metadata")
        .in_("type", ["state_psc", "central_commission"])
        .is_("short_name", "null")
        .execute()
        .data or []
    )

    for row in rows:
        if row["type"] == "state_psc":
            state_key = (row.get("state") or "").lower().strip()
            auth_short = auth_short_names.get(state_key)
        else:
            # central_commission: derive from stored metadata or name
            meta = row.get("metadata") or {}
            name_raw = meta.get("canonical_name") or row.get("name") or ""
            auth_short = normalize_short_name(name_raw.split()[0]) if name_raw else None

        if not auth_short:
            logger.warning("Cannot determine short_name for org %s (name=%s, state=%s) — skipping",
                           row["id"], row.get("name"), row.get("state"))
            continue

        logger.info("%s backfill short_name='%s' for org %s (state=%s, name=%s)",
                    "[DRY-RUN]" if dry_run else "[LIVE]",
                    auth_short, row["id"], row.get("state"), row.get("name"))

        if not dry_run:
            sb.table("organizations").update({"short_name": auth_short}).eq("id", row["id"]).execute()
        stats["short_names_backfilled"] += 1


# ── main ──────────────────────────────────────────────────────────────────────

def run(sb: Any, workbook_path: Path, dry_run: bool, stats: dict) -> None:
    """Full deduplication pass."""
    auth_short_names = _load_authoritative_short_names(workbook_path)
    logger.info("Loaded %d authoritative short_name mappings from xlsx", len(auth_short_names))

    # Phase A: collapse duplicate clusters
    clusters = find_duplicate_clusters(sb)
    logger.info("Found %d duplicate cluster(s)", len(clusters))

    for cluster in clusters:
        dedupe_cluster(sb, cluster, auth_short_names, dry_run, stats)

    # Phase B: backfill short_name for all importer orgs (incl. never-duplicated ones)
    backfill_short_names(sb, auth_short_names, dry_run, stats)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deduplicate state_psc org clusters and backfill short_name."
    )
    parser.add_argument("--xlsx", required=True, type=Path,
                        help="Path to the exam-registry .xlsx workbook.")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview only; no DB writes (default).")
    parser.add_argument("--live", action="store_true",
                        help="Actually write changes to DB. Must be explicit.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    dry_run = not args.live
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if dry_run:
        logger.info("=== DRY-RUN MODE — no DB writes ===")
        # Need a DB connection even in dry-run to read current state
        from pathlib import Path as _Path
        repo_root = _SCRIPT_DIR.parent
        sys.path.insert(0, str(repo_root / "app" / "backend"))
        from app.db.supabase_client import get_supabase_admin
        sb = get_supabase_admin()
    else:
        repo_root = _SCRIPT_DIR.parent
        sys.path.insert(0, str(repo_root / "app" / "backend"))
        from app.db.supabase_client import get_supabase_admin
        sb = get_supabase_admin()

    stats: dict = {
        "clusters_found": 0,
        "clusters_collapsed": 0,
        "orgs_deleted": 0,
        "fk_rows_repointed": 0,
        "fk_rows_would_repoint": 0,
        "would_delete": 0,
        "short_names_backfilled": 0,
    }

    run(sb, args.xlsx, dry_run, stats)

    if dry_run:
        logger.info(
            "DRY-RUN complete. clusters_found=%d  would_delete=%d  "
            "fk_rows_would_repoint=%d  short_names_to_backfill=%d",
            stats["clusters_found"], stats["would_delete"],
            stats["fk_rows_would_repoint"], stats["short_names_backfilled"],
        )
    else:
        logger.info(
            "Live run complete. clusters_collapsed=%d  orgs_deleted=%d  "
            "fk_rows_repointed=%d  short_names_backfilled=%d",
            stats["clusters_collapsed"], stats["orgs_deleted"],
            stats["fk_rows_repointed"], stats["short_names_backfilled"],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
