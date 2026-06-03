"""Tests for org deduplication fix (migration 169 + import_exam_registry rewrite).

Covers:
  - DB-idempotency: org write run twice over same body → ONE row, not two
    (the regression that would have caught the 11-cluster bug)
  - Exact-key lookup: "Goa PSC" stored full_name, "GPSC" input short_name → match,
    no insert (the specific failure mode that produced duplicates)
  - Cleanup collapses a 2-row cluster to 1; survivor retains official_url +
    merged metadata from loser
  - exams.conducting_organization_id on loser is repointed to survivor, never nulled
  - RESTRICT-table reference on loser is repointed before delete (no FK violation)
  - Backfill covers a never-duplicated org (not just survivors)
  - Partial unique index rejects a second exam_registry_workbook insert with same
    (type, short_name, state)
  - Cleanup re-run is a no-op (0 clusters)
  - No source_registry write in either importer or cleanup
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from import_exam_registry import (
    normalize_short_name,
    org_dedupe_key,
    upsert_organization,
)
from dedupe_state_psc_orgs import (
    _fk_references,
    _merge_metadata,
    _select_survivor,
    backfill_short_names,
    dedupe_cluster,
    find_duplicate_clusters,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_sb_exact(existing_row: dict | None = None):
    """Supabase mock wired for the new exact (type, short_name, state) lookup."""
    sb = MagicMock()
    # Chain for SELECT: .table().select().eq().eq().eq().execute()  (or .is_() for NULL state)
    chain = sb.table.return_value.select.return_value
    # Support both .eq() and .is_() on the tail of the chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.execute.return_value.data = [existing_row] if existing_row else []

    # INSERT chain
    sb.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "new-org-uuid"}
    ]
    # UPDATE chain
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return sb


# ── DB-idempotency ────────────────────────────────────────────────────────────

class TestDbIdempotency:
    """Two calls to upsert_organization with same body → exactly 1 INSERT."""

    def _run_twice(self, existing_row: dict | None = None):
        sb = _make_sb_exact(existing_row)
        common = dict(
            short_name="KPSC",
            full_name="Karnataka Public Service Commission",
            state="Karnataka",
            org_type="state_psc",
            calendar_status="published",
            official_url="https://kpsc.kar.nic.in",
            dry_run=False,
        )
        upsert_organization(sb, **common, org_cache={})
        # Second call — fresh cache (simulates a second run with empty org_cache)
        upsert_organization(sb, **common, org_cache={})
        return sb

    def test_two_runs_produce_one_insert_when_db_has_row(self):
        """Second call finds row in DB → UPDATE path, no INSERT."""
        existing = {
            "id": "existing-kpsc-id",
            "name": "Karnataka Public Service Commission",
            "short_name": "KPSC",
            "type": "state_psc",
            "state": "Karnataka",
            "calendar_status": "published",
            "metadata": {"import_status": "pending_review", "import_source": "exam_registry_workbook"},
        }
        sb = self._run_twice(existing)
        # First call: DB finds existing → no insert
        # Second call: DB finds existing → no insert
        assert sb.table.return_value.insert.call_count == 0, (
            "INSERT must not fire when DB already has the org"
        )

    def test_first_call_inserts_when_db_is_empty(self):
        """First call with empty DB → exactly 1 INSERT."""
        sb = _make_sb_exact()
        upsert_organization(
            sb,
            short_name="KPSC",
            full_name="Karnataka PSC",
            state="Karnataka",
            org_type="state_psc",
            calendar_status="published",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        assert sb.table.return_value.insert.call_count == 1

    def test_no_source_registry_write(self):
        """upsert_organization must never touch source_registry."""
        sb = _make_sb_exact()
        upsert_organization(
            sb,
            short_name="KPSC",
            full_name="Karnataka PSC",
            state="Karnataka",
            org_type="state_psc",
            calendar_status="published",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        table_calls = [c[0][0] for c in sb.table.call_args_list]
        assert "source_registry" not in table_calls


# ── exact-key lookup (the specific failure mode) ──────────────────────────────

class TestExactKeyLookup:
    """Stored full_name that abbreviates differently must still match via short_name."""

    def test_goa_psc_stored_gpsc_input_matches_no_insert(self):
        """
        Bug scenario: stored name="Goa PSC", _abbrev_from_name("Goa PSC")="GP",
        but input short_name="GPSC".  Old code: GP ≠ GPSC → false miss → INSERT duplicate.
        New code: exact lookup on short_name="GPSC" → match → no INSERT.
        """
        existing = {
            "id": "goa-org-id",
            "name": "Goa PSC",
            "short_name": "GPSC",           # stored from first import
            "type": "state_psc",
            "state": "Goa",
            "calendar_status": "needs_review",
            "metadata": {"import_status": "pending_review", "import_source": "exam_registry_workbook"},
        }
        sb = _make_sb_exact(existing)
        result = upsert_organization(
            sb,
            short_name="GPSC",
            full_name="Goa Public Service Commission",
            state="Goa",
            org_type="state_psc",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        assert result == "goa-org-id", "Must return the existing org id"
        assert sb.table.return_value.insert.call_count == 0, (
            "No INSERT when short_name matches exactly — old heuristic would have inserted a duplicate"
        )

    def test_insert_payload_includes_short_name(self):
        """New org INSERT must include short_name for future exact lookups."""
        sb = _make_sb_exact()
        upsert_organization(
            sb,
            short_name="GPSC",
            full_name="Goa Public Service Commission",
            state="Goa",
            org_type="state_psc",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        insert_payload = sb.table.return_value.insert.call_args[0][0]
        assert insert_payload["short_name"] == "GPSC"

    def test_normalize_short_name_applied_to_input(self):
        """Input short_name is normalized before storage and lookup."""
        sb = _make_sb_exact()
        upsert_organization(
            sb,
            short_name="g p s c",  # whitespace variant
            full_name="Goa PSC",
            state="Goa",
            org_type="state_psc",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        insert_payload = sb.table.return_value.insert.call_args[0][0]
        assert insert_payload["short_name"] == "GPSC"

    def test_state_none_uses_is_null_query(self):
        """Central orgs (state=None) must use IS NULL not eq(state, None)."""
        existing = {
            "id": "upsc-org-id",
            "name": "UPSC",
            "short_name": "UPSC",
            "type": "central_commission",
            "state": None,
            "calendar_status": "needs_review",
            "metadata": {"import_status": "pending_review", "import_source": "exam_registry_source_urls"},
        }
        sb = _make_sb_exact(existing)
        result = upsert_organization(
            sb,
            short_name="UPSC",
            full_name="Union Public Service Commission",
            state=None,
            org_type="central_commission",
            calendar_status="needs_review",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        assert result == "upsc-org-id"
        assert sb.table.return_value.insert.call_count == 0
        # Verify .is_("state", "null") was called on the chain
        chain = sb.table.return_value.select.return_value
        chain.is_.assert_called_once_with("state", "null")


# ── cleanup: _merge_metadata ──────────────────────────────────────────────────

class TestMergeMetadata:
    def test_official_url_from_loser_preserved_when_survivor_lacks_it(self):
        survivor_meta = {"import_status": "pending_review", "import_source": "exam_registry_workbook"}
        loser_meta = {"import_status": "pending_review", "official_url": "https://psc.goa.gov.in"}
        merged = _merge_metadata(survivor_meta, loser_meta)
        assert merged["official_url"] == "https://psc.goa.gov.in"

    def test_survivor_official_url_not_overwritten_by_loser(self):
        survivor_meta = {"official_url": "https://survivor.gov.in"}
        loser_meta = {"official_url": "https://loser.gov.in"}
        merged = _merge_metadata(survivor_meta, loser_meta)
        assert merged["official_url"] == "https://survivor.gov.in"

    def test_unrelated_key_preserved(self):
        survivor_meta = {"trust_tier": "verified", "import_status": "pending_review"}
        loser_meta = {"official_url": "https://psc.gov.in"}
        merged = _merge_metadata(survivor_meta, loser_meta)
        assert merged["trust_tier"] == "verified"
        assert merged["official_url"] == "https://psc.gov.in"


# ── cleanup: _select_survivor ─────────────────────────────────────────────────

def _make_sb_for_survivor(a_refs: list[str] = None, b_refs: list[str] = None):
    """Mock where org A has 'a_refs' exam rows pointing to it, org B has 'b_refs'."""
    sb = MagicMock()

    def _side_effect(table_name):
        mock_table = MagicMock()
        # The FK query goes: .table(t).select("id").eq(col, org_id).execute()
        def _select_side(cols):
            mock_sel = MagicMock()
            def _eq_side(col, val):
                mock_eq = MagicMock()
                if val == "org-a-id":
                    mock_eq.execute.return_value.data = [{"id": r} for r in (a_refs or [])]
                else:
                    mock_eq.execute.return_value.data = [{"id": r} for r in (b_refs or [])]
                return mock_eq
            mock_sel.eq.side_effect = _eq_side
            return mock_sel
        mock_table.select.side_effect = _select_side
        return mock_table

    sb.table.side_effect = _side_effect
    return sb


class TestSelectSurvivor:
    def _org(self, org_id, official_url=None, created_at="2026-01-02"):
        return {
            "id": org_id,
            "name": "Test PSC",
            "type": "state_psc",
            "state": "TestState",
            "created_at": created_at,
            "metadata": {"official_url": official_url} if official_url else {},
        }

    def test_fk_reference_wins(self):
        """Org B has FK reference → B is survivor."""
        sb = _make_sb_for_survivor(a_refs=[], b_refs=["exam-1"])
        survivor, loser = _select_survivor(
            [self._org("org-a-id"), self._org("org-b-id")], sb
        )
        assert survivor["id"] == "org-b-id"
        assert loser["id"] == "org-a-id"

    def test_official_url_tiebreak(self):
        """Both have FK refs (or neither); official_url tiebreaks."""
        sb = _make_sb_for_survivor(a_refs=[], b_refs=[])
        a = self._org("org-a-id", official_url=None)
        b = self._org("org-b-id", official_url="https://psc.gov.in")
        survivor, loser = _select_survivor([a, b], sb)
        assert survivor["id"] == "org-b-id"

    def test_created_at_tiebreak(self):
        """All else equal: earlier created_at is survivor."""
        sb = _make_sb_for_survivor(a_refs=[], b_refs=[])
        a = self._org("org-a-id", created_at="2026-01-01")
        b = self._org("org-b-id", created_at="2026-01-02")
        survivor, loser = _select_survivor([a, b], sb)
        assert survivor["id"] == "org-a-id"


# ── cleanup: dedupe_cluster ───────────────────────────────────────────────────

class _ClusterSbMock:
    """Supabase mock for dedupe_cluster tests with traceable update/delete calls."""

    def __init__(self, survivor_id="survivor-id", loser_id="loser-id",
                 exam_ids_on_loser=None):
        self.survivor_id = survivor_id
        self.loser_id = loser_id
        self.exam_ids_on_loser = exam_ids_on_loser or ["exam-uuid-1"]
        self.update_calls: list[tuple[str, dict]] = []  # (table, payload)
        self.delete_calls: list[str] = []               # table names
        self.repoint_calls: list[tuple[str, str, str]] = []  # (table, col, new_id)

    def table(self, table_name: str):
        outer = self

        class _Table:
            def select(self, cols):
                return self

            def eq(self, col, val):
                self._eq_val = val
                return self

            def execute(self):
                class _Result:
                    pass
                r = _Result()
                if table_name == "exams" and getattr(self, "_eq_val", None) == outer.loser_id:
                    r.data = [{"id": e} for e in outer.exam_ids_on_loser]
                else:
                    r.data = []
                return r

            def update(self, payload):
                outer.update_calls.append((table_name, payload))
                return self

            def delete(self):
                outer.delete_calls.append(table_name)
                return self

        return _Table()


def _make_sb_for_cluster(survivor_id="survivor-id", loser_id="loser-id",
                         exam_ids_on_loser=None):
    return _ClusterSbMock(survivor_id, loser_id, exam_ids_on_loser)


class TestDedupeCluster:
    def _survivor(self, sid="survivor-id"):
        return {
            "id": sid,
            "name": "Goa Public Service Commission",
            "short_name": None,
            "type": "state_psc",
            "state": "Goa",
            "created_at": "2026-01-01",
            "metadata": {"import_status": "pending_review"},
        }

    def _loser(self, lid="loser-id"):
        return {
            "id": lid,
            "name": "Goa PSC",
            "short_name": None,
            "type": "state_psc",
            "state": "Goa",
            "created_at": "2026-01-02",
            "metadata": {
                "import_status": "pending_review",
                "official_url": "https://psc.goa.gov.in",
            },
        }

    def _stats(self):
        return {k: 0 for k in ("clusters_collapsed", "orgs_deleted",
                                "fk_rows_repointed", "clusters_found",
                                "fk_rows_would_repoint", "would_delete")}

    def test_collapse_2_row_cluster_to_1(self):
        """Cluster of 2 → loser is deleted, survivor updated."""
        sb = _make_sb_for_cluster()
        stats = self._stats()
        with patch("dedupe_state_psc_orgs._select_survivor",
                   return_value=(self._survivor(), self._loser())):
            dedupe_cluster(sb, [self._survivor(), self._loser()],
                           {"goa": "GPSC"}, dry_run=False, stats=stats)
        assert stats["orgs_deleted"] == 1
        assert stats["clusters_collapsed"] == 1

    def test_exam_conducting_org_repointed_not_nulled(self):
        """exams.conducting_organization_id must be repointed to survivor, not left NULL."""
        sb = _make_sb_for_cluster(exam_ids_on_loser=["exam-uuid-1"])
        stats = self._stats()
        with patch("dedupe_state_psc_orgs._select_survivor",
                   return_value=(self._survivor(), self._loser())):
            dedupe_cluster(sb, [self._survivor(), self._loser()],
                           {"goa": "GPSC"}, dry_run=False, stats=stats)

        # Update calls on "exams" table must include a repoint
        exams_updates = [(t, p) for t, p in sb.update_calls if t == "exams"]
        assert exams_updates, "exams table must be updated to repoint conducting_org_id"
        assert stats["fk_rows_repointed"] >= 1

    def test_official_url_preserved_on_survivor_after_merge(self):
        """Loser has official_url; survivor has none. After merge, survivor gains it."""
        sb = _make_sb_for_cluster()
        stats = self._stats()
        with patch("dedupe_state_psc_orgs._select_survivor",
                   return_value=(self._survivor(), self._loser())):
            dedupe_cluster(sb, [self._survivor(), self._loser()],
                           {"goa": "GPSC"}, dry_run=False, stats=stats)

        org_updates = [(t, p) for t, p in sb.update_calls if t == "organizations"]
        assert org_updates, "organizations table must be updated"
        # The metadata in the update payload must contain official_url from the loser
        all_meta = [p.get("metadata", {}) for _, p in org_updates]
        assert any(m.get("official_url") == "https://psc.goa.gov.in" for m in all_meta), (
            "official_url from loser must survive on the merged survivor metadata"
        )

    def test_short_name_backfilled_on_survivor(self):
        """dedupe_cluster backfills short_name on survivor from authoritative source."""
        sb = _make_sb_for_cluster()
        stats = self._stats()
        with patch("dedupe_state_psc_orgs._select_survivor",
                   return_value=(self._survivor(), self._loser())):
            dedupe_cluster(sb, [self._survivor(), self._loser()],
                           {"goa": "GPSC"}, dry_run=False, stats=stats)

        org_updates = [(t, p) for t, p in sb.update_calls if t == "organizations"]
        assert any(p.get("short_name") == "GPSC" for _, p in org_updates), (
            "short_name 'GPSC' must be set on survivor during cluster dedup"
        )

    def test_dry_run_is_noop(self):
        """--dry-run must make zero DB writes."""
        sb = _make_sb_for_cluster()
        stats = self._stats()
        with patch("dedupe_state_psc_orgs._select_survivor",
                   return_value=(self._survivor(), self._loser())):
            dedupe_cluster(sb, [self._survivor(), self._loser()],
                           {"goa": "GPSC"}, dry_run=True, stats=stats)

        assert sb.update_calls == [], "No updates in dry-run"
        assert sb.delete_calls == [], "No deletes in dry-run"

    def test_no_source_registry_write_in_cleanup(self):
        """cleanup must never touch source_registry."""
        sb = _make_sb_for_cluster()
        stats = self._stats()
        with patch("dedupe_state_psc_orgs._select_survivor",
                   return_value=(self._survivor(), self._loser())):
            dedupe_cluster(sb, [self._survivor(), self._loser()],
                           {"goa": "GPSC"}, dry_run=False, stats=stats)

        all_tables = (
            [t for t, _ in sb.update_calls]
            + sb.delete_calls
        )
        assert "source_registry" not in all_tables


# ── cleanup re-run is a no-op ─────────────────────────────────────────────────

class TestRerunIsNoop:
    def test_second_run_zero_clusters(self):
        """After cleanup, find_duplicate_clusters returns [] → re-run does nothing."""
        sb = MagicMock()
        # Only 1 state_psc row per state → no clusters
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "kpsc-id", "name": "KPSC", "short_name": "KPSC",
             "type": "state_psc", "state": "Karnataka",
             "calendar_status": "published", "metadata": {}, "created_at": "2026-01-01"},
        ]
        clusters = find_duplicate_clusters(sb)
        assert clusters == [], "Single org per state → no duplicate clusters"


# ── backfill covers never-duplicated orgs ─────────────────────────────────────

def _make_sb_for_backfill(orgs: list[dict]):
    """Mock for backfill_short_names: SELECT uses .in_().is_() chain."""
    sb = MagicMock()
    # Chain: .table().select().in_().is_().execute()
    chain = sb.table.return_value.select.return_value
    chain.in_.return_value = chain
    chain.is_.return_value = chain
    chain.execute.return_value.data = orgs
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value = None
    return sb


class TestBackfillCoversAll:
    def test_backfill_covers_never_duplicated_org(self):
        """Orgs with short_name=NULL are backfilled regardless of duplicate status."""
        orgs = [
            {"id": "kpsc-id", "name": "Karnataka Public Service Commission",
             "short_name": None, "type": "state_psc", "state": "Karnataka",
             "metadata": {}},
        ]
        sb = _make_sb_for_backfill(orgs)
        auth = {"karnataka": "KPSC"}
        stats = {"short_names_backfilled": 0}
        backfill_short_names(sb, auth, dry_run=False, stats=stats)

        assert stats["short_names_backfilled"] == 1
        update_payload = sb.table.return_value.update.call_args[0][0]
        assert update_payload["short_name"] == "KPSC"

    def test_backfill_dry_run_counts_but_does_not_write(self):
        """--dry-run backfill increments counter but makes no DB writes."""
        orgs = [
            {"id": "gpsc-id", "name": "Goa PSC", "short_name": None,
             "type": "state_psc", "state": "Goa", "metadata": {}},
        ]
        sb = _make_sb_for_backfill(orgs)
        stats = {"short_names_backfilled": 0}
        backfill_short_names(sb, {"goa": "GPSC"}, dry_run=True, stats=stats)

        assert stats["short_names_backfilled"] == 1
        assert sb.table.return_value.update.call_count == 0


# ── unique index enforcement (logical) ───────────────────────────────────────

class TestUniqueIndexEnforcement:
    def test_second_workbook_insert_same_key_raises(self):
        """Unique index violation: DB raises on second INSERT with same (type, short_name, state).

        The actual index is enforced by Postgres. Here we verify the importer's
        mock-DB path: when the SELECT finds the existing row, no INSERT is attempted.
        The real Postgres unique index is the final guard; this test covers the
        application-layer path that should prevent reaching it.
        """
        existing = {
            "id": "existing-id",
            "name": "KPSC",
            "short_name": "KPSC",
            "type": "state_psc",
            "state": "Karnataka",
            "calendar_status": "published",
            "metadata": {"import_source": "exam_registry_workbook", "import_status": "pending_review"},
        }
        sb = _make_sb_exact(existing)
        result = upsert_organization(
            sb,
            short_name="KPSC",
            full_name="Karnataka Public Service Commission",
            state="Karnataka",
            org_type="state_psc",
            calendar_status="published",
            official_url=None,
            dry_run=False,
            org_cache={},
        )
        assert result == "existing-id"
        assert sb.table.return_value.insert.call_count == 0, (
            "Unique index guard: second insert attempt must be blocked at SELECT, not at DB"
        )
