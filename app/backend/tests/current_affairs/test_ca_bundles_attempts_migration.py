"""Migration 253 contract (GQR-G5a) — text-assertion style. Behavioural validation
of the start/save/submit RPCs (integrity lock, ON CONFLICT idempotency, seq guard,
RESTRICT cascade) is VERIFY DB via validate_ca_attempt_rpcs.sql.

Guards the own-tables + mastery-bypass + history-preservation invariants at the schema
layer.
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3] / "supabase/migrations/253_current_affairs_bundles_attempts.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_creates_bundle_and_attempt_tables():
    for t in (
        "current_affairs_bundles",
        "current_affairs_bundle_questions",
        "current_affairs_attempts",
        "current_affairs_attempt_responses",
    ):
        assert f"create table if not exists public.{t}" in _NORM


def test_attempts_are_own_tables_not_mock_attempts():
    # The whole point: GA never writes mock_attempts (no mastery/correction fan-out).
    assert "insert into public.mock_attempts" not in _NORM
    assert "mock_attempt_responses" not in _NORM
    # one attempt per learner+bundle (idempotent start).
    assert "unique (user_id, bundle_id)" in _NORM


def test_deleting_a_bundle_preserves_history():
    # F7: attempt→bundle must be ON DELETE RESTRICT so a bundle delete cannot cascade
    # away historical learner analytics.
    assert "bundle_id uuid not null references public.current_affairs_bundles(id) on delete restrict" in _NORM


def test_exam_family_scope_is_a_real_fk():
    # F2: exam_family_id is a real FK to exam_families, not a bare uuid.
    assert "exam_family_id uuid references public.exam_families(id) on delete set null" in _NORM


def test_no_advertised_attempt_ttl():
    # F4: no invented per-attempt expiry column/status (start gate is bundle availability).
    assert "expires_at" not in _NORM
    assert "'expired'" not in _NORM


def test_start_rpc_defined_conflict_safe_and_integrity_locked():
    assert "function public.ca_start_current_affairs_attempt" in _NORM
    start = _NORM.split("function public.ca_start_current_affairs_attempt")[1]
    # bundle locked + gated (published + verified + windows).
    assert "for update" in start
    assert "bundle_not_published" in start and "bundle_not_verified" in start
    assert "bundle_unavailable" in start
    # authoritative eligible set + exact-set integrity + no silent shortening.
    assert "ca_eligible_bundle_question_ids" in start
    assert "bundle_set_mismatch" in start
    assert "empty_bundle" in start
    # conflict-safe idempotent create.
    assert "on conflict (user_id, bundle_id) do nothing" in start
    assert "'reused'" in start


def test_save_rpc_defined_atomic_with_seq_and_option_guards():
    assert "function public.ca_save_current_affairs_answer" in _NORM
    save = _NORM.split("function public.ca_save_current_affairs_answer")[1]
    assert "for update" in save  # attempt + response locked
    assert "not_attempt_owner" in save
    assert "attempt_not_in_progress" in save
    assert "question_not_in_attempt" in save
    assert "option_not_in_question" in save
    # idempotent no-op on equal-or-lower client_seq (never an overwrite).
    assert "p_client_seq, 0) <= coalesce(v_resp.client_seq, 0)" in save
    assert "already_recorded" in save


def test_eligible_membership_helper_gates_reviewed_current_event_in_window():
    assert "function public.ca_eligible_bundle_question_ids" in _NORM
    helper = _NORM.split("function public.ca_eligible_bundle_question_ids")[1]
    assert "source_kind = 'current_event'" in helper
    assert "is_current_based = true" in helper
    assert "reviewer_status in ('verified', 'published', 'live')" in helper
    assert "valid_until is null or q.valid_until > now()" in helper


def test_submit_scores_inline_no_mastery():
    submit = _NORM.split("function public.ca_submit_current_affairs_attempt")[1]
    # ownership + inline scoring against the frozen snapshot; no mastery/analytics call.
    assert "not_attempt_owner" in submit
    assert "question_snapshot->>'correct_option_id'" in submit
    for forbidden in ("masterywriter", "apply_mock_mastery", "schedule_job",
                      "compute_and_persist", "job_analytics_retry"):
        assert forbidden not in _NORM


def test_service_role_only_grants():
    assert "enable row level security" in _NORM
    assert "create policy" not in _NORM
    for sig in (
        "ca_eligible_bundle_question_ids(uuid)",
        "ca_start_current_affairs_attempt(uuid, uuid, uuid, jsonb, jsonb)",
        "ca_save_current_affairs_answer(uuid, uuid, uuid, uuid, boolean, integer, integer)",
        "ca_submit_current_affairs_attempt(uuid, uuid)",
    ):
        assert f"revoke all on function public.{sig} from public, anon, authenticated" in _NORM
        assert f"grant execute on function public.{sig} to service_role" in _NORM


def test_security_definer_search_path():
    assert _NORM.count("security definer set search_path = public") >= 4
