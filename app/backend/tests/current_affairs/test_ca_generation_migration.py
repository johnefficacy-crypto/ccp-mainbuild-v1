"""Migration 245 contract (GQR-G3) — text-assertion style (matches the repo's
migration contracts, e.g. test_ewp_service_role_grants_migration.py). Behavioural
validation of the plpgsql RPCs is VERIFY DB / operator apply.

Guards the shadow/no-authority + lease/fencing invariants at the schema layer.
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3] / "supabase/migrations/245_current_affairs_generation.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_creates_the_three_tables():
    for t in (
        "current_affairs_generation_runs",
        "current_affairs_question_candidates",
        "current_affairs_generation_jobs",
    ):
        assert f"create table if not exists public.{t}" in _NORM


def test_defines_the_five_rpcs():
    for fn in (
        "ca_enqueue_generation_job",
        "ca_claim_generation_job",
        "ca_complete_generation",
        "ca_fail_generation_job",
        "ca_sweep_stale_generation_jobs",
    ):
        assert f"function public.{fn}" in _NORM


def test_lease_fencing_invariants():
    # claim uses FOR UPDATE SKIP LOCKED + mints a claim_token; complete/fail re-check it.
    assert "for update skip locked" in _NORM
    assert "claim_token = v_token" in _NORM
    assert "ca_job_fencing_failed" in _NORM
    # running job must hold a lease + token.
    assert "ca_generation_jobs_running_lease_ck" in _NORM
    # single in-flight per document.
    assert "uq_ca_generation_jobs_active" in _NORM


def test_candidates_start_in_staging_never_promoted():
    # The candidate status enum has no side-channel to the objective bank; the pipeline
    # only writes staging + pending claims. Promotion is GQR-G4/G5.
    assert "'generated', 'validation_failed', 'review_ready', 'approved', 'rejected', 'promoted'" in _NORM
    assert "reviewer_status)" in _NORM and "'pending'" in _NORM
    # This migration must not WRITE the objective bank (a mention in the header
    # comment is fine; an insert/update/promotion is not).
    assert "insert into public.mock_question_bank" not in _NORM
    assert "update public.mock_question_bank" not in _NORM


def test_generation_runs_is_append_only():
    assert "trg_ca_generation_runs_immutable" in _NORM
    assert "append-only" in _NORM


def test_service_role_only_grants():
    assert "enable row level security" in _NORM
    # no client allow-policy
    assert "create policy" not in _NORM
    for fn_sig in (
        "ca_claim_generation_job(integer, text[])",
        "ca_complete_generation(uuid, uuid, uuid, jsonb, jsonb, text)",
        "ca_fail_generation_job(uuid, uuid, text, integer)",
    ):
        assert f"revoke all on function public.{fn_sig} from public, anon, authenticated" in _NORM
        assert f"grant execute on function public.{fn_sig} to service_role" in _NORM


def test_security_definer_search_path():
    assert _NORM.count("security definer set search_path = public") >= 5


def test_candidate_conflict_target_matches_partial_index():
    # checkpost #966 F2: ON CONFLICT must carry the partial-index predicate, or Postgres
    # cannot infer uq_caqc_fingerprint (partial WHERE question_fingerprint IS NOT NULL).
    assert "on conflict (question_fingerprint) where question_fingerprint is not null do nothing" in _NORM
    assert "on conflict (question_fingerprint) do nothing" not in _NORM


def test_replay_guard_precedes_fencing():
    # checkpost #966 F3: an already-'done' job must return 'replayed' BEFORE the running
    # lease/token fencing branch (completion clears the token).
    complete = _NORM.split("function public.ca_complete_generation")[1]
    replay_at = complete.find("'replayed'")
    fencing_at = complete.find("ca_job_fencing_failed")
    assert 0 <= replay_at < fencing_at


def test_candidate_audit_lineage_is_persisted():
    # checkpost #966 F1: every candidate is linked to its generator + verifier run.
    assert "_ca_insert_generation_run" in _NORM
    assert "generator_run_id = v_gen_run_id" in _NORM
    assert "verifier_run_id = v_ver_run_id" in _NORM
    # runs are inserted with candidate_id lineage (mcq_generation / verification).
    assert "'mcq_generation'" in _NORM and "'verification'" in _NORM
