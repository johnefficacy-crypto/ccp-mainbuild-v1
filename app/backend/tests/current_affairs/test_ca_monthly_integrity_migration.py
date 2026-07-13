"""Contract checks for migration 260 — exam scope, source ordering, full provenance."""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/260_ca_monthly_retry_integrity.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_retry_queue_records_source_order_and_newer_source_wins():
    assert "add column if not exists source_period_end date" in _NORM
    assert "add column if not exists source_started_at timestamptz" in _NORM
    assert "add column if not exists source_submitted_at timestamptz" in _NORM
    fn = _NORM.split("function public.ca_enqueue_weekly_retry_items")[1]
    assert "source_period_end = excluded.source_period_end" in fn
    assert "source_started_at = excluded.source_started_at" in fn
    assert "source_submitted_at = excluded.source_submitted_at" in fn
    assert "coalesce(existing.source_period_end, '-infinity'::date)" in fn
    assert "coalesce(existing.source_started_at, '-infinity'::timestamptz)" in fn
    assert "coalesce(existing.source_submitted_at, '-infinity'::timestamptz)" in fn
    assert ") < (" in fn


def test_current_relevance_requires_every_link_to_remain_grounded():
    fn = _NORM.split("function public.ca_question_current_relevant")[1]
    assert "and not exists" in fn
    assert "ql.event_id is distinct from q.current_affairs_item_id" in fn
    assert "cl.event_id is distinct from q.current_affairs_item_id" in fn
    assert "cl.reviewer_status is distinct from 'verified'" in fn
    assert "cl.factual_status is distinct from 'current'" in fn
    assert "not exists ( select 1 from public.current_affairs_claim_evidence" in fn
    assert "authority_level in ('primary_official', 'official_secondary')" in fn


def test_bundle_authority_reuses_strict_question_predicate():
    fn = _NORM.split("function public.ca_eligible_bundle_question_ids")[1]
    assert "ca_question_current_relevant(bq.mock_question_id)" in fn


def test_retry_selector_is_exact_exam_scoped():
    assert "drop function public.ca_eligible_retry_tail(uuid)" in _NORM
    fn = _NORM.split("function public.ca_eligible_retry_tail(")[1]
    assert "p_user uuid, p_exam uuid" in fn
    assert "ri.exam_id is not distinct from p_exam" in fn
    assert (
        "grant execute on function public.ca_eligible_retry_tail(uuid, uuid) to service_role"
        in _NORM
    )


def test_guarded_start_validates_bundle_before_reuse_and_rechecks_retry_exam():
    fn = _NORM.split(
        "function public.ca_start_monthly_current_affairs_attempt_guarded"
    )[1]
    assert "pg_advisory_xact_lock" in fn
    bundle_at = fn.index("from public.current_affairs_bundles")
    publish_at = fn.index("bundle_not_published")
    existing_at = fn.index("from public.current_affairs_attempts")
    assert bundle_at < publish_at < existing_at
    assert "bundle_not_verified" in fn
    assert "bundle_not_yet_published" in fn
    assert "bundle_unavailable" in fn
    assert "bundle_scope_mismatch: exam" in fn
    assert "v_existing.exam_id is distinct from p_exam" in fn
    assert "ri.exam_id is not distinct from p_exam" in fn
    assert "for update" in fn
    assert "return public.ca_start_monthly_current_affairs_attempt(" in fn
    assert (
        "grant execute on function public.ca_start_monthly_current_affairs_attempt_guarded"
        in _NORM
    )
    assert (
        "revoke execute on function public.ca_start_monthly_current_affairs_attempt("
        in _NORM
    )


def test_integrity_hardening_stays_out_of_mastery_and_mock_attempts():
    for forbidden in (
        "user_topic_mastery",
        "insert into public.mock_attempts",
        "ensure_mock_correction",
        "job_analytics_retry",
    ):
        assert forbidden not in _NORM
