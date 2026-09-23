"""Migration 307 contract (EXPL-OPTID-01) — text-assertion style.

Behavioural validation against real PostgreSQL is VERIFY DB
(`app/supabase/validation/validate_mock_question_options_pyq_option_id.sql`),
which also carries the backfill dry run. These tests guard the invariants that
are decidable from the migration text: the projection writes the source id, the
backfill refuses to guess, and the column cannot delete a bank row.
"""
from __future__ import annotations

from pathlib import Path

_MIGRATIONS = Path(__file__).parents[3] / "supabase/migrations"


def _norm(sql: str) -> str:
    """Lower-case, comment-free, whitespace-collapsed SQL.

    Comments are STRIPPED, not just collapsed: this file asserts on what the
    migration *executes*. Leaving prose in would let a sentence in a header
    satisfy a test about a join condition, which is how a text-assertion suite
    quietly stops meaning anything.
    """
    body = "\n".join(line.split("--")[0] for line in sql.splitlines())
    return " ".join(body.lower().split())


_SQL = (_MIGRATIONS / "307_mock_question_options_pyq_option_id.sql").read_text()
_NORM = _norm(_SQL)

# The projection RPC body, from its create statement to the end of the file.
_FN = _NORM.split("create or replace function public.project_pyq_question_to_mock_bank")[1]
# The backfill statement alone: its leading CTE through its terminating semicolon.
_BACKFILL = _NORM.split("with src as (")[1].split("create or replace function")[0]


def test_column_is_added_nullable_with_an_fk_to_pyq_options():
    assert "alter table public.mock_question_options" in _NORM
    assert "add column if not exists pyq_option_id uuid" in _NORM
    assert "references public.pyq_options(id)" in _NORM
    # Nullable: authored and imported rows have no source option, ever.
    assert "not null" not in _NORM.split("add column if not exists pyq_option_id uuid")[1].split(";")[0]


def test_delete_action_is_set_null_never_cascade():
    """`on delete cascade` would delete projected option rows out from under
    in-flight attempts when a source option is removed. Only `set null` is safe:
    it degrades the join to the positional fallback, which is today's behaviour."""
    fk_clause = _NORM.split("references public.pyq_options(id)")[1].split(";")[0]
    assert "on delete set null" in fk_clause
    assert "cascade" not in fk_clause


def test_projection_writes_the_source_option_id_on_every_projected_option():
    insert = _FN.split("insert into public.mock_question_options")[1].split("returning id")[0]
    # Column list carries it, and the value is the SOURCE row's id.
    assert "pyq_option_id" in insert
    assert "v_opt_row.id" in insert


def test_projection_is_otherwise_272_verbatim():
    """307 re-creates the RPC only to add one column to one insert. If anything
    else drifted, the content hash or the projected field set could change and
    silently re-sync every paper."""
    fn_272 = _norm(
        (_MIGRATIONS / "272_pyq_projection_bytea_cast_fix.sql").read_text()
    ).split("create or replace function public.project_pyq_question_to_mock_bank")[1]

    def _strip_option_insert(body: str) -> str:
        head, rest = body.split("insert into public.mock_question_options", 1)
        _insert, tail = rest.split("returning id", 1)
        return head + tail

    assert _strip_option_insert(_FN) == _strip_option_insert(fn_272)


def test_content_hash_term_is_untouched_so_no_paper_resyncs():
    # The hash idiom 272 established must survive verbatim; pyq_option_id is
    # lineage and must not enter the hashed expression.
    assert "sha256(convert_to(" in _FN
    hashed = _FN.split("sha256(convert_to(")[1].split("'utf8'")[0]
    assert "pyq_option_id" not in hashed


def test_backfill_requires_the_positional_match():
    assert "s.opt_idx" in _BACKFILL and "t.option_index" in _BACKFILL
    assert "row_number() over (partition by o.question_id" in _NORM
    assert "order by o.option_label, o.id) - 1" in _NORM


def test_backfill_carries_a_count_guard():
    """A changed option-set size means no position is trustworthy."""
    assert "s.src_n = t.tgt_n" in _BACKFILL


def test_backfill_carries_a_text_guard():
    """The independent evidence that the position still means what it meant."""
    assert "s.option_text is not distinct from t.option_text" in _BACKFILL


def test_backfill_only_reads_verified_source_options():
    src = _BACKFILL.split(", tgt as (")[0]
    assert "from public.pyq_options o" in src
    assert "o.reviewer_status = 'verified'" in src


def test_backfill_never_overwrites_and_never_touches_authored_rows():
    # Only rows already NULL are written.
    assert "mo.pyq_option_id is null" in _BACKFILL
    # Only rows with PYQ lineage are candidates.
    assert "q.pyq_question_id is not null" in _NORM


def test_backfill_leaves_no_way_to_guess():
    """Every join condition in the backfill must be one of the four guards.
    A stray OR, or a coalesce that invents a match, would turn 'unambiguous'
    into 'best effort'."""
    assert " or " not in _BACKFILL
    assert "coalesce" not in _BACKFILL
    assert "limit 1" not in _BACKFILL


def test_index_exists_for_the_fk_enforcement_scan():
    assert "idx_mock_question_options_pyq_option" in _NORM
    assert "where pyq_option_id is not null" in _NORM


def test_migration_number_is_max_plus_one():
    numbers = sorted(
        int(p.name.split("_")[0])
        for p in _MIGRATIONS.glob("*.sql")
        if p.name.split("_")[0].isdigit()
    )
    assert numbers[-1] == 307
    assert numbers[-2] == 306


def test_header_ships_the_dry_run_and_names_the_validation_script():
    """The backfill's coverage cannot be known without a database, so the
    migration must hand the operator the query rather than assert a number.
    Asserted on the RAW text, because the dry run lives in a comment block."""
    raw = " ".join(_SQL.lower().split())
    assert "dry run" in raw
    assert "would_populate" in raw and "would_stay_null" in raw
    assert (
        _MIGRATIONS.parents[0] / "validation/validate_mock_question_options_pyq_option_id.sql"
    ).exists()
