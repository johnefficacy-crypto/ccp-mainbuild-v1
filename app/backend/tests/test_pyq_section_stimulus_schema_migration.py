"""Schema-contract tests for PYQ Intelligence v2 PR-1 migration 223
(section linkage, printed-order preservation, variable-option ordering,
shared stimuli).

Following the repo's documented convention (see
test_j3_applied_vs_appeared_migration.py / test_j3_competition_structure_migration.py):
"The repo has no live-DB migration harness; existing migration tests assert
against the migration SQL text."
"""
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase" / "migrations" / "223_pyq_section_stimulus_schema.sql"
).read_text().lower()


def test_pyq_questions_gains_section_and_order_columns():
    assert "section_id uuid references public.exam_phase_sections(id) on delete set null" in MIGRATION
    assert "source_question_ref text" in MIGRATION
    assert "add column if not exists display_order integer" in MIGRATION


def test_pyq_questions_display_order_is_positive_and_unique_per_paper():
    assert "pyq_questions_display_order_positive_chk" in MIGRATION
    assert "check (display_order is null or display_order >= 1)" in MIGRATION
    assert "pyq_questions_paper_display_order_uidx" in MIGRATION
    assert "on public.pyq_questions(pyq_paper_id, display_order) where display_order is not null" in MIGRATION


def test_pyq_options_gains_order_and_source_label():
    assert "pyq_options_display_order_positive_chk" in MIGRATION
    assert "add column if not exists source_label text" in MIGRATION
    assert "pyq_options_question_display_order_uidx" in MIGRATION
    assert "on public.pyq_options(question_id, display_order) where display_order is not null" in MIGRATION


def test_pyq_stimuli_table_shape():
    assert "create table if not exists public.pyq_stimuli" in MIGRATION
    assert "pyq_paper_id uuid not null references public.pyq_papers(id) on delete cascade" in MIGRATION
    assert "stimulus_type text not null default 'passage'" in MIGRATION
    assert "'passage', 'caselet', 'table', 'chart', 'image', 'diagram', 'other'" in MIGRATION


def test_pyq_stimuli_has_review_lifecycle_like_questions_and_options():
    # checkpost P0-2: stimuli must carry the same trust gate as pyq_questions/
    # pyq_options (migrations 032/103/155), not just content_text + metadata.
    assert "reviewer_status text not null default 'pending'" in MIGRATION
    assert "check (reviewer_status in ('pending', 'verified', 'rejected', 'needs_correction'))" in MIGRATION
    assert "reviewed_by uuid references public.profiles(id) on delete set null" in MIGRATION
    assert "reviewed_at timestamptz" in MIGRATION
    assert "idx_pyq_stimuli_review" in MIGRATION


def test_pyq_stimuli_display_order_is_positive_and_unique_per_paper():
    assert "pyq_stimuli_display_order_positive_chk" in MIGRATION
    assert "pyq_stimuli_paper_display_order_uidx" in MIGRATION
    assert "on public.pyq_stimuli(pyq_paper_id, display_order) where display_order is not null" in MIGRATION


def test_pyq_stimuli_has_updated_at_trigger():
    assert "trg_pyq_stimuli_updated_at" in MIGRATION
    assert "execute function public.tg_set_updated_at()" in MIGRATION


def test_pyq_question_stimuli_link_table_shape():
    assert "create table if not exists public.pyq_question_stimuli" in MIGRATION
    assert "question_id uuid not null references public.pyq_questions(id) on delete cascade" in MIGRATION
    assert "stimulus_id uuid not null references public.pyq_stimuli(id) on delete cascade" in MIGRATION
    assert "unique(question_id, stimulus_id)" in MIGRATION
    assert "pyq_question_stimuli_display_order_positive_chk" in MIGRATION
    assert "pyq_question_stimuli_question_display_order_uidx" in MIGRATION


def test_cross_parent_integrity_triggers_present_for_question_and_stimulus_section():
    # checkpost P0-1: FK existence alone does not prove the section belongs
    # to the same exam phase as the question's/stimulus's paper.
    assert "pyq_validate_question_section" in MIGRATION
    assert "trg_pyq_questions_validate_section" in MIGRATION
    assert "pyq_validate_stimulus_section" in MIGRATION
    assert "trg_pyq_stimuli_validate_section" in MIGRATION
    assert "v_paper_phase <> v_section_phase" in MIGRATION


def test_cross_parent_integrity_trigger_present_for_question_stimulus_link():
    assert "pyq_validate_question_stimulus_link" in MIGRATION
    assert "trg_pyq_question_stimuli_validate_link" in MIGRATION
    assert "v_question_paper <> v_stimulus_paper" in MIGRATION
    assert "v_question_section <> v_stimulus_section" in MIGRATION


def test_parent_move_revalidation_triggers_present():
    # checkpost P0-1: moving a section/paper/question/stimulus after links
    # already exist must re-validate, not silently orphan the invariant.
    assert "pyq_revalidate_section_move" in MIGRATION
    assert "trg_exam_phase_sections_revalidate_move" in MIGRATION
    assert "pyq_revalidate_paper_phase_move" in MIGRATION
    assert "trg_pyq_papers_revalidate_phase_move" in MIGRATION
    assert "pyq_revalidate_question_paper_move" in MIGRATION
    assert "trg_pyq_questions_revalidate_paper_move" in MIGRATION
    assert "pyq_revalidate_stimulus_paper_move" in MIGRATION
    assert "trg_pyq_stimuli_revalidate_paper_move" in MIGRATION


def test_move_revalidation_triggers_fire_before_update_of_the_moved_column():
    assert "before update of exam_phase_id on public.exam_phase_sections" in MIGRATION
    assert "before update of exam_phase_id on public.pyq_papers" in MIGRATION
    assert "before update of pyq_paper_id on public.pyq_questions" in MIGRATION
    assert "before update of pyq_paper_id on public.pyq_stimuli" in MIGRATION


def test_rls_uses_canonical_is_admin_not_deprecated_profiles_flag():
    assert "public.is_admin(auth.uid())" in MIGRATION
    assert "p.is_admin = true" not in MIGRATION
    assert "pyq_stimuli_admin_all" in MIGRATION
    assert "pyq_question_stimuli_admin_all" in MIGRATION


def test_no_authenticated_read_policy_added_for_canonical_pyq_tables():
    # Aspirant-facing reads continue to flow through the reviewed
    # mock_question_bank projection, matching pyq_papers/pyq_questions/pyq_options.
    assert "for select to authenticated using (true)" not in MIGRATION
