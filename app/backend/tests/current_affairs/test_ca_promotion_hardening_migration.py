"""Migration 251 contract (GQR-G4, checkpost #970 hardening) — text-assertion style.
Behavioural validation is VERIFY DB (validate_ca_promotion_rpcs.sql).
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3] / "supabase/migrations/251_current_affairs_promotion_hardening.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_drops_old_signatures_and_creates_new():
    # F3: signatures change → old ones dropped, new ones (timestamptz + reason) created.
    assert "drop function if exists public.ca_review_candidate(uuid, text, text, text, uuid, text)" in _NORM
    assert "drop function if exists public.ca_promote_candidate(uuid, text, uuid, text)" in _NORM
    assert "function public.ca_review_candidate(" in _NORM
    assert "function public.ca_promote_candidate(" in _NORM


def test_dual_cas_and_reason_on_both_rpcs():
    assert _NORM.count("p_expected_updated_at timestamptz") >= 2
    assert _NORM.count("updated_at is distinct from p_expected_updated_at") >= 2
    assert _NORM.count("invalid_reason: p_reason must be 8-500 characters") >= 2


def test_promotion_revalidates_stage_d():
    promote = _NORM.split("function public.ca_promote_candidate")[1]
    for tok in ("validation_not_passed", "no_linked_claim", "noncurrent_or_missing_claim",
                "no_resolvable_evidence", "sole_evidence_discovery_only",
                "must_have_exactly_four_options", "duplicate_options",
                "empty_stem", "empty_explanation"):
        assert tok in promote, tok


def test_multi_claim_provenance_links():
    # F5: one link per resolved claim; unique key includes claim_id.
    assert "foreach v_claim_id in array v_claim_ids" in _NORM
    assert "unique (candidate_id, mock_question_id, claim_id)" in _NORM
    assert "drop constraint if exists current_affairs_question_links_candidate_id_mock_question_id_key" in _NORM


def test_review_never_promotes():
    review = _NORM.split("function public.ca_review_candidate")[1].split("function public.ca_promote_candidate")[0]
    assert "in ('approved', 'rejected', 'review_ready')" in review
    assert "status = 'promoted'" not in review


def test_service_role_only_new_signatures():
    for sig in (
        "ca_review_candidate(uuid, text, timestamptz, text, text, text, uuid, text)",
        "ca_promote_candidate(uuid, text, timestamptz, text, uuid, text)",
    ):
        assert f"revoke all on function public.{sig} from public, anon, authenticated" in _NORM
        assert f"grant execute on function public.{sig} to service_role" in _NORM


def test_security_definer_search_path():
    assert _NORM.count("security definer set search_path = public") >= 2
