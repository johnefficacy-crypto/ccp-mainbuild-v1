"""Schema-contract tests for PYQ Intelligence v2 PR-4 migration 229
(projection / snapshot fidelity: section + printed-order + shared-stimulus
snapshot, verified-stimulus gating, and matching invalidation triggers).

Following the repo's documented convention (see
test_pyq_section_stimulus_schema_migration.py): "The repo has no live-DB
migration harness; existing migration tests assert against the migration SQL
text." Migrations 183/184 are MERGED + IMMUTABLE — the new projection fidelity
logic must live only in the forward migration (229), not by editing 183/184.
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

MIGRATION = (_MIGRATIONS / "229_pyq_projection_stimulus_fidelity.sql").read_text().lower()
MIG_183 = (_MIGRATIONS / "183_pyq_mock_projection_bridge.sql").read_text().lower()
MIG_184 = (_MIGRATIONS / "184_repair_pyq_mock_projection_bridge.sql").read_text().lower()


# ── Schema ───────────────────────────────────────────────────────────────────

def test_mock_question_bank_gains_section_id_snapshot():
    assert (
        "add column if not exists section_id uuid references public.exam_phase_sections(id) on delete set null"
        in MIGRATION
    )


def test_mock_question_options_gains_source_label_and_display_order():
    assert "add column if not exists source_label text" in MIGRATION
    assert "add column if not exists display_order integer" in MIGRATION


def test_mock_question_stimuli_table_shape():
    assert "create table if not exists public.mock_question_stimuli" in MIGRATION
    assert "mock_question_id uuid not null references public.mock_question_bank(id) on delete cascade" in MIGRATION
    # lineage only — NOT a cascading FK to pyq_stimuli
    assert "pyq_stimulus_id uuid" in MIGRATION
    assert "stimulus_type text not null" in MIGRATION
    assert "unique(mock_question_id, pyq_stimulus_id)" in MIGRATION
    assert "idx_mock_question_stimuli_question" in MIGRATION


def test_mock_question_stimuli_rls_and_service_role_grant():
    assert "alter table public.mock_question_stimuli enable row level security" in MIGRATION
    assert "mock_question_stimuli_admin_all" in MIGRATION
    assert "grant select, insert, update, delete on public.mock_question_stimuli to service_role" in MIGRATION


# ── RPC additions ────────────────────────────────────────────────────────────

def test_rpc_is_create_or_replace_and_selects_section_id():
    assert "create or replace function public.project_pyq_question_to_mock_bank" in MIGRATION
    assert "q.section_id," in MIGRATION


def test_rpc_has_stimulus_verification_gate():
    # conjunctive trust: any link ⇒ every link AND stimulus must be verified.
    assert "stimulus_not_verified" in MIGRATION
    assert "left join public.pyq_stimuli s on s.id = qs.stimulus_id" in MIGRATION
    assert "qs.reviewer_status is distinct from 'verified'" in MIGRATION
    assert "s.reviewer_status is distinct from 'verified'" in MIGRATION


def test_rpc_writes_section_and_option_printed_order():
    assert "section_id           = v_q.section_id" in MIGRATION
    assert "question_id, option_text, option_index, is_correct, source_label, display_order" in MIGRATION


def test_rpc_snapshots_verified_stimuli():
    assert "delete from public.mock_question_stimuli where mock_question_id = v_mock_q_id" in MIGRATION
    assert "insert into public.mock_question_stimuli" in MIGRATION
    assert "join public.pyq_stimuli s on s.id = qs.stimulus_id" in MIGRATION
    assert "and qs.reviewer_status = 'verified'" in MIGRATION
    assert "and s.reviewer_status  = 'verified'" in MIGRATION


def test_content_hash_appends_section_option_and_stimulus_fields():
    assert "coalesce(v_q.section_id::text, '')" in MIGRATION
    # per-verified-option printed-order metadata in the hash
    assert "coalesce(o.source_label, '')" in MIGRATION
    assert "coalesce(o.display_order::text, '')" in MIGRATION
    # per-verified-stimulus content in the hash
    assert "coalesce(s.stimulus_type, '')" in MIGRATION
    assert "coalesce(s.content_text, '')" in MIGRATION
    assert "order by qs.display_order nulls last, s.display_order nulls last, s.id" in MIGRATION


# ── Invalidation triggers ────────────────────────────────────────────────────

def test_invalidation_fn_branches_on_new_source_tables():
    assert "tg_table_name = 'pyq_stimuli'" in MIGRATION
    assert "tg_table_name = 'pyq_question_stimuli'" in MIGRATION


def test_new_invalidation_triggers_created():
    assert "trg_invalidate_pyq_projection_stim_upd" in MIGRATION
    assert "trg_invalidate_pyq_projection_stim_del" in MIGRATION
    assert "trg_invalidate_pyq_projection_qs_ins" in MIGRATION
    assert "trg_invalidate_pyq_projection_qs_upd" in MIGRATION
    assert "trg_invalidate_pyq_projection_qs_del" in MIGRATION
    assert "after update on public.pyq_stimuli" in MIGRATION
    assert "after delete on public.pyq_stimuli" in MIGRATION
    assert "after insert on public.pyq_question_stimuli" in MIGRATION
    assert "after update on public.pyq_question_stimuli" in MIGRATION
    assert "after delete on public.pyq_question_stimuli" in MIGRATION


def test_rpc_service_role_posture_preserved():
    assert "revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from anon" in MIGRATION
    assert "grant execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) to service_role" in MIGRATION
    assert "notify pgrst, 'reload schema'" in MIGRATION


# ── 183 / 184 remain immutable (new logic is forward-only) ────────────────────

def test_183_and_184_are_not_edited_with_pr4_logic():
    for text in (MIG_183, MIG_184):
        assert "mock_question_stimuli" not in text
        assert "stimulus_not_verified" not in text
        assert "trg_invalidate_pyq_projection_stim_upd" not in text
        assert "pyq_question_stimuli" not in text
