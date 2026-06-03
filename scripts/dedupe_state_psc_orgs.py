#!/usr/bin/env python3
"""Collapse duplicate state_psc (and central) org clusters.

Usage:
    python scripts/dedupe_state_psc_orgs.py [--live] [--xlsx PATH] [--verbose]

Default is dry-run (read-only). Pass --live to apply changes.
--xlsx is required for --live; dry-run warns and skips backfill if absent.

What it does:
  1. Reads all state_psc / central_commission org rows from the DB.
  2. Groups by (type, normalized_name, normalized_state).  Any group with >1 row
     is a duplicate cluster.  The number of clusters is a runtime observation,
     not a fixed expectation.
  3. For each cluster, picks ONE survivor:
       - Prefer the row referenced by a RESTRICT FK table (recruitment_units, courses).
       - Then prefer the row referenced by any FK table.
       - Then prefer the row with official_url in metadata.
       - Then the earliest created_at.
  4. Repoints ALL 7 FK tables loser→survivor BEFORE deleting the loser.
  5. Merges loser metadata onto survivor (no official_url / provenance loss).
  6. Deletes losers.
  7. Backfills short_name for ALL state_psc orgs that lack it, derived from the
     workbook using the SAME normalize_short_name(_cell("PSC Short Name","Short Name"))
     call the importer uses on INSERT — so backfill key and importer key are
     identical by construction and cannot diverge.

Idempotent: a second run finds 0 clusters, 0 changes.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("dedupe_state_psc_orgs")


# ── path bootstrap ─────────────────────────────────────────────────────────────

def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    scripts_dir = Path(__file__).resolve().parent
    # scripts/ must be on path so import_exam_registry is importable.
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    sys.path.insert(0, str(repo_root / "app" / "backend"))


# ── authoritative short-name fixture ──────────────────────────────────────────
# NOT the live backfill source — backfill derives from the workbook via the
# importer's own normalize_short_name(_cell(...)) call.
# Keep here only as a test fixture / reference.

_FIXTURE_STATE_PSC_SHORT_NAMES: dict[str, str] = {
    # state (lower, workbook-normalised)   : authoritative short_name
    "andhra pradesh"                       : "APPSC",
    "arunachal pradesh"                    : "APPSC",
    "assam"                                : "APSC",
    "bihar"                                : "BPSC",
    "chhattisgarh"                         : "CGPSC",
    "goa"                                  : "GPSC",
    "gujarat"                              : "GPSC",
    "haryana"                              : "HPSC",
    "himachal pradesh"                     : "HPPSC",
    "jharkhand"                            : "JPSC",
    "jammu & kashmir"                      : "JKPSC",
    "karnataka"                            : "KPSC",
    "kerala"                               : "KPSC",
    "madhya pradesh"                       : "MPPSC",
    "maharashtra"                          : "MPSC",
    "manipur"                              : "MPSC",
    "meghalaya"                            : "MPSC",
    "mizoram"                              : "MPSC",
    "nagaland"                             : "NPSC",
    "odisha"                               : "OPSC",
    "punjab"                               : "PPSC",
    "rajasthan"                            : "RPSC",
    "sikkim"                               : "SPSC",
    "tamil nadu"                           : "TNPSC",
    "telangana"                            : "TSPSC",
    "tripura"                              : "TPSC",
    "uttar pradesh"                        : "UPPSC",
    "uttarakhand"                          : "UKPSC",
    "west bengal"                          : "WBPSC",
    "delhi"                                : "DSSSB",
    "ladakh"                               : "LAHDC",
}

_CENTRAL_SHORT_NAMES: dict[str, str] = {
    "upsc"  : "UPSC",
    "ssc"   : "SSC",
    "ibps"  : "IBPS",
    "rrb"   : "RRB",
    "rrc"   : "RRC",
    "sbi"   : "SBI",
    "nta"   : "NTA",
    "dsssb" : "DSSSB",
    "lic"   : "LIC",
}

# FK tables that reference organizations.id, in repoint order.
# RESTRICT tables listed first — they hard-fail on delete if missed.
_FK_TABLES: list[dict] = [
    # RESTRICT + NOT NULL — must repoint before delete
    {"table": "recruitment_units",  "col": "organization_id",         "on_delete": "RESTRICT"},
    {"table": "courses",            "col": "organization_id",         "on_delete": "RESTRICT"},
    # SET NULL — silently null on delete; repoint anyway to preserve data
    {"table": "recruitments",       "col": "organization_id",         "on_delete": "SET NULL"},
    {"table": "source_registry",    "col": "organization_id",         "on_delete": "SET NULL"},
    {"table": "exams",              "col": "conducting_organization_id", "on_delete": "SET NULL"},
    {"table": "blog_posts",         "col": "related_organization_id", "on_delete": "SET NULL"},
    {"table": "blog_recruitment_links", "col": "organization_id",     "on_delete": "SET NULL"},
]


def _norm_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _find_clusters(sb: Any) -> list[list[dict]]:
    """Return list of clusters (each a list of ≥2 org rows) that need collapsing.

    Groups by (type, normalized_name, normalized_state).  Only rows with the
    same normalized name and state are considered duplicates — never collapsed
    across different bodies in the same state.
    """
    rows = (
        sb.table("organizations")
        .select("id,name,type,state,short_name,metadata,calendar_status,created_at")
        .in_("type", ["state_psc", "central_commission"])
        .execute()
        .data or []
    )

    from collections import defaultdict
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        bucket_key = (
            row["type"],
            _norm_text(row.get("name")),
            _norm_text(row.get("state")),
        )
        buckets[bucket_key].append(row)

    return [members for members in buckets.values() if len(members) > 1]


def _fk_refs(sb: Any, org_id: str) -> dict[str, list[str]]:
    """Return {table: [ref_ids]} for all FK tables pointing at org_id."""
    result: dict[str, list[str]] = {}
    for fk in _FK_TABLES:
        refs = (
            sb.table(fk["table"])
            .select("id")
            .eq(fk["col"], org_id)
            .execute()
            .data or []
        )
        if refs:
            result[fk["table"]] = [r["id"] for r in refs]
    return result


def _pick_survivor(cluster: list[dict], all_refs: dict[str, dict[str, list[str]]]) -> dict:
    """Choose the row to keep.

    Priority:
      1. Referenced by a RESTRICT table (recruitment_units, courses) — hard-fail risk.
      2. Referenced by any FK table.
      3. Has official_url in metadata.
      4. Earliest created_at.
    """
    restrict_tables = {fk["table"] for fk in _FK_TABLES if fk["on_delete"] == "RESTRICT"}

    def score(row: dict) -> tuple:
        refs = all_refs.get(row["id"], {})
        has_restrict = any(t in refs for t in restrict_tables)
        has_any_ref = bool(refs)
        has_url = bool((row.get("metadata") or {}).get("official_url"))
        created = row.get("created_at") or ""
        # Lower tuple = better (we'll sort ascending and take first)
        return (
            0 if has_restrict else 1,
            0 if has_any_ref else 1,
            0 if has_url else 1,
            created,
        )

    return sorted(cluster, key=score)[0]


def _merge_metadata(survivor_meta: dict, loser_meta: dict) -> dict:
    """Merge loser keys onto survivor without clobbering survivor values."""
    merged = dict(loser_meta)
    merged.update(survivor_meta)  # survivor wins on conflict
    return merged


def run(sb: Any, dry_run: bool, state_map: dict[str, str] | None = None) -> None:
    """Run dedup and backfill.

    state_map: workbook-derived state→short_name map, pre-loaded and validated by
        main() BEFORE this function is called so any bad workbook fails before the
        first mutation.  None means no workbook provided — backfill is skipped.
    """

    clusters = _find_clusters(sb)
    logger.info("duplicate_clusters_found=%d", len(clusters))
    if not clusters:
        logger.info("No duplicate clusters found. Nothing to do.")
        _backfill_short_names(sb, dry_run, state_map)
        return

    # Pre-fetch all FK refs for every org in every cluster
    all_org_ids = [row["id"] for cluster in clusters for row in cluster]
    all_refs: dict[str, dict[str, list[str]]] = {oid: _fk_refs(sb, oid) for oid in all_org_ids}

    for cluster in clusters:
        survivor = _pick_survivor(cluster, all_refs)
        losers = [r for r in cluster if r["id"] != survivor["id"]]

        logger.info(
            "Cluster: %s / %s — survivor=%s, losers=%s",
            cluster[0]["type"], cluster[0].get("state") or "(national)",
            survivor["id"], [r["id"] for r in losers],
        )

        for loser in losers:
            loser_refs = all_refs.get(loser["id"], {})

            # Report / repoint all FK references
            for fk in _FK_TABLES:
                ref_ids = loser_refs.get(fk["table"], [])
                if not ref_ids:
                    continue
                if fk["on_delete"] == "RESTRICT":
                    logger.warning(
                        "RESTRICT ref: %s.%s → loser %s (%d rows) — repointing to %s",
                        fk["table"], fk["col"], loser["id"], len(ref_ids), survivor["id"],
                    )
                else:
                    logger.info(
                        "Repointing %s.%s: loser %s → survivor %s (%d rows)",
                        fk["table"], fk["col"], loser["id"], survivor["id"], len(ref_ids),
                    )
                if not dry_run:
                    (
                        sb.table(fk["table"])
                        .update({fk["col"]: survivor["id"]})
                        .eq(fk["col"], loser["id"])
                        .execute()
                    )

            # Merge loser metadata onto survivor
            survivor_meta = survivor.get("metadata") or {}
            loser_meta = loser.get("metadata") or {}
            merged_meta = _merge_metadata(survivor_meta, loser_meta)
            if merged_meta != survivor_meta:
                logger.info("Merging metadata from loser %s onto survivor %s", loser["id"], survivor["id"])
                if not dry_run:
                    sb.table("organizations").update({"metadata": merged_meta}).eq("id", survivor["id"]).execute()
                    survivor["metadata"] = merged_meta  # keep in-memory state consistent

            # Also inherit official_url to top-level metadata if loser had one and survivor didn't
            loser_url = loser_meta.get("official_url")
            if loser_url and not survivor_meta.get("official_url"):
                logger.info("Inheriting official_url from loser: %s", loser_url)
                if not dry_run:
                    updated_meta = dict(survivor.get("metadata") or {})
                    updated_meta["official_url"] = loser_url
                    sb.table("organizations").update({"metadata": updated_meta}).eq("id", survivor["id"]).execute()

            # Delete loser (short_name stays NULL so it's outside the partial unique index)
            logger.info("Deleting loser org: %s (%s)", loser.get("name"), loser["id"])
            if not dry_run:
                sb.table("organizations").delete().eq("id", loser["id"]).execute()

    # Backfill short_name for ALL state_psc and central orgs (survivors + never-duplicated)
    _backfill_short_names(sb, dry_run, state_map)


def _build_workbook_short_name_map(xlsx_path: Path) -> dict[str, str]:
    """Build state→short_name map from the workbook using the importer's exact derivation.

    Calls normalize_short_name(_cell(row, "PSC Short Name", "Short Name")) — the same
    expression process_state_psc_sheet uses on INSERT — so the map values are
    identical to the short_names the importer would write.  Cannot diverge.

    Keyed by _norm_text(state) so lookups against DB org.state values are consistent.
    """
    # Import the shared helpers from the importer — same derivation, not a reimplementation.
    from import_exam_registry import normalize_short_name, _cell, load_workbook  # type: ignore[import]

    sheets = load_workbook(xlsx_path)
    sheet_rows = sheets.get("State PSC Detailed Registry")
    if sheet_rows is None:
        raise RuntimeError(
            "Workbook is missing sheet 'State PSC Detailed Registry'. "
            f"Sheets found: {sorted(sheets)}"
        )

    state_map: dict[str, str] = {}
    for row in sheet_rows:
        state = _cell(row, "State/UT", "State")
        raw_short = _cell(row, "PSC Short Name", "Short Name")
        if not state or not raw_short:
            continue
        norm_state = _norm_text(state)
        short_name = normalize_short_name(raw_short)
        if short_name:
            state_map[norm_state] = short_name

    return state_map


def _backfill_short_names(sb: Any, dry_run: bool, state_map: dict[str, str] | None = None) -> None:
    """Set short_name on every state_psc / central org that lacks it.

    state_map: workbook-derived state→short_name map pre-loaded by run() before
        any mutations.  None means no workbook was provided — backfill is skipped.

    state_psc: looked up in state_map; fails fast if an org's state is absent.
    central_commission: derived from _CENTRAL_SHORT_NAMES (no workbook column).
    """
    if state_map is None:
        logger.warning(
            "No --xlsx provided; skipping short_name backfill. "
            "Re-run with --xlsx PATH to backfill state_psc short names."
        )
        return

    orgs = (
        sb.table("organizations")
        .select("id,type,state,name,short_name")
        .in_("type", ["state_psc", "central_commission"])
        .execute()
        .data or []
    )

    backfilled = 0
    for org in orgs:
        if org.get("short_name"):
            continue  # already set

        if org["type"] == "state_psc":
            norm_state = _norm_text(org.get("state"))
            if norm_state not in state_map:
                raise RuntimeError(
                    f"state_psc org {org['id']!r} ({org.get('name')!r}) has state "
                    f"{org.get('state')!r} (normalized: {norm_state!r}) not found in "
                    f"workbook-derived map. Known states: {sorted(state_map)}. "
                    "Add the state to the workbook or investigate the org's state value."
                )
            short_name = state_map[norm_state]

        elif org["type"] == "central_commission":
            norm_name = _norm_text(org.get("name"))
            short_name = _CENTRAL_SHORT_NAMES.get(norm_name)
            if not short_name:
                for alias, sn in _CENTRAL_SHORT_NAMES.items():
                    if norm_name.startswith(alias):
                        short_name = sn
                        break
            if not short_name:
                logger.warning(
                    "No short_name for central org %s (%s)", org["id"], org.get("name")
                )
                continue

        else:
            continue

        logger.info("Backfill short_name=%s for org %s (%s)", short_name, org["id"], org.get("name"))
        backfilled += 1
        if not dry_run:
            sb.table("organizations").update({"short_name": short_name}).eq("id", org["id"]).execute()

    logger.info("short_name backfill: %d org(s) updated.", backfilled)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collapse duplicate state_psc org clusters.")
    parser.add_argument("--live", action="store_true", help="Apply changes (default: dry-run).")
    parser.add_argument(
        "--xlsx", type=Path, default=None, metavar="PATH",
        help="Path to exam-registry workbook (.xlsx). Required for --live; "
             "dry-run warns and skips backfill if absent.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    dry_run = not args.live

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.live and not args.xlsx:
        logger.error("--xlsx PATH is required when running --live. Aborting.")
        return 1

    if dry_run and not args.xlsx:
        logger.warning(
            "No --xlsx provided; short_name backfill will be skipped in this dry-run."
        )

    if dry_run:
        logger.info("=== DRY-RUN MODE — no rows will be written ===")

    _bootstrap_path()

    # Load and validate the workbook map HERE — before opening a DB connection —
    # so a bad path or missing sheet fails before any mutations are attempted.
    state_map: dict[str, str] | None = None
    if args.xlsx:
        state_map = _build_workbook_short_name_map(args.xlsx)
        logger.info("Workbook-derived state→short_name map: %d states", len(state_map))

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        return 1

    from supabase import create_client
    sb = create_client(supabase_url, supabase_key)

    run(sb, dry_run=dry_run, state_map=state_map)
    return 0


if __name__ == "__main__":
    sys.exit(main())
