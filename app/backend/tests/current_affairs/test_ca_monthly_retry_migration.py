"""Migration 258 contract (GQR-G6) — text-assertion. Behavioural validation of the
monthly core+tail start / retry enqueue / sweep RPCs is VERIFY DB (validate_ca_monthly_retry.sql).
"""
from __future__ import annotations

from pathlib import Path

_SQL = (Path(__file__).parents[3] / "supabase/migrations/258_ca_monthly_retry.sql").read_text()
_NORM = " ".join(_SQL.lower().split())


def test_creates_retry_items_table_with_history_safe_fks():
    assert "create table if not exists public.current_affairs_retry_items" in _NORM
    # question_id can't dangle; a purged weekly attempt / exam never blocks the item.
    assert "question_id uuid not null references public.mock_question_bank(id) on delete restrict" in _NORM
    assert "source_attempt_id uuid references public.current_affairs_attempts(id) on delete set null" in _NORM
    assert "unique (user_id, question_id)" in _NORM
    assert "status in ('pending', 'consumed', 'expired')" in _NORM


def test_adds_core_tail_discriminator():
    assert "add column if not exists item_role text not null default 'core'" in _NORM
    assert "item_role in ('core', 'retry_tail')" in _NORM


def test_relevance_predicate_reuses_full_promoted_integrity():
    fn = _NORM.split("function public.ca_question_current_relevant")[1]
    assert "source_kind = 'current_event'" in fn
    assert "cl.reviewer_status = 'verified'" in fn and "cl.factual_status = 'current'" in fn
    assert "ev.status = 'active'" in fn
    assert "authority_level in ('primary_official', 'official_secondary')" in fn


def test_enqueue_only_relevant_mistakes_from_submitted_weekly():
    fn = _NORM.split("function public.ca_enqueue_weekly_retry_items")[1]
    assert "attempt_not_submitted" in fn and "not_a_weekly_attempt" in fn
    assert "coalesce(resp.is_correct, false) = false" in fn      # wrong answers only
    assert "ca_question_current_relevant" in fn                  # still-relevant only
    assert "on conflict (user_id, question_id) do nothing" in fn  # idempotent


def test_monthly_start_verifies_core_and_tail():
    fn = _NORM.split("function public.ca_start_monthly_current_affairs_attempt")[1]
    assert "not_a_monthly_bundle" in fn
    # CORE: equals the eligible bundle set, in order (no shrink).
    assert "bundle_degraded" in fn and "bundle_set_mismatch" in fn
    assert "ca_eligible_bundle_question_ids" in fn
    # TAIL: capped, owned pending item, no overlap/dup, still relevant.
    assert "retry_tail_cap_exceeded" in fn and "retry_tail_overlaps_core" in fn
    assert "retry_tail_not_eligible" in fn and "retry_tail_not_relevant" in fn
    # per-row content authority reused (text/answer/options vs locked bank).
    assert "snapshot_text_mismatch" in fn and "snapshot_options_mismatch" in fn
    # tail freezes as retry_tail and consumes the item (never deletes it).
    assert "'retry_tail'" in fn and "set status = 'consumed'" in fn
    # conflict-safe idempotent create.
    assert "on conflict (user_id, bundle_id) do nothing" in fn


def test_sweep_expires_never_deletes():
    fn = _NORM.split("function public.ca_sweep_expired_retry_items")[1]
    assert "set status = 'expired'" in fn
    assert "delete from" not in fn


def test_no_mastery_or_correction_write():
    # No fan-out into the mastery / mock-attempt / correction machinery (GA own-tables).
    for forbidden in ("user_topic_mastery", "apply_mock_mastery", "insert into public.mock_attempts",
                      "job_analytics_retry", "ensure_mock_correction", "mock_attempt_responses"):
        assert forbidden not in _NORM


def test_service_role_only_grants():
    assert "enable row level security" in _NORM
    assert "create policy" not in _NORM
    for sig in (
        "ca_question_current_relevant(uuid)",
        "ca_eligible_retry_tail(uuid)",
        "ca_enqueue_weekly_retry_items(uuid, uuid)",
        "ca_sweep_expired_retry_items()",
        "ca_start_monthly_current_affairs_attempt(uuid, uuid, uuid, jsonb, jsonb, jsonb)",
    ):
        assert f"revoke all on function public.{sig} from public, anon, authenticated" in _NORM
        assert f"grant execute on function public.{sig} to service_role" in _NORM


def test_security_definer_search_path():
    assert _NORM.count("security definer set search_path = public") >= 5
