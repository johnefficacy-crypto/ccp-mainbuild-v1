"""Regression schema-contract tests for migration 238
(PYQ -> mock_question_bank projection: NUL-byte content-hash separator fix).

The projection RPC's content hash previously joined its top-level fields with
chr(0) (ASCII NUL). PostgreSQL `text` cannot contain a null byte — chr(0) raises
`null character not permitted` — so the RPC (and every PYQ->mock sync) crashed
the instant it reached the hash expression. Migration 238 `create or replace`s
the RPC with chr(29) (GS) as the top-level separator; the within-list chr(30)/
chr(31) separators are already valid non-null bytes and are unchanged.

Following the repo convention (no live-DB migration harness): assert against the
migration SQL text. Migrations 183/184/186/187/229 are MERGED + IMMUTABLE — the
fix lives only in the forward migration (238).
"""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

MIGRATION = (_MIGRATIONS / "238_pyq_projection_null_separator_fix.sql").read_text()
MIG_229 = (_MIGRATIONS / "229_pyq_projection_stimulus_fidelity.sql").read_text()


def _hash_expression(sql: str) -> str:
    """Extract just the sha256(...) content-hash expression from an RPC body."""
    lower = sql.lower()
    start = lower.index("sha256((")
    end = lower.index(")::bytea)", start)
    return sql[start:end]


# ── The fix itself ───────────────────────────────────────────────────────────

def test_rpc_is_create_or_replace():
    assert (
        "create or replace function public.project_pyq_question_to_mock_bank"
        in MIGRATION.lower()
    )


def test_hash_expression_has_no_null_byte_separator():
    # The crashing separator must be gone from the actual hash expression.
    expr = _hash_expression(MIGRATION)
    assert "chr(0)" not in expr, "chr(0)/NUL separator would crash the projection RPC"


def test_hash_expression_uses_group_separator_top_level():
    expr = _hash_expression(MIGRATION)
    # 229 joined the identical field set with 16 top-level chr(0) separators;
    # 238 swaps every one of them to chr(29). A drift here means a field was
    # added/removed without keeping the Python mirror in lockstep.
    assert _hash_expression(MIG_229).lower().count("chr(0)") == 16
    assert expr.count("chr(29)") == 16


def test_within_list_separators_unchanged():
    # chr(30) (RS, within item) and chr(31) (US, between list items) are valid
    # non-null bytes and must be preserved exactly as in 229.
    expr_238 = _hash_expression(MIGRATION)
    expr_229 = _hash_expression(MIG_229)
    assert expr_238.count("chr(30)") == expr_229.count("chr(30)")
    assert expr_238.count("chr(31)") == expr_229.count("chr(31)")


def test_field_set_and_order_preserved_from_229():
    # Pure separator swap: replacing chr(0) with chr(29) in the 229 hash
    # expression must reproduce the 238 hash expression verbatim. This proves no
    # projected field was silently added, removed, or reordered.
    assert _hash_expression(MIG_229).replace("chr(0)", "chr(29)") == _hash_expression(MIGRATION)


# ── Posture preserved ────────────────────────────────────────────────────────

def test_service_role_only_posture_preserved():
    low = MIGRATION.lower()
    assert "revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from anon" in low
    assert "revoke execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) from authenticated" in low
    assert "grant execute on function public.project_pyq_question_to_mock_bank(uuid, uuid, text) to service_role" in low


def test_invalidation_trigger_fn_not_rewritten():
    # fn_invalidate_pyq_projection() does not use chr(0); 238 must not re-create
    # it (a passing mention in a comment is fine).
    assert "create or replace function public.fn_invalidate_pyq_projection" not in MIGRATION.lower()
