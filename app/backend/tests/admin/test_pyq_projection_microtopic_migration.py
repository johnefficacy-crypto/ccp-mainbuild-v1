"""Regression schema-contract tests for migration 268
(PYQ -> mock_question_bank projection: microtopic fidelity).

The projection RPC wrote only ``topic_id``, set verbatim from the verified
primary tag. ``public.topics`` is a parent/child tree, so a tag pointing at a
MICROTOPIC was flattened into ``topic_id`` and ``mock_question_bank.microtopic_id``
(present since migration 135) stayed NULL. Migration 268 ``create or replace``s
the RPC to resolve the tag's level from ``topics.parent_topic_id`` and split it
across both columns, and appends the resolved microtopic to the content hash.

Following the repo convention (no live-DB migration harness): assert against the
migration SQL text. Migrations 183/184/186/187/229/239/252 are MERGED +
IMMUTABLE — the fix lives only in the forward migration (268). The executable
behavioural proof is ``app/supabase/tests/regression_268_pyq_projection_microtopic.sql``.
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

MIGRATION = (_MIGRATIONS / "268_pyq_projection_microtopic_fidelity.sql").read_text()
MIG_239 = (_MIGRATIONS / "239_pyq_projection_null_separator_fix.sql").read_text()


def _rpc_body(sql: str) -> str:
    """The RPC definition onwards (function body + grants)."""
    return sql[sql.index("create or replace function public.project_pyq_question_to_mock_bank"):]


def _hash_expression(sql: str) -> str:
    """Extract just the sha256(...) content-hash expression from an RPC body."""
    lower = sql.lower()
    start = lower.index("sha256((")
    end = lower.index(")::bytea)", start)
    return sql[start:end]


# ── Forward-migration posture ────────────────────────────────────────────────

def test_rpc_is_create_or_replace():
    assert (
        "create or replace function public.project_pyq_question_to_mock_bank"
        in MIGRATION.lower()
    )


def test_signature_unchanged():
    body = _rpc_body(MIGRATION)
    assert "p_pyq_question_id uuid" in body
    assert "p_actor_id        uuid" in body
    assert "p_audit_reason    text" in body
    assert "returns jsonb" in body


def test_does_not_edit_a_merged_migration():
    # 239 must still carry its own body untouched — the fix is forward-only.
    assert "microtopic_id" not in _rpc_body(MIG_239)


def test_invalidation_trigger_fn_not_rewritten():
    assert "create or replace function public.fn_invalidate_pyq_projection" not in MIGRATION.lower()


# ── 1/2. Level resolution from topics.parent_topic_id ────────────────────────

def test_resolves_level_from_parent_topic_id():
    body = _rpc_body(MIGRATION)
    assert "if v_topic.parent_topic_id is null then" in body


def test_top_level_tag_keeps_topic_and_nulls_microtopic():
    body = _rpc_body(MIGRATION)
    branch = body[body.index("if v_topic.parent_topic_id is null then"):]
    branch = branch[: branch.index("else")]
    assert "v_topic_id      := v_primary_tag.topic_id;" in branch
    assert "v_microtopic_id := null;" in branch


def test_microtopic_tag_promotes_parent_to_topic():
    body = _rpc_body(MIGRATION)
    branch = body[body.index("if v_topic.parent_topic_id is null then"):]
    branch = branch[branch.index("else"):]
    assert "v_microtopic_id := v_primary_tag.topic_id;" in branch
    assert "v_topic_id      := v_topic.parent_topic_id;" in branch


def test_no_write_path_still_uses_the_raw_tag_topic_id():
    # Every mock_question_bank write must go through the resolved v_topic_id.
    body = _rpc_body(MIGRATION)
    writes = body[body.index("if v_is_new then"):body.index("delete from public.mock_question_options")]
    assert "v_primary_tag.topic_id" not in writes


# ── 3. microtopic_id reaches the INSERT and the UPDATE ───────────────────────

def test_insert_column_list_includes_microtopic_id():
    body = _rpc_body(MIGRATION)
    stmt = body[body.index("insert into public.mock_question_bank ("):]
    cols = stmt[: stmt.index(") values (")]
    assert "microtopic_id" in cols
    # Column order must match the VALUES list: microtopic_id straight after topic_id.
    assert "topic_id, microtopic_id, section_id" in cols
    values = stmt[stmt.index(") values ("): stmt.index("delete from public.mock_question_options")]
    assert "v_topic_id, v_microtopic_id, v_q.section_id" in values


def test_update_branch_sets_microtopic_id():
    body = _rpc_body(MIGRATION)
    assert "topic_id             = v_topic_id," in body
    assert "microtopic_id        = v_microtopic_id," in body


# ── 4. Hash carries the microtopic, NULL-safely ──────────────────────────────

def test_hash_includes_microtopic_id():
    expr = _hash_expression(MIGRATION)
    assert "coalesce(v_microtopic_id::text, '')" in expr


def test_hash_microtopic_is_null_safe():
    # A bare `|| v_microtopic_id::text` would NULL the whole concatenation and
    # hash every top-level-topic question to the same digest.
    expr = _hash_expression(MIGRATION)
    assert "|| v_microtopic_id::text" not in expr.replace("coalesce(v_microtopic_id::text, '')", "")


def test_hash_is_239_plus_exactly_one_appended_field():
    # Pure append: the 239 expression must be a prefix of the 268 expression,
    # with only the new trailing GS + microtopic field after it. This proves no
    # existing projected field was reordered, added, or dropped.
    expr_239 = _hash_expression(MIG_239).rstrip()
    expr_268 = _hash_expression(MIGRATION).rstrip()
    assert expr_268.startswith(expr_239)
    tail = expr_268[len(expr_239):]
    assert tail.split() == ["||", "chr(29)", "||", "coalesce(v_microtopic_id::text,", "'')"]
    # One more top-level separator than 239 had, and no new list separators.
    assert expr_268.count("chr(29)") == expr_239.count("chr(29)") + 1
    assert expr_268.count("chr(30)") == expr_239.count("chr(30)")
    assert expr_268.count("chr(31)") == expr_239.count("chr(31)")


def test_hash_still_has_no_null_byte_separator():
    assert "chr(0)" not in _hash_expression(MIGRATION)


# ── 5. Everything else preserved ─────────────────────────────────────────────

def test_on_conflict_clause_unchanged():
    body_268 = _rpc_body(MIGRATION)
    body_239 = _rpc_body(MIG_239)

    def _on_conflict(b: str) -> str:
        start = b.index("on conflict (pyq_question_id) do update")
        return b[start: b.index("insert into public.admin_audit_logs", start)]

    assert _on_conflict(body_268) == _on_conflict(body_239)


def test_return_shape_unchanged():
    body_268 = _rpc_body(MIGRATION)
    body_239 = _rpc_body(MIG_239)

    def _final_return(b: str) -> str:
        start = b.rindex("return jsonb_build_object(")
        return b[start: b.index("exception", start)]

    assert _final_return(body_268) == _final_return(body_239)


def test_block_reasons_unchanged():
    body_268 = _rpc_body(MIGRATION)
    body_239 = _rpc_body(MIG_239)
    import re
    pat = re.compile(r"fn_block_projection_for_question\(p_pyq_question_id, '([a-z_]+)'\)")
    assert pat.findall(body_268) == pat.findall(body_239)


def test_service_role_only_posture_preserved():
    low = MIGRATION.lower()
    sig = "public.project_pyq_question_to_mock_bank(uuid, uuid, text)"
    assert f"revoke execute on function {sig} from anon" in low
    assert f"revoke execute on function {sig} from authenticated" in low
    assert f"grant execute on function {sig} to service_role" in low


def test_migration_performs_no_backfill():
    low = MIGRATION.lower()
    body = _rpc_body(MIGRATION)
    # No DML outside the function body — this migration only replaces the RPC.
    outside = low.replace(body.lower(), "")
    for dml in ("update public.", "insert into public.", "delete from public."):
        assert dml not in outside
