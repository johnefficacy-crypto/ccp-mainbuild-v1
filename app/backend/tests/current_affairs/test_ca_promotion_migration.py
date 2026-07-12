"""Migration 248 contract (GQR-G4a) — text-assertion style. Behavioural validation
of the review/promotion RPCs is VERIFY DB (validate_ca_promotion_rpcs.sql).

Guards the human-gate + audited-promotion invariants at the schema layer.
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3] / "supabase/migrations/248_current_affairs_promotion.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_creates_links_table_and_two_rpcs():
    assert "create table if not exists public.current_affairs_question_links" in _NORM
    assert "function public.ca_review_candidate" in _NORM
    assert "function public.ca_promote_candidate" in _NORM


def test_review_never_promotes():
    # ca_review_candidate must not accept 'promoted' as a target status.
    review = _NORM.split("function public.ca_review_candidate")[1].split("function public.ca_promote_candidate")[0]
    assert "in ('approved', 'rejected', 'review_ready')" in review
    # review must never WRITE the terminal 'promoted' status (only ca_promote_candidate does).
    assert "status = 'promoted'" not in review
    assert "p_new_status = 'promoted'" not in review


def test_promotion_is_cas_guarded_and_requires_approved():
    promote = _NORM.split("function public.ca_promote_candidate")[1]
    assert "concurrent_modification" in promote
    assert "candidate_not_approved" in promote
    # freshness gate: only a live, unexpired event may be promoted.
    assert "event_not_active" in promote and "event_relevance_expired" in promote


def test_promotion_writes_current_event_isolation():
    promote = _NORM.split("function public.ca_promote_candidate")[1]
    assert "insert into public.mock_question_bank" in promote
    assert "'current_event'" in promote
    assert "is_current_based" in promote
    assert "current_affairs_item_id" in promote
    # options child table + correct-option resolution.
    assert "insert into public.mock_question_options" in promote
    assert "correct_option_id = v_correct_opt_id" in promote
    # provenance link + candidate terminal state.
    assert "insert into public.current_affairs_question_links" in promote
    assert "status = 'promoted'" in promote


def test_both_rpcs_audit():
    assert _NORM.count("insert into public.admin_audit_logs") >= 2
    assert "ca_candidate_status_transition" in _NORM
    assert "ca_candidate_promoted" in _NORM


def test_service_role_only_grants():
    assert "enable row level security" in _NORM
    assert "create policy" not in _NORM
    for sig in (
        "ca_review_candidate(uuid, text, text, text, uuid, text)",
        "ca_promote_candidate(uuid, text, uuid, text)",
    ):
        assert f"revoke all on function public.{sig} from public, anon, authenticated" in _NORM
        assert f"grant execute on function public.{sig} to service_role" in _NORM


def test_security_definer_search_path():
    assert _NORM.count("security definer set search_path = public") >= 2
