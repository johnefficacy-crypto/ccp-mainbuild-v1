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


def test_migration_267_adds_nullable_canvas_position_columns():
    sql = Path(
        "../../app/supabase/migrations/267_essay_brainstorm_canvas_position.sql"
    ).read_text().lower()

    # Signed, sub-pixel, exact-decimal coordinates — added, never redefined.
    assert "add column if not exists canvas_x numeric(10,2)" in sql
    assert "add column if not exists canvas_y numeric(10,2)" in sql

    # The pair moves together; a half-placed row is unrenderable.
    assert "essay_brainstorm_blocks_canvas_position_check" in sql
    assert "check ((canvas_x is null) = (canvas_y is null))" in sql
    assert "notify pgrst, 'reload schema';" in sql

    # The "must not contain" checks below are about executable SQL, so drop
    # comment lines first — the header discusses 1440x900 and 266's grants
    # precisely to explain why this migration does NOT touch them.
    body = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )

    # Nullable: no NOT NULL, no default, no backfill. "Unplaced" is a real state.
    assert "not null" not in body
    assert "default" not in body
    assert "update public.essay_brainstorm_blocks" not in body

    # Canvas geometry stays a frontend concern — no bound on the values.
    assert "1440" not in body
    assert "900" not in body

    # Additive only: 266's constraints, RLS posture and grants are untouched.
    for forbidden in (
        "block_type_check",
        "lens_check",
        "enable row level security",
        "grant ",
        "revoke ",
        "drop column",
    ):
        assert forbidden not in body, forbidden
