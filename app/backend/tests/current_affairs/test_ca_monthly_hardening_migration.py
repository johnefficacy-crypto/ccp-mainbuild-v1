"""Contract checks for migration 259 — atomic enqueue + guarded monthly start."""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/259_ca_monthly_retry_hardening.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_submit_atomically_enqueues_weekly_mistakes():
    fn = _NORM.split("function public.ca_submit_current_affairs_attempt")[1]
    assert "set status = 'submitted'" in fn
    assert "v_att.cadence = 'weekly'" in fn
    assert "ca_enqueue_weekly_retry_items(p_attempt_id, p_user)" in fn
    assert "'retry_enqueued', v_retry_enqueued" in fn


def test_retry_upsert_is_same_attempt_idempotent_but_new_attempt_rearms():
    fn = _NORM.split("function public.ca_enqueue_weekly_retry_items")[1]
    assert "on conflict (user_id, question_id) do update" in fn
    assert "set source_attempt_id = excluded.source_attempt_id" in fn
    assert "status = 'pending'" in fn
    assert (
        "where existing.source_attempt_id is distinct from excluded.source_attempt_id"
        in fn
    )


def test_guarded_monthly_start_serializes_and_reuses_before_delegate():
    fn = _NORM.split(
        "function public.ca_start_monthly_current_affairs_attempt_guarded"
    )[1]
    lock_at = fn.index("pg_advisory_xact_lock")
    existing_at = fn.index("from public.current_affairs_attempts")
    delegate_at = fn.index("return public.ca_start_monthly_current_affairs_attempt(")
    assert lock_at < existing_at < delegate_at
    assert "'outcome', 'reused'" in fn
    assert "'core_count'" in fn and "'retry_tail_count'" in fn


def test_guarded_start_canonicalises_frozen_list_metadata():
    fn = _NORM.split(
        "function public.ca_start_monthly_current_affairs_attempt_guarded"
    )[1]
    for key in (
        "'question_ids', to_jsonb(v_all)",
        "'core_question_ids', to_jsonb(v_core)",
        "'retry_tail_question_ids', to_jsonb(v_tail)",
        "'total_questions', cardinality(v_all)",
    ):
        assert key in fn


def test_only_guarded_monthly_start_is_service_role_entrypoint():
    assert (
        "grant execute on function public.ca_start_monthly_current_affairs_attempt_guarded"
        in _NORM
    )
    assert (
        "revoke execute on function public.ca_start_monthly_current_affairs_attempt("
        in _NORM
    )
    assert "from service_role" in _NORM


def test_hardening_stays_inside_ca_tables():
    for forbidden in (
        "user_topic_mastery",
        "insert into public.mock_attempts",
        "ensure_mock_correction",
        "job_analytics_retry",
    ):
        assert forbidden not in _NORM
