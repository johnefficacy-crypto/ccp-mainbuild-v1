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


# ── migration 292: the merged link table ────────────────────────────────────
# CONTENT-02. 291 merged the content tables and left three near-identical
# junctions behind; 292 merges those too. These pin the part that was a real
# design choice — how the target is discriminated without losing referential
# integrity.

LINKS_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "supabase/migrations/292_content_card_links_generalisation.sql"
).read_text(encoding="utf-8").lower()
LINKS_SQL = " ".join(LINKS_MIGRATION.split())

# The migration's header explains at length WHY it does not use
# target_type+target_id, so "absent" assertions must read the executable
# surface, not the prose that justifies it.
LINKS_DDL = " ".join(
    line.split("--")[0]
    for line in LINKS_MIGRATION.split("\n")
).replace("  ", " ")
while "  " in LINKS_DDL:
    LINKS_DDL = LINKS_DDL.replace("  ", " ")


def _links_table_body() -> str:
    """The CREATE TABLE block only — no `--` prose, no `comment on` statements."""
    body = LINKS_DDL.split("create table if not exists public.content_card_links")[1]
    return body.split(");")[0]


def test_target_is_two_real_fks_not_target_type_plus_target_id():
    """The whole argument for this shape: PostgreSQL cannot foreign-key one
    column at two tables, so target_type+target_id would buy generality by
    giving up referential integrity. Both FKs and both cascades stay real."""
    assert "question_id uuid references public.mock_question_bank(id) on delete cascade" in LINKS_SQL
    assert "stimulus_id uuid references public.pyq_stimuli(id) on delete cascade" in LINKS_SQL
    # The `comment on constraint` statement records the choice in the database
    # itself and names the rejected shape, so scope this to the table body.
    assert "target_type" not in _links_table_body()
    assert "target_id" not in _links_table_body()


def test_exactly_one_target_is_enforced_by_the_database():
    assert "constraint content_card_links_one_target" in LINKS_SQL
    assert "check (num_nonnulls(question_id, stimulus_id) = 1)" in LINKS_SQL


def test_per_target_uniqueness_replaces_both_source_uniques():
    """The sources had unique (question_id, heuristic_id) and
    unique (stimulus_id, strategy_id). A plain UNIQUE would not reproduce those,
    because the unused target column is NULL on every row."""
    assert "content_card_links_question_card_uidx" in LINKS_SQL
    assert "content_card_links_stimulus_card_uidx" in LINKS_SQL
    assert "where question_id is not null" in LINKS_SQL
    assert "where stimulus_id is not null" in LINKS_SQL


def test_card_type_is_not_represented_on_a_link_row():
    """Card type lives on content_cards.content_type. A link table that also
    carried it would be a second place to get it wrong — and adding a card type
    would touch this table again, which is what the merge exists to stop."""
    assert "content_type" not in _links_table_body()


def test_link_lifecycle_stays_three_valued_not_four():
    """A link is never 'needs_correction': an unsound link is rejected and
    re-made, not revised. Carried over from 243/262/263 unchanged."""
    assert "check (reviewer_status in ('pending', 'verified', 'rejected'))" in LINKS_DDL
    assert "needs_correction" not in LINKS_DDL


def test_links_data_move_is_count_agnostic_and_checks_the_target_side():
    """A bare count would pass a question/stimulus mix-up."""
    assert "row count mismatch" in LINKS_SQL
    for phrase in ("quant link(s) did not round-trip",
                   "reasoning question link(s) did not round-trip",
                   "stimulus link(s) did not round-trip"):
        assert phrase in LINKS_SQL
    assert "t.question_id = s.question_id and t.stimulus_id is null" in LINKS_SQL
    assert "t.stimulus_id = s.stimulus_id and t.question_id is null" in LINKS_SQL


def test_all_three_source_tables_are_dropped_without_cascade():
    for table in ("quant_question_heuristics", "reasoning_question_strategies",
                  "reasoning_stimulus_strategies"):
        assert f"drop table if exists public.{table};" in LINKS_SQL
        assert f"drop table if exists public.{table} cascade" not in LINKS_SQL


def test_links_table_is_rls_enabled_and_service_role_only():
    assert "alter table public.content_card_links enable row level security" in LINKS_SQL
    assert "revoke all on public.content_card_links from anon" in LINKS_SQL
    assert "revoke all on public.content_card_links from authenticated" in LINKS_SQL
    assert "grant select, insert, update, delete on public.content_card_links to service_role" in LINKS_SQL
