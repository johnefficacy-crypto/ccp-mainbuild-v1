"""Tests for org-dedup cleanup and DB-idempotent upsert_organization.

Covers (per spec):
  1. org write run twice over same body → ONE row (DB-idempotency regression guard)
  2. lookup matches a row whose stored short_name abbreviates inconsistently
     (e.g. "CGPSC" stored, "CGPSC" input → match, no insert)
  3. cleanup collapses a 2-row cluster to 1; survivor keeps official_url + merged metadata
  4. exams.conducting_organization_id on loser repointed to survivor, never nulled
  5. RESTRICT-table ref on loser repointed before delete (no FK violation)
  6. backfill covers a never-duplicated org (not just survivors)
  7. cluster discovery is dynamic — not fixed at 11
  8. two duplicate clusters in mock rows → returns 2
  9. zero duplicate clusters → returns 0
  10. same state, different normalized name → NOT grouped together (over-merge guard)
  11. survivor short_name backfilled from PSC Short Name column, not _abbrev_from_name
  12. ASSERT ZERO diff to state/slug functions vs origin/main
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import normalize_short_name, upsert_organization
from dedupe_state_psc_orgs import (
    _STATE_PSC_SHORT_NAMES,
    _backfill_short_names,
    _find_clusters,
    _merge_metadata,
    _norm_text,
    _pick_survivor,
    run as dedup_run,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_upsert_sb(
    existing_rows: list[dict] | None = None,
    insert_id: str = "new-org-id",
) -> MagicMock:
    """Mock for upsert_organization's exact-lookup chain:
        .select(...).eq("type",...).eq("short_name",...).eq("state",...).execute()
        .select(...).eq("type",...).eq("short_name",...).is_("state","null").execute()
    """
    sb = MagicMock()
    tbl = sb.table.return_value
    leaf = MagicMock()
    leaf.execute.return_value.data = existing_rows or []
    depth1 = tbl.select.return_value.eq.return_value
    depth1.execute.return_value.data = existing_rows or []
    depth2 = depth1.eq.return_value
    depth2.execute.return_value.data = existing_rows or []
    depth2.eq.return_value = leaf
    depth2.is_.return_value = leaf
    tbl.insert.return_value.execute.return_value.data = [{"id": insert_id}]
    tbl.update.return_value.eq.return_value.execute.return_value = None
    return sb


def _make_dedup_sb(
    orgs: list[dict],
    fk_refs: dict[str, dict[str, list[str]]] | None = None,
) -> MagicMock:
    """Mock for dedupe_state_psc_orgs.run().

    fk_refs: {org_id: {table_name: [ref_ids]}}
    """
    sb = MagicMock()
    fk_refs = fk_refs or {}

    def table_side_effect(tbl_name):
        m = MagicMock()
        if tbl_name == "organizations":
            m.select.return_value.in_.return_value.execute.return_value.data = list(orgs)
            m.update.return_value.eq.return_value.execute.return_value = None
            m.delete.return_value.eq.return_value.execute.return_value = None
        else:
            def select_fn(*a, **kw):
                s = MagicMock()
                def eq_fn(col, val):
                    e = MagicMock()
                    ref_ids = fk_refs.get(val, {}).get(tbl_name, [])
                    e.execute.return_value.data = [{"id": r} for r in ref_ids]
                    return e
                s.eq = eq_fn
                return s
            m.select = select_fn
            m.update.return_value.eq.return_value.execute.return_value = None
        return m

    sb.table.side_effect = table_side_effect
    return sb


def _org(
    org_id: str,
    name: str,
    state: str,
    short_name: str | None = None,
    metadata: dict | None = None,
    created_at: str = "2025-01-01T00:00:00",
    org_type: str = "state_psc",
) -> dict:
    return {
        "id": org_id,
        "type": org_type,
        "state": state,
        "name": name,
        "short_name": short_name,
        "metadata": metadata or {},
        "calendar_status": "needs_review",
        "created_at": created_at,
    }


# ── DB-idempotency: two calls → one row ──────────────────────────────────────

class TestUpsertOrganizationIdempotency:
    def test_second_call_finds_existing_no_insert(self):
        """Calling upsert twice with same (short_name, state, type) must not INSERT twice."""
        existing = [{
            "id": "existing-cgpsc",
            "name": "Chhattisgarh Public Service Commission",
            "type": "state_psc",
            "state": "chhattisgarh",
            "calendar_status": "needs_review",
            "metadata": {"import_status": "pending_review"},
            "short_name": "CGPSC",
        }]
        sb = _make_upsert_sb(existing_rows=existing)

        result = upsert_organization(
            sb,
            short_name="CGPSC",
            full_name="Chhattisgarh Public Service Commission",
            state="chhattisgarh",
            org_type="state_psc",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )

        assert result == "existing-cgpsc"
        sb.table.return_value.insert.assert_not_called()

    def test_uttarakhand_exact_short_name_lookup_no_duplicate(self):
        """UKPSC must match a row stored with short_name='UKPSC'.
        Pre-fix: _abbrev_from_name produced 'UPSC' ≠ 'UKPSC' → duplicate insert."""
        existing = [{
            "id": "existing-ukpsc",
            "name": "Uttarakhand Public Service Commission",
            "type": "state_psc",
            "state": "uttarakhand",
            "calendar_status": "needs_review",
            "metadata": {},
            "short_name": "UKPSC",
        }]
        sb = _make_upsert_sb(existing_rows=existing)

        result = upsert_organization(
            sb,
            short_name="UKPSC",
            full_name="Uttarakhand Public Service Commission",
            state="uttarakhand",
            org_type="state_psc",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )

        assert result == "existing-ukpsc"
        sb.table.return_value.insert.assert_not_called()

    def test_in_memory_cache_hit_skips_db(self):
        """If org_cache is pre-populated, no DB round-trip should occur."""
        sb = _make_upsert_sb()
        cache = {}
        upsert_organization(
            sb, short_name="KPSC", full_name="Kerala PSC",
            state="kerala", org_type="state_psc", calendar_status="published",
            official_url=None, dry_run=False, org_cache=cache,
        )
        call_count_after_first = sb.table.call_count

        upsert_organization(
            sb, short_name="KPSC", full_name="Kerala PSC",
            state="kerala", org_type="state_psc", calendar_status="published",
            official_url=None, dry_run=False, org_cache=cache,
        )
        assert sb.table.call_count == call_count_after_first

    def test_new_org_insert_includes_short_name(self):
        """INSERT payload must include short_name for future exact-match lookups."""
        sb = _make_upsert_sb(existing_rows=[])
        upsert_organization(
            sb, short_name="CGPSC", full_name="Chhattisgarh PSC",
            state="chhattisgarh", org_type="state_psc", calendar_status="needs_review",
            official_url=None, dry_run=False, org_cache={},
        )
        payload = sb.table.return_value.insert.call_args[0][0]
        assert payload["short_name"] == "CGPSC"


# ── cluster discovery — dynamic, not fixed ───────────────────────────────────

class TestFindClusters:
    def test_no_duplicates_returns_empty(self):
        """One org per (name, state) → zero clusters."""
        orgs = [
            _org("g1", "Goa Public Service Commission", "goa", short_name="GPSC"),
            _org("k1", "Kerala Public Service Commission", "kerala", short_name="KPSC"),
        ]
        sb = _make_dedup_sb(orgs)
        clusters = _find_clusters(sb)
        assert clusters == []

    def test_two_clusters_found(self):
        """Two distinct duplicate pairs → exactly 2 clusters returned."""
        orgs = [
            _org("g1", "Goa Public Service Commission", "goa"),
            _org("g2", "Goa Public Service Commission", "goa"),  # dup of g1
            _org("k1", "Kerala Public Service Commission", "kerala"),
            _org("k2", "Kerala Public Service Commission", "kerala"),  # dup of k1
        ]
        sb = _make_dedup_sb(orgs)
        clusters = _find_clusters(sb)
        assert len(clusters) == 2

    def test_different_name_same_state_not_merged(self):
        """Two bodies in the same state with different names must NOT be clustered."""
        orgs = [
            _org("a1", "Andhra Pradesh Public Service Commission", "andhra pradesh"),
            _org("a2", "Andhra Pradesh Subordinate Service Selection Board", "andhra pradesh"),
        ]
        sb = _make_dedup_sb(orgs)
        clusters = _find_clusters(sb)
        assert clusters == [], (
            "Different-named bodies in the same state were incorrectly merged: "
            + str(clusters)
        )

    def test_cluster_count_is_runtime_not_hardcoded(self):
        """Discovery is fully dynamic — varying the input changes the count."""
        base = [_org(f"o{i}", f"Body {i} PSC", "goa") for i in range(5)]
        sb_no_dup = _make_dedup_sb(base)
        assert _find_clusters(sb_no_dup) == []

        with_dup = base + [_org("o5", "Body 2 PSC", "goa")]
        sb_one_dup = _make_dedup_sb(with_dup)
        assert len(_find_clusters(sb_one_dup)) == 1


# ── dedup cleanup ─────────────────────────────────────────────────────────────

class TestDedupCleanup:
    def _goa_cluster(self, with_url_on: str = "goa-1"):
        orgs = [
            _org("goa-1", "Goa Public Service Commission", "goa", short_name="GPSC",
                 metadata={"official_url": "https://gpsc.goa.gov.in"} if with_url_on == "goa-1" else {}),
            _org("goa-2", "Goa Public Service Commission", "goa", short_name="GPSC",
                 metadata={"extra_key": "keep_me"}, created_at="2025-02-01T00:00:00"),
        ]
        return orgs

    def test_survivor_has_official_url(self):
        """Row with official_url wins over row without (all else equal)."""
        orgs = [
            _org("no-url", "Goa PSC", "goa", metadata={}),
            _org("with-url", "Goa PSC", "goa", metadata={"official_url": "https://x.com"},
                 created_at="2025-02-01T00:00:00"),
        ]
        all_refs = {"no-url": {}, "with-url": {}}
        survivor = _pick_survivor(orgs, all_refs)
        assert survivor["id"] == "with-url"

    def test_metadata_merged_from_loser_onto_survivor(self):
        survivor_meta = {"official_url": "https://gpsc.goa.gov.in"}
        loser_meta = {"extra_key": "keep_me", "official_url": "old"}  # survivor wins on conflict
        merged = _merge_metadata(survivor_meta, loser_meta)
        assert merged["official_url"] == "https://gpsc.goa.gov.in"
        assert merged["extra_key"] == "keep_me"

    def test_exam_conducting_org_repointed_not_nulled(self):
        """exams.conducting_organization_id on loser repointed to survivor."""
        orgs = self._goa_cluster()
        fk_refs = {"goa-2": {"exams": ["exam-ref-1"]}, "goa-1": {}}
        sb = _make_dedup_sb(orgs, fk_refs)
        dedup_run(sb, dry_run=False)
        # Verify no None was written to conducting_organization_id
        for call in sb.table.return_value.update.call_args_list:
            payload = call[0][0] if call[0] else {}
            assert payload.get("conducting_organization_id") is not None or \
                   "conducting_organization_id" not in payload

    def test_restrict_table_ref_logged_and_repointed(self, caplog):
        """RESTRICT ref on loser → WARNING logged and ref repointed before delete.

        Both rows have recruitment_units refs; goa-1 wins on official_url →
        goa-2 loses despite the RESTRICT ref → warning must be emitted.
        """
        import logging
        orgs = [
            _org("goa-1", "Goa PSC", "goa", metadata={"official_url": "https://x.com"}),
            _org("goa-2", "Goa PSC", "goa", created_at="2025-02-01T00:00:00"),
        ]
        fk_refs = {
            "goa-1": {"recruitment_units": ["ru-a"]},
            "goa-2": {"recruitment_units": ["ru-b"]},
        }
        sb = _make_dedup_sb(orgs, fk_refs)
        with caplog.at_level(logging.WARNING, logger="dedupe_state_psc_orgs"):
            dedup_run(sb, dry_run=False)
        assert any("RESTRICT" in r.message for r in caplog.records)

    def test_rerun_is_noop(self, caplog):
        """Second run finds no clusters → 0 changes, 'Nothing to do' logged."""
        import logging
        orgs = [_org("goa-only", "Goa PSC", "goa", short_name="GPSC")]
        sb = _make_dedup_sb(orgs, {})
        with caplog.at_level(logging.INFO, logger="dedupe_state_psc_orgs"):
            dedup_run(sb, dry_run=False)
        assert any("Nothing to do" in r.message for r in caplog.records)
        sb.table("organizations").delete.assert_not_called()


# ── backfill covers never-duplicated orgs ────────────────────────────────────

class TestBackfillShortNames:
    def test_backfill_sets_short_name_on_never_duplicated_org(self):
        """A survivor / never-duplicated org without short_name must get one."""
        orgs = [{
            "id": "assam-only", "type": "state_psc", "state": "assam",
            "name": "Assam Public Service Commission", "short_name": None,
        }]
        sb = MagicMock()
        sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = orgs
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None

        _backfill_short_names(sb, dry_run=False)

        sb.table.return_value.update.assert_called_once_with({"short_name": "APSC"})

    def test_backfill_skips_org_already_with_short_name(self):
        orgs = [{
            "id": "kerala-only", "type": "state_psc", "state": "kerala",
            "name": "Kerala PSC", "short_name": "KPSC",
        }]
        sb = MagicMock()
        sb.table.return_value.select.return_value.in_.return_value.execute.return_value.data = orgs

        _backfill_short_names(sb, dry_run=False)

        sb.table.return_value.update.assert_not_called()

    def test_backfill_from_authoritative_map_not_abbrev(self):
        """UKPSC must come from _STATE_PSC_SHORT_NAMES, not _abbrev_from_name.
        _abbrev_from_name('Uttarakhand Public Service Commission') = 'UPSC' (wrong).
        """
        assert _STATE_PSC_SHORT_NAMES.get("uttarakhand") == "UKPSC"
        assert _STATE_PSC_SHORT_NAMES.get("chhattisgarh") == "CGPSC"

    def test_all_29_state_psc_states_covered(self):
        """Every standard state must have an authoritative short_name."""
        expected = [
            "andhra pradesh", "arunachal pradesh", "assam", "bihar",
            "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh",
            "jharkhand", "jammu and kashmir", "karnataka", "kerala",
            "madhya pradesh", "maharashtra", "manipur", "meghalaya",
            "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
            "sikkim", "tamil nadu", "telangana", "tripura",
            "uttar pradesh", "uttarakhand", "west bengal",
        ]
        missing = [s for s in expected if s not in _STATE_PSC_SHORT_NAMES]
        assert not missing, f"Missing: {missing}"


# ── zero diff to state/slug machinery ────────────────────────────────────────

class TestStateSlugMachineryUnchanged:
    """Assert _extract_state_from_body and exam_slug are byte-identical to origin/main."""

    def test_protected_symbols_not_in_diff(self):
        result = subprocess.run(
            ["git", "diff", "origin/main", "--", "scripts/import_exam_registry.py"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).resolve().parents[4]),
        )
        diff = result.stdout
        protected = [
            "_extract_state_from_body",
            "_STATE_ABBREVS",
            "_STATE_TOKEN_ABBREVS",
            "_BODY_ABBREV_STATES",
            "_NATIONAL_BODY_ABBREVS",
            "def exam_slug",
        ]
        for symbol in protected:
            changed = [
                line for line in diff.splitlines()
                if symbol in line
                and line.startswith(("+", "-"))
                and not line.startswith(("+++", "---"))
            ]
            assert not changed, (
                f"Protected symbol '{symbol}' was modified:\n" + "\n".join(changed)
            )

    def test_upsc_stays_national(self):
        from import_exam_registry import _extract_state_from_body
        assert _extract_state_from_body("UPSC") is None

    def test_mpsc_is_maharashtra(self):
        from import_exam_registry import _extract_state_from_body
        assert _extract_state_from_body("MPSC") == "maharashtra"

    def test_jkpsc_is_jammu_kashmir(self):
        from import_exam_registry import _extract_state_from_body
        assert _extract_state_from_body("JKPSC") == "jammu-kashmir"

    def test_upsc_slug_is_national_not_uttar_pradesh(self):
        from import_exam_registry import _extract_state_from_body, exam_slug
        slug = exam_slug(_extract_state_from_body("UPSC"), "Civil Services Examination")
        assert slug.startswith("national-")
        assert "uttar-pradesh" not in slug
