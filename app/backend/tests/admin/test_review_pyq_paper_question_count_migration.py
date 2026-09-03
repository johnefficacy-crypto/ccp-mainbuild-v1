"""Schema-contract tests for Migration 271
(review_pyq_paper: block verifying a paper that has no questions).

The 2026-08-25 audit added a ``pyq_questions`` count to the pending → verified
blocking-fields list in ``admin_exam_intel_cms.py``. The DB function
``public.review_pyq_paper`` re-validates the same provenance rules on the LOCKED
row in its step 6, but never gained the count check — so a direct ``/rpc/`` call
could verify an empty paper, bypassing the Python gate entirely. Papers
``b06305ad`` and ``c82f3e64`` were verified that way.

Migration 187 is MERGED + IMMUTABLE, so the fix lives only in the forward
migration (271), which ``CREATE OR REPLACE``s the function.

Following the repo convention (no live-DB migration harness): assert against the
migration SQL text, and pin that everything OTHER than the new check is carried
over from 187 unchanged. The executable behavioural proof is
``app/supabase/tests/regression_271_review_pyq_paper_question_count.sql``.
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

MIGRATION = (_MIGRATIONS / "271_review_pyq_paper_question_count_gate.sql").read_text()
MIG_187 = (_MIGRATIONS / "187_review_doc_lock.sql").read_text()

_SIGNATURE = "review_pyq_paper(text, text, text, text, text, text)"


def _fn_body(sql: str) -> str:
    """The review_pyq_paper definition, up to (not including) the grant block."""
    start = sql.index("CREATE OR REPLACE FUNCTION review_pyq_paper(")
    end = sql.index(f"GRANT  EXECUTE ON FUNCTION {_SIGNATURE} TO service_role;")
    return sql[start:end]


def test_migration_replaces_the_function() -> None:
    assert "CREATE OR REPLACE FUNCTION review_pyq_paper(" in MIGRATION
    # A forward migration, not an edit of 187.
    assert "271" in MIGRATION.splitlines()[0]


def test_appends_no_questions_to_the_blocking_list() -> None:
    body = _fn_body(MIGRATION)
    assert "v_blocking := v_blocking || ARRAY['no_questions'];" in body
    # Guarded by an existence check on this paper's questions, not a count scan.
    assert "FROM public.pyq_questions" in body
    assert "WHERE pyq_paper_id = p_paper_id::uuid" in body
    assert "IF NOT EXISTS (" in body


def test_check_sits_inside_the_pending_to_verified_gate() -> None:
    """The count must gate verification only — rejecting an empty paper, or
    reopening it, must stay possible."""
    body = _fn_body(MIGRATION)
    gate_open = body.index(
        "IF v_paper.trust_status = 'pending' AND p_target_status = 'verified' THEN"
    )
    raise_at = body.index("RAISE EXCEPTION 'provenance_incomplete: blocking_fields=%'")
    check_at = body.index("ARRAY['no_questions']")
    assert gate_open < check_at < raise_at


def test_existing_checks_are_preserved_verbatim() -> None:
    body = _fn_body(MIGRATION)
    for fragment in (
        # (a) source_type
        "IF v_paper.source_type IS NULL OR v_paper.source_type = 'unknown' THEN",
        "v_blocking := v_blocking || ARRAY['source_type'];",
        # (b) provenance anchor
        "AND v_paper.source_document_id IS NULL THEN",
        "v_blocking := v_blocking || ARRAY['source_url'];",
        # (c) attached document, still locked
        "FROM public.document_assets",
        "FOR UPDATE;",
        "ARRAY['source_document_id_not_found']",
        "ARRAY['source_document_id_wrong_scope']",
        "ARRAY['source_document_id_wrong_kind']",
        "ARRAY['source_document_id_bad_status']",
        "ARRAY['source_document_id_no_storage']",
        "ARRAY['source_document_id_exam_mismatch']",
    ):
        assert fragment in body, fragment


def test_transition_table_is_unchanged() -> None:
    """271 must not widen or narrow the permitted transitions. In particular it
    must not quietly add verified → pending — see the PR body."""
    body = _fn_body(MIGRATION)
    for clause in (
        "(v_paper.trust_status = 'pending'  AND p_target_status IN ('verified', 'rejected'))",
        "OR (v_paper.trust_status = 'verified' AND p_target_status = 'rejected')",
        "OR (v_paper.trust_status = 'rejected' AND p_target_status = 'pending')",
    ):
        assert clause in body, clause
    assert "v_paper.trust_status = 'verified' AND p_target_status = 'pending'" not in body


def test_reason_gate_and_concurrency_guards_are_unchanged() -> None:
    body = _fn_body(MIGRATION)
    for fragment in (
        "invalid_reason: reason must be 8-500 characters",
        "invalid_target_status: % is not a recognised trust_status",
        "not_found: paper % does not exist",
        "concurrent_modification: expected trust_status=% but found %",
        "concurrent_modification: zero rows updated after lock",
        "FROM public.pyq_papers\n    WHERE id = p_paper_id::uuid\n    FOR UPDATE;",
    ):
        assert fragment in body, fragment


def test_audit_insert_and_return_shape_are_unchanged() -> None:
    body = _fn_body(MIGRATION)
    assert "INSERT INTO public.admin_audit_logs (" in body
    assert "'exam_intel.cms.pyq_paper.review'" in body
    for key in ("'from_status'", "'to_status'", "'reason'", "'reviewed_by'", "'reviewed_at'"):
        assert key in body, key
    assert "'ok',       true" in body
    assert "'audit_id', v_audit_id" in body
    assert "'row',      to_jsonb(v_updated)" in body


def test_grants_match_187() -> None:
    for stmt in (
        f"REVOKE EXECUTE ON FUNCTION {_SIGNATURE} FROM PUBLIC;",
        f"REVOKE EXECUTE ON FUNCTION {_SIGNATURE} FROM anon;",
        f"REVOKE EXECUTE ON FUNCTION {_SIGNATURE} FROM authenticated;",
        f"GRANT  EXECUTE ON FUNCTION {_SIGNATURE} TO service_role;",
    ):
        assert stmt in MIGRATION, stmt


def test_only_the_new_check_differs_from_187() -> None:
    """The strongest assertion available without a live DB: strip the added
    block and what remains must be byte-identical to 187's function."""
    new = _fn_body(MIGRATION)
    old = _fn_body(MIG_187)

    start = new.index("        -- (d) the paper must actually carry questions.")
    end = new.index("        IF array_length(v_blocking, 1) > 0 THEN", start)
    stripped = new[:start] + new[end:]

    assert stripped == old


def test_187_never_had_the_check() -> None:
    """Pins the premise: this is a real gap in the DB path, not a duplicate."""
    assert "pyq_questions" not in _fn_body(MIG_187)
