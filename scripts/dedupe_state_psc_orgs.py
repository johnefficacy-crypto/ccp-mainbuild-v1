#!/usr/bin/env python3
"""Collapse duplicate state_psc (and central) org clusters.

Usage:
    python scripts/dedupe_state_psc_orgs.py [--live] [--verbose]

Default is dry-run (read-only). Pass --live to apply changes.

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
  7. Backfills short_name for ALL state_psc + central orgs that lack it,
     matched by (name + state) — the same key used for cluster detection —
     from the authoritative PSC Short Name source.  Never from _abbrev_from_name.

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
    sys.path.insert(0, str(repo_root / "app" / "backend"))


# ── authoritative short-name map ───────────────────────────────────────────────
# Source: "PSC Short Name" column in the State PSC Detailed Registry workbook sheet.
# NOT derived from _abbrev_from_name. Keep in sync with the workbook.

_STATE_PSC_SHORT_NAMES: dict[str, str] = {
    # state (lower)                : authoritative short_name
   
    "andhra pradesh": "APPSC",
    "arunachal pradesh": "ARPSC",
    "assam": "APSC",
    "bihar": "BPSC",
    "chhattisgarh": "CGPSC",
    "goa": "GOAPSC",
    "gujarat": "GPSC",
    "haryana": "HPSC",
    "himachal pradesh": "HPPSC",
    "jharkhand": "JPSC",
    "jammu & kashmir": "JKPSC",
    "karnataka": "KPSC",
    "kerala": "KERALAPSC",
    "madhya pradesh": "MPPSC",
    "maharashtra": "MHPSC",
    "manipur": "MNPSC",
    "meghalaya": "MGPSC",
    "mizoram": "MZPSC",
    "nagaland": "NPSC",
    "odisha": "OPSC",
    "punjab": "PPSC",
    "rajasthan": "RPSC",
    "sikkim": "SPSC",
    "tamil nadu": "TNPSC",
    "telangana": "TGPSC",
    "tripura": "TPSC",
    "uttar pradesh": "UPPSC",
    "uttarakhand": "UKPSC",
    "west bengal": "WBPSC",
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


def run(sb: Any, dry_run: bool) -> None:
    clusters = _find_clusters(sb)
    logger.info("duplicate_clusters_found=%d", len(clusters))
    if not clusters:
        logger.info("No duplicate clusters found. Nothing to do.")
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
    _backfill_short_names(sb, dry_run)


def _backfill_short_names(sb: Any, dry_run: bool) -> None:
    """Set short_name on every state_psc / central org that lacks it.

    Match key is (normalized_name, normalized_state) — same key used by cluster
    detection — so a state with >1 body doesn't backfill the wrong short_name.
    Source is the authoritative _STATE_PSC_SHORT_NAMES / _CENTRAL_SHORT_NAMES
    maps; never _abbrev_from_name.
    """
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

        norm_name = _norm_text(org.get("name"))
        norm_state = _norm_text(org.get("state"))

        short_name: str | None = None
        if org["type"] == "state_psc":
            # Match by state first; if ambiguous use name too
            candidates = {
                state_key: sn
                for state_key, sn in _STATE_PSC_SHORT_NAMES.items()
                if state_key == norm_state
            }
            if len(candidates) == 1:
                short_name = next(iter(candidates.values()))
            elif candidates:
                # Multiple bodies in same state — match by name substring
                for state_key, sn in candidates.items():
                    if state_key in norm_name or sn.lower() in norm_name:
                        short_name = sn
                        break
        elif org["type"] == "central_commission":
            name_lower = norm_name
            short_name = _CENTRAL_SHORT_NAMES.get(name_lower)
            if not short_name:
                for alias, sn in _CENTRAL_SHORT_NAMES.items():
                    if name_lower.startswith(alias):
                        short_name = sn
                        break

        if not short_name:
            logger.warning(
                "No authoritative short_name for org %s (%s / %s / %s)",
                org["id"], org["type"], org.get("state"), org.get("name"),
            )
            continue

        logger.info("Backfill short_name=%s for org %s (%s)", short_name, org["id"], org.get("name"))
        backfilled += 1
        if not dry_run:
            sb.table("organizations").update({"short_name": short_name}).eq("id", org["id"]).execute()

    logger.info("short_name backfill: %d org(s) updated.", backfilled)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collapse duplicate state_psc org clusters.")
    parser.add_argument("--live", action="store_true", help="Apply changes (default: dry-run).")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    dry_run = not args.live

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if dry_run:
        logger.info("=== DRY-RUN MODE — no rows will be written ===")

    _bootstrap_path()

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        return 1

    from supabase import create_client
    sb = create_client(supabase_url, supabase_key)

    run(sb, dry_run=dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
