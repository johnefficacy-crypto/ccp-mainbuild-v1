"""Schema-contract tests for migration 257 (eligibility document trust gate).

(Renumbered from 256 → 257 to avoid a collision with PR #983's
256_ca_relevance_window_sweep.sql.)

Repo convention (test_exam_stream_eligibility_migration.py): CI has no live-DB
migration harness, so these assert against the committed SQL text — schema
additions, FK actions, CHECK constraints, the direct-update block trigger, and
the two atomic review RPCs' locking / gate / grant surface.
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / ".." / "supabase" / "migrations" / "257_eligibility_document_trust_gate.sql"
).read_text().lower()


# ── A. exam_eligibility_rules columns + FKs ─────────────────────────────────


def test_rule_gains_source_document_fk_restrict():
    assert "add column if not exists source_document_id uuid" in MIGRATION
    assert "references public.document_assets(id) on delete restrict" in MIGRATION


def test_rule_gains_page_locator_and_created_by():
    assert "add column if not exists source_page_start integer" in MIGRATION
    assert "add column if not exists source_page_end integer" in MIGRATION
    assert "add column if not exists created_by uuid" in MIGRATION
    assert "references auth.users(id) on delete set null" in MIGRATION


def test_page_locator_checks():
    # positive
    assert "source_page_start is null or source_page_start > 0" in MIGRATION
    assert "source_page_end is null or source_page_end > 0" in MIGRATION
    # both present or both absent
    assert "(source_page_start is null) = (source_page_end is null)" in MIGRATION
    # end >= start
    assert "source_page_end >= source_page_start" in MIGRATION


def test_source_document_index():
    assert "idx_eer_source_document_id" in MIGRATION


# ── syllabus_documents reviewer attribution ─────────────────────────────────


def test_syllabus_documents_gain_reviewer_columns():
    assert "alter table public.syllabus_documents" in MIGRATION
    assert "add column if not exists reviewed_by uuid" in MIGRATION
    assert "add column if not exists reviewed_at timestamptz" in MIGRATION
    assert "add column if not exists reviewer_notes text" in MIGRATION


# ── B. direct-update block trigger ──────────────────────────────────────────


def test_verified_material_edit_block_trigger():
    assert "_exam_eligibility_rules_block_verified_material_edit" in MIGRATION
    assert "old.reviewer_status = 'verified'" in MIGRATION
    assert "new.reviewer_status = 'verified'" in MIGRATION
    assert "before update on public.exam_eligibility_rules" in MIGRATION
    # material fields watched
    for f in ("value_num", "value_text", "value_json", "source_document_id",
              "source_page_start", "source_page_end"):
        assert f"old.{f}" in MIGRATION


# ── C. review_syllabus_document RPC ─────────────────────────────────────────


def test_syllabus_rpc_is_security_definer_locked_and_gated():
    assert "create or replace function public.review_syllabus_document" in MIGRATION
    assert "security definer" in MIGRATION
    assert "from public.syllabus_documents\n    where id = p_document_id::uuid\n    for update" in MIGRATION
    # locks the linked asset too
    assert "from public.document_assets\n            where id = v_doc.source_document_id\n            for update" in MIGRATION
    # gate tokens
    for tok in (
        "source_document_id_missing", "source_document_id_wrong_scope",
        "source_document_id_wrong_kind", "source_document_id_not_processed",
        "source_document_id_untrusted_source_kind", "source_document_id_no_storage",
        "source_document_id_exam_mismatch", "source_document_id_cycle_mismatch",
        "source_document_id_no_extracted_pages", "reviewer_is_uploader",
        "uploader_missing",  # fail-closed on missing uploader attribution
    ):
        assert tok in MIGRATION
    # authoritative source kinds
    assert "'official_archive', 'official_scan'" in MIGRATION
    # notification/corrigendum only
    assert "not in ('notification', 'corrigendum')" in MIGRATION


def test_syllabus_rpc_clears_review_fields_off_verified():
    assert "reviewed_by     = null" in MIGRATION
    assert "reviewer_notes  = null" in MIGRATION


def test_syllabus_rpc_grants():
    assert "revoke execute on function public.review_syllabus_document(text, text, text, text, text, text) from public" in MIGRATION
    assert "grant  execute on function public.review_syllabus_document(text, text, text, text, text, text) to service_role" in MIGRATION


# ── D. review_exam_eligibility_rule RPC ─────────────────────────────────────


def test_rule_rpc_is_security_definer_locked_and_gated():
    assert "create or replace function public.review_exam_eligibility_rule" in MIGRATION
    assert "from public.exam_eligibility_rules\n    where id = p_rule_id::uuid\n    for update" in MIGRATION
    # reviewer separation — fail closed on missing authorship
    assert "reviewer_is_creator" in MIGRATION
    assert "creator_missing" in MIGRATION
    assert "v_rule.created_by::text = p_actor_id" in MIGRATION
    # page locator + verified syllabus + extracted pages
    assert "source_page_locator_missing" in MIGRATION
    assert "no_verified_syllabus_document" in MIGRATION
    assert "referenced_page_not_extracted" in MIGRATION
    assert "extraction_status = 'extracted'" in MIGRATION
    assert "trust_status       = 'verified'" in MIGRATION
    # the supporting syllabus authority row is LOCKED (no TOCTOU), ordered
    # syllabus → asset to match review_syllabus_document.
    assert "from public.syllabus_documents sd\n            where sd.source_document_id = v_rule.source_document_id" in MIGRATION
    assert "for update;\n            if v_syl_id is null then" in MIGRATION
    # ambiguity guard retained
    assert "ambiguous_linked_qualification" in MIGRATION


def test_rule_rpc_transition_matrix():
    assert "v_rule.reviewer_status = 'draft'    and p_target_status in ('verified', 'archived')" in MIGRATION
    assert "v_rule.reviewer_status = 'verified' and p_target_status in ('draft', 'archived')" in MIGRATION
    assert "v_rule.reviewer_status = 'archived' and p_target_status = 'draft'" in MIGRATION


def test_rule_rpc_grants():
    assert "revoke execute on function public.review_exam_eligibility_rule(text, text, text, text, text, text) from public" in MIGRATION
    assert "grant  execute on function public.review_exam_eligibility_rule(text, text, text, text, text, text) to service_role" in MIGRATION


# ── E. authority-dependency cascade-demotion trigger ────────────────────────


def test_cascade_demote_trigger_present():
    assert "_syllabus_documents_cascade_demote_dependent_rules" in MIGRATION
    assert "after update on public.syllabus_documents" in MIGRATION
    # fires when the authority is demoted OR its source/exam is reassigned
    assert "new.trust_status       is distinct from 'verified'" in MIGRATION
    assert "new.source_document_id is distinct from old.source_document_id" in MIGRATION
    # demotes dependent verified rules to draft, clearing the stamp
    assert "set    reviewer_status = 'draft'," in MIGRATION
    # only when no OTHER verified syllabus authority remains
    assert "and sd.id <> new.id" in MIGRATION
    # leaves a system audit trail
    assert "eligibility_rule.auto_demote" in MIGRATION


# ── Legacy safety ───────────────────────────────────────────────────────────


def test_migration_does_not_demote_or_mutate_legacy_rows():
    # Only additive schema + new constraints (satisfied by NULL) + functions.
    # No UPDATE of existing rows, no demotion of verified data.
    assert "update public.exam_eligibility_rules set" not in MIGRATION
    assert "update public.syllabus_documents set reviewer" not in MIGRATION
    # New columns are all NULLable — no NOT NULL default backfill on the wide table.
    assert "add column if not exists source_document_id uuid not null" not in MIGRATION
    assert "notify pgrst, 'reload schema';" in MIGRATION
