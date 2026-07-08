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
MIG_186 = (_MIGRATIONS / "186_pyq_paper_source_document.sql").read_text().lower()
MIG_187 = (_MIGRATIONS / "187_review_doc_lock.sql").read_text().lower()


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


# ── 186 / 187 provenance deltas preserved (no regression) ─────────────────────
#
# 229 CREATE-OR-REPLACEs the RPC and fn_invalidate that migrations 186 and 187
# had already extended with source_document_id provenance. Because a stale
# 184-era body would silently drop those deltas, these tests assert that 229's
# rebuilt bodies still carry every 186/187 addition.

def test_rpc_selects_paper_source_document_id_alias():
    # 186: the paper SELECT must alias p.source_document_id so the hash and the
    # mock_question_sources write can reference it.
    assert "p.source_document_id    as paper_source_document_id" in MIGRATION


def test_content_hash_includes_source_document_id_before_option_and_section_fields():
    # 186: paper_source_document_id is hashed immediately after paper_source_type
    # and BEFORE the options/correct/tag/section/stimulus fields.
    assert "coalesce(v_q.paper_source_document_id::text, '')" in MIGRATION
    doc_pos = MIGRATION.index("coalesce(v_q.paper_source_document_id::text, '')")
    type_pos = MIGRATION.index("coalesce(v_q.paper_source_type, '')")
    section_pos = MIGRATION.index("coalesce(v_q.section_id::text, '')")
    opt_meta_pos = MIGRATION.index("coalesce(o.source_label, '')")
    # source_type (186 predecessor field) comes first, then paper_source_document_id,
    # then the PR-4 section_id and per-option printed-order fields.
    assert type_pos < doc_pos < section_pos
    assert doc_pos < opt_meta_pos


def test_mock_question_sources_insert_writes_source_document_id():
    # 186: the provenance INSERT carries source_document_id.
    assert "pyq_paper_id, pyq_year, evidence_text, source_document_id" in MIGRATION
    assert "v_q.paper_source_document_id" in MIGRATION


def test_rpc_revalidates_source_document_provenance_step_2a():
    # 187 step-2a: revalidate the attached document before projecting.
    assert "source_document_invalid" in MIGRATION
    assert "and scope         = 'admin_exam_intelligence'" in MIGRATION
    assert "and document_kind = 'pyq_paper'" in MIGRATION
    assert "and status        not in ('failed', 'archived')" in MIGRATION


def test_invalidation_fn_watches_source_document_id_on_pyq_papers():
    # 186: fn_invalidate_pyq_projection must re-invalidate when a paper's
    # source_document_id changes (the content hash includes it).
    assert "or (old.source_document_id is distinct from new.source_document_id)" in MIGRATION


def test_186_and_187_provenance_deltas_are_the_source_of_truth():
    # Sanity: the deltas 229 must preserve genuinely originate in 186/187.
    assert "p.source_document_id    as paper_source_document_id" in MIG_186
    assert "coalesce(v_q.paper_source_document_id::text, '')" in MIG_186
    assert "or (old.source_document_id  is distinct from new.source_document_id)" in MIG_186
    assert "source_document_invalid" in MIG_187


def test_rpc_follows_187_base_no_review_log_reintroduction():
    # 187 dropped the mock_question_review_log write from the projection RPC
    # (admin_audit_logs remains the authoritative audit trail). Because 229 is a
    # CREATE OR REPLACE that becomes the new live definition, it must NOT silently
    # revert that removal — 229 builds forward from 187, not 186/184.
    assert "insert into public.mock_question_review_log" not in MIGRATION
    assert "mock_question_review_log" not in MIG_187
    # 186/184 predecessors still carry the insert (proving the divergence is real).
    assert "insert into public.mock_question_review_log" in MIG_186


def test_rpc_return_object_matches_187_slim_shape():
    # 187 slimmed the RETURN to the fields the Python caller consumes; 229 keeps
    # that shape rather than 186/184's fuller object.
    assert "'mock_question_id', v_mock_q_id," in MIGRATION
    assert "'is_new',           v_is_new" in MIGRATION


# ── 183 / 184 remain immutable (new logic is forward-only) ────────────────────

def test_183_and_184_are_not_edited_with_pr4_logic():
    for text in (MIG_183, MIG_184):
        assert "mock_question_stimuli" not in text
        assert "stimulus_not_verified" not in text
        assert "trg_invalidate_pyq_projection_stim_upd" not in text
        assert "pyq_question_stimuli" not in text
