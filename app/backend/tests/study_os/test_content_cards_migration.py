"""Static contract for migration 291's merged content-card authority.

Live apply/RLS proof remains an operator gate. These assertions pin the
structure, security and lifecycle DDL so a later edit cannot silently weaken the
governance contract — the same posture as
``test_reasoning_strategy_authority_migration.py`` for migration 262.

Two of these are the tests the CONTENT-01 brief asked for specifically: the
dual-FK scope CHECK and the activate/review authority split.
"""
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[3]
    / "supabase/migrations/291_content_cards_generalisation.sql"
)
MIGRATION = MIGRATION_PATH.read_text(encoding="utf-8").lower()
SQL = " ".join(MIGRATION.split())


# ── the dual FK and its scope CHECK ─────────────────────────────────────────

def test_dual_topic_fk_is_preserved_exactly_as_the_source_tables_had_it():
    """Both columns reference topics(id); the shape is house convention, not an
    accident, and CONTENT-01 explicitly forbids simplifying it."""
    assert "topic_id uuid references public.topics(id) on delete set null" in SQL
    assert "microtopic_id uuid references public.topics(id) on delete set null" in SQL


def test_scope_check_requires_at_least_one_of_the_two():
    assert "constraint content_cards_scope_present" in SQL
    assert "check (topic_id is not null or microtopic_id is not null)" in SQL


# ── the open discriminator ──────────────────────────────────────────────────

def test_content_type_is_format_checked_not_value_checked():
    """The contract's seven-value list was never respected by 243 or 262 and
    must not be re-imposed. A format check keeps the column disciplined while
    leaving the SET open."""
    assert "content_type text not null" in SQL
    assert "check (content_type ~ '^[a-z][a-z0-9_]{0,63}$')" in SQL
    for never_enumerate in ("objective_question", "grammar_drill", "passage_set",
                            "descriptive_prompt"):
        assert f"content_type in ('{never_enumerate}" not in SQL
    assert "content_type in (" not in SQL


def test_subtype_check_narrows_known_types_and_stays_open_for_new_ones():
    assert "constraint content_cards_subtype_valid" in SQL
    assert "when 'quant_heuristic' then" in SQL
    assert "when 'reasoning_strategy' then" in SQL
    # the ELSE arm is what keeps an unknown type insertable
    assert "else true" in SQL


# ── applicability_rule is gone, not carried ─────────────────────────────────

def test_applicability_rule_is_not_recreated_on_the_merged_table():
    """It was declared, stored, rendered and never read — no matcher ever
    existed. The merged table must not resurrect it."""
    assert "applicability_rule jsonb" not in SQL
    assert "applicability_rule" in SQL, "the migration should still EXPLAIN the removal"


# ── the data move ───────────────────────────────────────────────────────────

def test_data_move_is_count_agnostic_and_asserts_round_trip():
    """No row count is assumed anywhere; the migration verifies what it moved and
    raises rather than landing a partial move."""
    assert "from public.quant_heuristics h" in SQL
    assert "from public.reasoning_strategies s" in SQL
    assert "row count mismatch" in SQL
    assert "did not round-trip" in SQL


def test_renamed_columns_are_normalised_to_one_name_each():
    assert "h.heuristic_code" in SQL and "s.strategy_code" in SQL
    assert "card_code" in SQL
    assert "h.shortcut_method" in SQL  # -> faster_method
    assert "card_subtype" in SQL


# ── junction repoint ────────────────────────────────────────────────────────

def test_all_three_junctions_are_repointed_and_nothing_else_about_them_changes():
    for table in ("quant_question_heuristics", "reasoning_question_strategies",
                  "reasoning_stimulus_strategies"):
        assert f"alter table public.{table} rename column" in SQL
        assert f"foreign key (card_id) references public.content_cards(id) on delete cascade" in SQL
    # relevance / reviewer_status / unique pairs must be untouched by this migration
    assert "drop constraint if exists quant_question_heuristics_heuristic_id_fkey" in SQL
    assert "alter table public.quant_question_heuristics drop column" not in SQL
    assert "alter table public.reasoning_question_strategies drop column" not in SQL
    assert "alter table public.reasoning_stimulus_strategies drop column" not in SQL


def test_source_tables_are_dropped_without_cascade():
    """CASCADE would silently drop a dependant this migration did not account
    for. The drop must fail loudly instead."""
    assert "drop table if exists public.quant_heuristics;" in SQL
    assert "drop table if exists public.reasoning_strategies;" in SQL
    assert "drop table if exists public.quant_heuristics cascade" not in SQL
    assert "drop table if exists public.reasoning_strategies cascade" not in SQL


# ── security posture ────────────────────────────────────────────────────────

def test_table_is_rls_enabled_and_service_role_only():
    assert "alter table public.content_cards enable row level security" in SQL
    assert "revoke all on public.content_cards from anon" in SQL
    assert "revoke all on public.content_cards from authenticated" in SQL
    assert "grant select, insert, update, delete on public.content_cards to service_role" in SQL


def test_every_rpc_is_service_role_only():
    for fn in (
        "public.cms_review_content_card(uuid, text, timestamptz, text, text, text, uuid, text)",
        "public.cms_activate_content_card(uuid, timestamptz, text, uuid, text)",
        "public.cms_deactivate_content_card(uuid, timestamptz, text, uuid, text)",
    ):
        assert fn in SQL
    assert "revoke execute on function %s from anon" in SQL
    assert "revoke execute on function %s from authenticated" in SQL
    assert "grant execute on function %s to service_role" in SQL


# ── the review lifecycle, carried forward ───────────────────────────────────

def test_review_rpc_keeps_the_hardened_dual_cas_and_mandatory_reason():
    assert "p_expected_updated_at (cas token) is required" in SQL
    assert "invalid_reason: p_reason must be 8" in SQL
    assert "transition_not_allowed" in SQL
    assert "reviewer_notes required when reopening a verified card" in SQL


# ── the activate split — the authority that did not exist before ────────────

def test_activation_is_a_precondition_machine_not_a_toggle():
    """Mirrors migration 226: blockers are COLLECTED (no short-circuit) and a
    blocked activation returns eligible=false rather than raising."""
    assert "v_blockers text[] := '{}'" in SQL
    for blocker in ("reason_required", "card_not_verified", "already_active"):
        assert f"array_append(v_blockers, '{blocker}')" in SQL
    assert "'eligible', false, 'blockers', to_jsonb(v_blockers)" in SQL


def test_activation_cas_and_missing_actor_stay_hard_errors():
    """CAS is a HARD error, never a blocker — 226's rule."""
    assert "stale_card — p_expected_updated_at (cas token) is required" in SQL
    assert "missing_actor_id: p_actor_user_id must not be null" in SQL


def test_activation_writes_its_own_audit_action():
    assert "'content_card_activated'" in SQL
    assert "'content_card_deactivated'" in SQL


def test_activation_invents_no_applicability_gate():
    """writing_prompt_targets is prompt-specific and content_cards has no
    applicability model; asserting one here would be a gate that does not exist.

    The migration NAMES writing_prompt_targets in a comment explaining the
    deliberate difference from 226, so this checks the executable surface: no
    query against that table, and no such blocker.
    """
    assert "no_active_applicability_target" not in SQL
    assert "from public.writing_prompt_targets" not in SQL
    assert "v_has_active_target" not in SQL
