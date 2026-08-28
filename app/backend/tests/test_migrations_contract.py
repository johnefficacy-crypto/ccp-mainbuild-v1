from pathlib import Path


def test_active_migration_adds_eligibility_relationship_fks():
    sql = Path("../../app/supabase/migrations/027_eligibility_relationship_fks.sql").read_text().lower()

    for constraint in (
        "age_criteria_post_id_fkey",
        "education_criteria_post_id_fkey",
        "attempt_limits_post_id_fkey",
        "certification_criteria_post_id_fkey",
        "post_disability_requirements_post_id_fkey",
        "age_relaxation_rules_post_id_fkey",
        "posts_recruitment_id_fkey",
        "recruitments_organization_id_fkey",
    ):
        assert constraint in sql

    assert "not valid" in sql
    assert "notify pgrst, 'reload schema';" in sql


def test_migration_266_extends_essay_brainstorm_blocks_for_idea_canvas():
    sql = Path(
        "../../app/supabase/migrations/266_essay_brainstorm_idea_canvas.sql"
    ).read_text().lower()

    # Idea Canvas helper-rail resource types added to the block_type CHECK
    # (quote / example already existed in migration 265).
    for block_type in ("'vocab_term'", "'book_reference'", "'stat_to_verify'"):
        assert block_type in sql
    # Spine stages from 265 must survive the constraint swap.
    for block_type in (
        "'hook'", "'thesis'", "'argument_for'", "'argument_against'",
        "'example'", "'quote'", "'counter_narrative'", "'closing_thought'",
    ):
        assert block_type in sql

    # The six mind-map lenses, nullable for Spine-stage blocks.
    assert "add column if not exists lens text" in sql
    assert "lens is null or lens in" in sql
    for lens in (
        "'economic_efficiency'", "'global_comparative'",
        "'governance_implementation'", "'personal_onground'",
        "'social_equity_access'", "'historical_precedent'",
    ):
        assert lens in sql

    # RLS gap from 265 closed: RLS on, zero client policies, service_role only
    # (migration 195 §4 contract).
    assert "enable row level security" in sql
    assert "revoke all on public.essay_brainstorm_blocks from anon" in sql
    assert "revoke all on public.essay_brainstorm_blocks from authenticated" in sql
    assert "to service_role" in sql
    assert "create policy" not in sql
    assert "notify pgrst, 'reload schema';" in sql
