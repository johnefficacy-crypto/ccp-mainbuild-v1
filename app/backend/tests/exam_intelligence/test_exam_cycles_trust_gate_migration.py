"""Schema-contract tests for migration 261 (exam_cycles trust gate).

Repo convention (test_document_trust_gate_migration.py): CI has no live-DB
migration harness for these text assertions, so they assert against the
committed SQL text — the review lifecycle column + one-time legacy grandfather,
the verified-only RLS read policy replacing the permissive 035 policy, the
verified-material-edit block trigger, and the atomic CAS review RPC's
locking / transition / reviewer-separation / grant surface.

The behavioural proof (applying the migration to a real Postgres) lives in
tests/study_os/test_exam_cycles_trust_gate_behaviour.py.
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / ".." / "supabase" / "migrations" / "261_exam_cycles_trust_gate.sql"
).read_text().lower()


# ── A. review lifecycle column + legacy grandfather ─────────────────────────


def test_reviewer_status_column_default_draft():
    assert "add column reviewer_status text not null default 'draft'" in MIGRATION
    assert "reviewer_status in ('draft', 'reviewed', 'verified')" in MIGRATION


def test_legacy_rows_grandfathered_to_verified_only_on_first_apply():
    # The backfill is guarded by a column-existence check so a re-apply is a
    # no-op (idempotent) — it never blanket-re-verifies rows drafted since.
    assert "and column_name  = 'reviewer_status'" in MIGRATION
    assert "if not v_col_exists then" in MIGRATION
    assert "update public.exam_cycles set reviewer_status = 'verified';" in MIGRATION


def test_reviewer_attribution_and_authorship_columns():
    assert "add column if not exists reviewed_by uuid" in MIGRATION
    assert "add column if not exists reviewed_at timestamptz" in MIGRATION
    assert "add column if not exists created_by uuid" in MIGRATION
    assert "references auth.users(id) on delete set null" in MIGRATION


def test_reviewer_status_index():
    assert "idx_exam_cycles_reviewer_status" in MIGRATION


# ── B. verified-only RLS read policy ────────────────────────────────────────


def test_permissive_policy_replaced_with_verified_only():
    # the old permissive 035 policy is dropped
    assert "drop policy if exists exam_cycles_read_authenticated on public.exam_cycles" in MIGRATION
    # and replaced by a verified-only (admin-exempt) read policy using the
    # canonical app-metadata role predicate, never deprecated profiles.is_admin.
    assert "create policy exam_cycles_read_verified on public.exam_cycles" in MIGRATION
    assert "reviewer_status = 'verified'" in MIGRATION
    assert "public.is_admin(auth.uid())" in MIGRATION
    assert "p.is_admin = true" not in MIGRATION


# ── C. verified-material-edit block trigger ─────────────────────────────────


def test_verified_material_edit_block_trigger():
    assert "_exam_cycles_block_verified_material_edit" in MIGRATION
    assert "old.reviewer_status in ('reviewed', 'verified')" in MIGRATION
    assert "new.reviewer_status is distinct from 'draft'" in MIGRATION
    assert "before update on public.exam_cycles" in MIGRATION
    # reviewed content watched
    for f in ("exam_id", "year", "cycle_name", "notification_date",
              "application_start", "application_end", "exam_start", "exam_end",
              "source_url", "metadata"):
        assert f"old.{f}" in MIGRATION
    # operational status + planner exposure are deliberately NOT watched
    assert "old.status" not in MIGRATION
    assert "old.planner_activation_enabled" not in MIGRATION


# ── D. review_exam_cycle RPC ────────────────────────────────────────────────


def test_review_rpc_is_security_definer_locked_and_cas():
    assert "create or replace function public.review_exam_cycle" in MIGRATION
    assert "security definer" in MIGRATION
    # locks the cycle row
    assert "from public.exam_cycles\n    where id = p_cycle_id::uuid\n    for update" in MIGRATION
    # CAS on expected status
    assert "v_cycle.reviewer_status is distinct from p_expected_status" in MIGRATION
    assert "concurrent_modification" in MIGRATION


def test_review_rpc_transition_matrix():
    assert "v_cycle.reviewer_status = 'draft'    and p_target_status = 'reviewed'" in MIGRATION
    assert "v_cycle.reviewer_status = 'reviewed' and p_target_status in ('verified', 'draft')" in MIGRATION
    assert "v_cycle.reviewer_status = 'verified' and p_target_status in ('reviewed', 'draft')" in MIGRATION


def test_review_rpc_reviewer_separation_fails_closed():
    assert "creator_missing" in MIGRATION
    assert "reviewer_is_creator" in MIGRATION
    assert "v_cycle.created_by::text = p_actor_id" in MIGRATION


def test_review_rpc_audit_and_stamp_clearing():
    assert "'exam_intel.cms.cycle.review'" in MIGRATION
    # a demotion to draft clears the reviewer stamp
    assert "reviewed_by      = null" in MIGRATION
    assert "reviewed_at      = null" in MIGRATION


def test_review_rpc_grants():
    assert "revoke execute on function public.review_exam_cycle(text, text, text, text, text, text) from public" in MIGRATION
    assert "grant  execute on function public.review_exam_cycle(text, text, text, text, text, text) to service_role" in MIGRATION


# ── Legacy safety ───────────────────────────────────────────────────────────


def test_notify_reload_present():
    assert "notify pgrst, 'reload schema';" in MIGRATION
